"""Available soil nitrogen: N(t+1) = N + mineralization + fertilizer + fixation - removal - losses, in kg N/ha.

This is variable A03 of the team's model design. With it, what a crop leaves or takes changes the yield of the
next one that responds to N. Parameters come from the `model` block of data/reference/nitrogen-balance.json;
crops with no sourced number are neutral (no input, no removal, full yield).

All functions work on a batch of trajectories; `crop` is an array of crop indices.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

import numpy as np


@dataclass(frozen=True)
class Nitrogen:
    initial: float                  # kg N/ha available at the start
    credit: np.ndarray              # (C,) kg N/ha fixed in one cycle and left in the field at harvest
    fertilizer: np.ndarray          # (C,) lowest kg N/ha applied at planting
    fertilizer_high: np.ndarray     # (C,) highest; each trajectory draws its dose in between
    removal: np.ndarray             # (C,) kg N taken away per tonne harvested
    demand: np.ndarray              # (C,) kg N/ha available for full yield; 0 for crops with no N response
    floor: np.ndarray               # (C,) yield multiplier when no nitrogen is available
    loss_fraction: np.ndarray       # (3,) share of the available N lost per period, by rain class
    fertilizer_loss: float = 0.0    # share of the applied N lost at once (ammonia volatilization)
    mineralization: float = 0.0     # share of the total N stock made available per year

    def on(self, xp) -> "Nitrogen":
        arrays = {f.name: xp.asarray(getattr(self, f.name)) for f in fields(self)
                  if isinstance(getattr(self, f.name), np.ndarray)}
        return replace(self, **arrays)


def yield_multiplier(xp, params: Nitrogen, crop, available):
    """Linear-plateau response: full yield once the available N meets the crop's demand."""
    demand = params.demand[crop]
    supplied = xp.where(demand > 0, xp.minimum(1.0, available / xp.maximum(demand, 1e-9)), 1.0)
    return params.floor[crop] + (1 - params.floor[crop]) * supplied


def after_losses(params: Nitrogen, available, rain):
    """Available N after one period of leaching and gaseous losses, which grow with rain."""
    return available * (1 - params.loss_fraction[rain])


def after_mineralization(params: Nitrogen, available, total_n, years: float):
    """Available N after the organic N of the total stock mineralizes for `years`."""
    return available + params.mineralization * total_n * years


def after_harvest(xp, params: Nitrogen, crop, available, harvested_tonnes):
    """Available N after a harvest: the fixed N comes in, the N in the product goes out."""
    return xp.maximum(0.0, available + params.credit[crop] - params.removal[crop] * harvested_tonnes)


def dose(params: Nitrogen, crop, draw):
    """Fertilizer applied at planting, kg N/ha, for a draw in [0, 1)."""
    low = params.fertilizer[crop]
    return low + draw * (params.fertilizer_high[crop] - low)


def after_planting(params: Nitrogen, crop, available, draw=0.0):
    return available + dose(params, crop, draw) * (1 - params.fertilizer_loss)
