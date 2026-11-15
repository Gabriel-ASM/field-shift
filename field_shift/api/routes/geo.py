"""Boundaries for the map: Brazilian states and the municipality of each profile (GeoJSON from IBGE)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from ...ingest.geo import GEO

router = APIRouter(prefix="/geo", tags=["geo"])


def _read(name: str) -> dict[str, Any]:
    path = GEO / f"{name}.geojson"
    if not path.is_file():
        raise HTTPException(404, f"No boundary stored for {name!r}; run python -m field_shift.ingest.geo")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/states")
def states() -> dict[str, Any]:
    return _read("brazil-states")


@router.get("/profiles/{profile_id}")
def municipality(profile_id: str) -> dict[str, Any]:
    if not profile_id.replace("-", "").isalnum():
        raise HTTPException(404, "Unknown profile")
    return _read(f"municipalities/{profile_id}")
