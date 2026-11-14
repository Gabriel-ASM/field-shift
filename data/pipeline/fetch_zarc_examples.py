"""Download official MAPA SISZARC exports for project demo municipalities.

The MAPA open-data CSV is very large. SISZARC provides the same official ZARC
records as filtered XLS reports; this downloader keeps municipality-level slices
for the three examples without mirroring unrelated national rows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
import unicodedata

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
BASE = "https://sistemasweb.agricultura.gov.br/siszarc"
ACTION = BASE + "/gerarRelatorioPublicacoesDoZarc"
EXAMPLES = {"RO": "1100023", "SP": "3516200", "MG": "3170701"}


def options(html: str, select_id: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", id=select_id)
    if select is None:
        raise RuntimeError(f"SISZARC response lacks select #{select_id}")
    return [
        (option.get("value", ""), option.get_text(" ", strip=True))
        for option in select.find_all("option")
        if option.get("value", "").strip()
    ]


def choose(items: list[tuple[str, str]], pattern: str, *, required: bool = True) -> str:
    matches = [(value, label) for value, label in items if re.search(pattern, label, re.I)]
    if not matches:
        if required:
            raise RuntimeError(f"No SISZARC option matches {pattern!r}: {items}")
        return ""
    return matches[0][0]


def post(session: requests.Session, method: str, body: dict[str, str]) -> requests.Response:
    response = session.post(f"{ACTION}!{method}.action", data=body, timeout=120)
    response.raise_for_status()
    return response


def export_report(uf: str, crop: str, season: str, output: Path) -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "FieldShift-OpenData/1.0 (research demo; public SISZARC query)"})
    session.get(f"{BASE}/base.action", timeout=60).raise_for_status()
    response = session.post(
        f"{ACTION}.action", data={"idGlobal": "", "idLocal": "15203"}, timeout=60
    )
    response.raise_for_status()

    body = {
        "isRelatorio": "false",
        "form.filtroConsulta.anoSafra": season,
        "form.versaoPortaria": "Atual",
    }
    response = post(session, "carregarComboCulturas", body)
    crop_options = options(response.text, "comboCulturas")
    crop_id = choose(crop_options, crop)
    crop_label = next(label for value, label in crop_options if value == crop_id)
    body["form.filtroConsulta.cultura.codigoCultura"] = crop_id

    response = post(session, "carregarComboOutrosManejos", body)
    systems = options(response.text, "comboTipoSistemaCultivo")
    system_id = choose(systems, r"sequeiro", required=False)
    body["form.filtroConsulta.tipoSistemaCultivo.cdTipoCultivo"] = system_id
    system_label = next((label for value, label in systems if value == system_id), None)

    response = post(session, "carregarComboClima", body)
    climates = options(response.text, "comboTipoDeClima")
    climate_id = choose(climates, r"não se aplica", required=False)
    body["form.filtroConsulta.tipoClimaCultivo.idTipoClima"] = climate_id
    climate_label = next((label for value, label in climates if value == climate_id), None)

    response = post(session, "carregarComboUfs", body)
    body["form.filtroConsulta.sgUF"] = choose(options(response.text, "comboUfs"), rf"^{uf}$")

    response = post(session, "carregarComboPortarias", body)
    ordinances = options(response.text, "comboPortarias")
    ordinance_id = choose(ordinances, r"\d+", required=False)
    body["form.filtroConsulta.numeroPortaria"] = ordinance_id
    ordinance_label = next((label for value, label in ordinances if value == ordinance_id), None)

    response = post(session, "carregarComboGrupos", body)
    # Group and soil are optional. Leaving them blank retrieves every viable
    # cultivar group and soil class for the selected crop and state.
    body["form.filtroConsulta.grupo.cdGrupo"] = ""
    body["form.filtroConsulta.solo.cdSolo"] = ""
    body["isRelatorio"] = "true"
    response = session.post(
        f"{ACTION}!gerarRelatorioXLS.action", data=body, timeout=180
    )
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").lower()
    if "html" in content_type or response.content[:80].lstrip().lower().startswith(b"<!doctype"):
        raise RuntimeError(
            "SISZARC returned an HTML form instead of XLS; check required filters/availability."
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(response.content)
    source = {
        "publisher": "MAPA — SISZARC public report",
        "report_url": f"{ACTION}!gerarRelatorioXLS.action",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "season_filter": season,
        "crop_regex_requested": crop,
        "crop_option_returned": crop_label,
        "uf_filter": uf,
        "cultivation_system_filter": system_label,
        "climate_filter": climate_label,
        "ordinance_filter": ordinance_label or "Atual",
        "cultivar_group_filter": None,
        "soil_filter": None,
        "filter_note": "Cultivar group and soil filters were left blank so all official strata were included; municipality is retained during normalization.",
        "file": output.name,
        "bytes": len(response.content),
    }
    output.with_suffix(output.suffix + ".source.json").write_text(
        json.dumps(source, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{uf} | {crop} | {len(response.content):,} bytes | {output.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uf", choices=EXAMPLES, required=True)
    parser.add_argument("--crop", required=True, help="Regex matching the SISZARC crop label")
    parser.add_argument("--season", default="2026 / 2027")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    season_tag = re.sub(r"[^0-9]+", "-", args.season).strip("-")
    ascii_crop = "".join(
        char for char in unicodedata.normalize("NFKD", args.crop.lower())
        if not unicodedata.combining(char)
    )
    crop_tag = re.sub(r"[^a-z0-9]+", "-", ascii_crop).strip("-")
    output = args.output or ROOT / "data" / "raw" / "mapa-siszarc" / f"zarc-{args.uf.lower()}-{crop_tag}-{season_tag}.xls"
    export_report(args.uf, args.crop, args.season, output)


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, RuntimeError) as error:
        print(f"SISZARC ingestion failed: {error}", file=sys.stderr)
        raise SystemExit(1)
