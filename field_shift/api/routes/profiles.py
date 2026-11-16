"""Profiles: the places a simulation can run for."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ...db import find_one, list_documents
from ..builds import Builds, municipality
from ...engines.calendar import lowest_risk
from ...engines.payload import DATA_ROOT, read_json, reference_payload

router = APIRouter(prefix="/profiles", tags=["profiles"])
builds = Builds()


def experimental_ids() -> set[str]:
    """Profiles assembled by the fetchers and not reviewed (flagged in the catalog by build_profiles.py)."""
    catalog = read_json(DATA_ROOT / "catalog" / "perfis-exemplo.json")
    return {entry["profile"] for entry in catalog["profiles"] if entry.get("experimental")}


@router.get("")
def list_profiles(request: Request) -> list[dict[str, Any]]:
    experimental = experimental_ids()
    summaries = list_documents(request.app.state.database, "profiles", ("id", "label", "municipality", "scope"))
    return [{**summary, "experimental": summary["id"] in experimental} for summary in summaries]


@router.post("/builds/{code}", status_code=202)
def start_build(code: str, request: Request) -> dict[str, Any]:
    """Experimental: fetch and assemble the profile of any municipality, by IBGE code, in the background.
    Poll GET /profiles/builds/{id}: `fraction` and `stage` say how far it is; when `status` is "done" the profile
    `profile` can be read and simulated. Asking again for a municipality being assembled returns the same build."""
    target = municipality(code)
    if target is None:
        raise HTTPException(404, f"Unknown municipality {code!r}, or IBGE has no boundary for it")
    return builds.start(target, request.app.state.database).view()


@router.get("/builds/{build_id}")
def get_build(build_id: str) -> dict[str, Any]:
    build = builds.get(build_id)
    if build is None:
        raise HTTPException(404, f"No build {build_id!r}")
    return build.view()


@router.get("/{profile_id}")
def get_profile(profile_id: str, request: Request) -> dict[str, Any]:
    document = find_one(request.app.state.database, "profiles", profile_id)
    if document is None:
        raise HTTPException(404, f"Unknown profile {profile_id!r}")
    return {**document, "experimental": profile_id in experimental_ids()}


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
