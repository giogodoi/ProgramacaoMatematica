# Modelo PLI do Nível 1: CVRP com escolha de porto seco

**Disciplina:** GCC118 Programação Matemática, Fase 2 (formulação exata e testes em solver).
**Código de apoio:** `cafe_vrp.py` e `nivel1_cvrp_portos_secos.ipynb`.
**Convenção:** fórmulas em \( \) e \[ \]. Em visualizadores que só aceitam `$`, substitua os delimitadores.

## 1. Descrição do problema

Uma frota homogênea parte de uma garagem, coleta café em pontos de oferta (municípios ou armazéns agregados) e entrega a um porto seco. O solver decide:

- em quantas rotas dividir as coletas;
- qual a sequência de coletas de cada rota;
- **qual porto seco recebe cada rota** (um único por rota).

Toda a oferta deve ser coletada e entregue. O objetivo é minimizar o custo logístico total. Com receita e demanda fixas, minimizar custo equivale a maximizar a margem operacional.

### Hipóteses do Nível 1

1. Um único produto, medido em toneladas.
2. Frota homogênea de capacidade \(Q\), com no máximo \(K\) veículos.
3. Cada coleta é visitada exatamente uma vez e a oferta \(q_i\) é coletada por inteiro (sem divisão de lotes).
4. A oferta total pode exigir várias rotas, e cada rota tem carga máxima \(Q\).
5. Cada rota segue o padrão garagem, coletas, **um** porto seco, garagem.
6. Os portos secos não têm limite de recebimento (isso entra no Nível 2).
7. Duração máxima de rota \(T_{max}\), incluindo viagem, serviço nas coletas, serviço no terminal e retorno.
8. Custos lineares na distância, mais custos fixos por veículo e por entrada no terminal.

## 2. Conjuntos

| Símbolo | Descrição |
|---|---|
| \(0\) | garagem (depósito) |
| \(O = \{1,\dots,n\}\) | pontos de coleta |
| \(D = \{n+1,\dots,n+m\}\) | portos secos elegíveis |
| \(N = \{0\} \cup O \cup D\) | todos os nós |
| \(A_0 = \{(0,i): i \in O\}\) | arcos de saída da garagem |
| \(A_O = \{(i,j): i,j \in O,\ i \neq j\}\) | arcos entre coletas |
| \(A_D = \{(i,d): i \in O,\ d \in D\}\) | arcos de coleta para terminal |
| \(A_R = \{(d,0): d \in D\}\) | arcos de retorno à garagem |
| \(A = A_0 \cup A_O \cup A_D \cup A_R\) | todos os arcos permitidos |

Não existem arcos \((0,d)\) (rota vazia), \((d,i)\) nem \((i,0)\): depois de coletar, o veículo precisa passar por um terminal antes de voltar.

## 3. Parâmetros

| Símbolo | Unidade | Descrição | Fonte sugerida |
|---|---|---|---|
| \(q_i\) | t | oferta da coleta \(i\) | PAM/IBGE (agregada) ou dado da cooperativa |
| \(Q\) | t | capacidade do veículo | especificação da frota |
| \(K\) | veículos | frota máxima | dado da cooperativa |
| \(\delta_{ij}\) | km | distância rodoviária do arco \((i,j)\) | OSRM/OpenStreetMap |
| \(t_{ij}\) | h | tempo de viagem do arco \((i,j)\) | OSRM/OpenStreetMap |
| \(s_i\) | h | tempo de serviço (carga) na coleta \(i\) | estimativa |
| \(s_d\) | h | tempo de serviço (descarga e processos) no terminal \(d\) | operador |
| \(T_{max}\) | h | duração máxima da rota | jornada |
| \(c^{km}\) | R$/km | custo não combustível por km | estimativa |
| \(p\) | R$/L | preço do diesel | série ANP |
| \(g\) | L/km | consumo do veículo | especificação |
| \(c_{ij}\) | R$ | custo do arco: \(c_{ij} = \delta_{ij}\,(c^{km} + p\,g) + \text{pedágio}_{ij}\) | derivado |
| \(f\) | R$ | custo fixo por veículo usado | estimativa |
| \(F_d\) | R$ | custo fixo por entrada no terminal \(d\) | tarifa do operador |

No notebook, \(c_{ij}\) não inclui pedágio (instâncias sintéticas). Em dados reais, some o pedágio por arco e por número de eixos.

## 4. Variáveis de decisão

| Variável | Domínio | Significado |
|---|---|---|
| \(x_{ij}\), \((i,j) \in A_0 \cup A_O \cup A_D\) | \(\{0,1\}\) | 1 se algum veículo percorre o arco |
| \(x_{d0}\), \(d \in D\) | \(\{0,\dots,K\}\) inteiro | número de rotas que terminam no terminal \(d\) |
| \(L_i\), \(i \in O\) | \([q_i, Q]\) | carga acumulada do veículo após coletar em \(i\) |
| \(T_i\), \(i \in O\) | \([0, T_{max}]\) | instante em que o serviço em \(i\) termina |

A variável \(x_{d0}\) é inteira (e não binária) porque o mesmo terminal pode receber várias rotas.

## 5. Função objetivo

\[
\min Z = f \sum_{i \in O} x_{0i} \;+\; \sum_{(i,j) \in A} c_{ij}\, x_{ij} \;+\; \sum_{d \in D} F_d\, x_{d0} \tag{1}
\]

Os três termos são:

1. custo fixo de acionar veículos (cada rota sai da garagem uma vez);
2. custo de deslocamento (distância, combustível, manutenção);
3. custo fixo de cada entrada em um terminal.

O trade-off entre entregar no porto mais próximo e consolidar para um porto mais distante aparece sozinho: os termos \(f\) e \(F_d\) premiam rotas cheias e pouco numerosas, e o termo \(c_{ij}\) penaliza desvios.

## 6. Restrições

### 6.1 Atendimento e fluxo

Cada coleta tem exatamente um sucessor e um antecessor:

\[
\sum_{j:(i,j) \in A} x_{ij} = 1 \quad \forall i \in O \tag{2}
\]

\[
\sum_{j:(j,i) \in A} x_{ji} = 1 \quad \forall i \in O \tag{3}
\]

Conservação de fluxo nos terminais (tudo que entra sai para a garagem):

\[
\sum_{i \in O} x_{id} = x_{d0} \quad \forall d \in D \tag{4}
\]

Número de rotas igual nas saídas e nas chegadas da garagem, limitado pela frota:

\[
\sum_{i \in O} x_{0i} = \sum_{d \in D} x_{d0} \le K \tag{5}
\]

As restrições (2) a (5) garantem que cada rota é um caminho garagem, coletas, um terminal, garagem. Como os arcos que saem de \(d\) só vão para a garagem, **cada rota usa exatamente um porto seco**.

### 6.2 Capacidade (carga acumulada)

\[
q_i \le L_i \le Q \quad \forall i \in O \tag{6}
\]

\[
L_j \ge L_i + q_j - (Q + q_j)(1 - x_{ij}) \quad \forall (i,j) \in A_O \tag{7}
\]

\[
L_i \le q_i + (Q - q_i)(1 - x_{0i}) \quad \forall i \in O \tag{8}
\]

A restrição (7) propaga a carga ao longo da rota. A restrição (8) faz a carga começar em \(q_i\) na primeira coleta da rota. Essas restrições também eliminam subciclos que não passam pela garagem, porque \(q_j > 0\) torna a carga estritamente crescente em qualquer ciclo.

### 6.3 Duração da rota

\[
T_i \ge t_{0i} + s_i - T_{max}(1 - x_{0i}) \quad \forall i \in O \tag{9}
\]

\[
T_j \ge T_i + t_{ij} + s_j - (T_{max} + t_{ij} + s_j)(1 - x_{ij}) \quad \forall (i,j) \in A_O \tag{10}
\]

\[
T_i + t_{id} + s_d + t_{d0} \le T_{max} + (T_{max} + t_{id} + s_d + t_{d0})(1 - x_{id}) \quad \forall (i,d) \in A_D \tag{11}
\]

A restrição (11) usa a última coleta da rota \(i\) e exige que a viagem até o terminal, a descarga e o retorno caibam em \(T_{max}\). Ela não usa uma variável de tempo por terminal, porque vários veículos podem visitar o mesmo terminal em momentos diferentes (um tempo único por terminal tornaria o modelo infactível).

### 6.4 Domínio

\[
x_{ij} \in \{0,1\},\ (i,j) \in A_0 \cup A_O \cup A_D; \qquad x_{d0} \in \{0,1,\dots,K\},\ d \in D \tag{12}
\]

\[
L_i \in [q_i, Q],\quad T_i \in [0, T_{max}]\quad \forall i \in O \tag{13}
\]

### 6.5 Factibilidade mínima

O modelo só é factível se:

- \(q_i \le Q\) para toda coleta (sem divisão de lotes);
- \(\sum_i q_i \le K\,Q\);
- existe ao menos um terminal alcançável por rota dentro de \(T_{max}\).

Teste isso antes de rodar o solver.

## 7. Tamanho do modelo

Com \(n\) coletas e \(m\) terminais:

| Item | Quantidade |
|---|---|
| Variáveis binárias | \(n + n(n-1) + nm\) |
| Variáveis inteiras | \(m\) |
| Variáveis contínuas | \(2n\) (\(L_i\) e \(T_i\)) |
| Restrições de fluxo (2) a (5) | \(2n + m + 1\) |
| Restrições de carga (7) | \(n(n-1)\) |
| Restrições de tempo (10) | \(n(n-1)\) |
| Restrições de terminal (11) | \(nm\) |

O crescimento é quadrático em \(n\) (por causa de \(A_O\)). As restrições com big-M enfraquecem a relaxação linear, por isso o solver exato escala mal: o notebook mede tempo e número de variáveis para \(n\) de 4 a 10, e o ponto em que o limite de tempo estoura define quando a heurística da Fase 3 passa a ser necessária.

## 8. Como representar a política do "porto mais próximo"

Para comparar com a política ingênua, resolva o mesmo modelo com um conjunto de arcos reduzido. Seja \(\nu(i) = \arg\min_{d \in D} \delta_{id}\) o terminal mais próximo da coleta \(i\). Remova de \(A\):

- os arcos \((i,d)\) com \(d \neq \nu(i)\);
- os arcos \((i,j) \in A_O\) com \(\nu(i) \neq \nu(j)\).

Assim, uma rota só junta coletas com o mesmo terminal mais próximo e só entrega nele. A diferença entre os dois custos ótimos mede o valor da escolha flexível do terminal.

## 9. Extensão para o Nível 2 (tarifa por tonelada e capacidade do terminal)

Novos parâmetros: \(\tau_d\) (R$/t) e \(\text{Cap}_d\) (t por terminal no horizonte).

Nova variável: \(z_{id} \in [0, Q]\), a carga entregue em \(d\) por uma rota cuja última coleta é \(i\).

\[
z_{id} \le L_i,\qquad z_{id} \le Q\,x_{id},\qquad z_{id} \ge L_i - Q(1 - x_{id}) \quad \forall (i,d) \in A_D \tag{14}
\]

\[
\sum_{i \in O} z_{id} \le \text{Cap}_d \quad \forall d \in D \tag{15}
\]

Acrescente \(\sum_{(i,d) \in A_D} \tau_d\, z_{id}\) à função (1). Para que \(L_i\) seja exatamente a carga acumulada (e não só um limite inferior), inclua também a restrição \(L_j \le L_i + q_j + Q(1 - x_{ij})\) para \((i,j) \in A_O\), e \(L_i \ge q_i - Q(1-x_{0i})\) é redundante dada (6).

## 10. Roteiro de validação

1. Resolver à mão uma instância com \(n = 3\) e conferir o custo.
2. Conferir que cada coleta aparece uma única vez e que toda carga respeita \(Q\).
3. Conferir que nenhuma rota excede \(T_{max}\) (somando viagem, serviço e retorno).
4. Comparar a política flexível com a do porto mais próximo.
5. Aumentar \(n\) e registrar tempo, gap, número de variáveis e restrições.
6. Variar diesel, \(f\) e \(F_d\) e observar se o terminal escolhido muda.

## 11. Limitações

- Instâncias reais exigem preços e distâncias reais; os parâmetros do notebook são ilustrativos.
- Sem janelas de tempo, filas ou lotes divisíveis, o modelo ainda não é um VRPPD completo; isso fica para os níveis 3 e 4.
- Pontos de coleta agregados por município não representam estoques de fazendas individuais.
