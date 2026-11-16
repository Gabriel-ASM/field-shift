"""Download the SoilGrids 2.0 soil profile at the centroid of any set of municipalities.

One request to the ISRIC REST API per municipality gives the seven properties the profile needs (clay, sand,
silt, pH, organic carbon, total nitrogen, bulk density) in the five layers down to 100 cm. The answer is stored
unchanged in data/raw/soilgrids/municipalities/<code>.json.

The API allows about five requests a minute, so the requests are spaced: 30 municipalities take about 6
minutes and Brazil about 19 hours. SoilGrids has no prediction over water and cities, so a centroid without one
is tried again in rings around it, out to about 40 km; the answer records the point that was used. Lines
"progress <0-1>" are printed for whoever shows a progress bar.

Usage: python data/pipeline/fetch_soil.py [--sample | --all | --uf PR | --codes ...] [--refresh] [--pause 12]
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from targets import DATA, Report, add_arguments, download, resolve, write_atomic

OUT = DATA / "raw" / "soilgrids" / "municipalities"
PROPERTIES = ("clay", "sand", "silt", "phh2o", "soc", "nitrogen", "bdod")
DEPTHS = ("0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm")
TOPSOIL = DEPTHS[:3]
# Offsets in degrees tried when the centroid itself has no prediction: rings of about 5, 10, 20 and 40 km, west
# first (most Brazilian cities without a prediction are on the coast, with the farmland inland).
DIRECTIONS = ((-1, 0), (0, 1), (0, -1), (1, 0), (-0.7, 0.7), (-0.7, -0.7), (0.7, 0.7), (0.7, -0.7))
NEARBY = [(0.0, 0.0)] + [(round(dx * step, 4), round(dy * step, 4)) for step in (0.045, 0.09, 0.18, 0.36) for dx, dy in DIRECTIONS]


def path_for(code: str):
    return OUT / f"{code}.json"


def url_for(lon: float, lat: float) -> str:
    query = "".join(f"&property={name}" for name in PROPERTIES) + "".join(f"&depth={depth}" for depth in DEPTHS)
    return f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lon}&lat={lat}{query}&value=mean"


def complete(document: dict) -> bool:
    """Texture, pH and carbon in every layer; nitrogen and density in the topsoil (what build_profiles needs)."""
    layers = {layer["name"]: {depth["label"]: depth["values"]["mean"] for depth in layer["depths"]} for layer in document["properties"]["layers"]}
    for name in PROPERTIES:
        needed = TOPSOIL if name in ("nitrogen", "bdod") else DEPTHS
        if any(layers.get(name, {}).get(depth) is None for depth in needed):
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_arguments(parser)
    parser.add_argument("--pause", type=float, default=12.0, help="seconds between requests (the API allows about 5 a minute)")
    args = parser.parse_args()
    report = Report("soilgrids")
    pending = []
    for target in resolve(args):
        if path_for(target["code"]).is_file() and not args.refresh:
            report.cached += 1
        else:
            pending.append(target)
    last = 0.0
    for done, target in enumerate(pending, start=1):
        stored = False
        try:
            for attempt, (dx, dy) in enumerate(NEARBY):
                if len(pending) == 1:
                    print(f"progress {attempt / len(NEARBY):.2f}", flush=True)
                lon, lat = round(target["lon"] + dx, 5), round(target["lat"] + dy, 5)
                time.sleep(max(0.0, last + args.pause - time.monotonic()))
                url = url_for(lon, lat)
                body, retrieved = download(url, timeout=120, pause=args.pause)
                last = time.monotonic()
                report.downloaded(len(body))
                document = json.loads(body)
                if complete(document):
                    document["field_shift"] = {
                        "url": url, "retrieved_at_http": retrieved, "code": target["code"],
                        "centroid": {"lon": target["lon"], "lat": target["lat"]}, "point": {"lon": lon, "lat": lat},
                        "moved_from_centroid": bool(dx or dy),
                    }
                    write_atomic(path_for(target["code"]), (json.dumps(document, ensure_ascii=False) + "\n").encode("utf-8"))
                    report.stored += 1
                    stored = True
                    break
            if not stored:
                report.fail(target["id"], "SoilGrids has no soil prediction at the centre of this municipality or within 40 km of it")
        except (RuntimeError, KeyError, ValueError) as failure:
            report.fail(target["id"], failure)
        print(f"soilgrids {done}/{len(pending)} {target['id']}", flush=True)
    return report.finish()


if __name__ == "__main__":
    sys.exit(main())
