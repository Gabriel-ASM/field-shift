"""Validate every example in data/contracts/v2/examples against its contract.

The contract is the filename prefix (markov.franca-sp.json -> markov). markov.node.json is
checked against markov#/definitions/node.

Usage: python -m field_shift.contracts
"""

from __future__ import annotations

import json
import sys

from . import V2_DIR, check, contract_names, validate

FRAGMENTS = {"markov.node.json": ("markov", "#/definitions/node")}


def main() -> int:
    failures = 0
    for example in sorted((V2_DIR / "examples").glob("*.json")):
        name, fragment = FRAGMENTS.get(example.name, (example.name.split(".")[0], ""))
        if name not in contract_names():
            print(f"FAIL {example.name}: no contract {name!r}")
            failures += 1
            continue
        document = json.loads(example.read_text(encoding="utf-8"))
        errors = validate(name, document, fragment=fragment)
        if not errors and not fragment:
            errors = check(name, document)
        failures += bool(errors)
        for message in errors:
            print(f"FAIL {example.name} {message}")
        if not errors:
            print(f"ok   {example.name} -> {name}{fragment}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
