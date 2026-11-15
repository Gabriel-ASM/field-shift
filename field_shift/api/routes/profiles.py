"""Profiles: the places a simulation can run for."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ...db import find_one, list_documents
from ...engines.calendar import lowest_risk
from ...engines.payload import DATA_ROOT, read_json, reference_payload

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("")
def list_profiles(request: Request) -> list[dict[str, Any]]:
    return list_documents(request.app.state.database, "profiles", ("id", "label", "municipality", "scope"))


@router.get("/{profile_id}")
def get_profile(profile_id: str, request: Request) -> dict[str, Any]:
    document = find_one(request.app.state.database, "profiles", profile_id)
    if document is None:
        raise HTTPException(404, f"Unknown profile {profile_id!r}")
    return document


@router.get("/{profile_id}/planting-windows")
def planting_windows(profile_id: str) -> dict[str, Any]:
    """The MAPA ZARC planting windows the engine plants in, per crop: the lowest published risk of each decendio
    (1-36, three per month), and the all-year windows the project assumes for covers without an official row."""
    path = DATA_ROOT / "profiles" / profile_id / "zarc-planting-windows.json"
    if not path.is_file():
        raise HTTPException(404, f"Unknown profile {profile_id!r}")
    zarc, cycles = read_json(path), reference_payload()["crop_cycles"]
    levels = cycles["time_basis"]["planting_calendar"]["risk_levels_included_percent"]
    crops = set(cycles["crops"])
    official = lowest_risk(zarc["rows"], crops, levels)
    fallback = cycles.get("rotation_calendar_fallback") or {}
    assumed = {crop: fallback.get("all_year_decendios", []) for crop in fallback.get("crop_ids", []) if crop not in official}
    seasons = sorted({row["season"] for row in zarc["rows"] if re.fullmatch(r"\d{4}/\d{4}", str(row.get("season")))})
    return {
        "seasons": seasons,
        "risk_levels": levels,
        "crops": {crop: {"official": True, "risk": {str(d): level for d, level in sorted(days.items())}} for crop, days in official.items()}
                 | {crop: {"official": False, "risk": {str(d): None for d in days}} for crop, days in assumed.items()},
        "source": zarc["source"],
        "assumption": fallback.get("status"),
    }
