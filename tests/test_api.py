import json

from field_shift.contracts import V2_DIR, contract_names


def test_contracts_are_listed_and_served_bundled(client):
    assert [item["name"] for item in client.get("/contracts").json()] == contract_names()
    bundled = client.get("/contracts/markov").json()
    assert "$ref" not in json.dumps(bundled)
    assert "$ref" in json.dumps(client.get("/contracts/markov", params={"bundled": False}).json())
    assert client.get("/contracts/nope").status_code == 404


def test_mongo_validator_reports_what_it_cannot_enforce(client):
    body = client.get("/contracts/crop/mongo").json()
    assert "$jsonSchema" in body["validator"]
    assert body["not_enforced_by_mongodb"] == ["/properties/stage/propertyNames"]


def test_validate_reports_schema_and_graph_errors(client):
    chain = json.loads((V2_DIR / "examples/markov.franca-sp-observed.json").read_text(encoding="utf-8"))
    assert client.post("/validate/markov", json=chain).json() == {"valid": True, "errors": []}
    chain["transitions"][0]["probability"] = 0.5
    result = client.post("/validate/markov", json=chain).json()
    assert result["valid"] is False and "not 1" in result["errors"][0]
    result = client.post("/validate/soil", json={"pH": 99}).json()
    assert result["errors"] == ["/pH: 99 is greater than the maximum of 14"]
    node = {"state": "x", "soil": {"pH": 5}}
    assert client.post("/validate/markov", params={"fragment": "#/definitions/node"}, json=node).json()["valid"]


def test_views(client):
    graph = client.get("/views/graph").json()
    assert {node["id"] for node in graph["nodes"]} == set(contract_names())
    assert {"ref", "id", "pointer"} <= {edge["kind"] for edge in graph["edges"]}
    assert "field_shift_contracts_v2" in client.get("/views/tree").json()


def test_profiles_and_chain(client):
    assert [p["id"] for p in client.get("/profiles").json()] == ["ariquemes-ro", "franca-sp", "varginha-mg"]
    profile = client.get("/profiles/franca-sp").json()
    assert profile["initial_node"]["soil"]["available_water_capacity"] > 0 and "_id" not in profile
    assert client.get("/profiles/nowhere").status_code == 404
    chain = client.get("/profiles/franca-sp/chain").json()
    assert chain["profile"] == "franca-sp"
    assert client.get("/profiles/nowhere/chain").status_code == 404


def test_chain_matrix_is_square_and_rows_sum_to_one(client):
    matrix = client.get("/profiles/franca-sp/chain/matrix").json()
    size = len(matrix["states"])
    assert len(matrix["rows"]) == size and all(len(row["cells"]) == size for row in matrix["rows"])
    for row in matrix["rows"]:
        total = sum(cell["probability"] for cell in row["cells"] if cell)
        assert (abs(total - 1) < 1e-4) if row["has_edges"] else total == 0


def test_documented_entry_point_is_the_app_factory():
    """`uvicorn --factory field_shift.api:create_app` must resolve to a callable, not a module."""
    from uvicorn.importer import import_from_string

    assert callable(import_from_string("field_shift.api:create_app"))


def test_front_and_pages_are_served_without_shadowing_the_api(client):
    landing = client.get("/")
    assert landing.status_code == 200 and "Field Shift" in landing.text
    assert client.get("/pages/contracts-v2.html").headers["content-type"].startswith("text/html")
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/openapi.json").json()["info"]["title"] == "Field Shift API"
    assert client.get("/profiles/nowhere").status_code == 404


def test_web_dir_can_be_replaced(generated, tmp_path, monkeypatch):
    import mongomock
    from fastapi.testclient import TestClient
    from field_shift.api import create_app

    (tmp_path / "index.html").write_text("<h1>real front</h1>", encoding="utf-8")
    monkeypatch.setenv("FIELD_SHIFT_WEB_DIR", str(tmp_path))
    assert "real front" in TestClient(create_app(mongomock.MongoClient()["x"])).get("/").text


def test_large_pages_are_compressed(client):
    response = client.get("/pages/visualizacao.html", headers={"Accept-Encoding": "gzip"})
    assert response.headers["content-encoding"] == "gzip"
    assert len(response.content) > 1_000_000        # decoded body is the full page
    assert client.get("/health").headers.get("content-encoding") is None   # tiny responses stay as they are


def test_map_demo_is_served_and_its_api_calls_work(client):
    """web/demo.html reads profiles and chains and posts the stored chain back to /validate/markov."""
    assert "v2 demo" in client.get("/demo.html").text
    for profile in client.get("/profiles").json():
        detail = client.get(f"/profiles/{profile['id']}").json()
        assert {"lat", "long"} <= detail["initial_node"]["climate"].keys()
        chain = client.get(f"/profiles/{profile['id']}/chain").json()
        assert client.post("/validate/markov", json=chain).json()["valid"] is True


def test_profile_page_is_served(client):
    assert "Starting conditions" in client.get("/profile.html").text
