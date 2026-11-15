import json
from collections import defaultdict

import pytest

from field_shift import DATA
from field_shift.contracts import check, validate
from field_shift.ingest import ChainRules, build_chain, profile_ids
from field_shift.ingest.profiles import topsoil_mean
from field_shift.legacy.visualize import topsoil_carbon_g_kg

PROFILES = profile_ids()


def test_three_profiles_are_known():
    assert PROFILES == ["ariquemes-ro", "franca-sp", "varginha-mg"]


@pytest.mark.parametrize("profile", PROFILES)
def test_chain_is_valid_and_rows_sum_to_one(generated, profile):
    chain = generated["chains"][profile]
    assert validate("markov", chain) == [] and check("markov", chain) == []
    totals = defaultdict(float)
    for edge in chain["transitions"]:
        totals[edge["from"]] += edge["probability"]
    assert totals and all(abs(total - 1) < 1e-4 for total in totals.values())


@pytest.mark.parametrize("profile", PROFILES)
def test_chain_follows_the_agreed_rules(generated, profile):
    chain = generated["chains"][profile]
    rules = ChainRules()
    assert not any("coffee" in state["id"] for state in chain["states"])
    assert chain["states"][-1]["id"] == "fallow:skip_stages"
    for edge in chain["transitions"]:
        assert edge["support"] == "derived" and edge["mass"] > 0
        assert edge["probability"] >= rules.min_probability
        assert edge["outgoing_mass"] >= rules.min_row_mass
        assert edge["probability"] == pytest.approx(edge["mass"] / edge["outgoing_mass"], abs=1e-5)
    assert chain["initial_state"] in {edge["from"] for edge in chain["transitions"]}


def test_edge_mass_matches_the_v1_file(generated):
    v1 = json.loads((DATA / "profiles/franca-sp/crop-transition-markov.json").read_text(encoding="utf-8"))
    mass = {(t["from_state"], t["to_state"]): t["area_weighted_count"] for t in v1["transitions"]}
    for edge in generated["chains"]["franca-sp"]["transitions"]:
        key = (edge["from"].split(":")[0], edge["to"].split(":")[0])
        assert edge["mass"] == pytest.approx(mass[key], abs=1e-5)


def test_stricter_rules_drop_more_edges():
    loose, _ = build_chain("franca-sp", ChainRules(min_probability=0.0, min_row_mass=0.0))
    strict, _ = build_chain("franca-sp", ChainRules(min_probability=0.25))
    default, _ = build_chain("franca-sp")
    assert len(strict["transitions"]) < len(default["transitions"]) < len(loose["transitions"])


@pytest.mark.parametrize("profile", PROFILES)
def test_profile_is_valid_and_documents_every_value(generated, profile):
    document = generated["profiles"][profile]
    assert validate("profile", document) == []
    node = document["initial_node"]
    pointers = {f"/{group}/{field}" for group in ("soil", "climate") for field in node[group]}
    assert pointers == {value["pointer"] for value in document["values"]}
    assert node["state"] == generated["chains"][profile]["initial_state"]


def test_topsoil_mean_matches_the_v1_carbon_weighting():
    soil = json.loads((DATA / "profiles/franca-sp/soil-profile.json").read_text(encoding="utf-8"))
    assert topsoil_mean(soil["layers"], "organic_carbon_g_kg") == pytest.approx(topsoil_carbon_g_kg(soil))


def test_committed_documents_are_up_to_date(generated):
    for kind in ("chains", "profiles"):
        for profile, document in generated[kind].items():
            stored = json.loads((DATA / "v2" / kind / f"{profile}.json").read_text(encoding="utf-8"))
            assert stored == document, f"run `python -m field_shift.ingest` to refresh data/v2/{kind}/{profile}.json"
