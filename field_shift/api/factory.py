"""Application factory."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pymongo.database import Database
from starlette.responses import Response
from starlette.types import Scope

from .. import ROOT
from ..db import connect
from .routes import chains, config, contracts, geo, profiles, reference, runs, views

DESCRIPTION = """
Backend of Field Shift. This phase exposes the data contracts (v2), their views, and the
profiles and Markov chains generated from the current data, and Monte Carlo runs (POST /runs).
"""


class Front(StaticFiles):
    """The built front. Vite names everything under assets/ by its content hash, so those files never change;
    the rest (index.html above all) is revalidated on every load, so a redeploy reaches open tabs on reload."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        hashed = path.startswith("assets/")
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable" if hashed else "no-cache"
        return response


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

    for module in (config, contracts, views, profiles, chains, runs, geo):
        app.include_router(module.router)

    reference.install(app)

    # Static mounts come last, so every API route above wins over a file with the same path.
    pages = ROOT / "docs"
    if pages.is_dir():
        app.mount("/pages", StaticFiles(directory=pages), name="pages")
    web = Path(os.environ.get("FIELD_SHIFT_WEB_DIR", ROOT / "web"))
    if web.is_dir():
        app.mount("/", Front(directory=web, html=True), name="web")
    return app
