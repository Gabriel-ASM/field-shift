"""Load the v2 contracts and validate documents against them (Draft-07, cross-file $ref)."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

from .. import DATA

V2_DIR = DATA / "contracts" / "v2"
BASE_URI = "https://fieldshift.local/contracts/v2/"
VERSION = "v2"


@lru_cache(maxsize=1)
def load_schemas() -> dict[str, dict[str, Any]]:
    """Contract name -> schema. A contract is a JSON object with "$schema"; other files are ignored."""
    schemas = {}
    for path in sorted(V2_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "$schema" in data:
            Draft7Validator.check_schema(data)
            schemas[path.stem] = data
    return schemas


def contract_names() -> list[str]:
    return sorted(load_schemas())


def schema(name: str) -> dict[str, Any]:
    try:
        return load_schemas()[name]
    except KeyError:
        raise KeyError(f"Unknown contract {name!r}; available: {', '.join(contract_names())}") from None


@lru_cache(maxsize=1)
def _registry() -> Registry:
    resources = []
    for name, data in load_schemas().items():
        resource = Resource.from_contents(data, default_specification=DRAFT7)
        # Registered under the v2 URI and the bare filename, so relative refs resolve either way.
        resources += [(f"{BASE_URI}{name}.json", resource), (f"{name}.json", resource)]
    return Registry().with_resources(resources)


@lru_cache(maxsize=64)
def _validator(name: str, fragment: str) -> Draft7Validator:
    schema(name)  # raises on unknown names
    target = {"$ref": f"{BASE_URI}{name}.json{fragment}"}
    return Draft7Validator(target, registry=_registry())


def validate(name: str, document: Any, *, fragment: str = "") -> list[str]:
    """Return schema errors as '/path: message' strings; an empty list means the document is valid.

    `fragment` selects a definition inside the contract, e.g. '#/definitions/node'.
    """
    errors = sorted(_validator(name, fragment).iter_errors(document), key=lambda e: [str(p) for p in e.absolute_path])
    return [f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}" for error in errors]
