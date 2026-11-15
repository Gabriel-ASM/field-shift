"""Application factory."""

from __future__ import annotations

import os

from fastapi import FastAPI
from pymongo.database import Database

from ..db import connect
from .routes import chains, contracts, profiles, views

DESCRIPTION = """
Backend of Field Shift. This phase exposes the data contracts (v2), their views, and the
profiles and Markov chains generated from the current data. Simulation runs come with the engines.
"""


def create_app(database: Database | None = None) -> FastAPI:
    """Build the app. Without `database`, connect using FIELD_SHIFT_MONGO_URI and FIELD_SHIFT_DB."""
    app = FastAPI(title="Field Shift API", version="0.2.0", description=DESCRIPTION)
    app.state.database = database if database is not None else connect(
        os.environ.get("FIELD_SHIFT_MONGO_URI", "mongodb://localhost:27017"),
        os.environ.get("FIELD_SHIFT_DB", "field_shift"),
    )

    @app.get("/health", tags=["service"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for module in (contracts, views, profiles, chains):
        app.include_router(module.router)
    return app
