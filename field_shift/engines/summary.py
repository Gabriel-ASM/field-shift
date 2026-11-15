"""Turn the arrays of a simulated scenario into numbers a client can chart."""

from __future__ import annotations

import numpy as np

from .backend import to_numpy
from .tables import WATER_STATES, Tables

TAIL = 0.05
QUANTILES = (0.05, 0.5, 0.95)


def value_summary(values: np.ndarray) -> dict | None:
    """Present value in BRL/ha: mean, quantiles and the mean of the worst 5% (CVaR)."""
    if values.size == 0:
        return None
    ordered = np.sort(values)
    p5, p50, p95 = np.quantile(ordered, QUANTILES)
    worst = ordered[: max(1, int(np.ceil(TAIL * ordered.size)))]
    return {"mean": float(ordered.mean()), "p5": float(p5), "p50": float(p50), "p95": float(p95),
            "cvar5": float(worst.mean()), "count": int(ordered.size)}


def shares(labels: np.ndarray, size: int) -> list[float]:
    return (np.bincount(labels, minlength=size) / labels.size).round(6).tolist()


def occupancy(crop: np.ndarray, names: list[str]) -> list[dict[str, float]]:
    """Per year, the share of trajectories in each crop. Fallow is the last name."""
    rows = [shares(np.where(year < 0, len(names) - 1, year), len(names)) for year in crop]
    return [{name: share for name, share in zip(names, row) if share > 0} for row in rows]


def decode_route(key: int, names: list[str]) -> list[str]:
    """Crops planted, in order, from the base-(crops+1) route key built by the engine."""
    crops = []
    while key > 0:
        key, digit = divmod(key, len(names))
        crops.append(names[digit - 1])
    return crops[::-1]


def routes(route: np.ndarray, value: np.ndarray, priced: np.ndarray, names: list[str], limit: int) -> list[dict]:
    """The most frequent crop sequences, each with its share and present-value summary."""
    keys, inverse, counts = np.unique(route, return_inverse=True, return_counts=True)
    top = np.argsort(-counts)[:limit]
    return [{"crops": decode_route(int(keys[i]), names), "share": float(counts[i] / route.size),
             "value": value_summary(value[(inverse == i) & priced])} for i in top]


def tracks(track: dict, climate: np.ndarray, tables: Tables, names: list[str]) -> list[dict]:
    """Trajectories recorded period by period, for animation."""
    crop = to_numpy(track["crop"]).astype(int)
    series = {name: to_numpy(track[name]) for name in ("water_fraction", "carbon", "value")}
    years = to_numpy(climate)
    return [{"crop": [names[c] for c in crop[:, i]],
             "climate_years": [tables.climate_years[y] for y in years[i]],
             **{name: values[:, i].round(4).tolist() for name, values in series.items()}}
            for i in range(crop.shape[1])]


def summarize(result: dict, tables: Tables, route_limit: int = 10) -> dict:
    names = [*tables.crops, "fallow"]
    value, priced = to_numpy(result["value"]), to_numpy(result["priced"])
    crop, carbon = to_numpy(result["crop"]), to_numpy(result["carbon"])
    return {
        "trajectories": int(value.size),
        "priced_share": float(priced.mean()),
        "value": value_summary(value[priced]),
        "occupancy": occupancy(crop, names),
        "water": [dict(zip(WATER_STATES, shares(year, 3))) for year in to_numpy(result["water_class"])],
        "carbon": [dict(zip(("p5", "p50", "p95"), np.quantile(year, QUANTILES).round(4).tolist())) for year in carbon],
        "routes": routes(to_numpy(result["route"]), value, priced, names, route_limit),
        "tracks": tracks(result["track"], result["climate"], tables, names),
    }

