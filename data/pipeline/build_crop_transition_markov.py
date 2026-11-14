"""Derive a top-five area-weighted crop Markov proxy from municipal PAM histories."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from contract_registry import current_contract_version, validate_contract


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


def build_profile(profile_dir: Path, crop_water_parameters: dict, alpha_per_destination: float, lifecycle_rules: dict, top_crop_limit: int = 5) -> dict:
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
        ranked = sorted(areas, key=lambda state_id: (-areas[state_id], state_id))[:top_crop_limit]
        top_area = sum(areas[state_id] for state_id in ranked)
        ranked_crops = [
            {
                "rank": index + 1,
                "state_id": state_id,
                "crop_name": names[state_id],
                "harvested_area_ha": areas[state_id],
                "area_share_within_top5": areas[state_id] / top_area,
            }
            for index, state_id in enumerate(ranked)
        ]
        dominant = ranked_crops[0]
        annual.append({
            "year": year,
            "state_id": dominant["state_id"],
            "crop_name": dominant["crop_name"],
            "harvested_area_ha": dominant["harvested_area_ha"],
            "top5_area_total_ha": top_area,
            "top5_crops": ranked_crops,
            "reported_crop_areas_ha": areas,
        })

    dominant_edge_counts: dict[tuple[str, str], int] = {}
    dominant_edge_year_pairs: dict[tuple[str, str], list[list[int]]] = {}
    dominant_outgoing: dict[str, int] = {}
    area_weighted_edge_mass: dict[tuple[str, str], float] = {}
    area_weighted_outgoing: dict[str, float] = {}
    adjacent_year_pairs = 0
    for current, following in zip(annual, annual[1:]):
        if int(following["year"]) != int(current["year"]) + 1:
            continue
        adjacent_year_pairs += 1
        key = (current["state_id"], following["state_id"])
        dominant_edge_counts[key] = dominant_edge_counts.get(key, 0) + 1
        dominant_edge_year_pairs.setdefault(key, []).append([current["year"], following["year"]])
        dominant_outgoing[current["state_id"]] = dominant_outgoing.get(current["state_id"], 0) + 1

        # PAM has municipal crop areas, not field-linked pairs. The outer product
        # is the maximum-entropy joint distribution consistent with each year's
        # top-five area shares; it is expected transition mass, not an observed
        # field rotation.
        source_shares = {item["state_id"]: item["area_share_within_top5"] for item in current["top5_crops"]}
        destination_shares = {item["state_id"]: item["area_share_within_top5"] for item in following["top5_crops"]}
        for source, source_share in source_shares.items():
            area_weighted_outgoing[source] = area_weighted_outgoing.get(source, 0.0) + source_share
            for destination, destination_share in destination_shares.items():
                pair = (source, destination)
                area_weighted_edge_mass[pair] = area_weighted_edge_mass.get(pair, 0.0) + source_share * destination_share

    transitions = [
        {
            "from_state": source,
            "to_state": destination,
            "count": dominant_edge_counts.get((source, destination), 0),
            "outgoing_count": dominant_outgoing.get(source, 0),
            "observed_year_pairs": dominant_edge_year_pairs.get((source, destination), []),
            "area_weighted_count": round(area_weighted_edge_mass.get((source, destination), 0.0), 12),
            "area_weighted_outgoing_count": round(area_weighted_outgoing.get(source, 0.0), 12),
        }
        for source, destination in sorted(set(dominant_edge_counts) | set(area_weighted_edge_mass))
    ]
    observed_years = [item["year"] for item in annual]
    profile = manifest["location"]
    payload = {
        "schema_version": "1.2.0",
        "model": "municipal_top5_area_weighted_markov_proxy",
        "unit_of_analysis": "distribuições anuais de área PAM no município; transições marginais entre anos, não o mesmo talhão",
        "source": {
            "publisher": pam["source"]["publisher"],
            "survey": pam["source"]["survey"],
            "table": pam["source"]["table"],
            "url": pam["source"]["url"],
            "municipality_ibge_code": profile["ibge_code"],
            "municipality": profile["municipality"],
            "period": [min(observed_years), max(observed_years)] if observed_years else [],
        },
        "state_definition": f"Distribuição das {top_crop_limit} culturas do catálogo com maior área colhida PAM no município-ano, ponderadas pela participação na área somada do top {top_crop_limit}. Produtos fora do catálogo não competem. Café arábica e canephora são agregados no estado Café.",
        "probability_definition": "Massa de transição top-5 = participação de área da cultura de origem no ano t × participação da cultura de destino no ano t+1, somada nos pares anuais consecutivos; supõe independência entre talhões agregados e não é uma rotação observada. A cadeia usa essa massa fracionária + prior Dirichlet uniforme e fatores ambientais por trajetória; contagens do dominante rank 1 ficam separadas para auditoria.",
        "transition_weighting_method": "max_entropy_outer_product_of_top5_area_shares",
        "top_crop_limit": top_crop_limit,
        "area_weighted_transition_pair_count": adjacent_year_pairs,
        "alpha_per_destination": alpha_per_destination,
        "period": [min(observed_years), max(observed_years)] if observed_years else [],
        "annual_observation_count": len(annual),
        "adjacent_year_transition_count": adjacent_year_pairs,
        "states": states,
        "initial_crop_ids": [crop["id"] for crop in CATALOG if crop["initial"]],
        "lifecycle_rules": {crop_id: lifecycle_rules[crop_id] for crop_id in ("coffee", "sugarcane") if crop_id in lifecycle_rules},
        "transitions": transitions,
        "annual_sequence": annual,
        "limitations": [
            f"O top {top_crop_limit} é calculado apenas entre os produtos PAM mapeados ao catálogo; produtos fora dele, como arroz, não competem pelo ranking.",
            "As participações anuais são área colhida municipal e não identificam talhões, sucessões ou consórcios individuais.",
            "A massa de transição fracionária é o produto independente das participações top-5 em anos consecutivos; ela é uma aproximação de máxima entropia, não contagem observada de pares de lavouras.",
            "As transições rank 1 são mantidas como auditoria, mas a cadeia probabilística usa a massa top-5 ponderada para não duplicar os mesmos pares anuais como evidência independente.",
            "A prior uniforme torna todas as culturas elegíveis destinos possíveis; quando area_weighted_count=0, a probabilidade não é frequência observada.",
            "PAM não cobre todas as culturas de cobertura do catálogo; essas linhas dependem integralmente da prior.",
            "Para café e cana, regras estruturais mantêm a cultura no horizonte enquanto faltam idade e histórico de reforma; cobertura de entrelinha é manejo associado, não destino Markov.",
        ],
    }
    validate_contract("crop_transition_markov", payload, source=f"{profile_dir.name}/crop-transition-markov.json")
    output = profile_dir / "crop-transition-markov.json"
    write_json(output, payload)
    manifest.setdefault("datasets", {}).pop("crop-portfolio-markov.json", None)
    manifest.setdefault("datasets", {})[output.name] = {
        "origem": "IBGE PAM/SIDRA tabela 5457; derivado de pam-history.json",
        "responsavel": "Field Shift derivação; build_crop_transition_markov.py",
        "frequencia": f"anual; top {top_crop_limit} culturas por município-ano e pares consecutivos",
        "unidade": f"massa de transição esperada fracionária, formada pelo produto das participações da área top-{top_crop_limit}; pares rank 1 inteiros mantidos como diagnóstico; prior alpha={alpha_per_destination:g} por destino elegível",
        "periodo": f"{payload['period'][0]}–{payload['period'][1]}" if payload["period"] else "sem dados",
        "resolucao": "município IBGE; não identifica pixel ou talhão",
        "qualidade": "áreas colhidas PAM observadas; transições top-5 são pseudo-observações marginais com independência assumida; pares rank 1 são diagnósticos, não transições de talhão",
        "sha256": sha256(output.read_bytes()).hexdigest(),
        "contract_id": "crop_transition_markov",
    }
    manifest["contract_version"] = current_contract_version()
    manifest["contract_registry"] = "data/contracts/registry.json"
    validate_contract("profile_manifest", manifest, source=f"{profile_dir.name}/manifest.json")
    write_json(manifest_path, manifest)
    return payload


def main() -> None:
    water_parameters = read_json(ROOT / "data" / "reference" / "crop-water-parameters.json")
    soil_hypotheses = read_json(ROOT / "data" / "reference" / "soil-crop-response-hypotheses.json")
    alpha_per_destination = float(soil_hypotheses["probability_modifiers"]["rotation_prior_alpha_per_destination"])
    lifecycle_rules = soil_hypotheses.get("crop_lifecycle_rules", {})
    for profile_dir in sorted(PROFILE_ROOT.iterdir()):
        if profile_dir.is_dir() and (profile_dir / "pam-history.json").exists():
            payload = build_profile(profile_dir, water_parameters, alpha_per_destination, lifecycle_rules)
            print(
                f"{payload['source']['municipality_ibge_code']}: "
                f"{payload['annual_observation_count']} anos, "
                f"{payload['adjacent_year_transition_count']} pares anuais, "
                f"{len(payload['states'])} culturas no catálogo"
            )


if __name__ == "__main__":
    main()
