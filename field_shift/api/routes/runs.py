"""Simulation runs: post a Monte Carlo request, get every scenario summarized."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body, HTTPException, Query, Request

from ...contracts import validate
from ...db import find_one
from ...engines.run import MAX_TRACKS, RunError, run

router = APIRouter(prefix="/runs", tags=["runs"])


def _chain(request: Request, profile_id: str) -> dict[str, Any]:
    chain = find_one(request.app.state.database, "chains", profile_id)
    if chain is None:
        raise HTTPException(404, f"No chain for profile {profile_id!r}")
    return chain


@router.post("")
def create_run(
    request: Request,
    body: dict[str, Any] = Body(..., description="A monte_carlo document (contract v2) without 'chain'; the stored chain of the profile is used."),
    device: Literal["auto", "gpu", "cpu"] = Query("auto"),
    tracks: int = Query(0, ge=0, le=MAX_TRACKS, description="Trajectories returned period by period, for animation."),
) -> dict[str, Any]:
    chain = _chain(request, str(body.get("profile")))
    errors = validate("monte_carlo", {**body, "chain": chain})
    if errors:
        raise HTTPException(422, errors)
    try:
        return run(body, chain["initial_state"], device, tracks)
    except (RunError, RuntimeError) as error:
        raise HTTPException(422, str(error)) from error
