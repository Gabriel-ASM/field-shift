"""Download the boundaries shown on the map: Brazilian states and the municipality of each profile.

Source: IBGE "malhas" API. Usage: python -m field_shift.ingest.geo
"""

from __future__ import annotations

import gzip
import json
import sys
import urllib.request

from .. import DATA

GEO = DATA / "geo"
API = "https://servicodados.ibge.gov.br/api/v3/malhas"
FORMAT = "formato=application/vnd.geo%2Bjson"
STATES_URL = f"{API}/paises/BR?{FORMAT}&qualidade=minima&intrarregiao=UF"
MUNICIPALITY_URL = API + "/municipios/{code}?" + FORMAT + "&qualidade=intermediaria"


def fetch_geojson(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as response:
        body = response.read()
    if body[:2] == b"\x1f\x8b":        # the API answers gzip even when it is not asked for
        body = gzip.decompress(body)
    document = json.loads(body)
    if document.get("type") != "FeatureCollection" or not document.get("features"):
        raise ValueError(f"unexpected answer from {url}")
    return document


def write_geojson(name: str, document: dict, source: str) -> None:
    path = GEO / f"{name}.geojson"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**document, "source": source}, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(DATA.parent)} ({path.stat().st_size // 1024} KiB)")


def municipalities() -> dict[str, str]:
    """Profile id -> IBGE municipality code, from the profile catalog."""
    catalog = json.loads((DATA / "catalog" / "perfis-exemplo.json").read_text(encoding="utf-8"))
    return {entry["profile"]: str(entry["ibge_code"]) for entry in catalog["profiles"]}


def main() -> int:
    write_geojson("brazil-states", fetch_geojson(STATES_URL), STATES_URL)
    for profile, code in municipalities().items():
        url = MUNICIPALITY_URL.format(code=code)
        write_geojson(f"municipalities/{profile}", fetch_geojson(url), url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
