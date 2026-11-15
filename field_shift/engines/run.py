"""Run a Monte Carlo request (contract v2 `monte_carlo`, without the chain) for one profile."""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import lru_cache

from .backend import array_module
from .calendar import DAYS_PER_YEAR
from .batches import batch_for, simulate_batches
from .monte_carlo import Policy
from .payload import profile_payload, reference_payload
from .summary import Support, summarize, yield_penalties
from .tables import Tables, build_tables

MAX_TRAJECTORIES = 1_000_000
MAX_TRACKS = 200
DECENDIOS_PER_YEAR = 36
# Share of P95 (against CVaR5) in the economic score: the slider #ranking-return-weight of field_shift/front/index.html
# (0-100%, step 5, starts at 50). The team keeps it in the page, not in visualization-run-settings.json.
RETURN_WEIGHT = {"default": 0.5, "step": 0.05}


class RunError(ValueError):
    """The request is well formed but cannot be simulated."""


@lru_cache(maxsize=8)
def tables_for(profile_id: str) -> Tables:
    return build_tables(profile_payload(profile_id), reference_payload())


def crop_index(tables: Tables, crop: str) -> int:
    if crop not in tables.crops:
        raise RunError(f"crop {crop!r} is not in the chain of this profile")
    return tables.crops.index(crop)


def crop_of_state(state_id: str) -> str:
    return state_id.split(":")[0]


def sugarcane_cuts(tables: Tables) -> int | None:
    """Harvests of a cane field before it is reformed (crop-cycle-assumptions.json), or None without cane."""
    return int(tables.sugarcane_cuts) if tables.sugarcane >= 0 else None


def initial_cut(tables: Tables, scenario: dict) -> int:
    """The next harvest of standing cane, checked against the cuts the model has."""
    cut, cuts = int(scenario.get("initial_sugarcane_cut", 1)), sugarcane_cuts(tables)
    if cuts is not None and not 1 <= cut <= cuts:
        raise RunError(f"initial_sugarcane_cut={cut}: this profile models cuts 1 to {cuts}")
    return cut


def policy_of(tables: Tables, scenario: dict, default_state: str) -> Policy:
    """A rotation starts on its first crop unless the scenario says otherwise; a markov scenario on the chain's."""
    policy = scenario["policy"]
    sequence = tuple(crop_index(tables, crop) for crop in policy.get("sequence", ()))
    start = scenario.get("initial_state") or (None if sequence else default_state)
    initial = crop_index(tables, crop_of_state(start)) if start else sequence[0]
    return Policy(initial, sequence, initial_cut(tables, scenario))


def options(profile_id: str) -> dict:
    """What a client may choose for a run of this profile."""
    tables = tables_for(profile_id)
    selectable = profile_payload(profile_id)["crop_markov"]["initial_crop_ids"]
    return {"profile": profile_id, "crops": list(tables.crops), "initial_crops": [c for c in selectable if c in tables.crops],
            "sugarcane_cuts": sugarcane_cuts(tables), "ranking": ranking_settings(tables), "model": model_settings(tables),
            "max_trajectories": MAX_TRAJECTORIES, "horizon_days": tables.horizon_years * DAYS_PER_YEAR}


def model_settings(tables: Tables) -> dict:
    """The model's own numbers, for the explanation of how a result was computed."""
    return {"dirichlet_alpha": tables.alpha, "discount_rate": tables.discount_rate, "period_days": tables.period_days,
            "periods_per_year": tables.periods_per_year, "decision_steps_per_year": DECENDIOS_PER_YEAR,
            "horizon_years": tables.horizon_years}


def support_of(tables: Tables) -> Support:
    support = ranking_settings(tables)["support"]
    return Support(ranked=int(support["minimum_ranked"]), recommended=int(support["minimum_recommended"]))


def ranking_settings(tables: Tables) -> dict:
    """How a client turns route results into a 0-10 score: the team's ranking rules, with their sources."""
    settings = reference_payload()["run_settings"]
    score, environment, support = settings["ranking_score"], settings["ranking_score"]["environment"], settings["ranking_score"]["support"]
    water = [float(m) for m in tables.water_yield]
    return {
        "minimum": score["minimum"], "maximum": score["maximum"], "break_even": score["break_even"],
        "minimum_scale": score["minimum_scale_brl_per_ha"],
        "minimum_samples": settings["monte_carlo"]["minimum_leader_vpl_samples"],
        "return_weight": RETURN_WEIGHT,
        "support": {"weight": support["weight"], "minimum_ranked": support["minimum_ranked_vpl_samples"],
                    "minimum_recommended": support["minimum_recommended_vpl_samples"],
                    "full_score": support["full_score_vpl_samples"]},
        "environment_weight": {key: environment[key] for key in ("default_weight", "maximum_weight", "weight_step")},
        "soil_share": environment["soil_share"], "water_share": environment["water_share"],
        "carbon_share_within_soil": environment["carbon_share_within_soil"],
        "nitrogen_share_within_soil": environment["nitrogen_share_within_soil"],
        "nitrogen_target_per_carbon": tables.total_n_target_per_carbon,
        "nitrogen_ratio_limits": [float(v) for v in tables.total_n_class_limits],
        "soil_reference": environment["soil_reference_g_kg"],
        "water_scale": max(abs(m - 1) for m in water) or 1e-9,
    }


def check_request(tables: Tables, request: dict) -> None:
    horizon = tables.horizon_years * DAYS_PER_YEAR
    if request["horizon_days"] != horizon:
        raise RunError(f"this engine simulates {horizon} days; horizon_days={request['horizon_days']} is not supported yet")
    if request.get("events"):
        raise RunError("random events are not simulated yet: there is no event data for any profile")
    if request["trajectories"] > MAX_TRAJECTORIES:
        raise RunError(f"at most {MAX_TRAJECTORIES} trajectories per scenario")


def prepare(request: dict, default_state: str) -> tuple[Tables, list[Policy]]:
    """Check a request and turn its scenarios into policies; raises RunError before anything is simulated."""
    tables = tables_for(request["profile"])
    check_request(tables, request)
    return tables, [policy_of(tables, scenario, default_state) for scenario in request["scenarios"]]


def name_sequence(overall: dict, crops: list[str], tables: Tables) -> None:
    """A fixed rotation's own result is its sequence: name it, with the yield lost at each replanting."""
    overall["crops"], overall["yield_penalty"] = crops, yield_penalties(crops, tables)


def total_trajectories(request: dict) -> int:
    return request["trajectories"] * len(request["scenarios"])


def run(request: dict, default_state: str, device: str = "auto", tracks: int = 0,
        progress: Callable[[int], None] = lambda done: None, raw: list | None = None) -> dict:
    """Simulate every scenario with the same seed, so they all face the same environment.

    `progress` gets the trajectories done so far, over all scenarios. When `raw` is a list, the joined arrays of each
    scenario, with every trajectory's path codes, are appended to it (for route details served later)."""
    tables, policies = prepare(request, default_state)
    xp = array_module(device)
    on_device, started = tables.on(xp), time.perf_counter()
    scenarios = []
    for index, (scenario, policy) in enumerate(zip(request["scenarios"], policies)):
        before = index * request["trajectories"]
        result = simulate_batches(xp, on_device, policy, request["seed"], request["trajectories"], min(tracks, MAX_TRACKS),
                                  paths=raw is not None, batch=batch_for(xp), progress=lambda done: progress(before + done))
        if raw is not None:
            raw.append(result)
        summary = summarize(result, tables, support_of(tables))
        if policy.sequence:
            name_sequence(summary["overall"], [tables.crops[i] for i in policy.sequence], tables)
        scenarios.append({"id": scenario["id"], "label": scenario.get("label", scenario["id"]),
                          "initial_crop": tables.crops[policy.initial_crop], **summary})
    return {
        "profile": request["profile"], "seed": request["seed"], "device": "gpu" if xp.__name__ == "cupy" else "cpu",
        "seconds": round(time.perf_counter() - started, 3),
        "clock": {"period_days": tables.period_days, "periods": tables.periods, "horizon_years": tables.horizon_years},
        "crops": [*tables.crops, "fallow"], "ranking": ranking_settings(tables), "model": model_settings(tables),
        "scenarios": scenarios,
    }
