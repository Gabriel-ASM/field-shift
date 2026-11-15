"""Read and write contract-validated documents.

Every write is validated twice: here, against the JSON Schema contract and its cross-reference
checks (clear messages), and by the collection's MongoDB validator (protects against writers
that bypass this module).
"""

from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.database import Database

from ..contracts import check, contract_names, schema, validate
from ..contracts.registry import VERSION
from .collections import COLLECTIONS, validator_for


class InvalidDocument(ValueError):
    """A document violates its contract. `errors` lists every violation."""

    def __init__(self, collection: str, errors: list[str]):
        super().__init__(f"Invalid document for {collection!r}: " + "; ".join(errors[:5]))
        self.collection = collection
        self.errors = errors


def connect(uri: str, database: str = "field_shift") -> Database:
    return MongoClient(uri, serverSelectionTimeoutMS=5000)[database]


def ensure_collections(database: Database) -> None:
    """Create each collection with its validator and unique key index, or update the validator."""
    existing = set(database.list_collection_names())
    for spec in COLLECTIONS.values():
        options = {"validator": validator_for(spec.name), "validationLevel": "strict", "validationAction": "error"}
        if spec.name in existing:
            database.command("collMod", spec.name, **options)
        else:
            database.create_collection(spec.name, **options)
        database[spec.name].create_index([(spec.key, ASCENDING)], unique=True)
    sync_contracts(database)


def sync_contracts(database: Database) -> None:
    """Store the contracts themselves, so other services can read the schemas from the database."""
    database["contracts"].create_index([("name", ASCENDING), ("version", ASCENDING)], unique=True)
    for name in contract_names():
        # "$"-prefixed keys cannot be top-level field names in an update, so the schema is nested.
        document = {"name": name, "version": VERSION, "schema": _escape(schema(name))}
        database["contracts"].replace_one({"name": name, "version": VERSION}, document, upsert=True)


def _escape(value: Any) -> Any:
    """MongoDB treats a leading '$' in field names specially, so '$ref' is stored as '_$ref'."""
    if isinstance(value, dict):
        return {(f"_{key}" if key.startswith("$") else key): _escape(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_escape(item) for item in value]
    return value


def upsert(database: Database, collection: str, document: dict[str, Any]) -> None:
    spec = COLLECTIONS[collection]
    errors = validate(spec.contract, document) or check(spec.contract, document)
    if errors:
        raise InvalidDocument(collection, errors)
    database[collection].replace_one({spec.key: document[spec.key]}, document, upsert=True)


def find_one(database: Database, collection: str, key: str) -> dict[str, Any] | None:
    return database[collection].find_one({COLLECTIONS[collection].key: key}, {"_id": 0})


def list_documents(database: Database, collection: str, fields: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    projection = {"_id": 0, **{field: 1 for field in fields}}
    return list(database[collection].find({}, projection).sort(COLLECTIONS[collection].key, ASCENDING))
