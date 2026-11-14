"""Generate the offline, data-backed Markov and Monte Carlo demonstration."""

from argparse import ArgumentParser
import json
from pathlib import Path
from random import Random


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "catalog" / "municipios-exemplo-brasil.json"
TEMPLATE = Path(__file__).with_name("replay.html")
STATE_NAMES = {"RO": "Rondônia", "SP": "São Paulo", "MG": "Minas Gerais"}


def export_page(output: Path, seed: int) -> None:
    catalog = json.loads((ROOT / "data" / "catalog" / "perfis-exemplo.json").read_text(encoding="utf-8"))
    saved = json.loads((ROOT / "data" / "processed" / "demo-simulation-results.json").read_text(encoding="utf-8"))
    rng = Random(seed)
    by_uf = {}
    for profile in catalog["profiles"]:
        by_uf.setdefault(profile["uf"], []).append(profile)
    cases = []
    profile_data = {}
    saved_by_id = {result["profile"]: result for result in saved["results"]}
    for uf in ("RO", "SP", "MG"):
        selected = rng.choice(by_uf[uf])
        profile_id = selected["profile"]
        profile_dir = ROOT / "data" / "profiles" / profile_id
        manifest = json.loads((profile_dir / "manifest.json").read_text(encoding="utf-8"))
        profile_data[profile_id] = {
            "location": manifest["location"],
            "climate_summary": json.loads((profile_dir / "climate-summary.json").read_text(encoding="utf-8")),
            "soil": json.loads((profile_dir / "soil-profile.json").read_text(encoding="utf-8")),
            "states": json.loads((profile_dir / "states.json").read_text(encoding="utf-8")),
            "transitions": json.loads((profile_dir / "transitions.json").read_text(encoding="utf-8")),
            "environment": json.loads((profile_dir / "environment.json").read_text(encoding="utf-8")),
            "reference_simulation": saved_by_id[profile_id],
        }
        cases.append({
            "profile": profile_id,
            "municipality": selected["municipality"],
            "uf": uf,
            "state_name": STATE_NAMES[uf],
        })
    case_payload = json.dumps({
        "seed": seed,
        "selection_rule": catalog["selection_rule"],
        "cases": cases,
    }, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    profiles_payload = json.dumps(profile_data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    html = TEMPLATE.read_text(encoding="utf-8").replace("<!-- CASE_DATA -->", case_payload, 1)
    html = html.replace("<!-- PROFILE_DATA -->", profiles_payload, 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/visualizacao.html"))
    parser.add_argument("--seed", type=int, default=2026)
    options = parser.parse_args()
    export_page(options.output, options.seed)


if __name__ == "__main__":
    main()
