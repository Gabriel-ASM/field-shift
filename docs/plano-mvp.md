# Field Shift Brasil — plano do MVP

## 1. Escopo

Cobrir todo o Brasil desde o MVP. O produtor pode escolher qualquer município ou localizar seu talhão no mapa para simular cinco anos de manejo. O catálogo nacional tem quatro culturas principais (soja, milho, cana-de-açúcar e café) e dez candidatas de rotação, cobertura ou consórcio, selecionadas do levantamento anterior.

| Grupo | Culturas |
|---|---|
| Principais | Soja, milho, cana-de-açúcar, café |
| Candidatas | Sorgo, trigo, feijão, amendoim, aveia-preta, nabo forrageiro, braquiária, milheto, crotalária e mucuna |

Aplicar o catálogo por município, solo e janela, segundo o ZARC e regras agronômicas documentadas. Cana mantém a soqueira entre cortes e admite outra cultura na reforma. Café permanece no talhão durante o ciclo e admite manejo de entrelinha ou renovação. Habilitar resultados quantitativos para as combinações com dados suficientes.

| Cultura inicial | Rotações ou manejos candidatos |
|---|---|
| Soja ou milho | Sucessão com milho e braquiária, sorgo ou cobertura com milheto ou aveia-preta, conforme a região |
| Cana | Reforma com soja, amendoim ou crotalária antes do replantio |
| Café | Entrelinhas com braquiária ou cobertura leguminosa e renovação nas janelas elegíveis |

Começar pela cultura informada pelo produtor. Nas janelas posteriores, comparar culturas e coberturas elegíveis e propor uma sequência de rotação que respeite os intervalos agronômicos. A preferência pela cultura inicial pode ajustar sua pontuação nas janelas em que o retorno for elegível. Se a janela comercial fechar ou a água disponível limitar as candidatas, considerar cobertura ou pousio protegido. Registrar a origem de cada regra.

## 2. Dados e configuração inicial

1. Usar a [triagem dos recursos do desafio](dados-e-validacao.md#conferência-das-fontes), as frequências da seção 3 do [relatório da coleta](../research/relatorio_coleta_final_2026-11-10-v3.md) e o [catálogo de responsáveis](dados-e-validacao.md#frequência-e-responsabilidade). Localizar o manifesto e os arquivos processados antes de calibrar.
2. Priorizar POWER para meteorologia e ET₀ calculada, IMERG para chuva, ERA5-Land para extensão histórica, SMAP e INMET para comparação, SoilGrids e análise local para solo, MapBiomas para histórico descritivo, PAM para rendimento municipal e ZARC para elegibilidade. Conferir Kc e duração por fase com a FAO-56 e referências regionais. Documentar descontinuidades entre fontes e a escala das estimativas.
3. Usar a malha municipal do IBGE como índice nacional e associar as camadas de clima, solo, calendário e produção à localização selecionada. Registrar cobertura e lacunas por município, cultura e safra. Carregar um perfil inicial por região e cultura. O produtor pode ajustar cultura atual, histórico, irrigação, solo, água, preço, custos e prioridades. Mostrar unidade, origem e data dos padrões. Quando faltar um dado essencial, indicar qual entrada precisa ser informada para gerar o resultado.

**Estado deste checkout.** O relatório do Oeste do Paraná cita 22 conjuntos e 55 arquivos processados que não vieram neste checkout. Para os exemplos solicitados, foram baixados e normalizados NASA POWER Daily, SoilGrids v2.0 e malhas IBGE para Ariquemes (RO), Franca (SP) e Varginha (MG). Os perfis calculam um balanço hídrico de referência e rodam Markov + Monte Carlo, sem dados de talhão, cultura, manejo, produção ou economia. A página demonstra essa execução e registra as lacunas para a comparação de rotações.

## 3. Calibração das classes do estado

O estado reúne cultura atual, fase ou idade, histórico recente, água disponível e condição do solo. Calcular diariamente a fração da capacidade de água disponível na zona de raízes. Como premissa inicial de demonstração, usar baixa até 1/3, média acima de 1/3 até 2/3 e alta acima de 2/3. Substituir esses cortes pelos limiares calibrados por cultura e fase quando disponíveis. Classificar o solo como limitante quando algum indicador estiver abaixo do mínimo agronômico, adequado quando todos atingirem o mínimo e favorável quando todos estiverem nas faixas alvo. Usar pH, nutrientes e matéria orgânica conforme o perfil. Usar textura e profundidade para parametrizar o talhão e registrar a incerteza dos indicadores ausentes.

## 4. Transições e simulação

Usar 60 meses com duas atualizações quinzenais por mês (120 passos), balanço hídrico diário e atualização de mercado mensal. A política escolhe ações apenas nas janelas elegíveis com a informação disponível naquele momento. Uma ação de plantio determina a cultura implantada. Para as mudanças incertas de água e solo, estimar probabilidades condicionadas ao estado, à ação e ao clima com frequências de transições comparáveis. Restringir resultados fisicamente impossíveis e normalizar as probabilidades. Com poucos registros, agrupar contextos comparáveis ou usar parâmetros de resposta fundamentados. Quando a evidência for insuficiente, marcar a hipótese ou suspender o resultado quantitativo.

| Configuração inicial | Valor ou regra |
|---|---|
| Trajetórias | 10 mil por estratégia, com sementes registradas e verificação de estabilidade |
| Comparação | Mesmas trajetórias de clima e mercado para todas as estratégias |
| Clima | Reamostrar blocos diários da mesma época do ano para chuva, temperatura, radiação, umidade e vento. Derivar ET₀, veranicos e extremos da trajetória |
| Mercado | Variar preços de venda e custos de insumos em conjunto quando houver séries. Quando faltarem séries, usar valores iniciais editáveis e cenários de sensibilidade identificados |
| Agronomia e Markov | Variar a resposta residual ou os parâmetros de transição apenas quando houver base. Sortear parâmetros por trajetória e o próximo estado a cada passo |

Usar o balanço hídrico como base para a evolução da água. Qualquer transição probabilística adicional representa somente a incerteza residual dessa estimativa. Nas linhas com contagens, usar suavização de Dirichlet com 0,5 de pseudocontagem por destino viável como premissa inicial e testar a sensibilidade desse valor. Aplicar o critério de estabilidade da seção 6.

## 5. Economia e comparação

**Preço por safra.** Na data base da simulação, usar os ajustes dos contratos futuros que cobrem a data esperada de venda. Interpolar linearmente entre vencimentos com cotações válidas. Após o último vencimento com liquidez, carregar seu preço até a safra de venda e identificar o trecho como extrapolação. Registrar bolsa, contrato, vencimento, data base, moeda, unidade e ajuste para a praça. Usar B3 para milho, soja e café, conforme contrato e qualidade. Para cana, usar o contrato local de remuneração. A curva de açúcar ICE pode servir como referência apenas com uma fórmula documentada que converta açúcar e câmbio em remuneração da cana. Para culturas sem referência futura aplicável, usar preço contratado, cotação regional sazonal ou valor informado pelo produtor.

**Desconto.** Usar por padrão o último fechamento disponível da curva soberana prefixada da ANBIMA na data base, no vértice de 1.260 dias úteis (cinco anos), como taxa anual única para fluxos nominais em reais. Como referência inicial, o fechamento de 12/11/2026 foi de 15,4211% a.a. O sistema deve atualizar o valor na data da simulação e permitir substituição pelo produtor. Em um cenário com fluxos reais, usar o vértice correspondente da ETTJ IPCA. [Série ANBIMA](https://www.anbima.com.br/informacoes/est-termo/CZ.asp) · [Consulta de 13/11/2026, coluna fechamento D-1](https://www.anbima.com.br/informacoes/curvas-intradiarias/CIntra.asp).

Calcular o fluxo por hectare nas datas das operações e colheitas, com receita de produtividade × preço, custos de implantação, manejo, irrigação e colheita e valor residual quando aplicável a cana e café. Aplicar os choques do Monte Carlo sobre a curva base e usar as mesmas trajetórias de mercado para as estratégias comparadas. Para coberturas sem comercialização, registrar os custos e a receita das alternativas elegíveis.

Filtrar estratégias inviáveis antes de pontuar. Mostrar sequência proposta, VPL por hectare, mediana, faixa P5–P95, média dos 5% piores resultados, água e condição final do solo. Começar com 25% de peso para cada dimensão (VPL mediano, média dos 5% piores VPLs, menor déficit hídrico e menor frequência de solo limitante no fim do horizonte). Normalizar entre alternativas elegíveis no mesmo talhão. Dimensões empatadas recebem a mesma nota. O produtor pode alterar os pesos e comparar como o ranking muda.

## 6. Validação e expansão

Reservar as três safras completas mais recentes por cultura e região e ajustar com as anteriores. Em cada safra reservada, usar apenas dados disponíveis na data histórica da decisão. Comparar chuva e veranicos com estações, água com SMAP ou medições locais e produtividade com PAM ou registros do produtor. Registrar viés, erro absoluto e cobertura dos intervalos simulados. Incluir casos das cinco macrorregiões quando houver observações comparáveis e documentar lacunas. Usar a coleta do Oeste do Paraná como evidência regional.

Executar três sementes com 10 mil trajetórias por estratégia. Como critério inicial, exigir que a primeira colocada seja a mesma nas três execuções e que a amplitude entre sementes do VPL mediano e da média dos 5% piores VPLs fique abaixo de 1% e 5%, respectivamente, do custo acumulado mediano por hectare da rotação avaliada. Se algum critério falhar, aumentar para 30 mil trajetórias e sinalizar diferenças sem ordenação estável. Registrar versão, responsável e faixa de sensibilidade de cada premissa. Resultados de cenários diferentes podem levar a escolhas diferentes.

Manter o motor comum e configurar por mercado as fontes, culturas, regras de calendário, moeda, unidades e parâmetros. Cada execução identifica região, versões dos dados, perfil, estratégia e semente. Pré-processar séries uma vez por região, reaproveitar cenários entre estratégias e processar trajetórias em lotes. A expansão deve exigir um novo perfil e calibração local, com o mesmo contrato de entrada e saída.

**Ordem de execução** · Mapear cobertura nacional → calibrar água, solo e janelas por região e cultura → simular as estratégias elegíveis → integrar economia → validar em regiões representativas do país.
