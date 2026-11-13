# Field Shift

Proposta de apoio à decisão para comparar rotações de culturas usando observações da Terra da NASA, informações locais de solo e prioridades do produtor.

O projeto responde ao desafio [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/) do NASA Space Apps Challenge 2026.

> **Status:** núcleo Markov e Monte Carlo disponível com dados sintéticos. A calibração e a integração das fontes nacionais estão pendentes.

## Rodar o exemplo

Na raiz do repositório, execute `python -m field_shift` com Python 3.10 ou posterior. O exemplo compara duas políticas em 500 trajetórias de cinco anos e imprime as probabilidades dos estados finais. A configuração do motor usa 10 mil trajetórias por padrão. Consulte o [formato dos dados](data/README.md) para conectar um perfil próprio.

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

O MVP cobre todo o Brasil e simula cinco anos de manejo por talhão. O produtor pode selecionar qualquer município brasileiro. As opções de manejo dependem do calendário, do solo e dos dados disponíveis para a região. O catálogo prevê soja, milho, cana-de-açúcar, café e dez culturas candidatas para rotação, consórcio ou cobertura.

O produtor ajusta os dados iniciais e compara retorno, risco, água e solo. Preços e custos fazem parte da simulação. O motor usa perfis regionais de dados, regras e parâmetros para permitir expansão a outros mercados.
