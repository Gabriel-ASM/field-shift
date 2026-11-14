"""Build unified views of the v2 contracts from the schema files.

Outputs (regenerate after any schema change):
  data/contracts/v2/views/contracts-tree.json   one JSON for jsoncrack.com: every $ref is
                                               inlined, so connections show up as nesting
  data/contracts/v2/views/contracts-graph.json  nodes + typed edges + field status
  docs/contracts-v2.html                        web page with the map and one section per contract

Three kinds of connection exist between contracts and only the first is visible to
JSON Schema tools:
  ref      a "$ref" to another file or definition
  id       a string field that must match an id in another contract (e.g. state.crop -> crop.name)
  pointer  a JSON Pointer string resolved at runtime (effect.target -> node fields)

`id` links and the field status (where each value comes from, what reads it today) are
written by hand below, because no schema keyword expresses them.

Usage: python data/pipeline/build_contract_views.py [--fragment PATH]
  --fragment also writes the page body without the <html>/<head> wrapper (for hosts that add their own).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "data" / "contracts" / "v2"
VIEWS = V2 / "views"
TEMPLATE = Path(__file__).resolve().parent / "templates" / "contracts_view.html"
PAGE = ROOT / "docs" / "contracts-v2.html"

# String fields that must match an id defined in another contract.
ID_LINKS = [
    ("markov", "initial_state", "markov", "state.id"),
    ("markov", "state.crop", "crop", "name"),
    ("markov", "state.allowed_actions[]", "action", "id"),
    ("markov", "transition.from", "markov", "state.id"),
    ("markov", "transition.to", "markov", "state.id"),
    ("markov", "transition.action", "action", "id"),
    ("markov", "node.state", "markov", "state.id"),
    ("monte_carlo", "scenario.initial_state", "markov", "state.id"),
    ("monte_carlo", "rotation_policy.sequence[]", "crop", "name"),
    ("monte_carlo", "rotation_policy.fallback", "markov", "state.id"),
    ("monte_carlo", "profile", "profile", "data/profiles/<id>"),
    ("event", "crops[]", "crop", "name"),
]
# JSON Pointer strings resolved against the trajectory node.
POINTER_LINKS = [
    ("effect", "target", "markov#node", "written by effects"),
    ("effect", "condition.path", "markov#node", "read by conditions (when)"),
    ("event", "when", "markov#node", "event can start only while conditions hold"),
]
# Links that should exist but do not yet.
MISSING_LINKS: list[tuple[str, str, str, str]] = []

# Where each node value comes from today and whether the current app reads it.
# status: used | upstream | available | partial | none
# "used"     read by field_shift/ (engine or page)
# "upstream" consumed by data/pipeline to build something the app reads
# "available" in data/profiles but nothing reads it
# "partial"  some source exists but is not wired or has gaps
# "none"     no data in the repo
# "simulation" set by the simulation itself, not an input
FIELD_STATUS = {
    "climate.lat": ("available", "Profile centroid (soil-profile.json sample_point)", "Location only"),
    "climate.long": ("available", "Profile centroid (soil-profile.json sample_point)", "Location only"),
    "climate.alt": ("none", "Not collected", ""),
    "climate.month": ("upstream", "Derived from date_local", "Fortnight water periods and ZARC calendar"),
    "climate.season": ("none", "Derivable from month", "Nothing reads it"),
    "climate.solar_incidence": ("partial", "NASA POWER ALLSKY_SFC_SW_DWN, MJ/m2/day (gaps flagged)", "ET0 (Hargreaves fallback when missing)"),
    "climate.weather.pluviosity": ("upstream", "NASA POWER PRECTOTCORR, precipitation_mm", "Fortnight water balance -> water states"),
    "climate.weather.temperature": ("upstream", "NASA POWER T2M_MAX/T2M_MIN", "ET0"),
    "climate.weather.relative_humidity": ("upstream", "NASA POWER RH2M", "ET0"),
    "soil.order": ("partial", "IBGE SiBCS (R045) collected; sibcs_order is null in every profile", "Nothing reads it"),
    "soil.N2": ("none", "Not downloaded (SoilGrids has a nitrogen layer)", "Nothing reads it"),
    "soil.pH": ("available", "SoilGrids phh2o -> ph_water per layer", "Nothing reads it"),
    "soil.temperature_per_depth": ("none", "Not collected", "Nothing reads it"),
    "soil.organic_carbon": ("used", "SoilGrids soc -> organic_carbon_g_kg, 0-30 cm", "Carbon Monte Carlo, transition weights, yield"),
    "soil.available_water_capacity": ("used", "SoilGrids texture + Saxton & Rawls -> available_water_capacity_mm", "Water balance"),
    "soil.available_water_fraction": ("used", "Water balance state (v1 water_low / medium / high)", "Water states and water factor"),
    "climate.weather.et0": ("upstream", "Computed from NASA POWER (eto_mm_day, FAO-56 / Hargreaves)", "Water balance"),
    "markov.node.financial.yield": ("used", "PAM yield (kg/ha)", "NPV"),
    "markov.node.financial.price": ("used", "PAM real price, IPCA-adjusted", "NPV"),
    "markov.node.financial.cost": ("used", "CONAB production costs (economic-benchmarks.json)", "NPV"),
    "markov.node.financial.revenue": ("used", "PAM yield x PAM real price", "NPV"),
    "markov.node.financial.cash": ("simulation", "Running balance during the trajectory", ""),
    "markov.node.state": ("simulation", "Current Markov state", ""),
    "markov.node.day": ("simulation", "Trajectory clock", ""),
    "markov.state.duration_days": ("used", "crop-cycle-assumptions.json", "Crop clock in Monte Carlo"),
    "markov.transition.probability": ("used", "PAM dominant-crop counts + Dirichlet prior", "Markov draws"),
}
# Values the current app reads, and the v2 field that now holds each one.
V2_GAPS = [
    ("Soil water capacity (AWC)", "soil.available_water_capacity", "SoilGrids texture + Saxton & Rawls -> available_water_capacity_mm", "Water balance"),
    ("Water state", "soil.available_water_fraction", "states.json water_low / water_medium / water_high", "v1 Markov state dimension; in v2 a continuous value that edges test with 'when'"),
    ("Soil organic carbon", "soil.organic_carbon", "SoilGrids soc -> organic_carbon_g_kg, 0-30 cm", "Carbon Monte Carlo, transition weights, yield"),
    ("Reference evapotranspiration (ET0)", "climate.weather.et0", "Computed from NASA POWER (eto_mm_day)", "Water balance"),
    ("Crop coefficient (Kc)", "crop.kc_annual_effective, crop.stage_props.kc", "crop-water-parameters.json, kc_annual_effective", "Crop water demand (ETc = Kc x ET0)"),
    ("Planting windows (ZARC)", "crop.planting_windows", "MAPA SISZARC per municipality", "When a destination crop can be sown"),
    ("Yield and price", "markov.node.financial.yield, .price", "PAM yield and price, Yahoo futures", "Revenue = yield x price at harvest"),
]


def load_schemas() -> dict[str, dict]:
    schemas = {}
    for path in sorted(V2.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        # Skip bundles such as allcontracts.json: a schema is an object with $schema.
        if isinstance(data, dict) and "$schema" in data:
            schemas[path.stem] = data
    return schemas


def split_ref(ref: str, current: str) -> tuple[str, str]:
    file_part, _, fragment = ref.partition("#")
    contract = Path(file_part).stem if file_part else current
    return contract, fragment


def resolve(schemas: dict, contract: str, fragment: str) -> dict:
    node = schemas[contract]
    for part in [p for p in fragment.split("/") if p]:
        node = node[part]
    return node


def describe_leaf(schema: dict) -> str:
    bits = []
    if "enum" in schema:
        values = [str(v) for v in schema["enum"]]
        shown = " | ".join(values[:6]) + (f" | ... ({len(values)})" if len(values) > 6 else "")
        bits.append(f"enum: {shown}")
    elif "type" in schema:
        kind = schema["type"]
        bits.append(" or ".join(kind) if isinstance(kind, list) else kind)
    elif "oneOf" in schema:
        bits.append("number or distribution")
    else:
        bits.append("any")
    if schema.get("unit"):
        bits.append(f"[{schema['unit']}]")
    low, high = schema.get("minimum"), schema.get("maximum")
    if low is not None or high is not None:
        bits.append(f"{'' if low is None else low}..{'' if high is None else high}")
    return " ".join(bits)


def field_type(schema: dict) -> str:
    if "$ref" in schema:
        return "-> " + schema["$ref"]
    if schema.get("type") == "array" and "items" in schema:
        return "array of " + field_type(schema["items"])
    if "properties" in schema:
        return "object"
    return describe_leaf(schema)


def tree(schemas: dict, contract: str, schema: dict, trail: tuple = ()) -> object:
    """Readable tree for jsoncrack: '$ref' targets are inlined under a 'name -> target' key."""
    if "$ref" in schema:
        target, fragment = split_ref(schema["$ref"], contract)
        label = f"{target}.json" + (f"#{fragment}" if fragment else "")
        if label in trail:
            return f"(cycle back to {label})"
        return {f"-> {label}": tree(schemas, target, resolve(schemas, target, fragment), trail + (label,))}
    if schema.get("type") == "array" and "items" in schema:
        return {"[ ] each item": tree(schemas, contract, schema["items"], trail)}
    if "properties" in schema:
        required = set(schema.get("required", []))
        out = {}
        for name, sub in schema["properties"].items():
            key = name + (" *" if name in required else "")
            out[key] = tree(schemas, contract, sub, trail)
        return out
    if isinstance(schema.get("additionalProperties"), dict) and "propertyNames" in schema:
        return {
            "{ any key }": tree(schemas, contract, schema["propertyNames"], trail),
            "{ value }": tree(schemas, contract, schema["additionalProperties"], trail),
        }
    return describe_leaf(schema)


def collect_fields(schemas: dict, contract: str, schema: dict, prefix: str, out: list, refs: list, seen: set) -> None:
    """Flatten one contract into field rows and record its $ref edges (not following them)."""
    if "$ref" in schema:
        target, fragment = split_ref(schema["$ref"], contract)
        refs.append((contract, prefix, target, fragment))
        return
    if schema.get("type") == "array" and "items" in schema:
        collect_fields(schemas, contract, schema["items"], prefix + "[]", out, refs, seen)
        return
    if "properties" in schema:
        required = set(schema.get("required", []))
        for name, sub in schema["properties"].items():
            path = f"{prefix}.{name}" if prefix else name
            if "properties" not in sub or sub.get("description"):
                out.append({
                    "path": path,
                    "type": field_type(sub),
                    "required": name in required,
                    "description": sub.get("description", sub.get("$comment", "")),
                })
            collect_fields(schemas, contract, sub, path, out, refs, seen)
        return
    if isinstance(schema.get("additionalProperties"), dict):
        collect_fields(schemas, contract, schema["additionalProperties"], prefix + ".{key}", out, refs, seen)


def build_graph(schemas: dict) -> dict:
    nodes, edges = [], []
    for name, schema in schemas.items():
        fields, refs = [], []
        collect_fields(schemas, name, schema, "", fields, refs, set())
        for definition, body in schema.get("definitions", {}).items():
            collect_fields(schemas, name, body, definition, fields, refs, set())
        unique = {}
        for field in fields:
            unique.setdefault(field["path"], field)
        nodes.append({
            "id": name,
            "file": f"{name}.json",
            "title": schema.get("title", ""),
            "comment": schema.get("$comment", ""),
            "definitions": list(schema.get("definitions", {})),
            "fields": list(unique.values()),
        })
        for source, path, target, fragment in refs:
            kind = "internal" if target == source else "ref"
            edges.append({"kind": kind, "from": source, "field": path, "to": target, "target": fragment or "(whole contract)"})
    for source, field, target, target_field in ID_LINKS:
        edges.append({"kind": "id", "from": source, "field": field, "to": target, "target": target_field})
    for source, field, target, note in POINTER_LINKS:
        edges.append({"kind": "pointer", "from": source, "field": field, "to": target, "target": note})
    for source, field, target, note in MISSING_LINKS:
        edges.append({"kind": "missing", "from": source, "field": field, "to": target, "target": note})

    # Node fields (what effects can target), flattened with their source contract.
    node_fields = []
    node_schema = schemas["markov"]["definitions"]["node"]
    for name, sub in node_schema["properties"].items():
        if "$ref" in sub:
            target, _ = split_ref(sub["$ref"], "markov")
            for row in next(n for n in nodes if n["id"] == target)["fields"]:
                if "[]" in row["path"] or "{key}" in row["path"]:
                    continue  # items of a list are not separate node values
                node_fields.append({"pointer": f"/{name}/" + row["path"].replace(".", "/"), "key": f"{target}.{row['path']}", "type": row["type"]})
        elif "properties" in sub:
            for child, leaf in sub["properties"].items():
                node_fields.append({"pointer": f"/{name}/{child}", "key": f"markov.node.{name}.{child}", "type": describe_leaf(leaf)})
        else:
            node_fields.append({"pointer": f"/{name}", "key": f"markov.node.{name}", "type": describe_leaf(sub)})

    examples = {}
    for path in sorted((V2 / "examples").glob("*.json")):
        examples[path.name] = json.loads(path.read_text(encoding="utf-8"))
    written, read = {}, {}
    def walk(value, example):
        if isinstance(value, dict):
            if "target" in value and "operation" in value:
                written.setdefault(value["target"], set()).add(example)
            if "path" in value and "op" in value:
                read.setdefault(value["path"], set()).add(example)
            for child in value.values():
                walk(child, example)
        elif isinstance(value, list):
            for child in value:
                walk(child, example)
    for name, data in examples.items():
        walk(data, name)
    for row in node_fields:
        status = FIELD_STATUS.get(row["key"], ("none", "", ""))
        row.update({
            "status": status[0], "source": status[1], "read_by_app": status[2],
            "written_in_examples": sorted(written.get(row["pointer"], [])),
            "read_in_examples": sorted(read.get(row["pointer"], [])),
        })
    return {
        "generated_from": sorted(f"{n}.json" for n in schemas),
        "nodes": nodes,
        "edges": edges,
        "node_fields": node_fields,
        "field_status_extra": {k: v for k, v in FIELD_STATUS.items() if not k.startswith(("climate.", "soil.", "markov.node."))},
        "v2_gaps": [dict(zip(("value", "v2_field", "v1_source", "read_by_app"), gap)) for gap in V2_GAPS],
        "node_description": schemas["markov"]["definitions"]["node"].get("description", ""),
        "examples": sorted(examples),
    }


def build_tree(schemas: dict, graph: dict) -> dict:
    incoming = {e["to"] for e in graph["edges"] if e["kind"] == "ref" and e["target"] == "(whole contract)"}
    roots = [name for name in schemas if name not in incoming]
    return {
        "field_shift_contracts_v2": {
            "how_to_read": "Each '-> file.json' key is a $ref, inlined here. '*' marks required fields. 'id_links' and 'pointer_links' are connections JSON Schema cannot express.",
            "entry_points": {f"{name}.json": tree(schemas, name, schemas[name]) for name in roots},
            "id_links": [f"{e['from']}.{e['field']}  ==  {e['to']}.{e['target']}" for e in graph["edges"] if e["kind"] == "id"],
            "pointer_links": [f"{e['from']}.{e['field']}  ->  {e['to']} ({e['target']})" for e in graph["edges"] if e["kind"] == "pointer"],
            "missing_links": [f"{e['from']}.{e['field']}  -x-  {e['to']}: {e['target']}" for e in graph["edges"] if e["kind"] == "missing"],
            "node_fields_effects_can_target": {r["pointer"]: f"{r['type']}  ({r['status']})" for r in graph["node_fields"]},
        }
    }


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
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
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
