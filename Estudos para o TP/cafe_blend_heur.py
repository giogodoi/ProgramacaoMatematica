"""Heuristica da Fase 3 para o problema dos blends (ver 03_modelo_PLI_blends.md, secao 9).

1. Construcao gulosa por lote: para cada misturadora, escolhe silos por tipo (tarifa + desvio),
   ordena por insercao mais barata + 2-opt e enumera os portos secos.
2. Busca local VND: 2-opt, realocacao, troca de silo do mesmo tipo, inclusao/remocao de silo,
   troca de misturadora (o porto e sempre reotimizado por enumeracao).
3. ILS: perturbacao (embaralhar trecho, trocar silos, trocar misturadora) + VND, com aceitacao
   estilo simulated annealing. Registra o historico (tempo, melhor custo) para o grafico
   heuristica x exato.

Solucoes no mesmo formato de ``cafe_blend.solve_blend``: {"lots": [{"route": [...], "r": {...}}]}.
"""

import math, random, time

from cafe_blend import lot_cost, need_of, evaluate

PEN = 1e4   # penalidade por violacao (janela dura, Tmax) durante a busca


# ----------------------------------------------------------------------------- avaliacao de um lote
def allocate(inst, lot, seq, avail):
    """Retiradas mais baratas (por tarifa) entre os silos da sequencia; None se nao cobre a demanda."""
    nd = need_of(inst, lot)
    r = {}
    for k, falta in nd.items():
        if falta <= 0:
            continue
        for s in sorted((s for s in seq if inst["tipo"][s] == k), key=lambda s: inst["p"][s]):
            q = min(avail[s], falta)
            if q > 1e-9:
                r[s] = q
                falta -= q
            if falta <= 1e-9:
                break
        if falta > 1e-6:
            return None
    return r


def lot_eval(inst, lot, seq, m, avail):
    """Melhor porto para (sequencia, misturadora). Devolve (custo penalizado, rota, retiradas)."""
    r = allocate(inst, lot, seq, avail)
    if r is None:
        return math.inf, None, None
    seq = [s for s in seq if s in r]   # silo sem retirada sai da rota (so piora deslocamento e tempo)
    best = (math.inf, None, None)
    for d in inst["D"]:
        rota = [inst["G"], *seq, m, d, inst["G"]]
        cst, _, viol, _ = lot_cost(inst, lot, rota, r)
        cst += PEN * len(viol)
        if cst < best[0]:
            best = (cst, rota, r)
    return best


def _avail(inst, sol, b):
    uso = {s: 0.0 for s in inst["S"]}
    for bb, ls in enumerate(sol["lots"]):
        if bb != b and ls:
            for s, q in ls["r"].items():
                uso[s] += q
    return {s: inst["e"][s] - uso[s] for s in inst["S"]}


# ----------------------------------------------------------------------------- construcao
def _insertion_order(inst, chosen, m):
    c, G = inst["c_arc"], inst["G"]
    seq = []
    for s in sorted(chosen, key=lambda s: -(c[G][s] + c[s][m])):
        path = [G, *seq, m]
        pos = min(range(len(seq) + 1), key=lambda p: c[path[p]][s] + c[s][path[p + 1]] - c[path[p]][path[p + 1]])
        seq.insert(pos, s)
    return seq


def _two_opt(inst, lot, seq, m, avail, cur):
    melhorou = True
    while melhorou:
        melhorou = False
        for i in range(len(seq) - 1):
            for j in range(i + 1, len(seq)):
                cand = seq[:i] + seq[i:j + 1][::-1] + seq[j + 1:]
                val = lot_eval(inst, lot, cand, m, avail)
                if val[0] < cur[0] - 1e-9:
                    seq, cur, melhorou = cand, val, True
    return seq, cur


def construct_lot(inst, lot, avail):
    c, G = inst["c_arc"], inst["G"]
    nd = need_of(inst, lot)
    best = (math.inf, None, None, None, None)
    for m in inst["M"]:
        chosen = []
        for k, falta in nd.items():
            if falta <= 0:
                continue
            cand = [s for s in inst["S"] if inst["tipo"][s] == k and avail[s] > 1e-9]
            desvio = lambda s: c[G][s] + c[s][m] - c[G][m]
            cand.sort(key=lambda s: inst["p"][s] + desvio(s) / max(min(avail[s], falta), 1e-9))
            for s in cand:
                chosen.append(s)
                falta -= avail[s]
                if falta <= 1e-9:
                    break
        seq = _insertion_order(inst, chosen, m)
        cur = lot_eval(inst, lot, seq, m, avail)
        seq, cur = _two_opt(inst, lot, seq, m, avail, cur)
        if cur[0] < best[0]:
            best = (cur[0], seq, m, cur[1], cur[2])
    return best


def construct(inst):
    """Lotes em ordem decrescente de W (os maiores consomem estoque primeiro)."""
    sol = dict(lots=[None] * len(inst["lots"]))
    for b in sorted(range(len(inst["lots"])), key=lambda b: -inst["lots"][b]["W"]):
        _, seq, m, rota, r = construct_lot(inst, inst["lots"][b], _avail(inst, sol, b))
        sol["lots"][b] = dict(route=rota, r=r)
    return sol


# ----------------------------------------------------------------------------- busca local (VND)
def _vizinhos(inst, lot, seq, m, rng=None):
    """Gera (seq, m) vizinhos na ordem das vizinhancas do VND."""
    n = len(seq)
    for i in range(n - 1):                                     # N1: 2-opt
        for j in range(i + 1, n):
            yield "2opt", seq[:i] + seq[i:j + 1][::-1] + seq[j + 1:], m
    for i in range(n):                                         # N2: realocacao
        resto = seq[:i] + seq[i + 1:]
        for p in range(n):
            if p != i:
                yield "relocate", resto[:p] + [seq[i]] + resto[p:], m
    fora = [s for s in inst["S"] if s not in seq and lot["pi"].get(inst["tipo"][s], 0) > 0]
    for i, s in enumerate(seq):                                # N3: troca de silo do mesmo tipo
        for s2 in fora:
            if inst["tipo"][s2] == inst["tipo"][s]:
                yield "swap-source", seq[:i] + [s2] + seq[i + 1:], m
    for s2 in fora:                                            # N4: inclusao de silo
        for p in range(n + 1):
            yield "add", seq[:p] + [s2] + seq[p:], m
    for i in range(n):                                         # N5: remocao de silo
        yield "drop", seq[:i] + seq[i + 1:], m
    for m2 in inst["M"]:                                       # N6: troca de misturadora
        if m2 != m:
            yield "mixer", seq, m2


def local_search_lot(inst, lot, seq, m, avail, stats=None):
    cur = lot_eval(inst, lot, seq, m, avail)
    melhorou = True
    while melhorou:
        melhorou = False
        for nome, s2, m2 in _vizinhos(inst, lot, seq, m):
            val = lot_eval(inst, lot, s2, m2, avail)
            if val[0] < cur[0] - 1e-9:
                seq, m, cur, melhorou = s2, m2, val, True
                if stats is not None:
                    stats[nome] = stats.get(nome, 0) + 1
                break
    return seq, m, cur


def _seq_m(ls):
    return list(ls["route"][1:-3]), ls["route"][-3]


def local_search(inst, sol, stats=None):
    """VND lote a lote, repetido ate nenhum lote melhorar (estoque compartilhado entre lotes)."""
    sol = dict(lots=[dict(route=list(l["route"]), r=dict(l["r"])) for l in sol["lots"]])
    melhorou = True
    while melhorou:
        melhorou = False
        for b, lot in enumerate(inst["lots"]):
            avail = _avail(inst, sol, b)
            seq, m = _seq_m(sol["lots"][b])
            antes = lot_eval(inst, lot, seq, m, avail)[0]
            seq, m, cur = local_search_lot(inst, lot, seq, m, avail, stats)
            if cur[0] < antes - 1e-9:
                sol["lots"][b] = dict(route=cur[1], r=cur[2])
                melhorou = True
    return sol


def penalized(inst, sol):
    ev = evaluate(inst, sol)
    return ev["cost"] + PEN * len(ev["violations"]), ev


# ----------------------------------------------------------------------------- ILS
def _perturb(inst, sol, rng):
    sol = dict(lots=[dict(route=list(l["route"]), r=dict(l["r"])) for l in sol["lots"]])
    b = rng.randrange(len(inst["lots"]))
    lot = inst["lots"][b]
    avail = _avail(inst, sol, b)
    seq, m = _seq_m(sol["lots"][b])
    mov = rng.choice(["shuffle", "swap", "mixer"] if len(inst["M"]) > 1 else ["shuffle", "swap"])
    if mov == "shuffle" and len(seq) >= 3:
        i, j = sorted(rng.sample(range(len(seq)), 2))
        trecho = seq[i:j + 1]
        rng.shuffle(trecho)
        seq = seq[:i] + trecho + seq[j + 1:]
    elif mov == "mixer":
        m = rng.choice([x for x in inst["M"] if x != m])
    else:
        for _ in range(rng.choice([1, 2])):
            i = rng.randrange(len(seq))
            alt = [s for s in inst["S"] if inst["tipo"][s] == inst["tipo"][seq[i]] and s not in seq]
            if alt:
                seq[i] = rng.choice(alt)
    val = lot_eval(inst, lot, seq, m, avail)
    if val[1] is None:          # perturbacao inviavel (estoque): reconstroi o lote
        _, seq, m, rota, r = construct_lot(inst, lot, avail)
        val = (0, rota, r)
    sol["lots"][b] = dict(route=val[1], r=val[2])
    return sol


def ils(inst, iters=200, time_limit=30.0, seed=0, T0=0.02, alpha=0.98):
    """ILS + VND. Devolve melhor solucao, custo, tempo, historico [(t, melhor)] e estatisticas."""
    rng = random.Random(seed)
    t0 = time.time()
    stats = {}
    cur = local_search(inst, construct(inst), stats)
    c_cur, _ = penalized(inst, cur)
    best, c_best = cur, c_cur
    hist = [(time.time() - t0, c_best)]
    c_construcao = penalized(inst, construct(inst))[0]
    temp = T0 * c_cur
    for it in range(iters):
        if time.time() - t0 > time_limit:
            break
        cand = local_search(inst, _perturb(inst, cur, rng), stats)
        c_cand, _ = penalized(inst, cand)
        if c_cand < c_cur - 1e-9 or rng.random() < math.exp(-(c_cand - c_cur) / max(temp, 1e-9)):
            cur, c_cur = cand, c_cand
        if c_cand < c_best - 1e-9:
            best, c_best = cand, c_cand
            hist.append((time.time() - t0, c_best))
        temp *= alpha
    ev = evaluate(inst, best)
    hist.append((time.time() - t0, c_best))
    return dict(sol=best, cost=ev["cost"], feasible=ev["feasible"], violations=ev["violations"],
                time=time.time() - t0, history=hist, construction_cost=c_construcao, stats=stats, iters=it + 1)


if __name__ == "__main__":
    from cafe_blend import make_blend_instance, solve_blend
    casos = {"B1": dict(n_types=4), "B2": dict(n_types=3, silos_per_type=3),
             "B3": dict(n_types=3, silos_per_type=2, n_mix=2), "B4": dict(n_types=3, silos_per_type=2, n_mix=2, tw=True),
             "B5": dict(n_types=3, silos_per_type=2, n_mix=2, n_lots=2, tw=True)}
    for nome, kw in casos.items():
        inst = make_blend_instance(seed=5, **kw)
        ex = solve_blend(inst, time_limit=60)
        h = ils(inst, iters=100, time_limit=20, seed=1)
        gap = 100 * (h["cost"] / ex["obj"] - 1)
        print(f"{nome}: exato {ex['obj']:9.2f} ({ex['time']:5.2f} s) | construcao {h['construction_cost']:9.2f} | "
              f"ILS {h['cost']:9.2f} ({h['time']:5.2f} s) | gap {gap:5.2f}% | viavel {h['feasible']}")
        assert h["feasible"] and h["cost"] >= ex["obj"] - 1e-6 * ex["obj"] or not ex["proven_optimal"]
    print("autoteste heuristica ok")
