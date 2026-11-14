"""Derive an explicit single-crop Markov chain from municipal PAM histories."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = ROOT / "data" / "profiles"
CATALOG = [
    {"id": "soybean", "name": "Soja", "pam_crops": ["soja_em_grao"], "initial": True, "water_id": "soybean"},
    {"id": "maize_grain", "name": "Milho", "pam_crops": ["milho_em_grao"], "initial": True, "water_id": "maize_grain"},
    {"id": "sugarcane", "name": "Cana-de-açúcar", "pam_crops": ["cana_de_acucar"], "initial": True, "water_id": "sugarcane"},
    {"id": "coffee", "name": "Café", "pam_crops": ["cafe_arabica", "cafe_canephora"], "initial": True, "water_id": "coffee_bare"},
    {"id": "sorghum_grain", "name": "Sorgo", "pam_crops": ["sorgo_em_grao"], "initial": False, "water_id": "sorghum_grain"},
    {"id": "wheat", "name": "Trigo", "pam_crops": ["trigo_em_grao"], "initial": False, "water_id": "wheat"},
    {"id": "dry_bean", "name": "Feijão", "pam_crops": ["feijao_em_grao"], "initial": False, "water_id": "dry_bean"},
    {"id": "peanut", "name": "Amendoim", "pam_crops": ["amendoim_em_casca"], "initial": False, "water_id": "peanut"},
    {"id": "oat", "name": "Aveia-preta", "pam_crops": ["aveia_em_grao"], "initial": False, "water_id": "oat"},
    {"id": "forage_radish", "name": "Nabo forrageiro", "pam_crops": [], "initial": False, "water_id": "forage_radish"},
    {"id": "brachiaria", "name": "Braquiária", "pam_crops": [], "initial": False, "water_id": "brachiaria"},
    {"id": "millet", "name": "Milheto", "pam_crops": [], "initial": False, "water_id": "millet"},
    {"id": "crotalaria", "name": "Crotalária", "pam_crops": [], "initial": False, "water_id": "crotalaria"},
    {"id": "mucuna", "name": "Mucuna", "pam_crops": [], "initial": False, "water_id": "mucuna"},
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def annual_effective_kc(crop: dict) -> tuple[float | None, str]:
    kc = crop.get("kc") or {}
    if "internal_discrepancy" in str(crop.get("support", "")):
        return None, "FAO-56 phase duration is internally inconsistent; reference Kc=1 used in water evolution"
    if not kc or kc.get("mid") is None:
        return None, "missing_crop_specific_parameter; reference Kc=1 used in water evolution"
    stage_days = crop.get("stage_days")
    if not stage_days:
        return float(kc["mid"]), "published Kc_mid used across the year; annual phases unavailable"
    initial = float(kc.get("initial", kc["mid"]))
    middle = float(kc["mid"])
    final = float(kc.get("end", middle))
    development = (initial + middle) / 2
    late = (middle + final) / 2
    phase_kc = {"initial": initial, "development": development, "mid": middle, "late": late}
    crop_days = sum(int(days) for days in stage_days.values())
    demand = sum(phase_kc.get(phase, middle) * int(days) for phase, days in stage_days.items())
    duration = int(crop.get("duration_days") or crop_days)
    if duration > 365:
        crop_fraction = 1.0
        demand *= 365 / max(crop_days, 1)
    else:
        crop_fraction = duration / 365
    annual_demand = demand / 365 + (1 - crop_fraction) * 1.0
    return annual_demand, "derived from FAO-56 phase Kc/duration; off-crop reference Kc=1"


def build_profile(profile_dir: Path, crop_water_parameters: dict, alpha_per_destination: float) -> dict:
    pam = read_json(profile_dir / "pam-history.json")
    manifest_path = profile_dir / "manifest.json"
    manifest = read_json(manifest_path)
    pam_to_state = {
        pam_crop: crop["id"]
        for crop in CATALOG
        for pam_crop in crop["pam_crops"]
    }
    names = {crop["id"]: crop["name"] for crop in CATALOG}
    water_parameters = {crop["id"]: crop for crop in crop_water_parameters["crops"]}
    states = []
    for crop in CATALOG:
        water = water_parameters.get(crop["water_id"], {})
        effective_kc, effective_kc_support = annual_effective_kc(water)
        states.append({
            "id": crop["id"],
            "name": crop["name"],
            "initial_selectable": crop["initial"],
            "water_parameter_id": crop["water_id"],
            "kc_mid": (water.get("kc") or {}).get("mid"),
            "kc_annual_effective": effective_kc,
            "kc_annual_support": effective_kc_support,
            "water_parameter_support": water.get("support", "missing_crop_specific_parameter"),
        })

    areas_by_year: dict[int, dict[str, float]] = {}
    for row in pam["records"]:
        state_id = pam_to_state.get(str(row.get("crop", "")))
        area = row.get("harvested_area_ha")
        if state_id is None or area is None or float(area) <= 0:
            continue
        year = int(row["year"])
        areas = areas_by_year.setdefault(year, {})
        areas[state_id] = areas.get(state_id, 0.0) + float(area)

    annual = []
    for year, areas in sorted(areas_by_year.items()):
        dominant = max(areas, key=lambda state_id: (areas[state_id], state_id))
        annual.append({
            "year": year,
            "state_id": dominant,
            "crop_name": names[dominant],
            "harvested_area_ha": areas[dominant],
            "reported_crop_areas_ha": areas,
        })

    edge_counts: dict[tuple[str, str], int] = {}
    edge_year_pairs: dict[tuple[str, str], list[list[int]]] = {}
    outgoing: dict[str, int] = {}
    for current, following in zip(annual, annual[1:]):
        if int(following["year"]) != int(current["year"]) + 1:
            continue
        key = (current["state_id"], following["state_id"])
        edge_counts[key] = edge_counts.get(key, 0) + 1
        edge_year_pairs.setdefault(key, []).append([current["year"], following["year"]])
        outgoing[current["state_id"]] = outgoing.get(current["state_id"], 0) + 1

    transitions = [
        {
            "from_state": source,
            "to_state": destination,
            "count": count,
            "outgoing_count": outgoing[source],
            "observed_year_pairs": edge_year_pairs[(source, destination)],
        }
        for (source, destination), count in sorted(edge_counts.items())
    ]
    observed_years = [item["year"] for item in annual]
    profile = manifest["location"]
    payload = {
        "schema_version": "1.0.0",
        "model": "municipal_catalog_dominant_crop_markov_proxy",
        "unit_of_analysis": "município-ano; uma cultura de maior área entre os produtos do catálogo, não o mesmo talhão",
        "source": {
            "publisher": pam["source"]["publisher"],
            "survey": pam["source"]["survey"],
            "table": pam["source"]["table"],
            "url": pam["source"]["url"],
            "municipality_ibge_code": profile["ibge_code"],
            "municipality": profile["municipality"],
            "period": [min(observed_years), max(observed_years)] if observed_years else [],
        },
        "state_definition": "A cultura do catálogo com maior área colhida PAM no município-ano; produtos fora do catálogo não competem pelo estado dominante. Café arábica e canephora são agregados no estado Café.",
        "probability_definition": "Contagem PAM + prior Dirichlet uniforme alpha=0.5 por destino, reponderada pela água e hipótese explícita de carbono do solo durante o Monte Carlo.",
        "alpha_per_destination": alpha_per_destination,
        "period": [min(observed_years), max(observed_years)] if observed_years else [],
        "annual_observation_count": len(annual),
        "adjacent_year_transition_count": sum(edge_counts.values()),
        "states": states,
        "initial_crop_ids": [crop["id"] for crop in CATALOG if crop["initial"]],
        "transitions": transitions,
        "annual_sequence": annual,
        "limitations": [
            "O estado é dominante apenas entre os produtos incluídos no catálogo; produtos PAM fora dele, como arroz, não competem pelo estado dominante.",
            "A cultura de maior área entre os produtos do catálogo não identifica o cultivo ou a rotação do mesmo talhão.",
            "A prior uniforme torna todas as culturas destinos possíveis; quando count=0, a probabilidade não é frequência observada.",
            "PAM não cobre todas as culturas de cobertura do catálogo; essas linhas dependem integralmente da prior.",
        ],
    }
    output = profile_dir / "crop-transition-markov.json"
    write_json(output, payload)
    manifest.setdefault("datasets", {}).pop("crop-portfolio-markov.json", None)
    manifest.setdefault("datasets", {})[output.name] = {
        "origem": "IBGE PAM/SIDRA tabela 5457; derivado de pam-history.json",
        "responsavel": "Field Shift derivação; build_crop_transition_markov.py",
        "frequencia": "anual; uma cultura dominante por município-ano",
        "unidade": f"transições da cultura de maior área entre produtos do catálogo em anos consecutivos; pseudocontagem alpha={alpha_per_destination:g} separada das observações",
        "periodo": f"{payload['period'][0]}–{payload['period'][1]}" if payload["period"] else "sem dados",
        "resolucao": "município IBGE; não identifica pixel ou talhão",
        "qualidade": "contagens empíricas PAM; a prior uniforme habilita destinos sem contagem e está marcada no payload",
        "sha256": sha256(output.read_bytes()).hexdigest(),
    }
    write_json(manifest_path, manifest)
    return payload


def main() -> None:
    water_parameters = read_json(ROOT / "data" / "reference" / "crop-water-parameters.json")
    soil_hypotheses = read_json(ROOT / "data" / "reference" / "soil-crop-response-hypotheses.json")
    alpha_per_destination = float(soil_hypotheses["probability_modifiers"]["rotation_prior_alpha_per_destination"])
    for profile_dir in sorted(PROFILE_ROOT.iterdir()):
        if profile_dir.is_dir() and (profile_dir / "pam-history.json").exists():
            payload = build_profile(profile_dir, water_parameters, alpha_per_destination)
            print(
                f"{payload['source']['municipality_ibge_code']}: "
                f"{payload['annual_observation_count']} anos, "
                f"{payload['adjacent_year_transition_count']} pares anuais, "
                f"{len(payload['states'])} culturas no catálogo"
            )


if __name__ == "__main__":
    main()
