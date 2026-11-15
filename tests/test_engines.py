import numpy as np
import pytest

from field_shift.engines import markov
from field_shift.engines.calendar import DECENDIO_BY_DAY, days_until_open, decendio_of_day
from field_shift.engines.monte_carlo import Policy, simulate
from field_shift.engines.run import RunError, run, tables_for
from field_shift.engines.summary import decode_route, value_summary

REQUEST = {"seed": 2026, "trajectories": 4000, "horizon_days": 1825, "profile": "franca-sp", "scenarios": [
    {"id": "region", "policy": {"kind": "markov"}},
    {"id": "soy-maize", "policy": {"kind": "rotation", "sequence": ["soybean", "maize_grain"], "fallback": "fallow:skip_stages"}},
]}


@pytest.fixture(scope="module")
def tables():
    return tables_for("franca-sp")


def test_decendios_split_each_month_in_three():
    assert [decendio_of_day(day) for day in (0, 9, 10, 20, 30, 31, 364)] == [1, 1, 2, 3, 3, 4, 36]
    assert np.bincount(DECENDIO_BY_DAY)[1:].tolist()[:3] == [10, 10, 11]


def test_wait_for_a_window_wraps_around_the_year():
    wait = days_until_open({1})
    assert wait[0] == 0 and wait[9] == 0 and wait[10] == 355 and wait[364] == 1
    assert np.isinf(days_until_open(set())).all()


def test_chain_row_only_goes_to_destinations_with_edge_and_window(tables):
    soybean = tables.crops.index("soybean")
    row = markov.probabilities(np, tables, soybean, 0.5, tables.initial_carbon)
    assert row.sum() == pytest.approx(1) and (row[~tables.eligible[soybean]] == 0).all()


def test_same_seed_same_result_and_other_seed_differs(tables):
    policy = Policy(tables.crops.index("soybean"))
    first, again, other = (simulate(np, tables, policy, seed, 500) for seed in (1, 1, 2))
    assert (first["value"] == again["value"]).all() and (first["route"] == again["route"]).all()
    assert (first["value"] != other["value"]).any()


def test_scenarios_share_the_environment(tables):
    """Common random numbers: the climate years drawn do not depend on what the scenario chooses."""
    soybean, maize = tables.crops.index("soybean"), tables.crops.index("maize_grain")
    chain = simulate(np, tables, Policy(soybean), 7, 300, keep=300)
    rotation = simulate(np, tables, Policy(soybean, (soybean, maize)), 7, 300, keep=300)
    assert (chain["climate"] == rotation["climate"]).all()


def test_fixed_rotation_plants_its_sequence(tables):
    result = run({**REQUEST, "trajectories": 200}, "soybean:skip_stages", "cpu", tracks=1)
    rotation = result["scenarios"][1]
    assert rotation["initial_crop"] == "soybean" and len(rotation["routes"]) == 1
    crops = rotation["routes"][0]["crops"]
    assert crops[:4] == ["soybean", "maize_grain", "soybean", "maize_grain"]
    assert set(rotation["tracks"][0]["crop"]) <= {"soybean", "maize_grain", "fallow"}


def test_run_summary_is_consistent():
    result = run(REQUEST, "soybean:skip_stages", "cpu", tracks=2)
    region = result["scenarios"][0]
    assert result["device"] == "cpu" and len(region["occupancy"]) == result["clock"]["periods"] + 1 and len(region["tracks"]) == 2
    assert all(sum(year.values()) == pytest.approx(1, abs=1e-4) for year in region["occupancy"])
    assert region["occupancy"][0] == {"soybean": 1.0}
    assert len(region["tracks"][0]["crop"]) == result["clock"]["periods"] + 1
    value = region["value"]
    assert value["cvar5"] <= value["p5"] <= value["p50"] <= value["p95"]
    assert 0 < region["priced_share"] <= 1


def test_unsupported_requests_are_refused():
    with pytest.raises(RunError, match="horizon_days"):
        run({**REQUEST, "horizon_days": 365}, "soybean:skip_stages", "cpu")
    with pytest.raises(RunError, match="events"):
        run({**REQUEST, "events": [{"id": "x"}]}, "soybean:skip_stages", "cpu")
    with pytest.raises(RunError, match="not in the chain"):
        run({**REQUEST, "scenarios": [{"id": "x", "policy": {"kind": "rotation", "sequence": ["rice"], "fallback": "f"}}]},
            "soybean:skip_stages", "cpu")


def test_route_key_round_trip():
    names = ["a", "b", "c", "fallow"]
    key = 0
    for crop in (2, 0, 1):
        key = key * len(names) + crop + 1
    assert decode_route(key, names) == ["c", "a", "b"]
    assert value_summary(np.array([])) is None


def test_gpu_matches_cpu_statistically(tables):
    cupy = pytest.importorskip("cupy")
    from field_shift.engines.backend import gpu_module, to_numpy
    if gpu_module() is None:
        pytest.skip("no CUDA device")
    policy = Policy(tables.crops.index("soybean"))
    cpu = simulate(np, tables, policy, 3, 20000)
    gpu = simulate(cupy, tables.on(cupy), policy, 3, 20000)
    assert to_numpy(gpu["priced"]).mean() == pytest.approx(cpu["priced"].mean(), abs=0.02)
    assert to_numpy(gpu["carbon"][-1]).mean() == pytest.approx(cpu["carbon"][-1].mean(), abs=0.02)


def test_runs_endpoint(client):
    response = client.post("/runs", params={"device": "cpu", "tracks": 1}, json={**REQUEST, "trajectories": 300})
    assert response.status_code == 200, response.text
    assert [scenario["id"] for scenario in response.json()["scenarios"]] == ["region", "soy-maize"]
    assert client.post("/runs", json={**REQUEST, "profile": "nowhere"}).status_code == 404
    assert client.post("/runs", json={"profile": "franca-sp"}).status_code == 422
    assert client.post("/runs", params={"device": "cpu"}, json={**REQUEST, "horizon_days": 30}).status_code == 422
