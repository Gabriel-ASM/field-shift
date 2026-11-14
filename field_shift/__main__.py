"""Run Markov transitions from an explicitly supplied, provenance-tracked profile."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .data import load_profile
from .monte_carlo import MonteCarlo, SimulationConfig


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path, help="Directory with manifest/states/transitions/environment JSON")
    parser.add_argument("--policy", required=True, type=Path, help="JSON action policy for the supplied profile")
    parser.add_argument("--initial-state", required=True, help="Initial state ID from states.json")
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--trajectories", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--start-period", type=int, default=0)
    parser.add_argument("--block-periods", type=int, default=2)
    parser.add_argument("--pseudocount", type=float, default=0.5)
    parser.add_argument("--mean-kernel", action="store_true", help="Use posterior mean probabilities instead of one Dirichlet draw per trajectory")
    options = parser.parse_args()

    manifest = json.loads((options.profile / "manifest.json").read_text(encoding="utf-8"))
    policy_config = json.loads(options.policy.read_text(encoding="utf-8"))
    if not isinstance(policy_config.get("name"), str) or not policy_config["name"].strip():
        parser.error("The policy must have a nonempty name")
    if not isinstance(policy_config.get("provenance"), str) or not policy_config["provenance"].strip():
        parser.error("The policy must document its source or agronomic rule")
    if not isinstance(policy_config.get("actions_by_state"), dict) or not policy_config["actions_by_state"]:
        parser.error("The policy must map states to actions")
    model, history = load_profile(options.profile, pseudocount=options.pseudocount)
    actions_by_state = policy_config.get("actions_by_state", {})
    default_action = policy_config.get("default_action")
    eligible_periods = policy_config.get("eligible_periods", {})

    def policy(decision):
        action = actions_by_state.get(decision.state.id, default_action)
        if action is None:
            raise ValueError(f"Policy has no action for state {decision.state.id!r}")
        return action

    def eligible(period, state, action):
        periods = eligible_periods.get(action)
        return periods is None or period in periods

    config = SimulationConfig(
        steps=options.steps,
        trajectories=options.trajectories,
        seed=options.seed,
        start_period=options.start_period,
        block_periods=options.block_periods,
        sample_parameters=not options.mean_kernel,
    )
    results = MonteCarlo(model, history, config).compare(
        options.initial_state,
        {policy_config.get("name", "policy"): policy},
        eligible=eligible,
    )
    print(json.dumps({
        "profile": manifest["profile"],
        "profile_version": manifest["version"],
        "data_nature": manifest["natureza"],
        "policy": policy_config.get("name", "policy"),
        "config": asdict(config),
        "financial_results": None,
        "financial_note": "Não calculado: não há fluxo econômico local associado ao perfil/política.",
        "results": {name: asdict(summary) for name, summary in results.items()},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
