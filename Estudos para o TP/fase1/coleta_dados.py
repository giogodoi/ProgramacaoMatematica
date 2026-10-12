"""Fase 1 - coleta dos dados publicos usados no trabalho (GCC118, UFLA 2026/2).

Baixa as fontes brutas para ``dados/brutos`` e grava as tabelas limpas em
``dados/processados``. Uso (a partir da pasta "Estudos para o TP"):

    python fase1/coleta_dados.py            # baixa tudo e processa
    python fase1/coleta_dados.py --offline  # reprocessa os arquivos ja baixados

Fontes:
- PAM/IBGE (SIDRA, tabela 1613): producao municipal de cafe arabica e canephora.
- IBGE Localidades: meso/microrregiao e regiao intermediaria de cada municipio.
- Coordenadas das sedes municipais: repositorio kelvins/municipios-brasileiros.
- ANP: levantamento semanal de precos por estado (diesel S10 e S500).
- Receita Federal: lista oficial de portos secos (fev/2023) e ata Colfac-MG (nov/2022)
  para os CLIAs. A tabela de terminais e montada aqui, com a fonte de cada linha.
- OSRM (servidor publico de demonstracao): matriz rodoviaria de distancia e tempo.
"""

import argparse, json, math, os, sys, time
from datetime import date

import pandas as pd
import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRUTOS = os.path.join(BASE, "dados", "brutos")
PROC = os.path.join(BASE, "dados", "processados")
HDR = {"User-Agent": "Mozilla/5.0 (GCC118-UFLA trabalho academico)"}

ANOS_PAM = 5                 # serie 2021-2025 (ultimos 5 anos publicados)
MESO_SUL = 3110              # mesorregiao Sul/Sudoeste de Minas (IBGE)
N_OSRM = 30                  # municipios do Sul de Minas na matriz OSRM (maiores produtores)
GARAGEM = 3170701            # Varginha: base da frota assumida (polo cafeeiro do Sul de Minas)

URL = {
    "sidra_mun": "https://apisidra.ibge.gov.br/values/t/1613/n6/in%20n3%2031/v/214,216,112,215/p/last%20{a}/c82/31619,31620",
    "sidra_uf": "https://apisidra.ibge.gov.br/values/t/1613/n1/all/n3/all/v/214/p/last%20{a}/c82/31619,31620",
    "localidades": "https://servicodados.ibge.gov.br/api/v1/localidades/estados/31/municipios",
    "coords": "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv",
    "anp": "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/"
           "precos-revenda-e-de-distribuicao-combustiveis/shlp/semanal/semanal-estados-desde-2013.xlsx",
    "osrm": "https://router.project-osrm.org/table/v1/driving/{coords}?annotations=distance,duration",
}

# Recintos alfandegados de zona secundaria em MG. "porto_seco" = lista oficial da Receita
# (PortosSecosFev2023.pdf); "CLIA" = representantes na 2a reuniao Colfac-MG (17/11/2022).
TERMINAIS = [
    dict(terminal="T_JF", nome="Porto Seco de Juiz de Fora (Multiterminais)", tipo="porto_seco",
         cod_ibge=3136702, codigo_recinto="6.35.32.01-8", fonte="Receita Federal, PortosSecosFev2023"),
    dict(terminal="T_UBA", nome="Porto Seco do Triângulo (EADI Uberaba)", tipo="porto_seco",
         cod_ibge=3170107, codigo_recinto="6.45.32.01-1", fonte="Receita Federal, PortosSecosFev2023"),
    dict(terminal="T_VAG", nome="CLIA Varginha", tipo="CLIA",
         cod_ibge=3170701, codigo_recinto="", fonte="Ata 2a reuniao Colfac-MG, 17/11/2022"),
    dict(terminal="T_PAL", nome="CLIA Pouso Alegre", tipo="CLIA",
         cod_ibge=3152501, codigo_recinto="", fonte="Ata 2a reuniao Colfac-MG, 17/11/2022"),
    dict(terminal="T_BET", nome="CLIA Betim (TORA)", tipo="CLIA",
         cod_ibge=3106705, codigo_recinto="", fonte="Ata 2a reuniao Colfac-MG, 17/11/2022"),
]


def baixar(nome, url, arquivo, offline):
    caminho = os.path.join(BRUTOS, arquivo)
    if offline and os.path.exists(caminho):
        return caminho
    print(f"[coleta] {nome}: {url[:90]}...")
    for tentativa in range(4):  # o SIDRA as vezes derruba a conexao; tenta de novo com espera
        try:
            r = requests.get(url, timeout=300, headers=HDR)
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if tentativa == 3:
                raise
            print(f"[coleta] falhou ({e.__class__.__name__}), nova tentativa em {5 * (tentativa + 1)} s")
            time.sleep(5 * (tentativa + 1))
    with open(caminho, "wb") as f:
        f.write(r.content)
    return caminho


def sidra_para_df(caminho):
    """Converte o JSON do SIDRA em tabela longa; mantem os codigos especiais (-, .., ..., X)."""
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    df = pd.DataFrame(dados[1:])
    df = df.rename(columns={"D1C": "cod", "D1N": "local", "D2N": "variavel", "D3N": "ano",
                            "D4N": "produto", "MN": "unidade", "V": "valor_bruto"})
    df["valor"] = pd.to_numeric(df["valor_bruto"], errors="coerce")
    df["ano"] = df["ano"].astype(int)
    df["produto"] = df["produto"].str.replace("Café (em grão) ", "", regex=False).str.lower()
    return df[["cod", "local", "variavel", "unidade", "ano", "produto", "valor_bruto", "valor"]]


def processar_pam(off):
    mun = sidra_para_df(baixar("PAM municipios MG", URL["sidra_mun"].format(a=ANOS_PAM), "pam_1613_mg_municipios.json", off))
    uf = sidra_para_df(baixar("PAM Brasil/UF", URL["sidra_uf"].format(a=ANOS_PAM), "pam_1613_brasil_uf.json", off))
    with open(baixar("IBGE localidades", URL["localidades"], "ibge_localidades_mg.json", off), encoding="utf-8") as f:
        loc = pd.DataFrame([dict(cod_ibge=m["id"], municipio=m["nome"],
                                 microrregiao=m["microrregiao"]["nome"],
                                 mesorregiao_id=m["microrregiao"]["mesorregiao"]["id"],
                                 mesorregiao=m["microrregiao"]["mesorregiao"]["nome"],
                                 reg_intermediaria=m["regiao-imediata"]["regiao-intermediaria"]["nome"])
                            for m in json.load(f)])
    coords = pd.read_csv(baixar("coordenadas", URL["coords"], "municipios_coordenadas.csv", off))
    coords = coords.rename(columns={"codigo_ibge": "cod_ibge"})[["cod_ibge", "latitude", "longitude"]]

    mun["cod_ibge"] = mun["cod"].astype(int)
    longa = mun.merge(loc, on="cod_ibge", how="left").merge(coords, on="cod_ibge", how="left")
    longa.to_csv(os.path.join(PROC, "pam_mg_longa.csv"), index=False)

    # tabela larga: uma linha por municipio x ano x produto
    larga = longa.pivot_table(index=["cod_ibge", "municipio", "mesorregiao_id", "mesorregiao", "microrregiao",
                                     "reg_intermediaria", "latitude", "longitude", "ano", "produto"],
                              columns="variavel", values="valor", aggfunc="first").reset_index()
    larga.columns.name = None
    larga = larga.rename(columns={"Quantidade produzida": "producao_t", "Área colhida": "area_colhida_ha",
                                  "Rendimento médio da produção": "rendimento_kg_ha",
                                  "Valor da produção": "valor_mil_reais"})
    larga.to_csv(os.path.join(PROC, "pam_mg_municipios.csv"), index=False)

    uf = uf.rename(columns={"cod": "cod_local"})
    uf.to_csv(os.path.join(PROC, "pam_brasil_uf.csv"), index=False)
    print(f"[pam] {larga['cod_ibge'].nunique()} municipios, anos {sorted(larga['ano'].unique())}")
    return larga, coords


def processar_anp(off):
    caminho = baixar("ANP semanal estados", URL["anp"], "anp_semanal_estados_desde_2013.xlsx", off)
    bruto = pd.read_excel(caminho, header=None)
    linha_cab = bruto.index[bruto[0].astype(str).str.strip().eq("DATA INICIAL")][0]
    df = bruto.iloc[linha_cab + 1:].copy()
    df.columns = [str(c).strip() for c in bruto.iloc[linha_cab]]
    df = df[(df["ESTADO"] == "MINAS GERAIS") & df["PRODUTO"].astype(str).str.contains("DIESEL")]
    df = df.rename(columns={"DATA INICIAL": "data_inicial", "DATA FINAL": "data_final", "PRODUTO": "produto",
                            "NÚMERO DE POSTOS PESQUISADOS": "postos", "PREÇO MÉDIO REVENDA": "preco_medio",
                            "DESVIO PADRÃO REVENDA": "desvio_padrao", "PREÇO MÍNIMO REVENDA": "preco_min",
                            "PREÇO MÁXIMO REVENDA": "preco_max"})
    df = df[["data_inicial", "data_final", "produto", "postos", "preco_medio", "desvio_padrao", "preco_min", "preco_max"]]
    for c in ["postos", "preco_medio", "desvio_padrao", "preco_min", "preco_max"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["data_final"] = pd.to_datetime(df["data_final"])
    df["data_inicial"] = pd.to_datetime(df["data_inicial"])
    df = df.sort_values(["produto", "data_final"])
    df.to_csv(os.path.join(PROC, "anp_diesel_mg_semanal.csv"), index=False)
    print(f"[anp] {len(df)} semanas-produto, ate {df['data_final'].max().date()}")
    return df


def montar_terminais(coords):
    t = pd.DataFrame(TERMINAIS).merge(coords, on="cod_ibge", how="left")
    t["coordenada"] = "sede municipal (aproximacao; portao do recinto a georreferenciar)"
    t.to_csv(os.path.join(PROC, "terminais_mg.csv"), index=False)
    return t


def haversine_km(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def processar_osrm(pam, term, off):
    """Matriz OSRM: garagem + N_OSRM maiores produtores do Sul de Minas + terminais."""
    ult = pam[(pam["ano"] == pam["ano"].max()) & (pam["produto"] == "arábica") & (pam["mesorregiao_id"] == MESO_SUL)]
    top = ult.nlargest(N_OSRM, "producao_t")
    gar = pam[pam["cod_ibge"] == GARAGEM].iloc[0]
    nos = [dict(no="G", tipo="garagem", cod_ibge=GARAGEM, nome=gar["municipio"], latitude=gar["latitude"],
                longitude=gar["longitude"], producao_t=0.0)]
    nos += [dict(no=f"C{k+1}", tipo="coleta", cod_ibge=int(r.cod_ibge), nome=r.municipio, latitude=r.latitude,
                 longitude=r.longitude, producao_t=r.producao_t) for k, r in enumerate(top.itertuples())]
    nos += [dict(no=r.terminal, tipo=r.tipo, cod_ibge=int(r.cod_ibge), nome=r.nome, latitude=r.latitude,
                 longitude=r.longitude, producao_t=0.0) for r in term.itertuples()]
    nos = pd.DataFrame(nos)
    nos.to_csv(os.path.join(PROC, "osrm_nos.csv"), index=False)

    caminho = os.path.join(BRUTOS, "osrm_table.json")
    if not (off and os.path.exists(caminho)):
        cs = ";".join(f"{lo:.5f},{la:.5f}" for la, lo in zip(nos["latitude"], nos["longitude"]))
        baixar("OSRM table", URL["osrm"].format(coords=cs), "osrm_table.json", False)
        time.sleep(1)
    with open(caminho, encoding="utf-8") as f:
        res = json.load(f)
    assert res["code"] == "Ok", res.get("message")
    ids = list(nos["no"])
    pd.DataFrame(res["distances"], index=ids, columns=ids).div(1000).round(2).to_csv(os.path.join(PROC, "osrm_dist_km.csv"))
    pd.DataFrame(res["durations"], index=ids, columns=ids).div(3600).round(4).to_csv(os.path.join(PROC, "osrm_tempo_h.csv"))
    snap = [w["distance"] for w in res["sources"]]
    nos["snap_m"] = snap
    nos.to_csv(os.path.join(PROC, "osrm_nos.csv"), index=False)
    pts = list(zip(nos["latitude"], nos["longitude"]))
    pd.DataFrame([[haversine_km(a, b) for b in pts] for a in pts], index=ids, columns=ids).round(2) \
        .to_csv(os.path.join(PROC, "haversine_km.csv"))
    print(f"[osrm] matriz {len(ids)}x{len(ids)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="reprocessa os brutos sem baixar de novo")
    a = ap.parse_args()
    os.makedirs(BRUTOS, exist_ok=True)
    os.makedirs(PROC, exist_ok=True)
    pam, coords = processar_pam(a.offline)
    processar_anp(a.offline)
    term = montar_terminais(coords)
    processar_osrm(pam, term, a.offline)
    with open(os.path.join(PROC, "LEIAME_coleta.txt"), "w", encoding="utf-8") as f:
        f.write(f"Dados extraidos em {date.today().isoformat()} por fase1/coleta_dados.py\n")
        for k, u in URL.items():
            f.write(f"{k}: {u}\n")


if __name__ == "__main__":
    sys.exit(main())
