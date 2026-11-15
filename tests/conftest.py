import os

import mongomock
import pytest
from fastapi.testclient import TestClient

from field_shift.api import create_app
from field_shift.db import upsert
from field_shift.ingest.__main__ import generate


@pytest.fixture(scope="session")
def generated():
    chains, profiles, reports, errors = generate()
    assert errors == []
    return {"chains": chains, "profiles": profiles, "reports": {r["profile"]: r for r in reports}}


@pytest.fixture()
def client(generated):
    database = mongomock.MongoClient()["field_shift_test"]
    for document in generated["chains"].values():
        upsert(database, "chains", dict(document))
    for document in generated["profiles"].values():
        upsert(database, "profiles", dict(document))
    return TestClient(create_app(database))


@pytest.fixture()
def mongo():
    """A real MongoDB, needed to exercise $jsonSchema validators (mongomock ignores them)."""
    uri = os.environ.get("FIELD_SHIFT_TEST_MONGO_URI")
    if not uri:
        pytest.skip("set FIELD_SHIFT_TEST_MONGO_URI to run MongoDB validator tests")
    from field_shift.db import connect
    database = connect(uri, "field_shift_pytest")
    database.client.drop_database("field_shift_pytest")
    yield database
    database.client.drop_database("field_shift_pytest")
