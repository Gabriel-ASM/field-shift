"""Run a Monte Carlo request (contract v2 `monte_carlo`, without the chain) for one profile."""

from __future__ import annotations

import time
from functools import lru_cache

from .backend import array_module
from .calendar import DAYS_PER_YEAR
from .monte_carlo import Policy, simulate
from .payload import profile_payload, reference_payload
from .summary import summarize
from .tables import Tables, build_tables

MAX_TRAJECTORIES = 1_000_000
MAX_TRACKS = 200


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


def policy_of(tables: Tables, scenario: dict, default_state: str) -> Policy:
    """A rotation starts on its first crop unless the scenario says otherwise; a markov scenario on the chain's."""
    policy = scenario["policy"]
    sequence = tuple(crop_index(tables, crop) for crop in policy.get("sequence", ()))
    start = scenario.get("initial_state") or (None if sequence else default_state)
    initial = crop_index(tables, crop_of_state(start)) if start else sequence[0]
    return Policy(initial, sequence, int(scenario.get("initial_sugarcane_cut", 1)))


def options(profile_id: str) -> dict:
    """What a client may choose for a run of this profile."""
    tables = tables_for(profile_id)
    selectable = profile_payload(profile_id)["crop_markov"]["initial_crop_ids"]
    return {"profile": profile_id, "crops": list(tables.crops), "initial_crops": [c for c in selectable if c in tables.crops],
            "ranking": ranking_settings(tables), "max_trajectories": MAX_TRAJECTORIES, "horizon_days": tables.horizon_years * DAYS_PER_YEAR}


def ranking_settings(tables: Tables) -> dict:
    """How a client turns route results into a 0-10 score: the team's ranking rules, with their sources."""
    settings = reference_payload()["run_settings"]
    score, environment = settings["ranking_score"], settings["ranking_score"]["environment"]
    water = [float(m) for m in tables.water_yield]
    return {
        "minimum": score["minimum"], "maximum": score["maximum"], "break_even": score["break_even"],
        "minimum_scale": score["minimum_scale_brl_per_ha"],
        "minimum_samples": settings["monte_carlo"]["minimum_leader_vpl_samples"],
        "environment_weight": {key: environment[key] for key in ("default_weight", "maximum_weight", "weight_step")},
        "soil_share": environment["soil_share"], "water_share": environment["water_share"],
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


def run(request: dict, default_state: str, device: str = "auto", tracks: int = 0) -> dict:
    """Simulate every scenario with the same seed, so they all face the same environment."""
    tables = tables_for(request["profile"])
    check_request(tables, request)
    xp = array_module(device)
    on_device, started = tables.on(xp), time.perf_counter()
    scenarios = []
    for scenario in request["scenarios"]:
        policy = policy_of(tables, scenario, default_state)
        result = simulate(xp, on_device, policy, request["seed"], request["trajectories"], min(tracks, MAX_TRACKS))
        scenarios.append({"id": scenario["id"], "label": scenario.get("label", scenario["id"]),
                          "initial_crop": tables.crops[policy.initial_crop], **summarize(result, tables)})
    return {
        "profile": request["profile"], "seed": request["seed"], "device": "gpu" if xp.__name__ == "cupy" else "cpu",
        "seconds": round(time.perf_counter() - started, 3),
        "clock": {"period_days": tables.period_days, "periods": tables.periods, "horizon_years": tables.horizon_years},
        "crops": [*tables.crops, "fallow"], "ranking": ranking_settings(tables), "scenarios": scenarios,
    }
