# Modelagem da logística de coleta de café para portos secos

O documento completo e referenciado foi produzido no relatório de pesquisa associado a esta conversa. Ele consolida a especificação dos dados, o trade-off entre entrega parcial e consolidação, a função objetiva, os parâmetros, as variáveis e as restrições.

## Escopo

O problema é modelado como uma extensão do VRPPD: veículos capacitados coletam lotes de café em fazendas ou armazéns e entregam a um porto seco ou recinto aduaneiro interior. O objetivo é minimizar o custo logístico total sujeito ao atendimento de uma demanda mínima.

## Dados essenciais

- Nós: garagem, fazendas, armazéns e terminais, com coordenadas do acesso rodoviário.
- Arcos: distância rodoviária, duração, pedágios, restrições de peso/altura e condições da via.
- Lotes: origem, espécie, qualidade, peso, volume, embalagem, umidade, disponibilidade e divisibilidade.
- Demanda: produto, quantidade mínima, prazo, terminais elegíveis, lote mínimo e penalidades.
- Frota: capacidade, eixos, carroceria, consumo, custo fixo, custo por km, custo-hora e jornada.
- Terminais: capacidade estática e de recebimento, janelas, filas, serviços, compatibilidade e tarifas.
- Combustível: séries históricas ANP por município/UF, produto e período, em uma mesma base monetária.
- Operação: tempos de carga, descarga, inspeção, pesagem, documentação, fila e espera.

## Trade-off

O modelo compara a entrega parcial no terminal próximo com a continuação da coleta e entrega consolidada em outro terminal. A consolidação compensa quando as viagens e custos fixos evitados superam o desvio, o tempo, o pedágio, a tarifa adicional e o risco operacional. A comparação deve incluir a viagem futura necessária para buscar cargas deixadas para trás.

## Função objetiva

Minimizar:

\[
Z = C_{frota}+C_{distancia}+C_{combustivel}+C_{tempo}+C_{pedagio}+C_{coleta}+C_{terminal}+C_{armazenagem}+C_{espera}+C_{penalidades}+C_{qualidade}
\]

## Variáveis principais

- `x[i,j,k,t]`: veículo percorre o arco.
- `u[k,t]`: veículo é utilizado.
- `visit[i,k,t]`: nó é visitado.
- `v[d,k,t]`: terminal é escolhido pela rota.
- `y[i,p,k,t]`: quantidade coletada.
- `z[d,p,k,t]`: quantidade descarregada.
- `L[i,k,t]`: carga após visitar o nó.
- `B[i,k,t]`: início do serviço.
- `W[i,k,t]`: espera.
- `Late[i,k,t]`: atraso.
- `Short[d,p,t]`: falta de atendimento.

## Parâmetros principais

- `d[i,j]`, `tau[i,j,t]`: distância e tempo.
- `q[i,p,t]`: oferta.
- `dem[d,p,t]`: demanda.
- `Q[k]`, `V[k]`: capacidade de peso e volume.
- `f[k]`, `cKm[k]`, `cH[k]`: custos do veículo.
- `fuel[r,t]`: preço do diesel.
- `toll[i,j,k]`: pedágio.
- `CapReceive[d,t]`, `CapStatic[d,t]`: capacidades do terminal.
- `a[i]`, `b[i]`, `s[i]`: janela e serviço.
- Custos de coleta, movimentação, armazenagem, espera, atraso, falta e qualidade.

## Restrições principais

- Ativação e disponibilidade dos veículos.
- Saída e retorno à garagem.
- Conservação de fluxo.
- Coleta condicionada à visita e limitada à oferta.
- Balanço entre coleta e descarga.
- Atendimento da demanda mínima.
- Um terminal por rota na versão inicial.
- Compatibilidade entre produto, veículo e terminal.
- Capacidade de peso e volume ao longo da rota.
- Capacidade estática e de recebimento dos terminais.
- Propagação temporal, janelas e jornada máxima.
- Precedência entre coleta e entrega.
- Eliminação de subciclos.
- Segregação de lotes incompatíveis.

## Implementação recomendada

Começar com 10 a 30 coletas, uma garagem, dois ou três terminais, dois tipos de caminhão, horizonte diário ou semanal e um terminal por rota. Comparar terminal mais próximo, consolidação por ocupação e destino flexível otimizado. Depois, acrescentar múltiplas descargas, incerteza, filas e perda de qualidade.
