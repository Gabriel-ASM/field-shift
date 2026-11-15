# Field Shift — submission form texts (NASA Space Apps 2026)

Draft of 2026-11-15. One block per form field, ready to paste. `[PENDENTE: …]` marks what the team must fill or
confirm; all of them are listed again at the end. Numbers come from the repository at commit `b9a4918` and from
`docs/engine-validation.md` (100,000 trajectories, seeds 1–3).

---

## Summary

Field Shift is a decision-support tool that lets a farmer compare crop rotations before committing five years of land to one of them. The farmer picks a municipality, the crop in the field today and how much weight to give income against soil and water. The tool then simulates up to 100,000 possible five-year futures: a Markov chain built from regional crop statistics and official planting windows proposes what can be planted next, and a Monte Carlo engine replays historical rainfall and reference evapotranspiration from NASA POWER to track soil water every half month, soil carbon by crop, and discounted cash flow per hectare. The result is a suggested sequence with its alternatives, each shown with its income distribution (downside, median, upside) and the final state of soil and water, plus a plain account of how it was calculated and where the evidence is thin. Field Shift is exploratory: it supports, and does not replace, the judgment of the farmer and the local agronomist.

*(about 1,000 characters)*

---

## Project Demonstration

[PENDENTE: link to the video (up to 30 s) or the slides (up to 7)]

---

## Project (links)

[PENDENTE: public URL of the app, if it is published]
[PENDENTE: repository link, if the team wants it listed — https://github.com/Gabriel-ASM/field-shift]

---

## Project Details

### The problem
Choosing a rotation is a multi-year bet made under uncertain weather. The usual shortcut, repeating the crop that paid best last season, wears the soil and concentrates risk. Farmers rarely get to see what a different sequence would have meant across many plausible seasons, in money and in soil at the same time.

### What Field Shift does
The farmer answers three questions on a map-based journey: where the farm is, what is growing now (soybean, maize or sugarcane, with the next cut for standing cane), and what matters more, return or soil and water. Field Shift answers with a suggested five-year sequence, the other good options, and for each one: net present value per hectare with its distribution (average of the worst 5% of outcomes, median, 95th percentile), final soil organic carbon and final water condition. A "Behind your estimate" panel explains the method in plain words and then in full, with equations.

[IMAGE: the journey on the map — location, crop, priorities]
[IMAGE: the result screen — suggested sequence, income, soil, water, return distribution]

### How it works
1. **What can be planted next.** A Markov chain over 14 crops. Its starting probabilities come from municipal harvested-area statistics (IBGE PAM, 1988–2025) with a Dirichlet prior (α = 0.5), restricted to crops with an open planting window in the official climate-risk zoning (MAPA ZARC).
2. **Many futures.** A Monte Carlo engine draws up to 100,000 trajectories. Each one resamples blocks of historical years of rainfall and reference evapotranspiration from NASA POWER, so the simulated weather keeps the patterns that were actually observed.
3. **Soil and water respond.** Soil water is updated every half month from rain and crop demand (FAO-56 crop coefficients); soil organic carbon changes with each crop. Water, carbon and total nitrogen then shift the odds of the next crop, so the state of the field feeds back into the decision.
4. **Money.** Yields, prices and costs (IBGE PAM, CONAB) become cash flows discounted to present value in R$/ha.
5. **Ranking.** Sequences are scored from 0 to 10 on economics (upside against downside), final soil and water, and how many simulated futures support them; the farmer's priorities set the weights.

The engine runs on the server, on a GPU when one is available, and was checked against the team's original in-browser simulator: 144 statistics over 9 cases, none differing by more than 3 standard errors.

[IMAGE: "Under the hood" — sources, engine steps, decision layer]

### What the results show, and their limits
In Franca (SP), starting from soybean, the sequence the region most often follows is soybean then sugarcane (24% of simulated futures). Sequences that reach the top of the ranking are followed in far fewer futures (20 to 45 of 100,000), so their numbers move by about 5% between random seeds; the tool reports how much evidence stands behind each suggestion.

Field Shift is exploratory, not a forecast and not agronomic advice. The simulation explores historical climate variability; it does not simulate a shifted climate. The chain comes from municipal statistics, not from the history of a field. Soil and water responses per crop, and the nitrogen balance, are stated hypotheses that have not been calibrated. SoilGrids is a gridded estimate read at the municipal centroid. Sugarcane is undervalued inside a five-year horizon because the standing field has no end value. Erosion, frost, pests and forage are not modeled. This version covers three municipalities: Ariquemes (RO), Franca (SP) and Varginha (MG), as regional examples, not fields.

### Next steps
Mark the farmer's current rotation as its own strategy next to the suggested ones, with the reason, evidence, benefits, gaps and risks of each; simulate the candidate sequences directly so every suggestion rests on a full sample; calibrate the soil and nitrogen responses with sourced values; add rainfall from GPM IMERG and soil moisture from SMAP as a regional check; extend coverage to every Brazilian municipality with data.

*(about 4,100 characters with headings and image markers)*

---

## Use of Artificial Intelligence (AI)

**In the product:** none. The recommendation comes from a Markov chain and a Monte Carlo simulation with explicit equations; no machine-learning or generative model produces or adjusts results.

**In development:** AI coding assistants (Anthropic Claude, through Claude Code) were used to write and review code, port the simulator from JavaScript to Python, write tests and draft documentation and these form texts. [PENDENTE: other AI tools used by team members, and whether any image or text in the demo was AI-generated]. All data, modeling choices and numbers were defined and checked by the team; AI-assisted code is covered by automated tests and by the statistical comparison between the two engines.

---

## NASA Data

- **NASA POWER (Prediction Of Worldwide Energy Resources), Daily API** — daily precipitation and the meteorological variables used to compute reference evapotranspiration, for each municipality; the Monte Carlo engine resamples these historical years. https://power.larc.nasa.gov/ · https://power.larc.nasa.gov/docs/services/api/temporal/daily/ [PENDENTE: exact parameter names, period of years and access date]
- **NASA GIBS (Global Imagery Browse Services), Blue Marble** — base imagery of the map on which the farmer locates the farm; display only, not an input of the model. https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api [PENDENTE: confirm the map with the GIBS basemap is in the submitted version, and confirm the documentation link]

---

## Space Agency Partner & Other Data

Not NASA data:
- **ISRIC SoilGrids 2.0** (Web Coverage Service) — initial soil organic carbon, total nitrogen, bulk density and available water capacity, 0–30 cm. https://www.isric.org/explore/soilgrids
- **IBGE** — PAM, municipal crop production, table 5457 (areas, yields, values, 1988–2025); IPCA, table 1737 (inflation adjustment); municipal and state boundaries. https://sidra.ibge.gov.br/tabela/5457
- **MAPA ZARC** — official climate-risk planting windows by municipality (Tábua de Risco). https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico
- **CONAB** — agricultural production costs. https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/arquivos-custo-de-producao/agricolas
- **FAO-56** — crop coefficients (Kc) and stage lengths. https://www.fao.org/4/x0490e/x0490e0b.htm
- **Yahoo Finance** — CBOT soybean futures used as a price reference. https://finance.yahoo.com/
- **Embrapa** — crop cycle lengths (soybean, sugarcane, cover crops).
- **MapBiomas** — agricultural land use and soil organic carbon, as context. https://brasil.mapbiomas.org/

---

## References

Data
- NASA Langley Research Center. POWER Project, Daily API. https://power.larc.nasa.gov/ [PENDENTE: version and access date]
- NASA EOSDIS. Global Imagery Browse Services (GIBS). [PENDENTE: confirm use and link]
- Poggio, L. et al. (2021). SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. SOIL, 7, 217–240. https://doi.org/10.5194/soil-7-217-2021 — ISRIC WCS: https://docs.isric.org/globaldata/soilgrids/wcs.html (CC BY 4.0) [PENDENTE: access date; confirm DOI]
- IBGE. SIDRA, Produção Agrícola Municipal, table 5457; IPCA, table 1737; Malhas territoriais API. https://sidra.ibge.gov.br/
- MAPA. Tábua de Risco, Zoneamento Agrícola de Risco Climático (ZARC), 2026/27. https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico
- CONAB. Custos de produção agrícola. https://www.gov.br/conab/
- Yahoo Finance. Soybean futures (CBOT) price history. https://finance.yahoo.com/
- MapBiomas. Uso agrícola; MapBiomas Solo, carbono orgânico do solo. https://brasil.mapbiomas.org/

Methods and agronomy
- Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). Crop evapotranspiration. FAO Irrigation and Drainage Paper 56. https://www.fao.org/4/x0490e/x0490e0b.htm
- Seifert, C. A., Roberts, M. J., & Lobell, D. B. (2017). Continuous corn and soybean yield penalties across hundreds of thousands of fields. Agronomy Journal. https://doi.org/10.2134/agronj2016.03.0134 [PENDENTE: confirm authors, year and title against the DOI]
- Garbelini et al. (2022). Crop rotations in Paraná. European Journal of Agronomy. https://doi.org/10.1016/j.eja.2022.126528 [PENDENTE: full citation from the DOI]
- Guth et al. (2002). Soybean in monoculture and rotation. II Congresso Brasileiro de Soja e Mercosoja, abstracts. Embrapa. [PENDENTE: full citation]
- Embrapa. Soybean cycles (ZARC seminar, 2023); sugarcane planting and maturation; cover crop cycles (Circular Técnica 168, 2019). [PENDENTE: full citations]
- [PENDENTE: only if the carbon and nitrogen presentation enters the submission — Coleman & Jenkinson (1996), RothC-26.3, https://doi.org/10.1007/978-3-642-61094-3_17; Jenkinson (1990); Falloon et al. (1998); University of Minnesota Extension (C:N)]

Software
- Leaflet and Leaflet.draw (maps), React, GSAP (interface), FastAPI, NumPy, CuPy, MongoDB (server). [PENDENTE: confirm this list against the submitted version]

---

## Pendências e dúvidas para o time

1. Links: vídeo ou slides da demo; URL pública do app; se o repositório será listado.
2. NASA POWER: nomes exatos dos parâmetros, período de anos baixado e data de acesso (não achei no README; está na coluna `source` do arquivo de clima).
3. NASA GIBS: confirmar que a versão submetida usa o mapa com a base Blue Marble; se a submissão for a página `visualizacao.html` sozinha, tirar o GIBS de "NASA Data" e das referências.
4. Componente de carbono e nitrogênio da máquina `space` (RothC, 10 slides): entra na submissão? O texto acima não o descreve; cita só o N total que já está na página, como hipótese.
5. Uso de IA: outras ferramentas usadas por cada membro, e se há imagem ou texto gerado por IA na demo.
6. Referências escritas de memória no brief (Poggio, RothC, Seifert, Garbelini, Guth): conferir DOI, autores e páginas antes de enviar. Data de acesso do SoilGrids.
7. Lacuna 1 do desafio (rotação atual como estratégia separada): conferir se a comparação "região × recomendada" já está na tela final; se estiver, mover do "Next steps" para "What Field Shift does".
8. Lacuna 2 (por estratégia: por que foi sugerida, evidência, benefícios, lacunas, riscos): não está escrita no formulário; fica em "Next steps". Se quiserem a comparação no texto, dá para escrever a partir dos números de `docs/engine-validation.md`.
9. Interface: conferir que não sobrou português na versão gravada.
10. O exemplo de Franca usa os números da avaliação de 15/11 (commit `47a609a`); o modelo mudou depois (nitrogênio e carbono da soja repetida). Rodar de novo `tests/parity/evaluate_results.py` antes de enviar e ajustar "24%" e "20 to 45" se mudarem.
11. Nomes e países do time: não incluídos de propósito.
