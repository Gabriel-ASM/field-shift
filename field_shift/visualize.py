"""Generate the offline crop Markov and Monte Carlo demonstration."""

from argparse import ArgumentParser
import json
from pathlib import Path
from random import Random


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).with_name("replay.html")
STATE_NAMES = {"RO": "Rondônia", "SP": "São Paulo", "MG": "Minas Gerais"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def payload_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def topsoil_carbon_g_kg(soil: dict) -> float:
    layers = soil["layers"]
    intervals = [(0, 5), (5, 15), (15, 30)]
    weighted = 0.0
    depth = 0
    for top, bottom in intervals:
        layer = next(item for item in layers if item["depth_top_cm"] == top and item["depth_bottom_cm"] == bottom)
        layer_depth = bottom - top
        weighted += layer["organic_carbon_g_kg"] * layer_depth
        depth += layer_depth
    return weighted / depth


def water_markov(profile_dir: Path) -> dict:
    states = read_json(profile_dir / "states.json")
    transitions = read_json(profile_dir / "transitions.json")
    environment_history = read_json(profile_dir / "environment.json")
    labels = {"water_low": "Baixa", "water_medium": "Média", "water_high": "Alta"}
    return {
        "states": [
            {"id": state["id"], "water_class": state["water"], "label": labels[state["id"]]}
            for state in states
        ],
        "transitions": [
            {
                "from_state": row["state"],
                "environment": row["environment"],
                "counts": row["counts"],
                "sample_size": int(row["sample_size"]),
                "effective_sample_size": int(row.get("effective_sample_size", sum(row["counts"].values()))),
                "support": row["support"],
                "pooling": row.get("pooling"),
                "provenance": row["provenance"],
            }
            for row in transitions
        ],
        "environment_years": {
            year: labels
            for year, labels in sorted(environment_history.items())
            if 1983 <= int(year) <= 2025
        },
        "years": [1983, 2025],
        "periods_per_year": 24,
        "initial_state_id": "water_medium",
        "initial_storage_fraction": 0.5,
        "provenance": (
            "Transições derivadas de balanço hídrico quinzenal com chuva e ETo da NASA POWER, "
            "AWC SoilGrids/Saxton–Rawls e demanda de referência Kc=1. Não são medições de água no talhão."
        ),
    }


def export_page(output: Path, seed: int) -> None:
    catalog = read_json(ROOT / "data" / "catalog" / "perfis-exemplo.json")
    soil_hypotheses = read_json(ROOT / "data" / "reference" / "soil-crop-response-hypotheses.json")
    crop_cycles = read_json(ROOT / "data" / "reference" / "crop-cycle-assumptions.json")
    economic_prices = read_json(ROOT / "data" / "reference" / "yahoo-harvest-futures.json")
    economic_benchmarks = read_json(ROOT / "data" / "reference" / "economic-benchmarks.json")
    rng = Random(seed)
    by_uf = {}
    for profile in catalog["profiles"]:
        by_uf.setdefault(profile["uf"], []).append(profile)

    cases = []
    profile_data = {}
    for uf in ("RO", "SP", "MG"):
        selected = rng.choice(by_uf[uf])
        profile_id = selected["profile"]
        profile_dir = ROOT / "data" / "profiles" / profile_id
        manifest = read_json(profile_dir / "manifest.json")
        soil = read_json(profile_dir / "soil-profile.json")
        climate_summary = read_json(profile_dir / "climate-summary.json")
        crop_markov = read_json(profile_dir / "crop-transition-markov.json")
        zarc_planting_windows = read_json(profile_dir / "zarc-planting-windows.json")
        carbon = topsoil_carbon_g_kg(soil)

        profile_data[profile_id] = {
            "location": {
                "municipality": manifest["location"]["municipality"],
                "uf": manifest["location"]["uf"],
                "ibge_code": manifest["location"]["ibge_code"],
            },
            "soil": {
                "organic_carbon_top_0_30_g_kg": carbon,
                "available_water_capacity_mm": soil["available_water_capacity_mm"],
                "source": soil["source"],
                "scope": soil["scope"],
                "sample_point_basis": soil["sample_point"]["basis"],
            },
            "crop_markov": crop_markov,
            "zarc_planting_windows": zarc_planting_windows,
            "water_markov": water_markov(profile_dir),
            "climate_summary": climate_summary,
            "economics": economic_benchmarks["profiles"][profile_id],
        }
        cases.append(
            {
                "profile": profile_id,
                "municipality": selected["municipality"],
                "uf": uf,
                "state_name": STATE_NAMES[uf],
            }
        )

    html = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "<!-- CASE_DATA -->": payload_json({"seed": seed, "cases": cases}),
        "<!-- PROFILE_DATA -->": payload_json(profile_data),
        "<!-- SOIL_HYPOTHESES -->": payload_json(soil_hypotheses),
        "<!-- CROP_CYCLES -->": payload_json(crop_cycles),
        "<!-- ECONOMIC_DATA -->": payload_json({
            "price_snapshot": economic_prices,
            "discount_rate": economic_benchmarks["discount_rate"],
            "reference_currency_month": economic_benchmarks["reference_currency_month"],
        }),
    }
    for marker, value in replacements.items():
        html = html.replace(marker, value, 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/visualizacao.html"))
    parser.add_argument("--seed", type=int, default=2026)
    options = parser.parse_args()
    export_page(options.output, options.seed)


if __name__ == "__main__":
    main()
