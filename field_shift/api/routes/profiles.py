"""Profiles: the places a simulation can run for."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ...db import find_one, list_documents

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("")
def list_profiles(request: Request) -> list[dict[str, Any]]:
    return list_documents(request.app.state.database, "profiles", ("id", "label", "municipality", "scope"))


@router.get("/{profile_id}")
def get_profile(profile_id: str, request: Request) -> dict[str, Any]:
    document = find_one(request.app.state.database, "profiles", profile_id)
    if document is None:
        raise HTTPException(404, f"Unknown profile {profile_id!r}")
    return document
