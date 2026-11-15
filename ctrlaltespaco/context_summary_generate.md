# Prompt para o agente: escrever o formulário do Field Shift (NASA Space Apps 2026)

## Tarefa
Escreva os textos do formulário de submissão do nosso projeto no NASA Space Apps Challenge 2026, em inglês (o guia exige inglês na página de submissão e nos materiais ligados). Entregue, em um arquivo Markdown, um bloco pronto para colar em cada campo, mais a lista de References. Não invente dado, número, fonte ou resultado. Quando faltar informação, escreva "[PENDENTE: o que falta]" e liste tudo no fim.

## Contexto do evento
- Desafio: "Field Shift: Adapting Farms with NASA Data" (spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/).
- O desafio pede uma ferramenta de apoio à decisão que use observações da Terra da NASA, informação local de solo, características das culturas e prioridades do produtor, para explorar estratégias de rotação que melhorem a saúde do solo e a resiliência. Pede comparar pelo menos 3 estratégias, incluindo a rotação existente, e explicar por que cada uma foi sugerida, que evidência a sustenta, benefícios, lacunas de informação e riscos que exigem revisão local. A ferramenta apoia, não substitui, o produtor e o especialista local.
- Tudo o que está em "Potential Considerations" (nitrogênio, erosão, geada, pragas, forragem, deslizadores de cenário, mapas) é opcional ("You may, but are not required").
- Critérios de julgamento (nota de 1 a 5 em cada): Impacto, Criatividade, Validade, Relevância (uso real de dados da NASA como parte central) e Apresentação. O guia recomenda investir na narrativa. Regras da submissão (guia de 2026): demo de até 7 slides ou vídeo de até 30 s (vídeo em outro idioma exige legenda em inglês); times de 1 a 6 pessoas; tudo o que não é do time (código, texto, imagem, dado) deve estar no campo References; o time confirma que o trabalho é original. Nada exige repositório de código.

## Campos do formulário (aba "Project" da página do time)
Summary · Project Demonstration (links) · Project Details (texto livre) · Use of Artificial Intelligence (AI) · NASA Data · Space Agency Partner & Other Data · References. Em cada um, eu quero uma versão que siga os padrões dos vencedores abaixo.

## Como os vencedores de 2025 preencheram (amostra: os 10 Global Winners, lidos nas páginas dos times)
**Summary**
- Um único parágrafo, sem títulos nem listas, de 610 a 1.430 caracteres (mediana cerca de 1.100) e de 4 a 8 frases.
- Abre com o nome e o tipo do produto ("We developed X, a platform that…" ou "X is an interactive dashboard that…"). Depois vêm o problema, a solução, por que importa e o impacto.
- 9 dos 10 citam a NASA já no Summary. Poucos usam números (o Queñaris cita a queda da vazão de uma nascente de 14 L/s para 0).

**Project Details**
- Varia de cerca de 900 a 12.900 caracteres (mediana cerca de 2.500). Os mais longos têm seções com títulos (descrição detalhada, como funciona, benefícios e metas, roadmap, modelo de negócio) e imagens (4 de 10 usam imagens, até 16).
- Um deles usa emoji e tom narrativo (história infantil); a maioria é técnica e direta.

**Use of Artificial Intelligence (AI)**
- Todos preenchem, de 30 a 1.200 caracteres. Os melhores separam o uso de IA no produto do uso de IA no desenvolvimento e dizem o que a IA faz (por exemplo, contar árvores, avaliar a saúde da floresta).

**NASA Data**
- É uma lista curta de conjuntos e APIs da NASA, com nomes e links da documentação (por exemplo, NDVI/EVI, FIRMS, LAADS DAAC, Earthdata CMR), de 60 a 1.050 caracteres.

**Space Agency Partner & Other Data**
- Lista dos dados externos (por exemplo, EIA, OpenStreetMap, Open-Meteo, APIs do Google). O texto do desafio que aparece depois é inserido pela página, não pelo time.

**Entrega (links)**
- Só 2 de 10 têm repositório linkado. 6 de 10 têm site publicado (Vercel, Netlify, GitHub Pages), 4 de 10 têm vídeo no YouTube, e vários têm PDF no Drive. Para nós, o repositório é secundário. O que aparece é a demo, o vídeo ou os slides e o site.

## O que é o nosso projeto
Nome: **Field Shift** (repo local `~/Desktop/field-shift`; README e `docs/plano-mvp.md` descrevem tudo). É um app de apoio à decisão que compara rotações de culturas no Brasil.
- **Fluxo na tela (`docs/visualizacao.html`):** escolher o município, a cultura inicial (soja, milho ou cana), ajustar o controle de prioridades (retorno contra solo e água) e receber uma sequência recomendada para 5 anos, com alternativas, VPL por hectare, distribuição de risco (CVaR5, mediana, P95) e a evolução de água e carbono do solo.
- **Motor:** cadeia de Markov entre 14 culturas (prior regional da PAM/IBGE com Dirichlet α=0,5, limitada por janelas do ZARC/MAPA) + Monte Carlo de até 100.000 trajetórias, que reamostra blocos históricos de chuva e ETo do NASA POWER, atualiza a água a cada quinzena e o carbono do solo por cultura, e desconta os fluxos de caixa (VPL em R$/ha com preços e custos da PAM/CONAB).
- **Municípios disponíveis:** Ariquemes-RO, Franca-SP e Varginha-MG (exemplos regionais, não talhões).
- **Dados da NASA:** só o NASA POWER (chuva e ETo). Não use SMAP, MODIS, GPM, Landsat, ECOSTRESS, GRACE ou SRTM. Nada disso está no modelo. SoilGrids/ISRIC (carbono, capacidade de água) **não é dado da NASA**, e o texto deve deixar isso claro.
- **Componente de carbono e nitrogênio (na máquina `space`, em `/opt/projeto/teste2/apresentacao/`, servida na porta 3000 por túnel SSH):** apresentação de 10 slides com RothC mensal (DPM, RPM, BIO, HUM, IOM) e balanço de N total simplificado para 14 culturas e 4 áreas (Cascavel-PR, Franca-SP, Varginha-MG e Ariquemes-RO). Os aportes de C, C:N, fixação biológica de N e exportação por cultura são **hipóteses nossas**, marcadas [hip] no código. O COS cai em todas as áreas porque o aporte assumido é menor que o de equilíbrio. **Não é previsão.** Confirme com o time se esse componente entra na submissão antes de descrevê-lo.
- **Limites que o texto deve declarar:** resultado exploratório, não prova causal nem recomendação agronômica; o Monte Carlo explora a variabilidade climática histórica, mas **não simula um clima deslocado** (não há deslizador de chuva ou temperatura); a cadeia de Markov vem de dados municipais, não de histórico de talhão; rendimento, preço e custo vêm da PAM/CONAB ou de proxy identificado; as respostas de solo e água por cultura são hipóteses não calibradas; SoilGrids é estimativa de grade com cobertura parcial e o N é N total, não disponível; o NASA POWER pode subestimar a chuva em alguns lugares (Ariquemes, não conferido com o INMET). Só há 3 municípios nesta versão, embora o plano fale em cobrir o país.

## Lacunas conhecidas em relação ao desafio (não esconda; trate como "gaps" e "next steps")
1. A "rotação atual" do produtor não é marcada como uma estratégia separada; a página mostra a recomendada e 3 alternativas, cada uma com VPL.
2. A página não traz por estratégia as frases "por que foi sugerida, evidência, benefícios, lacunas e riscos". Se o formulário for fazer essa comparação, escreva-a a partir dos números reais da simulação, sem inventar.
3. Nitrogênio aparece só na apresentação da `space`, não na página. Erosão, geada, pragas e forragem não são modelados.
4. Há mistura de português e inglês na interface.

## Referências já levantadas (confirme DOI e páginas antes de enviar; foram escritas de memória)
- SoilGrids: Poggio, L. et al. (2021). SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. SOIL, 7, 217–240. https://doi.org/10.5194/soil-7-217-2021. ISRIC, Web Coverage Service: https://maps.isric.org/mapserv (licença CC BY 4.0; dados lidos pelo WCS, coberturas `<variável>_<profundidade>_mean`, 0–30 cm). Preencher a data de acesso.
- RothC: Coleman, K., & Jenkinson, D. S. (1996). RothC-26.3 – A model for the turnover of carbon in soil. In Evaluation of Soil Organic Matter Models (NATO ASI Series I, vol. 38, pp. 237–246), Springer. https://doi.org/10.1007/978-3-642-61094-3_17. Jenkinson, D. S. (1990). Phil. Trans. R. Soc. B, 329, 361–368. Falloon, P. et al. (1998). Soil Biology and Biochemistry, 30(8–9), 1207–1211 (equação do IOM).
- Também citar: NASA POWER (nome exato e versão a confirmar no projeto), FAO-56 (coeficientes Kc), MAPA ZARC / Tábua de Risco, IBGE SIDRA PAM (tabela 5457) e IPCA (tabela 1737), CONAB (custos), MapBiomas, Embrapa (ciclos), Guth et al., Seifert et al., Garbelini et al., University of Minnesota Extension (C:N de 12:1). A lista completa está na seção "Fontes, equações e limites" do `docs/visualizacao.html`.

## Como trabalhar
1. Leia `~/Desktop/field-shift/README.md`, `docs/plano-mvp.md`, `docs/dados-e-validacao.md` e a seção "Fontes, equações e limites" do `docs/visualizacao.html` (o HTML tem 2,8 MB, quase tudo dado embutido; extraia só o texto visível, sem os `<script>`). Se for preciso, rode a página servida localmente (o Chrome não abre `file://`).
2. Escreva cada campo no estilo dos vencedores: Summary em um parágrafo de cerca de 1.000 caracteres; Project Details estruturado com títulos (problema, como funciona, dados, resultados e limites, próximos passos), com 1.500 a 4.000 caracteres e indicação de onde entram imagens; Use of AI separando o uso de IA no produto do uso no desenvolvimento (descreva só o que realmente foi feito); NASA Data com a lista de conjuntos e links (só os que usamos); Other Data com SoilGrids, PAM, CONAB, ZARC, FAO-56 e os demais.
3. Todos os números precisam vir dos arquivos do projeto ou de uma simulação rodada. Marque o que é hipótese.
4. Ao final, entregue: (a) os blocos prontos; (b) a lista de References; (c) uma lista de pendências e dúvidas para o time (por exemplo, se o componente de C e N da `space` entra na submissão, a data de acesso do SoilGrids, links de demo/vídeo/slides, nomes e países do time).

## O que não fazer
Não afirmar que usamos SMAP, MODIS, GPM, Landsat ou outro dado da NASA que não esteja no modelo. Não chamar o resultado de previsão ou recomendação agronômica. Não prometer ganho de renda. Não incluir dado pessoal do time. Não enviar nem submeter nada no portal; o time cola os textos.
