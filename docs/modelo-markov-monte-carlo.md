# Modelo Markov + Monte Carlo

## Modelo mostrado na visualização

Em [`visualizacao.html`](visualizacao.html), a cultura conduz a ação e o carbono orgânico conduz o estado que a cadeia acompanha. A página não usa água como resultado principal.

| Parte | Definição na demonstração |
|---|---|
| Estado | Cultura anterior + faixa demonstrativa de carbono orgânico do solo em 0–30 cm |
| Ação | Próxima cultura anual com janela ZARC municipal de risco de 20% |
| Destino | Cultura escolhida + faixa de carbono orgânico depois da safra |
| Passo | Uma safra |
| Horizonte Monte Carlo | Cinco safras, 10.000 trajetórias pareadas por política |

O carbono inicial é a média ponderada das camadas SoilGrids de 0–5, 5–15 e 15–30 cm. As faixas `<12`, `12–20` e `>20 g/kg` existem apenas para tornar a cadeia visível; não são limites de diagnóstico de fertilidade. O ponto SoilGrids representa uma célula mapeada próxima ao centroide municipal, não uma amostra de talhão.

## Probabilidades de transição do solo

Não há medições pareadas de solo e rotação nestes municípios. Por isso, `data/reference/rotation-soil-prior.json` registra uma hipótese de demonstração sem calibração:

| Relação entre grupos | Piora uma faixa | Estável | Melhora uma faixa |
|---|---:|---:|---:|
| Repete o grupo botânico | 25% | 60% | 15% |
| Alterna gramínea e leguminosa | 10% | 55% | 35% |

Soja e amendoim contam como leguminosas; milho, sorgo e o consórcio de milho com braquiária contam como gramíneas. A transição fica no limite quando o solo já está na faixa baixa ou alta. Para sustentar apenas a direção da hipótese, o arquivo cita uma referência da Embrapa sobre resíduos, cobertura e rotação; os percentuais não vêm dessa publicação. Os números são premissas arbitrárias, devem aparecer como hipótese em toda saída e precisam ser substituídos por observações de campo antes de orientar manejo.

Em cada passo, a página desenha as probabilidades da linha `(estado atual, cultura seguinte)` e sorteia uma faixa de solo ao avançar. A história exibe a sequência de culturas e as faixas sorteadas.

## Monte Carlo

Para cada localidade, a simulação compara duas políticas começando da mesma cultura e faixa de solo:

1. **Cultura fixa:** repete a cultura escolhida para a próxima safra por cinco passos.
2. **Rotação local:** alterna grupos botânicos quando existe opção ZARC; se não existir outro grupo, alterna culturas distintas disponíveis.

As 10.000 trajetórias compartilham os mesmos uniformes sorteados entre as políticas. O gráfico mostra a fração final nas faixas baixa, intermediária e alta e a probabilidade de terminar na faixa baixa. A incerteza mostrada é somente a aleatoriedade da cadeia sob os percentuais fixos. O Monte Carlo não sorteia os próprios percentuais, clima, rendimento, preço ou custo; ele não valida a hipótese.

As culturas elegíveis vêm das linhas ZARC de cada município. Em Franca, soja e amendoim pertencem ao mesmo grupo funcional; dentro desta hipótese a troca entre elas não recebe o efeito de alternância entre gramínea e leguminosa.

## Preço congelado e referência de safra

[`data/reference/yahoo-harvest-futures.json`](../data/reference/yahoo-harvest-futures.json) congela os fechamentos Yahoo de 13/11/2026 para os contratos CBOT de maio/2027. Os valores normalizados são:

| Cultura | Contrato | Fechamento Yahoo | Referência convertida |
|---|---|---:|---:|
| Soja | `ZSK27.CBT` | 1.245,5 US¢/bu | R$ 2.586,51/t |
| Milho | `ZCK27.CBT` | 464,5 US¢/bu | R$ 1.033,52/t |

A conversão usa os pesos de bushel de 60 lb para soja e 56 lb para milho e a cotação de venda PTAX de R$ 5,6518/US$ em 13/11/2026. O valor bruto indicativo por hectare na página multiplica o preço convertido pelo rendimento médio municipal PAM/IBGE de 2021–2025. Ele não é preço de balcão nem receita prevista: exclui base local, qualidade, frete, custo, imposto, hedge e mudança de rendimento. A cotação é uma referência para a safra de 2027 e não é estendida como curva de preços de cinco anos. Amendoim e sorgo não têm contrato Yahoo comparável neste pacote.

O gerador salva as respostas originais em `data/raw/yahoo-finance/` e `data/raw/bacen/`. Para repetir a captura histórica, use `python -m field_shift.freeze_harvest_prices --date 2026-11-13`. A página gerada não faz chamadas externas.

## Outras matrizes mantidas no repositório

O pipeline `data/pipeline/build_crop_markov.py` continua a gerar matrizes água×fase de demanda hídrica por cultura, usando NASA POWER, SoilGrids, FAO-56 e janelas ZARC. `field_shift.crop_demo` e o CLI usam essa trilha derivada de balanço hídrico. Ela não representa transições observadas de cultura ou resposta de solo; a visualização foi reorientada para demonstrar a cadeia cultura×solo explicitamente hipotética.

O resumo mais recente de coleta está em [`research/field_shift_cerne_dos_dados_2026-11-14.md`](../research/field_shift_cerne_dos_dados_2026-11-14.md). O relatório lista arquivos da máquina de origem; nem todos estão neste checkout. O inventário efetivamente ingerido está descrito em [`data/README.md`](../data/README.md).
