"""Download the PAM crop history (IBGE SIDRA table 5457) of any set of municipalities.

SIDRA answers at most 100,000 values per request. One municipality is 4 variables x 38 years x 11 crops
= 1,672 values, so the municipalities are asked for in batches of 50 (about 112 requests for Brazil).
Each municipality is stored on its own in data/raw/ibge/pam/<code>.json.gz, in the layout of
pam-municipal-5457-1988-2025.json, so an interrupted run resumes where it stopped.

Usage: python data/pipeline/fetch_pam_targets.py [--sample | --all | --uf PR | --codes ...] [--refresh]
"""

from __future__ import annotations

import argparse
import json
import sys

from fetch_pam import PRODUCTS, VARIABLES
from targets import DATA, Report, add_arguments, download, resolve, write_json_gz

OUT = DATA / "raw" / "ibge" / "pam"
PERIOD = "1988-2025"
BATCH = 50
VALUES_PER_REQUEST = 100_000
assert BATCH * len(VARIABLES) * len(PRODUCTS) * 38 <= VALUES_PER_REQUEST


def url_for(codes: list[str]) -> str:
    return (f"https://apisidra.ibge.gov.br/values/t/5457/n6/{','.join(codes)}/v/{','.join(VARIABLES)}"
            f"/p/{PERIOD}/c782/{','.join(PRODUCTS)}?formato=json")


def path_for(code: str):
    return OUT / f"{code}.json.gz"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_arguments(parser)
    args = parser.parse_args()
    report = Report("ibge-pam")
    pending = []
    for target in resolve(args):
        if path_for(target["code"]).is_file() and not args.refresh:
            report.cached += 1
        else:
            pending.append(target["code"])
    for start in range(0, len(pending), BATCH):
        codes = pending[start:start + BATCH]
        url = url_for(codes)
        try:
            body, retrieved = download(url)
        except RuntimeError as failure:
            report.fail(f"{codes[0]}..{codes[-1]}", failure)
            continue
        report.downloaded(len(body))
        records: dict[str, list] = {code: [] for code in codes}
        for row in json.loads(body)[1:]:
            records[str(row["D1C"])].append(row)
        for code in codes:      # a municipality without any record is stored too: it has no PAM history
            write_json_gz(path_for(code), {
                "source": {
                    "publisher": "IBGE", "survey": "Produção Agrícola Municipal (PAM)", "table": 5457, "url": url_for([code]),
                    "batch_url": url, "period": PERIOD, "retrieved_at_http": retrieved, "variables": VARIABLES,
                    "classification": {"id": 782, "name": "Produto das lavouras temporárias e permanentes", "categories": PRODUCTS},
                },
                "records": records[code],
            })
            report.stored += 1
        print(f"ibge-pam {min(start + BATCH, len(pending))}/{len(pending)}", flush=True)
    return report.finish()


if __name__ == "__main__":
    sys.exit(main())
