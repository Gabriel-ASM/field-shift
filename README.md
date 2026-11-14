# Field Shift

Proposta de apoio à decisão para comparar rotações de culturas usando observações da Terra da NASA, informações locais de solo e prioridades do produtor.

O projeto responde ao desafio [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/) do NASA Space Apps Challenge 2026.

> **Status:** NASA POWER/SoilGrids, PAM/IBGE e ZARC/MAPA ingeridos para Ariquemes‑RO, Franca‑SP e Varginha‑MG. A página interativa agora põe a cultura seguinte e o carbono orgânico do solo no centro de uma cadeia de Markov e compara 10.000 trajetórias de solo por rotação; as probabilidades de mudança do solo estão marcadas como hipóteses não calibradas. Há preços de referência congelados do Yahoo para soja e milho, vencimento maio/2027. A demonstração não é recomendação, preço local nem cálculo de margem.

## Executar o motor

Para executar a simulação de referência nos três perfis, rode `python -m field_shift.demo`. Para um perfil isolado, use `python -m field_shift --profile data/profiles/ariquemes-ro --policy data/policies/balanco-hidrico-referencia.json --initial-state water_medium`. Os dados brutos estão em `data/raw/`, os normalizados e as contagens Markov em `data/profiles/`, e as fontes/gaps estão em `data/README.md`.

Abra a [demonstração interativa](docs/visualizacao.html) para escolher a próxima cultura ZARC, avançar o estado cultura×solo e comparar 10.000 futuras cadeias em Ariquemes, Franca e Varginha. A página também mostra os fechamentos Yahoo de 13/11/2026 e um valor bruto indicativo por hectare, calculado com rendimentos municipais PAM/IBGE. Regenere a página com `python -m field_shift.visualize --output docs/visualizacao.html --seed 2026`.

## Ideia em uma figura

```mermaid
flowchart LR
    A[Campo, solo e histórico] --> S[Estado do talhão]
    S --> D[Ação: próxima cultura ZARC]
    D --> R[Estado após a safra: cultura + carbono do solo]
    S --> R
    R --> T[Transição Markov hipotética]
    T --> M[10 mil trajetórias de solo]
    T --> O[Distribuição de resultados]
    O --> C[Comparar rotações e riscos]
```

Na página interativa, o estado junta a última cultura e uma faixa demonstrativa de carbono orgânico do solo. O produtor escolhe a próxima cultura elegível no ZARC; uma hipótese explícita determina a probabilidade da classe de solo após a safra. O Monte Carlo compara repetição da cultura com uma rotação local por cinco safras. O motor de balanço hídrico e suas matrizes água×fase permanecem nos dados e no CLI, fora do foco desta página.

## Documentação

- [Modelo Markov + Monte Carlo](docs/modelo-markov-monte-carlo.md): estados, ações, transições e simulação.
- [Dados e validação](docs/dados-e-validacao.md): fontes previstas, limitações e validação.
- [Plano do MVP](docs/plano-mvp.md): sequência de trabalho e decisões em aberto.
- [Materiais de pesquisa](research/README.md): rascunhos recebidos, preservados como contexto.

## Escopo proposto

O escopo nacional continua como objetivo do produto. Esta entrega contém três exemplos municipais com dados ambientais remotos e agrícolas públicos; não representa fazendas nem recomenda manejo. Os 55 arquivos originais citados para o Oeste do Paraná continuam fora do checkout; não foram usados nem substituídos por arquivos sintéticos.

O caminho de dados para meteorologia, solo, estados Markov, contagens de transição e Monte Carlo está descrito em [data/README.md](data/README.md) e nos esquemas em `data/contracts/`. O inventário extraído do relatório e da planilha está em `data/catalog/` e `data/reference/`, com ausências e limites registrados.
