"""Normalize official PAM and filtered SISZARC rows into demo profiles."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from statistics import mean

import xlrd


ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / "data" / "profiles"
RAW_PAM = ROOT / "data" / "raw" / "ibge" / "pam-municipal-5457-1988-2025.json"
RAW_ZARC = ROOT / "data" / "raw" / "mapa-siszarc"
PROFILE_CITIES = {
    "ariquemes-ro": ("1100023", "ariquemes", "RO"),
    "franca-sp": ("3516200", "franca", "SP"),
    "varginha-mg": ("3170701", "varginha", "MG"),
}
VARIABLE_FIELDS = {
    "112": "yield_kg_ha",
    "214": "production_tonnes",
    "215": "production_value_thousand_brl_nominal",
    "216": "harvested_area_ha",
}
PAM_CROP_LABELS = {
    "40101": "amendoim_em_casca", "40103": "aveia_em_grao", "40106": "cana_de_acucar",
    "40112": "feijao_em_grao", "40122": "milho_em_grao", "40124": "soja_em_grao",
    "40125": "sorgo_em_grao", "40127": "trigo_em_grao", "40140": "cafe_arabica",
    "40141": "cafe_canephora",
}


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).casefold().strip()


def number(value: object) -> float | None:
    if value is None or str(value).strip() in {"", "-", "...", "..", "x", "X"}:
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def load_pam() -> tuple[dict[str, dict[str, dict[str, object]]], dict[str, object]]:
    payload = json.loads(RAW_PAM.read_text(encoding="utf-8"))
    by_municipality: dict[str, dict[tuple[str, int], dict[str, object]]] = {
        code: {} for code, _, _ in PROFILE_CITIES.values()
    }
    for row in payload["records"]:
        code = str(row.get("D1C", ""))
        if code not in by_municipality:
            continue
        product = str(row.get("D4C", ""))
        if product not in PAM_CROP_LABELS:
            continue
        variable = str(row.get("D2C", ""))
        if variable not in VARIABLE_FIELDS:
            continue
        year = int(row["D3C"])
        record = by_municipality[code].setdefault((product, year), {
            "product_id": product,
            "crop": PAM_CROP_LABELS[product],
            "year": year,
        })
        record[VARIABLE_FIELDS[variable]] = number(row.get("V"))
        record.setdefault("official_product_label", row.get("D4N"))

    result: dict[str, dict[str, dict[str, object]]] = {}
    for profile_id, (municipality_code, _, _) in PROFILE_CITIES.items():
        records = list(by_municipality[municipality_code].values())
        for record in records:
            value = record.get("production_value_thousand_brl_nominal")
            production = record.get("production_tonnes")
            area = record.get("harvested_area_ha")
            record["unit_value_brl_per_tonne_nominal"] = (
                value * 1000 / production if value is not None and production else None
            )
            record["gross_value_brl_per_ha_nominal"] = (
                value * 1000 / area if value is not None and area else None
            )
        records.sort(key=lambda row: (str(row["crop"]), int(row["year"])))
        crops = sorted({str(row["crop"]) for row in records})
        summaries = {}
        for crop in crops:
            yields = [
                float(row["yield_kg_ha"]) for row in records
                if row["crop"] == crop and row.get("yield_kg_ha") is not None
            ]
            observed = [row for row in records if row["crop"] == crop and row.get("yield_kg_ha") is not None]
            recent = [float(row["yield_kg_ha"]) for row in observed if int(row["year"]) >= 2021]
            summaries[crop] = {
                "valid_yield_years": len(yields),
                "yield_min_kg_ha": min(yields) if yields else None,
                "yield_median_kg_ha": sorted(yields)[len(yields) // 2] if yields else None,
                "yield_max_kg_ha": max(yields) if yields else None,
                "yield_mean_2021_2025_kg_ha": mean(recent) if recent else None,
                "first_valid_year": min((int(row["year"]) for row in observed), default=None),
                "last_valid_year": max((int(row["year"]) for row in observed), default=None),
                "evidence": "observed municipal PAM statistics; not parcel yield or a causal crop-response function",
            }
        result[profile_id] = {
            "source": payload["source"],
            "municipality_ibge_code": municipality_code,
            "records": records,
            "crop_summaries": summaries,
            "limitations": [
                "A PAM municipal mean is not the yield of an individual farm or field.",
                "Historical yield dispersion includes changes in technology, planted area, and reporting; it is not an IID yield distribution.",
                "Production value is nominal and is not inflation-adjusted; do not use it as a real-price series.",
                "A missing or dash value in SIDRA is retained as null, not interpreted as zero.",
            ],
        }
    return result, payload["source"]


def read_zarc() -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {key: [] for key in PROFILE_CITIES}
    files = sorted(path for path in RAW_ZARC.rglob("*.xls") if path.is_file())
    for path in files:
        try:
            sheet = xlrd.open_workbook(path, on_demand=True).sheet_by_index(0)
        except Exception as exc:
            raise RuntimeError(f"Cannot parse SISZARC XLS {path}: {exc}") from exc
        header_row = next(
            (index for index in range(min(sheet.nrows, 30))
             if any(norm(cell).startswith("safra") for cell in sheet.row_values(index))),
            None,
        )
        if header_row is None:
            continue
        header = sheet.row_values(header_row)
        decendio_cols = [index for index, label in enumerate(header) if re.fullmatch(r"(?:dec|dev)\s*\d+", norm(label))]
        if len(decendio_cols) != 36:
            continue
        for row_index in range(header_row + 1, sheet.nrows):
            row = sheet.row_values(row_index)
            if len(row) < max(decendio_cols) + 1:
                continue
            uf = str(row[4]).strip().upper()
            city = norm(row[7])
            profile_id = next((key for key, (_, city_name, city_uf) in PROFILE_CITIES.items()
                               if city == city_name and uf == city_uf), None)
            if profile_id is None:
                continue
            risk_codes = [int(number(row[index]) or 0) for index in decendio_cols]
            source_file = path.relative_to(ROOT).as_posix()
            result[profile_id].append({
                "season": str(row[0]).strip(),
                "crop": str(row[3]).strip(),
                "uf": uf,
                "portaria": str(row[5]).strip(),
                "portaria_date": str(row[6]).strip(),
                "municipality": str(row[7]).strip(),
                "cultivar_group": str(row[9]).strip(),
                "zarc_soil_class": str(row[10]).strip(),
                "decendio_values": risk_codes,
                "planting_decendios_by_risk_percent": {
                    str(risk): [i + 1 for i, value in enumerate(risk_codes) if value == risk]
                    for risk in (20, 30, 40)
                },
                "source_file": source_file,
                "source": "MAPA SISZARC public report; report query is filtered by crop/state, this row by municipality name and UF",
            })
    for profile_rows in result.values():
        profile_rows.sort(key=lambda row: (str(row["season"]), str(row["crop"]), str(row["cultivar_group"]), str(row["zarc_soil_class"])))
    return result


def main() -> None:
    pam, pam_source = load_pam()
    zarc = read_zarc()
    summaries = {"source": pam_source, "profiles": {}}
    for profile_id, (ibge_code, city_name, uf) in PROFILE_CITIES.items():
        profile_dir = PROFILES / profile_id
        pam_file = profile_dir / "pam-history.json"
        zarc_file = profile_dir / "zarc-planting-windows.json"
        pam_file.write_text(json.dumps(pam[profile_id], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        zarc_payload = {
            "municipality": {"name": city_name.title(), "uf": uf, "ibge_code": ibge_code},
            "source": {
                "publisher": "MAPA",
                "system": "SISZARC — Publicações do Zarc",
                "url": "https://sistemasweb.agricultura.gov.br/siszarc/base.action",
                "open_dataset": "https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico",
                "current_season": "2026 / 2027",
                "download_scope": "filtered SISZARC XLS exports per crop and UF; raw exports include the selected UF and were reduced here to the example municipality",
                "license": "Creative Commons Attribution (MAPA open-data catalog)",
                "dictionary_url": "https://dados.agricultura.gov.br/dataset/6d3d141c-885e-41a4-ab7f-dc8ff323b96f/resource/bebb0ebb-bc75-460c-b900-a7a1ebd87bee/download/dicionario-de-dados-tabua-de-risco-2026.pdf",
            },
            "row_count": len(zarc[profile_id]),
            "risk_semantics": "Each decendio entry preserves the MAPA report value 0/20/30/40. Non-zero values are published risk levels; zero means no planting indication for that row/decendio. Group and AD soil class must match the producer's cultivar and soil classification.",
            "soil_matching": "The AD1–AD6 ZARC categories are not inferred from the mapped SoilGrids AWC. The interface must ask for the applicable ZARC class or show all strata without claiming a match.",
            "rows": zarc[profile_id],
        }
        zarc_file.write_text(json.dumps(zarc_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summaries["profiles"][profile_id] = {
            "ibge_code": ibge_code,
            "pam_records": len(pam[profile_id]["records"]),
            "pam_crops": pam[profile_id]["crop_summaries"],
            "zarc_rows": len(zarc[profile_id]),
            "zarc_crops": sorted({str(row["crop"]) for row in zarc[profile_id]}),
            "zarc_files": sorted({str(row["source_file"]) for row in zarc[profile_id]}),
        }
        print(f"{profile_id}: {len(pam[profile_id]['records'])} PAM crop-years; {len(zarc[profile_id])} ZARC rows")
    (ROOT / "data" / "reference" / "crop-data-coverage.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
