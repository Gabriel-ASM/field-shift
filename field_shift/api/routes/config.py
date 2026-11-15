"""Runtime configuration of the front. The deployment sets it through environment variables;
the front reads it from here at start-up, so one build runs anywhere."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter

from ..version import server_version

router = APIRouter(tags=["service"])

GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg"


def _env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(f"FIELD_SHIFT_{name}") or default


@router.get("/config")
def runtime_config() -> dict[str, Any]:
    return {
        "version": server_version(),
        "basemap": {
            "tiles": _env("BASEMAP_TILES", GIBS),
            "max_zoom": int(_env("BASEMAP_MAX_ZOOM", "8")),
            "attribution": _env("BASEMAP_ATTRIBUTION", "NASA EOSDIS GIBS, Blue Marble"),
        },
        "cms": {"url": _env("CMS_URL"), "token": _env("CMS_PUBLIC_TOKEN")},
        "run": {"trajectories": int(_env("RUN_TRAJECTORIES", "100000")), "tracks": int(_env("RUN_TRACKS", "40"))},
    }
