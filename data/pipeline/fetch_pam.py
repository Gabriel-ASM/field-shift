"""Download municipal crop histories from IBGE PAM/SIDRA table 5457."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
MUNICIPALITIES = ("1100023", "3516200", "3170701")
STATE_LEVEL = "all"
PRODUCTS = {
    "40101": "amendoim_em_casca",
    "40102": "arroz_em_casca",
    "40103": "aveia_em_grao",
    "40106": "cana_de_acucar",
    "40112": "feijao_em_grao",
    "40122": "milho_em_grao",
    "40124": "soja_em_grao",
    "40125": "sorgo_em_grao",
    "40127": "trigo_em_grao",
    "40140": "cafe_arabica",
    "40141": "cafe_canephora",
}
VARIABLES = {"112": "rendimento_medio_kg_ha", "214": "quantidade_produzida_t", "215": "valor_producao_mil_reais", "216": "area_colhida_ha"}
URL = (
    "https://apisidra.ibge.gov.br/values/t/5457/n6/"
    + ",".join(MUNICIPALITIES)
    + "/v/"
    + ",".join(VARIABLES)
    + "/p/1988-2025/c782/"
    + ",".join(PRODUCTS)
    + "?formato=json"
)
STATE_URL = (
    "https://apisidra.ibge.gov.br/values/t/5457/n3/"
    + STATE_LEVEL
    + "/v/"
    + ",".join(VARIABLES)
    + "/p/1988-2025/c782/"
    + ",".join(PRODUCTS)
    + "?formato=json"
)


def main() -> None:
    request = Request(URL, headers={"User-Agent": "FieldShift-OpenData/1.0"})
    with urlopen(request, timeout=120) as response:
        raw = json.load(response)
        retrieved_at = response.headers.get("Date")
    destination = ROOT / "data" / "raw" / "ibge" / "pam-municipal-5457-1988-2025.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {
                "source": {
                    "publisher": "IBGE",
                    "survey": "Produção Agrícola Municipal (PAM)",
                    "table": 5457,
                    "url": URL,
                    "classification": {"id": 782, "name": "Produto das lavouras temporárias e permanentes", "categories": PRODUCTS},
                    "period": "1988–2025",
                    "municipalities_ibge": MUNICIPALITIES,
                    "variables": VARIABLES,
                    "retrieved_at_http": retrieved_at,
                    "units": {
                        "112": "kg/ha",
                        "214": "t",
                        "215": "mil R$; nominal, not inflation-adjusted",
                        "216": "ha",
                    },
                },
                "records": raw[1:],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(raw) - 1:,} PAM records written to {destination.relative_to(ROOT)}")

    state_request = Request(STATE_URL, headers={"User-Agent": "FieldShift-OpenData/1.0"})
    with urlopen(state_request, timeout=120) as response:
        state_raw = json.load(response)
        state_retrieved_at = response.headers.get("Date")
    state_destination = ROOT / "data" / "raw" / "ibge" / "pam-state-5457-1988-2025.json"
    state_destination.write_text(
        json.dumps(
            {
                "source": {
                    "publisher": "IBGE",
                    "survey": "Produção Agrícola Municipal (PAM)",
                    "table": 5457,
                    "url": STATE_URL,
                    "classification": {"id": 782, "name": "Produto das lavouras temporárias e permanentes", "categories": PRODUCTS},
                    "territorial_level": "Unidades da Federação",
                    "period": "1988–2025",
                    "variables": VARIABLES,
                    "retrieved_at_http": state_retrieved_at,
                    "units": {
                        "112": "kg/ha",
                        "214": "t",
                        "215": "mil R$; nominal, not inflation-adjusted",
                        "216": "ha",
                    },
                    "usage": "Preencher faltas de série municipal com rendimento e valor unitário observados no estado; não é estimativa do município ou talhão.",
                },
                "records": state_raw[1:],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(state_raw) - 1:,} state-level PAM records written to {state_destination.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
