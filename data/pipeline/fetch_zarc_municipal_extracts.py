"""Download municipality-level extracts from MAPA's open ZARC risk tables."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "data" / "raw" / "mapa-siszarc"
DATASET_PAGE = "https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico"
EXAMPLES = {
    "1100023": "Ariquemes-RO",
    "3516200": "Franca-SP",
    "3170701": "Varginha-MG",
}
RESOURCES = {
    "annual": {
        "id": "139e5a60-1f43-4cc8-aeab-a35dbbf816c0",
        "file": "dados-abertos-tabua-de-risco-safra-2026-2027.csv",
        "output": "zarc-annual-2026-2027-municipal-extract.csv",
        "season": "2026/2027",
    },
    "perennial": {
        "id": "dae65d31-683f-4ac4-ab90-3abd0c1583ba",
        "file": "dados-abertos-tabua-de-risco-safra-perene-olericola-sem-safra.csv",
        "output": "zarc-perennial-2026-municipal-extract.csv",
        "season": "perennial/olericulture/no-season resource current at retrieval",
    },
}


def extract(name: str, resource: dict[str, str]) -> dict[str, object]:
    url = (
        "https://dados.agricultura.gov.br/dataset/6d3d141c-885e-41a4-ab7f-dc8ff323b96f/"
        f"resource/{resource['id']}/download/{resource['file']}"
    )
    response = requests.get(url, stream=True, timeout=(20, 180))
    response.raise_for_status()
    response.encoding = "utf-8-sig"
    reader = csv.reader(response.iter_lines(decode_unicode=True), delimiter=";")
    header = next(reader, None)
    if not header:
        raise RuntimeError(f"Empty MAPA ZARC resource: {url}")
    required = {"Nome_cultura", "geocodigo", *(f"dec{index}" for index in range(1, 37))}
    missing = required - set(header)
    if missing:
        raise RuntimeError(f"MAPA ZARC resource lacks fields {sorted(missing)}: {url}")
    positions = {field: header.index(field) for field in required}
    max_index = max(positions.values())
    output = OUTPUT_DIR / resource["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    row_count = Counter()
    crop_counts: dict[str, Counter] = {code: Counter() for code in EXAMPLES}
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, delimiter=";", lineterminator="\n")
        writer.writerow(header)
        for values in reader:
            if len(values) <= max_index:
                continue
            code = values[positions["geocodigo"]].strip()
            if code not in EXAMPLES:
                continue
            writer.writerow(values)
            row_count[code] += 1
            crop_counts[code][values[positions["Nome_cultura"]].strip()] += 1
    response.close()
    if not sum(row_count.values()):
        raise RuntimeError(f"No example municipality rows found in {url}")

    payload = {
        "publisher": "Ministério da Agricultura e Pecuária (MAPA)",
        "dataset": "Zoneamento Agrícola de Risco Climático (Zarc) - Tábua de Risco",
        "dataset_page": DATASET_PAGE,
        "resource_id": resource["id"],
        "source_url": url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "resource_scope": resource["season"],
        "extract_method": "Original CSV rows retained, filtered only by the three municipality IBGE geocodes in this project.",
        "municipality_filter_field": "geocodigo",
        "municipalities": EXAMPLES,
        "row_count_by_ibge_code": dict(row_count),
        "crop_rows_by_ibge_code": {
            code: dict(sorted(counts.items())) for code, counts in crop_counts.items()
        },
        "file": output.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "license": "Creative Commons Attribution (MAPA open-data catalog)",
    }
    sidecar = output.with_suffix(output.suffix + ".source.json")
    sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{name}: {sum(row_count.values())} linhas oficiais filtradas -> {output.relative_to(ROOT)}")
    return payload


def main() -> None:
    for name, resource in RESOURCES.items():
        extract(name, resource)


if __name__ == "__main__":
    main()
