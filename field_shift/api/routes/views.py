"""Views of the contracts for the web: link graph and inlined tree."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ...views import contract_graph, contract_tree

router = APIRouter(prefix="/views", tags=["views"])


@router.get("/graph")
def graph() -> dict[str, Any]:
    """Contracts as nodes; $ref, id and JSON Pointer links as edges; status of every node value."""
    return contract_graph()


@router.get("/tree")
def tree() -> dict[str, Any]:
    """One tree with every $ref inlined (the file used on jsoncrack.com)."""
    return contract_tree()
