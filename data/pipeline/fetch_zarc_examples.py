"""Download official MAPA SISZARC exports for project demo municipalities.

The MAPA open-data CSV is very large. SISZARC provides the same official ZARC
records as filtered XLS reports; this downloader keeps municipality-level slices
for the three examples without mirroring unrelated national rows.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

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
    crop_id = choose(options(response.text, "comboCulturas"), crop)
    body["form.filtroConsulta.cultura.codigoCultura"] = crop_id

    response = post(session, "carregarComboOutrosManejos", body)
    body["form.filtroConsulta.tipoSistemaCultivo.cdTipoCultivo"] = choose(
        options(response.text, "comboTipoSistemaCultivo"), r"sequeiro", required=False
    )

    response = post(session, "carregarComboClima", body)
    body["form.filtroConsulta.tipoClimaCultivo.idTipoClima"] = choose(
        options(response.text, "comboTipoDeClima"), r"não se aplica", required=False
    )

    response = post(session, "carregarComboUfs", body)
    body["form.filtroConsulta.sgUF"] = choose(options(response.text, "comboUfs"), rf"^{uf}$")

    response = post(session, "carregarComboPortarias", body)
    body["form.filtroConsulta.numeroPortaria"] = choose(
        options(response.text, "comboPortarias"), r"\d+", required=False
    )

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
    print(f"{uf} | {crop} | {len(response.content):,} bytes | {output.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uf", choices=EXAMPLES, required=True)
    parser.add_argument("--crop", required=True, help="Regex matching the SISZARC crop label")
    parser.add_argument("--season", default="2026 / 2027")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    season_tag = re.sub(r"[^0-9]+", "-", args.season).strip("-")
    crop_tag = re.sub(r"[^a-z0-9]+", "-", args.crop.lower()).strip("-")
    output = args.output or ROOT / "data" / "raw" / "mapa-siszarc" / f"zarc-{args.uf.lower()}-{crop_tag}-{season_tag}.xls"
    export_report(args.uf, args.crop, args.season, output)


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, RuntimeError) as error:
        print(f"SISZARC ingestion failed: {error}", file=sys.stderr)
        raise SystemExit(1)
