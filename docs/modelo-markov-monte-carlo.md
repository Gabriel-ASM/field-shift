# Markov de culturas + Monte Carlo

## Estados e sequência de culturas

A demonstração trabalha com **uma cultura por talhão em cada passo anual**. O estado Markov é uma cultura individual. O catálogo tem as quatro culturas iniciais do research (soja, milho, cana e café) e as dez culturas candidatas de rotação ou cobertura do plano do MVP. A matriz expõe todos os 14 estados como possíveis destinos.

O pipeline `data/pipeline/build_crop_transition_markov.py` deriva `data/profiles/<perfil>/crop-transition-markov.json` de `pam-history.json`:

1. Soma as áreas PAM por cultura em cada município-ano. Café arábica e canephora são combinados; aveia em grão é usada como proxy de aveia-preta.
2. Seleciona uma única cultura por ano: a de maior área colhida entre os produtos do catálogo. Produtos PAM fora do catálogo, como arroz, não competem por essa posição.
3. Conta transições entre anos civis consecutivos. Anos com lacuna não formam uma aresta.
4. Mantém as contagens e os anos de cada aresta separados da prior.

| Item | Definição |
|---|---|
| Estado | Uma das 14 culturas individuais do catálogo |
| Início selecionável | Soja, milho, cana-de-açúcar ou café |
| Observação histórica | Cultura de maior área PAM entre os produtos do catálogo naquele ano |
| Aresta observada | Mudança da cultura dominante entre dois anos consecutivos |
| Evidência disponível | 38 anos e até 37 pares consecutivos por município |
| Escala | Município-ano; não o mesmo talhão |

A PAM não mostra qual cultura foi plantada no mesmo campo no ano seguinte. Por isso, as contagens são um proxy regional para a demo, e a página não as apresenta como frequências de rotação parcelar. As candidatas sem produto PAM correspondente (braquiária, milheto, nabo forrageiro, crotalária e mucuna) ficam visíveis na matriz, mas têm `n=0` e nenhuma contagem empírica.

## Probabilidade Markov condicionada pelo ambiente

Para não eliminar destinos por falta de amostras, cada linha recebe uma prior Dirichlet uniforme com `α = 0,5` em cada um dos 14 destinos:

```text
base(source → destination) = (count + 0,5) / (saídas_observadas + 14 × 0,5)
```

Essa pseudocontagem não é dado. Quando uma cultura de destino não aparece no histórico, sua probabilidade deriva da prior e deve ser lida como hipótese. A matriz deixa `count/n` observável ao lado de cada probabilidade.

Em cada trajetória, o Monte Carlo sorteia uma linha Dirichlet por estado com parâmetros `count + 0,5`. Depois de simular um ano do ambiente, repondera cada destino e normaliza a linha:

```text
Pₜ(j | i, ambiente) ∝ baseₜ(i → j)
                    × exp[βágua × alinhamento_água × (Kc_efetivoⱼ − Kc_efetivo_médio)]
                    × exp[βsolo × déficit_COS × (ΔCOSⱼ / 0,2)]
```

`Kc` vem de `data/reference/crop-water-parameters.json`; quando a referência Kc de uma cultura falta, o fator hídrico dela é neutro e isso aparece em `water_parameter_support`. Os coeficientes, limites do carbono, pseudocontagem e faixas por cultura estão em `data/reference/soil-crop-response-hypotheses.json`.

## Monte Carlo: ordem em cada ano

Cada uma das 10.000 trajetórias começa na cultura escolhida, água média (50% da CAD de referência) e carbono inicial de SoilGrids. Em cada ano:

1. Sorteia um bloco de chuva quinzenal observado da NASA POWER, com reposição, dentre os anos completos locais.
2. Percorre 24 quinzenas pela matriz de água, condicionando a água seguinte à classe de chuva seca, normal ou úmida. Em cada quinzena ajusta a classe hídrica sorteada pelo `Kc` anual efetivo da cultura atual, ETo média da quinzena e CAD do perfil.
3. Sorteia a variação anual de carbono da faixa hipotética associada à cultura que estava no talhão naquele ano.
4. Atualiza a probabilidade Markov usando a água final e o carbono atualizado.
5. Sorteia uma única próxima cultura; ela vira o estado de origem do próximo ano.

O resultado mostra distribuição da cultura após cinco anos, água e carbono finais, mudança nas probabilidades para a cultura inicial e cinco caminhos amostrados. Cada seta do caminho mostra a probabilidade usada após o ambiente daquele ano.

## Grafo da cadeia e leitura do Monte Carlo

O HTML mostra os 14 estados como nós e todas as 196 transições possíveis como setas, incluindo laços da cultura para si mesma. Selecione um nó para destacar suas 14 saídas. A espessura da seta representa P média no contexto de água e carbono selecionado; o rótulo mostra essa probabilidade com duas casas decimais. A lista lateral discrimina cada destino:

- `k/n PAM`: contagem observada na cadeia municipal e número de saídas históricas da cultura de origem.
- `P₀`: `(k + α)/(n + 14α)`, antes de reponderar ambiente.
- fatores de água e solo: multiplicadores de destino aplicados antes de normalizar a linha.
- `Dirichlet 90%`: intervalo empírico de 5º a 95º percentil calculado com 1.200 sorteios da linha posterior, mantendo o contexto ambiental fixo. Não é intervalo de confiança das rotações reais do talhão.
- `MC`: quantas trajetórias passaram pela origem e quantas escolheram aquela seta no ano exibido. As cores dos nós mostram a frequência de ocupação por ano.

Assim ficam distintos o suporte observado na PAM, a massa da prior, a probabilidade média contextualizada e as frequências realmente sorteadas. As linhas de posterior usadas pelo Monte Carlo são sorteadas novamente em cada trajetória; água e carbono também variam no tempo. Por isso, a frequência de uma seta no Monte Carlo pode diferir da P média fixa exibida no grafo.

Ao carregar a página, o Monte Carlo inicia depois da primeira pintura da interface. A barra avança a cada 200 trajetórias e o grafo recebe novas frequências a cada 1.000. Uma execução usa a mesma linha Dirichlet sorteada por estado ao longo de cada trajetória; cada nova trajetória sorteia seus próprios parâmetros. A seta mostra a transição da cultura anterior para a atual, e o brilho de cada nó mostra quantas trajetórias ocupam essa cultura no ano selecionado.

As linhas do grafo continuam completas, mas restrições de ciclo ficam explícitas. Sem idade do cafezal ou histórico de reforma, café só transita para café no horizonte; a mesma regra conservadora vale para cana enquanto faltarem idade e número de cortes. As arestas bloqueadas aparecem tracejadas em ferrugem e com probabilidade operacional zero. Braquiária manejada nas entrelinhas é exibida como opção de manejo associado ao nó Café, fora do conjunto de destinos Markov. Seu efeito não é inserido numericamente no Monte Carlo porque não há coeficiente compatível com estes perfis.

### Água

Os dados `states.json`, `transitions.json` e `environment.json` guardam os estados hídricos. A chuva e ETo da NASA POWER alimentam o balanço de referência Kc=1; a CAD é derivada do SoilGrids por Saxton–Rawls. Para cada cultura, o `Kc` anual efetivo combina as fases FAO‑56 com a demanda Kc=1 fora do ciclo. Após cada classe hídrica sorteada, o armazenamento representativo muda por `(Kc_efetivo − 1) × ETo_quinzenal / CAD` e a classe é reavaliada nos cortes publicados. Culturas sem uma curva válida usam Kc=1. Esse ajuste é um balanço resumido, não medição do talhão.

### Solo

O valor inicial é a média SoilGrids de carbono orgânico em 0–30 cm, ponderada pelas camadas de 0–5, 5–15 e 15–30 cm. A série local não tem medições de carbono pareadas com sequência de culturas; assim, a evolução anual e o efeito do carbono nas probabilidades são hipóteses editáveis, deliberadamente identificadas como não calibradas. Não são estimativas de efeito causal.

## Dados ausentes e limites

O relatório de research lista MapBiomas Coleção 11 e tabelas de transição agrícola, mas os rasters/tabelas correspondentes não estão neste checkout. A página oficial informa que o produto agrícola 1ª safra é uma série anual baseada em pixels e publica os assets pelo GEE; seu produto de 2ª safra é complementar. Sem a sequência local do mesmo pixel, a PAM municipal não pode ser convertida em rotação do talhão. Os destinos sem PAM são mantidos como possibilidades via prior explícita, nunca como contagem inventada.

A cadeia é uma demonstração regional, não recomendação agronômica, previsão de produtividade ou efeito econômico. Para calibrar rotação e carbono do talhão são necessários histórico espacial do mesmo talhão, cultura por safra, análise local de solo e validação agronômica.

## Objetivo econômico: maximizar VPL

O objetivo econômico é **maximizar o VPL esperado por hectare em cinco safras futuras** entre as sequências completas que a cadeia gerou nas 10.000 trajetórias Monte Carlo. A interface agrupa as trajetórias pela sequência de cinco transições e calcula média, mediana, P5–P95, probabilidade de VPL negativo e média dos 5% piores a partir dos ambientes simulados associados à rota. Frequência Monte Carlo e probabilidade Markov média aparecem separadamente. Só sequências com ao menos 20 ocorrências entram no quadro principal; a tabela expandida mostra também as rotas raras para transparência, com baixa precisão. O método otimiza entre rotas amostradas, não prova que encontrou a melhor entre as 14⁵ sequências possíveis, não modela política dinâmica anual e não é evidência causal.

```text
VPL = Σₜ [(rendimentoₜ × preçoₜ × fator ambientalₜ) − custo totalₜ] / (1 + r_real)ᵗ
```

As 14 linhas econômicas são editáveis. Soja/milho usam preços futuros Yahoo congelados; rendimentos e demais valores unitários comerciais vêm da PAM em escala municipal, estadual ou nacional identificada. Custos usam painéis totais CONAB diretos quando disponíveis; sem painel direto, usam a cultura proxy identificada na tabela. Feijão usa proxy de custo da soja, milheto usa sorgo como proxy de colheita/custo, aveia-preta usa aveia em grão, e nabo, braquiária, crotalária e mucuna começam com receita comercial zero e custo de cultura análoga. O usuário pode editar rendimento, preço, custo e inclusão no ranking. Essas entradas deixam o VPL calculável para cada estado, mas hipóteses/proxies não são dados observados das culturas cobertas. Custos e PAM são convertidos para reais do último mês IPCA; a taxa real aproxima a curva prefixada ANBIMA de cinco anos e o IPCA dos últimos 12 meses.

O multiplicador de rendimento combina classe hídrica e carbono do solo: água baixa/média/alta usa 0,90/1,00/1,05; carbono baixo/médio/alto usa 0,80/1,00/1,20. Essas são hipóteses de sensibilidade, não funções de produção medidas. Preços e custos ficam constantes em termos reais no ciclo. PAM municipal não é rendimento do talhão, preços PAM não são contratos futuros, contratos Yahoo não são preço à vista e custos CONAB de outra localidade não são custo observado no perfil. Café e cana são perenes: idade, implantação e reforma do talhão não entram no estado Markov anual. Portanto, o ranking é uma comparação econômica de cenário, não uma prova causal nem recomendação agronômica.

## Reproduzir os artefatos

```powershell
python data/pipeline/build_profiles.py
python data/pipeline/build_crop_transition_markov.py
python data/pipeline/build_economic_benchmarks.py
python -m field_shift.visualize --output docs/visualizacao.html --seed 2026
```

Os pipelines resolvem os contratos ativos por nome lógico em `data/contracts/registry.json`; instale os requisitos de `data/pipeline/requirements.txt` antes de reconstruir os perfis.

O motor de água×fase×decêndio em `data/pipeline/build_crop_markov.py` segue disponível para cenários de balanço hídrico no CLI; não é confundido com a cadeia de transição entre culturas desta página.
