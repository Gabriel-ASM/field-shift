"""Needs a real MongoDB: FIELD_SHIFT_TEST_MONGO_URI=mongodb://localhost:27017 pytest -m mongo"""

import copy

import pytest
from pymongo.errors import DuplicateKeyError, WriteError

from field_shift.db import COLLECTIONS, InvalidDocument, ensure_collections, find_one, upsert

pytestmark = pytest.mark.mongo


def test_validators_are_installed_and_accept_generated_documents(mongo, generated):
    ensure_collections(mongo)
    ensure_collections(mongo)  # idempotent: second call updates validators in place
    for name in COLLECTIONS:
        assert "$jsonSchema" in mongo.command("listCollections", filter={"name": name})["cursor"]["firstBatch"][0]["options"]["validator"]
    for profile in generated["chains"]:
        upsert(mongo, "chains", copy.deepcopy(generated["chains"][profile]))
        upsert(mongo, "profiles", copy.deepcopy(generated["profiles"][profile]))
    assert mongo["chains"].count_documents({}) == 3
    assert find_one(mongo, "profiles", "franca-sp") == generated["profiles"]["franca-sp"]
    assert mongo["contracts"].count_documents({}) == 9


def test_application_validation_rejects_before_the_database(mongo, generated):
    ensure_collections(mongo)
    bad = copy.deepcopy(generated["chains"]["franca-sp"])
    bad["transitions"][0]["probability"] = 0.01
    with pytest.raises(InvalidDocument) as caught:
        upsert(mongo, "chains", bad)
    assert "not 1" in caught.value.errors[0]
    assert mongo["chains"].count_documents({}) == 0


@pytest.mark.parametrize("mutate", [
    lambda d: d["initial_node"]["soil"].update(pH=99),            # out of range
    lambda d: d["initial_node"]["soil"].update(ph=5.0),           # unknown field
    lambda d: d["initial_node"].pop("soil"),                      # missing required
    lambda d: d.update(scope="planet"),                           # not in enum
    lambda d: d["values"][0].update(support="guess"),             # nested enum through $ref
    lambda d: d["initial_node"]["soil"].update(pH="acid"),        # wrong type
])
def test_database_validator_rejects_writes_that_bypass_the_application(mongo, generated, mutate):
    ensure_collections(mongo)
    bad = copy.deepcopy(generated["profiles"]["franca-sp"])
    mutate(bad)
    with pytest.raises(WriteError):
        mongo["profiles"].insert_one(bad)


def test_key_is_unique(mongo, generated):
    ensure_collections(mongo)
    mongo["profiles"].insert_one(copy.deepcopy(generated["profiles"]["franca-sp"]))
    with pytest.raises(DuplicateKeyError):
        mongo["profiles"].insert_one(copy.deepcopy(generated["profiles"]["franca-sp"]))
