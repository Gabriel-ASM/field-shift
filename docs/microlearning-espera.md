# Microlearning na espera da simulação

Cards para a tela "We're growing possibilities" (`SimulationStep.tsx`), que aparece enquanto o motor roda.
Cada card explica uma ideia que o resultado final usa, com as mesmas palavras do diálogo "Wanna know how it was calculated?" e dos textos de métricas.

Conteúdo em inglês, porque a interface é toda em inglês. A coluna "PT" é só para revisão.

Regras de exibição (a definir na implementação):

- Um card por vez, trocando a cada ~8 s; o contador de cenários continua visível.
- Ordem fixa, da ideia mais geral para a mais técnica.
- Se a simulação for mais rápida que a leitura, o último card fica na tela até o resultado chegar.
- Sem botões de avanço nem tempo mínimo de espera: o card não pode atrasar o resultado.

| # | Título | EN | PT |
|---|---|---|---|
| 1 | Many futures | We don't forecast one year. Each simulated scenario draws its own sequence of weather years from the region's history. | Não prevemos um único ano. Cada cenário simulado sorteia uma sequência de anos climáticos do histórico da região. |
| 2 | Same environment, fair comparison | Every sequence faces the same scenarios and the same seed, so the comparison is fair. The same seed reproduces the result exactly. | Todas as sequências enfrentam os mesmos cenários e a mesma semente, então a comparação é justa. A mesma semente reproduz o resultado exatamente. |
| 3 | Crop states | Each crop is a state. Regional history, water and soil guide the odds of the next crop in the sequence. | Cada cultura é um estado. Histórico regional, água e solo orientam a chance da próxima cultura na sequência. |
| 4 | Water in the soil | Rain and evaporation update the water in the soil every half month, adjusted for what each crop needs. | Chuva e evaporação atualizam a água no solo a cada quinze dias, ajustada à necessidade de cada cultura. |
| 5 | Value over time | Income and costs over five years are brought to today's value in R$/ha. A harvest later counts for less than one now. | Receitas e custos de cinco anos são trazidos ao valor de hoje em R$/ha. Uma colheita mais tarde vale menos que uma agora. |
| 6 | Median net income | The estimated net income is the median: half of the scenarios end above it and half below. | A renda líquida estimada é a mediana: metade dos cenários termina acima dela e metade abaixo. |
| 7 | CVaR₅: the bad years | CVaR₅ is the average of the worst 5% of outcomes. It shows how bad a bad year can get. | CVaR₅ é a média dos 5% piores resultados. Mostra quão ruim pode ficar um ano ruim. |
| 8 | P95: the good years | P95 is the value that only 5% of scenarios beat. It measures the upside of a sequence. | P95 é o valor que apenas 5% dos cenários superam. Mede o potencial de ganho de uma sequência. |
| 9 | Soil carbon | Soil carbon changes slowly, season by season. A sequence that keeps carbon up protects the land for the next cycle. | O carbono do solo muda devagar, safra a safra. Uma sequência que mantém o carbono protege a terra para o ciclo seguinte. |
| 10 | Total nitrogen is not fertilizer | Total nitrogen is the stock in the soil, not the nitrogen a crop can use right now. | Nitrogênio total é o estoque no solo, não o nitrogênio que a cultura pode usar agora. |
| 11 | Support | A sequence with few valid NPVs is a weak guide. Support grows with the number of scenarios behind it. | Uma sequência com poucos VPLs válidos é um guia fraco. O suporte cresce com o número de cenários por trás dela. |
| 12 | Compare before you confirm | A higher median can come with a worse bad-year outcome. The comparison shows what you give up. | Uma mediana maior pode vir com um pior ano ruim. A comparação mostra o que você abre mão. |
| 13 | Estimates, not guarantees | These are estimates from municipal data and model assumptions. An agronomist should check them against your field. | São estimativas com base em dados municipais e premissas do modelo. Um agrônomo deve checá-las no seu talhão. |
