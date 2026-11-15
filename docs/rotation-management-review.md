# Repetição, suporte e qualidade agronômica

## Política atual — cultura intermediária, com retorno permitido

A proibição de coexistência durante cinco anos foi removida. A configuração atual é `sequence_constraints.break_required_between_crop_groups`, com milho e soja no mesmo grupo. A troca direta milho → soja ou soja → milho exige completar antes um ciclo de outra cultura. Milho → sorgo → soja e soja → braquiária → soja são permitidos. Pousio não equivale a uma cultura intermediária. O limite de repetição no teto permanece ativo.

Cana permanece concorrendo normalmente, por decisão expressa do usuário. As novas regras não garantem a vitória de sorgo, nem certificam adequação agronômica. Sorgo, milho, milheto e braquiária são gramíneas; diversificar espécies não resolve necessariamente problemas compartilhados por família.

## Correção da base econômica

A ingestão aceitava qualquer registro municipal, mesmo antigo e sem rendimento recente. Isso impedia recorrer a dados estaduais. Sorgo e milheto ficavam fora do ranking em Franca e Varginha. Varginha chegava a mostrar preço nominal de 1993 como se fosse referência real recente.

Agora, cada recorte precisa ter rendimento positivo em 2021–2025 e preço positivo deflacionável em 2017–2025. A busca segue município → UF → macrorregião → Brasil, mantendo rendimento e preço no mesmo recorte. Sem recorte válido, os valores ficam ausentes, sem aproveitar preço nominal antigo. Proxies ficam identificados no contrato e na interface. Sorgo e milheto passaram a ser elegíveis nos três perfis.

## Verificação da política atual

Com 10.000 trajetórias, Ariquemes, milho inicial e semente 2026, houve sorgo em 3.072 trajetórias, milheto em 3.237 e braquiária em 3.697. A melhor sequência continuou milho ×3 → cana, com 229 VPLs e mediana de R$ 5.855/ha. Isso mostra exploração das alternativas, não sua superioridade financeira. Os critérios continuam 68% econômico, 17% ambiente e 15% suporte, com P95/CVaR5 igualmente ponderados dentro da parcela econômica.

Em Ariquemes, sorgo tem receita-base aproximada de R$ 2.383/ha e custo R$ 2.456/ha antes de ambiente, tendência e desconto. Braquiária tem receita zero e o mesmo custo como proxy. Custos de cobertura precisam de orçamento específico de implantação/manejo, sem assumir custo de colheita de grãos. Milheto também combina ciclo curto de cobertura com rendimento/preço proxy de sorgo, limitação que requer separar usos comerciais e de cobertura em uma evolução do contrato. Não alteramos esses números arbitrariamente para produzir o vencedor desejado.

O suporte pela frequência de uma sequência completa também pode favorecer sequências curtas perenes, enquanto alternativas anuais se dividem em muitos caminhos. O próximo passo mais consistente para comparar resiliência seria reavaliar as melhores sequências sob um mesmo conjunto de cenários climáticos, em vez de interpretar frequência de descoberta como qualidade agronômica. Isso é proposta futura, não parte desta correção.

Para reproduzir o diagnóstico atual: `node tests/audit_rotation_support.cjs --current --samples=10000`. Os testes do front verificam bloqueio direto, retorno após intermediária, preservação dos candidatos e viabilidade econômica do sorgo/milheto. Testes de ingestão cobrem série antiga, fallback estadual e ausência total de preço real válido.

Referência sobre alternativas comerciais e coberturas: [Embrapa — rotação de culturas](https://www.embrapa.br/web/agencia-de-informacao-tecnologica/cultivos/soja/producao/manejo-do-solo/rotacao-de-culturas).

## Histórico — comparação anterior às correções de dados e de retorno

Os resultados abaixo descrevem a etapa anterior. A auditoria sem `--current` desativa a regra de intermediária, mas usa a base econômica atual; portanto não congela os antigos resultados de ranking.

## Diagnóstico

O resumo de Ariquemes informa 354 VPLs em 100.000 trajetórias. Não contém a sequência, semente, valores financeiros ou eventuais parâmetros editados. Portanto, não permite reproduzir exatamente a execução. O suporte satura em 100 VPLs, de modo que 354 recebem 10/10. Isso não é probabilidade de sucesso nem evidência de adequação agronômica. Trocar esse teto para 60 não altera a nota dessa sequência.

A auditoria com padrões do repositório e semente 2026 reproduziu essa contagem: dez plantios de milho, 354 VPLs, mediana R$ 20.338/ha, CVaR5 R$ 17.576/ha, P95 R$ 22.102/ha e nota 9,40069. É uma reprodução compatível com o relato, sem acesso ao estado original do navegador. A sequência não dava prejuízo financeiro; a limitação era permitir repetir indefinidamente com perda de rendimento constante após o teto.

Com o bloqueio ativo, nas mesmas 100.000 trajetórias/mesma semente, a recomendação passa a milho ×3 → soja ×3 → milho ×2, com 80 VPLs, mediana R$ 11.674/ha, CVaR5 R$ 9.077/ha, P95 R$ 13.312/ha e nota 9,09635. Nenhuma trajetória violou o bloqueio. Os sorteios divergem após alterar destinos, portanto não é comparação pareada de clima. As notas normalizam por uma referência recalculada em cada execução e não são diretamente comparáveis entre execuções. O bloqueio reduz o retorno recomendado neste cenário; não prova superioridade econômica da diversificação. A recomendação continua sendo alternância simples, sem certificação agronômica.

Com preferência ambiental de 20%, os pesos finais são 68% econômico, 17% ambiental e 15% suporte. O econômico combina P95 e CVaR5 conforme outro controle. Solo e água são estados finais; a nota não mede diversidade, patógenos ou cobertura contínua. A penalidade do milho é 2,2 pontos percentuais por repetição, limitada a 4,3%; após a terceira safra, mais repetições não aumentavam a perda. O teto limita perda de rendimento, não prejuízo financeiro.

## Mudança aplicada

`repeated_crop_effect.block_replant_after_penalty_cap` habilita uma restrição de manejo antes do sorteio do próximo plantio. Após uma colheita no teto de perda, retira a mesma cultura dos destinos e renormaliza as probabilidades restantes. Mantém os calendários e a maturação. Sem alternativa, permanece em pousio. A restrição não altera conjuntos de destinos em cache nem os cortes de culturas perenes.

Com os padrões atuais, milho pode ser colhido três vezes consecutivas e soja quatro; o plantio seguinte precisa mudar. A regra usa os coeficientes configurados, não limites escondidos. Desativá-la restaura o comportamento anterior. Um teto zero desativa esse bloqueio para a cultura. É uma hipótese explícita de manejo solicitada para o projeto, não um limite universal publicado pela Embrapa.

## Próximo passo para sucessão soja/milho

A Embrapa distingue sucessão anual repetida soja/milho safrinha de rotação diversificada. Uma lista isolada milho → soja → milho não identifica a estação nem demonstra, por si, manejo inadequado.

Proposta de evolução, ainda não implementada:

1. Classificar pelos eventos de plantio e datas já existentes: repetição da mesma cultura, alternância simples, sucessão anual recorrente e sequência diversificada. Não chamar a última de rotação agronomicamente certificada.
2. Usar anos agrícolas e janelas locais para comparar a cultura da mesma estação entre anos. Não confundir troca dentro do ano com diversidade ao longo dos anos.
3. Acrescentar famílias botânicas e funções (comercial/cobertura) ao contrato. Contar espécies sozinho é insuficiente; culturas diferentes podem compartilhar patógenos.
4. Calibrar intervalo de retorno por cultura/problema agronômico e região somente quando houver base. Não bloquear todo padrão A–B–A nem inventar uma bonificação financeira para uma terceira espécie.
5. Separar elegibilidade agronômica do ranking econômico. Se nenhuma sequência satisfizer a política escolhida, informar ausência de recomendação; não relaxar silenciosamente as regras.

Limitação atual: trocar a cultura reinicia a penalidade consecutiva. O modelo não guarda memória de patógenos ou esgotamento por família. O bloqueio implementado resolve a repetição indefinida no teto, mas não essa limitação. Pousio não reinicia a contagem.

## Validação reproduzível

`node tests/test_front.cjs` verifica limites, preservação de caches, ausência de destinos, cálculos de penalidade e ciclo da cana. `node tests/audit_rotation_support.cjs` compara 100 mil trajetórias de Ariquemes, milho inicial, semente 2026, preferência ambiental 20% e econômico dividido igualmente entre P95 e CVaR5, com e sem bloqueio. Usa o simulador incorporado no HTML gerado.

## Referências

- [Embrapa — organização do sistema produtivo e sucessão soja/milho](https://www.embrapa.br/web/agencia-de-informacao-tecnologica/tematicas/sistema-plantio-direto/fazendo-certo/planejando-e-executando/fase-de-implantacao/organizando-o-sistema-produtivo/rotacao-de-culturas)
- [Embrapa — conceitos e benefícios da rotação](https://www.embrapa.br/en/web/agencia-de-informacao-tecnologica/cultivos/soja/producao/rotacao-de-culturas/conceitos-e-beneficios-da-rotacao-de-cultura)

Essas fontes fundamentam diversificação e planejamento temporal; não fundamentam os limites numéricos de três ou quatro safras adotados pela hipótese do projeto.
