# Políticas de manejo

Não há políticas carregadas neste checkout. Cada política deve ser um JSON conforme o contrato lógico `strategy_policy` do registro `../contracts/registry.json` (atualmente `../contracts/v1/strategy-policy.schema.json`), com ação por estado, períodos elegíveis e proveniência legível. Vincule as janelas ao ZARC da safra e às restrições agronômicas da cultura/localidade.

O CLI roda a distribuição de estados para a política informada. Sem um modelo econômico explícito, não calcula VPL nem recomenda uma rotação.
