"""Contracts: the schemas, their MongoDB validators, and document validation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from ...contracts import bundle, check, contract_names, schema, to_mongo, validate
from ...contracts.mongo_schema import unenforced_keywords
from ...contracts.registry import VERSION

router = APIRouter(tags=["contracts"])


def _known(name: str) -> str:
    if name not in contract_names():
        raise HTTPException(404, f"Unknown contract {name!r}. Available: {', '.join(contract_names())}")
    return name


@router.get("/contracts")
def list_contracts() -> list[dict[str, str]]:
    return [{"name": name, "title": schema(name).get("title", name), "version": VERSION} for name in contract_names()]


@router.get("/contracts/{name}")
def get_contract(name: str, bundled: bool = Query(True, description="Inline every $ref into one self-contained schema")) -> dict[str, Any]:
    return bundle(_known(name)) if bundled else schema(_known(name))


@router.get("/contracts/{name}/mongo")
def get_mongo_validator(name: str) -> dict[str, Any]:
    bundled = bundle(_known(name))
    return {"validator": {"$jsonSchema": to_mongo(bundled)}, "not_enforced_by_mongodb": unenforced_keywords(bundled)}


@router.post("/validate/{name}")
def validate_document(
    name: str,
    document: Any = Body(...),
    fragment: str = Query("", description="Validate against one definition, e.g. #/definitions/node"),
) -> dict[str, Any]:
    """Schema errors first; cross-reference checks (ids, probabilities) run only on schema-valid documents."""
    try:
        errors = validate(_known(name), document, fragment=fragment)
    except Exception as error:  # an unknown fragment surfaces as a resolution error
        raise HTTPException(400, f"Cannot validate against {name}{fragment}: {error}") from error
    if not errors and not fragment:
        errors = check(name, document)
    return {"valid": not errors, "errors": errors}
