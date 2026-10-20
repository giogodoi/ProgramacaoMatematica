
import math, time, random
import numpy as np
import pulp

def make_instance(n=8, m=2, seed=1, Q=30.0, K=6, Tmax=9.0, speed=60.0,
                  c_km=2.8, diesel=6.2, cons=0.40, f_veh=350.0,
                  F_term=(120.0, 60.0), tariff=(0.0, 0.0), cap_term=(1e9, 1e9),
                  s_pick=0.5, s_term=(0.5, 1.0), area=200.0):
    """Instancia SINTETICA (coordenadas em km no plano) para validar o modelo."""
    rng = random.Random(seed)
    depot = (area*0.5, area*0.1)
    pick = [(rng.uniform(0, area), rng.uniform(area*0.25, area)) for _ in range(n)]
    term = [(area*0.15, area*0.05), (area*0.9, area*0.0)][:m] if m <= 2 else \
           [(rng.uniform(0, area), rng.uniform(0, area*0.3)) for _ in range(m)]
    q = [round(rng.uniform(4, 14), 1) for _ in range(n)]
    coords = [depot] + pick + term
    N = len(coords)
    dist = np.array([[math.dist(a, b)*1.25 for b in coords] for a in coords])  # fator de desvio viario
    return dict(n=n, m=m, coords=coords, dist=dist, q=q, Q=Q, K=K, Tmax=Tmax, speed=speed,
                c_arc=dist*(c_km + diesel*cons), t_arc=dist/speed, f_veh=f_veh,
                F_term=list(F_term)[:m], tariff=list(tariff)[:m], cap_term=list(cap_term)[:m],
                s_pick=s_pick, s_term=list(s_term)[:m])

def solve(inst, policy="flexible", time_limit=60, msg=False, with_cap=False, solver_name='highs'):
    n, m = inst["n"], inst["m"]
    O = list(range(1, n+1)); D = list(range(n+1, n+m+1)); G = 0
    q = {i: inst["q"][i-1] for i in O}
    Q, K, Tmax = inst["Q"], inst["K"], inst["Tmax"]
    c, t = inst["c_arc"], inst["t_arc"]
    near = {i: min(D, key=lambda d: inst["dist"][i][d]) for i in O}

    A = [(G, i) for i in O]
    A += [(i, j) for i in O for j in O if i != j]
    A += [(i, d) for i in O for d in D]
    A += [(d, G) for d in D]
    if policy == "nearest":
        A = [(a, b) for (a, b) in A if not (a in O and b in D and b != near[a])
             and not (a in O and b in O and near[a] != near[b])]

    prob = pulp.LpProblem("CVRP_multiterminal", pulp.LpMinimize)
    x = {a: (pulp.LpVariable(f"x_{a[0]}_{a[1]}", lowBound=0, upBound=K, cat="Integer") if a[0] in D
             else pulp.LpVariable(f"x_{a[0]}_{a[1]}", cat="Binary")) for a in A}
    L = {i: pulp.LpVariable(f"L_{i}", lowBound=0, upBound=Q) for i in O}
    T = {v: pulp.LpVariable(f"T_{v}", lowBound=0, upBound=Tmax) for v in O}
    inn = lambda v: [a for a in A if a[1] == v]
    out = lambda v: [a for a in A if a[0] == v]
    Fd = dict(zip(D, inst["F_term"])); td = dict(zip(D, inst["tariff"])); Cd = dict(zip(D, inst["cap_term"]))
    sd = dict(zip(D, inst["s_term"])); sp = inst["s_pick"]

    z = {}
    if with_cap or any(v > 0 for v in td.values()):
        for (i, d) in [a for a in A if a[0] in O and a[1] in D]:
            z[(i, d)] = pulp.LpVariable(f"z_{i}_{d}", lowBound=0, upBound=Q)
            prob += z[(i, d)] <= L[i]
            prob += z[(i, d)] <= Q * x[(i, d)]
            prob += z[(i, d)] >= L[i] - Q * (1 - x[(i, d)])

    prob += (pulp.lpSum(inst["f_veh"] * x[a] for a in A if a[0] == G)
             + pulp.lpSum(c[a[0]][a[1]] * x[a] for a in A)
             + pulp.lpSum(Fd[a[0]] * x[a] for a in A if a[0] in D)
             + pulp.lpSum(td[d] * z[(i, d)] for (i, d) in z))

    for i in O:
        prob += pulp.lpSum(x[a] for a in out(i)) == 1
        prob += pulp.lpSum(x[a] for a in inn(i)) == 1
    for d in D:
        prob += pulp.lpSum(x[a] for a in inn(d)) == pulp.lpSum(x[a] for a in out(d))
    prob += pulp.lpSum(x[a] for a in out(G)) == pulp.lpSum(x[a] for a in inn(G))
    prob += pulp.lpSum(x[a] for a in out(G)) <= K

    for i in O:
        prob += L[i] >= q[i] + 0
        prob += L[i] <= Q
    for (i, j) in [a for a in A if a[0] in O and a[1] in O]:
        prob += L[j] >= L[i] + q[j] - (Q + q[j]) * (1 - x[(i, j)])
        prob += L[j] <= L[i] + q[j] + Q * (1 - x[(i, j)])
    for i in O:
        if (G, i) in x:
            prob += L[i] <= q[i] + Q * (1 - x[(G, i)])
            prob += L[i] >= q[i] - Q * (1 - x[(G, i)])

    for i in O:
        if (G, i) in x:
            prob += T[i] >= t[G][i] + sp - Tmax * (1 - x[(G, i)])
    for (i, j) in [a for a in A if a[0] in O and a[1] in O]:
        prob += T[j] >= T[i] + t[i][j] + sp - (Tmax + t[i][j] + sp) * (1 - x[(i, j)])
    for (i, d) in [a for a in A if a[0] in O and a[1] in D]:
        tail = t[i][d] + sd[d] + t[d][G]
        prob += T[i] + tail <= Tmax + (Tmax + tail) * (1 - x[(i, d)])

    if with_cap:
        for d in D:
            prob += pulp.lpSum(z[(i, dd)] for (i, dd) in z if dd == d) <= Cd[d]

    solver = (pulp.HiGHS(msg=msg, timeLimit=time_limit) if solver_name=='highs' else pulp.PULP_CBC_CMD(msg=msg, timeLimit=time_limit))
    t0 = time.time(); prob.solve(solver); el = time.time() - t0
    status = pulp.LpStatus[prob.status]
    if prob.status != 1 and prob.objective is None:
        return dict(status=status)
    succ = {}
    for a in A:
        if x[a].value() is not None and x[a].value() > 0.5:
            succ.setdefault(a[0], []).append(a[1])
    routes = []
    for first in succ.get(G, []):
        r = [G, first]
        while r[-1] != G:
            r.append(succ[r[-1]][0])
        routes.append(r)
    obj = pulp.value(prob.objective)
    return dict(status=status, obj=obj, time=el, hit_limit=el >= 0.97*time_limit, routes=routes, n_vars=len(prob.variables()),
                n_cons=len(prob.constraints), n_bin=len([a for a in A if a[0] not in D]))

def route_cost(inst, r):
    n = inst["n"]; D0 = n + 1
    d = r[-2]
    cost = inst["f_veh"] + sum(inst["c_arc"][a][b] for a, b in zip(r[:-1], r[1:])) + inst["F_term"][d - D0]
    return cost


def plot_routes(inst, res, title="", ax=None):
    import matplotlib.pyplot as plt
    n = inst["n"]; coords = inst["coords"]
    ax = ax or plt.subplots(figsize=(6, 6))[1]
    cols = plt.cm.tab10.colors
    for k, r in enumerate(res["routes"]):
        xs = [coords[v][0] for v in r]; ys = [coords[v][1] for v in r]
        ax.plot(xs, ys, "-o", color=cols[k % 10], lw=1.6, ms=4, label=f"rota {k+1}")
    ax.scatter(*coords[0], marker="s", s=90, c="k", zorder=5, label="garagem")
    for d in range(n+1, n+inst["m"]+1):
        ax.scatter(*coords[d], marker="^", s=130, c="red", zorder=5)
        ax.annotate(f"T{d-n}", coords[d], textcoords="offset points", xytext=(6, 6), color="red")
    for i in range(1, n+1):
        ax.annotate(f"{i} ({inst['q'][i-1]}t)", coords[i], textcoords="offset points", xytext=(4, 4), fontsize=7)
    ax.set_title(title); ax.set_xlabel("km"); ax.set_ylabel("km"); ax.legend(fontsize=7)
    return ax
