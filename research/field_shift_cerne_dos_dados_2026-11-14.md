# Field Shift: cerne dos dados

> Transcrição estruturada do PDF de 7 páginas gerado em 14/11/2026. O texto e as tabelas foram extraídos do PDF; a paginação original é indicada para facilitar a conferência. A revisão visual do original foi feita nas sete páginas renderizadas.

<!-- Página 1 do PDF original -->

Field Shift: cerne dos dados
NASA Space Apps 2026, tema 7 · Oeste do Paraná (Cascavel, Toledo, Assis Chateaubriand) · evento 14 e 15/11/2026
Como usar. Este PDF reúne o essencial de três documentos: V3 = relatório final da coleta v3 (28 p., 2026-11-10); FAO = material
FAO (9 p., 2026-11-10); GR = guia rápido v2 (3 p., 2026-11-14). Cada bloco termina com “Ref:” indicando seção e página da fonte. A
seção final (Referências) traz o índice “preciso de X, onde está” e os arquivos de dados de origem. Onde a fonte diz NÃO
ENCONTRADO ou NÃO LEGÍVEL, está igual aqui.
## 1. Visão em 30 segundos
- Escopo da fase: coleta, padronização e validação de dados. Nenhuma modelagem foi feita; nenhum estado climático foi
calculado.
- Núcleo de ingestão pronto: limites IBGE; POWER diário com ET0; chuva IMERG (de 1998) e ERA5-Land (de 1981); SMAP L4;
NDVI MOD13Q1; MapBiomas C11; PAM; ZARC; solo (SoilGrids, CAD, SiBCS) e relevo; ONI v6; NEX-GDDP-CMIP6; tabela diária
observada.
- Tabela diária observada: 50 238 linhas, 41 colunas, 1981-01-01 a 2026-11-06 (clima_observado_diario_municipio).
Integridade: 55 de 55 arquivos do manifesto com sha256 igual.
- Kanban de mapeamento: 108 recursos; 67 verificado, 37 em_andamento, 2 bloqueado (R002 SICAR, R018 ANA HidroWeb), 2
descartado (R037 Cemaden umidade do solo, R067 TerraClass).
- Culturas do plano: soja, milho 1ª safra, milho 2ª safra e trigo; coberturas aveia-preta, braquiária e crotalária.
- O que o desafio pede: ferramenta de apoio à decisão que compare pelo menos 3 rotações (incluindo a atual), com por quê,
evidência, benefícios, lacunas e riscos para revisão local. Apoia, não substitui o agricultor.
- Pendente: conferência do Kc do FAO-56 (0 de 25 linhas), dados bônus (yfinance, PTAX, CONAB), rotação de credenciais e
parâmetros que a modelagem ainda fixa (seção 9).
Ref: V3 §1 p.2, §10 p.23, §11 p.25 · FAO §1 p.2 · GR §1 p.1
## 2. Mapa dos dados
Um conjunto por linha. “Cuidado” é a ressalva que mais pesa no uso. Períodos são os realmente ingeridos.

| Dado (fonte) | Período | Resolução | Uso | Cuidado |
| --- | --- | --- | --- | --- |
| Limites municipais (IBGE<br>Malha 2025) | edição 2025 | polígonos,<br>1:250.000 | base das agregações | — |
| POWER diário + ET0<br>(NASA POWER,<br>comunidade AG) | 1981-01-01 a<br>2026-11-06 | 0,5° × 0,625°;<br>radiação 1° ×<br>1° | temperatura, radiação,<br>umidade, vento, ET0<br>(M4) | radiação só desde 1984; ET0 de 1981–83 com radiação<br>por Hargreaves; Toledo e Assis na mesma célula<br>(430,2 m) |
| Chuva IMERG V07 (NASA<br>GPM) | 1998-01-01 a<br>2026-11-07 | 0,1° | chuva padrão<br>(prec_padrao_mm) | Final só até 2025-09-29; depois provisório (403 dias<br>por município) |
| Chuva ERA5-Land<br>(ECMWF) | 1981-01-01 a<br>2026-11-02 | 0,1° (~9 km) | alternativa e série<br>1981–1997 | 5% a 8% abaixo do IMERG; não emendar com IMERG |
| SMAP L4 (NASA) | 2015-03-31 a<br>2026-11-04 | 9 km | umidade de superfície e<br>zona radicular (apoio,<br>validação) | aviso de geolocalização do NSIDC de 2026-05-14 a<br>2026-07-28 (76 dias, sinalizado) |
| NDVI e EVI MOD13Q1<br>(NASA MODIS v061) | 2000-02-18 a<br>2026-10-16 | 250 m, só pixels<br>agrícolas | vigor por safra (M5) | 16 composições com menos de 50% de pixels válidos;<br>filtrar por frac_valida |
| ONI v6 (NOAA CPC) | 1950-01-15 a<br>2026-09-15 | índice único<br>(Niño 3.4) | fase do ENOS (M6) | NOAA passou a usar o RONI no monitoramento oficial |
| MapBiomas Coleção 11 | 1985 a 2025 | 30 m | sequência de culturas<br>(M7, D5) | soja +11% a +21% acima da PAM; 2ª safra e ciclos em<br>beta |
| PAM (IBGE, SIDRA 5457<br>e 839) | área plantada<br>1988–2025;<br>demais variáveis<br>1974–2025 | município | área e rendimento (M5) | repete valores em anos seguidos; milho 1ª e 2ª safra<br>só desde 2003; valor em 5 moedas |
| ZARC (MAPA) | safra 2016/2017 a<br>2026/2027 | município ×<br>cultura × ciclo<br>× solo | janelas de plantio (M3);<br>4 433 linhas | valores 0/20/30/40 lidos como risco em %, inferido<br>(dicionário do MAPA não define) |
| Solo (SoilGrids; CAD<br>Saxton e Rawls; SiBCS<br>IBGE) | estático | 250 m; SiBCS<br>1:250.000 | CAD de 103 a 121 mm<br>até 1 m; ordem<br>dominante: Latossolo | média por município e máscara agrícola, não por<br>talhão |
| Relevo (NASADEM) | 2000-02-11 a<br>2000-02-21 | 1 arco-segundo<br>(~30 m) | altitude e declive;<br>correção futura da<br>temperatura | altitude difere da célula do POWER (seção 5) |
| NEX-GDDP-CMIP6<br>(NASA) | 1981-01-01 a<br>2060-12-31 | 0,25° (pixel de<br>27,8 km) | clima futuro SSP2-4.5 e<br>SSP5-8.5 (M6, M9) | viés por modelo e modelos com defeito (seção 4) |
| INMET (chuva horária,<br>10 estações PR) | 2006-01-01 a<br>2026-10-31 | estação | só validação da chuva | estações a 31–158 km dos centroides; lacunas longas;<br>só chuva extraída |


---

<!-- Página 2 do PDF original -->

| Dado (fonte) | Período | Resolução | Uso | Cuidado |
| --- | --- | --- | --- | --- |
| FAO-56 (extrato de Kc e<br>estágios) | 1998 | não se aplica | Kc do balanço hídrico<br>(M4) | pendente: 0 de 25 linhas conferidas (seção 6) |

Ref: V3 §2 p.3–4 (inventário), §3 p.5–6 (frequência e latência), §3.1 p.6 (divergências entre arquivos) · GR §2 p.1
## 3. Chuva: o que a evidência diz (decisão D1)

| Comparação | Resultado | Janela / base |
| --- | --- | --- |
| POWER × IMERG | IMERG 16,7% a 18,3% maior (POWER 14% a 16% abaixo); r diário 0,72–0,75,<br>mensal 0,93–0,95 | 1998-01-01 a 2025-09-29; 3<br>municípios |
| ERA5-Land × IMERG | ERA5-Land 4,7% a 7,9% abaixo; r diário 0,66–0,69, mensal 0,86–0,87 | idem |
| IMERG × pluviômetro<br>INMET | r diário 0,784, mensal 0,862; viés +7,4% (diário) e +5,7% (mensal); por estação de<br>−3,1% (B804) a +17,2% (A846) | 10 estações, pixel da estação,<br>2006-01-01 a 2025-09-29; 39 005<br>dias |
| ERA5-Land ×<br>pluviômetro INMET | r diário 0,626, mensal 0,764; viés −4,1% e −5,3%; por estação de −24,8% (B803)<br>a +18,6% (A846) | idem |
| Viés por janela<br>(calculado) | 1998–2011: POWER −13,3% (r mensal 0,970), ERA5-Land −3,6% (0,856).<br>2012–2025-09-29: POWER −16,9% (0,917), ERA5-Land −8,5% (0,873). O viés<br>cresce da calibração para o teste | tabela diária, 3 municípios |
| Decisão do plano (D1): IMERG é a chuva padrão de 1998 em diante. Para a série longa do Markov, testar POWER corrigido por<br>quantis para o IMERG (1981–2025) e ERA5-Land corrigido; calibrar em 1998–2011, testar em 2012–2025, reportar viés e correlação<br>antes e depois; não emendar fontes. Nada foi corrigido nesta fase. |  |  |

- O IMERG tem correlação maior que o ERA5-Land em todas as 33 combinações de estação e escala. O POWER não entrou na
comparação com pluviômetros.
- A chuva de 1981 a 2005 continua sem validação por pluviômetro. As estações não ficam dentro dos municípios. Lacunas: A843 e
A855 sem dado em 2021; A846 sem dado em 2025 e 2026.
- IMERG Final V07 terminou em 2025-09-29. São 403 dias provisórios por município (2025-10-01 a 2026-11-07), mais 1 dia misto;
status_imerg marca cada dia. O Final V08 estava previsto para o outono de 2026 e não está confirmado.
Ref: V3 §5.2 p.8, §5.8 p.12–13, §8 itens 9 e 12 p.20–21, §11.2 (D1) p.26 · GR §7 p.3
## 4. Clima futuro: NEX-GDDP-CMIP6 (decisão D6)
O que é: projeções climáticas diárias de modelos globais (CMIP6), reduzidas de escala pela NASA. Variáveis: chuva (pr),
temperatura máxima, mínima e média (tasmax, tasmin, tas). Cenários SSP2-4.5 e SSP5-8.5, ingeridos até 2060. Alimenta o slider
de cenário, a cadeia de Markov futura (M6) e o Monte Carlo (M9).

| Escolha | Modelos | Regra | Ficam de fora |
| --- | --- | --- | --- |
| Catálogo | 34 | sem exclusão | nenhum |
| Comuns aos dois cenários | 33 | presentes em SSP2-4.5 e SSP5-8.5 | HadGEM3-GC31-MM (só em historical e SSP5-8.5) |
| Com tasmax e tasmin | 30 | os 33, sem os que não têm as duas bandas | CESM2, CESM2-WACCM, HadGEM3-GC31-MM, IITM-ESM |
| Sem o fora de curva<br>térmico | 29 | os 30, sem o CMCC-CM2-SR5 | os 4 acima + CMCC-CM2-SR5 |
| Sem os três fora da curva | 27 | os 30, sem CMCC-CM2-SR5, TaiESM1 e<br>GFDL-ESM4 | os 4 acima + CMCC-CM2-SR5, GFDL-ESM4, TaiESM1 |

- Ingestão: histórico e cenários 2015–2020: 101 de 101 séries, 1 707 228 linhas; cenários 2021–2060: 67 de 67 séries, 2 936 610
linhas; 0 falhas.
- Viés de referência 1981–2014, sem correção (mediana entre modelos): Tmax +0,52 °C, Tmin +0,13 °C, tmédia +0,74
°C contra o POWER. Chuva −9,11% contra o IMERG (1998–2014), −7,21% contra o POWER e −15,27% contra o ERA5-Land
(1981–1997). O viés depende da referência de chuva escolhida; fixe a referência antes de comparar cenários.
- Janela 2021–2025 contra o observado: SSP2-4.5 com Tmax +0,12, Tmin +0,22, tmédia +0,58 °C e chuva −2,50%; SSP5-8.5
com +0,24, +0,33, +0,71 °C e −2,85%. Janela curta e com El Niño 2023–24: não serve de referência de viés.
- Modelos com defeito: CMCC-CM2-SR5 (Tmin +8,2 °C já no histórico; amplitude térmica de 3,2 °C contra ~11 °C nos outros;
dado suspeito na origem). TaiESM1 (banda tas dos cenários salta +3,6 °C; não usar tas dele). CanESM5 (salto de tasmax +1,25
°C no SSP5-8.5) e GISS-E2-1-G (salto de tas +1,11 °C no SSP5-8.5). GFDL-ESM4 só é fora de curva em 2021–2025 (chuva −20%
no SSP5-8.5); no histórico fica em −12,0%, dentro da faixa.
- Linhas com Tmin > Tmax: 45 em 2021–2060 e 24 na rodada histórica e nos cenários 2015–2020; mantidas e sinalizadas.
Decisão do plano (D6): usar os modelos comuns aos dois cenários; estados de cada modelo (seco, normal, úmido) pelos tercis do
próprio período histórico dele (1981–2014), nunca pelos limiares do observado. Falta: calcular os tercis e escolher o conjunto de
modelos (33, 30, 29 ou 27). A exclusão de 29 e 27 vem do dicionário, não de uma regra no arquivo de modelos.
Ref: V3 §5.6–5.7 p.11, §6 p.14–16 (tabela dos 34 modelos e regras), §7 p.18, §11.2 (D6) p.26 · GR §2 p.1


---

<!-- Página 3 do PDF original -->

## 5. Cultivo, solo e relevo
MapBiomas × PAM (soja) e disponibilidade da PAM

| Item | Resultado |
| --- | --- |
| Área de soja, MapBiomas<br>contra PAM | média +11,5% (Assis), +12,6% (Cascavel), +20,7% (Toledo), 38 anos (1988–2025). Mínimo −30,5% (Cascavel<br>2003, causa não verificada), máximo +75,4% (Cascavel) |
| Cautela antes de ~1995 | média de 1988 a 1995: +30,1% (24 linhas); de 1996 em diante: +10,9% (90 linhas). Hipótese de uso, a testar:<br>MapBiomas para a sequência de culturas, PAM para a magnitude |
| PAM: soja, trigo e milho total | área plantada 1988–2025 (38 anos); área colhida, produção e rendimento 1974–2025 (52 anos), sem falha nos 3<br>municípios |
| PAM: milho por safra | 1ª e 2ª safra só desde 2003 (tabela 839): 2003–2025 em Cascavel e Toledo; Assis 1ª safra 2003–2023 sem 2018<br>(2024 e 2025 sem linha); 2ª safra 2003–2025 nos três. Sem valor da produção |
| PAM: valor e aveia | valor da produção em 5 moedas (mil Cruzeiros a Reais), não comparável sem conversão. Aveia da PAM com<br>muitas lacunas (Assis só 5 anos); não use como proxy da aveia-preta de cobertura (observação minha, não dos<br>documentos) |
| Não testado | consistência do rendimento e da produção antes de 1988 e antes de ~1995 (a cautela do v3 foi medida só para<br>área plantada) |

Relevo, solo e outros limites
- Altitude, município menos a célula do POWER: Assis −47,8 m, Cascavel +49,2 m, Toledo +72,9 m (na máscara agrícola:
−43,0, +68,8 e +81,5 m). Gradiente de temperatura com a altitude: NÃO ENCONTRADO.
- Solo: CAD de 103 a 121 mm até 1 m; ordem de solo dominante Latossolo (SiBCS). Valores por município e máscara, não por
talhão.
- Irrigação é marginal: 1.189 ha em 2017 (0,28% do território); não condiciona a rotação. MapBiomas de pivô central contra o
Censo 2017 não valida.
- A classe de soja do MapBiomas não separa milho 1ª safra nem trigo; a matriz de transição dela não é de rotação. A 2ª safra
(beta) só detecta milho, algodão e outras.
- El Niño: 2026 termina com ONI ASO 2026 = +2,46 °C. A relação ENOS, chuva e rendimento no Oeste do Paraná não foi testada;
falta comparar o ONI v6 com o RONI antes de fixar limiares.
Ref: V3 §5.3 p.9, §8 itens 3, 7 e 10 p.19–21, §11.2 (D3, D5) p.26 · GR §2 p.1 · conferência da PAM em disco de 14/11 (pam_municipio_cultura_ano.csv,
668 linhas; resultado colado pelo usuário)
## 6. FAO-56: ET0 e Kc
- ET0 de Penman-Monteith (eq. 6 do FAO-56) implementada e validada no Exemplo 18 (Uccle): 3,880 contra 3,88 mm/dia;
todas as grandezas dentro de 0,1%. Valida as equações em um dia; não valida a radiação estimada nem o preenchimento de
lacunas do POWER.
- Extrato de Kc e estágios: 25 linhas (18 da Tabela 11, 7 da Tabela 12). Conferidas contra o PDF: 0 de 25. Células NÃO
LEGÍVEIS: 6. Linhas com valor inferido: 1 (trigo de inverno, Califórnia, soma 180).
- Nenhuma linha da Tabela 11 é do Oeste do Paraná. Escolher a linha por cultura e época de plantio (ou combinar com o
ZARC) fica para a modelagem.
Kc impresso (Tabela 12), condições-padrão: UR mínima ~45%, u2 ~2 m/s. Todos pendentes de
conferência.

| Cultura (projeto) | Kc ini | Kc mid | Kc end | Altura máx. (m) |
| --- | --- | --- | --- | --- |
| Soja | NÃO LEGÍVEL | 1.15 | 0.50 | 0.5–1.0 |
| Milho grão (1ª e 2ª safra) | NÃO LEGÍVEL | 1.20 | 0.60–0.35 | 2 |
| Trigo de inverno, solos congelados | 0.4 | 1.15 | 0.25–0.4 | 1 |
| Trigo de inverno, solos não congelados | 0.7 | 1.15 | 0.25–0.4 | NÃO LEGÍVEL |
| Trigo de primavera | NÃO LEGÍVEL | 1.15 | 0.25–0.4 | 1 |
| Pastagem rotacionada (não equivale a<br>braquiária) | 0.40 | 0.85–1.05 | 0.85 | 0.15–0.30 |
| Pastagem extensiva (não equivale a braquiária) | 0.30 | 0.75 | 0.75 | 0.10 |

- Durações dos estágios (Tabela 11), L_total: soja 85 d (Trópicos), 140 d (EUA central), 150 d (Japão); milho grão de 125 a
180 d conforme a região; trigo de inverno de 180 a 335 d. Todas de outras regiões.
- Notas do extrato: milho Kc end 0.60 é com grão úmido e 0.35 após secagem no campo; trigo, o valor maior de Kc end é para
colheita manual. Faixas como “0.60-0.35” são impressas assim.
- Coberturas: aveia-preta usa a linha combinada “Barley/Oats/Wheat” (suposição, não é a mesma espécie; Kc de Oats na Tabela
12: NÃO EXTRAÍDO). Braquiária usa “Grazing Pasture” (suposição). Crotalária: sem linha nem substituto (NÃO
ENCONTRADO).
- Ajuste do Kc por umidade relativa mínima e vento (eq. 62) previsto pelo FAO-56 não foi aplicado. A tabela diária tem rh_pct
(RH2M) e u2_ms; a UR mínima diária que a eq. 62 usa NÃO ENCONTRADA em arquivo.
- Balanço hídrico (M4): chuva padrão (IMERG) menos ET0 × Kc, balde limitado pela CAD.
- Outras fontes FAO (nenhuma ingerida): GAEZ v5 (só SSP1-2.6, 3-7.0 e 5-8.5, sem SSP2-4.5; 5 modelos; uso comercial exige
licença FAO; serve de apoio); HWSD v2.2 (o solo do projeto vem de SoilGrids e SiBCS); FAOSTAT (HTTP 521 e 401); EcoCrop


---

<!-- Página 4 do PDF original -->

(HTTP 503); PyAEZ (MIT).
- Citação: Allen, R.G.; Pereira, L.S.; Raes, D.; Smith, M. (1998). Crop evapotranspiration: guidelines for computing crop water
requirements. FAO Irrigation and Drainage Paper 56. FAO, Roma. ISBN 92-5-104219-5. Cap. 6, Tabelas 11 e 12. © FAO 1998;
extrato mínimo com citação completa, só para uso educacional.
Ref: FAO §1 p.2, §2 p.3 (Tabela 11), §3 p.4 (Tabela 12), §4 p.5 (células NÃO LEGÍVEIS), §5 p.6 (por cultura e coberturas), §6 p.7 (ET0 e citação), §7 p.8
(demais fontes) · V3 §5.1 p.8, §11.2 (D4) p.26
## 7. Dados × módulos do plano (M1 a M12)

| Módulo | Dados que o alimentam | Estado dos dados |
| --- | --- | --- |
| M1 Tabela de culturas | FAO-56 Kc e estágios; ZARC (ciclo e janela); AGROFIT e<br>Embrapa (doenças) | parcial: Kc pendente; atributos botânicos e<br>doenças ausentes |
| M2 Matriz de compatibilidade | regras do usuário sobre a tabela do M1 | ausente (depende do M1) |
| M3 Calendário e encaixe pelo<br>ZARC | ZARC (4 433 linhas); calendário CONAB (mapeado, não<br>ingerido) | pronto |
| M4 Balanço hídrico | tabela diária (ET0, IMERG, ERA5-Land); CAD; Kc; SMAP como<br>apoio; INMET só valida chuva | pronto, exceto Kc (inicial NÃO LEGÍVEL em 3<br>linhas; coberturas sem Kc) |
| M5 Produtividade municipal | PAM; tabela diária; NDVI; ONI; solo | dados-base prontos; índices por safra não<br>calculados |
| M6 Cadeia de Markov do clima | IMERG; POWER e ERA5-Land sem correção; ONI; GDDP | dados prontos; nenhum estado calculado;<br>correção por quantis (D1) pendente |
| M7 Markov descritivo do<br>MapBiomas | MapBiomas C11; transições agrícolas 1985–2024 | pronto (só se sobrar tempo) |
| M8 Pontuação (filtros e critérios 0<br>a 1) | saídas de M1 a M4; pesos do usuário | ausente (pesos NÃO ENCONTRADO) |
| M9 Monte Carlo | saídas do M6; GDDP (33 modelos comuns) | dados prontos |
| M10 Simulador | M1 a M9 | ausente (não é dado) |
| M11 Interface offline | tabelas processadas no PC (Parquet somam 95,7 MB; CSV<br>complementares) | dados no PC; GDDP só em Parquet |
| M12 Bônus de preço, câmbio e<br>custo | yfinance (R098), PTAX (R094), custos CONAB (R091) | ausente, não iniciado |

Prazos do plano: até 11/11 D1–D6, M1–M4 e M8; até 12/11 M5, M6, M9, M10; até 13/11 M11 testado offline (M7 e M12 só se sobrar
tempo); 14 e 15/11 evento. Se atrasar, cortar nesta ordem: M12, M7, sensibilidade dos pesos no M9, random forest no M5. O estado de
execução do código de M1 a M12 é NÃO ENCONTRADO (src/ tinha só ingestão e inmet).
Ref: V3 §11.1 p.25, §11.3 p.27 · GR §1 p.1
## 8. O desafio, o que falta e o que usar

| Exigência do desafio | No plano | O que falta |
| --- | --- | --- |
| 3 ou mais rotações, incluindo a atual | coberto | M1–M3, M8, M10. A rotação atual vem do MapBiomas e da PAM (D5) |
| Por que foi sugerida; evidência | coberto | M8 (pesos pendentes); M4, M5 e M6 |
| Benefícios | parcial | M2 e M8; o texto do desafio cita nitrogênio, erosão e matéria orgânica |
| Lacunas de informação | falta | nenhum módulo lista lacunas por rotação: gerar lista fixa por cultura e dado na<br>saída do M10 |
| Riscos para revisão local | parcial | M9 cobre risco climático; falta o campo “revisar com agrônomo local” |
| Apoia, não substitui o agricultor | parcial | falta o aviso na interface (M11) e no slide |
| Incerteza | coberto | M9; viés conhecido do GDDP e da chuva entra como ressalva |
| Satélite versus medição em solo | coberto (só chuva) | 10 pluviômetros do INMET (2006–2025) |

Lacunas que dá para fechar com o que já está no PC
- Risco de geada: coluna tmin_c (POWER), 1981-01-01 a 2026-11-06, 16 746 dias por município, sem vazio. Mínimos: Cascavel
−3,15 °C; Toledo e Assis −2,10 °C. Futuro: tasmin do NEX-GDDP. O limiar de geada é decisão sua.
- Anomalias de umidade: sm_rootzone_m3m3 e sm_surface_m3m3 (SMAP L4) contra a média por dia do ano; base de só 11
anos.
- Balanço hídrico: prec_padrao_mm menos ET0 × Kc, limitado pela CAD; depende do Kc. NDVI por safra: ndvi_medio e
evi_medio agrupados pela janela da safra, filtrando frac_valida (o corte é decisão sua).
- Para a apresentação: mapa por município (limites, relevo, solo); linha do tempo (IMERG, NDVI, SMAP, ONI); slider de chuva e
temperatura (NEX-GDDP e fase do ENOS); ondas de calor e geada (tmax_c, tmin_c).
Recursos da lista do desafio que você ainda não ingeriu
- SE SOBRAR TEMPO: GRACE/GRACE-FO (2002-04-16 a 2026-08-16, lacuna em 2017 e 2018; boa figura de tendência, resolução
NÃO ENCONTRADO).
- SÓ MENCIONAR: ECOSTRESS (cobertura no recorte não validada), HLS/Landsat (~2,1 h de transferência por ano), VIIRS VI (4,2
GB por ano; o MOD13Q1 já cobre), GLDAS (39,7 GB por ano; emenda 2.0/2.1), SRTM (redundante com NASADEM, inferido),
Sentinel-2, FAO GAEZ v5.


---

<!-- Página 5 do PDF original -->

- Só dos EUA, não é lacuna: USDA Ag Data Commons, Web Soil Survey, Cropland Data Layer, PRISM, SSURGO/STATSGO2, NAIP,
NLCD, NLDAS, NWIS, AMS Market News, NASS QuickStats, LANDFIRE, CoCoRaHS (América do Norte), OpenET (oeste dos EUA).
GEDI: não está no kanban.
Ref: GR §1 p.1, §3 p.2, §4 p.2, §5 p.2, §6 p.2 · texto da aba Detalhes e Recursos do desafio, lido em 14/11/2026 (colado pelo usuário)
## 9. Pendências, riscos e o que a modelagem não pode assumir

| Item | Responsável | Situação |
| --- | --- | --- |
| Conferir as 25 linhas do Kc contra o PDF do FAO-56 e preencher pagina_pdf | usuário | 0 conferidas; 6 células NÃO LEGÍVEIS |
| Kc inicial de soja, milho grão e trigo de primavera; altura do trigo de inverno<br>em solos não congelados; região de 2 linhas da Tabela 11; Kc de Oats | usuário | ler no PDF |
| Gradiente de temperatura com a altitude (D3) | usuário | NÃO ENCONTRADO |
| Critério de “relevante” no D3 | usuário | NÃO ENCONTRADO: o plano não diz o<br>limite |
| UR mínima diária para a eq. 62 (D4) | usuário | NÃO ENCONTRADA na tabela diária |
| Pesos do M8 | usuário | NÃO ENCONTRADO |
| Dados bônus: yfinance (R098), PTAX (R094), CONAB custos (R091) | a definir | só depois do núcleo validado |
| Rotacionar credenciais coladas no chat (CDS, Earthdata, token); revogar a<br>chave de API do Google e guardar a conta de serviço fora de pastas<br>versionadas | usuário | ao fim do hackathon |
| DOI e citação formal da Coleção 11 do MapBiomas | a definir | NÃO ENCONTRADO |
| Testar ENOS × chuva × rendimento e comparar ONI v6 com RONI | modelagem | não feito |
| 37 recursos do kanban em andamento, sem verificação completa | a definir | ver V3 §10 |

O que a modelagem não pode assumir hoje
- Chuva de 1981 a 2005 sem validação por pluviômetro; estações fora dos municípios; POWER fora da comparação.
- IMERG depois de 2025-09-29 é provisório. Toledo e Assis compartilham a célula do POWER: temperatura, ET0 e chuva do POWER
são idênticas nos dois (Tmin idêntica nos 16 746 dias); só IMERG e ERA5-Land os diferenciam.
- Aveia-preta, braquiária e crotalária sem Kc próprio; Kc inicial de soja, milho e trigo de primavera NÃO LEGÍVEL; códigos de risco
do ZARC inferidos.
- POWER e ERA5-Land com chuva abaixo do IMERG; ET0 de 1981–83 com radiação estimada; temperatura e ET0 sem correção por
altitude; CMCC-CM2-SR5, tas do TaiESM1 e 3 modelos sem tasmax e tasmin; 2ª safra e ciclos do MapBiomas em beta.
Ref: V3 §11.4 p.27, §12 p.28, §8 p.19–21 · FAO §8 p.9 · GR §7 p.3
## 10. Se eu só tiver 2 horas
1. Fixar os parâmetros pendentes: gradiente e critério do D3, UR mínima da eq. 62, pesos do M8.
2. Conferir os Kc de soja, milho e trigo contra o PDF da FAO-56 e liberar o balanço hídrico (M4).
3. Montar a saída do M10 para 3 rotações, com a atual: por quê, evidência, benefício, lacunas e riscos.
4. Risco de geada: contar os dias abaixo do limiar na coluna tmin_c, por município, e mostrar o resultado (o limiar é decisão sua).
5. Colocar o aviso “apoia, não substitui o agricultor” e a incerteza na interface e no slide.
6. Usar os gráficos que já existem em validacao/ (satélite contra pluviômetro) como slide de evidência.
Ref: GR §8 p.3


---

<!-- Página 6 do PDF original -->

## Referências
Use esta parte para voltar à fonte. A primeira tabela diz em que página do documento original está cada assunto; a
segunda, em que arquivo de dados está o número.
### A. Preciso de… onde está

| Assunto | Documento e seção | Página |
| --- | --- | --- |
| Inventário completo dos conjuntos (22) | V3 §2 | 3–4 |
| Frequência, latência, última amostra, lacunas | V3 §3 | 5–6 |
| Divergências entre arquivos (IMERG, ERA5-Land, SMAP, NDVI, POWER, INMET) | V3 §3.1 | 6 |
| Linha do tempo dos conjuntos (figura) | V3 §4 | 7 |
| ET0 contra o Exemplo 18 do FAO-56 | V3 §5.1 · FAO §6 | 8 · 7 |
| Chuva POWER × IMERG × ERA5-Land | V3 §5.2 | 8–9 |
| Soja MapBiomas × PAM | V3 §5.3 | 9 |
| Faixas físicas e lacunas por fonte e ano | V3 §5.4–5.5 | 9–11 |
| GDDP 2021–2025 contra o observado; viés 1981–2014 | V3 §5.6–5.7 | 11–12 |
| Chuva contra os 10 pluviômetros do INMET (tabelas e figuras) | V3 §5.8 | 12–13 |
| Tabela dos 34 modelos do GDDP | V3 §6 | 14–15 |
| Regras que produzem 33, 30, 29 e 27 modelos; ressalvas | V3 §6 | 15–16 |
| Viés e descontinuidade por modelo (figura) | V3 §6 (Figura 11) | 17 |
| Problemas encontrados e como foram tratados | V3 §7 | 18 |
| Riscos e lacunas em aberto (credenciais, quebras de série, latência, escopo, INMET) | V3 §8 | 19–21 |
| Estado da execução e integridade dos arquivos | V3 §9 | 22 |
| Kanban por status e lista de recursos | V3 §10 | 23–24 |
| Dado → módulo (M1 a M12) | V3 §11.1 | 25 |
| Decisões D1 a D6: evidência e o que falta medir | V3 §11.2 | 26 |
| Prazos, ordem de corte, o que não assumir | V3 §11.3–11.4 | 27 |
| Pendências com responsável | V3 §12 | 28 |
| Tabela 11 do FAO-56 (duração dos estágios) | FAO §2 | 3 |
| Tabela 12 do FAO-56 (Kc e altura) | FAO §3 | 4 |
| Células NÃO LEGÍVEIS e linhas inferidas | FAO §4 | 5 |
| O que falta por cultura; coberturas | FAO §5 | 6 |
| Citação e licença do FAO-56; uso do Kc na modelagem | FAO §6 | 7 |
| Demais fontes FAO (GAEZ, HWSD, FAOSTAT, EcoCrop, PyAEZ) | FAO §7 | 8 |
| Pendências do FAO-56 | FAO §8 | 9 |
| Desafio × plano | GR §1 | 1 |
| Dados que já tenho e como usar | GR §2 | 1 |
| Mapeados e não ingeridos (decidir); dados só dos EUA | GR §3–4 | 2 |
| Lacunas fecháveis (geada, umidade, balanço, NDVI); ideias de apresentação | GR §5–6 | 2 |
| Pendências e riscos; “se eu só tiver 2 horas” | GR §7–8 | 3 |


---

<!-- Página 7 do PDF original -->

### B. Arquivos de dados de origem (onde está o número)

| Assunto | Arquivo |
| --- | --- |
| Tabela diária observada (POWER, IMERG, ERA5-Land,<br>SMAP) | data/processed/clima_observado_diario_municipio.csv |
| Manifesto de ingestão (períodos, linhas, sha256) | data/processed/manifesto_ingestao.csv |
| Chuva POWER × IMERG × ERA5-Land | data/processed/qc_chuva_validacao.csv |
| Chuva contra pluviômetros do INMET | validacao/inmet/inmet_comparacao_estacoes.csv; inmet_estacoes_series.csv;<br>inmet_estacoes_oeste_pr.csv |
| Soja MapBiomas × PAM | data/processed/qc_soja_mapbiomas_x_pam.csv |
| PAM (668 linhas, 1974–2025) | data/processed/pam_municipio_cultura_ano.csv |
| GDDP: modelos, viés, descontinuidade | data/processed/gddp_modelos_por_cenario.csv; qc_gddp_vies_historico_1981_2014.csv;<br>qc_gddp_descontinuidade_2014_2015.csv; qc_gddp_2021_2025_vs_observado.csv |
| Radiação por Hargreaves (ET0 1981–83) | data/processed/qc_power_rs_hargreaves.csv |
| Relevo por município | data/processed/relevo_municipio.csv |
| Kc e estágios do FAO-56 | data/processed/fao56_kc_culturas.csv (idêntico a mapeamento/fao56_kc_culturas.csv; notas<br>em .md) |
| ET0 contra o Exemplo 18 | validacao/et0_fao56_exemplo18.csv |
| Kanban | Field_Shift_Status.csv |
| Plano de modelagem (D1–D6, M1–M12, prazos) | docs/plano_modelagem.md |
| Dicionário de dados; riscos e lacunas; tabela mestre | data/dicionario_dados.md; mapeamento/riscos_e_lacunas.md;<br>mapeamento/tabela_mestre.csv |
| Gráficos | validacao/ingestao_*.png (linha do tempo, ET0, chuva, soja, faixas, lacunas, GDDP, INMET<br>painel e geral) |

### C. Fontes externas citadas nos documentos
- Allen, R.G.; Pereira, L.S.; Raes, D.; Smith, M. (1998). FAO Irrigation and Drainage Paper 56, Crop evapotranspiration. FAO, Roma.
ISBN 92-5-104219-5.
- Página do desafio: Space Apps 2026, “Adapting Farms with NASA Data” (abas Detalhes e Recursos),
https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/. Conteúdo lido em 14/11/2026 e colado
pelo usuário.
- Notícias do GPM (gpm.nasa.gov, data news) sobre o encerramento do IMERG Final V07 e a V08, citadas no V3 §8; NWS PIS 26-05
sobre o RONI, citado no V3 §8.
### D. Notas de conferência desta compilação
- Período da PAM: o V3 diz “1988 a 2025”; a tabela em disco tem área colhida, produção, rendimento e valor desde 1974. Os
dois estão certos para a área plantada (1988–2025). Resolvido pela conferência de 14/11 no arquivo em disco.
- Números arredondados: correlações aparecem com 2 ou 3 casas conforme a fonte (por exemplo, IMERG × INMET r diário 0,78
na tabela por estação e 0,784 no texto).
- Itens que dependem de você: o limiar de geada, a escolha do conjunto de modelos do GDDP (33, 30, 29 ou 27), o gradiente
de temperatura e os pesos do M8 não estão em nenhum arquivo e este PDF não os fixa.


---
