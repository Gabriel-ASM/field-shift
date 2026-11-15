"""Inputs of the simulation, assembled from the data files of one profile.

The same payload feeds the offline page (field_shift.front) and the engines, so both read one source.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import DATA as DATA_ROOT
from ..ingest import build_chain, build_profile


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
                "from": row["state"],
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



def profile_payload(profile_id: str) -> dict:
    """Chain, calendar, water model, soil, climate and economics of one profile."""
    profile_dir = DATA_ROOT / "profiles" / profile_id
    soil = read_json(profile_dir / "soil-profile.json")
    climate_summary = read_json(profile_dir / "climate-summary.json")
    crop_markov = read_json(profile_dir / "crop-transition-markov.json")
    zarc_planting_windows = read_json(profile_dir / "zarc-planting-windows.json")
    chain, _ = build_chain(profile_id)
    profile = build_profile(profile_id, chain["initial_state"])
    node = profile["initial_node"]
    crop_ids = {state["id"]: state["crop"] for state in chain["states"] if state["crop"] != "fallow"}
    crops = set(crop_ids.values())
    history = chain["pam_history"]
    initial_crops = [crop for crop in crop_markov["initial_crop_ids"] if crop in crops]
    # The browser groups v2 states by crop for its one-node-per-crop UI.
    # Keep v1 sources for display metadata, calendar and the climate calibration.
    crop_view = {
        **{key: crop_markov[key] for key in ("annual_observation_count", "adjacent_year_transition_count",
                                            "area_weighted_transition_pair_count")},
        **history,
        "alpha_per_destination": chain["alpha_per_destination"],
        "states": [{**state, "initial_selectable": state["id"] in initial_crops}
                   for state in crop_markov["states"] if state["id"] in crops],
        "initial_crop_ids": initial_crops,
        "sugarcane_reform_pam_mass": {
            edge["to_state"]: edge["area_weighted_count"]
            for edge in crop_markov["transitions"]
            if edge["from_state"] == "sugarcane" and edge["to_state"] in crops
        },
        "lifecycle_rules": {crop: rule for crop, rule in crop_markov["lifecycle_rules"].items() if crop in crops},
        "transitions": [
            {**edge, "from": crop_ids[edge["from"]], "to": crop_ids[edge["to"]]}
            for edge in chain["transitions"]
        ],
    }
    water = water_markov(profile_dir)
    water["initial_storage_fraction"] = node["soil"]["available_water_fraction"]
    economics = profile["economics"]
    crop_economics = {
        **economics,
        "crop_inputs": {crop: entry for crop, entry in economics["crop_inputs"].items() if crop in crops},
        "economically_supported_crop_ids": [crop for crop in economics["economically_supported_crop_ids"] if crop in crops],
        "economic_exclusions": [crop for crop in economics["economic_exclusions"] if crop in crops],
    }

    return {
        "location": {
            "municipality": profile["municipality"]["name"],
            "uf": profile["municipality"]["uf"],
            "ibge_code": profile["municipality"]["ibge_code"],
        },
        "soil": {
            "organic_carbon_top_0_30_g_kg": node["soil"]["organic_carbon"],
            "available_water_capacity_mm": node["soil"]["available_water_capacity"],
            "source": soil["source"],
            "scope": profile["scope"],
            "sample_point_basis": soil["sample_point"]["basis"],
        },
        "crop_markov": crop_view,
        "zarc_planting_windows": zarc_planting_windows,
        "water_markov": water,
        "water_classes": profile["water_classes"],
        "climate_summary": climate_summary,
        "economics": crop_economics,
    }

def reference_payload() -> dict:
    """Assumptions shared by every profile: soil response, crop clock and run settings."""
    reference = DATA_ROOT / "reference"
    return {
        "soil_hypotheses": read_json(reference / "soil-crop-response-hypotheses.json"),
        "crop_cycles": read_json(reference / "crop-cycle-assumptions.json"),
        "run_settings": read_json(reference / "visualization-run-settings.json"),
    }
