"""Problema dos blends: garagem -> silos (tipos do blend) -> misturadora -> porto seco -> garagem.

Modelo PLI descrito em ``03_modelo_PLI_blends.md`` (niveis B1 a B5). Uma rota por lote de blend;
o mesmo veiculo faz coleta, mistura e entrega. O grafo e em camadas (0 -> S -> M -> D -> 0), entao
a precedencia "misturadora depois dos silos e antes do porto seco" vem dos arcos permitidos.

Instancias:
- ``make_blend_instance``: SINTETICA (coordenadas em km num plano), para validar o modelo.
- ``make_semireal_instance``: rede REAL da Fase 1 (matriz OSRM, portos secos de MG, diesel ANP)
  com estoques, tipos, silos e misturadoras SINTETICOS.
"""

import itertools, math, os, random, re, tempfile, time

import numpy as np
import pulp

TIPOS_COB = [2, 3, 4, 5, 6, 7, 8]   # tipos da Classificacao Oficial Brasileira usados como rotulos


# ----------------------------------------------------------------------------- instancias
def _blend_aleatorio(rng, n_types):
    """Proporcoes multiplas de 5% que somam 1, todas positivas."""
    while True:
        cortes = sorted(rng.sample(range(1, 20), n_types - 1))
        partes = [b - a for a, b in zip([0] + cortes, cortes + [20])]
        if min(partes) > 0:
            return {k: p / 20 for k, p in enumerate(partes)}


def _montar(nomes, coords, G, S, M, D, tipo, dist, t_arc, rng, *, n_types, n_lots, W, blends, rho, Q, c_km,
            diesel, cons, f_veh, F_mix, s_mix, F_port, tau, s_port, s_silo, price, tw, Tmax, beta, stock_slack,
            sintetica):
    lots = []
    for b in range(n_lots):
        pi = blends[b] if blends and b < len(blends) else (
            {0: 0.10, 1: 0.25, 2: 0.65} if (n_types == 3 and b == 0) else _blend_aleatorio(rng, n_types))
        lots.append(dict(W=W, pi=pi))
    need = {k: sum(l["pi"].get(k, 0) * l["W"] / (1 - rho) for l in lots) for k in range(n_types)}

    e, p = {}, {}
    for k in range(n_types):
        Sk = [s for s in S if tipo[s] == k]
        if len(Sk) == 1:
            e[Sk[0]] = need[k] * rng.uniform(1.2, 2.0)
        else:  # um silo sozinho as vezes basta, as vezes nao; o conjunto sempre basta
            raw = [rng.uniform(0.6, 1.6) for _ in Sk]
            fator = max(1.0, stock_slack / sum(raw))
            for s, x in zip(Sk, raw):
                e[s] = need[k] * x * fator
        for s in Sk:
            e[s] = round(e[s], 1)
            p[s] = round(rng.uniform(*price), 1)

    janela = {i: (0.0, Tmax) for i in range(len(nomes))}
    soft = set()
    if tw:
        for s in S:
            a = rng.choice([0.0, 0.5, 1.0, 1.5, 2.0, 3.0])
            janela[s] = (a, round(a + rng.uniform(4.0, 7.0), 1))   # horario de expedicao do armazem
        for m in M:
            janela[m] = (1.0, 11.0)
        for d in D:
            janela[d] = (0.0, round(rng.uniform(6.0, 9.0), 1))   # cut-off do recinto (flexivel)
            soft.add(d)

    serv = {G: 0.0}
    serv.update({s: s_silo for s in S})
    serv.update(dict(zip(M, s_mix)))
    serv.update(dict(zip(D, s_port)))
    return dict(sintetica=sintetica, nomes=nomes, coords=coords, G=G, S=S, M=M, D=D, tipo=tipo,
                tipos=list(range(n_types)), rotulo_tipo={k: f"tipo {rot}" for k, rot in enumerate(
                    [2, 4, 8] if n_types == 3 else TIPOS_COB[:n_types])},
                e=e, p=p, lots=lots, Q=Q, rho=rho, f_veh=f_veh, F_mix=dict(zip(M, F_mix)),
                F_port=dict(zip(D, F_port)), tau=dict(zip(D, tau)), serv=serv, janela=janela, soft=soft,
                Tmax=Tmax, beta=beta, dist=dist, t_arc=t_arc, c_arc=dist * (c_km + diesel * cons))


def make_blend_instance(n_types=3, silos_per_type=1, n_mix=1, n_ports=2, n_lots=1, tw=False, seed=1,
                        Q=30.0, W=19.2, blends=None, rho=0.0, area=120.0, speed=60.0, circuity=1.39,
                        c_km=2.8, diesel=6.01, cons=0.40, f_veh=350.0, F_mix=None, s_mix=None,
                        F_port=(120.0, 60.0), tau=(0.0, 0.0), s_port=(0.5, 1.0), s_silo=0.5,
                        price=(15.0, 40.0), Tmax=14.0, beta=200.0, stock_slack=1.2):
    """Instancia SINTETICA para validar o modelo (nao representa silos reais).

    W = 19,2 t (1 conteiner de 320 sacas); circuity = 1,39 e diesel = 6,01 R$/L vem da Fase 1
    (mediana OSRM/linha reta e P50 ANP-MG). Tipos rotulados pela COB (2, 4, 8, ...).
    """
    rng = random.Random(seed)
    G = 0
    S = list(range(1, n_types * silos_per_type + 1))
    M = list(range(S[-1] + 1, S[-1] + 1 + n_mix))
    D = list(range(M[-1] + 1, M[-1] + 1 + n_ports))
    tipo = {s: (s - 1) // silos_per_type for s in S}
    coords = [(area * 0.5, area * 0.1)]
    coords += [(rng.uniform(0, area), rng.uniform(area * 0.35, area)) for _ in S]
    coords += [(rng.uniform(area * 0.3, area * 0.7), rng.uniform(area * 0.2, area * 0.4)) for _ in M]
    base_d = [(area * 0.15, area * 0.05), (area * 0.9, area * 0.0)]
    coords += base_d[:n_ports] if n_ports <= 2 else \
        base_d + [(rng.uniform(0, area), rng.uniform(0, area * 0.15)) for _ in range(n_ports - 2)]
    nomes = ["G"] + [f"S{s}" for s in S] + [f"M{j+1}" for j in range(n_mix)] + [f"D{j+1}" for j in range(n_ports)]
    dist = np.array([[math.dist(a, b) * circuity for b in coords] for a in coords])
    F_mix = list(F_mix) if F_mix else [round(rng.uniform(120, 250), 0) for _ in M]
    s_mix = list(s_mix) if s_mix else [round(rng.uniform(1.0, 2.0), 1) for _ in M]
    F_port = list(F_port) + [round(rng.uniform(40, 150), 0) for _ in range(n_ports - len(F_port))]
    tau = list(tau) + [0.0] * (n_ports - len(tau))
    s_port = list(s_port) + [0.75] * (n_ports - len(s_port))
    return _montar(nomes, coords, G, S, M, D, tipo, dist, dist / speed, rng, n_types=n_types, n_lots=n_lots,
                   W=W, blends=blends, rho=rho, Q=Q, c_km=c_km, diesel=diesel, cons=cons, f_veh=f_veh,
                   F_mix=F_mix[:n_mix], s_mix=s_mix[:n_mix], F_port=F_port[:n_ports], tau=tau[:n_ports],
                   s_port=s_port[:n_ports], s_silo=s_silo, price=price, tw=tw, Tmax=Tmax, beta=beta,
                   stock_slack=stock_slack, sintetica="SINTETICA")


def make_semireal_instance(n_types=3, silos_per_type=2, mixers=("Três Pontas", "Alfenas"), n_lots=1, tw=False,
                           seed=1, dados=None, Q=30.0, W=19.2, blends=None, rho=0.0, c_km=2.8, diesel=None,
                           cons=0.40, f_veh=350.0, F_mix=(180.0, 150.0), s_mix=(1.5, 1.5),
                           F_port=None, tau=None, s_port=None, s_silo=0.5, price=(15.0, 40.0), Tmax=16.0,
                           beta=200.0, stock_slack=1.2):
    """Rede REAL da Fase 1 com parametros de blend SINTETICOS.

    Reais: garagem (Varginha), municipios produtores, 5 recintos alfandegados de MG, distancias e
    tempos OSRM, diesel P50 ANP-MG. Sinteticos: quais municipios tem silo de cada tipo, estoques,
    tarifas, misturadoras (em municipios-polo), janelas.
    """
    import pandas as pd
    dados = dados or os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados", "processados")
    nos = pd.read_csv(os.path.join(dados, "osrm_nos.csv"))
    dk = pd.read_csv(os.path.join(dados, "osrm_dist_km.csv"), index_col=0)
    th = pd.read_csv(os.path.join(dados, "osrm_tempo_h.csv"), index_col=0)
    if diesel is None:
        an = pd.read_csv(os.path.join(dados, "anp_diesel_mg_semanal.csv"))
        diesel = float(an[an["produto"] == "OLEO DIESEL S10"]["preco_medio"].tail(104).median())
    rng = random.Random(seed)
    col = nos[nos["tipo"] == "coleta"]
    mix_ids = [col[col["nome"] == m]["no"].iloc[0] for m in mixers]
    candidatos = [c for c in col["no"] if c not in mix_ids]
    silo_ids = rng.sample(candidatos, n_types * silos_per_type)
    port_ids = list(nos[nos["no"].str.startswith("T_")]["no"])
    ids = ["G"] + silo_ids + mix_ids + port_ids
    G = 0
    S = list(range(1, len(silo_ids) + 1))
    M = list(range(S[-1] + 1, S[-1] + 1 + len(mix_ids)))
    D = list(range(M[-1] + 1, M[-1] + 1 + len(port_ids)))
    tipo = {s: (s - 1) // silos_per_type for s in S}
    info = nos.set_index("no")
    nomes = [info.loc[i, "nome"] for i in ids]
    coords = [(info.loc[i, "longitude"], info.loc[i, "latitude"]) for i in ids]
    dist = dk.loc[ids, ids].to_numpy(dtype=float)
    t_arc = th.loc[ids, ids].to_numpy(dtype=float)
    nD = len(D)
    F_port = list(F_port) if F_port else [round(rng.uniform(60, 160), 0) for _ in D]
    tau = list(tau) if tau else [0.0] * nD
    s_port = list(s_port) if s_port else [1.0] * nD
    inst = _montar(nomes, coords, G, S, M, D, tipo, dist, t_arc, rng, n_types=n_types, n_lots=n_lots, W=W,
                   blends=blends, rho=rho, Q=Q, c_km=c_km, diesel=diesel, cons=cons, f_veh=f_veh,
                   F_mix=list(F_mix)[:len(M)], s_mix=list(s_mix)[:len(M)], F_port=F_port, tau=tau,
                   s_port=s_port, s_silo=s_silo, price=price, tw=tw, Tmax=Tmax, beta=beta,
                   stock_slack=stock_slack, sintetica="SEMI-REAL (rede real, blends sinteticos)")
    inst["ids_osrm"] = ids
    inst["diesel"] = diesel
    return inst


def need_of(inst, lot):
    return {k: lot["pi"].get(k, 0.0) * lot["W"] / (1 - inst["rho"]) for k in inst["tipos"]}


def check_instance(inst):
    """Factibilidade minima antes do solver (capacidade e estoque agregado)."""
    erros = []
    for b, lot in enumerate(inst["lots"]):
        if abs(sum(lot["pi"].values()) - 1) > 1e-9:
            erros.append(f"lote {b}: proporcoes nao somam 1")
        if lot["W"] / (1 - inst["rho"]) > inst["Q"] + 1e-9:
            erros.append(f"lote {b}: W/(1-rho) > Q (dividir em lotes)")
    for k in inst["tipos"]:
        total = sum(need_of(inst, l)[k] for l in inst["lots"])
        if sum(inst["e"][s] for s in inst["S"] if inst["tipo"][s] == k) < total - 1e-9:
            erros.append(f"tipo {k}: estoque total menor que a demanda")
    return erros


# ----------------------------------------------------------------------------- modelo exato
def _gap_cbc(log_path, obj):
    try:
        txt = open(log_path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return None
    lb = re.findall(r"Lower bound:\s+(-?[\d.eE+]+)", txt)
    if lb and obj:
        return max(0.0, (obj - float(lb[-1])) / abs(obj))
    return None


def solve_blend(inst, time_limit=60, solver_name="cbc", msg=False, mtz=True):
    """Resolve o PLI dos blends (todos os niveis: o que muda e so a instancia)."""
    erros = check_instance(inst)
    if erros:
        return dict(status="Infeasible (pre-check)", erros=erros)
    G, S, M, D = inst["G"], inst["S"], inst["M"], inst["D"]
    c, t, sv, jan, Tmax = inst["c_arc"], inst["t_arc"], inst["serv"], inst["janela"], inst["Tmax"]
    bigM = Tmax + float(np.max(t)) + max(sv.values())
    prob = pulp.LpProblem("blends", pulp.LpMinimize)
    x, v, r, w, u, T, late, arcs_b = {}, {}, {}, {}, {}, {}, {}, {}
    obj = []
    for b, lot in enumerate(inst["lots"]):
        Kb = [k for k in inst["tipos"] if lot["pi"].get(k, 0) > 0]
        Sb = [s for s in S if inst["tipo"][s] in Kb]
        A = [(G, s) for s in Sb] + [(i, j) for i in Sb for j in Sb if i != j]
        A += [(s, m) for s in Sb for m in M] + [(m, d) for m in M for d in D] + [(d, G) for d in D]
        arcs_b[b] = A
        for (i, j) in A:
            x[b, i, j] = pulp.LpVariable(f"x_{b}_{i}_{j}", cat="Binary")
        for s in Sb:
            v[b, s] = pulp.LpVariable(f"v_{b}_{s}", cat="Binary")
            r[b, s] = pulp.LpVariable(f"r_{b}_{s}", lowBound=0, upBound=min(inst["e"][s], inst["Q"]))
            u[b, s] = pulp.LpVariable(f"u_{b}_{s}", lowBound=1, upBound=len(Sb))
        for m in M:
            w[b, m] = pulp.LpVariable(f"w_{b}_{m}", cat="Binary")
        for i in Sb + M + D:
            T[b, i] = pulp.LpVariable(f"T_{b}_{i}", lowBound=jan[i][0], upBound=Tmax)
        if any(d in inst["soft"] for d in D):
            late[b] = pulp.LpVariable(f"late_{b}", lowBound=0)

        y = {d: x[b, d, G] for d in D}
        obj += [inst["f_veh"]] + [c[i][j] * x[b, i, j] for (i, j) in A]
        obj += [inst["p"][s] * r[b, s] for s in Sb] + [inst["F_mix"][m] * w[b, m] for m in M]
        obj += [(inst["F_port"][d] + inst["tau"][d] * lot["W"]) * y[d] for d in D]
        if b in late:
            obj.append(inst["beta"] * late[b])

        out = lambda n: [x[b, i, j] for (i, j) in A if i == n]
        inn = lambda n: [x[b, i, j] for (i, j) in A if j == n]
        prob += pulp.lpSum(out(G)) == 1, f"saida_garagem_{b}"
        for s in Sb:
            prob += pulp.lpSum(inn(s)) == v[b, s], f"entra_{b}_{s}"
            prob += pulp.lpSum(out(s)) == v[b, s], f"sai_{b}_{s}"
        for m in M:
            prob += pulp.lpSum(inn(m)) == w[b, m], f"entra_mist_{b}_{m}"
            prob += pulp.lpSum(out(m)) == w[b, m], f"sai_mist_{b}_{m}"
        prob += pulp.lpSum(w[b, m] for m in M) == 1, f"uma_misturadora_{b}"
        for d in D:
            prob += pulp.lpSum(inn(d)) == y[d], f"porto_{b}_{d}"

        nd = need_of(inst, lot)
        for k in Kb:
            prob += pulp.lpSum(r[b, s] for s in Sb if inst["tipo"][s] == k) == nd[k], f"composicao_{b}_{k}"
        for s in Sb:
            prob += r[b, s] <= min(inst["e"][s], inst["Q"]) * v[b, s], f"retira_se_visita_{b}_{s}"

        if mtz:
            for (i, j) in A:
                if i in Sb and j in Sb:
                    prob += u[b, j] >= u[b, i] + 1 - len(Sb) * (1 - x[b, i, j]), f"mtz_{b}_{i}_{j}"

        for (i, j) in A:
            if j == G:
                continue
            ti = 0.0 if i == G else T[b, i]
            prob += T[b, j] >= ti + sv[i] + t[i][j] - bigM * (1 - x[b, i, j]), f"tempo_{b}_{i}_{j}"
        for s in Sb:
            prob += T[b, s] <= jan[s][1] + bigM * (1 - v[b, s]), f"janela_{b}_{s}"
        for m in M:
            prob += T[b, m] <= jan[m][1] + bigM * (1 - w[b, m]), f"janela_{b}_{m}"
        for d in D:
            folga = late[b] if (b in late and d in inst["soft"]) else 0
            prob += T[b, d] <= jan[d][1] + folga + bigM * (1 - y[d]), f"janela_{b}_{d}"
            prob += T[b, d] + sv[d] + t[d][G] <= Tmax + bigM * (1 - y[d]), f"retorno_{b}_{d}"

    for s in S:
        lotes = [b for b in range(len(inst["lots"])) if (b, s) in r]
        if len(lotes) > 1:
            prob += pulp.lpSum(r[b, s] for b in lotes) <= inst["e"][s], f"estoque_compartilhado_{s}"
    prob += pulp.lpSum(obj)

    log = os.path.join(tempfile.gettempdir(), f"cbc_blend_{os.getpid()}_{time.time_ns()}.log")
    if solver_name == "highs":
        solver = pulp.HiGHS(msg=msg, timeLimit=time_limit)
    else:
        solver = pulp.PULP_CBC_CMD(msg=msg, timeLimit=time_limit, logPath=log)
    t0 = time.time()
    prob.solve(solver)
    el = time.time() - t0
    n_bin = sum(1 for var in prob.variables() if var.cat == "Integer")
    base = dict(time=el, n_vars=len(prob.variables()), n_cons=len(prob.constraints), n_bin=n_bin,
                hit_limit=el >= 0.97 * time_limit)
    if prob.sol_status not in (1, 2):
        return dict(status=pulp.LpStatus[prob.status], **base)

    objv = pulp.value(prob.objective)
    proven = prob.sol_status == 1 and not base["hit_limit"]
    gap = 0.0 if proven else None
    if not proven:
        if solver_name == "highs":
            try:
                gap = prob.solverModel.getInfo().mip_gap
            except Exception:
                gap = None
        else:
            gap = _gap_cbc(log, objv)
    if os.path.exists(log):
        os.remove(log)

    lots = []
    for b, lot in enumerate(inst["lots"]):
        succ = {i: j for (bb, i, j), var in x.items() if bb == b and var.value() > 0.5}
        rota = [G]
        while True:
            rota.append(succ[rota[-1]])
            if rota[-1] == G or len(rota) > len(inst["nomes"]) + 2:
                break
        ret = {s: round(var.value(), 4) for (bb, s), var in r.items() if bb == b and var.value() > 1e-6}
        lots.append(dict(route=rota, r=ret))
    return dict(status="Optimal" if proven else "Feasible", proven_optimal=proven, obj=objv, gap=gap,
                sol=dict(lots=lots), **base)


# ----------------------------------------------------------------------------- avaliacao independente
def schedule(inst, rota):
    """Propaga o tempo ao longo da rota (espera permitida). Devolve inicio de servico, atraso, violacoes."""
    t, sv, jan = inst["t_arc"], inst["serv"], inst["janela"]
    T, late, viol = {rota[0]: 0.0}, 0.0, []
    agora = 0.0
    for i, j in zip(rota[:-1], rota[1:]):
        chegada = agora + sv[i] + t[i][j]
        if j == inst["G"]:
            fim = chegada
            if fim > inst["Tmax"] + 1e-6:
                viol.append(f"duracao {fim:.2f} h > Tmax")
            return T, late, viol, fim
        agora = max(chegada, jan[j][0])
        T[j] = agora
        if agora > jan[j][1] + 1e-6:
            if j in inst["soft"]:
                late = max(late, agora - jan[j][1])
            else:
                viol.append(f"janela de {inst['nomes'][j]} ({agora:.2f} > {jan[j][1]:.2f})")
    return T, late, viol, agora


def lot_cost(inst, lot, rota, r):
    """Custo de um lote e lista de violacoes (estrutura, composicao, capacidade, janelas)."""
    G, S, M, D = inst["G"], inst["S"], inst["M"], inst["D"]
    viol = []
    if rota[0] != G or rota[-1] != G or len(rota) < 5:
        viol.append("rota nao comeca/termina na garagem")
    meio = rota[1:-3]
    m, d = rota[-3], rota[-2]
    if any(s not in S for s in meio) or m not in M or d not in D or len(set(meio)) != len(meio):
        viol.append("estrutura garagem -> silos -> misturadora -> porto -> garagem violada")
    nd = need_of(inst, lot)
    for k in inst["tipos"]:
        got = sum(q for s, q in r.items() if inst["tipo"][s] == k)
        if abs(got - nd[k]) > 1e-4:
            viol.append(f"composicao do tipo {k}: {got:.3f} != {nd[k]:.3f}")
    if any(s not in meio for s, q in r.items() if q > 1e-6):
        viol.append("retirada em silo nao visitado")
    if sum(r.values()) > inst["Q"] + 1e-6:
        viol.append("capacidade Q excedida")
    T, late, v2, fim = schedule(inst, rota)
    viol += v2
    desloc = sum(inst["c_arc"][i][j] for i, j in zip(rota[:-1], rota[1:]))
    comp = dict(veiculo=inst["f_veh"], deslocamento=desloc,
                aquisicao=sum(inst["p"][s] * q for s, q in r.items()),
                misturadora=inst["F_mix"].get(m, 0.0),
                porto=inst["F_port"].get(d, 0.0) + inst["tau"].get(d, 0.0) * lot["W"],
                atraso=inst["beta"] * late)
    return sum(comp.values()), comp, viol, dict(T=T, late=late, fim=fim)


def evaluate(inst, sol):
    """Recalcula custo e verifica todas as restricoes; serve para o exato e para a heuristica."""
    total, comp_tot, viol, det = 0.0, {}, [], []
    uso = {}
    for b, (lot, ls) in enumerate(zip(inst["lots"], sol["lots"])):
        cst, comp, v, info = lot_cost(inst, lot, ls["route"], ls["r"])
        total += cst
        for k, val in comp.items():
            comp_tot[k] = comp_tot.get(k, 0.0) + val
        viol += [f"lote {b}: {x}" for x in v]
        det.append(dict(custo=cst, **info))
        for s, q in ls["r"].items():
            uso[s] = uso.get(s, 0.0) + q
    for s, q in uso.items():
        if q > inst["e"][s] + 1e-6:
            viol.append(f"estoque do silo {inst['nomes'][s]} excedido ({q:.2f} > {inst['e'][s]:.2f})")
    return dict(cost=total, components=comp_tot, feasible=not viol, violations=viol, lots=det)


# ----------------------------------------------------------------------------- forca bruta (validacao B1/B3)
def brute_force(inst):
    """Enumera ordens x misturadoras x portos. So para 1 lote e 1 silo por tipo (retiradas fixas)."""
    if len(inst["lots"]) != 1:
        raise ValueError("forca bruta so para 1 lote")
    lot = inst["lots"][0]
    nd = need_of(inst, lot)
    Kb = [k for k in inst["tipos"] if nd[k] > 0]
    Sb = [s for s in inst["S"] if inst["tipo"][s] in Kb]
    if len(Sb) != len(Kb):
        raise ValueError("forca bruta so com 1 silo por tipo")
    r = {s: nd[inst["tipo"][s]] for s in Sb}
    best = (math.inf, None)
    for perm in itertools.permutations(Sb):
        for m in inst["M"]:
            for d in inst["D"]:
                rota = [inst["G"], *perm, m, d, inst["G"]]
                cst, _, viol, _ = lot_cost(inst, lot, rota, r)
                if not viol and cst < best[0]:
                    best = (cst, dict(lots=[dict(route=rota, r=r)]))
    return best


# ----------------------------------------------------------------------------- relatorios
def describe(inst, sol):
    """Linhas legiveis: rota com nomes e retiradas por silo."""
    linhas = []
    for b, ls in enumerate(sol["lots"]):
        partes = []
        for n in ls["route"]:
            nome = inst["nomes"][n]
            if n in inst["S"]:
                nome += f"[{inst['rotulo_tipo'][inst['tipo'][n]]}: {ls['r'].get(n, 0):.2f} t]"
            partes.append(nome)
        linhas.append(f"lote {b}: " + " -> ".join(partes))
    return linhas


def plot_blend(inst, sol, title="", ax=None):
    import matplotlib.pyplot as plt
    ax = ax or plt.subplots(figsize=(6, 6))[1]
    xy = inst["coords"]
    cores = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]
    marcas = ["o", "s", "D", "P", "X", "v", "*"]
    for k in inst["tipos"]:
        Sk = [s for s in inst["S"] if inst["tipo"][s] == k]
        ax.scatter([xy[s][0] for s in Sk], [xy[s][1] for s in Sk], marker=marcas[k % 7], s=55, color="white",
                   edgecolor="#52514e", zorder=4, label=f"silo {inst['rotulo_tipo'][k]}")
    ax.scatter(*xy[inst["G"]], marker="s", s=90, color="#0b0b0b", zorder=5, label="garagem")
    ax.scatter([xy[m][0] for m in inst["M"]], [xy[m][1] for m in inst["M"]], marker="h", s=140,
               color="#6250d6", zorder=5, label="misturadora")
    ax.scatter([xy[d][0] for d in inst["D"]], [xy[d][1] for d in inst["D"]], marker="^", s=130,
               color="#e34948", zorder=5, label="porto seco")
    for b, ls in enumerate(sol["lots"]):
        rr = ls["route"]
        ax.plot([xy[n][0] for n in rr], [xy[n][1] for n in rr], "-", color=cores[b % 7], lw=1.8, zorder=3,
                label=f"rota lote {b}")
    for n in range(len(inst["nomes"])):
        ax.annotate(inst["nomes"][n], xy[n], textcoords="offset points", xytext=(4, 4), fontsize=7)
    ax.set_title(title)
    ax.legend(fontsize=7, loc="best")
    return ax


if __name__ == "__main__":
    # autoteste rapido: B1 exato = forca bruta; B2-B5 viaveis e custo recalculado = objetivo
    inst = make_blend_instance(n_types=4, silos_per_type=1, n_mix=1, n_ports=2, seed=3)
    ex = solve_blend(inst, time_limit=30)
    bf, _ = brute_force(inst)
    print(f"B1: exato {ex['obj']:.2f} | forca bruta {bf:.2f} | tempo {ex['time']:.2f} s")
    assert abs(ex["obj"] - bf) < 1e-4
    casos = {"B2": dict(n_types=3, silos_per_type=3), "B3": dict(n_types=3, silos_per_type=2, n_mix=2),
             "B4": dict(n_types=3, silos_per_type=2, n_mix=2, tw=True),
             "B5": dict(n_types=3, silos_per_type=2, n_mix=2, n_lots=2, tw=True)}
    for nome, kw in casos.items():
        inst = make_blend_instance(seed=5, **kw)
        res = solve_blend(inst, time_limit=60)
        ev = evaluate(inst, res["sol"])
        print(f"{nome}: {res['status']:8s} obj {res['obj']:9.2f} | recalculado {ev['cost']:9.2f} | "
              f"viavel {ev['feasible']} | bin {res['n_bin']} | {res['time']:.2f} s")
        assert ev["feasible"], ev["violations"]
        assert abs(ev["cost"] - res["obj"]) < 1e-3 * max(1, abs(res["obj"]))
    print("autoteste ok")
