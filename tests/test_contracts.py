import copy
import json

import pytest

from field_shift.contracts import V2_DIR, bundle, check, contract_names, to_mongo, validate
from field_shift.contracts.__main__ import main as validate_examples
from field_shift.contracts.mongo_schema import BSON_TYPES

MONGO_KEYWORDS = {
    "bsonType", "properties", "required", "enum", "minimum", "maximum", "minLength", "maxLength", "pattern",
    "minItems", "maxItems", "uniqueItems", "minProperties", "maxProperties", "title", "description",
    "items", "additionalProperties", "not", "oneOf", "anyOf", "allOf",
}


def example(name):
    return json.loads((V2_DIR / "examples" / name).read_text(encoding="utf-8"))


def test_every_example_is_valid():
    assert validate_examples() == 0


@pytest.mark.parametrize("name", contract_names())
def test_bundle_has_no_references(name):
    assert "$ref" not in json.dumps(bundle(name))


def _keywords(schema, inside_properties=False):
    if isinstance(schema, dict):
        for key, value in schema.items():
            if inside_properties:
                yield from _keywords(value)
            else:
                yield key
                yield from _keywords(value, inside_properties=(key == "properties"))
    elif isinstance(schema, list):
        for item in schema:
            yield from _keywords(item)


@pytest.mark.parametrize("name", contract_names())
def test_mongo_schema_uses_only_supported_keywords(name):
    assert set(_keywords(to_mongo(bundle(name)))) <= MONGO_KEYWORDS


def test_mongo_schema_translates_types_and_keeps_units():
    soil = to_mongo(bundle("soil"))
    assert soil["properties"]["pH"]["bsonType"] == BSON_TYPES["number"]
    assert soil["properties"]["organic_carbon"]["description"].endswith("[g/kg]")
    assert soil["properties"]["_id"] == {}
    policy = to_mongo(bundle("monte_carlo"))["properties"]["scenarios"]["items"]["properties"]["policy"]["oneOf"][0]
    assert policy["properties"]["kind"]["enum"] == ["rotation"]


def test_schema_errors_name_the_field():
    assert validate("soil", {"pH": 99}) == ["/pH: 99 is greater than the maximum of 14"]
    assert validate("markov", {"soil": {}}, fragment="#/definitions/node") == ["/: 'state' is a required property"]


def test_chain_checks_catch_unknown_states_and_bad_sums():
    chain = example("markov.franca-sp-observed.json")
    assert check("markov", chain) == []
    broken = copy.deepcopy(chain)
    broken["transitions"][0]["probability"] = 0.5
    broken["transitions"][1]["to"] = "rice:skip_stages"
    errors = check("markov", broken)
    assert any("is not a declared state" in e for e in errors) and any("not 1" in e for e in errors)


def test_run_checks_catch_scenarios_outside_the_chain():
    run = example("monte_carlo.s1-three-scenarios.json")
    assert check("monte_carlo", run) == []
    run["scenarios"][0]["policy"]["sequence"].append("rice")
    run["scenarios"][1]["policy"]["fallback"] = "nowhere:skip_stages"
    assert len(check("monte_carlo", run)) == 2
