# Markov de culturas + Monte Carlo

## Estados e sequência de culturas

A demonstração trabalha com **uma cultura por talhão em cada passo anual**. O estado Markov é uma cultura individual. O catálogo tem as quatro culturas iniciais do research (soja, milho, cana e café) e as dez culturas candidatas de rotação ou cobertura do plano do MVP. A matriz expõe todos os 14 estados como possíveis destinos.

O pipeline `data/pipeline/build_crop_transition_markov.py` deriva `data/profiles/<perfil>/crop-transition-markov.json` de `pam-history.json`:

1. Soma a área PAM por cultura em cada município-ano. Café arábica e canephora são combinados; aveia em grão é usada como proxy de aveia-preta.
2. Ordena as culturas mapeadas por área e guarda as cinco maiores. Cada uma recebe participação `área_cultura / soma_das_áreas_top5`; culturas fora do catálogo, como arroz, não competem pelo top 5.
3. Para cada par de anos civis consecutivos sem lacuna, soma a massa esperada `participação_t(i) × participação_t+1(j)` a cada aresta i→j. Essa distribuição conjunta de máxima entropia assume independência entre as marginais municipais. Não é contagem observada de talhões ou de sucessões.
4. Preserva os pares rank 1 inteiros e anos de cada mudança como diagnóstico auditável, sem somá-los de novo à massa top-5.

| Item | Definição |
|---|---|
| Estado | Uma das 14 culturas individuais do catálogo |
| Início selecionável | Soja, milho, cana-de-açúcar ou café |
| Marginal anual | Participações de área das cinco maiores culturas PAM mapeadas |
| Massa de aresta | Soma dos produtos das participações em anos consecutivos; fracionária e baseada em independência assumida |
| Diagnóstico rank 1 | Mudanças da cultura que ocupou o primeiro lugar entre anos consecutivos; não usadas como uma segunda contagem |
| Evidência disponível | 38 anos e até 37 pares consecutivos por município |
| Escala | Município-ano; não o mesmo talhão |

A PAM não mostra qual cultura foi plantada no mesmo campo no ano seguinte. A cadeia usa marginais municipais top-5 para criar massa de transição sob independência; por isso ela é um proxy regional e não frequência de rotação parcelar. Braquiária, milheto, nabo forrageiro, crotalária e mucuna não têm produto PAM correspondente e recebem apenas a prior Dirichlet, embora continuem visíveis na matriz.

## Probabilidade Markov condicionada pelo ambiente

Para não eliminar destinos por falta de suporte, cada linha recebe uma prior Dirichlet uniforme com `α = 0,5` em cada destino elegível:

```text
M(i → j) = Σₜ participaçãoₜ(i) × participaçãoₜ₊₁(j)
base(i → j) = (M(i → j) + 0,5) / (suporte_top5_elegível(i) + m_elegível × 0,5)
```

Essa pseudocontagem não é dado. Uma cultura sem massa de destino ainda recebe α: com suporte zero e 14 destinos elegíveis, a probabilidade-base é 7,1%; com suporte positivo cai conforme aumenta o denominador. Os 6–7% são possíveis em linhas pouco apoiadas, mas não são piso, frequência observada ou proporção fixa para toda cultura rara. A prior α=0,5 da cadeia Markov é independente do `n₀` que ajusta a confiabilidade do score econômico das rotas.

Em cada trajetória, o Monte Carlo sorteia uma linha Dirichlet por estado com parâmetros `M(i → j) + 0,5`; massas fracionárias são formas Dirichlet válidas. Depois de simular um ano do ambiente, repondera cada destino e normaliza a linha:

```text
Pₜ(j | i, ambiente) ∝ baseₜ(i → j)
                    × exp[βágua × alinhamento_água × (Kc_efetivoⱼ − Kc_efetivo_médio)]
                    × exp[βsolo × déficit_COS × (ΔCOSⱼ / 0,2)]
```

`Kc` vem de `data/reference/crop-water-parameters.json`; quando a referência Kc de uma cultura falta, o fator hídrico dela é neutro e isso aparece em `water_parameter_support`. Os coeficientes, limites do carbono, pseudocontagem e faixas por cultura estão em `data/reference/soil-crop-response-hypotheses.json`.

## Monte Carlo: ciclo agronômico e calendário

Cada trajetória começa com uma cultura principal já estabelecida, água média e carbono inicial de SoilGrids. O ambiente é atualizado a cada quinzena usando um bloco sazonal NASA POWER sorteado para cada ano; a demanda hídrica acompanha a cultura ativa e o carbono evolui com a faixa hipotética da cultura/cobertura. No fim do ciclo de uma cultura anual, o talhão entra em pousio até a próxima oportunidade municipal de decisão.

Na decisão, a linha de massa PAM top-5 da cultura atual é ajustada pela água e carbono simulados. Os destinos possíveis são culturas com janela MAPA standalone no município em algum momento dos 365 dias seguintes, respeitando também as regras de ciclo perene. A decisão sorteia uma única cultura principal. O plantio só acontece na próxima janela aplicável dessa cultura; o período até lá continua como pousio. A cultura recém-plantada só gera receita após completar o ciclo/maturação indicado. As tábuas MAPA anual 2026/2027 e perene vigente são repetidas nos cinco anos como hipótese, agregam riscos 20/30/40 e unem grupos de cultivar e classes oficiais de solo, pois o exemplo não seleciona o estrato de uma gleba.

Para visualizar o ambiente, cada trajetória registra água e carbono no início (`A0`) e no fechamento de cada ano (`A1` a `A5`). Dois gráficos de área empilhada mostram a participação das trajetórias em cada estado a cada fechamento; as faixas somam 100% em cada `A`. O solo é classificado pelos limiares já usados no modelo: degradado `<10 g/kg`, regular `10–<20 g/kg` e bom `≥20 g/kg`. A água mantém os três estados da cadeia (baixa, média e alta). As classes são hipóteses de demonstração, não rótulos de qualidade calibrados em campo; os gráficos mostram simultaneamente a evolução da distribuição e as contagens finais.

Para manter alternativas de rotação sem calendário publicado, `crop-cycle-assumptions.json` libera qualquer decêndio apenas para nabo forrageiro, braquiária, crotalária, mucuna e aveia-preta quando o perfil não tem linha standalone mapeada. Aveia-preta tem um proxy oficial genérico “Aveia” em Franca e Varginha; apenas Ariquemes usa a hipótese. Soja, milho, cana, café, feijão, amendoim, sorgo, milheto e demais culturas comerciais não recebem esse fallback. Uma linha oficial sem risco 20/30/40 bloqueia a cultura naquele perfil, sem substituição pela hipótese. A lista é uma premissa exploratória de disponibilidade e não afirma que qualquer data seja agronomicamente adequada.

Replantios consecutivos reduzem o rendimento bruto por uma hipótese editável específica por cultura: soja perde 8 pontos percentuais por repetição até 20%, e milho 2,2 pontos até 4,3%. Outras anuais/coberturas mantêm o padrão genérico de 8 pontos até 40%. Os valores de soja e milho se ancoram em estudos de outras regiões e em ensaios brasileiros limitados, não são calibração local. A penalidade afeta receita e VPL, mas não custos nem probabilidades Markov; portanto, uma sequência pode continuar frequente mesmo depois de deixar de liderar o ranking econômico. Esse efeito é somente por replantio consecutivo da mesma cultura: o modelo não simula pragas, doenças ou pressão entre culturas da mesma família. O calendário também não prova que toda janela agregada seja adequada a qualquer talhão; os dias de pousio deixam explícito quando a próxima semeadura só ocorre depois.

## Grafo da cadeia e leitura do Monte Carlo

O HTML mostra os 14 estados como nós e todas as 196 transições possíveis como setas, incluindo laços da cultura para si mesma. Selecione um nó para destacar suas 14 saídas. A espessura da seta representa P média no contexto de água e carbono selecionado; o rótulo mostra essa probabilidade com duas casas decimais. A lista lateral discrimina cada destino:

- `massa/suporte top-5`: massa fracionária esperada i→j e suporte fracionário da cultura de origem após restringir destinos elegíveis.
- `rank 1 PAM`: pares inteiros em que a cultura de maior área mudou, mostrados como diagnóstico; não entram de novo no peso da aresta.
- `P₀`: `(M(i→j) + α)/(suporte_top5_elegível + m_elegível × α)`, antes de reponderar ambiente; a massa e a prior são condicionadas aos destinos elegíveis pelo calendário e pelas regras perenes.
- fatores de água e solo: multiplicadores de destino aplicados antes de normalizar a linha.
- `Dirichlet 90%`: intervalo empírico de 5º a 95º percentil calculado com 1.200 sorteios da linha posterior, mantendo o contexto ambiental fixo. Não é intervalo de confiança das rotações reais do talhão.
- `MC`: quantas trajetórias passaram pela origem e quantas escolheram aquela seta no ano exibido. As cores dos nós mostram a frequência de ocupação por ano.

Assim ficam distintos as áreas PAM observadas, a aproximação de transição top-5, o diagnóstico rank 1, a massa da prior, a probabilidade média contextualizada e as frequências realmente sorteadas. As linhas de posterior usadas pelo Monte Carlo são sorteadas novamente em cada trajetória; água e carbono também variam no tempo. Por isso, a frequência de uma seta no Monte Carlo pode diferir da P média fixa exibida no grafo.

Ao carregar a página, o Monte Carlo inicia depois da primeira pintura da interface e percorre 100.000 trajetórias. A barra atualiza a cada 1.000 e o grafo recebe novas frequências a cada 5.000 trajetórias. As frequências e estatísticas econômicas são acumuladas durante a execução; para cada rota, a interface conserva apenas os valores de VPL e uma trilha compacta de exemplo, evitando guardar os caminhos completos das 100.000 simulações. Uma execução usa a mesma linha Dirichlet sorteada por estado ao longo de cada trajetória; cada nova trajetória sorteia seus próprios parâmetros.

O seletor de decêndio do grafo representa o contexto da decisão; destinos com janela própria mais tarde no horizonte anual podem ser sorteados e esperam em pousio até o plantio. O grafo preserva os 14 nós para inspeção, inclusive os destinos bloqueados na janela contextual, que aparecem com probabilidade operacional zero. As setas exibem massa top-5, suporte fracionário, diagnóstico rank 1, probabilidade contextual, fatores de água/solo, intervalo Dirichlet e contagem Monte Carlo no recorte escolhido. Sem idade do cafezal ou histórico de reforma, café só transita para café no horizonte; a mesma regra vale para cana. Para café, uma subcadeia separada acompanha coberturas de entrelinha sem substituir a cultura principal.

### Água

Os dados `states.json`, `transitions.json` e `environment.json` guardam os estados hídricos. A chuva e ETo da NASA POWER alimentam o balanço de referência Kc=1; a CAD é derivada do SoilGrids por Saxton–Rawls. Para cada cultura, o `Kc` anual efetivo combina as fases FAO‑56 com a demanda Kc=1 fora do ciclo. Após cada classe hídrica sorteada, o armazenamento representativo muda por `(Kc_efetivo − 1) × ETo_quinzenal / CAD` e a classe é reavaliada nos cortes publicados. Culturas sem uma curva válida usam Kc=1. Esse ajuste é um balanço resumido, não medição do talhão.

### Solo

O valor inicial é a média SoilGrids de carbono orgânico em 0–30 cm, ponderada pelas camadas de 0–5, 5–15 e 15–30 cm. A série local não tem medições de carbono pareadas com sequência de culturas; assim, a evolução anual e o efeito do carbono nas probabilidades são hipóteses editáveis, deliberadamente identificadas como não calibradas. Não são estimativas de efeito causal.

## Dados ausentes e limites

O relatório de research lista MapBiomas Coleção 11 e tabelas de transição agrícola, mas os rasters/tabelas correspondentes não estão neste checkout. A página oficial informa que o produto agrícola 1ª safra é uma série anual baseada em pixels e publica os assets pelo GEE; seu produto de 2ª safra é complementar. Sem a sequência local do mesmo pixel, a PAM municipal não pode ser convertida em rotação do talhão. Os destinos sem PAM são mantidos como possibilidades via prior explícita, nunca como contagem inventada.

A cadeia é uma demonstração regional, não recomendação agronômica, previsão de produtividade ou efeito econômico. Para calibrar rotação e carbono do talhão são necessários histórico espacial do mesmo talhão, cultura por safra, análise local de solo e validação agronômica.

## Nota econômica e ambiente final

O ranking agrupa pela **sequência agrícola efetivamente realizada**. A assinatura registra a cultura inicial, cada plantio principal (inclusive replantio da mesma cultura) e, separadamente, as coberturas nas entrelinhas do café. Datas diferentes não criam grupos distintos, mas continuam afetando os fluxos do VPL por meio de ambiente, maturação, colheita, custo e desconto. Decisões cujo plantio fica fora do horizonte não entram na sequência realizada.

A nota total varia de 0 a 10 e divide o peso entre economia e ambiente final. Dentro da economia, o controle combina CVaR5 (resiliência, média dos 5% piores VPLs) e P95 (retorno alto, sem usar o máximo isolado); CVaR5 é uma medida econômica, não um terceiro componente separado. A subnota econômica é convertida para 0–10 com uma escala comum calculada sobre os VPLs elegíveis; 5 equivale a um score econômico composto de R$ 0/ha. Mediana, probabilidade de perda, CVaR5 e P95 continuam expostos em R$/ha.

O segundo controle ajusta o peso do ambiente final entre 0% e 50%, com padrão de 20%. O peso restante fica com a parte econômica. Dentro do ambiente, dois terços da nota vêm do carbono do solo e um terço da água. Na configuração padrão, com a composição econômica em 50/50, a nota total tem 40% P95, 40% CVaR5, 13,3% solo e 6,7% água.

Para cada rotação, a nota de solo usa a **média do carbono orgânico final** das trajetórias agrupadas: `solo10 = limitar(media_SOC_final / 20 g/kg × 10, 0, 10)`. O limiar de 20 g/kg é a referência da classe alta em `soil-crop-response-hypotheses.json`; a conversão para pontos é uma hipótese linear, não uma função de produção calibrada. A tabela mostra o carbono final médio observado na simulação.

A nota de água usa a distribuição das classes hídricas finais da rota e os multiplicadores de rendimento existentes (baixa/média/alta: 0,90/1,00/1,05). Com a classe média como referência 5 e a maior perda como escala, as notas são 0 para baixa, 5 para média e 7,5 para alta. Essa assimetria espelha os multiplicadores atuais: baixa reduz 10%, alta acrescenta 5%. A tabela mostra a frequência de cada classe final, não apenas a classe mais comum.

As notas usam diretamente os resultados da rotação, sem contração ou peso por frequência. O número de trajetórias, de VPLs completos e a fração da amostra aparecem para contextualizar a incerteza; não aumentam nem reduzem o score. Portanto, rotas raras podem alcançar qualquer posição conforme seus resultados, mas sua pontuação deve ser lida junto ao tamanho da amostra.

Em forma compacta: `nota_total = (1 − peso_ambiente) × subnota_econômica + peso_ambiente × (2/3 × solo10 + 1/3 × água10)`. A contagem amostral não aparece na fórmula. Por isso, 5 é o ponto de equilíbrio da **subnota econômica**; a nota total também pode subir ou cair com as condições finais de solo e água. Os sliders reordenam o ranking sem refazer as trajetórias.

O ranking compara rotas amostradas; não avalia sequências que nunca ocorreram na simulação, não é uma política anual ótima e não modela pragas/doenças, idade e reforma de perenes ou preço local na porteira. Solo e água finais são resultados do modelo e dependem das hipóteses documentadas.

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
python -m field_shift.legacy.visualize --output docs/visualizacao.html --seed 2026
```

Os pipelines resolvem os contratos ativos por nome lógico em `data/contracts/registry.json`; instale os requisitos de `data/pipeline/requirements.txt` antes de reconstruir os perfis.

O motor de água×fase×decêndio em `data/pipeline/build_crop_markov.py` segue disponível para cenários de balanço hídrico no CLI; não é confundido com a cadeia de transição entre culturas desta página.
