# Dados do Field Shift

## O que está disponível

A síntese mais recente da coleta está em [`research/field_shift_cerne_dos_dados_2026-11-14.md`](../research/field_shift_cerne_dos_dados_2026-11-14.md); ela descreve 55 arquivos do computador de origem, que continuam ausentes deste checkout. O inventário abaixo lista o que está disponível aqui. Para os exemplos pedidos, foram baixados NASA POWER Daily e SoilGrids, malhas municipais IBGE, relatórios SISZARC do MAPA e série municipal PAM/SIDRA do IBGE para Ariquemes (RO), Franca (SP) e Varginha (MG). Os parâmetros de água FAO‑56 foram extraídos para as culturas listadas e mantêm as incompatibilidades/ausências da fonte.

| Diretório | Conteúdo |
|---|---|
| `raw/` | Respostas sem alteração de NASA POWER, SoilGrids, GeoJSON IBGE, exportações XLS SISZARC, consulta PAM/SIDRA, Yahoo Finance e PTAX/BCB |
| `profiles/<id>/` | Clima/solo normalizados; PAM e ZARC; estado hídrico de referência; transições de referência e por cultura/fase/decêndio; história ambiental, premissas e manifesto |
| `processed/` | Execução registrada de referência e resultados de Monte Carlo por ação agrícola quando gerados |
| `catalog/` | Inventário do PR, fontes recomendadas no desafio e perfis dos exemplos |
| `contracts/` | JSON Schemas para clima, solo, estado, transição, observação de campo e manifesto |
| `reference/` | FAO‑56 Kc/fases, hipótese de rotação/solo, preços futuros congelados, cobertura de dados, contratos e desenhos de pesquisa |

Cada perfil tem 16.746 dias NASA POWER de 1981-01-01 a 2026-11-06. O Monte Carlo usa os 45 anos completos, 1981–2025. O ponto meteorológico e a célula SoilGrids são os centroides de área calculados a partir da malha municipal IBGE. São pontos regionais para demonstração, não localização de fazenda, talhão ou média municipal.

| Perfil | Município | Precipitação POWER média anual¹ | ETo média anual¹ | CAD derivada até 1 m |
|---|---|---:|---:|---:|
| `ariquemes-ro` | Ariquemes · RO | 1.848,9 mm | 1.399,6 mm | 121,3 mm |
| `franca-sp` | Franca · SP | 1.455,5 mm | 1.635,1 mm | 108,3 mm |
| `varginha-mg` | Varginha · MG | 1.341,5 mm | 1.463,0 mm | 123,8 mm |

¹ Média dos anos completos de 1981 a 2025, no ponto do perfil. Estatísticas descritivas de estimativas remotas, não médias de estações ou observações agrícolas.

O [catálogo de recursos do desafio](catalog/fontes-desafio-nasa.json) distingue produtos NASA baixados e pendentes; [model-data-flow.json](reference/model-data-flow.json) mostra o caminho das fontes até Markov e Monte Carlo. Para o MVP, NASA POWER é o recurso NASA efetivamente ingerido. SoilGrids é um prior de solo, ZARC/PAM são fontes públicas brasileiras de agricultura e IBGE é usado somente para gerar coordenadas representativas. Não há seleção de talhão por mapa.

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

### Cultura, ZARC e PAM

`raw/mapa-siszarc/` preserva os XLS oficiais consultados no SISZARC para cada cultura/UF; `profiles/<id>/zarc-planting-windows.json` mantém somente as linhas do município de exemplo, ainda desdobradas por safra, cultura oficial, grupo, código oficial de solo e todos os 36 decêndios de risco. Os códigos podem variar por norma e não são cruzados com a AWC de SoilGrids. A interface lista as culturas anuais locais com janela ZARC de risco de 20% e permite escolher a próxima safra.

`raw/ibge/pam-municipal-5457-1988-2025.json` preserva os dados SIDRA da tabela PAM 5457. Cada perfil separa produto×ano e inclui produtividade (kg/ha), área, quantidade e valor nominal. O resumo tem mediana correta, faixa observada, anos válidos e a razão nominal valor da produção/área para 2021–2025. PAM é agregado municipal e não vira resposta causal de produtividade, preço atual ou série em reais constantes.

`raw/yahoo-finance/` guarda as respostas históricas de fechamento para soja CBOT `ZSK27.CBT` e milho CBOT `ZCK27.CBT` em 13/11/2026; `raw/bacen/` preserva a PTAX de venda da mesma data. `reference/yahoo-harvest-futures.json` normaliza os preços por tonelada, com moeda, unidade, vencimento e conversão. Recrie o snapshot com `python -m field_shift.freeze_harvest_prices --date 2026-11-13`. As cotações ficam congeladas na data da simulação e não são chamadas durante a página.

A página usa o preço futuro de maio/2027 como referência internacional e multiplica pelo rendimento médio municipal da PAM/IBGE em 2021–2025 para calcular um valor bruto indicativo por hectare. Essa conta não considera base local, qualidade, frete, custos, impostos nem produtividade do talhão. Yahoo não tem contrato comparável para amendoim e sorgo nesta demonstração; nesses casos o valor/ha não é calculado. Os custos Conab e outras fontes R091/R092/R097 continuam fora do fluxo; PTAX (R094) entra somente na conversão pontual.

`reference/crop-water-parameters.json` registra Kc e duração de fases da FAO‑56, com a referência e a adequação de cada curva. `pipeline/build_crop_markov.py` gera `profiles/<id>/crop-markov-scenarios.json` para culturas que tenham janela ZARC local e ciclo anual FAO‑56 internamente consistente. Essa matriz de processo usada pelo CLI continua com unidade água×fase e ação cultura×decêndio; ela não mede o efeito de rotação ou manejo.

`reference/rotation-soil-prior.json` alimenta a cadeia mostrada na página: estado `(última cultura, classe demonstrativa de carbono orgânico 0–30 cm)`, ação `próxima cultura elegível no ZARC` e destino `(nova cultura, nova classe de carbono)`. O carbono inicial é média ponderada das camadas SoilGrids 0–30 cm. Os limites de 12/20 g/kg e as probabilidades de transição estão explicitamente marcados como hipótese sem calibração. A referência Embrapa dá contexto direcional sobre cobertura vegetal, palhada e diversificação; não é fonte dos percentuais configurados. O modelo da página não usa a água como estado ou resultado central.

O contrato ponta a ponta está em `reference/model-data-flow.json`; `field_shift.data.load_crop_scenario()` carrega a matriz condicionada à cultura e ao decêndio para o mesmo motor Markov/Monte Carlo.

O motor adiciona Dirichlet `α=0,5` por destino viável a cada linha de contagem. Essa pseudocontagem representa incerteza da matriz, não dados. Como as linhas são derivadas do mesmo balanço, o modelo não tem evidência de efeito de ação agrícola. O esquema `contracts/field-observation.schema.json` permanece separado para dados pareados reais de manejo quando existirem.

## Simulação Monte Carlo

`python -m field_shift.demo` roda uma execução registrada por perfil com 10.000 trajetórias, 120 quinzenas (cinco anos), semente 2026 e blocos de duas quinzenas. Cada trajetória sorteia blocos de clima de anos históricos completos, uma realização das linhas Dirichlet e o estado hídrico seguinte por passo. As métricas em `processed/demo-simulation-results.json` mostram frequência de quinzenas em água baixa, duração de sequências baixas e a distribuição do estado final. Esse motor continua disponível como trilha de balanço hídrico.

Na página, o Monte Carlo compara 10.000 trajetórias pareadas de cinco safras entre uma cultura repetida e a rotação local, propagando as probabilidades de solo explicitamente hipotéticas. A saída mostra a distribuição final de classes de carbono; não simula clima, resposta de produtividade, custos ou lucro. O valor bruto indicativo usa somente rendimento municipal observado na PAM e uma cotação de bolsa congelada. O relatório cita arquivos processados do PR, mas eles não são entradas ocultas.

## Reconstruir e abrir

```powershell
python data/pipeline/build_profiles.py
python data/pipeline/prepare_crop_data.py
python data/pipeline/build_crop_markov.py
python -m field_shift.demo
python -m field_shift.crop_demo --profile data/profiles/franca-sp --crop peanut --planting-decendio 1 --risk 20
python -m field_shift --profile data/profiles/ariquemes-ro --policy data/policies/balanco-hidrico-referencia.json --initial-state water_medium
python -m field_shift.visualize --output docs/visualizacao.html --seed 2026
```

Os pipelines de transformação leem `raw/`; não baixam dados por conta própria. `fetch_pam.py` e `fetch_zarc_examples.py` fazem as consultas públicas usadas nesta entrega. A página gerada empacota ZARC, PAM, Kc, modelos e história ambiental para abrir localmente sem API externa. A origem, o período, as unidades, a resolução, o hash e a qualidade de cada conjunto estão no manifesto de cada perfil.
