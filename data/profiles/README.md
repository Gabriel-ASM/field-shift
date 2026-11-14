# Perfis de simulação

## Exemplo disponível

- `ariquemes-ro/`
- `franca-sp/`
- `varginha-mg/`

Cada perfil tem `manifest.json`, clima/solo, `pam-history.json`, `zarc-planting-windows.json` e duas matrizes Markov: referência Kc=1 (`states.json`/`transitions.json`) e cultura×fase×decêndio (`crop-markov-scenarios.json`), cujas curvas Kc estão em `../reference/crop-water-parameters.json`. `environment.json` guarda blocos sazonais; `markov-derivation.json` e `assumptions.json` documentam premissas e limites. Os hashes no manifesto ligam arquivos normalizados às fontes em `data/raw/` e `data/reference/`.

Os pontos são centroides municipais e não observações de talhão. A matriz base descreve demanda de referência; as matrizes por cultura aplicam Kc de literatura durante o ciclo e demanda Kc=1 fora dele. As duas são derivadas de balanço hídrico, não observações de água/manejo. ZARC é filtro de elegibilidade; PAM dá contexto municipal e não calibra resposta do talhão. Veja [`data/README.md`](../README.md) para método, incerteza e interpretação.

## Adicionar perfil

Use `data/pipeline/build_profiles.py` como referência de normalização, mas mantenha os arquivos originais, os metadados de origem, data, período, unidade e qualidade. Não copie estimativas entre municípios. Para modelar ação agrícola, acrescente observações longitudinais da mesma unidade de manejo no contrato `data/contracts/field-observation.schema.json`; as transições precisam ficar separadas de estados derivados por clima.
