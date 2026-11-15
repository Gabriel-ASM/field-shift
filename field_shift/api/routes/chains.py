"""Markov chains per profile, and their probability matrix for charts."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ...db import find_one

router = APIRouter(prefix="/profiles/{profile_id}/chain", tags=["chains"])


def _chain(request: Request, profile_id: str) -> dict[str, Any]:
    document = find_one(request.app.state.database, "chains", profile_id)
    if document is None:
        raise HTTPException(404, f"No chain for profile {profile_id!r}")
    return document


def chain_matrix(chain: dict[str, Any]) -> dict[str, Any]:
    """Row per origin state, column per destination: probability, support and evidence of each edge."""
    states = [state["id"] for state in chain["states"]]
    edges = {(edge["from"], edge["to"]): edge for edge in chain["transitions"]}
    with_edges = {origin for origin, _ in edges}
    rows = []
    for origin in states:
        cells = []
        for destination in states:
            edge = edges.get((origin, destination))
            cells.append(None if edge is None else {
                "probability": edge["probability"], "support": edge["support"],
                "mass": edge.get("mass"), "count": edge.get("count"),
            })
        outgoing = next((edge.get("outgoing_mass") for (o, _), edge in edges.items() if o == origin), None)
        rows.append({"from": origin, "has_edges": origin in with_edges, "outgoing_mass": outgoing, "cells": cells})
    return {
        "profile": chain.get("profile"), "initial_state": chain["initial_state"], "states": states, "rows": rows,
        "dead_ends": sorted({destination for _, destination in edges} - with_edges),
    }


@router.get("")
def get_chain(profile_id: str, request: Request) -> dict[str, Any]:
    return _chain(request, profile_id)


@router.get("/matrix")
def get_chain_matrix(profile_id: str, request: Request) -> dict[str, Any]:
    return chain_matrix(_chain(request, profile_id))
