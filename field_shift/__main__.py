"""Run a reproducible comparison with the bundled synthetic profile."""

from dataclasses import asdict
import json
from pathlib import Path

from .data import load_profile
from .monte_carlo import Decision, MonteCarlo, SimulationConfig


def adaptive(decision: Decision) -> str:
    return "irrigar" if decision.state.water == "baixa" else "manter"


def main() -> None:
    profile = Path(__file__).resolve().parent.parent / "data" / "example"
    model, history = load_profile(profile)
    simulation = MonteCarlo(model, history, SimulationConfig(trajectories=500))
    results = simulation.compare(
        "soja_baixa",
        {"referencia": lambda decision: "manter", "adaptativa": adaptive},
    )
    print(json.dumps({name: asdict(summary) for name, summary in results.items()}, indent=2))


if __name__ == "__main__":
    main()
