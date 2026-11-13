# Dados e validação

## Dados previstos

| Fonte | Uso no projeto | Limite principal |
|---|---|---|
| [NASA POWER Daily](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | Temperatura, radiação, vento e variáveis meteorológicas | Resolução e incerteza podem não representar um talhão |
| [NASA GPM IMERG](https://gpm.nasa.gov/data/imerg) | Chuva e períodos secos | Estimativa por satélite; comparar com pluviômetros locais quando possível |
| [SMAP L4 / NSIDC](https://nsidc.org/data/spl4smgp/versions/4) | Contexto e validação de umidade da superfície e zona de raízes | Escala espacial maior que muitos talhões |
| [SoilGrids / ISRIC](https://isric.org/explore/soilgrids) | Prior de textura, carbono, pH e propriedades do solo | Mapa estimado; usar análise local para calibrar |
| [Embrapa](https://www.embrapa.br/web/agencia-de-informacao-tecnologica/cultivos/milho/producao/rotacao-de-culturas) | Regras de rotação e respostas agronômicas | A recomendação depende da região, cultura e manejo |
| [ZARC / MAPA](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/zoneamento-agricola) | Janelas e risco de plantio por local, solo e cultivar | Consultar a indicação vigente para cada área |
| [Conab — preços de mercado](https://consultaprecosdemercado.conab.gov.br/) | Preços para estimar margem, se necessário | Preço regional e custo da fazenda podem divergir |

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
5. **Referência:** comparar com a rotação atual ou uma prática local documentada.

Sem histórico suficiente para estimar uma transição, usar uma premissa identificada como hipótese e reportar a incerteza. Simulação não transforma essa hipótese em dado observado.
