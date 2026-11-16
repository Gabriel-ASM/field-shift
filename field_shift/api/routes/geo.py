"""Boundaries and places for the map: Brazilian states, the municipality of each profile, and (experimental) a
search over every Brazilian municipality with its IBGE boundary, all from files written by the geo ingest."""

from __future__ import annotations

import gzip
import json
import unicodedata
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response

from ...ingest.geo import ALL_BOUNDARIES, GEO

router = APIRouter(prefix="/geo", tags=["geo"])

SEARCH_LIMIT = 12


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
    if (GEO / f"municipalities/{profile_id}.geojson").is_file():
        return _read(f"municipalities/{profile_id}")
    # A profile beyond the examples has no file of its own: its boundary is in the file of every municipality.
    catalog = json.loads((GEO.parent / "catalog" / "perfis-exemplo.json").read_text(encoding="utf-8"))
    code = next((str(entry["ibge_code"]) for entry in catalog["profiles"] if entry["profile"] == profile_id), None)
    body = _boundaries().get(code) if code else None
    if body is None:
        raise HTTPException(404, f"No boundary stored for {profile_id!r}; run python -m field_shift.ingest.geo")
    return json.loads(body)


def folded(text: str) -> str:
    """Lower case without accents, so "sao" finds "São"."""
    return "".join(c for c in unicodedata.normalize("NFD", text.casefold()) if unicodedata.category(c) != "Mn")


@lru_cache(maxsize=1)
def _municipalities() -> tuple[tuple[str, dict[str, str]], ...]:
    path = GEO / "municipalities.json"
    if not path.is_file():
        raise HTTPException(503, "The municipality list is not stored; run python -m field_shift.ingest.geo")
    rows = json.loads(path.read_text(encoding="utf-8"))["municipalities"]
    return tuple((folded(row["name"]), row) for row in rows)


def search(query: str, limit: int) -> list[dict[str, str]]:
    """Municipalities whose name starts with the query first, then those that contain it."""
    wanted = folded(query.strip())
    if not wanted:
        return []
    rows = _municipalities()
    starts = [row for name, row in rows if name.startswith(wanted)]
    inside = [row for name, row in rows if wanted in name and not name.startswith(wanted)]
    return (starts + inside)[:limit]


@router.get("/municipalities")
def municipalities(q: str = Query("", max_length=60), limit: int = Query(SEARCH_LIMIT, ge=1, le=50)) -> list[dict[str, str]]:
    """Experimental: every Brazilian municipality (IBGE localidades), searched by name."""
    return search(q, limit)


@lru_cache(maxsize=1)
def _boundaries() -> dict[str, bytes]:
    """IBGE code -> GeoJSON of that municipality, ready to send (about 12 MB in memory for 5,570)."""
    if not ALL_BOUNDARIES.is_file():
        raise HTTPException(503, "The municipal boundaries are not stored; run python -m field_shift.ingest.geo")
    document = json.loads(gzip.decompress(ALL_BOUNDARIES.read_bytes()))
    return {str(feature["properties"]["codarea"]): json.dumps(
                {"type": "FeatureCollection", "features": [feature], "source": document["source"]},
                separators=(",", ":")).encode("utf-8")
            for feature in document["features"]}


@router.get("/municipalities/{code}")
def boundary(code: str) -> Response:
    """Experimental: the IBGE boundary of any municipality."""
    body = _boundaries().get(code)
    if body is None:
        listed = any(row["code"] == code for _, row in _municipalities())
        raise HTTPException(404, "IBGE has no boundary for this municipality yet" if listed else f"Unknown municipality {code!r}")
    return Response(body, media_type="application/json")
