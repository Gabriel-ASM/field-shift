"""Build identity: the commit the image was built from, so a front bundle can tell it is out of date.

The image sets FIELD_SHIFT_VERSION at build time; without it (tests, a local uvicorn) the version is "dev",
which matches any client."""

from __future__ import annotations

import os

from fastapi import HTTPException, Request

DEV = "dev"
HEADER = "X-Field-Shift-Version"


def server_version() -> str:
    return os.environ.get("FIELD_SHIFT_VERSION") or DEV


def mismatch(client: str | None, server: str) -> bool:
    """Only two known builds can disagree: a missing or dev version on either side always matches."""
    return bool(client) and client != DEV and server != DEV and client != server


def same_version(request: Request) -> None:
    """Dependency of the run routes: refuse a front built from another commit than this API."""
    client, server = request.headers.get(HEADER), server_version()
    if mismatch(client, server):
        raise HTTPException(409, f"The page was built for Field Shift {client}, the server runs {server}; reload the page.",
                            headers={HEADER: server})
