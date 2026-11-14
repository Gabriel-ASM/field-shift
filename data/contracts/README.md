# Contratos de dados

Os esquemas ficam em pastas imutáveis por versão. `registry.json` registra a versão ativa e associa cada nome lógico ao arquivo JSON Schema correspondente. Os pipelines resolvem o nome lógico pelo registro; não devem montar caminhos diretos para `contracts/<arquivo>.schema.json`.

## Versão ativa

`v1/` contém todos os contratos publicados atualmente: clima diário, perfil de solo, estados e transições hídricas Markov, transições de cultura Markov, manifesto de perfil, política e observação de campo. Os `$id` dos esquemas incluem `/contracts/v1/`.

O script `data/pipeline/contract_registry.py` fornece `contract_path`, `current_contract_version` e `validate_contract`. `build_profiles.py` valida cada linha normalizada de clima, solo, estados, transições e manifesto antes de concluir a ingestão. A coluna CSV `quality_valid` e as listas JSON de flags são projetadas para a representação semântica definida em `climate-daily.schema.json`. `build_crop_transition_markov.py` valida a cadeia e o manifesto atualizado.

Os manifestos guardam `contract_version`, `contract_registry` e `contract_id` em cada conjunto validado. Os geradores mantêm conjuntos e fontes complementares, como PAM, ZARC e custos, mesmo quando não os reconstroem. Assim é possível descobrir qual contrato definiu cada artefato, além de saber qual revisão estava ativa.

`field_observation` e `strategy_policy` já têm contratos publicados, mas este MVP não ingere observações de talhão nem políticas agronômicas. A existência do schema não indica que esse dado esteja carregado.

## Publicar uma nova versão

1. Copie os esquemas atuais para `v2/`; não edite arquivos de `v1/` para alterar regras já publicadas.
2. Atualize os `$id` para `/contracts/v2/` e adicione as entradas novas em `registry.json`.
3. Mude `current_version` para `v2` e ajuste os produtores/consumidores que precisarem da nova forma.
4. Preserve o suporte de leitura de `v1` enquanto houver perfis ou integrações que apontem para ela.

Uma nova versão não deve converter uma hipótese, um proxy ou uma estimativa em observação real; mantenha proveniência e resolução no payload.
