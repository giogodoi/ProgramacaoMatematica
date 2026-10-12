"""Fase 1 - analise exploratoria: tamanho da instancia, qualidade e viabilidade dos dados.

Le ``dados/processados`` (gerado por coleta_dados.py) e grava em ``fase1/relatorio``:
- figuras/*.png   : graficos usados no relatorio LaTeX;
- tabelas/*.tex   : tabelas booktabs incluidas com \\input;
- valores.tex     : macros \\newcommand com os numeros citados no texto.

Uso (a partir da pasta "Estudos para o TP"):  python fase1/analise_exploratoria.py
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, "dados", "processados")
REL = os.path.join(BASE, "fase1", "relatorio")
FIG = os.path.join(REL, "figuras")
TAB = os.path.join(REL, "tabelas")

MESO_SUL = 3110
ANO = 2025
Q = 30.0            # t por caminhao (mesmo Q do Nivel 1)
DIAS_UTEIS = 250    # dias de expedicao por ano (hipotese)
CONSUMO = 0.40      # L/km (hipotese do Nivel 1)
C_KM = 2.80         # R$/km nao combustivel (hipotese do Nivel 1)

# paleta de referencia (modo claro, documento impresso)
AZUL, LARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA2, GRADE, CINZA = "#0b0b0b", "#52514e", "#e4e3df", "#b9b8b2"
plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": CINZA, "axes.labelcolor": TINTA2, "xtick.color": TINTA2,
    "ytick.color": TINTA2, "axes.grid": True, "grid.color": GRADE, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 10,
    "axes.titlecolor": TINTA, "axes.axisbelow": True, "legend.frameon": False, "savefig.dpi": 200, "figure.dpi": 100,
})

MACROS = {}
EXTENSO = {0.5: "Cinquenta", 0.8: "Oitenta", 0.9: "Noventa", 0.95: "NoventaCinco", 1.0: "Cem"}


def macro(nome, valor):
    MACROS[nome] = valor


def br(x, casas=0):
    """Formata numero no padrao brasileiro (1.234,5) para o texto LaTeX."""
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def tabela_tex(nome, df, colfmt, legenda, rotulo, notas=None):
    linhas = [r"\begin{table}[htbp]", r"\centering", r"\small", rf"\caption{{{legenda}}}", rf"\label{{{rotulo}}}",
              rf"\begin{{tabular}}{{{colfmt}}}", r"\toprule", " & ".join(df.columns) + r" \\", r"\midrule"]
    linhas += [" & ".join(str(v) for v in row) + r" \\" for row in df.itertuples(index=False)]
    linhas += [r"\bottomrule", r"\end{tabular}"]
    if notas:
        linhas += [r"\par\smallskip\footnotesize\raggedright " + notas]
    linhas += [r"\end{table}"]
    with open(os.path.join(TAB, f"{nome}.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


def salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, f"{nome}.png"), facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- 1. producao (PAM)
def analisar_producao():
    W = pd.read_csv(os.path.join(PROC, "pam_mg_municipios.csv"))
    L = pd.read_csv(os.path.join(PROC, "pam_mg_longa.csv"))
    U = pd.read_csv(os.path.join(PROC, "pam_brasil_uf.csv"))
    arab = W[W["produto"] == "arábica"]
    sul = arab[arab["mesorregiao_id"] == MESO_SUL]

    br_ar = U[(U["local"] == "Brasil") & (U["produto"] == "arábica")].set_index("ano")["valor"]
    mg_ar = U[(U["local"] == "Minas Gerais") & (U["produto"] == "arábica")].set_index("ano")["valor"]
    mg_cn = U[(U["local"] == "Minas Gerais") & (U["produto"] == "canephora")].set_index("ano")["valor"]
    sul_ano = sul.groupby("ano")["producao_t"].sum()
    soma_mun = arab.groupby("ano")["producao_t"].sum()

    macro("AnoPAM", str(ANO))
    macro("ProdBRArab", br(br_ar[ANO]))
    macro("ProdMGArab", br(mg_ar[ANO]))
    macro("ProdMGCan", br(mg_cn[ANO]))
    macro("PctMGBR", br(100 * mg_ar[ANO] / br_ar[ANO], 1))
    macro("ProdSul", br(sul_ano[ANO]))
    macro("PctSulMG", br(100 * sul_ano[ANO] / mg_ar[ANO], 1))
    macro("DifSomaMun", br(abs(soma_mun[ANO] - mg_ar[ANO])))
    macro("SacasSul", br(sul_ano[ANO] * 1000 / 60 / 1e6, 1))

    # tabela anual (bienalidade)
    anos = sorted(sul_ano.index)
    t = pd.DataFrame({
        "Ano": anos,
        r"Brasil arábica (t)": [br(br_ar[a]) for a in anos],
        r"MG arábica (t)": [br(mg_ar[a]) for a in anos],
        r"Sul/Sudoeste MG (t)": [br(sul_ano[a]) for a in anos],
        r"Var. Sul (\%)": ["--"] + [br(100 * (sul_ano[a] / sul_ano[b] - 1), 1) for b, a in zip(anos[:-1], anos[1:])],
        r"MG canephora (t)": [br(mg_cn[a]) for a in anos],
    })
    tabela_tex("producao_anual", t, "lrrrrr", "Produção de café em grão (PAM/IBGE, tabela 1613).",
               "tab:producao_anual",
               "Fonte: SIDRA/IBGE, extraído pelo script \\texttt{coleta\\_dados.py}. A soma municipal de MG "
               "coincide com o total estadual publicado.")

    # concentracao no ano de referencia
    def curva(df):
        p = df[(df["ano"] == ANO) & (df["producao_t"] > 0)]["producao_t"].sort_values(ascending=False).values
        return np.cumsum(p) / p.sum(), len(p)

    c_mg, n_mg = curva(arab)
    c_sul, n_sul = curva(sul)
    linhas = []
    for alvo in (0.5, 0.8, 0.9, 0.95, 1.0):
        k_mg = int(np.searchsorted(c_mg, alvo - 1e-9) + 1)
        k_sul = int(np.searchsorted(c_sul, alvo - 1e-9) + 1)
        linhas.append({r"Fração da produção": f"{int(alvo*100)}\\%", "Municípios MG": k_mg, "Municípios Sul/Sudoeste": k_sul})
        macro(f"NMG{EXTENSO[alvo]}", str(k_mg))
        macro(f"NSul{EXTENSO[alvo]}", str(k_sul))
    tabela_tex("concentracao", pd.DataFrame(linhas), "lrr",
               f"Número de municípios necessários para cobrir uma fração da produção de arábica ({ANO}).",
               "tab:concentracao")
    macro("NMunMG", str(n_mg))
    macro("NMunSul", str(n_sul))

    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    ax.plot(np.arange(1, n_mg + 1), 100 * c_mg, color=AZUL, lw=2, label="Minas Gerais")
    ax.plot(np.arange(1, n_sul + 1), 100 * c_sul, color=LARANJA, lw=2, label="Sul/Sudoeste de Minas")
    ax.axhline(80, color=CINZA, lw=1, ls="--")
    ax.set_xlabel("municípios, em ordem decrescente de produção")
    ax.set_ylabel("produção acumulada (%)")
    ax.set_ylim(0, 102)
    ax.legend(loc="lower right")
    salvar(fig, "concentracao")

    # maiores produtores do Sul de Minas
    top = sul[sul["ano"] == ANO].nlargest(15, "producao_t")[::-1]
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    ax.barh(top["municipio"], top["producao_t"] / 1000, color=AZUL, height=0.7)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("produção de arábica (mil t)")
    for y, v in enumerate(top["producao_t"] / 1000):
        ax.text(v + 0.3, y, br(v, 1), va="center", fontsize=7, color=TINTA2)
    salvar(fig, "top_sul")

    # mapa (dispersao lon/lat) com terminais
    T = pd.read_csv(os.path.join(PROC, "terminais_mg.csv"))
    T["cidade"] = T["cod_ibge"].map({3136702: "Juiz de Fora", 3170107: "Uberaba", 3170701: "Varginha",
                                     3152501: "Pouso Alegre", 3106705: "Betim"})
    a25 = arab[(arab["ano"] == ANO) & (arab["producao_t"] > 0)]
    fig, ax = plt.subplots(figsize=(5.6, 4.4))
    outros = a25[a25["mesorregiao_id"] != MESO_SUL]
    s25 = a25[a25["mesorregiao_id"] == MESO_SUL]
    esc = lambda p: 4 + 120 * p / a25["producao_t"].max()
    ax.scatter(outros["longitude"], outros["latitude"], s=esc(outros["producao_t"]), color=CINZA, alpha=0.7,
               edgecolor="white", linewidth=0.4, label="municípios produtores (demais regiões)")
    ax.scatter(s25["longitude"], s25["latitude"], s=esc(s25["producao_t"]), color=AZUL, alpha=0.8,
               edgecolor="white", linewidth=0.4, label="municípios produtores (Sul/Sudoeste)")
    ax.scatter(T["longitude"], T["latitude"], marker="^", s=70, color=LARANJA, edgecolor="white",
               linewidth=0.8, zorder=5, label="portos secos e CLIAs")
    for r in T.itertuples():
        rotulo = f"{r.cidade} ({'porto seco' if r.tipo == 'porto_seco' else 'CLIA'})"
        ax.annotate(rotulo, (r.longitude, r.latitude), textcoords="offset points", xytext=(5, 4), fontsize=7, color=TINTA)
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.set_aspect("equal")
    ax.legend(loc="upper left", fontsize=7, markerscale=0.7)
    salvar(fig, "mapa")

    fig, ax = plt.subplots(figsize=(5.6, 2.8))
    ax.plot(anos, mg_ar.loc[anos] / 1e6, "-o", color=AZUL, lw=2, ms=5, label="MG arábica")
    ax.plot(anos, sul_ano.loc[anos] / 1e6, "-o", color=LARANJA, lw=2, ms=5, label="Sul/Sudoeste de Minas")
    ax.set_xticks(anos)
    ax.set_ylabel("produção (milhões de t)")
    ax.set_ylim(0, None)
    ax.legend(loc="lower right")
    salvar(fig, "serie_anual")

    # qualidade: codigos especiais, consistencia e variabilidade
    nao_disp = L[L["valor_bruto"] == "..."]
    zeros = L[L["valor_bruto"] == "-"]
    q_ano = nao_disp[nao_disp["variavel"] == "Quantidade produzida"].groupby("ano")["cod_ibge"].nunique()
    macro("NaoDispMunMax", str(int(q_ano.max())) if len(q_ano) else "0")
    macro("NaoDispMunMin", str(int(q_ano.min())) if len(q_ano) else "0")
    nd_ult = nao_disp[(nao_disp["ano"] == ANO) & (nao_disp["variavel"] == "Quantidade produzida")]
    macro("NaoDispSul", str(nd_ult[nd_ult["mesorregiao_id"] == MESO_SUL]["cod_ibge"].nunique()))
    macro("NaoDispReg", br(len(nao_disp)))
    macro("ZerosReg", br(len(zeros)))
    macro("TotalReg", br(len(L)))

    a = arab[(arab["ano"] == ANO) & (arab["producao_t"] > 0)].copy()
    a["prod_calc"] = a["area_colhida_ha"] * a["rendimento_kg_ha"] / 1000
    erro = (a["prod_calc"] / a["producao_t"] - 1).abs()
    macro("ErroIdentMed", br(100 * erro.median(), 2))
    macro("ErroIdentMax", br(100 * erro.max(), 1))
    rend = a["rendimento_kg_ha"]
    q1, q3 = rend.quantile([0.25, 0.75])
    out = a[(rend < q1 - 1.5 * (q3 - q1)) | (rend > q3 + 1.5 * (q3 - q1))]
    macro("RendMed", br(rend.median()))
    macro("RendMin", br(rend.min()))
    macro("RendMax", br(rend.max()))
    macro("RendOut", str(len(out)))

    piv = sul.pivot_table(index="cod_ibge", columns="ano", values="producao_t")
    piv = piv[(piv > 0).all(axis=1)]
    cv = piv.std(axis=1) / piv.mean(axis=1)
    macro("CVMed", br(100 * cv.median(), 1))
    macro("CVPnov", br(100 * cv.quantile(0.9), 1))
    macro("NMunCV", str(len(piv)))
    return sul_ano, c_sul


# ---------------------------------------------------------------- 2. diesel (ANP)
def analisar_diesel():
    D = pd.read_csv(os.path.join(PROC, "anp_diesel_mg_semanal.csv"), parse_dates=["data_final"])
    s10 = D[D["produto"] == "OLEO DIESEL S10"].set_index("data_final")["preco_medio"]
    s500 = D[D["produto"] == "OLEO DIESEL"].set_index("data_final")["preco_medio"]
    fim = s10.index.max()
    j = s10[s10.index > fim - pd.Timedelta(weeks=104)]
    p10, p50, p90 = j.quantile([0.1, 0.5, 0.9])
    semanas_esperadas = int((s10.index.max() - s10.index.min()).days / 7) + 1
    macro("DieselFim", fim.strftime("%d/%m/%Y"))
    macro("DieselUlt", br(s10.iloc[-1], 2))
    macro("DieselSemanas", str(len(s10)))
    macro("DieselFaltam", str(semanas_esperadas - len(s10)))
    macro("DieselPdez", br(p10, 2))
    macro("DieselPcinq", br(p50, 2))
    macro("DieselPnov", br(p90, 2))
    macro("DieselSpread", br(100 * ((s500 - s10).dropna() / s10).loc[j.index].mean(), 1))
    macro("PostosMed", br(D[D["produto"] == "OLEO DIESEL S10"]["postos"].tail(104).median()))

    linhas = []
    for nome, p in (("baixo (P10)", p10), ("base (P50)", p50), ("alto (P90)", p90)):
        linhas.append({"Cenário": nome, "Diesel S10 (R\\$/L)": br(p, 2),
                       "Custo por km (R\\$/km)": br(C_KM + CONSUMO * p, 2)})
    macro("CustoKmDif", br(100 * (CONSUMO * (p90 - p10)) / (C_KM + CONSUMO * p10), 1))
    macro("PctDieselKm", br(100 * CONSUMO * p50 / (C_KM + CONSUMO * p50)))
    tabela_tex("diesel_cenarios", pd.DataFrame(linhas), "lrr",
               "Cenários de preço do diesel S10 em MG (últimas 104 semanas) e custo por quilômetro.",
               "tab:diesel",
               f"Custo por km $= c^{{km}} + p\\,g$, com $c^{{km}} = {br(C_KM, 2)}$ R\\$/km e "
               f"$g = {br(CONSUMO, 2)}$ L/km (hipóteses do Nível 1).")

    fig, ax = plt.subplots(figsize=(5.6, 2.8))
    ax.plot(s10.index, s10.values, color=AZUL, lw=1.4, label="diesel S10 (média semanal MG)")
    ax.plot(s500.index, s500.values, color=LARANJA, lw=1.0, alpha=0.9, label="diesel S500")
    ax.fill_between([j.index.min(), fim], p10, p90, color=AZUL, alpha=0.12, lw=0,
                    label="P10–P90 do S10 (104 semanas)")
    ax.set_ylabel("R$/L (nominal)")
    ax.legend(loc="upper left")
    salvar(fig, "diesel")


# ---------------------------------------------------------------- 3. distancias (OSRM)
def analisar_distancias():
    N = pd.read_csv(os.path.join(PROC, "osrm_nos.csv"))
    d = pd.read_csv(os.path.join(PROC, "osrm_dist_km.csv"), index_col=0)
    t = pd.read_csv(os.path.join(PROC, "osrm_tempo_h.csv"), index_col=0)
    h = pd.read_csv(os.path.join(PROC, "haversine_km.csv"), index_col=0)
    ids = list(d.index)
    pares = [(i, j) for i in ids for j in ids if i != j and h.loc[i, j] > 5]
    razao = np.array([d.loc[i, j] / h.loc[i, j] for i, j in pares])
    vel = np.array([d.loc[i, j] / t.loc[i, j] for i, j in pares])
    assim = np.array([abs(d.loc[i, j] - d.loc[j, i]) / max(d.loc[i, j], d.loc[j, i]) for i, j in pares])
    macro("NNosOSRM", str(len(ids)))
    macro("NParesOSRM", br(len(pares)))
    macro("CircMed", br(np.median(razao), 2))
    macro("CircMedia", br(razao.mean(), 2))
    macro("CircPdez", br(np.quantile(razao, 0.1), 2))
    macro("CircPnov", br(np.quantile(razao, 0.9), 2))
    macro("VelMed", br(np.median(vel), 1))
    macro("AssimMed", br(100 * np.median(assim), 1))
    macro("AssimMax", br(100 * assim.max(), 1))
    macro("SnapMax", br(N["snap_m"].max()))

    col = [c for c in ids if c.startswith("C")]
    term = [c for c in ids if c.startswith("T_")]
    linhas = []
    for tt in term:
        nome = {"T_JF": "Juiz de Fora (porto seco)", "T_UBA": "Uberaba (porto seco)", "T_VAG": "Varginha (CLIA)",
                "T_PAL": "Pouso Alegre (CLIA)", "T_BET": "Betim (CLIA)"}.get(tt, N.set_index("no").loc[tt, "nome"])
        linhas.append({"Terminal": nome,
                       "Dist. média (km)": br(d.loc[col, tt].mean()),
                       "Dist. mín.--máx. (km)": f"{br(d.loc[col, tt].min())}--{br(d.loc[col, tt].max())}",
                       "Tempo médio (h)": br(t.loc[col, tt].mean(), 1)})
    tabela_tex("dist_terminais", pd.DataFrame(linhas), "lrrr",
               f"Distância rodoviária (OSRM) dos {len(col)} maiores municípios produtores do Sul/Sudoeste "
               "até cada recinto alfandegado.", "tab:dist_terminais")

    fig, ax = plt.subplots(figsize=(5.0, 3.2))
    hh = np.array([h.loc[i, j] for i, j in pares])
    dd = np.array([d.loc[i, j] for i, j in pares])
    ax.scatter(hh, dd, s=8, color=AZUL, alpha=0.35, edgecolor="none", label="pares de nós")
    xs = np.linspace(0, hh.max(), 50)
    ax.plot(xs, xs * 1.25, color=LARANJA, lw=1.6, label="fator 1,25 (instâncias sintéticas)")
    ax.plot(xs, xs * np.median(razao), color=AQUA, lw=1.6, ls="--",
            label=f"mediana observada ({br(np.median(razao), 2)})")
    ax.set_xlabel("distância em linha reta (km)")
    ax.set_ylabel("distância rodoviária OSRM (km)")
    ax.legend(loc="upper left", fontsize=7)
    salvar(fig, "circuidade")


# ---------------------------------------------------------------- 4. tamanho da instancia
def tamanho_instancia(sul_ano):
    prod = sul_ano[ANO]
    viagens_ano = prod / Q
    macro("ViagensAno", br(viagens_ano))
    macro("ViagensDia", br(viagens_ano / DIAS_UTEIS))
    macro("TonDia", br(prod / DIAS_UTEIS))
    macro("DiasUteis", str(DIAS_UTEIS))
    macro("CapQ", br(Q))

    esc = pd.read_csv(os.path.join(BASE, "escalabilidade_nivel1.csv"))
    ultimo_otimo = esc[~esc["parou_no_limite"]]["n_coletas"].max()
    macro("NOtimoNivelUm", str(int(ultimo_otimo)))

    m = 5
    linhas = []
    for nome, n in (("instância de teste (Nível 1)", 8), ("50\\% da produção do Sul/Sudoeste", int(MACROS["NSulCinquenta"])),
                    ("80\\% da produção", int(MACROS["NSulOitenta"])), ("90\\% da produção", int(MACROS["NSulNoventa"])),
                    ("todos os produtores", int(MACROS["NMunSul"]))):
        nbin = n + n * (n - 1) + n * m
        ncons = 2 * n + m + 1 + 2 * n * (n - 1) + n * m
        if n == int(MACROS["NSulOitenta"]):
            macro("BinOitenta", br(nbin))
            macro("RazaoBin", br(nbin / (8 + 8 * 7 + 8 * m)))
        linhas.append({"Escopo": nome, "$n$": n, "$m$": m, "Binárias": br(nbin), "Contínuas": br(2 * n),
                       "Restrições (aprox.)": br(ncons)})
    tabela_tex("tamanho", pd.DataFrame(linhas), "lrrrrr",
               "Tamanho do modelo PLI do Nível 1 em função do escopo da instância real.", "tab:tamanho",
               "Binárias $= n + n(n-1) + nm$; restrições $\\approx 2n + m + 1 + 2n(n-1) + nm$ "
               "(fluxo, carga, tempo e terminal), conforme \\texttt{02\\_modelo\\_PLI\\_nivel1.md}.")

    linhas = [{"$n$": int(r.n_coletas), "Binárias": int(r.binarias), "Variáveis": int(r.variaveis),
               "Restrições": int(r.restricoes), "Tempo (s)": br(r.tempo_s, 2),
               "Ótimo provado": "não" if r.parou_no_limite else "sim"} for r in esc.itertuples()]
    tabela_tex("escalabilidade", pd.DataFrame(linhas), "rrrrrc",
               "Escalabilidade do modelo exato do Nível 1 (CBC, limite de 20 s, instâncias sintéticas).",
               "tab:escalabilidade")


def main():
    os.makedirs(FIG, exist_ok=True)
    os.makedirs(TAB, exist_ok=True)
    sul_ano, _ = analisar_producao()
    analisar_diesel()
    analisar_distancias()
    tamanho_instancia(sul_ano)
    with open(os.path.join(REL, "valores.tex"), "w", encoding="utf-8") as f:
        f.write("% Gerado por fase1/analise_exploratoria.py - nao editar a mao\n")
        for k, v in MACROS.items():
            f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    print(f"[eda] {len(MACROS)} macros, figuras em {FIG}")
    for k, v in MACROS.items():
        print(f"  {k} = {v}")


if __name__ == "__main__":
    main()
