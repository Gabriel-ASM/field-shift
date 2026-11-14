"""Extract official CONAB costs and join them with municipal PAM/Yahoo inputs."""

from __future__ import annotations

import json
import re
import unicodedata
from hashlib import sha256
from pathlib import Path
from statistics import median

import xlrd


ROOT = Path(__file__).resolve().parents[2]
COST_DIR = ROOT / "data" / "raw" / "conab" / "costs"
PAM_DIR = ROOT / "data" / "profiles"
IPCA_PATH = ROOT / "data" / "raw" / "ibge" / "ipca-table-1737-2017-202610.json"
STATE_PAM_PATH = ROOT / "data" / "raw" / "ibge" / "pam-state-5457-1988-2025.json"
YAHOO_PATH = ROOT / "data" / "reference" / "yahoo-harvest-futures.json"
OUTPUT = ROOT / "data" / "reference" / "economic-benchmarks.json"
COVERAGE_OUTPUT = ROOT / "data" / "reference" / "economic-input-coverage.json"

PROFILE_INFO = {
    "ariquemes-ro": {"name": "Ariquemes", "uf": "RO", "coffee_pam": "cafe_canephora"},
    "franca-sp": {"name": "Franca", "uf": "SP", "coffee_pam": "cafe_arabica"},
    "varginha-mg": {"name": "Varginha", "uf": "MG", "coffee_pam": "cafe_arabica"},
}
PAM_CROPS = {
    "soybean": "soja_em_grao",
    "maize_grain": "milho_em_grao",
    "sugarcane": "cana_de_acucar",
    "sorghum_grain": "sorgo_em_grao",
    "wheat": "trigo_em_grao",
    "dry_bean": "feijao_em_grao",
    "peanut": "amendoim_em_casca",
    "oat": "aveia_em_grao",
}
MARKOV_CROPS = [
    "soybean", "maize_grain", "sugarcane", "coffee", "sorghum_grain", "wheat", "dry_bean",
    "peanut", "oat", "forage_radish", "brachiaria", "millet", "crotalaria", "mucuna",
]
PAM_PRODUCT_IDS = {
    "amendoim_em_casca": "40101", "aveia_em_grao": "40103", "cana_de_acucar": "40106",
    "feijao_em_grao": "40112", "milho_em_grao": "40122", "soja_em_grao": "40124",
    "sorgo_em_grao": "40125", "trigo_em_grao": "40127", "cafe_arabica": "40140",
    "cafe_canephora": "40141",
}
SOURCE_URLS = {
    "serie-historica-custos-soja-1997-a-2026.xls": "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/arquivos-custo-de-producao/agricolas/serie-historica-custos-soja-1997-a-2026.xls/view",
    "milho_1a_safra_serie_historica_1997-2026.xls": "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/arquivos-custo-de-producao/agricolas/milho/milho_1a_safra_serie_historica_1997-2026.xls/view",
    "milho_2a_safra_serie_historica_2005-2026.xls": "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/arquivos-custo-de-producao/agricolas/milho/milho_2a_safra_serie_historica_2005-2026.xls/view",
    "serie-historica-custos-cana-de-acucar-2008-a-2025.xls": "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/arquivos-custo-de-producao/agricolas/serie-historica-custos-cana-de-acucar-2008-a-2025.xls/view",
    "seriehistoricacustoscafearabica2003a2025.xls": "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/arquivos-custo-de-producao/agricolas/seriehistoricacustoscafearabica2003a2025.xls/view",
    "seriehistoricacustoscafeconilon2007a2025.xls": "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/arquivos-custo-de-producao/agricolas/seriehistoricacustoscafeconilon2007a2025.xls/view",
    "seriehistoricacustossorgo2013a2026.xls": "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/arquivos-custo-de-producao/agricolas/seriehistoricacustossorgo2013a2026.xls/view",
    "seriehistoricacustostrigo1998a2025.xls": "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/arquivos-custo-de-producao/agricolas/seriehistoricacustostrigo1998a2025.xls/view",
    "serie-historica-custos-amendoim-2005-a-2024.xls": "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/arquivos-custo-de-producao/agricolas/serie-historica-custos-amendoim-2005-a-2024.xls/view",
    "serie-historica-custos-aveia-2012-a-2023.xls": "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/arquivos-custo-de-producao/agricolas/serie-historica-custos-aveia-2012-a-2023.xls/view",
}
PANEL_SELECTION = {
    "ariquemes-ro": {
        "maize_grain": ("milho_2a_safra_serie_historica_2005-2026.xls", "Vilhena-RO-2019"),
        "coffee": ("seriehistoricacustoscafeconilon2007a2025.xls", "Cacoal-RO-2018"),
    },
    "franca-sp": {
        "soybean": ("serie-historica-custos-soja-1997-a-2026.xls", "Assis-SP-2021"),
        "maize_grain": ("milho_2a_safra_serie_historica_2005-2026.xls", "Assis-SP-2023"),
        "sugarcane": ("serie-historica-custos-cana-de-acucar-2008-a-2025.xls", "Penápolis-SP-2025"),
        "coffee": ("seriehistoricacustoscafearabica2003a2025.xls", "Franca-SP-2018"),
    },
    "varginha-mg": {
        "soybean": ("serie-historica-custos-soja-1997-a-2026.xls", "Unaí-MG-2026"),
        "maize_grain": ("milho_2a_safra_serie_historica_2005-2026.xls", "Unaí-MG-2026"),
        "sugarcane": ("serie-historica-custos-cana-de-acucar-2008-a-2025.xls", "V. do Rio Branco-MG-2024"),
        "coffee": ("seriehistoricacustoscafearabica2003a2025.xls", "Três Pontas-MG-2025"),
    },
}
COST_FILES_BY_CROP = {
    "soybean": ("serie-historica-custos-soja-1997-a-2026.xls",),
    "maize_grain": ("milho_1a_safra_serie_historica_1997-2026.xls", "milho_2a_safra_serie_historica_2005-2026.xls"),
    "sugarcane": ("serie-historica-custos-cana-de-acucar-2008-a-2025.xls",),
    "coffee_arabica": ("seriehistoricacustoscafearabica2003a2025.xls",),
    "coffee_conilon": ("seriehistoricacustoscafeconilon2007a2025.xls",),
    "sorghum_grain": ("seriehistoricacustossorgo2013a2026.xls",),
    "wheat": ("seriehistoricacustostrigo1998a2025.xls",),
    "peanut": ("serie-historica-custos-amendoim-2005-a-2024.xls",),
    "oat": ("serie-historica-custos-aveia-2012-a-2023.xls",),
}
COST_PROXY_CROP = {
    "dry_bean": "soybean",
    "forage_radish": "oat",
    "brachiaria": "sorghum_grain",
    "millet": "sorghum_grain",
    "crotalaria": "soybean",
    "mucuna": "soybean",
}
HARVESTLESS_CROPS = {"forage_radish", "brachiaria", "crotalaria", "mucuna"}
INCOME_PROXY_CROP = {"millet": "sorghum_grain"}
CROP_LABELS = {
    "soybean": "Soja",
    "maize_grain": "Milho",
    "sugarcane": "Cana-de-açúcar",
    "coffee": "Café",
    "sorghum_grain": "Sorgo",
    "wheat": "Trigo",
    "dry_bean": "Feijão",
    "peanut": "Amendoim",
    "oat": "Aveia em grão (proxy; não equivale a aveia-preta de cobertura)",
    "forage_radish": "Nabo forrageiro",
    "brachiaria": "Braquiária",
    "millet": "Milheto",
    "crotalaria": "Crotalária",
    "mucuna": "Mucuna",
}
MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).casefold().strip()


def number(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value or "").strip()
    if not raw:
        return None
    match = re.search(r"[-+]?\d[\d.]*,\d+|[-+]?\d+(?:\.\d+)?", raw)
    if not match:
        return None
    token = match.group(0)
    if "," in token:
        token = token.replace(".", "").replace(",", ".")
    try:
        return float(token)
    except ValueError:
        return None


def text_rows(sheet: xlrd.sheet.Sheet) -> list[list[str]]:
    return [[str(sheet.cell_value(row, col)).strip() for col in range(sheet.ncols)] for row in range(sheet.nrows)]


def metric_value(sheet: xlrd.sheet.Sheet, label: str) -> float | None:
    needle = norm(label)
    for row in range(sheet.nrows):
        cells = [sheet.cell_value(row, col) for col in range(sheet.ncols)]
        joined = norm(" ".join(str(value) for value in cells))
        if needle not in joined:
            continue
        for value in cells:
            if isinstance(value, (int, float)) and float(value) > 0:
                return float(value)
    return None


def parse_location_year(sheet_name: str) -> tuple[str, str, int] | None:
    match = re.search(r"^(?P<city>.+)-(?P<uf>[A-Z]{2})-(?P<year>(?:19|20)\d{2})(?:-|$)", sheet_name)
    if not match:
        return None
    return match.group("city"), match.group("uf"), int(match.group("year"))


def month_date(sheet: xlrd.sheet.Sheet, year_fallback: int) -> tuple[int, int, str]:
    for row in range(min(sheet.nrows, 8)):
        joined = norm(" ".join(str(sheet.cell_value(row, col)) for col in range(sheet.ncols)))
        if "mes/ano" not in joined:
            continue
        month = next((num for name, num in MONTHS.items() if name in joined), None)
        year_match = re.search(r"(?:19|20)\d{2}", joined)
        year = int(year_match.group(0)) if year_match else year_fallback
        if month:
            return year, month, "month/year field in CONAB sheet"
    return year_fallback, 12, "December fallback from worksheet year"


def productivity_kg_ha(sheet: xlrd.sheet.Sheet) -> float | None:
    for row in range(min(sheet.nrows, 10)):
        joined = " ".join(str(sheet.cell_value(row, col)) for col in range(sheet.ncols))
        if "produtividade" in norm(joined):
            return number(joined)
    return None


def title_text(sheet: xlrd.sheet.Sheet) -> str:
    parts = []
    for row in range(min(sheet.nrows, 6)):
        parts.extend(str(sheet.cell_value(row, col)).strip() for col in range(sheet.ncols))
    return " ".join(part for part in parts if part)


def extract_cost_panels() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    sources = []
    panels = []
    for path in sorted(COST_DIR.glob("*.xls")):
        digest = sha256(path.read_bytes()).hexdigest()
        sources.append({
            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": digest,
            "source_url": SOURCE_URLS.get(path.name),
            "publisher": "CONAB",
        })
        book = xlrd.open_workbook(str(path), on_demand=True)
        for sheet in book.sheets():
            location = parse_location_year(sheet.name)
            if location is None:
                continue
            city, uf, year = location
            cost_year, cost_month, date_basis = month_date(sheet, year)
            row = {
                "crop_id": path.name,
                "sheet": sheet.name,
                "municipality": city,
                "uf": uf,
                "worksheet_year": year,
                "cost_date": f"{cost_year:04d}-{cost_month:02d}",
                "cost_date_basis": date_basis,
                "productivity_kg_ha_panel": productivity_kg_ha(sheet),
                "variable_cost_brl_ha": metric_value(sheet, "CUSTO VARIAVEL"),
                "operational_cost_brl_ha": metric_value(sheet, "CUSTO OPERACIONAL"),
                "total_cost_brl_ha": metric_value(sheet, "CUSTO TOTAL"),
                "sheet_title": title_text(sheet),
                "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
            }
            if row["total_cost_brl_ha"] is None and row["operational_cost_brl_ha"] is None:
                continue
            panels.append(row)
        book.release_resources()
    return sources, panels


def ipca_indices() -> tuple[dict[str, float], dict[str, float], dict[str, object]]:
    raw = json.loads(IPCA_PATH.read_text(encoding="utf-8-sig"))
    indices: dict[str, float] = {}
    for row in raw[1:]:
        period = str(row.get("D3C", ""))
        value = number(row.get("V"))
        if re.fullmatch(r"\d{6}", period) and value:
            indices[period] = value
    base_month = max(indices)
    yearly_averages: dict[str, float] = {}
    for year in sorted({period[:4] for period in indices}):
        yearly = [value for period, value in indices.items() if period.startswith(year)]
        yearly_averages[year] = sum(yearly) / len(yearly)
    return indices, yearly_averages, {
        "raw_file": str(IPCA_PATH.relative_to(ROOT)).replace("\\", "/"),
        "source_url": "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2266/p/201701-202610",
        "table": 1737,
        "variable": "2266 — número-índice IPCA",
        "base_month": base_month,
        "base_index": indices[base_month],
        "last_twelve_month_change_percent": round((indices[base_month] / indices.get("202510", indices[base_month]) - 1) * 100, 4),
        "data_semantics": "IPCA geral usado apenas para converter valores nominais de anos diferentes à mesma referência; não é índice de custo agrícola.",
    }


def deflator(indices: dict[str, float], annual: dict[str, float], year: int, month: int | None) -> float | None:
    base = max(indices)
    source_index = indices.get(f"{year:04d}{month:02d}") if month else annual.get(f"{year:04d}")
    if source_index is None or source_index <= 0:
        source_index = annual.get(f"{year:04d}")
    if source_index is None or source_index <= 0:
        return None
    return indices[base] / source_index


def panel_index(panels: list[dict[str, object]]) -> dict[tuple[str, str], dict[str, object]]:
    return {(str(row["source_file"]).split("/")[-1], str(row["sheet"])): row for row in panels}


def state_pam_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int, str], dict[str, float]] = {}
    for row in payload.get("records", []):
        uf_code, year, product = str(row.get("D1C", "")), number(row.get("D3C")), str(row.get("D4C", ""))
        variable, value = str(row.get("D2C", "")), number(row.get("V"))
        if year is None or value is None:
            continue
        grouped.setdefault((uf_code, int(year), product), {})[variable] = value
    result = []
    for (uf_code, year, product), values in grouped.items():
        production = values.get("214")
        production_value = values.get("215")
        area = values.get("216")
        result.append({
            "uf_code": uf_code,
            "year": year,
            "product_id": product,
            "yield_kg_ha": values.get("112"),
            "production_tonnes": production,
            "production_value_thousand_brl_nominal": production_value,
            "harvested_area_ha": area,
            "unit_value_brl_per_tonne_nominal": (production_value * 1000 / production) if production and production > 0 and production_value is not None else None,
        })
    return result


def macroregion(uf: str) -> str:
    return {"RO": "North", "AC": "North", "AM": "North", "RR": "North", "PA": "North", "AP": "North", "TO": "North",
            "MA": "Northeast", "PI": "Northeast", "CE": "Northeast", "RN": "Northeast", "PB": "Northeast", "PE": "Northeast", "AL": "Northeast", "SE": "Northeast", "BA": "Northeast",
            "MT": "Center-West", "MS": "Center-West", "GO": "Center-West", "DF": "Center-West",
            "MG": "Southeast", "ES": "Southeast", "RJ": "Southeast", "SP": "Southeast",
            "PR": "South", "SC": "South", "RS": "South"}.get(uf, "Brazil")


UF_CODES = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}

PAM_SCOPE_LABELS = {"municipality": "municipal", "state": "estadual", "macroregion": "macrorregional", "Brazil": "nacional"}


def aggregate_state_harvests(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_year: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        by_year.setdefault(int(row["year"]), []).append(row)
    aggregate = []
    for year, group in by_year.items():
        production_values = [float(row["production_tonnes"]) for row in group if row.get("production_tonnes") is not None and float(row["production_tonnes"]) > 0]
        value_values = [float(row["production_value_thousand_brl_nominal"]) for row in group if row.get("production_value_thousand_brl_nominal") is not None]
        area_values = [float(row["harvested_area_ha"]) for row in group if row.get("harvested_area_ha") is not None and float(row["harvested_area_ha"]) > 0]
        production = sum(production_values) if production_values else None
        production_value = sum(value_values) if value_values else None
        area = sum(area_values) if area_values else None
        yield_value = production * 1000 / area if production and area else None
        if yield_value is None:
            yields = [float(row["yield_kg_ha"]) for row in group if row.get("yield_kg_ha") is not None and float(row["yield_kg_ha"]) > 0]
            yield_value = median(yields) if yields else None
        aggregate.append({
            "year": year,
            "yield_kg_ha": yield_value,
            "unit_value_brl_per_tonne_nominal": (production_value * 1000 / production) if production and production > 0 and production_value is not None else None,
        })
    return aggregate


def pam_crop_values(
    profile_id: str, crop_id: str, municipal_pam: dict[str, object], state_rows: list[dict[str, object]],
    indices: dict[str, float], annual_indices: dict[str, float],
) -> tuple[float | None, dict[str, object] | None, str, list[str]]:
    info = PROFILE_INFO[profile_id]
    proxy_id = INCOME_PROXY_CROP.get(crop_id, crop_id)
    if crop_id in HARVESTLESS_CROPS:
        source = "Hipótese editável: cultura de cobertura sem colheita comercial valorada na PAM; receita inicial zero."
        return 0.0, {"brl_per_tonne": 0.0, "source": source, "scope": "editable zero-harvest base case"}, source, (["receita zero por falta de colheita comercial"] if crop_id else [])
    pam_product = info["coffee_pam"] if proxy_id == "coffee" else PAM_CROPS.get(proxy_id)
    product_id = PAM_PRODUCT_IDS.get(pam_product or "")
    if not product_id:
        return 0.0, {"brl_per_tonne": 0.0, "source": "Hipótese editável: sem produto PAM diretamente identificável; receita inicial zero.", "scope": "editable zero-harvest base case"}, "Sem produto PAM direto; receita inicial zero, editável.", ["produto colhido sem PAM"]

    municipal_rows = [
        row for row in municipal_pam.get("records", [])
        if row.get("crop") == pam_product and 2021 <= int(row.get("year", 0)) <= 2025
        and number(row.get("yield_kg_ha")) and number(row.get("unit_value_brl_per_tonne_nominal"))
    ]
    scope = "municipality"
    source_notes = []
    annual = []
    if municipal_rows:
        annual = [{"year": int(row["year"]), "yield_kg_ha": float(row["yield_kg_ha"]), "unit_value_brl_per_tonne_nominal": float(row["unit_value_brl_per_tonne_nominal"])} for row in municipal_rows]
    else:
        uf_code = next((code for code, uf in UF_CODES.items() if uf == info["uf"]), None)
        local_state = [row for row in state_rows if row["uf_code"] == uf_code and row["product_id"] == product_id and 2021 <= int(row["year"]) <= 2025]
        if local_state:
            annual = aggregate_state_harvests(local_state)
            scope = "state"
            source_notes.append("Rendimento/preço PAM estadual usado como proxy quando falta série municipal.")
        else:
            region_states = {code for code, uf in UF_CODES.items() if macroregion(uf) == macroregion(info["uf"])}
            regional = [row for row in state_rows if row["uf_code"] in region_states and row["product_id"] == product_id and 2021 <= int(row["year"]) <= 2025]
            if regional:
                annual = aggregate_state_harvests(regional)
                scope = "macroregion"
                source_notes.append("Mediana/valor unitário PAM da macrorregião usado como proxy; dado municipal/estadual ausente.")
            else:
                national = [row for row in state_rows if row["product_id"] == product_id and 2021 <= int(row["year"]) <= 2025]
                annual = aggregate_state_harvests(national)
                scope = "Brazil"
                source_notes.append("Mediana/valor unitário PAM nacional usado como proxy; recorte regional sem colheita identificável.")
    valid_yields = [float(row["yield_kg_ha"]) for row in annual if row.get("yield_kg_ha") is not None and float(row["yield_kg_ha"]) > 0]
    valid_prices = [row for row in annual if row.get("unit_value_brl_per_tonne_nominal") is not None and float(row["unit_value_brl_per_tonne_nominal"]) > 0]
    if not valid_prices and scope != "Brazil":
        national = [row for row in state_rows if row["product_id"] == product_id and 2021 <= int(row["year"]) <= 2025]
        valid_prices = [row for row in aggregate_state_harvests(national) if row.get("unit_value_brl_per_tonne_nominal") is not None and float(row["unit_value_brl_per_tonne_nominal"]) > 0]
        if valid_prices:
            scope = "Brazil"
            source_notes.append("Preço unitário PAM nacional substitui preço local sem comercialização informada.")
    yield_value = median(valid_yields) if valid_yields else None
    if valid_prices:
        latest = max(valid_prices, key=lambda row: int(row["year"]))
        latest_year = int(latest["year"])
        nominal_price = float(latest["unit_value_brl_per_tonne_nominal"])
        price_deflator = deflator(indices, annual_indices, latest_year, None)
        price = {
            "brl_per_tonne": nominal_price * price_deflator if price_deflator else nominal_price,
            "source": "IBGE PAM; valor da produção / toneladas produzidas, no recorte " + PAM_SCOPE_LABELS.get(scope, scope) + "; IPCA para moeda-base.",
            "scope": scope,
            "observed_year": latest_year,
            "observed_nominal_brl_per_tonne": nominal_price,
            "deflator_factor": price_deflator,
            "editable_hypothesis": scope != "municipality",
        }
    else:
        price = None
    if proxy_id != crop_id:
        source_notes.append("Proxy de colheita: dados de sorgo em grão aplicados ao milheto; rendimento e preço são editáveis.")
        if price:
            price["source"] = "Proxy sorgo em grão → milheto; " + price["source"]
            price["proxy_crop_id"] = proxy_id
            price["editable_hypothesis"] = True
    if crop_id == "oat":
        source_notes.append("A PAM mede aveia em grão; esta é uma aproximação da aveia-preta de cobertura e pode ser editada.")
        if price:
            price["source"] = "Aveia em grão usada como proxy para aveia-preta; " + price["source"]
            price["editable_hypothesis"] = True
    yield_source = "IBGE PAM; mediana 2021–2025 em " + scope + ("; não é previsão do talhão." if scope == "municipality" else "; proxy regional editável, não é rendimento municipal/talhão.")
    if proxy_id != crop_id or crop_id == "oat":
        yield_source = "".join(source_notes) + " " + yield_source
    return yield_value, price, yield_source, source_notes


def cost_file_keys(crop_id: str, profile_info: dict[str, str]) -> tuple[str, ...]:
    source_crop = COST_PROXY_CROP.get(crop_id, crop_id)
    if source_crop == "coffee":
        coffee_file = "coffee_conilon" if profile_info["coffee_pam"] == "cafe_canephora" else "coffee_arabica"
        return COST_FILES_BY_CROP[coffee_file]
    return COST_FILES_BY_CROP.get(source_crop, ())


def choose_cost_panel(
    profile_id: str, crop_id: str, profiles: dict[str, object], panels: list[dict[str, object]],
    lookup: dict[tuple[str, str], dict[str, object]], source_urls: dict[str, str | None],
    indices: dict[str, float], annual_indices: dict[str, float],
) -> dict[str, object] | None:
    info = PROFILE_INFO[profile_id]
    selected = PANEL_SELECTION.get(profile_id, {}).get(crop_id)
    raw_panel = lookup.get(selected) if selected else None
    match_level = "mesmo município" if raw_panel and norm(raw_panel["municipality"]) == norm(info["name"]) else "mesma UF · outro município" if raw_panel else ""
    source_crop = COST_PROXY_CROP.get(crop_id, crop_id)
    files = set(cost_file_keys(crop_id, info))
    if raw_panel is None:
        candidates = [row for row in panels if row["source_file"].split("/")[-1] in files and row.get("total_cost_brl_ha") is not None]
        same_uf = [row for row in candidates if row["uf"] == info["uf"]]
        same_macroregion = [row for row in candidates if macroregion(str(row["uf"])) == macroregion(info["uf"])]
        pool = same_uf or same_macroregion or candidates
        if not pool:
            return None
        raw_panel = sorted(pool, key=lambda row: (int(row["worksheet_year"]), int(str(row["cost_date"])[5:7])), reverse=True)[0]
        match_level = "mesma UF · outro município" if same_uf else "mesma macrorregião" if same_macroregion else "painel nacional"
    date_match = re.fullmatch(r"(\d{4})-(\d{2})", str(raw_panel["cost_date"]))
    factor = deflator(indices, annual_indices, int(date_match.group(1)), int(date_match.group(2))) if date_match else None
    nominal_cost = raw_panel.get("total_cost_brl_ha")
    if nominal_cost is None or factor is None:
        return None
    proxy = source_crop != crop_id
    source_note = "Custo total CONAB do produto no painel; localidade, ano e sistema estão identificados." if not proxy else "Hipótese editável de custo: painel CONAB de " + CROP_LABELS[source_crop] + " usado como proxy para " + CROP_LABELS[crop_id] + "."
    return {
        "source_file": raw_panel["source_file"],
        "source_url": source_urls.get(str(raw_panel["source_file"])),
        "sheet": raw_panel["sheet"],
        "municipality": raw_panel["municipality"],
        "uf": raw_panel["uf"],
        "match_level": match_level,
        "cost_date": raw_panel["cost_date"],
        "panel_productivity_kg_ha": raw_panel["productivity_kg_ha_panel"],
        "total_cost_brl_ha_nominal": nominal_cost,
        "operational_cost_brl_ha_nominal": raw_panel["operational_cost_brl_ha"],
        "total_cost_brl_ha_reference_month": float(nominal_cost) * factor,
        "deflator_factor": factor,
        "cost_definition": "CONAB CUSTO TOTAL por hectare; se a cultura/UF não tem painel, usa proxy explicitamente identificado e editável.",
        "panel_title": raw_panel["sheet_title"],
        "source_crop_id": source_crop,
        "proxy": proxy,
        "source_note": source_note,
    }


def economic_inputs(
    sources: list[dict[str, object]], panels: list[dict[str, object]],
    indices: dict[str, float], annual_indices: dict[str, float], ipca_meta: dict[str, object],
) -> dict[str, object]:
    yahoo = json.loads(YAHOO_PATH.read_text(encoding="utf-8"))
    quotes = {"soybean": None, "maize_grain": None}
    for item in yahoo["quotes"]:
        key = "soybean" if item["crop"] == "soybean" else "maize_grain" if item["crop"] == "maize" else None
        if key:
            quotes[key] = item
    lookup = panel_index(panels)
    source_urls = {str(item["file"]): item.get("source_url") for item in sources}
    state_raw = json.loads(STATE_PAM_PATH.read_text(encoding="utf-8-sig"))
    state_rows = state_pam_rows(state_raw)
    profiles: dict[str, object] = {}
    for profile_id, info in PROFILE_INFO.items():
        pam = json.loads((PAM_DIR / profile_id / "pam-history.json").read_text(encoding="utf-8"))
        crop_inputs = {}
        for crop_id in MARKOV_CROPS:
            yield_value, price, yield_source, assumption_notes = pam_crop_values(profile_id, crop_id, pam, state_rows, indices, annual_indices)
            pam_id = info["coffee_pam"] if crop_id == "coffee" else PAM_CROPS.get(crop_id)
            quote = quotes.get(crop_id)
            if quote:
                price = {
                    "brl_per_tonne": float(quote["price_brl_per_metric_ton"]),
                    "source": "Fechamento congelado de futuro CBOT no Yahoo Finance, convertido pela PTAX de venda do mesmo dia; referência de bolsa, não preço local à vista.",
                    "quote_date": quote["quote_date"], "symbol": quote["symbol"], "contract": quote["contract_name"],
                    "unit": "BRL/metric tonne", "editable_hypothesis": False,
                }
            cost = choose_cost_panel(profile_id, crop_id, profiles, panels, lookup, source_urls, indices, annual_indices)
            cost_complete = bool(cost and cost.get("total_cost_brl_ha_reference_month") is not None)
            yield_complete = yield_value is not None and float(yield_value) >= 0
            price_complete = bool(price and price.get("brl_per_tonne") is not None and float(price["brl_per_tonne"]) >= 0)
            complete = yield_complete and price_complete and cost_complete
            notes = list(assumption_notes)
            if cost and cost.get("proxy"):
                notes.append(str(cost["source_note"]))
            if cost and cost.get("match_level") != "mesmo município":
                notes.append("Custo CONAB: " + str(cost["match_level"]) + "; confira a localidade e edite o valor se necessário.")
            if crop_id in HARVESTLESS_CROPS:
                notes.append("Receita inicial zero: trata a cultura como cobertura sem colheita comercial; altere rendimento/preço para testar um uso comercial.")
            crop_inputs[crop_id] = {
                "label": CROP_LABELS[crop_id],
                "pam_product": pam_id,
                "yield_kg_ha_median_2021_2025": yield_value,
                "yield_source": yield_source,
                "price": price,
                "cost_panel": cost,
                "eligible_for_economic_comparison": complete,
                "include_in_vpl": complete,
                "editable": True,
                "assumption_notes": notes,
                "missing_inputs": [name for name, exists in (("PAM yield or explicit zero-harvest case", yield_complete), ("price or explicit zero-harvest case", price_complete), ("CONAB cost or documented proxy", cost_complete)) if not exists],
            }
        profiles[profile_id] = {
            "municipality": info["name"],
            "uf": info["uf"],
            "crop_inputs": crop_inputs,
            "economically_supported_crop_ids": [key for key, value in crop_inputs.items() if value["eligible_for_economic_comparison"]],
            "economic_exclusions": [key for key, value in crop_inputs.items() if not value["eligible_for_economic_comparison"]],
        }

    nominal_rate = 0.154211
    recent_inflation = float(ipca_meta["last_twelve_month_change_percent"]) / 100
    real_rate = (1 + nominal_rate) / (1 + recent_inflation) - 1
    return {
        "schema_version": "1.1.0",
        "purpose": "Base econômica rastreável e editável para comparar rotações; hipóteses e proxies têm origem identificada e não são recomendação agrícola nem previsão validada.",
        "reference_currency_month": ipca_meta["base_month"],
        "reference_currency_basis": "R$ constantes do último mês IPCA disponível na coleta; preços Yahoo do dia 2026-11-13 são mantidos como referência futura congelada.",
        "sources": {
            "conab_cost_workbooks": sources,
            "ibge_pam": {
                "publisher": "IBGE",
                "survey": "Produção Agrícola Municipal (PAM), SIDRA tabela 5457",
                "municipal_source_file_pattern": "data/profiles/<profile>/pam-history.json",
                "state_source_file": str(STATE_PAM_PATH.relative_to(ROOT)).replace("\\", "/"),
                "municipal_source_url": "https://apisidra.ibge.gov.br/values/t/5457/n6/1100023,3516200,3170701/v/112,214,215,216/p/1988-2025/c782/40101,40102,40103,40106,40112,40122,40124,40125,40127,40140,40141?formato=json",
                "state_source_url": "https://apisidra.ibge.gov.br/values/t/5457/n3/all/v/112,214,215,216/p/1988-2025/c782/40101,40102,40103,40106,40112,40122,40124,40125,40127,40140,40141?formato=json",
                "usage": "Yield mediano 2021–2025; PAM municipal primeiro, com fallback estadual/macrorregional/nacional. Preço unitário calculado de valor da produção / toneladas produzidas, deflacionado por IPCA. Proxies aparecem no painel e são editáveis.",
            },
            "yahoo_futures": {
                "file": str(YAHOO_PATH.relative_to(ROOT)).replace("\\", "/"),
                "as_of_date": yahoo["as_of_date"],
                "semantics": yahoo["price_semantics"],
            },
            "ipca": ipca_meta,
        },
        "discount_rate": {
            "nominal_annual_rate": nominal_rate,
            "source": "ANBIMA prefixado 5 anos, fechamento de 2026-11-12, conforme plano-MVP",
            "source_url": "https://www.anbima.com.br/informacoes/est-termo/CZ.asp",
            "inflation_proxy_12m": recent_inflation,
            "real_annual_rate_approx": real_rate,
            "formula": "(1 + taxa nominal ANBIMA) / (1 + IPCA últimos 12 meses) − 1; inflação passada é apenas aproximação da inflação esperada",
        },
        "cost_panels": panels,
        "profiles": profiles,
        "limitations": [
            "O IPCA geral equaliza datas monetárias, mas não mede inflação de insumos agropecuários.",
            "Painéis CONAB não são sempre do mesmo município, safra, sistema tecnológico ou tipo de empreendimento dos exemplos; a localidade e o nível de correspondência ficam visíveis.",
            "O VPL inclui as 14 culturas do catálogo com valores iniciais rastreáveis ou hipóteses/proxies explicitamente marcados e editáveis. Nabo, braquiária, crotalária e mucuna começam sem receita comercial e com custo proxy; feijão, milheto e aveia-preta também usam proxies identificados. Esses valores não são observações dessas culturas.",
            "Preço e custo permanecem constantes em termos reais no horizonte; preços futuros Yahoo de maio/2027 são referências de bolsa, não oferta local nem curva de cinco anos.",
            "Café e cana são perenes/semi-perenes; o painel de custo pode representar etapa de produção, e a cadeia anual não modela idade, implantação ou reforma do canavial/cafezal.",
            "A resposta de produtividade a água e carbono é hipótese explícita não calibrada; resultados VPL são exploratórios e não provam superioridade agronômica nem causal.",
            "A página ranqueia sequências completas de cinco transições que apareceram nas 10.000 trajetórias Monte Carlo; VPL e frequência dependem da amostra, e sequências raras têm alta incerteza. A probabilidade Markov indica plausibilidade sob a cadeia municipal, não validação agronômica nem restrição de manejo.",
        ],
    }


def main() -> None:
    sources, panels = extract_cost_panels()
    indices, annual_indices, ipca_meta = ipca_indices()
    payload = economic_inputs(sources, panels, indices, annual_indices, ipca_meta)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    coverage = {
        "schema_version": "1.1.0",
        "status": "all_states_editable_exploratory_vpl_available",
        "source_of_truth": "data/reference/economic-benchmarks.json",
        "objective": "maximizar o VPL esperado por hectare em cinco safras futuras entre sequências completas observadas nas trajetórias Monte Carlo iniciadas pela cultura escolhida",
        "sequence_ranking": "agrupar por sequência completa de cinco transições as rotas amostradas em 10.000 trajetórias; calcular média, mediana, faixa, probabilidade de prejuízo e cauda do VPL a partir dos ambientes simulados em que a sequência ocorreu; exibir frequência Monte Carlo e probabilidade Markov média separadamente; sinalizar que rotas raras têm baixa precisão",
        "profile_coverage": {
            profile_id: {
                "included_crop_ids": profile["economically_supported_crop_ids"],
                "excluded_crop_ids": profile["economic_exclusions"],
            }
            for profile_id, profile in payload["profiles"].items()
        },
        "markov_states": "Todas as 14 culturas são destinos Markov e têm uma linha econômica inicial editável nos três perfis. Valores observados, proxies e hipóteses de receita zero para coberturas estão diferenciados nos campos de fonte; a inclusão de cada cultura no ranking pode ser alterada na página.",
        "price_sources": {
            "soybean_and_maize": "Yahoo CBOT May-2027, snapshot 2026-11-13, convertido por PTAX; referência de bolsa, sem base local",
            "sugarcane_and_coffee": "valor unitário municipal da PAM no último ano válido, convertido a moeda-base por IPCA",
        },
        "cost_source": "Custo total CONAB por hectare quando há painel direto; para culturas sem painel, proxy de custo por cultura indicada, localidade, ano, sistema produtivo e fator IPCA constam em economic-benchmarks.json. Todos os valores podem ser editados na interface.",
        "known_limits": payload["limitations"],
    }
    COVERAGE_OUTPUT.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
