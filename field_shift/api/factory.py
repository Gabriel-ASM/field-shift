"""Application factory."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pymongo.database import Database

from .. import ROOT
from ..db import connect
from .routes import chains, contracts, profiles, views

DESCRIPTION = """
Backend of Field Shift. This phase exposes the data contracts (v2), their views, and the
profiles and Markov chains generated from the current data. Simulation runs come with the engines.
"""


def create_app(database: Database | None = None) -> FastAPI:
    """Build the app. Without `database`, connect using FIELD_SHIFT_MONGO_URI and FIELD_SHIFT_DB.

    The front is served from `web/` (or FIELD_SHIFT_WEB_DIR) at `/`, and the generated HTML pages in `docs/` at `/pages`.
    """
    app = FastAPI(title="Field Shift API", version="0.2.0", description=DESCRIPTION)
    app.state.database = database if database is not None else connect(
        os.environ.get("FIELD_SHIFT_MONGO_URI", "mongodb://localhost:27017"),
        os.environ.get("FIELD_SHIFT_DB", "field_shift"),
    )

    # The v1 demo page is 2.5 MB of inline JSON; compressed it is about 130 kB.
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.get("/health", tags=["service"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for module in (contracts, views, profiles, chains):
        app.include_router(module.router)

    # Static mounts come last, so every API route above wins over a file with the same path.
    pages = ROOT / "docs"
    if pages.is_dir():
        app.mount("/pages", StaticFiles(directory=pages), name="pages")
    web = Path(os.environ.get("FIELD_SHIFT_WEB_DIR", ROOT / "web"))
    if web.is_dir():
        app.mount("/", StaticFiles(directory=web, html=True), name="web")
    return app
