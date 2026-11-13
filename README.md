# Field Shift

Proposta de apoio à decisão para comparar rotações de culturas usando observações da Terra da NASA, informações locais de solo e prioridades do produtor.

O projeto responde ao desafio [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/) do NASA Space Apps Challenge 2026.

> **Status:** documentação da proposta. O modelo ainda não foi implementado nem calibrado.

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

Começar com uma área de estudo, poucas culturas candidatas e três classes por variável. Comparar uma rotação de referência com alternativas adaptativas. O horizonte de cinco anos é uma hipótese de planejamento herdada do material inicial; deve ser ajustado às culturas e ao calendário local.

O resultado deve mostrar, por estratégia, produtividade ou margem estimada, condição de água e solo, e a faixa de incerteza. Preços e custos só entram quando houver dados locais confiáveis. A ferramenta apoia a comparação; não substitui recomendação agronômica.
