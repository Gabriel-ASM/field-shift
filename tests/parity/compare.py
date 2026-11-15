"""Statistical comparison of the Python engine with the team's JS simulator.

    uv run python tests/parity/compare.py [trajectories] [seed]

Both sides draw their own random numbers, so the comparison is statistical: for each profile and starting crop,
the share of trajectories ending in each crop, the share of the most frequent routes and the mean present value.
A |z| above 4 is reported as a difference (the sample is large and the tests are many, so smaller z values are
expected by chance). The JS side is field_shift/front/analysis.js as embedded in docs/visualizacao.html.

Rules the engine has and the page does not yet are switched off here (not run any more: rollback to the tag parity-ok-2026-11-15 instead; the per-cycle total-N balance and the window-mean soil differ from the page on purpose):
(data/reference/soybean-repetition-soil.json) and the available-N balance
(model block of data/reference/nitrogen-balance.json).
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

from field_shift.engines.monte_carlo import Policy, simulate
from field_shift.engines.run import tables_for
from field_shift.engines.summary import decode_route

ROOT = Path(__file__).resolve().parents[2]
LIMIT_Z = 4.0
TOP_ROUTES = 8


def js_cases(count: int, seed: int) -> list[dict]:
    output = subprocess.run(["node", str(ROOT / "tests/parity/js_stats.cjs"), str(count), str(seed)],
                            check=True, capture_output=True, text=True).stdout
    return json.loads(output)


def shared_model(profile: str):
    """The engine's tables without the rules the page does not have."""
    return replace(tables_for(profile), repeat_carbon_penalty=np.zeros(2), nitrogen=None)


def python_case(profile: str, start: str, count: int, seed: int) -> dict:
    tables = shared_model(profile)
    names = [*tables.crops, "fallow"]
    result = simulate(np, tables, Policy(tables.crops.index(start)), seed, count)
    final = [names[c] for c in result["crop"][-1]]
    routes = [",".join(decode_route(int(key), names)) for key in result["route"]]
    values = result["value"][result["priced"]]
    return {"final_crop": counted(final), "routes": counted(routes), "priced": int(values.size),
            "value": {"mean": float(values.mean()), "sd": float(values.std(ddof=1))}}


def counted(labels: list[str]) -> dict[str, int]:
    keys, counts = np.unique(labels, return_counts=True)
    return dict(zip(keys.tolist(), counts.tolist()))


def share_z(a: int, n: int, b: int, m: int) -> float:
    """Two-proportion z statistic."""
    pooled = (a + b) / (n + m)
    spread = math.sqrt(max(pooled * (1 - pooled) * (1 / n + 1 / m), 1e-12))
    return (a / n - b / m) / spread


def mean_z(x: dict, nx: int, y: dict, ny: int) -> float:
    """Welch z statistic of two means."""
    return (x["mean"] - y["mean"]) / math.sqrt(x["sd"] ** 2 / nx + y["sd"] ** 2 / ny)


def share_rows(kind: str, js: dict, py: dict, n: int, keys) -> list[tuple]:
    return [(kind, key, js.get(key, 0) / n, py.get(key, 0) / n, share_z(js.get(key, 0), n, py.get(key, 0), n))
            for key in keys]


def compare(js: dict, py: dict) -> list[tuple]:
    n = js["count"]
    finals = sorted(set(js["final_crop"]) | set(py["final_crop"]))
    top = sorted(js["routes"], key=lambda key: -js["routes"][key])[:TOP_ROUTES]
    rows = share_rows("final", js["final_crop"], py["final_crop"], n, finals)
    rows += share_rows("route", js["routes"], py["routes"], n, top)
    rows.append(("priced", "share", js["priced"] / n, py["priced"] / n, share_z(js["priced"], n, py["priced"], n)))
    rows.append(("value", "mean BRL/ha", js["value"]["mean"], py["value"]["mean"],
                 mean_z(js["value"], js["priced"], py["value"], py["priced"])))
    return rows


def report(case: dict, rows: list[tuple]) -> int:
    print(f"\n{case['profile']} from {case['start']} ({case['count']} trajectories per side)")
    differences = 0
    for kind, key, js, py, z in rows:
        flag = "  <-- differs" if abs(z) > LIMIT_Z else ""
        differences += bool(flag)
        number = (lambda v: f"{v:12.1f}") if kind == "value" else (lambda v: f"{100 * v:11.2f}%")
        print(f"  {kind:6} {key[:60]:60} js {number(js)}  py {number(py)}  z {z:6.1f}{flag}")
    return differences


def main(count: int = 20000, seed: int = 2026) -> int:
    differences = 0
    for case in js_cases(count, seed):
        py = python_case(case["profile"], case["start"], count, seed)
        differences += report(case, compare(case, py))
    print(f"\n{differences} statistic(s) with |z| > {LIMIT_Z}")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main(*map(int, sys.argv[1:3])))
