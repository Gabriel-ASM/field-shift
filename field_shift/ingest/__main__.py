"""Generate the v2 documents from v1 data, validate them, and write them to data/v2.

Usage: python -m field_shift.ingest [--mongo URI]
With --mongo the documents are also upserted into the database (collections get their validators first).
"""

from __future__ import annotations

import argparse
import json
import sys

from .. import DATA
from ..contracts import check, validate
from . import build_chain, build_profile, profile_ids

OUT = DATA / "v2"


def generate() -> tuple[dict[str, dict], dict[str, dict], list[dict], list[str]]:
    chains, profiles, reports, errors = {}, {}, [], []
    for profile in profile_ids():
        chain, report = build_chain(profile)
        document = build_profile(profile, chain["initial_state"])
        for name, payload in (("markov", chain), ("profile", document)):
            found = validate(name, payload) or check(name, payload)
            errors += [f"{profile} {name}: {message}" for message in found]
        chains[profile], profiles[profile] = chain, document
        reports.append(report)
    return chains, profiles, reports, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mongo", help="MongoDB URI to upsert into, e.g. mongodb://localhost:27017")
    parser.add_argument("--database", default="field_shift")
    args = parser.parse_args()

    chains, profiles, reports, errors = generate()
    if errors:
        print("\n".join(f"FAIL {message}" for message in errors))
        return 1
    for kind, documents in (("chains", chains), ("profiles", profiles)):
        (OUT / kind).mkdir(parents=True, exist_ok=True)
        for key, document in documents.items():
            (OUT / kind / f"{key}.json").write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "ingestion-report.json").write_text(json.dumps({"chains": reports}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for report in reports:
        kept = sum(1 for row in report["rows"] if row["kept"])
        print(f"ok   {report['profile']}: {len(chains[report['profile']]['transitions'])} edges from {kept} crops; "
              f"initial state {chains[report['profile']]['initial_state']}")
    if args.mongo:
        from ..db import connect, ensure_collections, upsert
        database = connect(args.mongo, args.database)
        ensure_collections(database)
        for document in chains.values():
            upsert(database, "chains", document)
        for document in profiles.values():
            upsert(database, "profiles", document)
        print(f"ok   upserted {len(chains)} chains and {len(profiles)} profiles into {args.database}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
