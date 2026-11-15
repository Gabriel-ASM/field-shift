"""v1 crop-transition-markov.json -> v2 markov chain, one per profile.

v1 does not observe field rotations. Its edge 'mass' is the sum, over consecutive years, of
(area share of the origin crop) x (area share of the destination crop) among the top-5 PAM
crops of the municipality, which assumes the two years are independent. So generated edges are
'derived', never 'observed'.

Rules (decided with the project owner, 2026-11-14):
  - one state per catalog crop, '<crop>:skip_stages', plus 'fallow:skip_stages';
  - excluded crops are removed with their mass (coffee: the profitable cycle is too long);
  - no Dirichlet prior: an edge exists only where there is mass. Rows with too little mass get
    no edge at all, and edges below a minimum probability are dropped; the rest is renormalized;
  - v1 lifecycle rules still restrict destinations (sugarcane stays sugarcane).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from .. import DATA

STAGE = "skip_stages"
FALLOW = f"fallow:{STAGE}"


@dataclass(frozen=True)
class ChainRules:
    excluded_crops: tuple[str, ...] = ("coffee",)
    min_row_mass: float = 1.0       # a row needs at least this much mass to say anything
    min_probability: float = 0.02   # weaker edges are dropped before renormalizing


def state_id(crop: str) -> str:
    return f"{crop}:{STAGE}"


def build_chain(profile: str, rules: ChainRules = ChainRules()) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (chain document for markov.json, audit report of what the rules kept and dropped)."""
    source = DATA / "profiles" / profile / "crop-transition-markov.json"
    v1 = json.loads(source.read_text(encoding="utf-8"))
    crops = [s["id"] for s in v1["states"] if s["id"] not in rules.excluded_crops]
    lifecycle = {crop: rule["allowed_destinations"] for crop, rule in v1["lifecycle_rules"].items()}
    mass = {(t["from_state"], t["to_state"]): float(t.get("area_weighted_count", 0.0)) for t in v1["transitions"]}
    rank1 = {(t["from_state"], t["to_state"]): int(t["count"]) for t in v1["transitions"]}
    start, end = v1["period"]
    provenance = (
        f"IBGE PAM {start}-{end}, {profile}: top-{v1['top_crop_limit']} area shares of consecutive years "
        f"multiplied under independence ({source.relative_to(DATA.parent).as_posix()})"
    )

    transitions, rows = [], []
    for origin in crops:
        allowed = [c for c in lifecycle.get(origin, crops) if c in crops]
        candidates = {dest: mass.get((origin, dest), 0.0) for dest in allowed}
        row_mass = sum(candidates.values())
        row = {"from": origin, "v1_mass": round(sum(v for (o, _), v in mass.items() if o == origin), 4),
               "eligible_mass": round(row_mass, 4), "rule": "lifecycle: " + ", ".join(lifecycle[origin]) if origin in lifecycle else "",
               "kept": [], "dropped": []}
        if row_mass <= 0 or row_mass < rules.min_row_mass:
            row["status"] = "no edges: row mass below minimum"
            row["dropped"] = sorted(d for d, m in candidates.items() if m > 0)
        else:
            kept = {d: m for d, m in candidates.items() if m / row_mass >= rules.min_probability}
            kept_mass = sum(kept.values())
            row["status"] = "edges kept"
            row["dropped"] = sorted(d for d, m in candidates.items() if m > 0 and d not in kept)
            row["kept_mass_share"] = round(kept_mass / row_mass, 4)
            for dest, value in sorted(kept.items(), key=lambda item: -item[1]):
                probability = round(value / kept_mass, 6)
                row["kept"].append({"to": dest, "probability": probability})
                edge = {
                    "from": state_id(origin), "to": state_id(dest), "action": None,
                    "probability": probability, "mass": round(value, 6), "outgoing_mass": round(kept_mass, 6),
                    "support": "derived", "provenance": provenance,
                }
                if rank1.get((origin, dest)):
                    edge["count"] = rank1[(origin, dest)]
                transitions.append(edge)
        rows.append(row)

    with_edges = {edge["from"] for edge in transitions}
    preferred = [state_id(c) for c in v1["initial_crop_ids"] if c in crops]
    initial = next((s for s in preferred if s in with_edges), None) or next(iter(sorted(with_edges)), FALLOW)
    chain = {
        "id": profile,
        "profile": profile,
        "description": (
            f"Regional baseline for {profile}: what the municipality's crop areas suggest follows each crop. "
            "Edges exist only where PAM gives mass; crops without edges are reachable only through rotation scenarios."
        ),
        "provenance": f"{provenance}. Rules: {json.dumps(asdict(rules))}.",
        "initial_state": initial,
        "states": [{"id": state_id(crop), "crop": crop, "stage": STAGE} for crop in crops]
                  + [{"id": FALLOW, "crop": "fallow", "stage": STAGE}],
        "transitions": transitions,
    }
    dead_ends = sorted({edge["to"] for edge in transitions} - with_edges)
    absorbing = sorted(o for o in with_edges if all(e["to"] == o for e in transitions if e["from"] == o))
    report = {"profile": profile, "period": [start, end], "rules": asdict(rules),
              "dead_ends": dead_ends, "absorbing": absorbing,
              "excluded_crops": [c for c in rules.excluded_crops if any(s["id"] == c for s in v1["states"])], "rows": rows}
    return chain, report
