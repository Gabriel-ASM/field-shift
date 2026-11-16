"""Download NASA POWER daily weather for any set of municipalities, once per grid cell.

POWER answers a point with the values of the grid cell it falls in. The meteorology comes from MERRA-2
(0.5 deg latitude x 0.625 deg longitude, cells centred on multiples of those steps) and the solar radiation from
CERES (1 deg x 1 deg, cell edges on whole degrees). Two municipalities in the same MERRA-2 cell and the same
CERES cell get the same series, so the series is stored once per pair of cells:

    data/raw/nasa_power/cells/<cell>.json.gz

That turns the 5,570 municipalities of Brazil into roughly 2,400-3,000 requests. `cell_of` gives the file of a
point; build_profiles.py reads the weather of a municipality through it.

Usage: python data/pipeline/fetch_power.py [--sample | --all | --uf PR | --codes ...] [--refresh] [--workers 4]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor

from targets import DATA, Report, add_arguments, download, resolve, write_json_gz

OUT = DATA / "raw" / "nasa_power" / "cells"
PARAMETERS = ("T2M_MAX", "T2M_MIN", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR")
START, END = "19810101", "20261106"     # the period of the example profiles (build_profiles.py)
MERRA_LAT, MERRA_LON = 0.5, 0.625


def cell_of(lon: float, lat: float) -> str:
    """Name of the pair of grid cells (MERRA-2 centre, CERES south-west corner) a point falls in."""
    merra_lat = round(lat / MERRA_LAT) * MERRA_LAT
    merra_lon = round(lon / MERRA_LON) * MERRA_LON
    return f"m{merra_lat:+06.2f}_{merra_lon:+08.3f}_c{math.floor(lat):+03d}_{math.floor(lon):+04d}"


def path_for(lon: float, lat: float):
    return OUT / f"{cell_of(lon, lat)}.json.gz"


def url_for(lon: float, lat: float) -> str:
    return (f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters={','.join(PARAMETERS)}"
            f"&community=AG&longitude={lon}&latitude={lat}&start={START}&end={END}&format=JSON")


def fetch_cell(target: dict) -> tuple[dict, int]:
    url = url_for(target["lon"], target["lat"])
    body, retrieved = download(url, timeout=300)
    document = json.loads(body)
    days = document["properties"]["parameter"]["PRECTOTCORR"]
    if len(days) < 16000:
        raise RuntimeError(f"only {len(days)} days in the answer")
    document["field_shift"] = {
        "url": url, "retrieved_at_http": retrieved, "cell": cell_of(target["lon"], target["lat"]),
        "requested_for": {"code": target["code"], "lon": target["lon"], "lat": target["lat"]},
    }
    write_json_gz(path_for(target["lon"], target["lat"]), document)
    return target, len(body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_arguments(parser)
    parser.add_argument("--workers", type=int, default=4, help="requests at a time (POWER asks for few)")
    args = parser.parse_args()
    report = Report("nasa-power")
    targets = resolve(args)
    cells: dict[str, dict] = {}
    for target in targets:
        cells.setdefault(cell_of(target["lon"], target["lat"]), target)
    pending = []
    for target in cells.values():
        if path_for(target["lon"], target["lat"]).is_file() and not args.refresh:
            report.cached += 1
        else:
            pending.append(target)
    print(f"nasa-power: {len(targets)} municipalities in {len(cells)} cells, {len(pending)} to download", flush=True)

    def attempt(target: dict):
        try:
            return fetch_cell(target)
        except (RuntimeError, KeyError, ValueError) as failure:
            return target, failure

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for done, (target, outcome) in enumerate(pool.map(attempt, pending), start=1):
            if isinstance(outcome, int):
                report.downloaded(outcome)
                report.stored += 1
            else:
                report.fail(cell_of(target["lon"], target["lat"]), outcome)
            if done % 10 == 0 or done == len(pending):
                print(f"nasa-power {done}/{len(pending)}", flush=True)
    return report.finish()


if __name__ == "__main__":
    sys.exit(main())
