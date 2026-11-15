"""Monte Carlo of crop trajectories, one array row per trajectory.

A run separates three things, each with its own random stream:
  environment  climate years, soil water and soil carbon response; identical in every scenario of a run
  parameters   the uncertain chain of each trajectory
  choice       which crop the scenario plants next
Outcomes (harvests, costs, present value) are deterministic given those three.

Every period runs the same short steps in a fixed order: water, soil, clocks, harvest, decide, plant,
formation cost. Each step is one function over the whole batch, so the loop runs on a GPU unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import markov
from .calendar import DAYS_PER_YEAR
from .tables import FALLOW, Tables

STREAMS = ("environment", "parameters", "choice")
EPSILON = 1e-9
ROUTE_LIMIT = 15        # plantings encoded in a route key


@dataclass(frozen=True)
class Policy:
    """How a scenario chooses. `sequence` empty means draw from the chain; otherwise plant it in order."""
    initial_crop: int
    sequence: tuple[int, ...] = ()
    initial_sugarcane_cut: int = 1


class State:
    """Arrays of one batch. Days are floats, crops are indices (FALLOW = no crop in the field)."""

    def __init__(self, xp, tables: Tables, policy: Policy, count: int):
        full = lambda value, dtype=float: xp.full(count, value, dtype=dtype)
        self.crop = full(policy.initial_crop, int)
        self.last_crop = full(policy.initial_crop, int)
        self.streak = full(1, int)
        self.cane_cut = full(policy.initial_sugarcane_cut, int)
        self.water_fraction = full(tables.initial_water)
        self.water_class = water_class(xp, tables, self.water_fraction)
        self.carbon = full(tables.initial_carbon)
        self.harvest_in = full(float(tables.cycle_days[policy.initial_crop]))
        self.maturing_for = full(0.0)
        self.formation_in = full(xp.inf)
        self.pending_day = full(xp.inf)
        self.pending_crop = full(FALLOW, int)
        self.pending_streak = full(1, int)
        self.sequence_position = full(1, int)
        self.value = full(0.0)
        self.priced = full(True, bool)
        self.route = full(policy.initial_crop + 1, int)
        self.plantings = full(0, int)


def water_class(xp, tables: Tables, fraction):
    return (fraction > tables.water_class_limits[0]).astype(int) + (fraction > tables.water_class_limits[1])


def carbon_class(xp, tables: Tables, carbon):
    return (carbon >= tables.carbon_class_limits[0]).astype(int) + (carbon >= tables.carbon_class_limits[1])


def day_of_year(xp, day):
    return day.astype(int) % DAYS_PER_YEAR


def discount(tables: Tables, day):
    return (1 + tables.discount_rate) ** (day / DAYS_PER_YEAR)


def crop_or_first(xp, crop):
    """Crop index safe for table lookups; callers mask the fallow rows afterwards."""
    return xp.maximum(crop, 0)


def advance_water(xp, tables: Tables, state: State, rain, uniform) -> None:
    """Draw the next water class from the profile counts, then shift it by the crop's water demand."""
    counts = tables.water_counts[state.water_class, rain]
    sampled = xp.where(counts.sum(axis=1) > 0, markov.draw(xp, counts, uniform), state.water_class)
    demand = xp.where(state.crop >= 0, tables.demand_shift[crop_or_first(xp, state.crop)], 0.0)
    state.water_fraction = xp.clip(tables.water_fraction_of[sampled] - demand, 0, 1)
    state.water_class = water_class(xp, tables, state.water_fraction)


def advance_soil(xp, tables: Tables, state: State, soil_rate) -> None:
    """Soil carbon moves at the rate of the crop in the field; fallow leaves it unchanged."""
    rows = xp.arange(state.crop.shape[0])
    rate = xp.where(state.crop >= 0, soil_rate[rows, crop_or_first(xp, state.crop)], 0.0)
    state.carbon = xp.maximum(0.1, state.carbon + rate * tables.period_days / DAYS_PER_YEAR)


def advance_clocks(tables: Tables, state: State) -> None:
    state.harvest_in = state.harvest_in - tables.period_days
    state.maturing_for = state.maturing_for - tables.period_days * (state.maturing_for > 0)
    state.formation_in = state.formation_in - tables.period_days


def repeat_multiplier(xp, tables: Tables, crop, streak):
    return xp.maximum(tables.repeat_floor[crop], 1 - (streak - 1) * tables.repeat_penalty[crop])


def harvest_cash(xp, tables: Tables, state: State, crop, day):
    """Revenue minus cost of one harvest, in BRL/ha of that day."""
    price = tables.price[crop] * (1 + tables.price_trend[crop]) ** (day / DAYS_PER_YEAR)
    response = tables.water_yield[state.water_class] * tables.carbon_yield[carbon_class(xp, tables, state.carbon)]
    return tables.yield_tonnes[crop] * price * response * repeat_multiplier(xp, tables, crop, state.streak) - tables.cost[crop]


def harvest(xp, tables: Tables, state: State, day: float) -> None:
    """Harvest ripe fields. Perennials start a new cycle; other fields go fallow and wait for a planting window."""
    ripe = (state.crop >= 0) & (state.harvest_in <= EPSILON)
    crop = crop_or_first(xp, state.crop)
    state.value = state.value + xp.where(ripe, harvest_cash(xp, tables, state, crop, day) / discount(tables, day), 0.0)
    state.priced = state.priced & ~(ripe & ~tables.harvest_priced[crop])
    cane = ripe & (crop == tables.sugarcane)
    reform = cane & (state.cane_cut == tables.sugarcane_cuts)
    state.cane_cut = state.cane_cut + cane
    stays = ripe & tables.perennial[crop] & ~reform
    leaves = ripe & ~stays
    first = xp.ceil(xp.full(crop.shape, day))
    opportunity = first + tables.opportunity_wait[crop, day_of_year(xp, first)]
    horizon_days = tables.periods * tables.period_days
    state.pending_day = xp.where(leaves, xp.where(reform & (day >= horizon_days), xp.inf, opportunity), state.pending_day)
    state.pending_crop = xp.where(leaves, FALLOW, state.pending_crop)
    state.last_crop = xp.where(leaves, crop, state.last_crop)
    state.crop = xp.where(leaves, FALLOW, state.crop)
    state.harvest_in = xp.where(stays, tables.cycle_days[crop], xp.where(leaves, xp.inf, state.harvest_in))
    state.maturing_for = xp.where(ripe, 0.0, state.maturing_for)
    state.formation_in = xp.where(ripe, xp.inf, state.formation_in)


def choose_from_chain(xp, tables: Tables, state: State, allowed, reform, rows, reform_rows, uniform):
    index = xp.arange(state.crop.shape[0])
    base = xp.where(reform[:, None], reform_rows, rows[index, state.last_crop])
    weights = markov.destination_weights(xp, tables, base, allowed, state.water_fraction, state.carbon)
    return markov.draw(xp, weights, uniform), allowed.any(axis=1)


def choose_from_sequence(xp, state: State, allowed, sequence):
    """Next crop of a fixed rotation. It is feasible only where the chain has that edge and a window exists."""
    target = sequence[state.sequence_position % sequence.shape[0]]
    return target, allowed[xp.arange(target.shape[0]), target]


def decide(xp, tables: Tables, state: State, day: float, choose) -> None:
    """At a planting opportunity, pick the next crop and schedule its sowing; otherwise wait for the next one."""
    deciding = (state.crop < 0) & (state.pending_crop < 0) & (state.pending_day <= day)
    reform = state.last_crop == tables.sugarcane
    allowed = xp.where(reform[:, None], tables.reform_eligible[None, :], tables.eligible[state.last_crop])
    chosen, feasible = choose(allowed, reform)
    today = xp.where(deciding, state.pending_day, 0.0)
    sowing = today + tables.window_wait[chosen, day_of_year(xp, today)]
    planned = deciding & feasible & xp.isfinite(sowing)
    waiting = deciding & ~planned
    retry = today + 1 + tables.opportunity_wait[state.last_crop, day_of_year(xp, today + 1)]
    state.pending_streak = xp.where(planned, xp.where(chosen == state.last_crop, state.streak + 1, 1), state.pending_streak)
    state.pending_crop = xp.where(planned, chosen, state.pending_crop)
    state.pending_day = xp.where(planned, sowing, xp.where(waiting, retry, state.pending_day))
    state.sequence_position = state.sequence_position + planned


def formation_cash(xp, tables: Tables, crop, days):
    """Cost of forming a perennial for `days` (at most one year), in BRL/ha."""
    return -tables.cost[crop] * tables.formation_share[crop] * xp.minimum(1.0, days / DAYS_PER_YEAR)


def plant(xp, tables: Tables, state: State, day: float) -> None:
    """Sow the scheduled crop and start its clocks; a perennial pays its first formation cost."""
    sowing = (state.crop < 0) & (state.pending_crop >= 0) & (state.pending_day <= day)
    crop = crop_or_first(xp, state.pending_crop)
    sown_on = xp.where(sowing, state.pending_day, 0.0)
    elapsed = xp.maximum(0.0, day - sown_on)
    perennial = sowing & tables.perennial[crop]
    first_cycle = xp.maximum(tables.cycle_days[crop], tables.maturation_days[crop])
    cash = formation_cash(xp, tables, crop, xp.minimum(DAYS_PER_YEAR, tables.maturation_days[crop]))
    state.value = state.value + xp.where(perennial, cash / discount(tables, sown_on), 0.0)
    state.priced = state.priced & ~(perennial & ~tables.formation_priced[crop])
    state.crop = xp.where(sowing, crop, state.crop)
    state.streak = xp.where(sowing, state.pending_streak, state.streak)
    state.cane_cut = xp.where(sowing & (crop == tables.sugarcane), 1, state.cane_cut)
    state.harvest_in = xp.where(sowing, xp.maximum(tables.period_days, first_cycle - elapsed), state.harvest_in)
    state.maturing_for = xp.where(sowing, xp.maximum(0.0, tables.maturation_days[crop] - elapsed), state.maturing_for)
    state.formation_in = xp.where(sowing, xp.where(perennial, xp.maximum(0.0, DAYS_PER_YEAR - elapsed), xp.inf), state.formation_in)
    counted = sowing & (state.plantings < ROUTE_LIMIT)
    state.route = xp.where(counted, state.route * (tables.cycle_days.shape[0] + 1) + crop + 1, state.route)
    state.plantings = state.plantings + sowing
    state.pending_crop = xp.where(sowing, FALLOW, state.pending_crop)
    state.pending_day = xp.where(sowing, xp.inf, state.pending_day)


def charge_formation(xp, tables: Tables, state: State, day: float) -> None:
    """Each year a perennial is still maturing, charge another formation cost."""
    due = xp.isfinite(state.formation_in) & (state.maturing_for > 0) & (state.formation_in <= 0)
    crop = crop_or_first(xp, state.crop)
    cash = formation_cash(xp, tables, crop, xp.minimum(DAYS_PER_YEAR, state.maturing_for))
    state.value = state.value + xp.where(due, cash / discount(tables, day), 0.0)
    state.priced = state.priced & ~(due & ~tables.formation_priced[crop])
    state.formation_in = state.formation_in + DAYS_PER_YEAR * due


def chooser(xp, tables: Tables, state: State, policy: Policy, rows, reform_rows, rng):
    """The scenario's way of choosing, as a function of (allowed, reform)."""
    if policy.sequence:
        sequence = xp.asarray(policy.sequence)
        return lambda allowed, reform: choose_from_sequence(xp, state, allowed, sequence)
    return lambda allowed, reform: choose_from_chain(
        xp, tables, state, allowed, reform, rows, reform_rows, rng.random(state.crop.shape[0]))


def simulate(xp, tables: Tables, policy: Policy, seed: int, count: int, keep: int = 0) -> dict:
    """Run `count` trajectories of one scenario. Returns arrays on the device of `xp`.

    `keep` trajectories are also recorded period by period, for animation.
    """
    from .backend import streams
    rng = streams(xp, seed, STREAMS)
    state = State(xp, tables, policy, count)
    climate = rng["environment"].integers(0, tables.rain_years.shape[0], (count, tables.horizon_years))
    low, high = tables.soil_delta_low[None, :], tables.soil_delta_high[None, :]
    soil_rate = low + rng["environment"].random((count, low.shape[1])) * (high - low)
    rows = sample_or_none(xp, rng["parameters"], tables, policy, count)
    choose = chooser(xp, tables, state, policy, *rows, rng["choice"])
    yearly = Recorder(xp, tables, state, count, keep)
    for period in range(tables.periods):
        year = min(tables.horizon_years - 1, int(period * tables.period_days // DAYS_PER_YEAR))
        rain = tables.rain_years[climate[:, year], period % tables.periods_per_year]
        day = round((period + 1) * tables.period_days, 9)
        advance_water(xp, tables, state, rain, rng["environment"].random(count))
        advance_soil(xp, tables, state, soil_rate)
        advance_clocks(tables, state)
        harvest(xp, tables, state, day)
        decide(xp, tables, state, day, choose)
        plant(xp, tables, state, day)
        charge_formation(xp, tables, state, day)
        yearly.record(period, state)
    return yearly.result(state, climate)


def sample_or_none(xp, rng, tables: Tables, policy: Policy, count: int):
    """Chain draws are only needed (and only consume the parameter stream) when the scenario follows the chain."""
    if policy.sequence:
        return None, None
    return markov.sample_rows(xp, rng, tables, count), markov.sample_reform_rows(xp, rng, tables, count)


class Recorder:
    """Collects the state at each year end for every trajectory, and each period for the first `keep`."""

    def __init__(self, xp, tables: Tables, state: State, count: int, keep: int):
        self.xp, self.tables, self.keep = xp, tables, min(keep, count)
        years = tables.horizon_years + 1
        self.crop = xp.empty((years, count), dtype=int)
        self.water_class = xp.empty((years, count), dtype=int)
        self.carbon = xp.empty((years, count))
        self.track = {name: xp.empty((tables.periods + 1, self.keep)) for name in ("crop", "water_fraction", "carbon", "value")}
        self._year(0, state)
        self._period(0, state)

    def _year(self, year: int, state: State) -> None:
        self.crop[year], self.water_class[year], self.carbon[year] = state.crop, state.water_class, state.carbon

    def _period(self, step: int, state: State) -> None:
        for name, row in self.track.items():
            row[step] = getattr(state, name)[: self.keep]

    def record(self, period: int, state: State) -> None:
        self._period(period + 1, state)
        if (period + 1) % self.tables.periods_per_year == 0:
            self._year((period + 1) // self.tables.periods_per_year, state)

    def result(self, state: State, climate) -> dict:
        return {"value": state.value, "priced": state.priced, "route": state.route, "crop": self.crop,
                "water_class": self.water_class, "carbon": self.carbon, "track": self.track,
                "climate": climate[: self.keep]}
