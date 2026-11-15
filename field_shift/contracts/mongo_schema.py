"""Translate a bundled Draft-07 contract into a MongoDB $jsonSchema validator.

MongoDB implements a subset of draft 4 and rejects unknown keywords, so the translation is a
whitelist: anything not listed here is dropped. Dropped keywords that carry meaning for people
('unit') are appended to the description.
"""

from __future__ import annotations

from typing import Any

BSON_TYPES = {
    "string": ["string"], "boolean": ["bool"], "object": ["object"], "array": ["array"], "null": ["null"],
    "integer": ["int", "long"],
    "number": ["double", "int", "long", "decimal"],
}
PASS_THROUGH = {
    "required", "enum", "minimum", "maximum", "minLength", "maxLength", "pattern",
    "minItems", "maxItems", "uniqueItems", "minProperties", "maxProperties", "title",
}
SCHEMA_VALUED = {"items", "additionalProperties", "not"}
SCHEMA_LISTS = {"oneOf", "anyOf", "allOf"}
# Draft-07 keywords with no MongoDB equivalent. The application-level validation still enforces them.
NOT_ENFORCED = {"propertyNames", "format", "if", "then", "else", "contains", "dependencies"}


def _bson_types(json_type: str | list[str]) -> str | list[str]:
    names = [json_type] if isinstance(json_type, str) else json_type
    types = [bson for name in names for bson in BSON_TYPES[name]]
    return types[0] if len(types) == 1 else types


def to_mongo(schema: Any, *, root: bool = True) -> Any:
    """Convert a bundled contract. With root=True, '_id' is allowed even under additionalProperties: false."""
    if isinstance(schema, bool):
        return schema
    out: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "type":
            out["bsonType"] = _bson_types(value)
        elif key == "const":
            out["enum"] = [value]
        elif key == "properties":
            out["properties"] = {name: to_mongo(sub, root=False) for name, sub in value.items()}
        elif key in SCHEMA_VALUED:
            out[key] = to_mongo(value, root=False)
        elif key in SCHEMA_LISTS:
            out[key] = [to_mongo(sub, root=False) for sub in value]
        elif key in PASS_THROUGH:
            out[key] = value
    description = schema.get("description", "")
    if schema.get("unit"):
        description = f"{description} [{schema['unit']}]".strip()
    if description:
        out["description"] = description
    if root and out.get("additionalProperties") is False:
        out.setdefault("properties", {})["_id"] = {}
    return out


def unenforced_keywords(schema: Any, path: str = "") -> list[str]:
    """Locations of contract rules the MongoDB validator cannot express (for the audit report)."""
    found = []
    if isinstance(schema, dict):
        found += [f"{path}/{key}" for key in schema if key in NOT_ENFORCED]
        for key, value in schema.items():
            found += unenforced_keywords(value, f"{path}/{key}")
    elif isinstance(schema, list):
        for index, value in enumerate(schema):
            found += unenforced_keywords(value, f"{path}/{index}")
    return found
