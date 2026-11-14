"""Run the data-backed, five-year water-state Monte Carlo for demo profiles."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from .data import load_profile
from .markov import TransitionKey
from .monte_carlo import MonteCarlo, SimulationConfig


ROOT = Path(__file__).resolve().parent.parent
PROFILE_ROOT = ROOT / "data" / "profiles"
POLICY = "reference_et0_demand"
STATE_IDS = ("water_low", "water_medium", "water_high")
STATE_LABELS = {"water_low": "baixa", "water_medium": "média", "water_high": "alta"}
WATER_ORDER = ("baixa", "media", "alta")


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(position)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[min(lower + 1, len(ordered) - 1)] * fraction


def simulate_profile(profile_dir: Path, *, trajectories: int = 10_000, seed: int = 2026) -> dict:
    manifest = json.loads((profile_dir / "manifest.json").read_text(encoding="utf-8"))
    model, history = load_profile(profile_dir)
    config = SimulationConfig(
        steps=120,
        trajectories=trajectories,
        seed=seed,
        start_period=0,
        block_periods=2,
        sample_parameters=True,
    )
    low_periods = [0] * trajectories
    current_low_run = [0] * trajectories
    maximum_low_run = [0] * trajectories

    def observe(event) -> None:
        index = event.trajectory
        if event.next_state.water == "baixa":
            low_periods[index] += 1
            current_low_run[index] += 1
            maximum_low_run[index] = max(maximum_low_run[index], current_low_run[index])
        else:
            current_low_run[index] = 0

    def policy(_decision) -> str:
        return POLICY

    summaries = MonteCarlo(model, history, config).compare(
        "water_medium",
        {"balanco_hidrico_referencia": policy},
        on_transition=observe,
    )
    summary = summaries["balanco_hidrico_referencia"]
    rows = json.loads((profile_dir / "transitions.json").read_text(encoding="utf-8"))
    transition_rows = []
    for row in rows:
        mean_distribution = model.mean_kernel().distribution(row["state"], row["action"], row["environment"])
        probabilities = {destination: probability for destination, probability in zip(mean_distribution.destinations, mean_distribution.probabilities)}
        transition_rows.append({
            "state": row["state"], "action": row["action"], "environment": row["environment"],
            "counts": row["counts"], "sample_size": row.get("sample_size"),
            "effective_sample_size": row.get("effective_sample_size"), "support": row["support"],
            "pooling": row.get("pooling"), "provenance": row["provenance"],
            "posterior_mean": probabilities,
        })

    low_fractions = [value / config.steps for value in low_periods]
    return {
        "profile": manifest["profile"],
        "version": manifest["version"],
        "policy": "balanco_hidrico_referencia",
        "scope": "probabilidade de estados de água baixa no balanço de referência; não é produtividade, perda de safra ou comparação de rotação",
        "config": {"steps": config.steps, "horizon_years": 5, "trajectories": config.trajectories, "seed": config.seed, "block_periods": config.block_periods, "pseudocount_per_destination": 0.5, "sample_transition_parameters_per_trajectory": True},
        "metrics": {
            "mean_low_water_periods": mean(low_periods),
            "median_low_water_periods": quantile(low_periods, 0.5),
            "p5_low_water_periods": quantile(low_periods, 0.05),
            "p95_low_water_periods": quantile(low_periods, 0.95),
            "mean_fraction_of_horizon_low_water": mean(low_fractions),
            "probability_low_water_at_least_24_periods": sum(value >= 24 for value in low_periods) / trajectories,
            "median_longest_low_water_run_periods": quantile(maximum_low_run, 0.5),
            "p95_longest_low_water_run_periods": quantile(maximum_low_run, 0.95),
            "terminal_probabilities": summary.terminal_probabilities,
        },
        "transitions": transition_rows,
        "environment_years": history._years,
        "water_order": list(WATER_ORDER),
        "state_labels": STATE_LABELS,
    }


def main() -> None:
    profiles = sorted(path for path in PROFILE_ROOT.iterdir() if path.is_dir() and (path / "manifest.json").is_file())
    results = [simulate_profile(path) for path in profiles]
    output = ROOT / "data" / "processed" / "demo-simulation-results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"generated_by": "field_shift.demo", "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "profiles": [{"profile": item["profile"], **item["metrics"]} for item in results],
        "output": str(output.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
