"""Numeric tables of one profile, indexed by crop, ready for vectorized simulation.

Everything the Monte Carlo needs is looked up here by integer crop index, so a run never touches a dict.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields, replace

import numpy as np

from .calendar import DAYS_PER_YEAR, days_until_open, planting_windows

WATER_STATES = ("water_low", "water_medium", "water_high")
RAIN_LABELS = ("dry", "normal", "wet")
ANNUAL_CLASSES = ("annual", "cover_or_annual")
DEFAULT_FORMATION_SHARE = 0.55
FALLOW = -1


@dataclass(frozen=True)
class Tables:
    crops: tuple[str, ...]
    sugarcane: int                  # crop index, or -2 when the profile has no sugarcane
    sugarcane_cuts: float           # harvests before the field is reformed
    period_days: float
    periods_per_year: int
    horizon_years: int
    # crop clock
    cycle_days: np.ndarray          # (C,)
    maturation_days: np.ndarray     # (C,)
    perennial: np.ndarray           # (C,) bool
    repeat_penalty: np.ndarray      # (C,) yield loss per consecutive replanting
    repeat_floor: np.ndarray        # (C,) lowest yield multiplier from replanting
    # choice
    mass: np.ndarray                # (C, C) PAM mass of each edge
    reform_mass: np.ndarray         # (C,) PAM mass out of sugarcane, used after reform
    alpha: float
    edge: np.ndarray                # (C, C) bool, edge exists in the chain
    eligible: np.ndarray            # (C, C) bool, edge exists and the destination has a planting window
    reform_eligible: np.ndarray     # (C,) bool
    opportunity_wait: np.ndarray    # (C, 365) days until some destination of the source can be planted
    window_wait: np.ndarray         # (C, 365) days until the crop itself can be planted
    kc_choice: np.ndarray           # (C,) Kc minus the mean Kc
    soil_delta_mean: np.ndarray     # (C,)
    water_reference: float
    water_span: float
    water_coefficient: float
    soil_reference: float
    soil_span: float
    soil_coefficient: float
    # environment
    water_counts: np.ndarray        # (3 from, 3 rain, 3 to)
    rain_years: np.ndarray          # (Y, periods_per_year) rain label index
    climate_years: tuple[int, ...]
    water_fraction_of: np.ndarray   # (3,) representative fraction of each water class
    water_class_limits: np.ndarray  # (2,) upper bounds of low and medium
    demand_shift: np.ndarray        # (C,) fraction of AWC used per period above the reference Kc
    soil_delta_low: np.ndarray      # (C,) g/kg per year
    soil_delta_high: np.ndarray     # (C,)
    initial_water: float
    initial_carbon: float
    # economics
    yield_tonnes: np.ndarray        # (C,) t/ha
    price: np.ndarray               # (C,) BRL/t today
    price_trend: np.ndarray         # (C,) per year
    cost: np.ndarray                # (C,) BRL/ha per cycle
    formation_share: np.ndarray     # (C,) share of the cost charged per year while a perennial forms
    harvest_priced: np.ndarray      # (C,) bool, harvest cash flow can be computed
    formation_priced: np.ndarray    # (C,) bool
    water_yield: np.ndarray         # (3,) yield multiplier per water class
    carbon_yield: np.ndarray        # (3,) yield multiplier per soil carbon class
    carbon_class_limits: np.ndarray  # (2,)
    discount_rate: float

    @property
    def periods(self) -> int:
        return self.horizon_years * self.periods_per_year

    def on(self, xp) -> "Tables":
        """Copy with every array moved to the array module `xp` (numpy or cupy)."""
        arrays = {f.name: xp.asarray(getattr(self, f.name)) for f in fields(self)
                  if isinstance(getattr(self, f.name), np.ndarray)}
        return replace(self, **arrays)


def _number(value, default=math.nan) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _per_crop(crops, value_of, dtype=float) -> np.ndarray:
    return np.array([value_of(crop) for crop in crops], dtype=dtype)


def _round_up_to_period(days: float, period: float) -> float:
    return max(period, math.ceil(days / period) * period)


def _clock(crops, crop_cycles, lifecycle, period) -> dict:
    rules = crop_cycles["crops"]
    rule = lambda crop: rules.get(crop) or {"cycle_days": 365, "maturation_days": 365}
    effect = crop_cycles.get("repeated_crop_effect") or {}
    applies = lambda crop: rule(crop).get("class") in (effect.get("applies_to_classes") or [])
    specific = lambda crop: (effect.get("crop_specific") or {}).get(crop) or effect
    penalty = lambda crop: max(0.0, _number(specific(crop).get("yield_penalty_per_consecutive_replant_fraction"), 0.0))
    cap = lambda crop: min(1.0, max(0.0, _number(specific(crop).get("maximum_yield_penalty_fraction"), 0.0)))
    return {
        "cycle_days": _per_crop(crops, lambda c: _round_up_to_period(float(rule(c)["cycle_days"]), period)),
        "maturation_days": _per_crop(crops, lambda c: _round_up_to_period(float(rule(c)["maturation_days"]), period)),
        "perennial": _per_crop(crops, lambda c: bool(lifecycle.get(c)), bool),
        "repeat_penalty": _per_crop(crops, lambda c: penalty(c) if applies(c) else 0.0),
        "repeat_floor": _per_crop(crops, lambda c: 1.0 - cap(c) if applies(c) else 1.0),
        "sugarcane_cuts": _number(rule("sugarcane").get("modeled_harvest_cuts")),
    }


def _calendar(crops, chain, windows, crop_cycles, lifecycle) -> dict:
    index = {crop: i for i, crop in enumerate(crops)}
    size = len(crops)
    mass, edge = np.zeros((size, size)), np.zeros((size, size), bool)
    for row in chain["transitions"]:
        mass[index[row["from"]], index[row["to"]]] = _number(row.get("mass"), 0.0)
        edge[index[row["from"]], index[row["to"]]] = True
    has_window = _per_crop(crops, lambda c: bool(windows.get(c)), bool)
    persistent = _per_crop(crops, lambda c: (lifecycle.get(c) or {}).get("mode") == "persistent_within_horizon", bool)
    annual = _per_crop(crops, lambda c: (crop_cycles["crops"].get(c) or {}).get("class") in ANNUAL_CLASSES, bool)
    reform_eligible = annual & has_window
    eligible = np.where(persistent[:, None], edge, edge & has_window[None, :])
    targets = edge.copy()
    if "sugarcane" in index:
        targets[index["sugarcane"]] = reform_eligible
    opportunity = [set().union(*(windows.get(crops[j], set()) for j in np.flatnonzero(targets[i]))) for i in range(size)]
    return {
        "mass": mass, "edge": edge, "eligible": eligible, "reform_eligible": reform_eligible,
        "reform_mass": _per_crop(crops, lambda c: _number(chain["sugarcane_reform_pam_mass"].get(c), 0.0)),
        "alpha": float(chain["alpha_per_destination"]),
        "opportunity_wait": np.stack([days_until_open(decendios) for decendios in opportunity]),
        "window_wait": np.stack([days_until_open(windows.get(crop, set())) for crop in crops]),
    }


def _choice(crops, states, hypotheses) -> dict:
    params, kc = hypotheses["probability_modifiers"], _per_crop(crops, lambda c: _number(states[c].get("kc_annual_effective")))
    mean_kc = float(np.nanmean(kc)) if np.isfinite(kc).any() else 0.0
    ranges = hypotheses["soil_carbon"]["delta_by_crop"]
    return {
        "kc_choice": np.where(np.isfinite(kc), kc, mean_kc) - mean_kc,
        "soil_delta_mean": _per_crop(crops, lambda c: sum(map(float, ranges.get(c, (0, 0)))) / 2),
        "soil_delta_low": _per_crop(crops, lambda c: float(ranges.get(c, (0, 0))[0])),
        "soil_delta_high": _per_crop(crops, lambda c: float(ranges.get(c, (0, 0))[1])),
        "water_reference": _number(params.get("water_reference_fraction"), 0.5),
        "water_span": _number(params.get("water_span_fraction"), 0.3),
        "water_coefficient": float(params["water_log_weight_coefficient"]),
        "soil_reference": float(params["soil_carbon_reference_g_kg"]),
        "soil_span": float(params["soil_carbon_deficit_span_g_kg"]),
        "soil_coefficient": float(params["soil_log_weight_coefficient"]),
    }


def _water(crops, states, payload, hypotheses) -> dict:
    model, params = payload["water_markov"], hypotheses["probability_modifiers"]
    counts = np.zeros((3, 3, 3))
    for row in model["transitions"]:
        source, rain = WATER_STATES.index(row["from"]), RAIN_LABELS.index(row["environment"])
        counts[source, rain] = [float(row["counts"].get(state, 0)) for state in WATER_STATES]
    years = {int(year): labels for year, labels in model["environment_years"].items()
             if isinstance(labels, list) and len(labels) == model["periods_per_year"]}
    reference_kc = float(params["water_reference_kc"])
    kc = _per_crop(crops, lambda c: _number(states[c].get("kc_annual_effective"), reference_kc))
    eto_per_period = float(payload["climate_summary"]["mean_annual_eto_mm"]) / model["periods_per_year"]
    capacity = max(1.0, float(payload["soil"]["available_water_capacity_mm"]))
    limits = payload["water_classes"]
    return {
        "water_counts": counts,
        "rain_years": np.array([[RAIN_LABELS.index(label) for label in years[year]] for year in sorted(years)]),
        "climate_years": tuple(sorted(years)),
        "water_fraction_of": np.array([float(params["water_state_representative_fraction"].get(s, 0.5)) for s in WATER_STATES]),
        "water_class_limits": np.array([float(limits["low_max_inclusive"]), float(limits["medium_max_inclusive"])]),
        "demand_shift": (kc - reference_kc) * eto_per_period / capacity,
        "initial_water": float(model["initial_storage_fraction"]),
        "initial_carbon": float(payload["soil"]["organic_carbon_top_0_30_g_kg"]),
    }


def _economics(crops, payload, hypotheses, crop_cycles) -> dict:
    economics, response = payload["economics"], hypotheses["economic_yield_response"]
    inputs = economics.get("crop_inputs") or {}
    entry = lambda crop: inputs.get(crop) or {}
    selected = _per_crop(crops, lambda c: bool(entry(c).get("include_in_vpl", entry(c).get("eligible_for_economic_comparison"))), bool)
    yields = _per_crop(crops, lambda c: _number(entry(c).get("yield_kg_ha_median_2021_2025")) / 1000)
    price = _per_crop(crops, lambda c: _number((entry(c).get("price") or {}).get("brl_per_tonne")))
    cost = _per_crop(crops, lambda c: _number((entry(c).get("cost_panel") or {}).get("total_cost_brl_ha_reference_month")))
    formation = crop_cycles.get("new_perennial_formation") or {}
    thresholds = hypotheses["soil_carbon"]["state_thresholds_g_kg"]
    priced = selected & np.isfinite(cost)
    return {
        "yield_tonnes": np.nan_to_num(yields), "price": np.nan_to_num(price), "cost": np.nan_to_num(cost),
        "price_trend": _per_crop(crops, lambda c: _number((entry(c).get("price") or {}).get("trend_annual_fraction"), 0.0)),
        "formation_share": _per_crop(crops, lambda c: _number(formation.get(f"{c}_annual_formation_cost_fraction"), DEFAULT_FORMATION_SHARE)),
        "harvest_priced": priced & np.isfinite(yields) & np.isfinite(price),
        "formation_priced": priced,
        "water_yield": np.array([float(response["water_multiplier_by_class"][state]) for state in WATER_STATES]),
        "carbon_yield": np.array([float(response["soil_carbon_multiplier_by_class"][k]) for k in ("low", "medium", "high")]),
        "carbon_class_limits": np.array([float(thresholds["low_max_exclusive"]), float(thresholds["medium_max_exclusive"])]),
        "discount_rate": float(economics["discount_rate"]["real_annual_rate_approx"]),
    }


def build_tables(payload: dict, reference: dict) -> Tables:
    """Turn the payload of one profile and the shared assumptions into lookup tables."""
    chain, hypotheses, crop_cycles = payload["crop_markov"], reference["soil_hypotheses"], reference["crop_cycles"]
    states = {state["id"]: state for state in chain["states"]}
    crops, basis = tuple(states), crop_cycles["time_basis"]
    lifecycle = chain.get("lifecycle_rules") or {}
    period = float(basis["days_per_year"]) / int(basis["environment_periods_per_year"])
    if int(basis["days_per_year"]) != DAYS_PER_YEAR:
        raise ValueError("the planting calendar assumes a 365-day year")
    windows = planting_windows((payload.get("zarc_planting_windows") or {}).get("rows") or [], list(crops), crop_cycles)
    return Tables(
        crops=crops, sugarcane=crops.index("sugarcane") if "sugarcane" in crops else -2,
        period_days=period, periods_per_year=int(basis["environment_periods_per_year"]),
        horizon_years=int(basis["horizon_months"]) // 12,
        **_clock(crops, crop_cycles, lifecycle, period),
        **_calendar(crops, chain, windows, crop_cycles, lifecycle),
        **_choice(crops, states, hypotheses),
        **_water(crops, states, payload, hypotheses),
        **_economics(crops, payload, hypotheses, crop_cycles),
    )
