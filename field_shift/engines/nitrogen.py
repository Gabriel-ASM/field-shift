"""Soil nitrogen balance: N(t+1) = N + fixation + fertilizer - removal - losses, in kg N/ha.

This is variable A03 of the team's model design. With it, what a crop leaves or takes changes the yield of
the next one, which is what rewards rotation over repeating the same crop. It replaces the fixed
repeated-crop penalty whenever a profile has nitrogen parameters; without them the engine keeps the penalty.

All functions work on a batch of trajectories; `crop` is an array of crop indices.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

import numpy as np


@dataclass(frozen=True)
class Nitrogen:
    initial: float                  # kg N/ha available at the start
    credit: np.ndarray              # (C,) kg N/ha left in the soil by one cycle (legume fixation, cover residue)
    fertilizer: np.ndarray          # (C,) kg N/ha applied at planting
    removal: np.ndarray             # (C,) kg N taken away per tonne harvested
    demand: np.ndarray              # (C,) kg N/ha needed for full yield; 0 for crops that fix their own
    floor: np.ndarray               # (C,) yield multiplier when no nitrogen is available
    loss_fraction: np.ndarray       # (3,) share of the available N lost per period, by rain class

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


def after_harvest(xp, params: Nitrogen, crop, available, harvested_tonnes):
    """Available N after a harvest: the crop's credit comes in, the N in the product goes out."""
    return xp.maximum(0.0, available + params.credit[crop] - params.removal[crop] * harvested_tonnes)


def after_planting(params: Nitrogen, crop, available):
    return available + params.fertilizer[crop]
