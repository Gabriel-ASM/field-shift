# Dados do Field Shift

## O que está disponível

O relatório de pesquisa descreve 22 conjuntos e 55 arquivos processados do Oeste do Paraná. Os 55 arquivos brutos originais continuam ausentes deste checkout. Para preencher a falta de dados nos exemplos pedidos, foram baixados diretamente dados de Ariquemes (RO), Franca (SP) e Varginha (MG): NASA POWER Daily, ISRIC SoilGrids e malhas municipais do IBGE.

| Diretório | Conteúdo |
|---|---|
| `raw/` | Respostas sem alteração das APIs NASA POWER e SoilGrids e GeoJSON municipal do IBGE |
| `profiles/<id>/` | Clima diário normalizado, perfil do solo por camada, estados, contagens Markov, história ambiental, premissas e manifesto |
| `processed/` | Saída registrada da simulação Python de cinco anos |
| `catalog/` | Inventário do PR, fontes recomendadas no desafio e perfis dos exemplos |
| `contracts/` | JSON Schemas para clima, solo, estado, transição, observação de campo e manifesto |
| `reference/` | Dados extraídos do relatório e da planilha arquitetural |

Cada perfil tem 16.746 dias NASA POWER de 1981-01-01 a 2026-11-06. O Monte Carlo usa os 45 anos completos, 1981–2025. O ponto meteorológico e a célula SoilGrids são os centroides de área calculados a partir da malha municipal IBGE. São pontos regionais para demonstração, não localização de fazenda, talhão ou média municipal.

| Perfil | Município | Precipitação POWER média anual¹ | ETo média anual¹ | CAD derivada até 1 m |
|---|---|---:|---:|---:|
| `ariquemes-ro` | Ariquemes · RO | 1.848,9 mm | 1.399,6 mm | 121,3 mm |
| `franca-sp` | Franca · SP | 1.455,5 mm | 1.635,1 mm | 108,3 mm |
| `varginha-mg` | Varginha · MG | 1.341,5 mm | 1.463,0 mm | 123,8 mm |

¹ Média dos anos completos de 1981 a 2025, no ponto do perfil. Estatísticas descritivas de estimativas remotas, não médias de estações ou observações agrícolas.

O [catálogo de recursos do desafio](catalog/fontes-desafio-nasa.json) registra a lista NASA Space Apps e distingue os produtos baixados dos que ainda não foram ingeridos. O desafio recomenda combinar observações da Terra com informação local; esta demonstração usa NASA POWER para meteorologia, SoilGrids como prior de solo e IBGE somente para gerar coordenadas representativas. Não usa seleção de talhão por mapa.

`reference/desenho-markov-monte-carlo.json` preserva as 42 variáveis, 42 ligações da matriz de impacto e 12 famílias de distribuição extraídas da planilha. São uma referência de arquitetura, não parâmetros calibrados nem efeitos causais. A extração pode ser refeita com `python research/extrair_referencia_monte_carlo.py` (requer `openpyxl`).

## Ingestão de clima

Os JSON originais do NASA POWER estão em `raw/nasa_power/`. Cada perfil em `profiles/` tem uma linha diária por data, com a origem, as unidades, o padrão temporal e as flags de qualidade. O contrato é `contracts/climate-daily.schema.json`.

Parâmetros usados: `PRECTOTCORR` (mm/dia), `T2M_MAX` e `T2M_MIN` (°C), `ALLSKY_SFC_SW_DWN` (MJ/m²/dia), `RH2M` (%) e `WS2M` (m/s). O POWER retorna `time_standard=LST`: as datas são em hora solar local, não devem ser rotuladas como dia civil ou convertidas silenciosamente para UTC−3.

ET₀ foi calculada no pipeline `pipeline/build_profiles.py`:

- A partir de 1984, Penman–Monteith FAO-56 com radiação, temperatura máxima/mínima, vento a 2 m e umidade relativa média diária. A umidade relativa diária é uma aproximação para a pressão de vapor real.
- Nos 1.095 dias de 1981–1983 sem radiação no POWER, Hargreaves–Samani usa temperatura máxima/mínima e radiação extraterrestre. As flags separam esse método alternativo.

O POWER `PRECTOTCORR` é a chuva disponível nos perfis atuais. A pesquisa do Oeste do Paraná encontrou POWER 14–18% abaixo do IMERG naquela região. Isso não foi corrigido nem transferido aos três estados. O IMERG V07 continua sendo a fonte prioritária de chuva a integrar; o material bruto citado pelo relatório e as séries de GPM não vieram neste checkout. Assim, o resultado hídrico atual deve ser tratado como demonstração com essa limitação de precipitação, não como estimativa agronômica validada.

## Ingestão de solo

As respostas originais SoilGrids v2.0 estão em `raw/soilgrids/`. `soil-profile.json` guarda as camadas de 0–5, 5–15, 15–30, 30–60 e 60–100 cm e o perfil estático de 0–100 cm. O contrato `contracts/soil-profile.schema.json` mantém cada intervalo e unidade separados.

O endpoint retorna valores codificados junto com `d_factor` e unidades de destino. O pipeline divide pelo fator indicado: por exemplo, 281 → 28,1% de argila e 44 → pH 4,4. O carbono orgânico é convertido de dg/kg para g/kg. A água disponível em cada camada é derivada das equações de capacidade de campo (33 kPa) e ponto de murcha (1.500 kPa) de Saxton & Rawls (2006), com areia/argila como frações 0–1 e matéria orgânica aproximada como SOC × 1,724. A soma ponderada das camadas compõe a CAD em mm até 1 m.

Isso é uma estimativa de mapa e uma função de pedotransferência, não amostra de solo. Cada perfil marca `scope=grid_cell`, `quality.status=mapped_estimate`, `available_water_fraction=null` e guarda a CAD por camada. Não atribuímos ordem SiBCS nem diagnóstico de fertilidade sem uma fonte correspondente.

## Balanço hídrico e estados Markov

`pipeline/build_profiles.py` gera o balanço diário de referência por ponto, limita o armazenamento à CAD e agrega o estado no início/fim de cada quinzena. Para esta demonstração, a chuva efetiva é o total POWER, a demanda é ET₀ (Kc=1) e a água armazenada obedece a `0 ≤ SW ≤ CAD`. Chuva acima da CAD é descartada como excedente sem coeficiente de escoamento calibrado; não há modelo explícito de infiltração, drenagem profunda ou ascensão capilar. O estado inicial do spin-up é 50% da CAD, declarado como premissa, e 1981–1982 são descartados das contagens Markov.

As classes de água seguem o plano MVP: baixa se `SW/CAD ≤ 1/3`, média se `1/3 < SW/CAD ≤ 2/3`, alta se `SW/CAD > 2/3`. A classe ambiental da quinzena é seca, normal ou úmida segundo a chuva zero e os percentis 20/80 locais daquela quinzena do calendário. Isso preserva a sazonalidade dos três locais sem misturar chuva de fontes diferentes.

Os arquivos de modelo são:

- `states.json`: três estados do balanço de água; o campo de solo fica como `mapeado_sem_classificacao` porque não foi feita classificação agronômica.
- `transitions.json`: contagens `estado atual × ação de referência × classe ambiental → próximo estado de água`. `support=derived` significa transição calculada por balanço físico com dados climáticos e solo mapeado; não é transição observada de talhão, cultura ou manejo. Se houver menos de 30 transições diretas, `support=pooled` agrupa ambientes para o mesmo estado e registra `sample_size`, `effective_sample_size` e a regra.
- `environment.json`: 24 classes quinzenais por ano completo, 1981–2025. O amostrador reusa blocos de duas quinzenas no mesmo período do ano.
- `markov-derivation.json`: balanço quinzenal e trilha dos estados, chuva e fração armazenada para auditoria.
- `assumptions.json`: classe, inicialização, prior, regra de pooling e limitações.

O motor adiciona Dirichlet `α=0,5` por destino viável a cada linha de contagem. Essa pseudocontagem representa incerteza da matriz, não dados. Como as linhas são derivadas do mesmo balanço, o modelo não tem evidência de efeito de ação agrícola. O esquema `contracts/field-observation.schema.json` permanece separado para dados pareados reais de manejo quando existirem.

## Simulação Monte Carlo

`python -m field_shift.demo` roda uma execução registrada por perfil com 10.000 trajetórias, 120 quinzenas (cinco anos), semente 2026 e blocos de duas quinzenas. Cada trajetória sorteia blocos de clima de anos históricos completos, uma realização das linhas Dirichlet e o estado hídrico seguinte por passo. As métricas em `processed/demo-simulation-results.json` mostram frequência de quinzenas em água baixa, duração de sequências baixas e a distribuição do estado final.

Essa saída quantifica somente o balanço de referência. Ela não é probabilidade de quebra de safra, rendimento, VPL ou uma comparação de rotação. Não foram criadas transições sintéticas de cultura, produtividade, preços ou custos. O relatório cita os arquivos processados do PR, mas eles não são entradas ocultas desta simulação.

## Reconstruir e abrir

```powershell
python data/pipeline/build_profiles.py
python -m field_shift.demo
python -m field_shift --profile data/profiles/ariquemes-ro --policy data/policies/balanco-hidrico-referencia.json --initial-state water_medium
python -m field_shift.visualize --output docs/visualizacao.html --seed 2026
```

O pipeline de transformação lê os arquivos de `raw/`; não baixa dados por conta própria. A página gerada empacota estados, transições, história ambiental e resultados no HTML para abrir localmente sem API externa. A origem, o período, as unidades, a resolução e a qualidade de cada conjunto estão no manifesto de cada perfil.
