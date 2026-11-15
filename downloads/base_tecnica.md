# Field Shift — Base técnico-científica para recomendação e rotação de culturas

15/11/2026

## Escopo, convenções e lacunas

Este documento reúne apenas valores que consegui verificar em fonte aberta nesta sessão; toda célula sem verificação traz **"Não encontrado em fonte científica verificada."** (NE). A base serve ao Field Shift (Oeste do Paraná: Cascavel, Toledo, Assis Chateaubriand) e não é uma revisão exaustiva das 14 culturas.

**Convenções.** Origem do dado: [exp] experimental, [ref] valor de referência/norma, [est] estimativa, [mod] resultado de modelo, [hip] hipótese. Correlação não é tratada como causalidade. Onde fontes divergem, as duas aparecem.

**Lacunas principais desta sessão:**

- Janelas do ZARC para os três municípios **não foram extraídas**: o proxy da sessão bloqueou o domínio dados.agricultura.gov.br (HTTP 403). O padrão de acesso está na Entrega III; nenhuma janela foi inventada.
- Kc inicial, faixas ideais de N/CTC/COS, tabelas BBCH e produtividade CONAB por cultura e região ficaram em grande parte NE.
- Não há equações de tempo validadas para recuperação de densidade, porosidade e resistência à penetração após culturas de cobertura: entram na classe C da arquitetura.
- Culturas ambíguas: braquiária = *Urochloa brizantha* (referência adotada, [hip]); crotalária = *Crotalaria juncea* (referência adotada, [hip]); mucuna = *Mucuna pruriens* (referência adotada, [hip]).

## Entrega I-A — Cultura e solo (tabelas 1–7)

Somente botânica e profundidade radicular de culturas comerciais têm valor verificado; faixas de pH, N, CTC e COS por cultura ficaram NE.

### Tabela 1 — Botânica e raízes

Zr = profundidade radicular efetiva de [FAO-56, Tabela 22](https://www.fao.org/4/x0490e/x0490e0e.htm) [ref]; p = fração de esgotamento sem estresse (ETc ≈ 5 mm/dia). Profundidade máxima documentada: NE.

| Cultura | Espécie | Família | Tipo de ciclo | Zr (m) | p | Papel na rotação |
| --- | --- | --- | --- | --- | --- | --- |
| Soja | *Glycine max* (L.) Merr. | Fabaceae | anual | 0,6–1,3 | 0,50 | comercial; fixa N (FBN) |
| Milho | *Zea mays* L. | Poaceae | anual | 1,0–1,7 | 0,55 | comercial; palha |
| Cana-de-açúcar | *Saccharum* spp. | Poaceae | semiperene | 1,2–2,0 | 0,65 | comercial |
| Café | *Coffea arabica* L. | Rubiaceae | perene | 0,9–1,5 | 0,40 | comercial |
| Sorgo | *Sorghum bicolor* (L.) Moench | Poaceae | anual | 1,0–2,0 | 0,55 | comercial/cobertura |
| Trigo | *Triticum aestivum* L. | Poaceae | anual | 1,5–1,8 | 0,55 | comercial (inverno) |
| Feijão | *Phaseolus vulgaris* L. | Fabaceae | anual | 0,6–0,9 | 0,45 | comercial; fixa N |
| Amendoim | *Arachis hypogaea* L. | Fabaceae | anual | 0,5–1,0 | 0,50 | comercial; fixa N |
| Aveia-preta | *Avena strigosa* Schreb. | Poaceae | anual | NE | NE | cobertura |
| Nabo-forrageiro | *Raphanus sativus* L. var. *oleiferus* | Brassicaceae | anual | NE | NE | cobertura/descompactação biológica [hip] |
| Braquiária | *Urochloa brizantha* (ref. adotada) | Poaceae | perene | NE | NE | cobertura/pastagem |
| Milheto | *Pennisetum glaucum* (L.) R.Br. | Poaceae | anual | NE | NE | cobertura |
| Crotalária | *Crotalaria juncea* L. (ref. adotada) | Fabaceae | anual | NE | NE | cobertura; fixa N |
| Mucuna | *Mucuna pruriens* (L.) DC. (ref. adotada) | Fabaceae | anual | NE | NE | cobertura; fixa N |

Família, espécie e tipo de ciclo são taxonomia estável; a coluna de papel é classificação funcional geral, não resultado experimental.

### Tabela 2 — Temperatura do solo

Nenhum limiar de temperatura do solo por cultura foi verificado (NE para as 14 culturas: mínimo, ótimo, máximo e fases de germinação). O dado de entrada existe nas camadas pedidas: o ERA5-Land fornece temperatura do solo em quatro níveis, entre eles 0–7, 7–28 e 28–100 cm, o que permite cobrir as três profundidades sem remapeamento.

### Tabela 3 — pH

Faixas mínima/ideal/máxima por cultura: NE para as 14 culturas. Atenção à unidade: o SoilGrids entrega pH em água (phh2o), enquanto o manejo brasileiro usa pH CaCl₂ ou SMP; não há conversão verificada aqui e ela não deve ser aplicada sem calibração regional [hip].

### Tabela 4 — Nitrogênio

N total (g/kg, SoilGrids) ≠ N mineral (NH₄⁺ + NO₃⁻) ≠ necessidade de adubo nitrogenado; as faixas por cultura são NE. Para as leguminosas (soja, feijão, amendoim, crotalária, mucuna) a FBN entra como balanço de massa, não como faixa de N do solo [hip].

### Tabela 5 — CTC

Faixas por cultura: NE. Distinguir CTC efetiva de CTC a pH 7; o SoilGrids (cec) refere-se a pH 7.

### Tabela 6 — Carbono orgânico do solo (COS)

Faixas por cultura: NE. Conversão: COS (g/kg) = soc mapeado ÷ 10; matéria orgânica não deve ser obtida por fator fixo sem fonte.

### Tabela 7 — Propriedades físicas

| Propriedade | Critério/modelo verificado | Valor | Origem | Observação |
| --- | --- | --- | --- | --- |
| Resistência à penetração (RP) limitante | LLWR/IHO | 2 MPa | [ref] | limite inferior de θ = máx(θ em PMP, θ em RP = 2 MPa) |
| Porosidade de aeração mínima | LLWR/IHO | 10% | [ref] | limite superior de θ = mín(θ em CC, θ com 10% de ar) |
| RP em função de θ e Ds | Busscher: RP = a·θ^b·Ds^c | a, b, c ajustados por solo | [mod] | parâmetros NE para Latossolos do Oeste do PR |
| Densidade, porosidade total, macro/microporosidade, condutividade hidráulica, estabilidade de agregados | por cultura | NE | — | — |

Densidade do solo no SoilGrids (bdod) vem em cg/cm³: dividir por 100 para kg/dm³.

## Entrega I-B — Clima, calendário, água e mercado (tabelas 8–13)

O bloco hídrico (FAO-56) é o mais sólido; ZARC, produtividade e preços dependem de download ou consulta que não foi possível nesta sessão.

### Tabela 8 — Temperatura do ar e graus-dia

Temperaturas base, ótimas e letais por fase: NE para as 14 culturas. O único critério verificado é o de geada da soja no ZARC (Tmin ≤ 3 °C) [ref]. O modelo de graus-dia é a forma geral, com Tb de cada cultura a ser preenchida de fonte verificada:

```latex
GDD = \sum_{d} \max\!\left(0,\ \frac{T_{max,d}+T_{min,d}}{2}-T_b\right)
```

### Tabela 9 — Fenologia (BBCH)

Estádios BBCH e duração de cada fase por cultura e cultivar: NE. Fase vegetativa, florescimento e enchimento de grãos não devem ser inferidos de ciclo total.

### Tabela 10 — ZARC

| Item | Situação |
| --- | --- |
| Níveis de risco | 20%, 30% e 40% [ref] |
| Resolução | por município, safra, grupo de cultivar e tipo de solo [ref] |
| Janelas Cascavel / Toledo / Assis Chateaubriand | **Não extraídas** (domínio bloqueado no ambiente); NE |
| Observação | janela de plantio do ZARC ≠ época de colheita; colheita deve ser derivada do ciclo, não lida do ZARC |

### Tabela 11 — ETo, Kc e ETc (FAO-56)

```latex
ET_c = K_c \cdot ET_o \qquad p_{aj} = p_{T22} + 0{,}04\,(5 - ET_c),\quad 0{,}1 \le p_{aj} \le 0{,}8
```

Kc de referência ([FAO-56, Tabela 12](https://www.fao.org/4/x0490e/x0490e0b.htm)) vale para clima sub-úmido (UR mín ≈ 45%, u2 ≈ 2 m/s) e exige correção por clima local. Valores de Kc mid e Kc end foram recuperados de trechos de busca; **conferir no texto original antes de usar**. Kc ini: NE.

| Cultura | Kc ini | Kc mid | Kc end |
| --- | --- | --- | --- |
| Soja | NE | 1,15 | 0,50 |
| Milho (grão) | NE | 1,20 | 0,60 |
| Cana-de-açúcar | NE | 1,25 | 0,75 |
| Café | NE | 0,95–1,10 | 0,95–1,10 |
| Sorgo | NE | 1,00–1,10 | 0,55 |
| Trigo | NE | 1,15 | 0,25–0,40 |
| Feijão | NE | 1,15 | 0,35 |
| Amendoim | NE | 1,15 | 0,60 |
| Aveia, nabo, braquiária, milheto, crotalária, mucuna | NE | NE | NE |

Para estresse hídrico, Ks = (TAW − Dr)/((1 − p)·TAW) quando Dr > p·TAW (FAO-56, abordagem de coeficiente de estresse); TAW depende de θ em CC, θ em PMP e Zr.

### Tabela 12 — Produtividade

Produtividade por cultura e região (CONAB, IBGE/PAM, Embrapa) e biomassa de culturas de cobertura: NE nesta sessão. A PAM (SIDRA) e os levantamentos da CONAB são as fontes a consultar; é preciso separar produtividade potencial, atingível e média observada.

### Tabela 13 — Dados financeiros

| Dado | Fonte | Tipo | Observação |
| --- | --- | --- | --- |
| Preço à vista de soja, milho, trigo, café, açúcar | CEPEA/ESALQ | spot | preço regional não é o preço ao produtor local |
| Contratos futuros | B3 | futuro | não misturar com spot |
| Custos de produção | CONAB | custo médio por região | valores NE nesta sessão |

Nenhum preço ou endpoint foi inventado; cotações devem ser lidas na fonte, com data.

## Entrega II — Modelos de mudança do solo

Há modelos maduros para carbono (RothC, Century/DayCent) e para a distribuição de raízes e resistência à penetração; **não foi encontrada equação de tempo validada** para recuperação de densidade, porosidade ou RP após cobertura vegetal.

| Modelo | Propriedade | Equação / estrutura | Entradas | Aplicação no Brasil | Origem |
| --- | --- | --- | --- | --- | --- |
| RothC | COS (5 compartimentos: DPM, RPM, BIO, HUM, IOM) | decaimento de 1ª ordem mensal com modificadores de temperatura, umidade e cobertura | C aportado, argila, T, chuva, evaporação | uso em solos brasileiros (validações pontuais; escopo regional não verificado) | [mod] |
| Century / DayCent | COS, N, ciclagem | compartimentos ativo/lento/passivo, passo mensal (Century) ou diário (DayCent) | clima, textura, manejo, aportes | validações brasileiras encontradas; detalhe NE | [mod] |
| Distribuição radicular de Gale–Grigal / Jackson | fração de raízes acima de d | Y = 1 − β^d (d em cm) | β por tipo de vegetação | genérico; β por cultura NE | [mod] |
| Busscher | RP | RP = a·θ^b·Ds^c | θ, Ds | parâmetros por solo, NE para a região | [mod] |
| LLWR/IHO | faixa de água não limitante | limites θ_CC, θ_PMP, θ_RP=2 MPa, θ_ar=10% | curvas de retenção e de RP | uso consolidado na literatura de solos tropicais (não verificado aqui) | [ref] |
| Densidade, porosidade, RP, agregação, K pós-cultura | tempo | NE | — | — | — |

**RothC — constantes verificadas.** k (ano⁻¹): DPM 10, RPM 0,3, BIO 0,66, HUM 0,02; razão DPM/RPM de resíduos agrícolas = 1,44; produtos da decomposição divididos em BIO e HUM na proporção 46:54 (função da argila); IOM = 0,049·COS^1,139 (t C/ha).

**Fração radicular por camada** (Jackson, Y = 1 − β^d), calculada para as camadas pedidas, com β genérico (não específico de cultura) [mod]:

| Vegetação (β) | 0–7 cm | 7–28 cm | 28–100 cm | > 100 cm |
| --- | --- | --- | --- | --- |
| Todos os ecossistemas (0,966) | 21,5% | 40,5% | 34,8% | 3,1% |
| Gramíneas (0,952) | 29,1% | 45,6% | 24,5% | 0,7% |
| Pastagem temperada (0,943) | 33,7% | 47,0% | 19,1% | 0,3% |

Os β usados são valores genéricos de Jackson et al. recordados desta sessão; confirmar na publicação antes de uso.

### Simuladores e integração com Python

| Simulador | Foco | Integração Python | Licença |
| --- | --- | --- | --- |
| DSSAT (inclui módulo CENTURY) | crescimento, água, N, C | DSSATTools | aberto |
| APSIM | sistemas de cultivo e rotação | apsimNGpy | aberto |
| AquaCrop | produtividade limitada por água | AquaCrop-OSPy | aberto |
| DNDC | C e N, gases | NE | NE |

Validações brasileiras por simulador: NE além das de Century/DayCent citadas acima.

### Estrutura conceitual de rotação

```latex
Solo_{t+1} = f\left(Solo_t,\ Cultura,\ Clima,\ Manejo,\ \Delta t\right)
```

Isto é um esqueleto conceitual [hip], não um modelo validado. Cada componente de Solo (COS, N, Ds, RP) precisa de sua própria função; hoje só COS tem modelo mecanístico verificado (RothC/Century).

## Entrega III — Dados, APIs e conversão do SoilGrids

Todos os insumos de clima e solo do projeto têm fonte aberta consultável remotamente; o ZARC é o único insumo crítico que depende de download de CSV, e o SoilGrids exige conversão de unidades.

### Tabela de disponibilidade

Classe: **O** observado, **S** sensoriamento remoto, **R** reanálise, **M** modelo, **E** estático. Resoluções e frequências abaixo são as nominais conhecidas das bases; atualização e limites de uso: conferir na fonte.

| Variável | Fonte | Classe | Resol. espacial | Resol. temporal | Acesso | Limitações |
| --- | --- | --- | --- | --- | --- | --- |
| Temp., radiação, vento, UR, chuva (ponto) | NASA POWER | R/M | ~0,5° | diária | API REST (abaixo) | grade grosseira; subestima extremos locais |
| Precipitação | IMERG (NASA) | S | ~0,1° | 30 min a mensal | earthaccess/CMR, GEE | viés por satélite; calibrar com pluviômetros |
| Temperatura do solo 0–7, 7–28, 28–100 cm | ERA5-Land | R | ~9 km | horária | Copernicus CDS, GEE | modelo, não medição; incerteza em solo tropical não verificada |
| pH, areia/silte/argila, COS, CTC, N, Ds | SoilGrids 2.0 | M/E | 250 m | estático | GEE, WCS; **API REST pausada** | incerteza por pixel; pH em água; ver conversão |
| Solos do Brasil | IBGE / PronaSolos | E | variável | estático | download | escala e cobertura desiguais |
| Relevo | NASADEM | S | 30 m | estático | earthaccess, GEE | — |
| Uso e cobertura | MapBiomas | S | 30 m | anual | GEE, download | classificação de safra/cultura limitada |
| Produção e área colhida municipal | IBGE PAM (SIDRA) | O | município | anual | API SIDRA | defasagem; sem informação de cultivar |
| Janelas de plantio | ZARC (MAPA, CKAN) | M/O | município | por safra | CKAN / CSV | **não baixado nesta sessão** |
| Clima futuro | NEX-GDDP-CMIP6 | M | 0,25° | diária | NASA / GEE | correção estatística; incerteza entre modelos |
| Preços | CEPEA, B3; custos CONAB | O | — | diária a mensal | sites / download | sem endpoint verificado |

### Consulta remota sem baixar raster

- **NASA POWER (ponto, diário):** `GET https://power.larc.nasa.gov/api/temporal/daily/point?start=20240101&end=20240131&latitude=<lat>&longitude=<lon>&community=ag&parameters=T2M,PRECTOTCORR&format=json` [ref].
- **SoilGrids no GEE:** `ee.Image("projects/soilgrids-isric/phh2o_mean")`; reduzir por ponto ou polígono com `reduceRegion` evita baixar o raster.
- **ZARC:** o conjunto está no portal de dados abertos do MAPA (CKAN). Em uma sessão com o domínio liberado, listar os recursos pelo `package_show` da API CKAN e filtrar o CSV por município e cultura; os nomes de colunas é preciso conferir no arquivo.

### Tabela de conversão do SoilGrids

O SoilGrids guarda inteiros; divida pelo fator para obter a unidade final. Camadas: 0–5, 5–15, 15–30, 30–60, 60–100, 100–200 cm.

| Variável (asset) | Divisão | Unidade final |
| --- | --- | --- |
| pH em água (phh2o_mean) | ÷ 10 | pH |
| Areia, silte, argila (sand/silt/clay_mean) | ÷ 10 | % (massa) |
| Carbono orgânico (soc_mean) | ÷ 10 | g/kg |
| CTC (cec_mean) | ÷ 10 | cmol(c)/kg |
| Nitrogênio total (nitrogen_mean) | ÷ 100 | g/kg |
| Densidade do solo (bdod_mean) | ÷ 100 | kg/dm³ |
| Fragmentos grossos (cfvo_mean) | ÷ 10 | % (vol) |
| Densidade de COS (ocd_mean) | ÷ 10 | kg/m³ |
| Estoque de COS (ocs_mean) | ÷ 10 | kg/m² |

**Reamostragem para 0–7, 7–28 e 28–100 cm.** Média ponderada pela espessura de sobreposição, assumindo valor uniforme em cada camada [hip]:

| Camada-alvo | Composição (cm de cada camada SoilGrids) |
| --- | --- |
| 0–7 | 5 de 0–5 + 2 de 5–15 |
| 7–28 | 8 de 5–15 + 13 de 15–30 |
| 28–100 | 2 de 15–30 + 30 de 30–60 + 40 de 60–100 |

Valor da camada = Σ(espessura × valor) ÷ espessura total. Vale para propriedades intensivas (pH, textura, CTC, N, Ds); para estoques, somar em vez de ponderar.

## Entrega IV — Arquitetura do sistema

Com o que foi verificado, dá para implementar agora o núcleo hídrico-climático e o filtro ZARC; o módulo de evolução do solo só é defensável para carbono.

Fluxo proposto: (1) ingestão de clima e solo por ponto/município; (2) filtro duro ZARC (janela e risco); (3) balanço hídrico FAO-56 por cultura; (4) estado do solo pelo módulo de carbono; (5) pontuação de compatibilidade cultura×sucessora; (6) cenários climáticos por Monte Carlo/Markov, com parâmetros em config/*.yaml.

| Classe | Componente | Base científica | Condição |
| --- | --- | --- | --- |
| **A — implementável agora** | Ingestão NASA POWER, SoilGrids (com conversão), ERA5-Land | APIs e tabela de conversão verificadas | — |
| **A** | Balanço hídrico ETc = Kc·ETo, Zr e p por cultura comercial | FAO-56 Tabelas 12 e 22 | conferir Kc no original; Kc ini NE |
| **A** | Distribuição de raízes por camada | Y = 1 − β^d | β genérico até calibrar |
| **A** | Módulo de carbono do solo | RothC (constantes verificadas) | exige aportes de C e clima mensal |
| **A** | Filtro ZARC | CSV do MAPA | **depende do download do CSV** |
| **B — exige calibração regional** | Faixas de pH, N, CTC, COS por cultura | NE na literatura recuperada | Manual de adubação do Paraná/Embrapa |
| **B** | Temperaturas base e fenologia (BBCH) | NE | fontes por cultivar |
| **B** | Parametrização de RP (Busscher) e LLWR | forma funcional verificada | ajuste com dados locais de Latossolo |
| **B** | Kc das culturas de cobertura | NE | experimentos ou literatura |
| **B** | Produtividade e custos | CONAB/PAM | coleta e padronização |
| **C — evidência insuficiente** | Recuperação de Ds, porosidade e RP por tempo após culturas de cobertura | nenhuma equação validada encontrada | tratar como hipótese; não entra no escore |
| **C** | Efeito causal de cada cultura de cobertura na produtividade seguinte | não verificado | não atribuir causalidade a correlações |
| **C** | Simulação integrada de rotação, Solo(t+1) = f(…) | esqueleto conceitual | não validado |

## Fontes

- [FAO-56, Cap. 8 — Tabela 22 (Zr e p)](https://www.fao.org/4/x0490e/x0490e0e.htm)
- [FAO-56, Cap. 6 — Tabelas 12 e 17 (Kc, Kcb)](https://www.fao.org/4/x0490e/x0490e0b.htm)
- NASA POWER (API diária por ponto), SoilGrids 2.0 / ISRIC (GEE), ERA5-Land (Copernicus), ZARC (MAPA, dados abertos), IBGE PAM (SIDRA), CEPEA/ESALQ, B3, CONAB — catálogo R001–R108 do projeto (`field-shift-recursos.md`).
- RothC, Century/DayCent, DSSAT, APSIM, AquaCrop-OSPy: documentação e literatura dos modelos; referências originais e validações brasileiras devem ser citadas na forma completa antes da publicação.

As páginas da FAO não puderam ser abertas diretamente nesta sessão (acesso bloqueado); os valores de Zr, p e Kc vieram de trechos de busca.
