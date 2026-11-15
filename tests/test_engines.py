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
    route = region["routes"][0]
    assert route["final_carbon"] > 0 and 0 < route["final_water_multiplier"] < 2
    assert result["ranking"]["environment_weight"]["default_weight"] == 0.2
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


def nitrogen_fixture(tables):
    """Made-up parameters to exercise the mechanism only; real ones come from data/reference."""
    from field_shift.engines.nitrogen import Nitrogen
    size, legume = len(tables.crops), tables.crops.index("soybean")
    credit, demand = np.zeros(size), np.full(size, 120.0)
    credit[legume], demand[legume] = 40.0, 0.0
    return Nitrogen(initial=60.0, credit=credit, fertilizer=np.zeros(size), removal=np.full(size, 15.0), demand=demand,
                    floor=np.full(size, 0.5), loss_fraction=np.array([0.0, 0.01, 0.03]))


def test_nitrogen_response_is_linear_up_to_the_demand(tables):
    from field_shift.engines.nitrogen import after_harvest, yield_multiplier
    params = nitrogen_fixture(tables)
    soybean, maize = tables.crops.index("soybean"), tables.crops.index("maize_grain")
    crop = np.array([maize, maize, maize, soybean])
    assert yield_multiplier(np, params, crop, np.array([0.0, 60.0, 500.0, 0.0])).tolist() == [0.5, 0.75, 1.0, 1.0]
    assert after_harvest(np, params, np.array([soybean, maize]), np.array([10.0, 10.0]), np.array([3.0, 6.0])).tolist() == [5.0, 0.0]


def test_with_nitrogen_maize_after_soybean_beats_maize_after_maize(tables):
    from dataclasses import replace
    with_n = replace(tables, nitrogen=nitrogen_fixture(tables))
    soybean, maize = tables.crops.index("soybean"), tables.crops.index("maize_grain")
    rotated = simulate(np, with_n, Policy(soybean, (soybean, maize)), 5, 400)["value"].mean()
    repeated = simulate(np, with_n, Policy(maize, (maize,)), 5, 400)["value"].mean()
    penalty_only = simulate(np, tables, Policy(maize, (maize,)), 5, 400)["value"].mean()
    assert rotated > repeated and repeated != penalty_only


def chain_routes(tables, start: str, count: int = 3000) -> list[list[str]]:
    names = [*tables.crops, "fallow"]
    result = simulate(np, tables, Policy(tables.crops.index(start)), 11, count)
    return [decode_route(int(key), names) for key in np.unique(result["route"])]


def longest_run(route: list[str], crop: str) -> int:
    best = run = 0
    for planted in route:
        run = run + 1 if planted == crop else 0
        best = max(best, run)
    return best


def test_chain_never_switches_directly_between_maize_and_soybean(tables):
    """crop-cycle-assumptions.json: maize and soybean need a completed cycle of another crop in between."""
    assert tables.sequence_block[tables.crops.index("soybean"), tables.crops.index("maize_grain")]
    for route in chain_routes(tables, "soybean"):
        pairs = zip(route, route[1:])
        assert not any({a, b} == {"soybean", "maize_grain"} for a, b in pairs), route


def test_chain_stops_replanting_at_the_penalty_cap(tables):
    """crop-cycle-assumptions.json: maize loses 0.022 per replanting up to 0.043, soybean 0.08 up to 0.20, so the
    cap is reached at the 3rd maize and the 4th soybean in a row, and neither is planted again after that."""
    routes = chain_routes(tables, "maize_grain") + chain_routes(tables, "soybean")
    assert max(longest_run(route, "maize_grain") for route in routes) == 3
    assert max(longest_run(route, "soybean") for route in routes) == 4


def test_cover_crop_cost_is_split_and_the_next_soybean_gains(tables):
    from field_shift.engines.monte_carlo import State, harvest_cash, residual_gain, sowing_cash
    brachiaria, soybean = tables.crops.index("brachiaria"), tables.crops.index("soybean")
    crop = np.array([brachiaria])
    at_sowing, at_harvest = sowing_cash(np, tables, crop), harvest_cash(tables, crop, np.zeros(1), np.zeros(1), 0.0)
    assert (at_sowing + at_harvest)[0] == pytest.approx(-tables.cost[brachiaria])
    state = State(np, tables, Policy(brachiaria), 3)
    state.last_harvest_day = np.array([100.0, 100.0, np.nan])
    gain = residual_gain(np, tables, state, np.full(3, soybean), np.array([100.0, 160.0, 160.0]))
    assert gain.tolist() == pytest.approx([0.06, 0.03, 0.0])
    assert residual_gain(np, tables, state, np.full(3, brachiaria), np.array([100.0, 160.0, 160.0])).tolist() == [0, 0, 0]


def test_standing_cane_reforms_after_its_last_modeled_cut(tables):
    """Franca from cane: from the 1st cut the field keeps cane for years; from the 5th (last) cut it is reformed
    at the first harvest, so after two years almost no trajectory still has its first cane field."""
    cane = tables.crops.index("sugarcane")
    still_cane = {}
    for cut in (1, 5):
        result = simulate(np, tables, Policy(cane, initial_sugarcane_cut=cut), 3, 2000)
        planted_again = result["route"] != cane + 1      # any planting after the first cane
        still_cane[cut] = float(((result["crop"][2] == cane) & ~planted_again).mean())
    assert int(tables.sugarcane_cuts) == 5
    assert still_cane[1] > 0.95 and still_cane[5] < 0.05


def test_tracks_show_the_cut_of_standing_cane():
    """Cut 1: the first field still has cane, and cuts 2+ follow. Cut 5: the first harvest is the last, then reform."""
    scenario = {"id": "cane", "initial_state": "sugarcane:skip_stages", "policy": {"kind": "markov"}}
    tracks = {}
    for cut in (1, 5):
        result = run({**REQUEST, "trajectories": 20, "scenarios": [{**scenario, "initial_sugarcane_cut": cut}]}, "soybean:skip_stages", "cpu", tracks=5)
        tracks[cut] = result["scenarios"][0]["tracks"]
    for cut, recorded in tracks.items():
        assert all(track["cane_cut"][0] == cut for track in recorded)
    after_first_harvest = 25   # 24 half-month periods in a year
    assert all(track["cane_cut"][after_first_harvest] == 2 for track in tracks[1])
    assert all(track["cane_cut"][after_first_harvest] in (0, 1) for track in tracks[5])


def test_cane_cut_is_checked_against_the_modeled_cuts():
    scenario = {"id": "cane", "initial_state": "sugarcane:skip_stages", "policy": {"kind": "markov"}}
    with pytest.raises(RunError, match="cuts 1 to 5"):
        run({**REQUEST, "trajectories": 10, "scenarios": [{**scenario, "initial_sugarcane_cut": 6}]}, "soybean:skip_stages", "cpu")
    from field_shift.engines.run import options
    assert options("franca-sp")["sugarcane_cuts"] == 5


def test_routes_carry_what_the_result_page_shows(tables):
    """Distribution of recommendable routes, final water and soil, yield loss by planting, ranking reference."""
    from field_shift.engines.summary import Support, summarize, yield_penalties
    result = simulate(np, tables, Policy(tables.crops.index("soybean")), 4, 6000)
    summary = summarize(result, tables, Support(ranked=2, recommended=20))
    routes = summary["routes"]
    assert summary["ranking_reference"]["cvar5"] <= summary["ranking_reference"]["p95"]
    for route in routes:
        assert sum(route["final_water"].values()) == pytest.approx(1, abs=1e-5)
        assert route["final_carbon_class"] in ("low", "medium", "high") and len(route["yield_penalty"]) == len(route["crops"])
        value = route["value"]
        if value and value["count"] >= 20:
            assert sum(value["distribution"]["counts"]) == value["count"]
        elif value:
            assert "distribution" not in value
    assert any(route["value"] and route["value"]["count"] >= 20 for route in routes)
    # maize: 0.022 per replanting, capped at 0.043 (crop-cycle-assumptions.json)
    assert yield_penalties(["soybean", "maize_grain", "maize_grain", "maize_grain"], tables) == [0, 0, 0.022, 0.043]


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
    assert client.get("/runs/options/franca-sp").json()["initial_crops"] == ["soybean", "maize_grain", "sugarcane"]
    assert client.get("/runs/options/nowhere").status_code == 404
    assert client.post("/runs", json={"profile": "franca-sp"}).status_code == 422
    assert client.post("/runs", params={"device": "cpu"}, json={**REQUEST, "horizon_days": 30}).status_code == 422


def test_batches_are_the_same_batches_run_one_after_another(tables):
    """A run in batches equals simulating each batch with its derived seed in sequence and joining the results."""
    from field_shift.engines.batches import batch_seed, batch_sizes, join, on_host, simulate_batches
    from field_shift.engines.summary import Support, summarize
    policy, done = Policy(tables.crops.index("soybean")), []
    batched = simulate_batches(np, tables, policy, 9, 2500, keep=3, batch=1000, progress=done.append)
    by_hand = join([on_host(simulate(np, tables, policy, batch_seed(9, i), size, 3 if i == 0 else 0))
                    for i, size in enumerate(batch_sizes(2500, 1000))])
    support = Support(ranked=2, recommended=20)
    assert done == [1000, 2000, 2500]
    assert summarize(batched, tables, support) == summarize(by_hand, tables, support)


def test_a_job_gives_the_same_result_as_one_call_and_serves_route_details():
    import time
    from field_shift.api.jobs import Jobs
    from field_shift.engines.summary import route_detail
    request = {**REQUEST, "trajectories": 1200}
    direct = run(request, "soybean:skip_stages", "cpu", tracks=2)
    jobs = Jobs()
    job = jobs.start(request, "soybean:skip_stages", "cpu", 2)
    for _ in range(600):
        if job.status != "running":
            break
        time.sleep(0.05)
    assert job.status == "done" and job.done == job.total == 2400
    strip = lambda result: [{k: v for k, v in s.items()} for s in result["scenarios"]]
    assert strip(job.result) == strip(direct)
    route = job.result["scenarios"][0]["routes"][0]
    detail = route_detail(job.raw[0], tables_for("franca-sp"), route["crops"])
    assert detail["trajectories"] == route["trajectories"]
    assert all(sum(period) == route["trajectories"] for period in detail["frames"]["water"])
    assert all(track["crop"][0] == route["crops"][0] for track in detail["tracks"])
    assert route_detail(job.raw[0], tables_for("franca-sp"), ["mucuna", "mucuna", "mucuna"]) is None


def test_job_endpoints(client):
    import time
    started = client.post("/runs/jobs", params={"device": "cpu"}, json={**REQUEST, "trajectories": 300})
    assert started.status_code == 202, started.text
    job_id = started.json()["id"]
    for _ in range(600):
        view = client.get(f"/runs/jobs/{job_id}").json()
        if view["status"] != "running":
            break
        time.sleep(0.05)
    assert view["status"] == "done" and view["done"] == view["total"] == 600
    crops = ",".join(view["result"]["scenarios"][0]["routes"][0]["crops"])
    assert client.get(f"/runs/jobs/{job_id}/route", params={"crops": crops}).status_code == 200
    assert client.get("/runs/jobs/nothing").status_code == 404
    assert client.post("/runs/jobs", json={**REQUEST, "horizon_days": 30}).status_code == 422


def test_total_nitrogen_moves_by_the_crop_balance_and_steers_the_chain(tables):
    """soil_nitrogen (7a836bf): the stock moves by each crop's annual net balance; below the C:N target the chain
    favours crops with a positive balance (crotalaria +450) over negative ones (maize −192)."""
    from field_shift.engines.monte_carlo import State, advance_total_nitrogen
    maize, crotalaria = tables.crops.index("maize_grain"), tables.crops.index("crotalaria")
    state = State(np, tables, Policy(maize), 2)
    state.crop = np.array([maize, -1])
    advance_total_nitrogen(np, tables, state)
    step = tables.period_days / 365
    assert state.total_nitrogen.tolist() == pytest.approx([tables.total_n_initial - 192 * step, tables.total_n_initial])
    target = tables.total_n_target_per_carbon * tables.initial_carbon
    soybean = tables.crops.index("soybean")
    poor = markov.probabilities(np, tables, soybean, 0.5, tables.initial_carbon, 0.4 * target)
    rich = markov.probabilities(np, tables, soybean, 0.5, tables.initial_carbon, 1.5 * target)
    ratio = lambda row: row[crotalaria] / row[maize]
    assert ratio(poor) > ratio(rich)



def test_soybean_on_soybean_costs_soil_carbon(tables):
    """soybean-repetition-soil.json (Campos et al. 2011): a soybean replanted on soybean loses 0.29-0.51 Mg C/ha/yr
    that a rotation would build, converted to g/kg in 0-30 cm with the profile's bulk density."""
    from field_shift.engines.monte_carlo import State, advance_soil
    soybean, maize = tables.crops.index("soybean"), tables.crops.index("maize_grain")
    density = 1.3566666666666667          # Franca, SoilGrids bdod 0-30 cm
    assert tables.repeat_carbon_penalty.tolist() == pytest.approx([0.29 / 3 / density, 0.51 / 3 / density])
    state = State(np, tables, Policy(soybean), 3)
    state.crop, state.streak = np.array([soybean, soybean, maize]), np.array([1, 2, 2])
    rate, penalty = np.zeros((3, len(tables.crops))), np.full(3, 0.1)
    advance_soil(np, tables, state, rate, penalty)
    step = tables.period_days / 365
    assert state.carbon.tolist() == pytest.approx([tables.initial_carbon, tables.initial_carbon - 0.1 * step, tables.initial_carbon])
