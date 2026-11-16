"""Which municipalities a fetcher or a pipeline works on, and how it downloads.

Every fetcher takes the same options:

    --codes 3516200 4104808     these IBGE codes
    --uf PR SC                  every municipality of these states
    --sample                    the validation sample in data/catalog/municipios-amostra.json
    --all                       every municipality of Brazil
    (none)                      the three example municipalities

Municipalities come from the files of `python -m field_shift.ingest.geo`: the IBGE list in
data/geo/municipalities.json and the boundaries in data/geo/municipality-boundaries.json.gz, whose area centroid
is the point the weather and the soil are read at.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
LIST = DATA / "geo" / "municipalities.json"
BOUNDARIES = DATA / "geo" / "municipality-boundaries.json.gz"
COORDINATE_DECIMALS = 5  # about 1 m
SAMPLE = DATA / "catalog" / "municipios-amostra.json"
# The demonstration profiles keep the ids they always had.
EXAMPLES = {"1100023": "ariquemes-ro", "3516200": "franca-sp", "3170701": "varginha-mg"}
USER_AGENT = "FieldShift-OpenData/1.0"
ATTEMPTS = 5


def slug(name: str, uf: str) -> str:
    """Profile id of a municipality: 'São João del Rei', 'MG' -> 'sao-joao-del-rei-mg'."""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(char for char in text if not unicodedata.combining(char)).lower()
    words = "".join(char if char.isalnum() else " " for char in text).split()
    return "-".join([*words, uf.lower()])


def _ring_area_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    area2 = cx = cy = 0.0
    for first, second in zip(ring, ring[1:]):
        cross = first[0] * second[1] - second[0] * first[1]
        area2 += cross
        cx += (first[0] + second[0]) * cross
        cy += (first[1] + second[1]) * cross
    if abs(area2) < 1e-15:
        return 0.0, 0.0, 0.0
    return area2 / 2, cx / (3 * area2), cy / (3 * area2)


def centroid(geometry: dict) -> tuple[float, float]:
    """Area-weighted (longitude, latitude) of a Polygon or MultiPolygon; holes count as negative area."""
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    total = lon = lat = 0.0
    for polygon in polygons:
        for index, ring in enumerate(polygon):
            signed, x, y = _ring_area_centroid(ring)
            area = abs(signed) * (1 if index == 0 else -1)
            total += area
            lon += area * x
            lat += area * y
    if total <= 0:
        raise ValueError("polygon without area")
    return lon / total, lat / total


def municipalities() -> dict[str, dict[str, Any]]:
    """Every municipality with a boundary, by IBGE code: {code, name, uf, lon, lat, id}."""
    for path in (LIST, BOUNDARIES):
        if not path.is_file():
            raise SystemExit(f"{path.relative_to(ROOT)} is missing; run python -m field_shift.ingest.geo")
    listed = {row["code"]: row for row in json.loads(LIST.read_text(encoding="utf-8"))["municipalities"]}
    known = {}
    for feature in json.loads(gzip.decompress(BOUNDARIES.read_bytes()))["features"]:
        code = str(feature["properties"]["codarea"])
        row = listed.get(code)
        if row is None:
            continue
        lon, lat = centroid(feature["geometry"])
        known[code] = {
            "code": code, "name": row["name"], "uf": row["uf"],
            "lon": round(lon, COORDINATE_DECIMALS), "lat": round(lat, COORDINATE_DECIMALS),
            "id": EXAMPLES.get(code) or slug(row["name"], row["uf"]),
        }
    return known


def add_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--codes", nargs="+", metavar="IBGE", help="IBGE municipality codes")
    group.add_argument("--uf", nargs="+", metavar="UF", help="every municipality of these states")
    group.add_argument("--sample", action="store_true", help=f"the municipalities in {SAMPLE.relative_to(ROOT)}")
    group.add_argument("--all", action="store_true", help="every municipality of Brazil")
    parser.add_argument("--refresh", action="store_true", help="download again what is already stored")


def resolve(args: argparse.Namespace) -> list[dict[str, Any]]:
    """The municipalities the options ask for, by code."""
    known = municipalities()
    if args.all:
        codes = list(known)
    elif args.uf:
        wanted = {uf.upper() for uf in args.uf}
        codes = [code for code, entry in known.items() if entry["uf"] in wanted]
    elif args.sample:
        if not SAMPLE.is_file():
            raise SystemExit(f"{SAMPLE.relative_to(ROOT)} is missing; run python data/pipeline/select_sample.py")
        codes = [entry["code"] for entry in json.loads(SAMPLE.read_text(encoding="utf-8"))["municipalities"]]
    else:
        codes = args.codes or list(EXAMPLES)
    unknown = [code for code in codes if code not in known]
    if unknown:
        raise SystemExit(f"Unknown IBGE municipality codes: {', '.join(unknown)}")
    return [known[code] for code in sorted(set(codes))]


def download(url: str, timeout: float = 180, pause: float = 2.0) -> tuple[bytes, str | None]:
    """GET a URL; returns the body and the HTTP Date. Retries what can pass (network, 429, 5xx) with a growing pause."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                if body[:2] == b"\x1f\x8b":
                    body = gzip.decompress(body)
                return body, response.headers.get("Date")
        except urllib.error.HTTPError as failure:
            detail = failure.read()[:200].decode("utf-8", "replace")
            if failure.code not in (429, 500, 502, 503, 504) or attempt == ATTEMPTS:
                raise RuntimeError(f"HTTP {failure.code} from {url}: {detail}") from failure
        except (urllib.error.URLError, TimeoutError, ConnectionError) as failure:
            if attempt == ATTEMPTS:
                raise RuntimeError(f"{url}: {failure}") from failure
        time.sleep(pause * 2 ** attempt)
    raise AssertionError("unreachable")


def write_atomic(path: Path, body: bytes) -> None:
    """Write through a temporary file, so an interrupted run never leaves half a file that looks stored."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    partial.write_bytes(body)
    os.replace(partial, path)


def write_json_gz(path: Path, payload: Any) -> None:
    write_atomic(path, gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), mtime=0))


def read_json_gz(path: Path) -> Any:
    return json.loads(gzip.decompress(path.read_bytes()))


class Report:
    """What one fetcher did, printed at the end and returned as the exit code."""

    def __init__(self, source: str):
        self.source, self.started = source, time.monotonic()
        self.requests = self.bytes = self.stored = self.cached = 0
        self.failures: list[str] = []

    def downloaded(self, size: int) -> None:
        self.requests += 1
        self.bytes += size

    def fail(self, what: str, failure: object) -> None:
        self.failures.append(f"{what}: {failure}")
        print(f"FAIL {self.source} {what}: {failure}", flush=True)

    def finish(self) -> int:
        seconds = time.monotonic() - self.started
        print(json.dumps({
            "source": self.source, "stored": self.stored, "already_stored": self.cached, "requests": self.requests,
            "megabytes": round(self.bytes / 1e6, 2), "seconds": round(seconds, 1), "failures": len(self.failures),
        }))
        return 1 if self.failures else 0
