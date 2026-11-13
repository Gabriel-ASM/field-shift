"""Action and environment conditioned transitions for agricultural states."""

from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from itertools import accumulate
from math import isfinite
from random import Random
from typing import Iterable, Mapping


@dataclass(frozen=True)
class FieldState:
    id: str
    crop: str
    phase: str
    water: str
    soil: str
    recent_crops: tuple[str, ...] = ()


@dataclass(frozen=True)
class TransitionKey:
    state: str
    action: str
    environment: str


@dataclass(frozen=True)
class Distribution:
    destinations: tuple[str, ...]
    probabilities: tuple[float, ...]
    cumulative: tuple[float, ...]

    @classmethod
    def from_weights(cls, weights: Mapping[str, float]) -> "Distribution":
        if any(not isfinite(value) or value < 0 for value in weights.values()):
            raise ValueError("Transition weights must be finite and nonnegative")
        destinations = tuple(sorted(key for key, value in weights.items() if value > 0))
        total = sum(weights[key] for key in destinations)
        if not isfinite(total) or total <= 0:
            raise ValueError("A transition distribution needs positive finite mass")
        probabilities = tuple(weights[key] / total for key in destinations)
        cumulative = tuple(min(1.0, value) for value in accumulate(probabilities))
        return cls(destinations, probabilities, (*cumulative[:-1], 1.0))

    def draw(self, uniform: float) -> str:
        if not 0 <= uniform < 1:
            raise ValueError("The transition draw must be in [0, 1)")
        return self.destinations[bisect_right(self.cumulative, uniform)]


class MissingTransition(ValueError):
    """No transition was configured for a state, action and environment."""


class TransitionKernel:
    def __init__(self, rows: Mapping[TransitionKey, Distribution]):
        self._rows = dict(rows)

    def distribution(self, state: str, action: str, environment: str) -> Distribution:
        key = TransitionKey(state, action, environment)
        try:
            return self._rows[key]
        except KeyError as exc:
            raise MissingTransition(
                f"Missing transition for state={state!r}, action={action!r}, "
                f"environment={environment!r}"
            ) from exc

    def next_state(self, state: str, action: str, environment: str, uniform: float) -> str:
        return self.distribution(state, action, environment).draw(uniform)


class MarkovModel:
    """Each row lists viable destinations and their observed counts."""

    def __init__(
        self,
        states: Iterable[FieldState],
        rows: Mapping[TransitionKey, Mapping[str, int]],
        *,
        pseudocount: float = 0.5,
    ):
        if not isfinite(pseudocount) or pseudocount < 0:
            raise ValueError("pseudocount must be finite and nonnegative")
        self._states: dict[str, FieldState] = {}
        for state in states:
            if not state.id or state.id in self._states:
                raise ValueError(f"Empty or duplicate state ID: {state.id!r}")
            self._states[state.id] = state
        if not self._states or not rows:
            raise ValueError("At least one state and transition row are required")

        self._parameters: dict[TransitionKey, dict[str, float]] = {}
        actions: dict[str, set[str]] = defaultdict(set)
        for key in sorted(rows, key=lambda row: (row.state, row.action, row.environment)):
            counts = rows[key]
            self.state(key.state)
            if not key.action or not key.environment:
                raise ValueError(f"Empty action or environment in {key}")
            for destination, count in counts.items():
                self.state(destination)
                if type(count) is not int or count < 0:
                    raise ValueError(f"Counts must be nonnegative integers in {key}")
            if not any(counts.values()):
                raise ValueError(f"No observations in {key}")
            self._parameters[key] = {
                destination: counts[destination] + pseudocount
                for destination in sorted(counts)
            }
            actions[key.state].add(key.action)
        self._actions = {state: tuple(sorted(values)) for state, values in actions.items()}
        self._mean = TransitionKernel({
            key: Distribution.from_weights(parameters)
            for key, parameters in self._parameters.items()
        })

    def state(self, state_id: str) -> FieldState:
        try:
            return self._states[state_id]
        except KeyError as exc:
            raise ValueError(f"Unknown state: {state_id!r}") from exc

    def actions(self, state_id: str) -> tuple[str, ...]:
        self.state(state_id)
        return self._actions.get(state_id, ())

    def mean_kernel(self) -> TransitionKernel:
        return self._mean

    def sample_kernel(self, rng: Random) -> TransitionKernel:
        """Draw each row once from its Dirichlet distribution."""
        rows = {}
        for key, parameters in self._parameters.items():
            weights = {
                state: rng.gammavariate(parameter, 1.0)
                for state, parameter in parameters.items()
                if parameter > 0
            }
            # Very small shape parameters can underflow in floating point.
            rows[key] = (
                Distribution.from_weights(weights) if any(weights.values())
                else self._mean.distribution(key.state, key.action, key.environment)
            )
        return TransitionKernel(rows)
