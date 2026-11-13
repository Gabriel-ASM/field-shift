# Dados de entrada

Cada perfil corresponde a uma área ou contexto homogêneo. O motor consome três JSONs já preparados e um manifesto para rastreabilidade. O perfil [example](example/) é sintético e serve para demonstrar a API. Os arquivos operacionais ficam em data/processed/, ignorados pelo Git.

| Arquivo | Campos |
|---|---|
| states.json | Lista com id, crop, phase, water, soil e recent_crops opcional |
| transitions.json | Lista com state, action, environment e counts. Cada chave em counts é um destino viável e seu valor é a contagem inteira observada. Contagens zero permitem destinos viáveis ainda não observados. A linha precisa ter ao menos uma observação |
| environment.json | Mapa de ano civil para 24 classes ambientais ordenadas, duas por mês. A preparação diária e a definição dos rótulos antecedem o carregamento |
| manifest.json | Perfil, natureza dos dados, origem, responsável, versão e frequência por arquivo. Manter unidades, datas, cobertura, resolução e indicadores de qualidade nos perfis operacionais |

As contagens e os rótulos ambientais devem usar a mesma classificação. Uma política recebe estado, quinzena e ações permitidas. O filtro de elegibilidade aplica calendário e outras restrições locais. O simulador reporta uma linha de transição ausente quando uma política alcança uma combinação sem suporte.

O método `MonteCarlo.compare` aceita uma função opcional de fluxo de caixa por hectare, chamada com a decisão, a ação, o ambiente realizado e o estado seguinte. Junto dela, informe a taxa anual como fração decimal. O motor desconta cada fluxo ao fim da quinzena e resume VPL mediano, P5, P95, média dos 5% piores VPLs e a frequência de superar a referência nos mesmos cenários. A preparação de preços, custos e balanços diários entra antes ou fora deste núcleo.
