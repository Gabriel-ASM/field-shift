"""Generate the offline crop Markov and Monte Carlo demonstration."""

from argparse import ArgumentParser
import json
from pathlib import Path
from random import Random

from ..engines.payload import profile_payload
from ..ingest.profiles import topsoil_mean


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data"
FRONT = Path(__file__).parent
TEMPLATE = FRONT / "index.html"
STATE_NAMES = {"RO": "Rondônia", "SP": "São Paulo", "MG": "Minas Gerais"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def payload_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def topsoil_carbon_g_kg(soil: dict) -> float:
    return topsoil_mean(soil["layers"], "organic_carbon_g_kg")


def export_page(output: Path, seed: int) -> None:
    if not DATA_ROOT.is_dir():
        raise FileNotFoundError(f"Canonical data directory not found: {DATA_ROOT}")
    catalog = read_json(DATA_ROOT / "catalog" / "perfis-exemplo.json")
    soil_hypotheses = read_json(DATA_ROOT / "reference" / "soil-crop-response-hypotheses.json")
    crop_cycles = read_json(DATA_ROOT / "reference" / "crop-cycle-assumptions.json")
    run_settings = read_json(DATA_ROOT / "reference" / "visualization-run-settings.json")
    economic_prices = read_json(DATA_ROOT / "reference" / "yahoo-harvest-futures.json")
    rng = Random(seed)
    by_uf = {}
    for profile in catalog["profiles"]:
        by_uf.setdefault(profile["uf"], []).append(profile)

    cases = []
    profile_data = {}
    for uf in ("RO", "SP", "MG"):
        selected = rng.choice(by_uf[uf])
        profile_id = selected["profile"]
        profile_data[profile_id] = profile_payload(profile_id)
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
        "<!-- FRONT_CSS -->": (FRONT / "styles.css").read_text(encoding="utf-8"),
        "<!-- ANALYSIS_JS -->": (FRONT / "analysis.js").read_text(encoding="utf-8"),
        "<!-- PRODUCER_JS -->": (FRONT / "producer.js").read_text(encoding="utf-8"),
        "<!-- CASE_DATA -->": payload_json({"seed": seed, "cases": cases}),
        "<!-- PROFILE_DATA -->": payload_json(profile_data),
        "<!-- SOIL_HYPOTHESES -->": payload_json(soil_hypotheses),
        "<!-- CROP_CYCLES -->": payload_json(crop_cycles),
        "<!-- RUN_SETTINGS -->": payload_json(run_settings),
        "<!-- ECONOMIC_DATA -->": payload_json({
            "price_snapshot": economic_prices,
        }),
    }
    for marker, value in replacements.items():
        marker_count = html.count(marker)
        if marker_count != 1:
            raise ValueError(
                f"Expected exactly one {marker!r} placeholder in {TEMPLATE}, found {marker_count}"
            )
        html = html.replace(marker, value, 1)
    unresolved = [marker for marker in replacements if marker in html]
    if unresolved:
        raise ValueError(f"Unresolved data placeholders in {TEMPLATE}: {', '.join(unresolved)}")
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
