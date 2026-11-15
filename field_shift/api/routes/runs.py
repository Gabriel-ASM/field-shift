"""Simulation runs: post a Monte Carlo request, get every scenario summarized."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

from ...contracts import validate
from ...db import find_one
from ...engines.run import MAX_TRACKS, RunError, options, prepare, run, tables_for
from ...engines.summary import route_detail
from ..jobs import Jobs
from ..version import same_version

router = APIRouter(prefix="/runs", tags=["runs"], dependencies=[Depends(same_version)])
jobs = Jobs()


def _chain(request: Request, profile_id: str) -> dict[str, Any]:
    chain = find_one(request.app.state.database, "chains", profile_id)
    if chain is None:
        raise HTTPException(404, f"No chain for profile {profile_id!r}")
    return chain


@router.get("/options/{profile_id}")
def run_options(profile_id: str, request: Request) -> dict[str, Any]:
    """Crops of the profile, and the ones a simulation may start from."""
    _chain(request, profile_id)
    return options(profile_id)


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


def _checked(request: Request, body: dict[str, Any]) -> str:
    """Validate a run body against the contract and the engine; returns the chain's initial state."""
    chain = _chain(request, str(body.get("profile")))
    errors = validate("monte_carlo", {**body, "chain": chain})
    if errors:
        raise HTTPException(422, errors)
    try:
        prepare(body, chain["initial_state"])
    except RunError as error:
        raise HTTPException(422, str(error)) from error
    return chain["initial_state"]


@router.post("/jobs", status_code=202)
def start_job(
    request: Request,
    body: dict[str, Any] = Body(..., description="Same body as POST /runs."),
    device: Literal["auto", "gpu", "cpu"] = Query("auto"),
    tracks: int = Query(0, ge=0, le=MAX_TRACKS),
) -> dict[str, Any]:
    """Start a run in the background. Poll GET /runs/jobs/{id}: `done` counts finished trajectories; when `status`
    is done, `result` is what POST /runs returns for the same body."""
    default_state = _checked(request, body)
    job = jobs.start(body, default_state, device, tracks)
    return {"id": job.id, "total": job.total}


def _job(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, f"No job {job_id!r} (finished jobs are kept for a while only)")
    return job


@router.get("/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, Any]:
    return _job(job_id).view()


@router.get("/jobs/{job_id}/route")
def job_route(job_id: str, crops: str = Query(..., description="Comma-separated crops of the route, as in its summary."),
              scenario: int = Query(0, ge=0)) -> dict[str, Any]:
    """Water and soil every period, year-end charts and some trajectories of one route of a finished job."""
    job = _job(job_id)
    if job.status != "done":
        raise HTTPException(409, f"Job {job_id!r} is {job.status}")
    if scenario >= len(job.raw):
        raise HTTPException(404, f"No scenario {scenario}")
    detail = route_detail(job.raw[scenario], tables_for(job.profile), crops.split(","))
    if detail is None:
        raise HTTPException(404, f"No trajectory followed {crops!r}")
    return detail
