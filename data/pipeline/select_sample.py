"""Choose the validation sample: in each state, the municipality with the largest harvested area in the last PAM year.

One SIDRA request (table 5457, total of all crops, every municipality). The three example municipalities are
always kept. Writes data/catalog/municipios-amostra.json, which `--sample` reads in every fetcher.
"""

from __future__ import annotations

import json

from targets import EXAMPLES, ROOT, SAMPLE, download, municipalities

URL = "https://apisidra.ibge.gov.br/values/t/5457/n6/all/v/216/p/last%201/c782/0?formato=json"


def main() -> None:
    body, retrieved = download(URL)
    known = municipalities()
    largest: dict[str, tuple[float, str]] = {}
    year = None
    for row in json.loads(body)[1:]:
        code, year = str(row["D1C"]), row["D3C"]
        try:
            area = float(row["V"])
        except ValueError:      # "-", "..." and "X" are not areas
            continue
        if code in known and area > largest.get(known[code]["uf"], (0.0, ""))[0]:
            largest[known[code]["uf"]] = (area, code)
    chosen = {code: {"harvested_area_ha": area, "reason": "largest harvested area of the state"} for area, code in largest.values()}
    for code in EXAMPLES:
        chosen.setdefault(code, {"harvested_area_ha": None})["reason"] = "example municipality"
    SAMPLE.write_text(json.dumps({
        "purpose": "Amostra de validação dos fetchers e do pipeline antes da rodada do Brasil inteiro.",
        "rule": f"Município de maior área colhida total (PAM, variável 216, {year}) em cada UF, mais os três municípios de exemplo.",
        "source": {"url": URL, "retrieved_at_http": retrieved},
        "municipalities": [
            {"code": code, "id": known[code]["id"], "name": known[code]["name"], "uf": known[code]["uf"], **chosen[code]}
            for code in sorted(chosen)
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(chosen)} municipalities in {len(largest)} states written to {SAMPLE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
