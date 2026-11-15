import json
from collections import defaultdict

import pytest

from field_shift import DATA
from field_shift.contracts import check, validate
from field_shift.ingest import ChainRules, build_chain, profile_ids
from field_shift.ingest.profiles import topsoil_mean
from field_shift.front.__main__ import topsoil_carbon_g_kg

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
    rows = defaultdict(list)
    for edge in chain["transitions"]:
        rows[edge["from"]].append(edge)
        assert edge["support"] == ("derived" if edge["mass"] > 0 else "prior")
    assert chain["alpha_per_destination"] == rules.alpha_per_destination == 0.5
    for edges in rows.values():
        for edge in edges:
            alpha = rules.alpha_per_destination
            assert edge["probability"] == pytest.approx(
                (edge["mass"] + alpha) / (edge["outgoing_mass"] + alpha * len(edges))
            )
    assert chain["initial_state"] in rows
    assert {edge["to"] for edge in rows["sugarcane:skip_stages"]} == {"sugarcane:skip_stages"}
    assert "fallow:skip_stages" not in rows
    assert any(edge["support"] == "prior" for edge in chain["transitions"])


def test_edge_mass_matches_the_v1_file(generated):
    v1 = json.loads((DATA / "profiles/franca-sp/crop-transition-markov.json").read_text(encoding="utf-8"))
    mass = {(t["from_state"], t["to_state"]): t["area_weighted_count"] for t in v1["transitions"]}
    for edge in generated["chains"]["franca-sp"]["transitions"]:
        key = (edge["from"].split(":")[0], edge["to"].split(":")[0])
        assert edge["mass"] == pytest.approx(mass.get(key, 0))


def test_pam_history_preserves_original_crop_shares():
    v1 = json.loads((DATA / "profiles/varginha-mg/crop-transition-markov.json").read_text(encoding="utf-8"))
    chain, _ = build_chain("varginha-mg")
    assert chain["pam_history"]["annual_sequence"] == v1["annual_sequence"]
    assert any(c["state_id"] == "coffee" for year in chain["pam_history"]["annual_sequence"] for c in year["top5_crops"])


@pytest.mark.parametrize("profile", PROFILES)
def test_profile_is_valid_and_documents_every_value(generated, profile):
    document = generated["profiles"][profile]
    assert validate("profile", document) == []
    node = document["initial_node"]
    pointers = {f"/{group}/{field}" for group in ("soil", "climate") for field in node[group]}
    assert pointers == {value["pointer"] for value in document["values"]}
    assert node["state"] == generated["chains"][profile]["initial_state"]
    assert document["water_classes"]["low_max_inclusive"] < node["soil"]["available_water_fraction"] < document["water_classes"]["medium_max_inclusive"]
    benchmarks = json.loads((DATA / "reference/economic-benchmarks.json").read_text(encoding="utf-8"))
    assert document["economics"]["crop_inputs"] == benchmarks["profiles"][profile]["crop_inputs"]


def test_topsoil_mean_matches_the_v1_carbon_weighting():
    soil = json.loads((DATA / "profiles/franca-sp/soil-profile.json").read_text(encoding="utf-8"))
    assert topsoil_mean(soil["layers"], "organic_carbon_g_kg") == pytest.approx(topsoil_carbon_g_kg(soil))


def test_committed_documents_are_up_to_date(generated):
    for kind in ("chains", "profiles"):
        for profile, document in generated[kind].items():
            stored = json.loads((DATA / "v2" / kind / f"{profile}.json").read_text(encoding="utf-8"))
            assert stored == document, f"run `python -m field_shift.ingest` to refresh data/v2/{kind}/{profile}.json"
