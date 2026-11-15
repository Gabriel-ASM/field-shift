"""Choice of the next crop: the Markov chain of a profile, reweighted by water and soil.

All functions work on a batch of trajectories at once; arrays have one row per trajectory.
"""

from __future__ import annotations

from .tables import Tables


def sample_rows(xp, rng, tables: Tables, count: int):
    """Uncertain chain per trajectory: gamma draws of the PAM mass of every edge (Dirichlet rows, unnormalized)."""
    shape = xp.broadcast_to(tables.mass + tables.alpha, (count, *tables.mass.shape))
    return rng.standard_gamma(shape) * tables.edge


def sample_reform_rows(xp, rng, tables: Tables, count: int):
    """Same as sample_rows, for the choice made after a sugarcane field is reformed."""
    shape = xp.broadcast_to(tables.reform_mass + tables.alpha, (count, tables.reform_mass.shape[0]))
    return rng.standard_gamma(shape) * tables.reform_eligible


def water_factor(xp, tables: Tables, water_fraction):
    """Wetter soil than the reference favours crops with above-average Kc, drier soil the opposite."""
    alignment = xp.clip((water_fraction - tables.water_reference) / tables.water_span, -1, 1)
    return xp.exp(tables.water_coefficient * alignment[:, None] * tables.kc_choice[None, :])


def soil_factor(xp, tables: Tables, carbon):
    """Carbon-poor soil favours crops that build carbon."""
    deficit = xp.clip((tables.soil_reference - carbon) / tables.soil_span, 0, 1)
    return xp.exp(tables.soil_coefficient * deficit[:, None] * tables.soil_delta_mean[None, :] / 0.2)


def total_nitrogen_target(tables: Tables, carbon):
    """C:N target stock of total N for the current soil carbon, kg N/ha."""
    return tables.total_n_target_per_carbon * carbon


def nitrogen_factor(xp, tables: Tables, total_n, carbon):
    """A total-N stock below the C:N target favours crops with a positive N balance (cropEnvironmentalFactors)."""
    target = total_nitrogen_target(tables, carbon)
    deficit = xp.where(target > 0, xp.clip((target - total_n) / xp.maximum(target * tables.total_n_span, 1e-12), 0, 1), 0.0)
    return xp.exp(tables.total_n_coefficient * deficit[:, None] * tables.total_n_balance[None, :] / tables.total_n_scale)


def destination_weights(xp, tables: Tables, base, allowed, water_fraction, carbon, total_n):
    """Unnormalized probability of each destination, zero where it is not allowed."""
    environment = water_factor(xp, tables, water_fraction) * soil_factor(xp, tables, carbon) * nitrogen_factor(xp, tables, total_n, carbon)
    return base * environment * allowed


def draw(xp, weights, uniform):
    """Index drawn from each row of `weights`, using one uniform number per row."""
    cumulative = xp.cumsum(weights, axis=1)
    target = uniform * cumulative[:, -1]
    return xp.minimum((cumulative <= target[:, None]).sum(axis=1), weights.shape[1] - 1)


def probabilities(xp, tables: Tables, source: int, water_fraction: float, carbon: float, total_n: float | None = None):
    """Mean chain row of `source` under one water, carbon and total-N condition (no parameter uncertainty)."""
    total_n = tables.total_n_initial if total_n is None else total_n
    base = (tables.mass[source] + tables.alpha) * tables.eligible[source]
    weights = destination_weights(xp, tables, base[None, :], tables.eligible[source][None, :],
                                  xp.asarray([water_fraction]), xp.asarray([carbon]), xp.asarray([total_n]))[0]
    total = weights.sum()
    return weights / total if float(total) > 0 else weights
