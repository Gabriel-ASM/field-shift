"""Rules JSON Schema cannot express: ids that must exist and probabilities that must sum to 1."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Callable

TOLERANCE = 1e-3


def markov_graph_errors(chain: dict[str, Any]) -> list[str]:
    ids = [state["id"] for state in chain["states"]]
    errors = [f"duplicate state id {state_id!r}" for state_id in sorted({i for i in ids if ids.count(i) > 1})]
    known = set(ids)
    if chain["initial_state"] not in known:
        errors.append(f"initial_state {chain['initial_state']!r} is not a declared state")
    totals: dict[tuple, float] = defaultdict(float)
    for index, edge in enumerate(chain["transitions"]):
        for end in ("from", "to"):
            if edge[end] not in known:
                errors.append(f"transitions/{index}/{end}: {edge[end]!r} is not a declared state")
        group = (edge["from"], edge.get("action"), json.dumps(edge.get("when", []), sort_keys=True))
        totals[group] += edge["probability"]
    for (origin, action, when), total in totals.items():
        if abs(total - 1) > TOLERANCE:
            errors.append(f"edges from {origin!r} (action={action}, when={when}) sum to {total:.4f}, not 1")
    return errors


def monte_carlo_errors(run: dict[str, Any]) -> list[str]:
    chain = run["chain"]
    errors = [f"chain: {message}" for message in markov_graph_errors(chain)]
    ids = {state["id"] for state in chain["states"]}
    crop_by_state = {state["id"]: state["crop"] for state in chain["states"]}
    crops = {state["crop"] for state in chain["states"]}
    for scenario in run["scenarios"]:
        policy, name = scenario["policy"], scenario["id"]
        if scenario.get("initial_state") and scenario["initial_state"] not in ids:
            errors.append(f"scenario {name}: initial_state {scenario['initial_state']!r} is not a chain state")
        effective_start = scenario.get("initial_state", chain["initial_state"])
        if "initial_sugarcane_cut" in scenario and crop_by_state.get(effective_start) != "sugarcane":
            errors.append(f"scenario {name}: initial_sugarcane_cut requires a sugarcane initial state")
        if policy["kind"] == "rotation":
            errors += [f"scenario {name}: crop {crop!r} has no state in the chain" for crop in policy["sequence"] if crop not in crops]
            if policy["fallback"] not in ids:
                errors.append(f"scenario {name}: fallback {policy['fallback']!r} is not a chain state")
    for event in run.get("events", []):
        errors += [f"event {event['id']}: crop {crop!r} has no state in the chain" for crop in event.get("crops", []) if crop not in crops]
    return errors


CHECKS: dict[str, Callable[[dict[str, Any]], list[str]]] = {
    "markov": markov_graph_errors,
    "monte_carlo": monte_carlo_errors,
}


def check(name: str, document: Any) -> list[str]:
    """Cross-reference rules for a document that already passed schema validation."""
    rule = CHECKS.get(name)
    return rule(document) if rule else []
