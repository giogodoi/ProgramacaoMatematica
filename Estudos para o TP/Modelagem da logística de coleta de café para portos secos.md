# Modelagem da logística de coleta de café para portos secos

## Resumo executivo

Este documento especifica os dados e apresenta um rascunho matemático para otimizar a coleta de café em fazendas ou armazéns e sua entrega a portos secos ou outros recintos aduaneiros interiores. O problema é tratado como uma extensão do **Vehicle Routing Problem with Pickup and Delivery (VRPPD)**, com frota capacitada, múltiplos produtos, destinos alternativos, janelas de atendimento, custos de armazenagem e possibilidade de consolidação de cargas.

O objetivo recomendado é **minimizar o custo logístico total**, atendendo uma demanda mínima obrigatória. Quando a quantidade vendida e a receita são fixas, minimizar custos equivale a maximizar a margem operacional, pois `lucro = receita fixa − custo total`. Caso a receita varie com a escolha dos lotes, da qualidade, da quantidade ou do destino, essa equivalência deixa de valer e a formulação deve explicitamente maximizar lucro.

O principal trade-off é decidir entre: **entregar antecipadamente uma carga parcial em um terminal próximo** ou **continuar coletando, consolidar carga e seguir para um terminal potencialmente mais distante**. Escolher sempre o terminal mais próximo pode ser subótimo, pois ignora utilização da frota, custos fixos de viagem e terminal, tarifas, filas, capacidade e viagens futuras evitadas. A literatura mostra que atribuições flexíveis entre clientes e depósitos podem reduzir custos de roteamento e gerar melhor compartilhamento de capacidade em relação à regra do depósito mais próximo.[^1][^2]

## Escopo do problema

A proposta original define a otimização da coleta e distribuição de café entre armazéns de cooperativa e portos secos, admitindo diferentes tipos e qualidades, estoques distribuídos, coleta em múltiplos locais, capacidade dos caminhões e terminais, custos de transporte e armazenagem. Para esta versão, o escopo operacional sugerido começa na garagem ou base da frota, inclui coleta, deslocamento e entrega, e termina após a aceitação da carga pelo recinto aduaneiro interior.[^3]

Se o transporte do porto seco até um porto marítimo também for relevante, ele deverá ser representado em uma segunda etapa ou camada da rede. Misturar os dois trechos sem dados de transferência, modal ferroviário/rodoviário, contêineres e agenda portuária pode produzir uma função de custo incompleta.

### Premissas iniciais

- Existe uma quantidade mínima de café a ser entregue no horizonte de planejamento.
- A receita associada a essa quantidade é considerada fixa na formulação-base.
- As cargas podem ser coletadas em fazendas, cooperativas ou armazéns.
- Cada veículo pode visitar vários pontos de coleta.
- O solver escolhe a sequência das coletas e o terminal de destino.
- Na primeira versão, cada rota entrega em apenas um terminal.
- Todos os custos são convertidos para reais na mesma data-base.
- Todas as quantidades são convertidas para quilogramas ou toneladas.
- Distância é rodoviária, e não euclidiana.
- Tempo inclui viagem, serviço, espera e pausas operacionais.

### Por que a demanda é obrigatória

Uma formulação que apenas minimize custo, sem demanda mínima ou penalidade por não atendimento, escolherá racionalmente não usar caminhões e não coletar café. Para evitar essa solução trivial, o modelo deve usar pelo menos uma destas alternativas:

- Atendimento obrigatório de toda a demanda;
- Atendimento de uma quantidade mínima global;
- Penalidade elevada por tonelada não atendida;
- Maximização explícita de lucro, quando a coleta for opcional.

A formulação-base deste documento usa atendimento obrigatório, podendo incluir variável de falta apenas para diagnóstico de inviabilidade.

## Enquadramento matemático

O VRPPD clássico determina rotas para transportar requisições entre pontos de coleta e entrega, respeitando capacidade, pareamento e precedência. Quando há janelas de tempo, cada local deve ser visitado dentro do intervalo permitido; o veículo pode esperar se chegar antecipadamente, mas uma janela rígida impede atendimento após o fechamento.[^4][^5][^6][^7]

A aplicação cafeeira acrescenta:

- Múltiplos pontos de coleta;
- Múltiplos terminais de destino;
- Frota heterogênea;
- Lotes e qualidades diferentes;
- Tarifas não lineares de terminal;
- Estoque e disponibilidade temporal;
- Custo de combustível dependente do período e da região;
- Capacidade estática e vazão de recebimento dos terminais;
- Entrega parcial versus consolidação;
- Escolha flexível do terminal.

A literatura de roteamento multi-depósito mostra que considerar distância e “esforço de roteamento” conjuntamente pode gerar custo menor do que alocar cada atendimento ao depósito geograficamente mais próximo. Portanto, proximidade deve entrar como dado da matriz viária, não como uma regra que fixa o destino.[^2][^8]

## Decisões do modelo

O modelo deverá responder:

- Quais pontos de coleta serão visitados;
- Quanto de cada lote será coletado;
- Qual veículo realizará cada coleta;
- Em qual ordem os pontos serão visitados;
- Qual terminal receberá cada rota;
- Em que horário cada serviço começará;
- Quantos veículos serão acionados;
- Se é melhor descarregar uma porção menor no terminal próximo;
- Se é melhor visitar outras origens e consolidar em terminal mais distante;
- Se alguma demanda ficará não atendida, caso isso seja permitido mediante penalidade.

Essas decisões precisam ser tomadas de forma integrada. Resolver primeiro a escolha do terminal e depois as rotas pode bloquear combinações melhores; pesquisas sobre redes com regiões e depósitos distintos destacam que decisões inter-relacionadas tratadas conjuntamente superam esquemas estritamente sequenciais.[^9]

## Granularidade

A granularidade precisa ser coerente com a decisão:

| Planejamento | Oferta | Tempo | Combustível | Capacidade terminal |
|---|---|---|---|---|
| Diário | Estoque/lote por dia | Horários e minutos | Preço vigente ou semanal | Veículos/h e t/dia |
| Semanal | Lote e disponibilidade semanal | Janelas por dia | Média semanal | t/semana e agenda diária |
| Mensal | Volume agregado | Horas médias | Média mensal | t/mês |

Para estudar sequência de visitas, filas, jornada e trade-off de consolidação, recomenda-se planejamento diário ou semanal. Um modelo mensal agregado é apropriado para alocação de fluxos, mas não representa bem o roteamento físico de cada caminhão.

## Dados geográficos

### Estrutura da rede

A rede deverá conter:

- Nós de garagem ou bases de veículos;
- Nós de fazendas e pontos de coleta;
- Nós de cooperativas e armazéns;
- Nós de portos secos e CLIAs;
- Arcos rodoviários possíveis entre os nós;
- Opcionalmente, postos de abastecimento e portos marítimos.

Cada nó deve usar o ponto de acesso do caminhão. O centroide de uma fazenda pode ficar distante da entrada ou desconectado da rede viária, produzindo distância e duração incorretas.

### Fazendas

| Campo | Unidade/tipo | Uso |
|---|---:|---|
| `farm_id` | texto | Identificação anônima |
| `name_or_code` | texto | Referência operacional |
| `municipality_code` | código IBGE | Integração estatística |
| `property_geometry` | polígono | Mapeamento |
| `access_latitude` | grau decimal | Entrada da rota |
| `access_longitude` | grau decimal | Entrada da rota |
| `access_road_type` | categoria | Restrição veicular |
| `access_weight_limit` | t | Elegibilidade do caminhão |
| `pickup_window_start/end` | data-hora | Janela de coleta |
| `loading_resources` | categoria | Infraestrutura local |
| `fixed_service_time` | min | Entrada e preparação |
| `variable_loading_time` | min/t | Carregamento |

O SICAR disponibiliza consulta pública, download estruturado e geosserviços, com perímetros e informações cadastrais das propriedades. Entretanto, os dados públicos não substituem o cadastro operacional: não informam com confiabilidade estoque disponível, produção de café, qualidade, preço, ponto real de acesso ou disponibilidade para coleta.[^10][^11]

Quando não existirem dados por fazenda, a Produção Agrícola Municipal do IBGE pode sustentar instâncias agregadas por município. A PAM contém área, quantidade produzida, rendimento e valor de produção, e separa café arábica e canephora desde 2012. Produção municipal não deve ser apresentada como estoque de uma propriedade específica.[^12][^13]

### Armazéns

| Campo | Unidade/tipo | Uso |
|---|---:|---|
| `warehouse_id` | texto | Identificação |
| Coordenadas do acesso | graus decimais | Roteamento |
| Capacidade estática total | t | Limite físico |
| Capacidade disponível | t/período | Limite operacional |
| Estoque inicial por produto | t | Balanço |
| Taxa de recepção | t/h | Serviço e fila |
| Taxa de expedição | t/h | Carregamento |
| Custo de armazenagem | R$/t/dia | Função objetivo |
| Custo de entrada/saída | R$/t | Movimentação |
| Janelas de funcionamento | data-hora | Viabilidade |
| Compatibilidade | categorias | Produto/embalagem |
| Equipamentos | categorias | Capacidade operacional |

O SICARM/Conab permite consulta de unidades por empresa, código, município e coordenadas, incluindo situação cadastral e oferta de armazenagem. Cadastros e recadastramentos verificam capacidade estática, recepção, expedição, conservação e equipamentos.[^14][^15][^16]

### Portos secos e CLIAs

A lista oficial da Receita Federal deve identificar os terminais elegíveis. A Receita publica separadamente portos secos e Centros Logísticos e Industriais Aduaneiros, portanto o trabalho precisa declarar se “porto seco” será usado em sentido estrito ou como termo operacional abrangente para recintos interiores.[^17][^18][^19]

| Campo | Unidade/tipo | Uso |
|---|---:|---|
| `terminal_id` | texto | Chave interna |
| Código oficial do recinto | texto | Identificação regulatória |
| Classificação | categoria | Porto Seco, CLIA etc. |
| Operador | texto | Cadastro e tarifas |
| Coordenadas do portão | graus decimais | Roteamento |
| Produtos aceitos | lista | Compatibilidade |
| Embalagens aceitas | lista | Compatibilidade |
| Capacidade estática | t/sacas/TEU | Estoque simultâneo |
| Capacidade de recebimento | t/dia ou veículos/h | Fluxo diário |
| Capacidade disponível | t/período | Restrição real |
| Número de docas | inteiro | Atendimento simultâneo |
| Janela de entrega | data-hora | Roteamento temporal |
| Agendamento obrigatório | binário | Regra operacional |
| Tempo de fila | min/h | Custo e jornada |
| Tempo de descarga | min/veículo ou min/t | Programação |
| Tarifa de armazenagem | fórmula | Custo |
| Tarifa de movimentação | fórmula | Custo |
| Pesagem, inspeção e documentação | R$/processo | Custo fixo |
| Estadia | R$/veículo/h ou dia | Penalidade |
| Faturamento mínimo | R$/operação | Não linearidade |

Tarifas de terminais podem ser percentuais sobre FOB/CIF, por período, tonelada, metro cúbico ou contêiner, além de conter mínimos de faturamento e cobranças de balança. Por isso, a base deve armazenar fórmula, faixa, vigência e base de incidência, em vez de uma única coluna genérica de preço.[^20][^21][^22]

### Estradas e arcos

| Campo | Unidade/tipo | Uso |
|---|---:|---|
| `origin_id`, `destination_id` | texto | Chave do arco |
| `distance_road_km` | km | Custo de deslocamento |
| `travel_time_base_h` | h | Jornada e custo-hora |
| `travel_time_peak_h` | h | Cenário de congestionamento |
| `road_type` | categoria | Velocidade/restrição |
| `paved_share` | % | Consumo e risco |
| `road_condition` | índice/categoria | Ajuste operacional |
| `toll_cost` | R$/veículo | Custo direto |
| `toll_plazas` | lista | Auditoria |
| `height_limit` | m | Compatibilidade |
| `weight_limit` | t | Compatibilidade |
| `seasonal_restriction` | calendário | Viabilidade |
| `routing_profile` | texto | Caminhão/perfil |
| `source_date` | data | Versionamento |

A distância precisa ser calculada sobre a rede viária. O serviço de matriz do OSRM fornece distâncias e durações origem-destino das rotas calculadas. O DNIT disponibiliza dados da malha rodoviária federal, enquanto a ANTT oferece dados abertos das praças de pedágio com rodovia, quilômetro, município, sentido e coordenadas.[^23][^24][^25][^26][^27]

A matriz deverá ser direcionada, pois distância, tempo, pedágio e acesso podem mudar conforme o sentido. Cada cálculo deverá guardar data, fonte, perfil do veículo e versão da rede.

## Dados do café

O lote é a unidade recomendada, porque espécie, qualidade, embalagem, disponibilidade e valor podem variar dentro da mesma origem.

| Campo | Unidade/tipo | Uso |
|---|---:|---|
| `lot_id` | texto | Identificação |
| `pickup_node_id` | texto | Local de coleta |
| `product_id` | texto | Produto/classe |
| Espécie | arábica/canephora | Compatibilidade e preço |
| Forma | cru, coco, torrado etc. | Operação |
| Classificação/qualidade | categoria | Segregação e valor |
| Quantidade disponível | t e sacas | Limite de coleta |
| Peso por unidade | kg | Conversão |
| Volume/densidade | m³ ou kg/m³ | Capacidade volumétrica |
| Embalagem | saca/big bag/granel | Compatibilidade |
| Umidade | % | Qualidade |
| Data de disponibilidade | data-hora | Planejamento |
| Data-limite | data-hora | Prioridade |
| Lote divisível | binário | Coleta/entrega parcial |
| Mistura permitida | matriz binária | Consolidação |
| Preço de aquisição | R$/t | Extensão de lucro |
| Valor comercial | R$/t | Extensão de lucro/risco |
| Custo de carregamento | R$/t ou lote | Objetivo |
| Tempo de carregamento | min/t + fixo | Jornada |

O padrão oficial do café beneficiado cru contempla espécie, formato/granulometria, aroma e sabor, bebida, cor e qualidade. A norma da Conab para café em big bag inclui controle de umidade na recepção e expedição, o que justifica registrar umidade, embalagem e condição do lote.[^28][^29][^30]

## Demanda

| Campo | Unidade/tipo | Uso |
|---|---:|---|
| `demand_id` | texto | Identificação |
| Produto/qualidade | categoria | Compatibilidade |
| Quantidade mínima | t | Impede solução zero |
| Quantidade máxima | t | Evita excesso |
| Terminais elegíveis | conjunto | Destino flexível |
| Terminal obrigatório | identificador/nulo | Contrato específico |
| Data inicial | data-hora | Janela |
| Prazo final | data-hora | Serviço |
| Entrega parcial aceita | binário | Trade-off |
| Lote mínimo de entrega | t | Viabilidade econômica |
| Penalidade de falta | R$/t | Demanda flexível |
| Penalidade de atraso | R$/t/h | Janela flexível |

Uma demanda global permite que o solver escolha o terminal mais econômico. Uma demanda contratual específica deve fixar destino, quantidade e prazo.

## Frota

| Campo | Unidade/tipo | Uso |
|---|---:|---|
| `vehicle_id` | texto | Identificação |
| `vehicle_type` | texto | Classe |
| Base inicial/final | nó | Rota |
| Capacidade de peso | t | Restrição |
| Capacidade volumétrica | m³ | Restrição |
| Número de eixos | inteiro | Pedágio/frete |
| Tipo de carroceria | categoria | Compatibilidade |
| Produtos/embalagens aceitos | lista | Elegibilidade |
| Custo fixo | R$/rota ou dia | Ativação |
| Consumo vazio | L/km | Combustível |
| Consumo carregado | L/km | Combustível |
| Função consumo-carga | fórmula opcional | Maior precisão |
| Manutenção/pneus/depreciação | R$/km | Custo variável |
| Motorista em hora normal | R$/h | Tempo |
| Hora extra | R$/h | Jornada |
| Jornada máxima | h/dia | Restrição |
| Tempo máximo de rota | h | Restrição |
| Disponibilidade | calendário | Frota |
| Local de abastecimento | município/nó | Preço do diesel |
| Limpeza/preparação | R$/rota | Troca de produto |

O número de eixos influencia pedágio e os coeficientes do piso de frete. A metodologia da ANTT representa o piso da carga lotação por coeficiente de deslocamento multiplicado pela distância, somado ao coeficiente de carga e descarga.[^31][^32][^33]

## Dados de tempo

O tempo total de uma rota deverá separar:

- Deslocamento entre nós;
- Entrada e identificação;
- Pesagem;
- Amostragem e inspeção;
- Carregamento;
- Descarga;
- Documentação;
- Fila e espera;
- Intervalos do motorista;
- Retorno à garagem;
- Eventuais atrasos por período do dia.

Janelas rígidas tornam o serviço fora do horário inviável. Janelas flexíveis permitem atraso mediante penalidade. Formulações de PDPTW normalmente combinam conservação de fluxo, capacidade, propagação temporal, janelas e precedência.[^34][^4]

## Custos

### Transporte próprio

| Componente | Unidade/fórmula |
|---|---|
| Combustível | km × L/km × R$/L |
| Manutenção e pneus | km × R$/km |
| Depreciação | km × R$/km ou R$/dia |
| Seguro/licenciamento | parcela por dia/rota |
| Motorista | h × R$/h |
| Pedágio | soma por praça/classe/sentido |
| Custo fixo do veículo | R$/rota |
| Limpeza/preparação | R$/rota |
| Hora extra | h excedente × R$/h |
| Pernoite | R$/ocorrência |

### Frete contratado

Quando o transporte for terceirizado, devem ser registrados cotação, piso aplicável, pedágio, margem, estadia e itens incluídos. Não se deve somar o preço integral do frete contratado com todos os custos internos do veículo, pois isso gera dupla contagem. A regulamentação do piso também não incorpora automaticamente lucro, pedágio e todas as movimentações.[^35][^32]

### Coleta e armazenagem

- Taxa fixa por visita;
- Custo de carregamento por tonelada;
- Custo de pesagem;
- Secagem e beneficiamento, se aplicáveis;
- Armazenagem por tonelada e período;
- Seguro e quebra técnica;
- Expedição e braçagem.

A Conab publica tarifas separadas por serviço e unidade, confirmando que armazenagem, secagem, braçagem e demais operações não devem ser condensadas sem critério em um único custo.[^36][^37]

### Terminal

- Entrada e documentação;
- Pesagem;
- Descarga;
- Movimentação;
- Armazenagem;
- Inspeção;
- Utilização de equipamentos;
- Estadia;
- Faturamento mínimo;
- Taxa fixa por processo ou visita.

### Penalidades e risco

- Demanda não atendida;
- Atraso;
- Excesso de jornada;
- Permanência prolongada em trânsito;
- Perda de qualidade;
- Mistura incompatível;
- Cancelamento de agendamento;
- Capacidade reservada e não utilizada.

## Combustível

A ANP publica séries históricas semanais e mensais por abrangência nacional, regional, estadual e municipal, inclusive para óleo diesel. Os dados abertos e o painel permitem filtrar localidade, produto e período.[^38][^39][^40][^41]

### Estrutura da série

| Campo | Unidade/tipo |
|---|---|
| `period_start`, `period_end` | data |
| `frequency` | semanal/mensal |
| `state` | UF |
| `municipality` | texto/código IBGE |
| `fuel_type` | Diesel B S10/S500 etc. |
| `mean_price` | R$/L |
| `minimum_price` | R$/L |
| `maximum_price` | R$/L |
| `standard_deviation` | R$/L |
| `sample_size` | postos |
| `price_basis` | nominal/real |
| `reference_date` | data-base |
| `downloaded_at` | data |

### Tratamento recomendado

1. Escolher o diesel efetivamente usado pela frota.
2. Baixar 24 a 60 meses de dados semanais ou mensais.
3. Filtrar os municípios onde ocorre abastecimento.
4. Usar média estadual apenas quando faltar observação municipal, registrando a imputação.
5. Agregar para a frequência do modelo.
6. Corrigir monetariamente os valores quando comparar anos em termos reais.
7. Criar cenários baixo, base e alto a partir da distribuição observada.
8. Separar preço histórico, preço vigente e previsão.
9. Relacionar cada rota ao local provável de abastecimento.
10. Versionar o arquivo e a data de extração.

O consumo poderá ser linear por quilômetro na primeira versão. Uma extensão pode fazê-lo depender da carga transportada em cada arco, capturando a diferença entre veículo vazio, parcialmente carregado e cheio.

## Distância, tempo e gasto

As três dimensões não devem ser somadas diretamente com unidades incompatíveis. Distância e tempo devem gerar custos monetários, permanecendo também como indicadores operacionais.

| Dimensão | Entrada | Conversão econômica |
|---|---|---|
| Distância | km rodoviários | combustível + manutenção + depreciação + pedágio |
| Tempo | viagem + serviço + espera | motorista + hora extra + estadia + atraso |
| Quantidade | t por arco | consumo dependente da carga e custo por tonelada |
| Terminal | visitas e toneladas | fixo por processo + variável + armazenagem |

Como objetivo secundário, pode-se usar otimização lexicográfica: minimizar custo; entre soluções equivalentes, minimizar tempo; depois minimizar distância.

## Trade-off logístico

### Alternativa A: entrega antecipada

O veículo leva a carga já coletada ao terminal próximo, mesmo sem utilizar toda a capacidade. Essa política reduz tempo de trânsito da carga e pode diminuir risco de atraso, mas pode aumentar o número de viagens, processos, pesagens e descargas.

### Alternativa B: consolidação

O veículo ignora o terminal próximo, visita origens adicionais, aumenta sua ocupação e segue para outro terminal. Essa política pode diluir custos fixos e evitar uma viagem futura, mas aumenta distância, duração, exposição a filas e risco de ultrapassar janela ou jornada.

| Fator | Favorece entrega próxima | Favorece consolidação |
|---|---|---|
| Urgência | Alta | Baixa |
| Ocupação atual | Alta | Baixa/média |
| Capacidade residual | Pequena | Grande |
| Desvio para novas coletas | Grande | Pequeno |
| Volume adicional | Pequeno/incerto | Grande/confirmado |
| Custo fixo por visita | Baixo | Alto |
| Nova viagem futura | Não necessária | Evitada pela consolidação |
| Tarifa terminal distante | Alta | Baixa |
| Fila no terminal distante | Longa | Curta |
| Compatibilidade dos lotes | Baixa | Alta |
| Janela operacional | Apertada | Compatível |
| Risco de qualidade | Alto | Baixo/controlado |

### Critério marginal

Considere que um veículo está no ponto `i`, com carga atual `q`, capacidade `Q`, terminal próximo `d_1`, origens adicionais `S` e terminal distante `d_2`.

A entrega próxima custa:

\[
C^{prox}=C(i,d_1)+F_{d_1}+M_{d_1}(q)+C(d_1,g)+C^{futuro}(S)
\]

A consolidação custa:

\[
C^{cons}=C(i,S)+C^{coleta}(S)+C(S,d_2)+F_{d_2}+M_{d_2}(q+q_S)+C(d_2,g)+C^{risco}
\]

A consolidação é preferível quando:

\[
C^{cons}<C^{prox}
\]

A parcela `C^{futuro}(S)` é indispensável. Comparar apenas o deslocamento imediato favorece artificialmente o terminal próximo, pois ignora que as cargas ainda disponíveis precisarão de outro veículo ou viagem.

### Ganho líquido

\[
G=C^{viagens\ evitadas}+C^{fixos\ evitados}+C^{terminal\ evitado}-C^{desvio}-C^{tempo\ adicional}-C^{pedágio\ adicional}-C^{risco}
\]

Se `G > 0`, consolidar é economicamente vantajoso; se `G < 0`, entregar no terminal próximo é preferível. A decisão continua subordinada a capacidade, compatibilidade, demanda, prazo e janela.

### Política inicial

Recomenda-se permitir **um terminal por rota** e deixar o solver escolher o destino. Isso já captura a escolha entre terminal próximo e distante sem adicionar descargas intermediárias. Na segunda versão, poderão ser permitidas entregas parciais em vários terminais, adicionando balanço de carga após cada descarga e custo fixo por parada.

## Estrutura dos dados

| Tabela | Chave principal | Conteúdo |
|---|---|---|
| `nodes` | `node_id` | Tipo, município, coordenadas e acesso |
| `farms` | `farm_id` | Propriedade, infraestrutura e janela |
| `warehouses` | `warehouse_id` | Capacidade, estoque e custos |
| `lots` | `lot_id` | Produto, qualidade, quantidade e disponibilidade |
| `terminals` | `terminal_id` | Capacidade, janela, serviços e compatibilidade |
| `terminal_tariffs` | chave composta | Fórmulas tarifárias e vigência |
| `vehicles` | `vehicle_id` | Capacidade, consumo, custo e jornada |
| `vehicle_availability` | chave composta | Calendário da frota |
| `od_matrix` | origem/destino/cenário | Distância, duração, pedágio e restrições |
| `toll_plazas` | `plaza_id` | Local, sentido, classe e tarifa |
| `fuel_prices` | período/local/produto | Série ANP |
| `demands` | `demand_id` | Quantidade, prazo, destino e penalidade |
| `service_times` | nó/operação | Tempo fixo e variável |
| `storage_costs` | local/produto/período | Armazenagem e manuseio |
| `assumptions` | `parameter_id` | Valor, unidade, fonte e confiança |

No PostGIS, os nós podem ser `Point`, propriedades `Polygon/MultiPolygon` e vias `LineString/MultiLineString`. A matriz de custos deverá ser calculada sobre uma rede roteável, enquanto as geometrias servirão para mapeamento, auditoria e associação espacial.

## Fontes sugeridas

| Dado | Fonte primária | Limitação |
|---|---|---|
| Produção municipal | PAM/SIDRA IBGE | Não é estoque por fazenda[^12][^13] |
| Geometria rural | SICAR/CAR | Não informa lote comercial[^10][^11] |
| Lotes reais | Cooperativa/produtores | Dados privados |
| Armazéns | SICARM/Conab | Confirmar disponibilidade atual[^14][^15] |
| Recintos interiores | Receita Federal | Tarifas exigem consulta ao operador[^17][^18] |
| Rede federal | DNIT/SNV | Complementar vias locais[^27] |
| Matriz distância/tempo | OSRM/OSM ou API comercial | Validar acessos de caminhão[^23][^26] |
| Pedágio | Dados Abertos ANTT | Complementar tarifas por classe[^24][^25] |
| Diesel | ANP | Cobertura municipal variável[^38][^39] |
| Piso de frete | ANTT | Não representa sozinho todo preço comercial[^32][^33] |
| Armazenagem | Conab/operadores | Fórmulas heterogêneas[^36][^20] |
| Classificação do café | MAPA/Conab | Exige dados reais do lote[^28][^30] |
| Comércio exterior | Comex Stat | Município exportador não é origem produtiva exata[^42][^43] |

## Instância mínima viável

Para a primeira implementação:

- 10 a 30 pontos de coleta;
- 1 garagem;
- 2 ou 3 terminais;
- 2 tipos de caminhão;
- 1 produto ou 2 espécies;
- Horizonte diário ou semanal;
- Um terminal por rota;
- Demanda mínima obrigatória;
- Distância, duração e pedágio reais;
- Estoque e janela por origem;
- Capacidade e custo por veículo;
- Diesel da ANP;
- Custo fixo e variável de cada terminal;
- Capacidade de recebimento dos terminais;
- Retorno à garagem claramente definido.

## Rascunho matemático

### Conjuntos

- `N`: conjunto de todos os nós;
- `O ⊂ N`: pontos de coleta;
- `D ⊂ N`: terminais elegíveis;
- `B ⊂ N`: bases ou garagens;
- `K`: veículos;
- `P`: produtos ou classes de café;
- `T`: períodos;
- `A ⊂ N × N`: arcos viáveis;
- `O_p`: origens que possuem produto `p`;
- `D_p`: terminais compatíveis com produto `p`.

### Parâmetros geográficos e temporais

- `d_ij`: distância rodoviária do arco `(i,j)`, em km;
- `tau_ijt`: duração de viagem no arco `(i,j)` no período `t`, em horas;
- `a_i`, `b_i`: início e fim da janela no nó `i`;
- `s_ip`: tempo de serviço no nó `i` para o produto `p`;
- `wbar_i`: espera máxima admitida;
- `H_k`: duração máxima da rota do veículo `k`;
- `M`: constante suficientemente grande para linearização.

### Parâmetros de oferta e demanda

- `q_ipt`: quantidade do produto `p` disponível na origem `i` e período `t`;
- `dem_dpt`: demanda do produto `p` no terminal `d` e período `t`;
- `demMin_pt`: demanda global mínima do produto `p` no período `t`;
- `div_ip`: 1 se o lote pode ser dividido;
- `comp_ipk`: 1 se veículo `k` pode transportar o lote/produto de `i`;
- `comp_p d`: 1 se terminal `d` aceita produto `p`;
- `mix_pp'`: 1 se produtos/classes `p` e `p'` podem compartilhar o veículo.

### Parâmetros da frota

- `Q_k`: capacidade de peso do veículo `k`;
- `V_k`: capacidade volumétrica;
- `base(k)`: garagem do veículo `k`;
- `avail_kt`: 1 se o veículo está disponível;
- `f_k`: custo fixo de utilização;
- `g_k^0`: consumo vazio, em L/km;
- `g_k^1`: consumo carregado, em L/km;
- `c_k^km`: custo não combustível por km;
- `c_k^h`: custo do veículo/motorista por hora;
- `eixos_k`: número de eixos.

### Parâmetros de custo

- `fuel_rt`: preço do diesel na região `r` e período `t`;
- `toll_ijk`: pedágio do arco `(i,j)` para o veículo `k`;
- `c_i^pick`: custo variável de coleta no nó `i`, em R$/t;
- `F_i^pick`: custo fixo de visita/coleta;
- `c_d^mov(p)`: movimentação no terminal `d`, em R$/t;
- `F_d^visit`: custo fixo por entrada/processo no terminal;
- `c_dpt^stor`: armazenagem, em R$/t/período;
- `c_i^wait`: custo de espera, em R$/h;
- `c_i^late`: penalidade por atraso;
- `c_dpt^short`: penalidade por falta;
- `c_ip^quality`: custo de perda de qualidade por tempo, se modelado.

### Parâmetros de capacidade terminal

- `Cap_dt^static`: capacidade estática disponível;
- `Cap_dt^receive`: capacidade de recebimento no período;
- `Dock_dt`: número de docas ou atendimentos simultâneos;
- `minDrop_dp`: lote mínimo aceito;
- `maxVehicles_dt`: máximo de veículos recebidos.

### Variáveis binárias

- `x_ijkt = 1` se o veículo `k` percorre o arco `(i,j)` no período `t`;
- `u_kt = 1` se o veículo `k` é utilizado;
- `visit_ikt = 1` se o veículo `k` visita o nó `i`;
- `v_dkt = 1` se o veículo `k` escolhe o terminal `d`;
- `r_idpkt = 1` se a quantidade de `i,p` é destinada a `d` pelo veículo `k`;
- `served_ipt = 1` se o lote indivisível é atendido;
- `split_ipt = 1` se ocorre divisão permitida do lote.

### Variáveis contínuas

- `y_ipkt`: quantidade do produto `p` coletada em `i` pelo veículo `k`;
- `z_dpkt`: quantidade do produto `p` descarregada em `d` pelo veículo `k`;
- `L_ikt`: carga total do veículo após o nó `i`;
- `L_ipkt`: carga do produto `p` após o nó `i`;
- `B_ikt`: início do atendimento no nó `i`;
- `W_ikt`: tempo de espera;
- `Late_ikt`: atraso, se a janela for flexível;
- `Short_dpt`: quantidade não atendida;
- `Ride_ipkt`: tempo do lote em trânsito;
- `Fuel_ijkt`: combustível consumido no arco.

## Função objetiva

A estrutura geral é:

\[
\min Z = C^{fixo}_{frota}+C^{distância}+C^{combustível}+C^{tempo}+C^{pedágio}+C^{coleta}+C^{terminal}+C^{armazenagem}+C^{espera}+C^{penalidades}+C^{qualidade}
\]

Um rascunho expandido é:

\[
\begin{aligned}
\min Z =
&\sum_{k,t} f_k u_{kt} \\
&+\sum_{(i,j)\in A}\sum_{k,t} d_{ij}c_k^{km}x_{ijkt} \\
&+\sum_{(i,j)\in A}\sum_{k,t} fuel_{r(i),t}Fuel_{ijkt} \\
&+\sum_{(i,j)\in A}\sum_{k,t} toll_{ijk}x_{ijkt} \\
&+\sum_{(i,j)\in A}\sum_{k,t} \tau_{ijt}c_k^h x_{ijkt} \\
&+\sum_{i\in O}\sum_{p,k,t} c_i^{pick}y_{ipkt}
+\sum_{i\in O}\sum_{k,t}F_i^{pick}visit_{ikt} \\
&+\sum_{d\in D}\sum_{k,t}F_d^{visit}v_{dkt}
+\sum_{d\in D}\sum_{p,k,t}c_d^{mov}(p)z_{dpkt} \\
&+\sum_{d\in D}\sum_{p,k,t}c_{dpt}^{stor}z_{dpkt} \\
&+\sum_{i\in N}\sum_{k,t}c_i^{wait}W_{ikt} \\
&+\sum_{i\in N}\sum_{k,t}c_i^{late}Late_{ikt}
+\sum_{d,p,t}c_{dpt}^{short}Short_{dpt} \\
&+\sum_{i,p,k,t}c_{ip}^{quality}Ride_{ipkt}.
\end{aligned}
\]

A literatura usa objetivos de menor custo com custos variáveis de rota, custos fixos de veículos e custos operacionais adicionais. Para o trade-off, os termos fixos de veículo, visita à origem e entrada no terminal são indispensáveis: sem eles, a economia obtida ao evitar uma viagem ou processo adicional não será reconhecida.[^8][^4][^2]

### Consumo dependente da carga

Uma aproximação linear pode ser:

\[
Fuel_{ijkt} \geq d_{ij}\left[g_k^0+(g_k^1-g_k^0)\frac{L_{ikt}}{Q_k}\right]-M(1-x_{ijkt})
\]

Na primeira versão, pode-se usar consumo médio fixo `g_k`. Depois, a carga por arco poderá ajustar o consumo.

## Restrições

### Ativação da frota

Um veículo só percorre arcos se estiver usado e disponível:

\[
x_{ijkt}\leq u_{kt}\quad \forall(i,j),k,t
\]

\[
u_{kt}\leq avail_{kt}\quad \forall k,t
\]

### Saída e retorno

Cada veículo usado sai da base e retorna a ela:

\[
\sum_{j:(b,j)\in A}x_{bjkt}=u_{kt}\quad \forall k,t,\; b=base(k)
\]

\[
\sum_{i:(i,b)\in A}x_{ibkt}=u_{kt}\quad \forall k,t,\; b=base(k)
\]

### Conservação de fluxo

\[
\sum_{j:(i,j)\in A}x_{ijkt}-\sum_{j:(j,i)\in A}x_{jikt}=0
\quad \forall i\in N, k,t
\]

### Vinculação de visita

\[
\sum_{j:(i,j)\in A}x_{ijkt}=visit_{ikt}
\quad \forall i,k,t
\]

### Limite da oferta

\[
\sum_k y_{ipkt}\leq q_{ipt}
\quad \forall i\in O,p,t
\]

Para lote indivisível:

\[
\sum_k y_{ipkt}=q_{ipt}served_{ipt}
\]

### Coleta condicionada à visita

\[
y_{ipkt}\leq q_{ipt}visit_{ikt}
\quad \forall i,p,k,t
\]

### Compatibilidade veículo-produto

\[
y_{ipkt}\leq q_{ipt}comp_{ipk}
\quad \forall i,p,k,t
\]

### Balanço total

A quantidade descarregada deve igualar a quantidade coletada pelo veículo:

\[
\sum_{d\in D}z_{dpkt}=\sum_{i\in O}y_{ipkt}
\quad \forall p,k,t
\]

### Demanda

Para demanda por terminal:

\[
\sum_k z_{dpkt}+Short_{dpt}=dem_{dpt}
\quad \forall d,p,t
\]

Para demanda global com destino flexível:

\[
\sum_{d\in D_p}\sum_k z_{dpkt}\geq demMin_{pt}
\quad \forall p,t
\]

### Um terminal por rota

\[
\sum_{d\in D}v_{dkt}=u_{kt}
\quad \forall k,t
\]

### Descarga condicionada ao terminal

\[
z_{dpkt}\leq Q_kv_{dkt}
\quad \forall d,p,k,t
\]

### Compatibilidade terminal-produto

\[
z_{dpkt}\leq Q_k comp_{pd}
\quad \forall d,p,k,t
\]

### Entrega mínima no terminal

\[
\sum_p z_{dpkt}\geq minDrop_{d}v_{dkt}
\quad \forall d,k,t
\]

Essa restrição deve ser usada somente se houver mínimo operacional real; caso contrário, ela pode impedir entregas economicamente válidas.

### Capacidade do veículo

\[
0\leq L_{ikt}\leq Q_k
\quad \forall i,k,t
\]

Para cada arco utilizado, a carga evolui após coleta ou descarga:

\[
L_{jkt}\geq L_{ikt}+\sum_p y_{jpkt}-\sum_p z_{jpkt}-M(1-x_{ijkt})
\]

\[
L_{jkt}\leq L_{ikt}+\sum_p y_{jpkt}-\sum_p z_{jpkt}+M(1-x_{ijkt})
\]

A literatura de PDPTW exige que a carga seja atualizada ao longo da rota e nunca ultrapasse a capacidade do veículo.[^4][^34]

### Capacidade volumétrica

Se `vol_p` for volume por tonelada:

\[
\sum_p vol_p L_{ipkt}\leq V_k
\quad \forall i,k,t
\]

### Capacidade do terminal

\[
\sum_{p,k}z_{dpkt}\leq Cap_{dt}^{receive}
\quad \forall d,t
\]

Se houver estoque no terminal:

\[
Inventory_{dpt}=Inventory_{dp,t-1}+\sum_k z_{dpkt}-Outbound_{dpt}
\]

\[
\sum_p Inventory_{dpt}\leq Cap_{dt}^{static}
\]

### Limite de veículos no terminal

\[
\sum_k v_{dkt}\leq maxVehicles_{dt}
\quad \forall d,t
\]

### Propagação de tempo

\[
B_{jkt}\geq B_{ikt}+s_i+W_{ikt}+\tau_{ijt}-M(1-x_{ijkt})
\]

### Janelas rígidas

\[
a_i visit_{ikt}\leq B_{ikt}\leq b_i+M(1-visit_{ikt})
\]

### Janelas flexíveis

\[
Late_{ikt}\geq B_{ikt}-b_i
\]

\[
Late_{ikt}\geq 0
\]

### Espera

Se a chegada ocorrer antes da abertura, `W_ikt` absorve a diferença. O modelo deve evitar contar a espera duas vezes na propagação temporal.

### Precedência

Toda carga deve ser coletada antes de sua descarga. Uma forma temporal é:

\[
B_{dkt}\geq B_{ikt}+s_i+travelLowerBound_{id}-M(1-r_{idpkt})
\]

A precedência e o pareamento entre coleta e entrega são características centrais de problemas pickup-and-delivery.[^5][^6][^44]

### Atribuição origem-terminal

\[
y_{ipkt}\leq q_{ipt}\sum_{d\in D_p}r_{idpkt}
\]

\[
r_{idpkt}\leq v_{dkt}
\]

Quando houver apenas um terminal por rota, a segunda restrição vincula automaticamente todas as coletas do veículo ao mesmo destino.

### Jornada máxima

\[
ReturnTime_{kt}-StartTime_{kt}\leq H_k+Overtime_{kt}
\]

Hora extra pode ser proibida ou penalizada.

### Eliminação de subciclos

Além das restrições temporais, podem ser usadas restrições MTZ ou cortes de conectividade. Em muitos modelos com tempos estritamente positivos, a propagação temporal ajuda a eliminar subciclos, mas isso deve ser verificado na formulação implementada.[^34][^4]

### Incompatibilidade entre produtos

Para produtos `p` e `p'` incompatíveis:

\[
Carry_{pkt}+Carry_{p'kt}\leq 1
\quad \text{se } mix_{pp'}=0
\]

Uma implementação mais simples pode pré-processar veículos e lotes compatíveis, removendo combinações inviáveis.

## Como o trade-off emerge

Não é necessário criar uma regra “se passar perto, descarregue”. O trade-off surgirá da combinação dos parâmetros e variáveis:

- `v_dkt` permite escolher o terminal;
- `y_ipkt` permite escolher volumes adicionais;
- `x_ijkt` define o desvio para outras origens;
- `f_k` captura o custo de outra viagem;
- `F_d^visit` captura o custo fixo de outra entrada/descarga;
- `c_d^mov` e `c_d^stor` comparam terminais;
- `tau_ijt` e `c_k^h` monetizam o tempo adicional;
- `toll_ijk` captura pedágios;
- `H_k`, janelas e capacidades garantem viabilidade;
- `c^quality` penaliza permanência excessiva;
- A demanda obrigatória faz o modelo considerar também a viagem futura necessária para cargas não coletadas.

A flexibilidade de atribuição pode gerar simultaneamente benefício de roteamento e compartilhamento de capacidade. Entretanto, o terminal mais distante só será escolhido quando a redução em custos fixos, viagens futuras, tarifas ou frota superar o desvio e o custo temporal.[^1]

## Cenários experimentais

| Cenário | Regra |
|---|---|
| Próximo obrigatório | Cada origem usa o terminal elegível mais próximo |
| Consolidação mínima | Entrega apenas após atingir determinado nível de ocupação |
| Destino flexível | Solver escolhe rota e terminal pelo custo total |
| Flexível com tempo | Inclui janela, fila e jornada |
| Flexível com qualidade | Inclui tempo em trânsito e incompatibilidade |
| Múltiplas descargas | Permite terminais diferentes na mesma rota |

Devem ser testados preços de diesel baixo, base e alto com base na série ANP, além de variações em demanda, capacidade, fila, custo fixo terminal e disponibilidade de veículos. Limiares de ocupação podem ser comparados como políticas gerenciais, mas não devem ser declarados ótimos sem solução e análise de sensibilidade.

## Indicadores

- Custo total;
- Custo por tonelada entregue;
- Custo por rota;
- Quilômetros totais;
- Quilômetros vazios;
- Tonelada-quilômetro transportada;
- Tempo de viagem;
- Tempo de serviço;
- Tempo de espera;
- Número de veículos usados;
- Número de rotas;
- Número de coletas;
- Número de descargas;
- Ocupação média ponderada por quilômetro;
- Quantidade entregue no prazo;
- Demanda não atendida;
- Tempo médio do lote em trânsito;
- Utilização de cada terminal;
- Economia da atribuição flexível contra o terminal mais próximo.

A ocupação média deve considerar tonelada-quilômetro efetiva sobre tonelada-quilômetro disponível; medir somente a carga no momento da descarga pode ocultar longos trechos vazios ou parcialmente carregados.

## Validação

Antes de resolver:

- Validar coordenadas e conexão à rede viária;
- Confirmar que todos os arcos têm distância e tempo;
- Padronizar unidades e data-base monetária;
- Verificar se oferta compatível cobre a demanda;
- Verificar se frota e jornada tornam a demanda viável;
- Confirmar capacidade estática e capacidade de recebimento;
- Validar pedágio por sentido e número de eixos;
- Verificar conversão entre km/L e L/km;
- Confirmar a base de tarifas percentuais;
- Evitar dupla contagem entre frete e custo próprio;
- Impedir solução zero;
- Verificar continuidade, capacidade e precedência;
- Comparar algumas rotas com mapa e cálculo manual;
- Comparar custos com cotações ou viagens observadas.

## Etapas de implementação

1. Delimitar região, horizonte e terminais elegíveis.
2. Cadastrar nós e pontos de acesso.
3. Construir matriz direcionada de distância, duração e pedágio.
4. Cadastrar lotes, disponibilidade, qualidade e janela.
5. Definir demanda mínima e terminais compatíveis.
6. Cadastrar frota, capacidade, consumo, jornada e custos.
7. Importar série histórica da ANP e criar cenários.
8. Cadastrar tarifas e capacidades de armazéns e terminais.
9. Implementar o modelo-base com um terminal por rota.
10. Validar em instância pequena resolvível manualmente.
11. Executar os cenários de terminal próximo e destino flexível.
12. Acrescentar descarga parcial em vários terminais apenas depois da validação.

## Limitações

Dados públicos de produção agrícola normalmente estão agregados por município e não substituem estoques reais de fazendas. Tempos calculados por serviços de roteamento podem não representar filas, clima, safra ou restrições locais. Capacidades nominais de armazéns e terminais não equivalem necessariamente à capacidade disponível no dia. Tarifas podem depender de contrato, valor aduaneiro, faixa, período e serviços específicos.

Todas as entradas deverão ter fonte, data, unidade, transformação e nível de confiança. Valores assumidos precisam ser separados dos observados, e resultados devem ser apresentados com análise de sensibilidade.

---

## References

1. [On the Benefits of Flexible Customer-to-Depot Assignments in ...](https://repub.eur.nl/pub/116065/ERS-2019-004-LIS.pdf)

2. [onlinelibrary.wiley.com · doi · absA solution approach for multi‐trip vehicle routing problems with ...](https://onlinelibrary.wiley.com/doi/abs/10.1002/net.22028)

3. [Programacao-Matematica.pdf](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/149864912/39833521-accc-491f-bbde-8ed11a871a7f/Programacao-Matematica.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Checksum-Mode=ENABLED&X-Amz-Credential=ASIA2F3EMEYESJZP4IGZ%2F20261011%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20261011T003243Z&X-Amz-Expires=2016&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEJn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIHC2KYsl%2BhC%2FspC0rszjyzkomGjNSVEx%2FOY1uFUWDo6IAiEAxF%2BOU9kUcU2JXM9pbnC4FVOHApbEWMKt32M5YxkWzWMqgAUIYBABGgw2OTk3NTMzMDk3MDUiDJYK03MVywJhAhjG%2BCrdBE62NiOugR3430ZvrIw5u4h12TOO1y%2Fy5DS%2FYhiuWXxAjZzQRvd6fd8osyp0h2YY4EP8SjYi7JarKBFRvvGIKK1ajfum%2B7u3eQwU5SwPi5Rgb0tJgk4IoXoRc5sL0z0OssteGUnOB9JDm%2FJ%2F3aeyoaYnx6MPULyw7UI6SXWsLWYZBsgEwwSovRWLRP7UQpp%2BADFLVDygAGH%2BkAHc2PRAMPIMAmkU97WUiEoK%2BnMdcfZsr5NVZIfvYuehtZfwM0fyGcNxlxC%2FZodIeJRjW2eFSoqcTaX5RSw9bJGnQj0ubBkSV95sUcnabccUd7IKh9s%2B%2F2hEeKLt9CdSULcj%2Bn%2BtUap33u%2F01ftt3eQ5Wm9pf%2B4BC2Z2kxbXqUvc1hPkunkl3UbNVPsOm%2FemKADFAZL2MmKsKMISK4QFDyAr9GkWBqse%2BUU%2BzmYI02LCiu9ukym7QELOMhPtGjBr%2BEsA3BR3k3mOeCR5EXxr%2BUWljKSeoLRi8SB30yQul5ihidlu%2BKm2hyKctulZFOOHga656WJASJi7GaXGieXHgFVIPK%2F3y%2B4sCwbU03CfOeQKE8Cgmb9Y%2Bmxm9T4bqgnJQQaElPd3X5BFoWRv%2FHapPZg%2F%2B09%2FD8cb8%2FeiSc4qg0zko13%2FFDv2sys5JoyfC1je5VG0EtF2k5TrmMsKK6r7dzfk6xA2zkwEPO8R66%2FR19KZ82xeEzXF8PNebN3Lus%2F3vbWMDMS1uX%2BJl81PVI6fEK1o1MLj9tKgkDv%2BVv%2FUnGVix8gsp1YBIfiaJHZiYv5pM9kuHOSuAfUUyw0hXNzkx6BJumTNMLimq9YGOpgBrCLTEucY3kZDNBuOVdmR1s7znkWHeetYZdRABTEhDitQc2V78zbt7p0jwZIh6I8hhKsWAo65ljd6mJeJyk0lrP40RU0uxjbFXDsWVa5GCro6%2Fa8TNM2zAIIBtMx3wnMrTf0CzF8MZYwoXoTz4JOcJXymK6zG8smaf45ArhQuc3ozl0kUZgwlikmFvxdqyKON2N%2FRDboJUqU%3D&X-Amz-SignedHeaders=host&x-id=GetObject&X-Amz-Signature=dde589e1444fd2e5b331b2b64e1a82299ee2073ece0cc4a79ac06653b025ca9d) - page-1 Fase 0 Proposta do Problema Tema Otimizao da logstica de coleta e distribuio de caf para port...

4. [A capacitated multi pickup online food delivery problem with time windows: a branch-and-cut algorithm](https://link.springer.com/article/10.1007/s10479-021-04145-6) - Online food delivery companies, nowadays, allow a customer to place an order for a combination of di...

5. [An Exact Algorithm for the Pickup and Delivery Problem with Time Windows | Operations Research](https://pubsonline.informs.org/doi/10.1287/opre.1100.0881) - The pickup and delivery problem with time windows (PDPTW) is a generalization of the vehicle routing...

6. [[PDF] A branch-and-price algorithm for the pickup and delivery problem ...](https://pure.tue.nl/ws/files/2480340/427429.pdf)

7. [extented-abstract.dvi](https://www.openscience.fr/IMG/pdf/iste_ro18v1n1_1.pdf)

8. [A solution approach for multi-trip vehicle routing problems ...](https://onlinelibrary.wiley.com/doi/full/10.1002/net.22028)

9. [The two-region multi-depot pickup and delivery problem](https://link.springer.com/article/10.1007/s00291-018-0534-2) - Logistics networks are constantly evolving such that new and more varied structures arise and need t...

10. [consulta.car.gov.br › aboutConsulta Pública - consulta.car.gov.br](https://consulta.car.gov.br/about)

11. [Consulta Pública - consulta.car.gov.br](https://consulta.car.gov.br/geoservices)

12. [Produção Agrícola Municipal (PAM) - sidra/ibge](https://sidra.ibge.gov.br/pesquisa/pam/tabelas)

13. [Produção Agrícola Municipal](https://biblioteca.ibge.gov.br/visualizacao/periodicos/66/pam_2025_v52_br_notas_tecnicas.pdf)

14. [Sistema de Cadastro Nacional de Unidades Armazenadoras](https://www.gov.br/conab/pt-br/atuacao/armazenagem/saiba-mais-sobre-o-cadastro) - O Sicarm permite, ainda, consultar a situação cadastral da Unidade Armazenadora quanto ao credenciam...

15. [Companhia faz cadastramento e recadastramento de unidades ...](https://www.gov.br/conab/pt-br/assuntos/noticias/companhia-faz-cadastramento-e-recadastramento-de-unidades-armazenadoras) - De hoje a 11 de agosto, a Companhia Nacional de Abastecimento (Conab) realizará visitas a unidades a...

16. [Operações de cadastro de armazéns seguem no estado ...](https://www.gov.br/conab/pt-br/assuntos/noticias/operacoes-de-cadastro-de-armazens-seguem-no-estado) - Entre os dias 1° e 4 de agosto, a Companhia Nacional de Abastecimento (Conab) realizará o cadastro d...

17. [Portos Secos — Receita Federal - Portal Gov.br](https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior/importacao-e-exportacao/recinto-aduaneiros/portos-secos)

18. [CLIAs - Centros Logísticos e Industriais Aduaneiros - Portal Gov.br](https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior/importacao-e-exportacao/recinto-aduaneiros/clias-centros-logisticos-e-industriais-aduaneiros)

19. [Recintos Aduaneiros — Receita Federal - Portal Gov.br](https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior/importacao-e-exportacao/recinto-aduaneiros)

20. [Grupo Porto Seco Centro-Oeste » Tabela de Preços](https://portal.portoseco.com.br/tabela-de-precos/)

21. [Porto Seco Midwest Group](https://portal.portoseco.com.br/en/price-list/)

22. [Tarifas](https://multiarmazens.com.br/tarifas/)

23. [General options - OSRM API Documentation](https://project-osrm.org/docs/v5.9.1/api/)

24. [Praça de Pedágio - Conjuntos de Dados - Portal de Dados ...](https://dados.antt.gov.br/pt_PT/dataset/praca-de-pedagio) - Informações sobre as praças de pedágio.

25. [Dados dos Praças de Pedágio](https://dados.antt.gov.br/dataset/praca-de-pedagio/resource/48ea27de-2df5-40a3-bab8-fe6bb6d1a529) - A geração e a inserção dos dados são transmitidas pelas concessionárias e salvas na rede da Superint...

26. [OSRM API Documentation](https://project-osrm.org/docs/v5.22.0/api/)

27. [Dataset - DNIT - Dados Abertos](https://servicos.dnit.gov.br/dadosabertos/dataset/) - Planilha com dados do Sistema Nacional de Viação (SNV), contendo o cadastro da malha rodoviária fede...

28. [INSTRUÇÃO NORMATIVA Nº 8, DE 11 DE JUNHO DE 2003](https://www.idrparana.pr.gov.br/sites/iapar/arquivos_restritos/files/documento/2020-07/cafebenef008_03.pdf)

29. [compendio-produtos-vegetais.pdf - Portal Gov.br](https://www.gov.br/agricultura/pt-br/assuntos/inspecao/produtos-vegetal/legislacao-programas-nacionais-e-seguranca-dos-alimentos-1/legislacao/compendios/compendio-produtos-vegetais.pdf)

30. [NORMA DE ARMAZENAGEM DE CAFÉ EM BIG BAG 30.109](https://www.gov.br/conab/pt-br/acesso-a-informacao/institucional/atos-normativos/normas-da-organizacao/operacoes/30-109_norma_de_armazenagem_cafe_big_bag_21-10-2025.pdf/@@download/file) - c) o processo de armazenagem de café deve abranger todos os procedimentos necessários à garantia da ...

31. [anttlegis.antt.gov.br › action › TematicaActionTABELA A - Transporte Rodoviário de Carga Lotação - anttlegis](https://anttlegis.antt.gov.br/action/TematicaAction.php?acao=abrirVinculos&cotematica=15971753&cod_menu=8719&cod_modulo=421) - ANTTlegis - Agência Nacional de Transportes Terrestres - ANTT

32. [anttlegis.antt.gov.br › action › ActionDatalegisRESOLUÇÃO Nº 5.867, DE 14 DE JANEIRO DE 2020](https://anttlegis.antt.gov.br/action/ActionDatalegis.php?acao=abrirTextoAto&link=S&tipo=RES&numeroAto=00005867&seqAto=000&valorAno=2020&orgao=DG/ANTT/MI&cod_modulo=421&cod_menu=8719) - ANTTlegis - Agência Nacional de Transportes Terrestres - ANTT

33. [ANTTlegis - Agência Nacional de Transportes Terrestres - ANTT](https://anttlegis.antt.gov.br/action/UrlPublicasAction.php?acao=abrirAtoPublico&num_ato=00006084&sgl_tipo=RES&sgl_orgao=DG/ANTT/MT&vlr_ano=2026&seq_ato=000&cod_modulo=623&cod_menu=9230) - ANTTlegis - Agência Nacional de Transportes Terrestres - ANTT

34. [QUBO Formulation of the Pickup and Delivery Problem ...](https://inspirehep.net/files/e50bd84c91334a3fc6dfca090cf96b8a)

35. [RESOLUÇÃO Nº 5.867, DE 14 DE JANEIRO DE 2020 - ANTTlegis](https://anttlegis.antt.gov.br/action/TematicaAction.php?acao=abrirVinculos&cotematica=20632116&cod_menu=7220&cod_modulo=392) - ANTTlegis - Agência Nacional de Transportes Terrestres - ANTT

36. [TABELA DE TARIFAS PARA UNIDADES ARMAZENADORAS ...](https://www.gov.br/conab/pt-br/atuacao/armazenagem/rede-armazenadora-da-conab/tarifas-de-armazenagem-da-conab/tarifas-de-armazenagem-08-2025/@@download/file)

37. [Tarifas de Armazenagem 09-2025.odt](https://www.gov.br/conab/pt-br/atuacao/armazenagem/rede-armazenadora-da-conab/tarifas-de-armazenagem-da-conab/tarifas-de-armazenagem-09-2025.pdf)

38. [Série histórica do levantamento de preços - Portal Gov.br](https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos) - Nesta seção estão disponibilizadas planilhas da série histórica do Levantamento de Preços, semanal e...

39. [Série Histórica de Preços de Combustíveis e de GLP](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis) - Em cumprimento às determinações da Lei do Petróleo (Lei nº 9478/1997, artigo 8º), a ANP acompanha os...

40. [ANP lança painel dinâmico de preços de combustíveis e ...](https://www.gov.br/anp/pt-br/canais_atendimento/imprensa/noticias-comunicados/anp-lanca-painel-dinamico-de-precos-de-combustiveis-e-derivados)

41. [Levantamento de Preços de Combustíveis (últimas semanas ...](https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas) - Série histórica do Levantamento de Preços (nacional, regional, estadual e municipal) ... Preços médi...

42. [Dados por Municípios - Comex Stat](https://comexstat.mdic.gov.br/pt/municipio) - Estão disponíveis dados mensais de exportação e importação, de 1997 ao ano atual. Os dados detalhado...

43. [Exportação - Comex Stat - Dados Gerais](https://comexstat.mdic.gov.br/pt/geral/111130) - Estão disponíveis dados mensais de exportação e importação, de 1997 ao ano atual. Este módulo aprese...

44. [Pickup and delivery problem with LIFO, time duration, and limited vehicle number](https://www.matec-conferences.org/articles/matecconf/pdf/2018/63/matecconf_imiec2018_07003.pdf)

