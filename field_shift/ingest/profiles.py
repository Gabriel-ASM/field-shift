"""v1 profile files -> v2 profile document with the initial trajectory node."""

from __future__ import annotations

import csv
import json
from typing import Any

from .. import DATA

TOPSOIL_CM = 30
INITIAL_WATER_FRACTION = 0.5


def _read(path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def profile_ids() -> list[str]:
    return [entry["profile"] for entry in _read(DATA / "catalog" / "perfis-exemplo.json")["profiles"]]


def topsoil_mean(layers: list[dict[str, Any]], field: str, depth_cm: float = TOPSOIL_CM) -> float:
    """Thickness-weighted mean of a layer property from the surface down to depth_cm."""
    weighted = covered = 0.0
    for layer in sorted(layers, key=lambda item: item["depth_top_cm"]):
        thickness = min(layer["depth_bottom_cm"], depth_cm) - layer["depth_top_cm"]
        if thickness <= 0:
            continue
        weighted += layer[field] * thickness
        covered += thickness
    if covered != depth_cm:
        raise ValueError(f"Soil layers cover {covered} cm, expected {depth_cm} cm")
    return weighted / covered


def _climate_period(path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        days = [row["date_local"] for row in csv.DictReader(stream)]
    return [days[0], days[-1]]


def build_profile(profile: str, initial_state: str) -> dict[str, Any]:
    """Build the profile document. initial_state comes from the profile's chain."""
    entry = next(item for item in _read(DATA / "catalog" / "perfis-exemplo.json")["profiles"] if item["profile"] == profile)
    directory = DATA / "profiles" / profile
    soil = _read(directory / "soil-profile.json")
    relative = directory.relative_to(DATA.parent).as_posix()
    soil_source = f"{soil['source']} ({relative}/soil-profile.json)"
    point = soil["sample_point"]
    node = {
        "state": initial_state,
        "day": 0,
        "soil": {
            "pH": round(topsoil_mean(soil["layers"], "ph_water"), 3),
            "organic_carbon": round(topsoil_mean(soil["layers"], "organic_carbon_g_kg"), 3),
            "N2": round(soil["total_nitrogen_stock_top_0_30_kg_ha"], 2),
            "available_water_capacity": round(soil["available_water_capacity_mm"], 2),
            "available_water_fraction": INITIAL_WATER_FRACTION,
        },
        "climate": {"lat": round(point["latitude"], 5), "long": round(point["longitude"], 5)},
    }
    values = [
        {"pointer": "/soil/pH", "support": "derived", "provenance": f"0-{TOPSOIL_CM} cm thickness-weighted mean of ph_water; {soil_source}"},
        {"pointer": "/soil/organic_carbon", "support": "derived", "provenance": f"0-{TOPSOIL_CM} cm thickness-weighted mean of organic_carbon_g_kg; {soil_source}"},
        {"pointer": "/soil/N2", "support": "derived", "provenance": f"SoilGrids total nitrogen in 0-{TOPSOIL_CM} cm × SoilGrids bulk density × layer thickness; stock in kg N/ha. Total N is not mineral/available N; {soil_source}"},
        {"pointer": "/soil/available_water_capacity", "support": "derived", "provenance": f"available_water_capacity_mm down to {soil['depth_cm']} cm; {soil_source}"},
        {"pointer": "/soil/available_water_fraction", "support": "prior", "provenance": "No measured soil moisture; v1 starts every trajectory at medium water"},
        {"pointer": "/climate/lat", "support": "derived", "provenance": point["basis"]},
        {"pointer": "/climate/long", "support": "derived", "provenance": point["basis"]},
    ]
    benchmarks = _read(DATA / "reference" / "economic-benchmarks.json")
    thresholds = _read(DATA / "reference" / "soil-crop-response-hypotheses.json")["soil_carbon"]["water_state_bin_thresholds_fraction"]
    climate_file = directory / "climate-daily.csv"
    return {
        "id": profile,
        "label": f"{entry['municipality']}, {entry['uf']}",
        "municipality": {"name": entry["municipality"], "uf": entry["uf"], "ibge_code": str(entry["ibge_code"])},
        "scope": soil["scope"],
        "initial_node": node,
        "values": values,
        "economics": {
            **benchmarks["profiles"][profile],
            "discount_rate": benchmarks["discount_rate"],
            "reference_currency_month": benchmarks["reference_currency_month"],
        },
        "water_classes": {
            "low_max_inclusive": thresholds["water_low_max_inclusive"],
            "medium_max_inclusive": thresholds["water_medium_max_inclusive"],
            "provenance": "Exploratory thirds of available water capacity; not crop-specific stress thresholds.",
        },
        "climate_history": {
            "file": climate_file.relative_to(DATA.parent).as_posix(),
            "period": _climate_period(climate_file),
            "source": "NASA POWER Daily API (see the 'source' column of the file)",
        },
    }
