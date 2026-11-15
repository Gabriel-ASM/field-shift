"""Boundaries and places for the map: Brazilian states, the municipality of each profile, and (experimental) a
search over every Brazilian municipality with its boundary fetched live from IBGE."""

from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ...ingest.geo import GEO, MUNICIPALITY_URL, fetch_geojson

router = APIRouter(prefix="/geo", tags=["geo"])

SEARCH_LIMIT = 12
BOUNDARY_TIMEOUT = 20       # seconds; the IBGE API is usually well under one


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


@lru_cache(maxsize=256)
def _boundary(code: str) -> str:
    return json.dumps(fetch_geojson(MUNICIPALITY_URL.format(code=code), BOUNDARY_TIMEOUT))


@router.get("/municipalities/{code}")
def boundary(code: str) -> dict[str, Any]:
    """Experimental: the boundary of any municipality, fetched live from the IBGE malhas API and kept in memory."""
    if not (code.isdigit() and len(code) == 7) or code not in {row["code"] for _, row in _municipalities()}:
        raise HTTPException(404, f"Unknown municipality {code!r}")
    try:
        return json.loads(_boundary(code))
    except (OSError, ValueError) as failure:
        raise HTTPException(502, f"IBGE did not return the boundary of {code}: {failure}") from failure
