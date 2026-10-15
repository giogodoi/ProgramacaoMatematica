# Modelo PLI do problema dos blends: silos, misturadora obrigatória e porto seco

**Disciplina:** GCC118 Programação Matemática, Fases 2 e 3 (formulação exata, testes em solver e heurística).
**Código de apoio:** `cafe_blend.py` (instâncias, modelo exato, avaliador, força bruta), `cafe_blend_heur.py` (heurística) e `blends_nivel1.ipynb` (experimentos).
**Convenção:** fórmulas em \( \) e \[ \], como em `02_modelo_PLI_nivel1.md`.

## 1. Descrição do problema

Um **blend** é uma mistura de tipos de café em proporções fixas, por exemplo 10% do tipo 2, 25% do tipo 4 e 65% do tipo 8. Cada tipo fica armazenado em silos diferentes, em locais distintos. Para produzir um lote de blend, um veículo:

1. sai da **garagem**;
2. visita silos que guardam os tipos do blend e retira as quantidades exigidas pelas proporções (Etapa 1);
3. passa **obrigatoriamente** por uma **misturadora**, onde o blend é feito (Etapa 2);
4. entrega o lote em um **porto seco** escolhido pelo modelo e volta à garagem (Etapa 3).

Caminho de cada rota: `garagem → silos (ordem e escolha decididas) → misturadora → porto seco → garagem`.

O objetivo é minimizar o custo logístico total: veículo, deslocamento, tarifa de expedição dos silos, uso da misturadora, entrada no porto seco e penalidade por atraso no *cut-off* do recinto. Assim como no Nível 1, com receita fixa isso equivale a maximizar a margem.

## 2. Decisões de modelagem (pontos em aberto resolvidos)

| # | Ponto | Decisão | Justificativa |
|---|---|---|---|
| 1 | "TSPW" | B1 a B3: caminho TSP com duração máxima \(T_{max}\). B4 em diante: janelas de tempo (TSPTW). | Mantém a versão mínima verificável por força bruta. As janelas têm sentido real: horário de expedição dos armazéns, agendamento da misturadora e *cut-off* do recinto. |
| 2 | Vários silos por tipo | B1: um silo por tipo. B2 em diante: vários, com estoque \(e_s\) e tarifa \(p_s\). O modelo escolhe os silos e as quantidades. | Vira um **Traveling Purchaser Problem** (TPP): comprar itens em "mercados" com preço e oferta limitados, minimizando deslocamento mais compra (Ramesh, 1981; Laporte, Riera-Ledesma e Salazar-González, 2003). |
| 3 | Blends por viagem | **Um lote de blend por rota.** | Rastreabilidade e certificação do lote de exportação, sem risco de misturar blends no caminhão. |
| 4 | Misturadoras | B1 e B2: uma. B3 em diante: várias candidatas, com custo \(F_\mu\) e tempo de processamento \(\sigma_\mu\). | Mesmo padrão da escolha de porto seco do Nível 1. |
| 5 | Divisão do blend | Se \(W_b/(1-\rho) > Q\), o pedido é dividido **antes** do modelo em \(\lceil W_b/((1-\rho)Q)\rceil\) lotes com as mesmas proporções. | Cada lote continua sendo um blend válido. Lote padrão \(W = 19{,}2\) t = 1 contêiner de 320 sacas. |
| 6 | Veículos | O **mesmo veículo** faz as Etapas 1 a 3 numa rota única e espera na misturadora. | Coerente com o Nível 1. Separar coleta e entrega em veículos diferentes é a **decomposição** proposta como adaptação na Seção 8. |
| 7 | Mistura física | A mistura ocorre **na misturadora**. No caminhão, os tipos viajam separados em sacas ou *big bags*. | A capacidade conta só a massa total. A composição é garantida pelas retiradas \(r_s\). Há um fator opcional de quebra \(\rho\) no rebenefício. |
| 8 | Dados | Silos, estoques por tipo, misturadoras, tarifas e janelas são **sintéticos**. A rede (municípios, recintos, OSRM, diesel) é real na instância semi-real. | Conclusão da Fase 1 (`fase1/relatorio/relatorio_fase1.pdf`): esses parâmetros não são públicos. |

**Três consequências estruturais:**

- **Precedência pelo grafo.** O conjunto de arcos é em camadas: \(0 \to S\), \(S \to S\), \(S \to M\), \(M \to D\) e \(D \to 0\). Não existem arcos \(M \to S\), \(0 \to M\) nem \(S \to D\). Por isso "misturadora depois de todos os silos e antes do porto seco" vale sem nenhuma restrição extra.
- **Capacidade vira pré-checagem.** A carga de cada lote é fixa (\(W_b/(1-\rho)\)) e não depende da ordem de visita. Basta conferir \(W_b/(1-\rho) \le Q\), e as cargas acumuladas \(L_i\) do Nível 1 não são necessárias.
- **Etapa 3 degenerada.** Com um lote por rota, a Etapa 3 se reduz à escolha do arco \(\mu \to d\), com janela de tempo em \(d\).

## 3. Conjuntos

| Símbolo | Descrição |
|---|---|
| \(0\) | garagem |
| \(K\) | tipos de café (rótulos da Classificação Oficial Brasileira, por exemplo tipos 2, 4 e 8) |
| \(S\), \(S_k \subseteq S\) | silos; \(S_k\) são os silos que guardam o tipo \(k\) (cada silo guarda um tipo \(k(s)\)) |
| \(M\) | misturadoras candidatas |
| \(D\) | portos secos (recintos alfandegados) |
| \(B\) | lotes de blend (um por rota) |
| \(K_b = \{k: \pi_{bk} > 0\}\), \(S_b = \bigcup_{k \in K_b} S_k\) | tipos e silos relevantes para o lote \(b\) |
| \(A_b\) | arcos do lote \(b\): \(\{(0,s)\} \cup \{(s,s'): s \ne s'\} \cup \{(s,\mu)\} \cup \{(\mu,d)\} \cup \{(d,0)\}\), com \(s,s' \in S_b\) |

Silos de tipos que não entram no blend \(b\) nem aparecem em \(A_b\). Esse pré-processamento reduz o modelo sem perder soluções.

## 4. Parâmetros

| Símbolo | Unidade | Descrição | Origem |
|---|---|---|---|
| \(\pi_{bk}\) | fração | proporção do tipo \(k\) no blend do lote \(b\), com \(\sum_k \pi_{bk} = 1\) | pedido do cliente |
| \(W_b\) | t | quantidade do lote (padrão 19,2 t) | pedido |
| \(\rho\) | fração | quebra no rebenefício (padrão 0) | assumido |
| \(e_s\) | t | estoque disponível no silo \(s\) | sintético |
| \(p_s\) | R$/t | tarifa de expedição/aquisição no silo \(s\) | sintético |
| \(Q\) | t | capacidade do veículo | frota |
| \(c_{ij}\), \(t_{ij}\) | R$, h | custo e tempo do arco, com \(c_{ij} = \delta_{ij}(c^{km} + p\,g)\), como no Nível 1 | OSRM e ANP |
| \(\sigma_i\) | h | tempo de serviço (carga no silo, mistura, descarga no porto) | assumido |
| \([a_i, b_i]\) | h | janela de início de serviço (B4) | sintético |
| \(T_{max}\) | h | duração máxima da rota | jornada |
| \(f\) | R$ | custo fixo por veículo e rota | assumido |
| \(F_\mu\) | R$ | custo de uso da misturadora \(\mu\) por lote | sintético |
| \(F_d\), \(\tau_d\) | R$, R$/t | custo fixo de entrada e tarifa por tonelada no porto seco \(d\) | assumido |
| \(\beta\) | R$/h | penalidade por hora de atraso após o *cut-off* do porto seco | assumido |

Demanda do tipo \(k\) no lote \(b\): \(n_{bk} = \pi_{bk}\, W_b / (1-\rho)\).

## 5. Variáveis de decisão

| Variável | Domínio | Significado |
|---|---|---|
| \(x^b_{ij}\), \((i,j) \in A_b\) | \(\{0,1\}\) | arco percorrido pela rota do lote \(b\) |
| \(v^b_s\), \(s \in S_b\) | \(\{0,1\}\) | silo \(s\) visitado pelo lote \(b\) |
| \(w^b_\mu\), \(\mu \in M\) | \(\{0,1\}\) | misturadora usada pelo lote \(b\) |
| \(r^b_s\), \(s \in S_b\) | \([0, \min(e_s, Q)]\) | toneladas retiradas do silo \(s\) para o lote \(b\) |
| \(u^b_s\), \(s \in S_b\) | \([1, |S_b|]\) | posição do silo na rota (MTZ) |
| \(T^b_i\), \(i \in S_b \cup M \cup D\) | \([a_i, T_{max}]\) | início do serviço no nó \(i\) |
| \(\ell^b\) | \(\ge 0\) | atraso após o *cut-off* do porto seco |

O porto seco escolhido é \(y^b_d \equiv x^b_{d0}\): a variável de retorno indica o terminal usado.

## 6. Função objetivo

\[
\min Z = \sum_{b \in B} \Big[ f + \sum_{(i,j) \in A_b} c_{ij}\, x^b_{ij} + \sum_{s \in S_b} p_s\, r^b_s + \sum_{\mu \in M} F_\mu\, w^b_\mu + \sum_{d \in D} (F_d + \tau_d W_b)\, x^b_{d0} + \beta\, \ell^b \Big] \tag{1}
\]

Os trade-offs aparecem sozinhos:

- silo barato e distante contra silo caro e próximo (\(p_s\) contra \(c_{ij}\));
- misturadora barata e fora do caminho contra misturadora cara no caminho;
- porto seco barato e distante contra porto seco próximo.

## 7. Restrições (para cada lote \(b \in B\))

### 7.1 Estrutura da rota

\[
\sum_{s \in S_b} x^b_{0s} = 1 \tag{2}
\]

\[
\sum_{i:(i,s) \in A_b} x^b_{is} = v^b_s, \qquad \sum_{j:(s,j) \in A_b} x^b_{sj} = v^b_s \qquad \forall s \in S_b \tag{3}
\]

\[
\sum_{s \in S_b} x^b_{s\mu} = w^b_\mu, \qquad \sum_{d \in D} x^b_{\mu d} = w^b_\mu \quad \forall \mu \in M, \qquad \sum_{\mu \in M} w^b_\mu = 1 \tag{4}
\]

\[
\sum_{\mu \in M} x^b_{\mu d} = x^b_{d0} \qquad \forall d \in D \tag{5}
\]

As restrições (2) a (5) e o grafo em camadas garantem um único caminho `0 → silos → μ → d → 0`, com exatamente uma misturadora e um porto seco por rota.

### 7.2 Composição do blend e estoque

\[
\sum_{s \in S_k} r^b_s = n_{bk} \qquad \forall k \in K_b \tag{6}
\]

\[
r^b_s \le \min(e_s, Q)\, v^b_s \qquad \forall s \in S_b \tag{7}
\]

\[
\sum_{b \in B} r^b_s \le e_s \qquad \forall s \in S \quad \text{(estoque compartilhado entre lotes, B5)} \tag{8}
\]

A restrição (6) é a do blend: a quantidade de cada tipo é exatamente a proporção \(\pi_{bk}\) do lote. A capacidade \(\sum_s r^b_s = W_b/(1-\rho) \le Q\) é uma consequência de (6), conferida antes de resolver (`check_instance`).

### 7.3 Eliminação de subciclos (MTZ)

\[
u^b_j \ge u^b_i + 1 - |S_b|\,(1 - x^b_{ij}) \qquad \forall (i,j) \in A_b,\ i,j \in S_b \tag{9}
\]

### 7.4 Tempo, janelas e duração

Com \(T^b_0 = 0\), \(\sigma_0 = 0\) e \(\bar M = T_{max} + \max t_{ij} + \max \sigma_i\):

\[
T^b_j \ge T^b_i + \sigma_i + t_{ij} - \bar M\,(1 - x^b_{ij}) \qquad \forall (i,j) \in A_b,\ j \ne 0 \tag{10}
\]

\[
T^b_s \le b_s + \bar M(1 - v^b_s), \qquad T^b_\mu \le b_\mu + \bar M(1 - w^b_\mu) \tag{11}
\]

\[
T^b_d \le b_d + \ell^b + \bar M(1 - x^b_{d0}) \qquad \forall d \in D \quad \text{(janela flexível no recinto)} \tag{12}
\]

\[
T^b_d + \sigma_d + t_{d0} \le T_{max} + \bar M(1 - x^b_{d0}) \qquad \forall d \in D \tag{13}
\]

O limite inferior \(T^b_i \ge a_i\) permite esperar até a abertura da janela. Ao contrário do Nível 1, aqui um nó é visitado no máximo uma vez por lote, então um tempo \(T^b_i\) por nó e por lote é válido. Sem janelas (B1 a B3), basta \([a_i, b_i] = [0, T_{max}]\) e (10) a (13) só impõem a duração máxima. As restrições (10) também eliminam subciclos quando \(t_{ij} > 0\). O MTZ (9) é mantido porque fortalece a formulação nos níveis sem janelas.

## 8. Níveis do problema e adaptações

| Nível | O que muda | Classe | Decisões |
|---|---|---|---|
| **B1 (mínimo)** | 1 lote, 1 misturadora, 1 silo por tipo (3 a 5 silos), 2 portos secos, sem janelas. \(v\) e \(r\) ficam fixos | caminho TSP com destino em duas camadas | ordem dos silos e porto seco |
| B2 | vários silos por tipo, estoque \(e_s\), tarifa \(p_s\) | TPP | quais silos, quanto retirar, ordem, porto |
| B3 | várias misturadoras | TPP com escolha de ponto intermediário | mais a misturadora |
| B4 | janelas nos silos e na misturadora (duras) e *cut-off* flexível no porto seco | TPPTW | mais o horário |
| B5 | vários lotes e estoque compartilhado (8) | TPP com vários veículos | tudo, por lote |

**Tamanho do modelo** (por lote, com \(n_b = |S_b|\), \(\mu = |M|\), \(\delta = |D|\)):

| Item | Quantidade |
|---|---|
| Binárias \(x\) | \(n_b + n_b(n_b - 1) + n_b\mu + \mu\delta + \delta\) |
| Binárias \(v\), \(w\) | \(n_b + \mu\) |
| Contínuas \(r\), \(u\), \(T\), \(\ell\) | \(3n_b + \mu + \delta + 1\) |
| Restrições MTZ e de tempo | \(O(n_b^2)\) |

Exemplos medidos (`solve_blend`): o B3 com 3 tipos, 2 silos por tipo, 2 misturadoras e 2 portos tem 62 binárias e resolve em menos de 1 s. Com 4 tipos, 4 silos por tipo, 3 misturadoras, 3 portos e 3 lotes são 1.005 binárias: o HiGHS termina o limite de 60 s com gap de 9%, e a ILS encontra uma solução 4% melhor em cerca de 15 s.

**Adaptações justificadas para o tamanho real** (exigência do enunciado):

1. **Restrição de escopo:** instâncias diárias com os \(k\) silos mais próximos de cada tipo (poda de arcos, como a política "nearest" do Nível 1).
2. **Decomposição em dois estágios:** primeiro, um PL escolhe silos e quantidades (relaxando a rota pelo custo de desvio); depois, o roteamento é resolvido com o conjunto fixo, o que no B1 é um TSP pequeno. Separar coleta e entrega em veículos diferentes é outra decomposição natural (dois problemas ligados pela misturadora).
3. **Heurística** (Seção 9) para a instância completa, comparada ao exato onde ele ainda prova o ótimo.

## 9. Heurística da Fase 3 (`cafe_blend_heur.py`)

**Construção (`construct`).** Os lotes são processados em ordem decrescente de \(W_b\), e o estoque usado por um lote fica indisponível para os seguintes. Para cada misturadora \(\mu\):

1. **Seleção:** para cada tipo \(k\), ordenar os silos pelo custo por tonelada \(p_s + (c_{0s} + c_{s\mu} - c_{0\mu})/\min(e_s, n_{bk})\) e incluí-los até cobrir \(n_{bk}\).
2. **Retiradas (`allocate`):** dado o conjunto de silos, retirar primeiro dos de menor tarifa. Como o custo de deslocamento não depende das quantidades, essa alocação é ótima para o conjunto.
3. **Ordem:** inserção mais barata no caminho \(0 \to \dots \to \mu\), seguida de 2-opt.
4. **Porto seco:** enumeração exata de todos os \(d \in D\), com a propagação de tempo de `schedule`.

A melhor misturadora é mantida.

**Busca local VND (`local_search`)**, em primeira melhoria, nesta ordem de vizinhanças:

| Vizinhança | Movimento |
|---|---|
| 2-opt | inverte um trecho da sequência de silos |
| realocação | move um silo para outra posição |
| *swap-source* | troca um silo por outro do mesmo tipo ainda não visitado |
| inclusão | acrescenta um silo de um tipo do blend (troca deslocamento por tarifa menor) |
| remoção | retira um silo se os demais ainda cobrem a demanda |
| misturadora | troca a misturadora (o porto seco é reotimizado em todo movimento) |

Silos que ficam sem retirada são removidos da rota automaticamente. Violações de janela dura ou de \(T_{max}\) recebem penalidade de 10.000 por violação durante a busca. A solução final é verificada pelo avaliador independente.

**Metaheurística ILS (`ils`):** a perturbação embaralha um trecho da rota, troca um ou dois silos por outros do mesmo tipo ou troca a misturadora. Depois vem o VND, com aceitação estilo *simulated annealing* (\(T_0 = 2\%\) do custo, resfriamento 0,98). A função guarda o histórico (tempo, melhor custo) para o gráfico obrigatório heurística × exato.

## 10. Validação

1. **Força bruta (`brute_force`):** no B1 e no B3 com um silo por tipo, enumera ordens × misturadoras × portos. O PLI deve dar o mesmo custo. Isso está no autoteste de `cafe_blend.py`.
2. **Avaliador independente (`evaluate`):** recalcula o custo e confere estrutura, composição, estoque, capacidade, janelas e \(T_{max}\) de qualquer solução, exata ou heurística. O custo recalculado deve bater com o objetivo do solver.
3. **Heurística × exato:** a heurística nunca pode ficar abaixo de um ótimo provado. O autoteste de `cafe_blend_heur.py` confere isso nos níveis B1 a B5.
4. **Instâncias reduzidas:** o notebook `blends_nivel1.ipynb` resolve as instâncias semi-reais R1 a R5 (níveis B1 a B5) sobre a rede da Fase 1. Elas usam seis silos em municípios próximos de Varginha, as misturadoras de Três Pontas e Alfenas e os cinco recintos de MG, e comparam exato e heurística.
5. **Escalabilidade (próxima iteração):** aumentar tipos, silos e lotes e registrar variáveis, restrições, tempo e gap. `escalabilidade_blends.csv` traz uma primeira rodada, com instâncias sintéticas de 22 a 1.005 binárias.

## 11. Relação com o Nível 1

| Elemento | Nível 1 | Blends |
|---|---|---|
| Pontos visitados | todas as coletas | só os silos escolhidos |
| Produto | 1 produto | vários tipos com proporção fixa \(\pi_{bk}\) |
| Ponto obrigatório | nenhum | misturadora, garantida pelo grafo em camadas |
| Destino | 1 porto seco por rota, escolhido | 1 porto seco por rota, escolhido |
| Capacidade | carga acumulada \(L_i\) com big-M | pré-checagem (carga do lote é fixa) |
| Subciclos | carga \(L_i\) | MTZ e tempos \(T_i\) |
| Custo do arco | \(\delta_{ij}(c^{km} + p\,g)\) | idem, com \(p\) = P50 ANP-MG e circuidade 1,39 da Fase 1 |

## 12. Limitações

- Não há conflito de horário entre lotes na mesma misturadora: falta uma restrição disjuntiva de capacidade de processamento, que fica como extensão.
- O custo do arco não depende da carga transportada.
- Silos, estoques por tipo, misturadoras e janelas são sintéticos. A instância semi-real usa a rede real da Fase 1, mas escolhe ao acaso quais municípios têm silos.
- O blend é definido só por proporções de massa, sem atributos de qualidade (bebida, peneira, umidade) com faixas de tolerância. Isso seria uma extensão do tipo *pooling*, que é não linear.

## Referências

- Ramesh, T. (1981). Traveling purchaser problem. *Opsearch*, 18, 78–91.
- Laporte, G., Riera-Ledesma, J., Salazar-González, J.-J. (2003). A branch-and-cut algorithm for the undirected traveling purchaser problem. *Operations Research*, 51(6), 940–951.
- Miller, C. E., Tucker, A. W., Zemlin, R. A. (1960). Integer programming formulation of traveling salesman problems. *Journal of the ACM*, 7(4), 326–329.
