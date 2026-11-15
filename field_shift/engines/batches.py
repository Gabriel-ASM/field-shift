"""A scenario simulated in batches of trajectories, so a run can report progress.

Each batch is an ordinary `simulate` call with its own seed, derived from the run's seed and the batch index; the
batches are then joined on the trajectory axis before `summarize`. The same seed and batch size always give the
same batches, so a run is reproducible however it is driven (in one call or as a job polled for progress).
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .backend import to_numpy
from .monte_carlo import Policy, simulate
from .tables import Tables

BATCH = 10_000

TRAJECTORY_AXIS = {"value": 0, "priced": 0, "route": 0, "water_fraction": 0, "crop": 1, "water_class": 1, "carbon": 1}
PATH_AXIS = 1


def batch_sizes(count: int, batch: int = BATCH) -> list[int]:
    """Trajectories in each batch: full batches, then the rest."""
    return [batch] * (count // batch) + ([count % batch] if count % batch else [])


def batch_seed(seed: int, index: int) -> int:
    """Seed of batch `index` of a run with `seed`: independent streams, fixed by the pair."""
    return int(np.random.SeedSequence([seed, index]).generate_state(1)[0])


def on_host(result: dict) -> dict:
    """Copy a batch result to NumPy, so batches can be joined and the device memory freed."""
    host = {name: to_numpy(result[name]) for name in (*TRAJECTORY_AXIS, "crop_count", "climate")}
    host["track"] = {name: to_numpy(values) for name, values in result["track"].items()}
    host["paths"] = {name: to_numpy(values) for name, values in result["paths"].items()} if result["paths"] else None
    return host


def join(results: list[dict]) -> dict:
    """One result from consecutive batches. Tracks (animation) come from the first batch only."""
    joined = {name: np.concatenate([r[name] for r in results], axis=axis) for name, axis in TRAJECTORY_AXIS.items()}
    joined["crop_count"] = sum(r["crop_count"] for r in results)
    joined["track"], joined["climate"] = results[0]["track"], results[0]["climate"]
    paths = [r["paths"] for r in results]
    joined["paths"] = {name: np.concatenate([p[name] for p in paths], axis=PATH_AXIS) for name in paths[0]} if paths[0] else None
    return joined


def simulate_batches(xp, tables: Tables, policy: Policy, seed: int, count: int, keep: int = 0, paths: bool = False,
                     batch: int = BATCH, progress: Callable[[int], None] = lambda done: None) -> dict:
    """Run `count` trajectories batch by batch; `progress` gets the trajectories done after each batch."""
    results, done = [], 0
    for index, size in enumerate(batch_sizes(count, batch)):
        results.append(on_host(simulate(xp, tables, policy, batch_seed(seed, index), size, keep if index == 0 else 0, paths)))
        done += size
        progress(done)
    return join(results)
