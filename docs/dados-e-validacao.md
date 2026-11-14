# Dados e validação

## Estado dos arquivos neste repositório

O relatório da coleta descreve 22 conjuntos e 55 arquivos processados para Cascavel, Toledo e Assis Chateaubriand (PR). Os originais do PR, ZARC, PAM, MapBiomas e QC continuam ausentes deste checkout. Para os exemplos solicitados, baixamos NASA POWER Daily, SoilGrids e malhas IBGE para Ariquemes (RO), Franca (SP) e Varginha (MG); veja os manifestos em `data/profiles/` e os arquivos fonte em `data/raw/`. Esses pontos municipais não são medições de talhão. O [inventário do PR](../data/catalog/coleta-oeste-pr.json) e as [métricas transcritas](../data/reference/coleta-oeste-pr-validacao.json) registram a cobertura citada sem afirmar que seus arquivos estejam carregados.

Os contratos em `data/contracts/` definem clima diário, solo em camadas, estado, observação pareada e transição. O HTML executa uma simulação de água no solo para os três perfis; não faz seleção de talhão no mapa, recomendação de cultura nem cálculo econômico. As fontes recomendadas na aba NASA Space Apps estão registradas em `data/catalog/fontes-desafio-nasa.json`.

## Dados previstos

A cobertura alvo é nacional. Usar a malha municipal do IBGE para localizar as áreas e verificar a disponibilidade das camadas por município e cultura. Séries climáticas e mapas de solo mantêm sua resolução original ao alimentar as estimativas.

| Fonte | Uso no projeto | Limite principal |
|---|---|---|
| [NASA POWER Daily](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | Temperatura, radiação, vento e variáveis meteorológicas | Resolução e incerteza podem não representar um talhão |
| [NASA GPM IMERG](https://gpm.nasa.gov/data/imerg) | Chuva e períodos secos | Estimativa por satélite; comparar com pluviômetros locais quando possível |
| [SMAP L4 v8 / NSIDC](https://nsidc.org/data/spl4smgp/versions/8) | Comparação regional de umidade da superfície e zona de raízes | Conferir o aviso de reprocessamento de 14 de maio a 28 de julho de 2026 antes de usar o trecho |
| [SoilGrids / ISRIC](https://isric.org/explore/soilgrids) | Prior de textura, carbono, pH e propriedades do solo | Mapa estimado; usar análise local para calibrar |
| [Embrapa](https://www.embrapa.br/web/agencia-de-informacao-tecnologica/cultivos/milho/producao/rotacao-de-culturas) | Regras de rotação e respostas agronômicas | A recomendação depende da região, cultura e manejo |
| [ZARC / MAPA](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/zoneamento-agricola) | Janelas e risco de plantio por local, solo e cultivar | Consultar a indicação vigente para cada área |
| [Conab — preços de mercado](https://consultaprecosdemercado.conab.gov.br/) | Preços para estimar margem, se necessário | Preço regional e custo da fazenda podem divergir |
| [IBGE PAM / SIDRA](https://sidra.ibge.gov.br/pesquisa/pam/tabelas) | Área e produtividade de referência | Agregação municipal |
| [FAO-56](https://www.fao.org/4/X0490E/x0490e0b.htm) | Coeficiente de cultivo e duração por fase | Conferir extrato e adequação regional antes de parametrizar |

## Frequência e responsabilidade

As frequências do núcleo seguem a seção 3 do relatório da coleta. O publicador identifica a origem institucional. O responsável interno é o papel que revisa a ingestão, as lacunas e as mudanças de versão. Antes de habilitar uma série, registrar no manifesto o nome da pessoa que ocupa esse papel.

| Dado | Publicador ou origem | Frequência nativa → uso | Responsável interno |
|---|---|---|---|
| Malha municipal | IBGE | Edição anual → geometria fixa por versão | Geodados |
| POWER e ET₀ | NASA POWER e Field Shift, com método FAO-56 | Diária em hora solar local → diária | Clima |
| IMERG V07 | NASA GPM | 30 min → chuva diária | Clima |
| ERA5-Land | ECMWF/Copernicus | Horária → chuva diária | Clima |
| SMAP L4 | NASA/NSIDC | 3 h → média diária | Clima |
| Estações | INMET | Horária → diária para comparação, coletada por arquivo anual | Clima |
| NDVI e EVI MOD13Q1 | NASA LP DAAC | Composição de 16 dias → 16 dias | Geodados |
| ONI e NEX-GDDP-CMIP6 | NOAA CPC e NASA, respectivamente | ONI mensal com trimestre móvel e projeções diárias → manter cada frequência | Clima |
| Clima observado consolidado | Field Shift, a partir de POWER, IMERG, ERA5-Land e SMAP | União diária por município e data | Clima |
| MapBiomas e PAM | MapBiomas e IBGE, respectivamente | Anual → histórico anual | Geodados |
| ZARC | MAPA | Por safra → janelas em decêndios | Agronomia |
| Solo, CAD e relevo | ISRIC SoilGrids, IBGE SiBCS, NASADEM e derivados Field Shift | Estático → atualizar por versão | Geodados |
| Parâmetros de cultivo e classes | FAO-56, Embrapa, registros regionais e premissas Field Shift | Por cultura e fase → versionar a cada revisão | Agronomia |
| Medições e manejo do talhão | Produtor ou laboratório identificado | Por medição ou operação → carregar na configuração | Agronomia |
| Ajustes futuros | [B3](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/up2data/dados-disponiveis/) e [ICE](https://www.ice.com/agriculture/sugar) | Por pregão → curva na data base e preço por safra | Mercado |
| Preços locais, custos e câmbio | Produtor, Conab e BCB/PTAX, conforme o dado | Conforme a publicação ou operação → usar no período correspondente e simular choques mensais | Mercado |
| Juros longos | [ANBIMA ETTJ](https://developers.anbima.com.br/pt/documentacao/precos-indices/apis-de-precos/titulos-publicos/) | Diária → congelar o último fechamento disponível na data base | Mercado |
| Pesos, taxa substituta e demais escolhas da execução | Produtor ou perfil Field Shift | Por execução → registrar origem do valor ativo | Produto |

O manifesto registra também versão, data de referência, cobertura, unidade, resolução, regra de agregação, arquivo e status de qualidade. Usar o fuso local do município para a agregação diária e documentar conversões entre dia civil e hora solar local. Para os derivados, preservar os identificadores das séries de origem. Cada premissa tem responsável, versão, valor inicial e faixa de sensibilidade quando aplicável.

## Conferência das fontes

A conferência usa o texto da aba **NASA Data & Resources** fornecido pela equipe. O acesso direto à [aba Resources](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=resources) permaneceu indisponível. A lista abaixo registra a aderência ao MVP e distingue a família citada no desafio do produto descrito no relatório.

| Prioridade | Recursos do desafio | Uso previsto |
|---|---|---|
| Núcleo | NASA POWER, GPM/IMERG | Meteorologia para calcular ET₀ e chuva para o balanço hídrico diário. Manter a distinção entre IMERG Final e provisório |
| Comparação regional | SMAP | Comparar umidade com o balanço hídrico na escala do produto. A coleta usa SMAP L4 v8, que estima umidade superficial e radicular por assimilação |
| Apoio já descrito na coleta | Landsat e MODIS/VIIRS, SRTM, ERA5 | Usar MODIS MOD13Q1 para vegetação, NASADEM para relevo e ERA5-Land para complementar a série de chuva. NASADEM é derivado do SRTM. ERA5-Land é um produto distinto do ERA5 |
| Complementos | Landsat, VIIRS, Sentinel-2, ECOSTRESS, GLDAS, FAO GAEZ e GEDI | Avaliar conforme cobertura e finalidade. Imagens e índices ajudam a observar vegetação. ECOSTRESS apoia a leitura de temperatura superficial e evapotranspiração. GLDAS e GAEZ oferecem contexto regional. GEDI fica reservado ao contexto de vegetação alta |
| Expansão e pesquisa | NLDAS, Web Soil Survey, SSURGO/STATSGO2, CDL/CropScape, PRISM, NAIP, NLCD, CoCoRaHS, NWIS, USDA AMS Market News, NASS Quick Stats, OpenET, LANDFIRE e USDA Ag Data Commons | Avaliar em um perfil para EUA ou América do Norte conforme cobertura. Consultar Ag Data Commons por estudo. No Brasil, priorizar fontes locais para clima, solo, histórico agrícola e mercado |

Os complementos entram quando respondem a uma lacuna concreta. Documentação técnica: [MODIS MOD13Q1](https://lpdaac.usgs.gov/products/mod13q1v061/), [NASADEM](https://www.earthdata.nasa.gov/data/catalog/lpcloud-nasadem-hgt-001), [ERA5-Land](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land), [Sentinel-2](https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-2) e [FAO GAEZ](https://www.fao.org/gaez/en).

O [relatório da coleta](../research/relatorio_coleta_final_2026-11-10-v3.md) registra cobertura, comparações e lacunas no Oeste do Paraná e serve como referência para aplicar o método de coleta no restante do país. O manifesto e as séries processadas citadas no relatório não estão neste repositório. Antes do ajuste, verificar arquivos, unidades, qualidade e disponibilidade por região e cultura. O relatório registra custos Conab como pendentes na coleta. O módulo econômico pode partir de valores informados pelo produtor ou de premissas identificadas.

## Dados mínimos para começar

- Localização e delimitação da área de estudo.
- Histórico de culturas e datas de plantio/colheita.
- Solo local, ou mapas explicitamente marcados como aproximação.
- Série histórica de clima e conjunto inicial de culturas/ações.
- Prioridades do produtor: retorno, água, saúde do solo ou combinação.

NASA fornece observações da Terra; histórico agrícola, análises de solo e preferências vêm de fontes locais. Resolução de satélite não deve ser confundida com medição no talhão.

## Validação planejada

1. **Clima:** comparar os cenários simulados com chuva, temperatura e veranicos observados na mesma região e estação.
2. **Água e solo:** comparar classes estimadas com análises, sensores ou observações de campo; usar SMAP como referência de escala regional.
3. **Transições e produção:** estimar em safras anteriores e testar em safras posteriores, sem misturar dados futuros no ajuste.
4. **Robustez:** repetir com outras sementes e mais trajetórias; confirmar que os resultados estabilizam e que diferenças entre estratégias persistem.
5. **Rotação:** conferir se as sequências propostas respeitam as janelas e são coerentes com as práticas agronômicas documentadas.

Sem histórico suficiente para estimar uma transição, usar uma premissa identificada como hipótese e reportar a incerteza. Simulação não transforma essa hipótese em dado observado.
