"""Validate the data/contracts/v2 schemas and the examples in v2/examples.

Each example is checked against the schema named by its filename prefix
(markov.franca-sp-observed.json -> markov.json). markov.node.json is checked
against markov.json#/definitions/node.

Markov chains also get graph checks that JSON Schema cannot express:
initial_state and every from/to must be a declared state, and the
probabilities leaving a state must sum to 1 for each (action, when) group.

Usage: python data/pipeline/validate_v2_examples.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

V2 = Path(__file__).resolve().parents[1] / "contracts" / "v2"
BASE = "https://fieldshift.local/contracts/v2/"
SPECIAL = {"markov.node.json": ("markov.json", "#/definitions/node")}
TOLERANCE = 1e-3


def markov_graph_errors(chain: dict) -> list[str]:
    ids = {state["id"] for state in chain["states"]}
    errors = []
    if chain["initial_state"] not in ids:
        errors.append(f"initial_state {chain['initial_state']!r} is not a declared state")
    totals: dict[tuple, float] = defaultdict(float)
    for index, edge in enumerate(chain["transitions"]):
        for end in ("from", "to"):
            if edge[end] not in ids:
                errors.append(f"transitions/{index}/{end}: {edge[end]!r} is not a declared state")
        group = (edge["from"], edge.get("action"), json.dumps(edge.get("when", []), sort_keys=True))
        totals[group] += edge["probability"]
    for (origin, action, when), total in totals.items():
        if abs(total - 1) > TOLERANCE:
            errors.append(f"edges from {origin!r} (action={action}, when={when}) sum to {total:.4f}, not 1")
    return errors


def main() -> int:
    # A schema is an object with "$schema"; bundles such as allcontracts.json are skipped.
    schemas = {}
    for path in sorted(V2.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "$schema" in data:
            schemas[path.name] = data
    failures = 0
    for name, schema in schemas.items():
        try:
            Draft7Validator.check_schema(schema)
        except Exception as error:  # noqa: BLE001 - report and keep going
            failures += 1
            print(f"FAIL schema {name}: {error.message}")
    # Each schema is registered under its v2 $id and its bare filename, because not every file has an $id yet.
    resources = []
    for name, schema in schemas.items():
        resource = Resource.from_contents(schema, default_specification=DRAFT7)
        resources += [(BASE + name, resource), (name, resource)]
    registry = Registry().with_resources(resources)

    for example in sorted((V2 / "examples").glob("*.json")):
        schema_name, fragment = SPECIAL.get(example.name, (example.name.split(".")[0] + ".json", ""))
        if schema_name not in schemas:
            failures += 1
            print(f"FAIL {example.name}: no schema {schema_name}")
            continue
        target = {"$ref": BASE + schema_name + fragment} if fragment else schemas[schema_name]
        payload = json.loads(example.read_text(encoding="utf-8"))
        messages = [
            f"/{'/'.join(map(str, error.absolute_path))}: {error.message}"
            for error in Draft7Validator(target, registry=registry).iter_errors(payload)
        ]
        if not messages and schema_name == "markov.json" and not fragment:
            messages = markov_graph_errors(payload)
        if messages:
            failures += 1
            for message in messages:
                print(f"FAIL {example.name} {message}")
        else:
            print(f"ok   {example.name} -> {schema_name}{fragment}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
