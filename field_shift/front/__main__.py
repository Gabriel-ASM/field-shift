"""Generate the crop Markov and Monte Carlo demonstration as one self-contained HTML page.

Two variants are built from the same sources in this folder (``index.html`` is the template):

``classic`` (default)
    ``docs/visualizacao.html``. Fully offline; step 1 is the schematic SVG map of Brazil.
    ``tests/test_front.cjs`` and ``tests/test_api.py`` depend on this file, and its bytes must not
    change when only the map variant evolves.

``map``
    ``docs/visualizacao2.html``. Same journey, but step 1 is a real Leaflet map with a polygon /
    rectangle selector limited to 500 ha (see ``aoi.js``, ``map.js``, ``map.css`` and
    ``docs/mapa-seletor.md``). It needs internet for the Leaflet libraries and the satellite
    basemap; if they fail to load the page falls back to the classic SVG map.

How the variants differ
    The template has three slots, written inline so that an empty slot leaves no trace::

        MAP_HEAD   inside <head>, before the main <style>   (Leaflet CSS + map.css)
        MAP_SCREEN inside the step-1 map card               (the container Leaflet draws into)
        MAP_JS     right before </body>                     (Leaflet, boundaries JSON, aoi.js, map.js)

    ``classic`` replaces them with an empty string; ``map`` fills them (``map_slots``).

Usage::

    python -m field_shift.front                                  # docs/visualizacao.html
    python -m field_shift.front --variant map                    # docs/visualizacao2.html
    python -m field_shift.front --variant map --output /tmp/v2.html --seed 7
"""

from argparse import ArgumentParser
import json
from pathlib import Path
from random import Random

from ..engines.payload import profile_payload
from ..ingest.profiles import topsoil_mean


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data"
FRONT = Path(__file__).parent
TEMPLATE = FRONT / "index.html"
STATE_NAMES = {"RO": "Rondônia", "SP": "São Paulo", "MG": "Minas Gerais"}
DEFAULT_OUTPUT = {"classic": Path("docs/visualizacao.html"), "map": Path("docs/visualizacao2.html")}
# Pinned on purpose: the same versions the OpenAgro map uses, known to work together.
LEAFLET = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min"
LEAFLET_DRAW = "https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw"
COORDINATE_DECIMALS = 5  # ~1 m; keeps the embedded boundaries to a few KB


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def payload_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def topsoil_carbon_g_kg(soil: dict) -> float:
    return topsoil_mean(soil["layers"], "organic_carbon_g_kg")


def municipal_boundaries(catalog: dict, profile_ids: list[str]) -> dict:
    """Municipal boundaries for the map selector, keyed by profile id.

    Reads the IBGE municipal mesh already stored in ``data/raw/ibge`` (no network). Each entry is
    ``{municipality, uf, ibge_code, polygons}`` where ``polygons`` is a MultiPolygon-shaped list
    (``[[outer_ring, hole, ...], ...]``) of ``[lon, lat]`` pairs, EPSG:4326. A Polygon is wrapped
    so the browser handles a single shape.
    """
    by_id = {profile["profile"]: profile for profile in catalog["profiles"]}
    boundaries = {}
    for profile_id in profile_ids:
        entry = by_id[profile_id]
        mesh = DATA_ROOT / "raw" / "ibge" / f"ibge-malha-municipal-{entry['ibge_code']}.geojson"
        geometry = read_json(mesh)["features"][0]["geometry"]
        if geometry["type"] == "Polygon":
            polygons = [geometry["coordinates"]]
        elif geometry["type"] == "MultiPolygon":
            polygons = geometry["coordinates"]
        else:
            raise ValueError(f"Unsupported geometry {geometry['type']!r} in {mesh}")
        boundaries[profile_id] = {
            "municipality": entry["municipality"],
            "uf": entry["uf"],
            "ibge_code": entry["ibge_code"],
            "polygons": [
                [[[round(lon, COORDINATE_DECIMALS), round(lat, COORDINATE_DECIMALS)] for lon, lat in ring] for ring in polygon]
                for polygon in polygons
            ],
        }
    return boundaries


def map_slots(variant: str, boundaries: dict) -> dict:
    """Content for the three template slots; empty strings for the classic variant."""
    if variant == "classic":
        return {"<!-- MAP_HEAD -->": "", "<!-- MAP_SCREEN -->": "", "<!-- MAP_JS -->": ""}
    return {
        "<!-- MAP_HEAD -->": (
            f'<link rel="stylesheet" href="{LEAFLET}.css">\n'
            f'<link rel="stylesheet" href="{LEAFLET_DRAW}.css">\n'
            f"<style>\n{(FRONT / 'map.css').read_text(encoding='utf-8')}</style>\n"
        ),
        "<!-- MAP_SCREEN -->": '<div class="aoi-map" id="aoi-map" hidden></div>\n',
        "<!-- MAP_JS -->": (
            # Leaflet scripts first and unconditional; if the CDN is unreachable, map.js notices that
            # `L` is undefined and leaves the classic SVG map in place.
            f'<script src="{LEAFLET}.js"></script>\n'
            f'<script src="{LEAFLET_DRAW}.js"></script>\n'
            f'<script id="municipal-boundaries" type="application/json">{payload_json(boundaries)}</script>\n'
            f"<script>\n{(FRONT / 'aoi.js').read_text(encoding='utf-8')}</script>\n"
            f"<script>\n{(FRONT / 'map.js').read_text(encoding='utf-8')}</script>\n"
        ),
    }


def export_page(output: Path, seed: int, variant: str = "classic") -> None:
    if variant not in DEFAULT_OUTPUT:
        raise ValueError(f"Unknown variant {variant!r}; expected one of {sorted(DEFAULT_OUTPUT)}")
    if not DATA_ROOT.is_dir():
        raise FileNotFoundError(f"Canonical data directory not found: {DATA_ROOT}")
    catalog = read_json(DATA_ROOT / "catalog" / "perfis-exemplo.json")
    soil_hypotheses = read_json(DATA_ROOT / "reference" / "soil-crop-response-hypotheses.json")
    crop_cycles = read_json(DATA_ROOT / "reference" / "crop-cycle-assumptions.json")
    run_settings = read_json(DATA_ROOT / "reference" / "visualization-run-settings.json")
    economic_prices = read_json(DATA_ROOT / "reference" / "yahoo-harvest-futures.json")
    rng = Random(seed)
    by_uf = {}
    for profile in catalog["profiles"]:
        by_uf.setdefault(profile["uf"], []).append(profile)

    cases = []
    profile_data = {}
    for uf in ("RO", "SP", "MG"):
        selected = rng.choice(by_uf[uf])
        profile_id = selected["profile"]
        profile_data[profile_id] = profile_payload(profile_id)
        cases.append(
            {
                "profile": profile_id,
                "municipality": selected["municipality"],
                "uf": uf,
                "state_name": STATE_NAMES[uf],
            }
        )

    html = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "<!-- FRONT_CSS -->": (FRONT / "styles.css").read_text(encoding="utf-8"),
        "<!-- ANALYSIS_JS -->": (FRONT / "analysis.js").read_text(encoding="utf-8"),
        "<!-- PRODUCER_JS -->": (FRONT / "producer.js").read_text(encoding="utf-8"),
        "<!-- CASE_DATA -->": payload_json({"seed": seed, "cases": cases}),
        "<!-- PROFILE_DATA -->": payload_json(profile_data),
        "<!-- SOIL_HYPOTHESES -->": payload_json(soil_hypotheses),
        "<!-- CROP_CYCLES -->": payload_json(crop_cycles),
        "<!-- RUN_SETTINGS -->": payload_json(run_settings),
        "<!-- ECONOMIC_DATA -->": payload_json({
            "price_snapshot": economic_prices,
        }),
        **map_slots(variant, municipal_boundaries(catalog, [case["profile"] for case in cases])),
    }
    for marker, value in replacements.items():
        marker_count = html.count(marker)
        if marker_count != 1:
            raise ValueError(
                f"Expected exactly one {marker!r} placeholder in {TEMPLATE}, found {marker_count}"
            )
        html = html.replace(marker, value, 1)
    # Non-empty replacements only: an empty slot disappears by design, so absence proves nothing,
    # but a leftover marker with content means a slot was replaced into itself.
    unresolved = [marker for marker, value in replacements.items() if value and marker in html]
    if unresolved:
        raise ValueError(f"Unresolved data placeholders in {TEMPLATE}: {', '.join(unresolved)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=sorted(DEFAULT_OUTPUT), default="classic",
                        help="classic: offline SVG map (docs/visualizacao.html); "
                             "map: Leaflet area selector (docs/visualizacao2.html)")
    parser.add_argument("--output", type=Path, default=None,
                        help="output file (default depends on --variant)")
    parser.add_argument("--seed", type=int, default=2026)
    options = parser.parse_args()
    export_page(options.output or DEFAULT_OUTPUT[options.variant], options.seed, options.variant)


if __name__ == "__main__":
    main()
