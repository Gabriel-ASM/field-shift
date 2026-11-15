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


def test_runtime_config_comes_from_the_environment(client, monkeypatch):
    assert "gibs.earthdata.nasa.gov" in client.get("/config").json()["basemap"]["tiles"]
    monkeypatch.setenv("FIELD_SHIFT_CMS_URL", "http://cms.local")
    assert client.get("/config").json()["cms"]["url"] == "http://cms.local"



def test_config_reports_the_build_and_defaults_to_dev(client, monkeypatch):
    assert client.get("/config").json()["version"] == "dev"
    monkeypatch.setenv("FIELD_SHIFT_VERSION", "abc1234")
    assert client.get("/config").json()["version"] == "abc1234"


def test_runs_refuse_a_front_built_from_another_commit(client, monkeypatch):
    monkeypatch.setenv("FIELD_SHIFT_VERSION", "abc1234")
    stale = client.get("/runs/options/franca-sp", headers={"X-Field-Shift-Version": "0000000"})
    assert stale.status_code == 409
    assert "reload the page" in stale.json()["detail"] and stale.headers["X-Field-Shift-Version"] == "abc1234"
    refused = client.post("/runs/jobs", headers={"X-Field-Shift-Version": "0000000"}, json={"profile": "franca-sp"})
    assert refused.status_code == 409
    for version in ("abc1234", "dev", None):
        headers = {"X-Field-Shift-Version": version} if version else {}
        assert client.get("/runs/options/franca-sp", headers=headers).status_code == 200


def test_a_dev_server_accepts_any_front(client):
    assert client.get("/runs/options/franca-sp", headers={"X-Field-Shift-Version": "0000000"}).status_code == 200


def test_the_page_is_revalidated_and_hashed_assets_are_kept(generated, tmp_path, monkeypatch):
    import mongomock
    from fastapi.testclient import TestClient
    from field_shift.api import create_app

    (tmp_path / "index.html").write_text("<h1>front</h1>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "index-3f2a.js").write_text("1", encoding="utf-8")
    monkeypatch.setenv("FIELD_SHIFT_WEB_DIR", str(tmp_path))
    front = TestClient(create_app(mongomock.MongoClient()["x"]))
    for path in ("/", "/index.html"):
        assert front.get(path).headers["cache-control"] == "no-cache"
    assert "immutable" in front.get("/assets/index-3f2a.js").headers["cache-control"]
    etag = front.get("/").headers["etag"]
    assert front.get("/", headers={"If-None-Match": etag}).headers["cache-control"] == "no-cache"

def test_reference_is_only_served_when_configured(client, generated, tmp_path, monkeypatch):
    import mongomock
    from fastapi.testclient import TestClient
    from field_shift.api import create_app

    assert client.get("/reference").status_code == 404
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "a<b>.md").write_text("# hi", encoding="utf-8")
    monkeypatch.setenv("FIELD_SHIFT_REFERENCE_DIR", str(tmp_path))
    browsing = TestClient(create_app(mongomock.MongoClient()["x"]))
    page = browsing.get("/reference").text
    assert "notes (1)" in page and "a&lt;b&gt;.md" in page
    assert browsing.get("/reference/files/notes/a<b>.md").text == "# hi"


def test_boundaries_are_served(client):
    assert len(client.get("/geo/states").json()["features"]) == 27
    assert client.get("/geo/profiles/franca-sp").json()["features"][0]["properties"]["codarea"] == "3516200"
    assert client.get("/geo/profiles/nowhere").status_code == 404


def test_planting_windows_give_the_lowest_zarc_risk_per_decendio():
    import mongomock
    from fastapi.testclient import TestClient
    from field_shift.api import create_app
    client = TestClient(create_app(mongomock.MongoClient()["x"]))
    windows = client.get("/profiles/franca-sp/planting-windows").json()
    soybean = windows["crops"]["soybean"]
    assert windows["risk_levels"] == [20, 30, 40] and soybean["official"] and windows["seasons"] == ["2026/2027"]
    assert soybean["risk"]["30"] == 20 and set(soybean["risk"].values()) <= {20, 30, 40}
    assert client.get("/profiles/nowhere/planting-windows").status_code == 404


def test_municipality_search_is_accent_insensitive_and_prefix_first():
    from field_shift.api.routes.geo import search
    names = [(row["name"], row["uf"]) for row in search("sao paulo", 5)]
    assert names[0] == ("São Paulo", "SP")
    franca = search("franca", 50)
    assert franca[0]["name"] == "Franca" and franca[0]["code"] == "3516200"
    assert search("   ", 5) == []


def test_any_municipal_boundary_comes_from_the_stored_file():
    import mongomock
    from fastapi.testclient import TestClient
    from field_shift.api import create_app
    client = TestClient(create_app(mongomock.MongoClient()["x"]))
    assert client.get("/geo/municipalities/9999999").status_code == 404
    rio_verde = client.get("/geo/municipalities/5218805").json()
    assert rio_verde["features"][0]["properties"]["codarea"] == "5218805"
    assert client.get("/geo/municipalities?q=vargin").json()[0]["name"] == "Varginha"
