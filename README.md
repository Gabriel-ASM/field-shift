# Field Shift

Proposta de apoio à decisão para comparar rotações de culturas usando observações da Terra da NASA, informações locais de solo e prioridades do produtor.

O projeto responde ao desafio [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/) do NASA Space Apps Challenge 2026.

> **Status:** NASA POWER Daily e SoilGrids baixados para três exemplos brasileiros; balanço hídrico de referência ligado a Markov + Monte Carlo. Sem transições de campo, cultura ou manejo, a execução não calcula recomendação de rotação nem VPL.

## Executar o motor

Para executar a simulação de referência nos três perfis, rode `python -m field_shift.demo`. Para um perfil isolado, use `python -m field_shift --profile data/profiles/ariquemes-ro --policy data/policies/balanco-hidrico-referencia.json --initial-state water_medium`. Os dados brutos estão em `data/raw/`, os normalizados e as contagens Markov em `data/profiles/`, e as fontes/gaps estão em `data/README.md`.

Abra a [demonstração interativa](docs/visualizacao.html) para conferir os dados e rodar novamente 10.000 trajetórias para Ariquemes, Franca e Varginha. A seleção de talhão no mapa foi deixada fora. Regenere a página com `python -m field_shift.visualize --output docs/visualizacao.html --seed 2026`.

## Ideia em uma figura

```mermaid
flowchart LR
    A[Campo, solo e histórico] --> S[Estado do talhão]
    B[Clima NASA + dados locais] --> M[Cenários Monte Carlo]
    S --> D[Ações de cultivo viáveis]
    D --> R[Resposta da cultura e do solo]
    M --> R
    R --> T[Transição de Markov]
    T --> O[Distribuição de resultados]
    O --> C[Comparar rotações e riscos]
```

O estado Markov descreve o talhão. O Monte Carlo cria futuros plausíveis de clima e incerteza dos parâmetros. Em cada cenário, uma ação de manejo e o ambiente determinam a distribuição de transição para o próximo estado.

## Documentação

- [Modelo Markov + Monte Carlo](docs/modelo-markov-monte-carlo.md): estados, ações, transições e simulação.
- [Dados e validação](docs/dados-e-validacao.md): fontes previstas, limitações e validação.
- [Plano do MVP](docs/plano-mvp.md): sequência de trabalho e decisões em aberto.
- [Materiais de pesquisa](research/README.md): rascunhos recebidos, preservados como contexto.

## Escopo proposto

O escopo nacional continua como objetivo do produto. Esta entrega contém três exemplos municipais com dados ambientais remotos e não representa fazendas nem recomenda manejo. Os 55 arquivos originais citados para o Oeste do Paraná continuam fora do checkout; não foram usados nem substituídos por exemplos sintéticos.

O caminho de dados para meteorologia, solo, estados Markov, contagens de transição e Monte Carlo está descrito em [data/README.md](data/README.md) e nos esquemas em `data/contracts/`. O inventário extraído do relatório e da planilha está em `data/catalog/` e `data/reference/`, com ausências e limites registrados.
