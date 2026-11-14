"""Run a ZARC-eligible crop-water Markov scenario with common Monte Carlo draws."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from .data import load_crop_scenario, load_profile
from .monte_carlo import MonteCarlo, SimulationConfig


ROOT = Path(__file__).resolve().parent.parent


def water_id(value: str) -> str:
    return {"baixa": "water_low", "media": "water_medium", "alta": "water_high"}[value]


def quantile(values: list[int], probability: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * probability
    lower = int(position)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[min(lower + 1, len(ordered) - 1)] * fraction


def run_model(model, history, initial_state: str, action: str, config: SimulationConfig) -> dict:
    low_counts = [0] * config.trajectories
    low_run = [0] * config.trajectories
    longest = [0] * config.trajectories

    def observe(event) -> None:
        index = event.trajectory
        if event.next_state.water == "baixa":
            low_counts[index] += 1
            low_run[index] += 1
            longest[index] = max(longest[index], low_run[index])
        else:
            low_run[index] = 0

    def policy(_decision) -> str:
        return action

    summaries = MonteCarlo(model, history, config).compare(
        initial_state,
        {action: policy},
        on_transition=observe,
    )
    terminal = {"water_low": 0, "water_medium": 0, "water_high": 0}
    for state_id, probability in summaries[action].terminal_probabilities.items():
        state = model.state(state_id)
        terminal[water_id(state.water)] += probability
    summary = summaries[action]
    return {
        "trajectories": config.trajectories,
        "mean_low_water_periods": mean(low_counts),
        "median_low_water_periods": quantile(low_counts, 0.5),
        "p5_low_water_periods": quantile(low_counts, 0.05),
        "p95_low_water_periods": quantile(low_counts, 0.95),
        "mean_fraction_of_horizon_low_water": mean(low_counts) / config.steps,
        "probability_low_water_at_least_24_periods": sum(value >= 24 for value in low_counts) / config.trajectories,
        "median_longest_low_run_periods": quantile(longest, 0.5),
        "p95_longest_low_run_periods": quantile(longest, 0.95),
        "terminal_probabilities": terminal,
        "state_terminal_probabilities": summary.terminal_probabilities,
    }


def run(profile: Path, crop_id: str, planting_decendio: int, *, trajectories: int, seed: int, zarc_group: str | None = None, zarc_soil: str | None = None, risk: int = 30) -> dict:
    profile = profile.resolve()
    base_model, history = load_profile(profile)
    crop_model, crop_history, scenario = load_crop_scenario(profile, crop_id, planting_decendio)
    if tuple(history._years) != tuple(crop_history._years):
        raise ValueError("Reference and crop scenario have different environmental histories")
    zarc = json.loads((profile / "zarc-planting-windows.json").read_text(encoding="utf-8"))
    matches = [
        row for row in zarc["rows"]
        if row.get("crop_parameter_id") == crop_id
        and (zarc_group is None or row["cultivar_group"] == zarc_group)
        and (zarc_soil is None or row["zarc_soil_class"] == zarc_soil)
        and planting_decendio in row["planting_decendios_by_risk_percent"].get(str(risk), [])
    ]
    if not matches:
        raise ValueError("The selected crop/decendio is not eligible for the requested ZARC group, soil class and risk")
    config = SimulationConfig(
        steps=120,
        trajectories=trajectories,
        seed=seed,
        start_period=0,
        block_periods=2,
        sample_parameters=True,
    )
    reference = run_model(base_model, history, "water_medium", "reference_et0_demand", config)
    crop = run_model(crop_model, crop_history, scenario["initial_state_id"], scenario["action"], config)
    return {
        "profile": json.loads((profile / "manifest.json").read_text(encoding="utf-8"))["profile"],
        "scenario": {
            "crop_parameter_id": crop_id,
            "crop_name_pt": scenario["crop_name_pt"],
            "official_zarc_crop_label": matches[0]["crop"],
            "zarc_group": matches[0]["cultivar_group"],
            "zarc_soil_class": matches[0]["zarc_soil_class"],
            "risk_percent": risk,
            "planting_decendio": planting_decendio,
            "portaria": matches[0]["portaria"],
            "portaria_date": matches[0]["portaria_date"],
            "action": scenario["action"],
            "support": "derived_process_model",
        },
        "config": {
            "steps": config.steps,
            "horizon_years": 5,
            "trajectories": config.trajectories,
            "seed": config.seed,
            "block_periods": config.block_periods,
            "pseudocount_per_viable_destination": 0.5,
            "common_random_numbers": "same seed, seasonal environment blocks and transition uniforms for the reference and crop-model runs; row parameters sampled from each model's own counts",
        },
        "reference_kc1": reference,
        "crop_water_scenario": crop,
        "interpretation": "Water-state sensitivity scenario only; not observed management effect, yield forecast, crop recommendation, or VPL.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--crop", required=True, help="FAO parameter id, for example soybean, peanut, maize_grain")
    parser.add_argument("--planting-decendio", type=int, required=True, choices=range(1, 37))
    parser.add_argument("--zarc-group")
    parser.add_argument("--zarc-soil")
    parser.add_argument("--risk", type=int, default=30, choices=(20, 30, 40))
    parser.add_argument("--trajectories", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    result = run(
        options.profile,
        options.crop,
        options.planting_decendio,
        trajectories=options.trajectories,
        seed=options.seed,
        zarc_group=options.zarc_group,
        zarc_soil=options.zarc_soil,
        risk=options.risk,
    )
    output = options.output or ROOT / "data" / "processed" / f"crop-scenario-{result['profile']}-{options.crop}-d{options.planting_decendio:02}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": output.relative_to(ROOT).as_posix() if output.is_relative_to(ROOT) else str(output), "profile": result["profile"], "scenario": result["scenario"], "reference_kc1": result["reference_kc1"], "crop_water_scenario": result["crop_water_scenario"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
