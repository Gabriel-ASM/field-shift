"""Compare policies over shared, seasonally aligned environment scenarios."""

from collections import Counter
from dataclasses import dataclass
from math import ceil, isfinite
from random import Random
from statistics import median
from typing import Callable, Iterable, Mapping, Sequence

from .markov import Distribution, FieldState, MarkovModel, MissingTransition, TransitionKernel


class SeasonalHistory:
    """Complete historical years in calendar order, with two periods per month."""

    periods_per_year = 24

    def __init__(self, years: Iterable[Sequence[str]]):
        self._years = tuple(tuple(year) for year in years)
        if not self._years or any(
            len(year) != self.periods_per_year
            or any(not isinstance(environment, str) or not environment for environment in year)
            for year in self._years
        ):
            raise ValueError("History requires complete years of 24 environment labels")

    def sample(
        self, steps: int, start_period: int, block_periods: int, rng: Random
    ) -> tuple[str, ...]:
        if steps <= 0 or block_periods <= 0 or not 0 <= start_period < self.periods_per_year:
            raise ValueError("Invalid number of steps, block length or starting period")
        path: list[str] = []
        while len(path) < steps:
            period = (start_period + len(path)) % self.periods_per_year
            size = min(block_periods, steps - len(path), self.periods_per_year - period)
            year = rng.choice(self._years)
            path.extend(year[period:period + size])
        return tuple(path)


@dataclass(frozen=True)
class SimulationConfig:
    steps: int = 120
    trajectories: int = 10_000
    seed: int = 2026
    start_period: int = 0
    block_periods: int = 2
    sample_parameters: bool = True

    def __post_init__(self):
        if any(
            type(value) is not int or value <= 0
            for value in (self.steps, self.trajectories, self.block_periods)
        ):
            raise ValueError("steps, trajectories and block_periods must be positive integers")
        if type(self.start_period) is not int or not 0 <= self.start_period < 24:
            raise ValueError("start_period must be in [0, 24)")


@dataclass(frozen=True)
class Decision:
    step: int
    period: int
    state: FieldState
    actions: tuple[str, ...]


Policy = Callable[[Decision], str]
Eligibility = Callable[[int, FieldState, str], bool]
CashFlow = Callable[[Decision, str, str, FieldState], float]
PestRisk = Callable[[Decision, str, str], float]
PestLoss = Callable[[Decision, str, str, FieldState], float]


@dataclass(frozen=True)
class TransitionEvent:
    trajectory: int
    policy: str
    decision: Decision
    action: str
    environment: str
    distribution: Distribution
    uniform: float
    next_state: FieldState
    pest_probability: float = 0.0
    pest_uniform: float | None = None
    pest_occurred: bool = False
    cash_flow: float | None = None
    cumulative_npv: float | None = None


Observer = Callable[[TransitionEvent], None]


@dataclass(frozen=True)
class FinancialSummary:
    median: float
    p5: float
    p95: float
    worst_5_percent_mean: float

    @classmethod
    def from_values(cls, values: Sequence[float]) -> "FinancialSummary":
        ordered = sorted(values)
        if not ordered:
            raise ValueError("Financial summary requires at least one sample")
        count = len(ordered)
        tail_size = 0.05 * count
        full = int(tail_size)
        fractional = tail_size - full
        tail_sum = sum(ordered[:full])
        if fractional:
            tail_sum += fractional * ordered[full]
        return cls(
            median(values),
            ordered[ceil(0.05 * count) - 1],
            ordered[ceil(0.95 * count) - 1],
            tail_sum / tail_size,
        )


@dataclass(frozen=True)
class PolicySummary:
    trajectories: int
    terminal_probabilities: dict[str, float]
    financial: FinancialSummary | None
    probability_beats_reference: float | None


class MonteCarlo:
    def __init__(self, model: MarkovModel, history: SeasonalHistory, config: SimulationConfig):
        self.model = model
        self.history = history
        self.config = config

    def compare(
        self,
        initial_state: str,
        policies: Mapping[str, Policy],
        *,
        reference: str | None = None,
        eligible: Eligibility | None = None,
        cash_flow: CashFlow | None = None,
        annual_discount: float | None = None,
        on_transition: Observer | None = None,
        pest_risk: PestRisk | None = None,
        pest_loss: PestLoss | None = None,
    ) -> dict[str, PolicySummary]:
        if not policies:
            raise ValueError("At least one policy is required")
        if reference is not None and reference not in policies:
            raise ValueError(f"Unknown reference policy: {reference!r}")
        if (cash_flow is None) != (annual_discount is None):
            raise ValueError("Provide cash_flow and annual_discount together")
        if pest_loss is not None and (cash_flow is None or pest_risk is None):
            raise ValueError("Pest losses require cash flows and pest risk")
        if annual_discount is not None and (
            not isfinite(annual_discount) or annual_discount <= -1
        ):
            raise ValueError("annual_discount must be finite and greater than -1")
        start = self.model.state(initial_state)
        config = self.config
        discounts = tuple(
            (1 + annual_discount) ** (-(step + 1) / 24)
            for step in range(config.steps)
        ) if annual_discount is not None else ()
        rng = Random(config.seed)
        pest_rng = Random(f"{config.seed}:pest")
        terminal = {name: Counter() for name in policies}
        values: dict[str, list[float]] = {name: [] for name in policies}

        for trajectory in range(config.trajectories):
            environment = self.history.sample(
                config.steps, config.start_period, config.block_periods, rng
            )
            parameter_rng = Random(rng.getrandbits(64))
            kernel = (
                self.model.sample_kernel(parameter_rng)
                if config.sample_parameters else self.model.mean_kernel()
            )
            uniforms = tuple(rng.random() for _ in range(config.steps))
            pest_uniforms = (
                tuple(pest_rng.random() for _ in range(config.steps))
                if pest_risk is not None else (None,) * config.steps
            )
            for name, policy in policies.items():
                try:
                    state, value = self._run(
                        start, policy, eligible, cash_flow, discounts, kernel, environment, uniforms,
                        trajectory, name, on_transition,
                        pest_uniforms, pest_risk, pest_loss,
                    )
                except MissingTransition as exc:
                    raise MissingTransition(f"Policy {name!r}: {exc}") from exc
                terminal[name][state] += 1
                if cash_flow is not None:
                    values[name].append(value)

        summaries = {}
        for name, counts in terminal.items():
            samples = values[name]
            beats_reference = None
            if samples and reference is not None and name != reference:
                wins = sum(value > base for value, base in zip(samples, values[reference]))
                beats_reference = wins / config.trajectories
            summaries[name] = PolicySummary(
                trajectories=config.trajectories,
                terminal_probabilities={
                    state: count / config.trajectories for state, count in sorted(counts.items())
                },
                financial=FinancialSummary.from_values(samples) if samples else None,
                probability_beats_reference=beats_reference,
            )
        return summaries

    def _run(
        self,
        state: FieldState,
        policy: Policy,
        eligible: Eligibility | None,
        cash_flow: CashFlow | None,
        discounts: Sequence[float],
        kernel: TransitionKernel,
        environments: Sequence[str],
        uniforms: Sequence[float],
        trajectory: int,
        policy_name: str,
        on_transition: Observer | None,
        pest_uniforms: Sequence[float | None],
        pest_risk: PestRisk | None,
        pest_loss: PestLoss | None,
    ) -> tuple[str, float]:
        value = 0.0
        for step, (environment, uniform) in enumerate(zip(environments, uniforms)):
            period = (self.config.start_period + step) % 24
            actions = self.model.actions(state.id)
            if eligible is not None:
                actions = tuple(action for action in actions if eligible(period, state, action))
            decision = Decision(step, period, state, actions)
            action = policy(decision)
            if action not in actions:
                raise ValueError(f"Ineligible action {action!r} at step {step} for {state.id!r}")
            distribution = kernel.distribution(state.id, action, environment)
            next_state = self.model.state(distribution.draw(uniform))
            probability = pest_risk(decision, action, environment) if pest_risk else 0.0
            if not 0 <= probability <= 1:
                raise ValueError(f"Invalid pest probability at step {step}")
            pest_draw = pest_uniforms[step] if probability else None
            pest_occurred = pest_draw is not None and pest_draw < probability
            flow = None
            if cash_flow is not None:
                flow = cash_flow(decision, action, environment, next_state)
                if pest_occurred and pest_loss is not None:
                    loss = pest_loss(decision, action, environment, next_state)
                    if not isfinite(loss) or loss < 0:
                        raise ValueError(f"Invalid pest loss at step {step}")
                    flow -= loss
                if not isfinite(flow):
                    raise ValueError(f"Non-finite cash flow at step {step}")
                value += flow * discounts[step]
            if on_transition is not None:
                on_transition(TransitionEvent(
                    trajectory, policy_name, decision, action, environment,
                    distribution, uniform, next_state,
                    probability, pest_draw, pest_occurred, flow,
                    value if cash_flow is not None else None,
                ))
            state = next_state
        return state.id, value
