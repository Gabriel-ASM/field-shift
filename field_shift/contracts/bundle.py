"""Inline every $ref of a contract, so one self-contained schema can be served or translated."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from .registry import load_schemas, schema

DROPPED = {"definitions", "$id", "$schema"}


def split_ref(ref: str, current: str) -> tuple[str, str]:
    """'effect.json#/definitions/quantity' -> ('effect', '/definitions/quantity')."""
    file_part, _, fragment = ref.partition("#")
    return (PurePosixPath(file_part).stem if file_part else current), fragment


def resolve(contract: str, fragment: str) -> dict[str, Any]:
    node: Any = load_schemas()[contract]
    for part in (p for p in fragment.split("/") if p):
        node = node[part]
    return node


def _inline(node: Any, contract: str, trail: tuple[str, ...]) -> Any:
    if isinstance(node, list):
        return [_inline(item, contract, trail) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        target, fragment = split_ref(node["$ref"], contract)
        key = f"{target}#{fragment}"
        if key in trail:
            raise ValueError(f"Recursive $ref cannot be bundled: {' -> '.join((*trail, key))}")
        resolved = _inline(resolve(target, fragment), target, (*trail, key))
        # Siblings of $ref (e.g. a field-specific description) override the referenced schema.
        siblings = {k: _inline(v, contract, trail) for k, v in node.items() if k != "$ref"}
        return {**resolved, **siblings}
    return {key: _inline(value, contract, trail) for key, value in node.items() if key not in DROPPED}


def bundle(name: str, *, fragment: str = "") -> dict[str, Any]:
    """The contract (or one of its definitions) with all references inlined and no definitions block."""
    schema(name)
    return _inline(resolve(name, fragment.lstrip("#")), name, (f"{name}#{fragment.lstrip('#')}",))
