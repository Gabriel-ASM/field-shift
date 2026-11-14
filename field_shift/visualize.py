"""Generate the offline crop-rotation, soil Markov and Monte Carlo demonstration."""

from argparse import ArgumentParser
import json
from pathlib import Path
from random import Random


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).with_name("replay.html")
STATE_NAMES = {"RO": "Rondônia", "SP": "São Paulo", "MG": "Minas Gerais"}
PAM_CROPS = {
    "soybean": "soja_em_grao",
    "peanut": "amendoim_em_casca",
    "maize_grain": "milho_em_grao",
    "sorghum_grain": "sorgo_em_grao",
}
CROP_GROUPS = {
    "soybean": "legume",
    "peanut": "legume",
    "dry_bean": "legume",
    "maize_grain": "grass",
    "maize_brachiaria": "grass",
    "sorghum_grain": "grass",
}
CROP_NAMES = {
    "soybean": "Soja",
    "peanut": "Amendoim",
    "maize_grain": "Milho-grão",
    "maize_brachiaria": "Milho 2ª safra + braquiária",
    "sorghum_grain": "Sorgo-grão",
}
PRICE_CROPS = {"soybean": "soybean", "maize_grain": "maize", "maize_brachiaria": "maize"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def payload_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def zarc_crop_id(row: dict) -> str | None:
    crop_id = row.get("crop_parameter_id")
    if crop_id in CROP_GROUPS:
        return crop_id
    label = str(row.get("crop", "")).casefold()
    if "milho" in label and "braqui" in label:
        return "maize_brachiaria"
    return None


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


def soil_class(carbon: float, prior: dict) -> str:
    thresholds = prior["soil_proxy"]["classes"]
    if carbon < thresholds[0]["maximum_exclusive_g_kg"]:
        return "low"
    if carbon <= thresholds[1]["maximum_inclusive_g_kg"]:
        return "medium"
    return "high"


def crop_options(profile_dir: Path, pam: dict, prices_by_crop: dict) -> list[dict]:
    zarc = read_json(profile_dir / "zarc-planting-windows.json")
    options = {}
    for row in zarc["rows"]:
        crop_id = zarc_crop_id(row)
        if not crop_id:
            continue
        planting_decendios = row.get("planting_decendios_by_risk_percent", {}).get("20", [])
        if not planting_decendios:
            continue
        item = options.setdefault(
            crop_id,
            {
                "id": crop_id,
                "name": CROP_NAMES[crop_id],
                "group": CROP_GROUPS[crop_id],
                "planting_decendios": set(),
                "risk_percent": 20,
            },
        )
        item["planting_decendios"].update(planting_decendios)

    result = []
    for crop_id, item in options.items():
        pam_id = PAM_CROPS.get(crop_id)
        pam_summary = pam.get("crop_summaries", {}).get(pam_id, {}) if pam_id else {}
        yield_kg_ha = pam_summary.get("yield_mean_2021_2025_kg_ha")
        price_crop = PRICE_CROPS.get(crop_id)
        quote = prices_by_crop.get(price_crop)
        item["planting_decendios"] = sorted(item["planting_decendios"])
        item["pam_yield_mean_2021_2025_kg_ha"] = yield_kg_ha
        item["pam_valid_yield_years"] = pam_summary.get("valid_yield_years", 0)
        item["pam_crop_id"] = pam_id
        item["price"] = quote
        item["gross_value_brl_per_ha"] = (
            yield_kg_ha / 1000 * quote["price_brl_per_metric_ton"]
            if yield_kg_ha is not None and quote
            else None
        )
        result.append(item)
    return sorted(result, key=lambda item: (item["name"], item["id"]))


def export_page(output: Path, seed: int) -> None:
    catalog = read_json(ROOT / "data" / "catalog" / "perfis-exemplo.json")
    rotation_prior = read_json(ROOT / "data" / "reference" / "rotation-soil-prior.json")
    prices = read_json(ROOT / "data" / "reference" / "yahoo-harvest-futures.json")
    prices_by_crop = {item["crop"]: item for item in prices["quotes"]}
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
        pam = read_json(profile_dir / "pam-history.json")
        crop_results = sorted((ROOT / "data" / "processed").glob(f"crop-scenario-{profile_id}-*-d*.json"))
        if not crop_results:
            raise FileNotFoundError(f"No registered crop scenario for {profile_id}")
        registered = read_json(crop_results[0])
        initial_crop_id = registered["scenario"]["crop_parameter_id"]
        options = crop_options(profile_dir, pam, prices_by_crop)
        if initial_crop_id not in {item["id"] for item in options}:
            raise ValueError(f"Initial crop {initial_crop_id} is not an eligible rotation option for {profile_id}")
        carbon = topsoil_carbon_g_kg(soil)

        profile_data[profile_id] = {
            "location": {
                "municipality": manifest["location"]["municipality"],
                "uf": manifest["location"]["uf"],
                "ibge_code": manifest["location"]["ibge_code"],
            },
            "soil": {
                "organic_carbon_top_0_30_g_kg": carbon,
                "initial_class": soil_class(carbon, rotation_prior),
                "source": soil["source"],
                "scope": soil["scope"],
                "sample_point_basis": soil["sample_point"]["basis"],
            },
            "initial_crop_id": initial_crop_id,
            "crop_options": options,
            "price_snapshot": {
                "as_of_date": prices["as_of_date"],
                "usd_brl_ptax_sell": prices["fx"]["rate"],
            },
            "pam_yield_period": "2021-2025 municipal mean; not a parcel estimate",
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
        "<!-- ROTATION_SOIL_PRIOR -->": payload_json(rotation_prior),
        "<!-- HARVEST_PRICES -->": payload_json(prices),
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
