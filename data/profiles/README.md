# Perfis de simulação

## Exemplo disponível

- `ariquemes-ro/`
- `franca-sp/`
- `varginha-mg/`

Cada perfil tem `manifest.json`, clima/solo, `pam-history.json`, `zarc-planting-windows.json` e cadeias Markov distintas: transição marginal ponderada pelo top 5 da área PAM (`crop-transition-markov.json`), água de referência Kc=1 (`states.json`/`transitions.json`) e água×fase×decêndio (`crop-markov-scenarios.json`), cujas curvas Kc estão em `../reference/crop-water-parameters.json`. `environment.json` guarda blocos sazonais; `markov-derivation.json` e `assumptions.json` documentam premissas e limites. Os hashes no manifesto ligam arquivos normalizados às fontes em `data/raw/` e `data/reference/`.

Os pontos são centroides municipais e não observações de talhão. As matrizes hídricas são derivadas de balanço, não observações de água/manejo. A cadeia de culturas usa as participações de área top-5 no município e o produto de marginais consecutivas para formar massa esperada; isso supõe independência e não conta transições do mesmo campo. Produtos fora do catálogo não participam do top 5. A prior habilita destinos sem massa PAM, e as faixas de carbono são hipóteses explícitas não calibradas. ZARC dá referência de janela; para coberturas listadas sem linha MAPA standalone, a cadeia interativa usa a hipótese de qualquer decêndio declarada em `data/reference/crop-cycle-assumptions.json`; linha oficial sempre prevalece. PAM não calibra resposta do talhão. Veja [`data/README.md`](../README.md) para método, incerteza e interpretação.

## Adicionar perfil

Use `data/pipeline/build_profiles.py` como referência de normalização, mas mantenha os arquivos originais, os metadados de origem, data, período, unidade e qualidade. Não copie estimativas entre municípios. O manifesto registra a versão do conjunto de contratos e cada `contract_id`; os pipelines resolvem esquemas pelo `data/contracts/registry.json` e validam antes de publicar os derivados. Para modelar ação agrícola, acrescente observações longitudinais da mesma unidade de manejo pelo contrato lógico `field_observation`; mantenha essas transições separadas de estados derivados por clima.
