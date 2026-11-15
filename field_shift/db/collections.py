"""Which contract validates which collection, and the field that identifies a document."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..contracts import bundle, to_mongo


@dataclass(frozen=True)
class CollectionSpec:
    name: str
    contract: str
    key: str


COLLECTIONS: dict[str, CollectionSpec] = {
    spec.name: spec
    for spec in (
        CollectionSpec("profiles", "profile", "id"),
        CollectionSpec("chains", "markov", "id"),
        CollectionSpec("crops", "crop", "name"),
        CollectionSpec("actions", "action", "id"),
        CollectionSpec("events", "event", "id"),
    )
}


def validator_for(collection: str) -> dict[str, Any]:
    """The MongoDB validator document for a collection, generated from its contract."""
    return {"$jsonSchema": to_mongo(bundle(COLLECTIONS[collection].contract))}
