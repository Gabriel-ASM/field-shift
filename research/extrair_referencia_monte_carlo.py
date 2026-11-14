"""Extrai o dicionário e as regras de distribuição da planilha de pesquisa."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research" / "Field_Shift_Monte_Carlo_Variaveis_e_Fluxograma.xlsx"
OUTPUT = ROOT / "data" / "reference" / "desenho-markov-monte-carlo.json"


def clean(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def rows(sheet):
    return [tuple(clean(value) for value in row) for row in sheet.iter_rows(values_only=True)]


def records_from_header(sheet, header_label):
    values = rows(sheet)
    header_index = next(
        index for index, row in enumerate(values)
        if row and row[0] == header_label
    )
    headers = [str(value).strip() if value is not None else "" for value in values[header_index]]
    records = []
    for row in values[header_index + 1:]:
        if not row or row[0] in (None, ""):
            continue
        if header_label == "ID" and (
            not isinstance(row[0], str) or not re.fullmatch(r"[A-Z]\d{2}", row[0])
        ):
            continue
        record = {
            headers[index]: value
            for index, value in enumerate(row[:len(headers)])
            if headers[index]
        }
        records.append(record)
    return records


def main():
    workbook = load_workbook(SOURCE, data_only=True, read_only=True)
    config_rows = rows(workbook["Configuracao"])
    draft_config = {
        str(row[1]).strip(): row[2]
        for row in config_rows
        if len(row) > 2 and row[1] not in (None, "") and row[2] not in (None, "")
        and not str(row[1]).startswith(("PARÂMETROS", "CÁLCULOS", "REGRAS"))
    }
    payload = {
        "source": {
            "file": "research/Field_Shift_Monte_Carlo_Variaveis_e_Fluxograma.xlsx",
            "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "sheets_extracted": ["Variaveis", "Matriz Impactos", "Distribuicoes", "Configuracao"],
            "nature": "desenho arquitetural; distribuições sugeridas e parâmetros agrícolas aguardam calibração",
        },
        "variables": records_from_header(workbook["Variaveis"], "ID"),
        "impact_matrix": {
            "interpretation": "2 = efeito direto; 1 = indireto; 0 = sem ligação principal. Não representa intensidade estatística nem causalidade comprovada.",
            "records": records_from_header(workbook["Matriz Impactos"], "ID"),
        },
        "distribution_families": records_from_header(workbook["Distribuicoes"], "Família"),
        "workbook_draft_configuration": draft_config,
        "configuration_note": "Preservada como referência da planilha. A taxa de 10% a.a. e outros parâmetros ilustrativos da planilha não substituem os valores vigentes em docs/plano-mvp.md; para esta execução o MVP usa as definições do plano.",
        "active_ingestion_contracts": {
            "daily_climate": "data/contracts/climate-daily.schema.json",
            "soil_profile": "data/contracts/soil-profile.schema.json",
            "field_observation": "data/contracts/field-observation.schema.json",
            "markov_transition_counts": "data/contracts/markov-transition.schema.json",
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"variables={len(payload['variables'])}; impacts={len(payload['impact_matrix']['records'])}; distribution_families={len(payload['distribution_families'])}; output={OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
