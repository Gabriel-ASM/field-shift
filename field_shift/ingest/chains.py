"""Project the municipal PAM proxy into a v2 chain; it is not field rotation data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .. import DATA

STAGE = "skip_stages"
FALLOW = f"fallow:{STAGE}"


@dataclass(frozen=True)
class ChainRules:
    excluded_crops: tuple[str, ...] = ("coffee",)
    alpha_per_destination: float = 0.5


def state_id(crop: str) -> str:
    return f"{crop}:{STAGE}"


def build_chain(profile: str, rules: ChainRules = ChainRules()) -> tuple[dict[str, Any], dict[str, Any]]:
    source = DATA / "profiles" / profile / "crop-transition-markov.json"
    v1 = json.loads(source.read_text(encoding="utf-8"))
    crops = [s["id"] for s in v1["states"] if s["id"] not in rules.excluded_crops]
    lifecycle = {crop: rule["allowed_destinations"] for crop, rule in v1["lifecycle_rules"].items()}
    evidence = {(t["from_state"], t["to_state"]): t for t in v1["transitions"]}
    start, end = v1["period"]
    alpha = rules.alpha_per_destination
    if not alpha > 0:
        raise ValueError("Dirichlet alpha must be positive")
    provenance = (
        f"IBGE PAM {start}-{end}, {profile}: top-{v1['top_crop_limit']} area shares of consecutive years "
        f"multiplied under independence ({source.relative_to(DATA.parent).as_posix()}). "
        f"Symmetric Dirichlet prior alpha={alpha:g} per eligible destination."
    )

    transitions, rows = [], []
    for origin in crops:
        allowed = [c for c in lifecycle.get(origin, crops) if c in crops]
        masses = {dest: float(evidence.get((origin, dest), {}).get("area_weighted_count", 0)) for dest in allowed}
        outgoing_mass = sum(masses.values())
        kept = []
        for dest, mass in masses.items():
            p = (mass + alpha) / (outgoing_mass + alpha * len(allowed))
            edge = {
                "from": state_id(origin), "to": state_id(dest), "action": None,
                "probability": p, "mass": mass, "outgoing_mass": outgoing_mass,
                "support": "derived" if mass > 0 else "prior", "provenance": provenance,
            }
            raw = evidence.get((origin, dest), {})
            if raw.get("count"):
                edge["count"] = raw["count"]
            if raw.get("outgoing_count"):
                edge["outgoing_count"] = raw["outgoing_count"]
            transitions.append(edge)
            kept.append({"to": dest, "probability": p, "support": edge["support"]})
        rows.append({"from": origin, "eligible_mass": outgoing_mass, "kept": kept})

    origins = {edge["from"] for edge in transitions}
    initial = next((state_id(c) for c in v1["initial_crop_ids"] if state_id(c) in origins), None)
    chain = {
        "id": profile, "profile": profile,
        "description": "Regional PAM proxy with a Dirichlet prior. Probabilities precede calendar and environmental adjustment.",
        "provenance": provenance,
        "initial_state": initial or next(iter(sorted(origins)), FALLOW),
        "alpha_per_destination": alpha,
        "pam_history": {key: v1[key] for key in ("source", "period", "top_crop_limit", "annual_sequence")},
        "states": [{"id": state_id(crop), "crop": crop, "stage": STAGE} for crop in crops]
                  + [{"id": FALLOW, "crop": "fallow", "stage": STAGE}],
        "transitions": transitions,
    }
    report = {
        "profile": profile, "period": [start, end], "alpha_per_destination": alpha,
        "dead_ends": sorted({edge["to"] for edge in transitions} - origins),
        "absorbing": sorted(o for o in origins if all(e["to"] == o for e in transitions if e["from"] == o)),
        "excluded_crops": list(rules.excluded_crops), "rows": rows,
    }
    return chain, report
