# Field Shift — Especificação do módulo Monte Carlo

**Objetivo:** avaliar, em um horizonte de **5 anos (60 meses)**, o VPL e o risco de diferentes políticas de manejo agrícola, integrando choques climáticos, econômicos e agronômicos às transições de uma cadeia de Markov previamente definida.

## 1. Escala temporal e volume de simulações

- **Horizonte:** 60 meses = **120 passos quinzenais** por trajetória. A cada passo, atualizar os parâmetros pertinentes; **não** sortear obrigatoriamente todas as variáveis de forma independente.
- **Execução inicial:** **10.000 trajetórias** por hipótese/política; testar estabilidade dos resultados com 20.000–30.000 se necessário. Cada hipótese terá, inicialmente, **1,2 milhão de passos simulados** (10.000 × 120).
- **Unidade de decisão:** decisões de plantio, colheita, reforma ou renovação ocorrem **nas janelas agronômicas viáveis**, não necessariamente a cada quinzena. O estado e os riscos podem ser atualizados quinzenalmente.
- **Comparabilidade:** executar todas as políticas com os **mesmos cenários exógenos sorteados** (chuva e preços, por exemplo) para reduzir ruído nas comparações.
- **Frequências distintas:** clima e balanço hídrico podem evoluir quinzenalmente; preços e custos podem ser atualizados mensalmente; produtividade efetiva e receitas de venda são apuradas na colheita.

## 2. Quatro grupos de incerteza

| Grupo | Variáveis simuladas | Dinâmica recomendada | Efeito no modelo |
|---|---|---|---|
| **1. Clima** | Precipitação, temperatura, evapotranspiração, veranicos e eventos extremos | Séries sazonais e **temporalmente correlacionadas**; amostragem de blocos históricos ou distribuições ajustadas por local e época | Altera umidade, estresse hídrico, aptidão da cultura, produtividade e necessidade de irrigação |
| **2. Mercado** | Preços das culturas, fertilizantes, energia/diesel e outros insumos | Choques com correlação entre mercados e possível persistência; atualizar em frequência compatível com os dados | Modifica receitas, custos, margens e, portanto, o VPL |
| **3. Agronomia** | Resposta da produtividade, disponibilidade de N/P/K, matéria orgânica, pragas e doenças | Evolução condicionada à **cultura, manejo, solo e clima**; adicionar incerteza residual calibrada | Modifica produtividade, custos de recuperação e viabilidade de cultivos futuros |
| **4. Transições de Markov** | Probabilidades de mudança entre classes de solo, água, sanidade e estágio produtivo | Usar `P(Sₜ₊₁ | Sₜ, açãoₜ, climaₜ, manejoₜ)` quando disponível; amostrar um próximo estado a partir dessa distribuição | Determina o estado que condicionará as decisões seguintes |

**Distribuições:** não usar uma única curva normal para tudo. Calibrar distribuições específicas conforme a variável (por exemplo, chuva assimétrica, choques de preço correlacionados, eventos de pragas discretos), respeitando **sazonalidade, dependências e limites físicos**.

## 3. Integração Monte Carlo × Markov

Em cada passo quinzenal `t` de uma trajetória `k`:

1. **Observar** o estado atual `S(t)` e a ação de manejo vigente `a(t)`.
2. **Sortear** cenário climático e econômico, preservando correlações e sazonalidade.
3. **Atualizar** balanço de água, nutrientes, riscos fitossanitários e produtividade acumulada conforme manejo e condições simuladas.
4. **Calcular** despesas e receitas quando ocorrerem; registrar o fluxo de caixa da quinzena.
5. **Calcular/consultar** a distribuição de transição Markov condicionada ao estado, à ação e aos choques relevantes; **sortear `S(t+1)`**.
6. **Reavaliar a política** apenas quando houver uma nova janela de decisão agrícola; prosseguir até `t = 120`.

> **Evitar dupla contagem:** se a matriz de Markov já incorpora o efeito da seca na degradação do solo, não aplicar uma segunda penalidade aleatória pelo mesmo efeito. Separar claramente choques exógenos, resposta agronômica e transição de estado.

> **Papel do Monte Carlo:** testar a robustez das transições e estimar frequências simuladas; **não comprovar empiricamente** que a matriz Markov está correta. A validação exige confrontar probabilidades e trajetórias com dados observados ou literatura agronômica.

## 4. Fluxo financeiro e métricas

Para cada trajetória, calcular o VPL com fluxos quinzenais e taxa anual de desconto `r`:

`VPL(k) = -I₀ + Σ[t=1..120] FC(k,t) / (1+r)^(t/24) + VR(k)/(1+r)^5`

- `FC(k,t)`: receitas menos custos no passo `t`, incluindo plantio, insumos, operação, irrigação, colheita e mudanças de setup.
- `VR(k)`: valor residual ao fim do quinto ano, especialmente relevante para **café e cana-de-açúcar**.
- Adotar premissas financeiras coerentes: fluxos **reais com desconto real** ou **nominais com desconto nominal**.

**Resultados mínimos por hipótese:** VPL médio, mediano (P50), P5/P95, probabilidade de VPL negativo, **CVaR 5%** (média dos 5% piores VPLs), probabilidade de superar o cultivo-base e frequência de violações de restrições hídricas, agronômicas ou financeiras.

## 5. Configuração inicial e validação

| Item | Configuração sugerida para MVP |
|---|---|
| Horizonte | 5 anos / 60 meses |
| Passos por trajetória | 120 (quinzenais) |
| Simulações por hipótese | 10.000 inicialmente |
| Hipóteses de manejo | 16 (4 por cultura principal) |
| Políticas comparadas | Ciclo fixo, baseline e política adaptativa (se disponível) |
| Dados para calibração | NASA POWER/INMET para clima; Embrapa para restrições e respostas agronômicas; Conab/mercado para custos e preços |
| Sensibilidade | Repetir com sementes distintas e 20.000–30.000 trajetórias; testar seca severa e choque de preços |

**Critérios de qualidade:** (i) transições sempre produzem estados possíveis; (ii) probabilidades somam 100%; (iii) decisões respeitam calendário, cultura e infraestrutura; (iv) clima e preços têm dependências coerentes; (v) métricas convergem com o aumento das trajetórias; (vi) o modelo é comparado com séries históricas e/ou resultados agronômicos documentados.

**Entrega esperada:** para cada uma das 16 hipóteses, uma distribuição de VPLs e riscos, acompanhada das principais trajetórias de clima/solo e da comparação com o baseline. O resultado deve explicar **qual estratégia é mais rentável, quão arriscada é e em quais condições a decisão ótima muda**.
