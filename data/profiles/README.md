# Perfis de simulação

## Exemplo disponível

- `ariquemes-ro/`
- `franca-sp/`
- `varginha-mg/`

Cada perfil tem `manifest.json`, `climate-daily.csv`, `climate-summary.json`, `soil-profile.json`, `states.json`, `transitions.json`, `environment.json`, `markov-derivation.json` e `assumptions.json`. Os hashes no manifesto ligam cada arquivo normalizado às fontes brutas em `data/raw/`.

Os pontos são centroides municipais e não observações de talhão. As transições descrevem apenas o estado de água de um balanço de referência baseado em clima e CAD mapeada. Não há cultura ou manejo nas contagens. Veja [`data/README.md`](../README.md) para método, incerteza e interpretação.

## Adicionar perfil

Use `data/pipeline/build_profiles.py` como referência de normalização, mas mantenha os arquivos originais, os metadados de origem, data, período, unidade e qualidade. Não copie estimativas entre municípios. Para modelar ação agrícola, acrescente observações longitudinais da mesma unidade de manejo no contrato `data/contracts/field-observation.schema.json`; as transições precisam ficar separadas de estados derivados por clima.
