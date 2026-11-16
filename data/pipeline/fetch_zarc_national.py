"""Download the MAPA ZARC risk tables (Tábua de Risco) of the whole country, once, split by state.

The two national CSV files (about 800 MB together) are read as a stream and their rows written unchanged, one
gzip file per state:

    data/raw/mapa-siszarc/by-uf/<annual|perennial>/<UF>.csv.gz   (+ source.json per table)

After that the planting windows of any municipality are read from the file of its state, without the network.
Lines "progress <0-1>" are printed while it downloads, for whoever shows a progress bar.

Usage: python data/pipeline/fetch_zarc_national.py [--refresh]
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

from targets import DATA, ROOT, USER_AGENT, Report

OUT = DATA / "raw" / "mapa-siszarc" / "by-uf"
DATASET = "https://dados.agricultura.gov.br/dataset/6d3d141c-885e-41a4-ab7f-dc8ff323b96f"
# Same resources as fetch_zarc_municipal_extracts.py. The server does not say the size; these are the sizes measured.
RESOURCES = {
    "annual": ("139e5a60-1f43-4cc8-aeab-a35dbbf816c0", "dados-abertos-tabua-de-risco-safra-2026-2027.csv", 248e6),
    "perennial": ("dae65d31-683f-4ac4-ab90-3abd0c1583ba", "dados-abertos-tabua-de-risco-safra-perene-olericola-sem-safra.csv", 550e6),
}
EXPECTED_TOTAL = sum(size for _, _, size in RESOURCES.values())
UF_BY_PREFIX = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA",
    "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS",
    "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}


def state_file(kind: str, uf: str):
    return OUT / kind / f"{uf}.csv.gz"


def stored(kind: str) -> bool:
    return (OUT / kind / "source.json").is_file()


def rows_of(kind: str, uf: str, codes: set[str]):
    """Header and the rows of the given municipalities in the stored table of a state."""
    path = state_file(kind, uf)
    if not path.is_file():
        return [], []
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, delimiter=";")
        header = next(reader)
        code_at = header.index("geocodigo")
        return header, [values for values in reader if len(values) > code_at and values[code_at].strip() in codes]


class _Counting(io.RawIOBase):
    """Counts the bytes read from the HTTP answer and prints the share of the whole download done."""

    def __init__(self, raw, before: float):
        self.raw, self.size, self.before, self.shown = raw, 0, before, -1

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        chunk = self.raw.read(len(buffer))
        buffer[:len(chunk)] = chunk
        self.size += len(chunk)
        step = int(min(0.99, (self.before + self.size) / EXPECTED_TOTAL) * 100)
        if step != self.shown:
            self.shown = step
            print(f"progress {step / 100:.2f}", flush=True)
        return len(chunk)


def download(kind: str, before: float, report: Report) -> None:
    resource, name, _ = RESOURCES[kind]
    url = f"{DATASET}/resource/{resource}/download/{name}"
    folder = OUT / kind
    folder.mkdir(parents=True, exist_ok=True)
    writers: dict[str, tuple] = {}
    rows: dict[str, int] = {}
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            counted = _Counting(response, before)
            reader = csv.reader(io.TextIOWrapper(counted, encoding="utf-8-sig", newline=""), delimiter=";")
            header = next(reader)
            code_at = header.index("geocodigo")
            for values in reader:
                uf = UF_BY_PREFIX.get(values[code_at].strip()[:2]) if len(values) > code_at else None
                if uf is None:
                    continue
                if uf not in writers:
                    stream = gzip.open(folder / f"{uf}.csv.gz.part", "wt", encoding="utf-8-sig", newline="")
                    writers[uf] = (stream, csv.writer(stream, delimiter=";", lineterminator="\n"))
                    writers[uf][1].writerow(header)
                writers[uf][1].writerow(values)
                rows[uf] = rows.get(uf, 0) + 1
    finally:
        for stream, _ in writers.values():
            stream.close()
    for uf in writers:      # only a complete download replaces what was stored
        os.replace(folder / f"{uf}.csv.gz.part", state_file(kind, uf))
    report.downloaded(counted.size)
    report.stored += len(writers)
    (folder / "source.json").write_text(json.dumps({
        "publisher": "Ministério da Agricultura e Pecuária (MAPA)",
        "dataset": "Zoneamento Agrícola de Risco Climático (Zarc) - Tábua de Risco",
        "source_url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "bytes": counted.size,
        "extract_method": "Original CSV rows retained, split by the state of the IBGE geocode.",
        "rows_by_state": dict(sorted(rows.items())),
        "license": "Creative Commons Attribution (MAPA open-data catalog)",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"mapa-zarc {kind}: {sum(rows.values())} rows in {len(rows)} states, {counted.size / 1e6:.0f} MB", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="download again what is already stored")
    args = parser.parse_args()
    report = Report("mapa-zarc")
    before = 0.0
    for kind, (_, _, size) in RESOURCES.items():
        if stored(kind) and not args.refresh:
            report.cached += 1
        else:
            try:
                download(kind, before, report)
            except (OSError, ValueError) as failure:
                report.fail(kind, failure)
        before += size
    print("progress 1.00", flush=True)
    return report.finish()


if __name__ == "__main__":
    sys.exit(main())
