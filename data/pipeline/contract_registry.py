"""Resolve and validate payloads against the active versioned data contracts."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "data" / "contracts"
REGISTRY_PATH = CONTRACT_ROOT / "registry.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def registry() -> dict[str, Any]:
    return _read_json(REGISTRY_PATH)


def current_contract_version() -> str:
    return str(registry()["current_version"])


def contract_path(contract_name: str, version: str | None = None) -> Path:
    selected_version = version or current_contract_version()
    version_entry = registry()["versions"].get(selected_version)
    if version_entry is None:
        supported = ", ".join(sorted(registry()["versions"]))
        raise ValueError(f"Unknown contract version {selected_version!r}; available versions: {supported}")
    relative_path = version_entry["contracts"].get(contract_name)
    if relative_path is None:
        raise ValueError(f"Contract {contract_name!r} is not registered in {selected_version}")
    path = (CONTRACT_ROOT / selected_version / relative_path).resolve()
    if CONTRACT_ROOT.resolve() not in path.parents:
        raise ValueError(f"Contract path escapes the registry directory: {relative_path}")
    if not path.is_file():
        raise FileNotFoundError(f"Registered contract does not exist: {path}")
    return path


@lru_cache(maxsize=64)
def _validator(contract_name: str, version: str) -> Draft202012Validator:
    schema_path = contract_path(contract_name, version)
    schema = _read_json(schema_path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_contract(
    contract_name: str,
    payload: Any,
    *,
    version: str | None = None,
    source: str | None = None,
) -> None:
    selected_version = version or current_contract_version()
    validator = _validator(contract_name, selected_version)
    errors = sorted(validator.iter_errors(payload), key=lambda error: tuple(map(str, error.absolute_path)))
    if not errors:
        return
    details = []
    for error in errors[:12]:
        location = "/" + "/".join(str(part) for part in error.absolute_path) if error.absolute_path else "/"
        details.append(f"{location}: {error.message}")
    subject = f" in {source}" if source else ""
    remainder = f"; and {len(errors) - len(details)} more" if len(errors) > len(details) else ""
    raise ValueError(
        f"Payload{subject} violates {selected_version}/{contract_name}: "
        + "; ".join(details)
        + remainder
    )
