"""Turn the arrays of a simulated scenario into numbers a client can chart."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .backend import to_numpy
from .tables import WATER_STATES, Tables

TAIL = 0.05
QUANTILES = (0.05, 0.5, 0.95)
BINS = 120              # histogram of a route's present values, for the return distribution chart
TOP_ROUTES = 40         # most frequent routes always listed, recommendable or not
CARBON_CLASSES = ("low", "medium", "high")


@dataclass(frozen=True)
class Support:
    """Priced trajectories a route needs to be ranked, and to be recommended (visualization-run-settings.json)."""
    ranked: int
    recommended: int


def value_summary(values: np.ndarray) -> dict | None:
    """Present value in BRL/ha: mean, quantiles and the mean of the worst 5% (CVaR)."""
    if values.size == 0:
        return None
    ordered = np.sort(values)
    p5, p50, p95 = np.quantile(ordered, QUANTILES)
    return {"mean": float(ordered.mean()), "p5": float(p5), "p50": float(p50), "p95": float(p95),
            "cvar5": float(tail_mean(ordered)), "count": int(ordered.size),
            "loss_probability": float((ordered < 0).mean())}


def tail_mean(ordered: np.ndarray) -> float:
    """Mean of the lowest 5% (at least one value) of sorted values."""
    return float(ordered[: max(1, int(np.ceil(TAIL * ordered.size)))].mean())


def distribution(values: np.ndarray) -> dict:
    """Fixed-bin histogram of present values, with the spread statistics the chart's smoothing uses
    (standard deviation and quartiles, as renderReturnChart in producer.js computes them)."""
    low, high = float(values.min()), float(values.max())
    width = (high - low) / BINS
    counts = np.histogram(values, bins=BINS, range=(low, high))[0] if width > 0 else np.array([values.size])
    q25, q75 = np.quantile(values, (0.25, 0.75))
    return {"start": low, "width": width, "counts": counts.tolist(), "sd": float(values.std()),
            "q25": float(q25), "q75": float(q75)}


def shares(labels: np.ndarray, size: int) -> list[float]:
    return (np.bincount(labels, minlength=size) / labels.size).round(6).tolist()


def occupancy(crop_count: np.ndarray, names: list[str]) -> list[dict[str, float]]:
    """Per period, the share of trajectories in each crop. Counts come with fallow first; names have it last."""
    ordered = np.roll(crop_count, -1, axis=1) / crop_count.sum(axis=1, keepdims=True)
    return [{name: share for name, share in zip(names, row) if share > 0} for row in ordered.round(6).tolist()]


def decode_route(key: int, names: list[str]) -> list[str]:
    """Crops planted, in order, from the base-(crops+1) route key built by the engine."""
    crops = []
    while key > 0:
        key, digit = divmod(key, len(names))
        crops.append(names[digit - 1])
    return crops[::-1]


def yield_penalties(crops: list[str], tables: Tables) -> list[float]:
    """Yield lost at each planting's harvest by replanting the same crop (repeated_crop_effect), as the result page of
    producer.js shows it. The available-N response comes on top of it and varies by trajectory, so it is not here."""
    penalties, streak = [], 0
    for index, crop in enumerate(crops):
        streak = streak + 1 if index and crop == crops[index - 1] else 1
        if crop not in tables.crops:
            penalties.append(0.0)
            continue
        i = tables.crops.index(crop)
        multiplier = max(float(tables.repeat_floor[i]), 1 - (streak - 1) * float(tables.repeat_penalty[i]))
        penalties.append(round(1 - multiplier, 6))
    return penalties


def carbon_class(tables: Tables, carbon: float) -> str:
    limits = to_numpy(tables.carbon_class_limits)
    return CARBON_CLASSES[int(carbon >= limits[0]) + int(carbon >= limits[1])]


def final_state(result: dict, tables: Tables) -> dict:
    """Per trajectory, the state at the end of the horizon."""
    water_class = to_numpy(result["water_class"])[-1]
    return {"carbon": to_numpy(result["carbon"])[-1], "water_class": water_class,
            "water_fraction": to_numpy(result["water_fraction"]), "total_nitrogen": to_numpy(result["total_nitrogen"]),
            "water_multiplier": to_numpy(tables.water_yield)[water_class]}


def route_summary(crops: list[str], members: np.ndarray, priced: np.ndarray, value: np.ndarray, final: dict,
                  total: int, tables: Tables, support: Support) -> dict:
    """One crop sequence: its share, present values, final soil and water, and yield losses by planting."""
    values = value[members[priced[members]]]
    summary = value_summary(values)
    if summary and values.size >= support.recommended:
        summary["distribution"] = distribution(values)
    carbon = float(final["carbon"][members].mean())
    return {"crops": crops, "share": float(members.size / total), "trajectories": int(members.size), "value": summary,
            "final_carbon": carbon, "final_carbon_class": carbon_class(tables, carbon),
            "final_water_multiplier": float(final["water_multiplier"][members].mean()),
            "final_water": dict(zip(WATER_STATES, shares(final["water_class"][members], 3))),
            "final_water_fraction": float(final["water_fraction"][members].mean()),
            "final_total_nitrogen": float(final["total_nitrogen"][members].mean()),
            "yield_penalty": yield_penalties(crops, tables)}


def groups(route: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
    """Distinct route keys, and the trajectory indices of each."""
    keys, inverse = np.unique(route, return_inverse=True)
    order = np.argsort(inverse, kind="stable")
    bounds = np.cumsum(np.bincount(inverse, minlength=keys.size))[:-1]
    return keys, np.split(order, bounds)


def routes(route: np.ndarray, value: np.ndarray, priced: np.ndarray, final: dict, tables: Tables,
           support: Support) -> tuple[list[dict], dict | None]:
    """The most frequent routes plus every route that can be recommended, and the money reference of the ranking:
    CVaR5 and P95 of all priced trajectories in routes that can be ranked (analysis.js, referenceCvar5/referenceP95)."""
    names = [*tables.crops, "fallow"]
    keys, members = groups(route)
    frequency = np.array([m.size for m in members])
    priced_count = np.array([int(priced[m].sum()) for m in members])
    listed = set(np.argsort(-frequency, kind="stable")[:TOP_ROUTES].tolist()) | set(np.flatnonzero(priced_count >= support.recommended).tolist())
    ordered = sorted(listed, key=lambda i: (-frequency[i], int(keys[i])))
    summaries = [route_summary(decode_route(int(keys[i]), names), members[i], priced, value, final, route.size, tables, support)
                 for i in ordered]
    rankable = [members[i][priced[members[i]]] for i in np.flatnonzero(priced_count >= support.ranked)]
    pooled = np.sort(value[np.concatenate(rankable)]) if rankable else np.array([])
    reference = ({"cvar5": tail_mean(pooled), "p95": float(np.quantile(pooled, 0.95)), "count": int(pooled.size),
                  "routes": len(rankable)} if pooled.size else None)
    return summaries, reference


def tracks(track: dict, climate: np.ndarray, tables: Tables, names: list[str]) -> list[dict]:
    """Trajectories recorded period by period, for animation. `cane_cut` is the next cut of the cane in the field,
    0 when the field holds another crop or none."""
    crop = to_numpy(track["crop"]).astype(int)
    series = {name: to_numpy(track[name]) for name in ("water_fraction", "carbon", "value")}
    cut = np.where(crop == tables.sugarcane, to_numpy(track["cane_cut"]), 0).astype(int)
    years = to_numpy(climate)
    return [{"crop": [names[c] for c in crop[:, i]],
             "climate_years": [tables.climate_years[y] for y in years[i]],
             "cane_cut": cut[:, i].tolist(),
             **{name: values[:, i].round(4).tolist() for name, values in series.items()}}
            for i in range(crop.shape[1])]


def summarize(result: dict, tables: Tables, support: Support) -> dict:
    names = [*tables.crops, "fallow"]
    value, priced = to_numpy(result["value"]), to_numpy(result["priced"])
    carbon, water_class = to_numpy(result["carbon"]), to_numpy(result["water_class"])
    final = final_state(result, tables)
    route_list, reference = routes(to_numpy(result["route"]), value, priced, final, tables, support)
    return {
        "trajectories": int(value.size),
        "priced_share": float(priced.mean()),
        "value": value_summary(value[priced]),
        "occupancy": occupancy(to_numpy(result["crop_count"]), names),
        "water": [dict(zip(WATER_STATES, shares(year, 3))) for year in water_class],
        "carbon": [dict(zip(("p5", "p50", "p95"), np.quantile(year, QUANTILES).round(4).tolist())) for year in carbon],
        "final_carbon": float(final["carbon"].mean()),
        "final_water_multiplier": float(final["water_multiplier"].mean()),
        "routes": route_list,
        "ranking_reference": reference,
        "tracks": tracks(result["track"], result["climate"], tables, names),
    }


ROUTE_TRACKS = 40      # trajectories of one route shown as strips


def route_key(crops: list[str], names: list[str]) -> int:
    """Inverse of decode_route."""
    key = 0
    for crop in crops:
        key = key * len(names) + names.index(crop) + 1
    return key


def class_counts(codes: np.ndarray, classes: int = 3) -> list[list[int]]:
    """Per period (rows of `codes`), how many trajectories are in each class."""
    return np.stack([(codes == c).sum(axis=1) for c in range(classes)], axis=1).tolist()


def route_tracks(paths: dict, members: np.ndarray, names: list[str]) -> list[dict]:
    """The first trajectories of a route, period by period: crop and cane cut."""
    shown = members[:ROUTE_TRACKS]
    crop, cut = paths["crop"][:, shown].astype(int), paths["cane_cut"][:, shown].astype(int)
    fallow = len(names) - 1
    return [{"crop": [names[c - 1] if c > 0 else names[fallow] for c in crop[:, i]], "cane_cut": cut[:, i].tolist()}
            for i in range(shown.size)]


def route_detail(raw: dict, tables: Tables, crops: list[str]) -> dict | None:
    """Everything the result view shows about one route besides its summary: water and soil class counts every
    period, water shares and carbon quantiles at each year end, and some of its trajectories. None if no trajectory
    followed it."""
    names = [*tables.crops, "fallow"]
    if any(crop not in names for crop in crops):
        return None
    members = np.flatnonzero(raw["route"] == route_key(crops, names))
    if members.size == 0:
        return None
    environment = raw["paths"]["environment"][:, members]
    carbon, water_class = raw["carbon"][:, members], raw["water_class"][:, members]
    return {
        "crops": crops, "trajectories": int(members.size),
        "frames": {"water": class_counts(environment % 3), "soil": class_counts((environment // 3) % 3),
                   "nitrogen": class_counts(environment // 9)},
        "water": [dict(zip(WATER_STATES, shares(year, 3))) for year in water_class],
        "carbon": [dict(zip(("p5", "p50", "p95"), np.quantile(year, QUANTILES).round(4).tolist())) for year in carbon],
        "tracks": route_tracks(raw["paths"], members, names),
    }
