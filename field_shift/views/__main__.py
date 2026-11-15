"""Write views/contracts-tree.json, views/contracts-graph.json and docs/contracts-v2.html.

Usage: python -m field_shift.views [--fragment PATH]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .. import ROOT
from ..contracts import load_schemas
from .graph import PAGE, TEMPLATE, VIEWS, build_graph, build_tree

PAGE_WRAPPER = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
</head>
<body>
{body}
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the contract views")
    parser.add_argument("--fragment", type=Path, help="also write the page without the html/head wrapper")
    args = parser.parse_args()
    schemas = load_schemas()
    graph = build_graph(schemas)
    VIEWS.mkdir(exist_ok=True)
    (VIEWS / "contracts-graph.json").write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (VIEWS / "contracts-tree.json").write_text(json.dumps(build_tree(schemas, graph), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    body = TEMPLATE.read_text(encoding="utf-8").replace("/*GRAPH_DATA*/null", json.dumps(graph, ensure_ascii=False))
    PAGE.write_text(PAGE_WRAPPER.format(body=body), encoding="utf-8")
    if args.fragment:
        args.fragment.write_text(body, encoding="utf-8")
    for path in (VIEWS / "contracts-tree.json", VIEWS / "contracts-graph.json", PAGE):
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
