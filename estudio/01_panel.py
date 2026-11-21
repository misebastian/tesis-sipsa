"""Paso 1. Construye el panel supervisado: una fila por serie (central x producto) y mes t con variables
conocidas al cierre de t, y el objetivo y = log p(t+1) - log p(t) (solo si ambos precios están observados).
Las series se seleccionan con precios hasta dic-2024 y el ONI se toma con dos meses de rezago para evitar fuga de información."""
import warnings
import numpy as np, pandas as pd
from comun import DATOS, BLOQUES_NUEVOS
warnings.filterwarnings("ignore")
UMBRAL = np.log(1.15)
ERRORES = [("Bogotá, D.C., Paloquemao", "Pastas alimenticias", "2024-02-01")]
PERECIBILIDAD = {"FRUTAS": 2, "VERDURAS Y HORTALIZAS": 2, "TUBERCULOS, RAICES Y PLATANOS": 1,
                 "LACTEOS Y HUEVOS": 1, "GRANOS Y CEREALES": 0, "PROCESADOS": 0, "PESCADOS": 1}
PASCUA = ["2018-04-01", "2019-04-21", "2020-04-12", "2021-04-04", "2022-04-17", "2023-04-09",
          "2024-03-31", "2025-04-20", "2026-04-05", "2027-03-28"]


def ciudad(m):
    m = m.replace('"', "")
    p = m.split(", ")
    c = ", ".join(p[:-1]) if len(p) > 1 else m
    return c.replace(", D.C.", "").split(" (")[0]


def oni():
    o = pd.read_csv(DATOS / "oni_v6.csv").melt("year", var_name="s", value_name="oni").dropna()
    centro = {s: i + 1 for i, s in enumerate(["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"])}
    o["mes"] = pd.to_datetime(dict(year=o.year, month=o.s.map(centro), day=1))
    return o.set_index("mes").oni.sort_index()


def construir(corte_series="2024-12-01", rezago_oni=2, guardar=True):
    B = pd.read_parquet(DATOS / "base_unida_mensual.parquet")
    for m, a, t in ERRORES:
        B.loc[(B.mercado == m) & (B.alimento == a) & (B.mes == pd.Timestamp(t)), "precio"] = np.nan
    meses = pd.date_range(B.mes.min(), B.mes.max(), freq="MS", name="mes")
    b = B[B.unidad == "$/kg"].copy()
    nobs = b[b.precio.notna() & (b.mes <= corte_series)].groupby(["mercado", "alimento"]).size()
    series = nobs[nobs >= 48].index
    W = lambda col, d=b: d.pivot_table(index=["mercado", "alimento"], columns="mes", values=col, aggfunc="first").reindex(columns=meses)
    LPo = np.log(W("precio")); LP = LPo.ffill(axis=1, limit=2)
    LT = np.log(W("ton").astype(float).clip(lower=0.1))
    MP = W("municipios_origen"); DP = W("departamentos_origen"); DI = W("dias_con_registro")
    R1 = LP.diff(axis=1); alza = (R1 > UMBRAL).astype(float).where(R1.notna())
    F = {}
    for k in (1, 2, 3, 6, 12): F[f"cambio_{k}m"] = LP - LP.shift(k, axis=1)
    for k in (1, 2, 3): F[f"cambio_mes_rez{k}"] = R1.shift(k, axis=1)
    for v in (3, 6, 12): F[f"vol_{v}m"] = R1.T.rolling(v, min_periods=max(2, v - 2)).std().T
    m12 = LP.T.rolling(12, min_periods=9).mean().T; s12 = LP.T.rolling(12, min_periods=9).std().T
    F["z_precio_12m"] = (LP - m12) / s12.replace(0, np.nan)
    F["dist_max_12m"] = LP - LP.T.rolling(12, min_periods=9).max().T
    F["dist_min_12m"] = LP - LP.T.rolling(12, min_periods=9).min().T
    F["alzas_12m"] = alza.T.rolling(12, min_periods=9).sum().T
    A = alza.fillna(0).values; out = np.full(A.shape, 24.0); c = np.full(A.shape[0], 24.0)
    for j in range(A.shape[1]):
        c = np.where(A[:, j] == 1, 0, np.minimum(c + 1, 24)); out[:, j] = c
    F["meses_desde_alza"] = pd.DataFrame(out, index=LP.index, columns=meses)
    F["cambio_ton_1m"] = LT.diff(axis=1); F["cambio_ton_12m"] = LT - LT.shift(12, axis=1)
    F["ton_rel_12m"] = LT - LT.shift(1, axis=1).T.rolling(12, min_periods=9).mean().T
    F["log_municipios"] = np.log1p(MP); F["departamentos"] = DP; F["dias_registro"] = DI
    S = LP.groupby(level="alimento").transform("sum"); N = LP.notna().groupby(level="alimento").transform("sum")
    otras = (S - LP.fillna(0)) / (N - LP.notna()).replace(0, np.nan)
    F["brecha_nacional"] = LP - otras; F["cambio_nacional_1m"] = otras.diff(axis=1)
    Su = alza.fillna(0).groupby(level="alimento").transform("sum"); Nu = alza.notna().groupby(level="alimento").transform("sum")
    F["prop_centrales_alza"] = (Su - alza.fillna(0)) / (Nu - alza.notna()).replace(0, np.nan)
    # información de t+1 de las DEMÁS centrales: solo para el análisis de faltantes (07); nunca es variable predictora
    F["fut_cambio_otras"] = F["cambio_nacional_1m"].shift(-1, axis=1); F["fut_prop_otras"] = F["prop_centrales_alza"].shift(-1, axis=1)
    F["obs_t"] = LPo.notna().astype(float)
    # ---- nuevas candidatas ----
    F["desv_ma3"] = LP - LP.T.rolling(3, min_periods=2).mean().T
    F["desv_ma6"] = LP - LP.T.rolling(6, min_periods=4).mean().T
    F["cambio_mismo_mes_ano_ant"] = R1.shift(11, axis=1)                       # cambio de t-11 a t-10 = el del mes objetivo un año antes
    F["cambio_nacional_mismo_mes_ano_ant"] = otras.diff(axis=1).shift(11, axis=1)
    F["cambio_nacional_2m"] = otras - otras.shift(2, axis=1); F["cambio_nacional_12m"] = otras - otras.shift(12, axis=1)
    F["brecha_nacional_cambio"] = F["brecha_nacional"].diff(axis=1)
    grp = b.drop_duplicates(["mercado", "alimento"]).set_index(["mercado", "alimento"]).grupo.reindex(LP.index)
    key = pd.MultiIndex.from_arrays([LP.index.get_level_values("mercado"), grp.values])
    R1g = R1.copy(); R1g.index = key; Ag = alza.copy(); Ag.index = key
    sg = R1g.fillna(0).groupby(level=[0, 1]).transform("sum").values; ng = R1g.notna().groupby(level=[0, 1]).transform("sum").values
    F["cambio_grupo_central"] = pd.DataFrame((sg - R1.fillna(0).values) / np.where(ng - R1.notna().values > 0, ng - R1.notna().values, np.nan), index=LP.index, columns=meses)
    sa = Ag.fillna(0).groupby(level=[0, 1]).transform("sum").values; na = Ag.notna().groupby(level=[0, 1]).transform("sum").values
    F["alzas_grupo_central"] = pd.DataFrame((sa - alza.fillna(0).values) / np.where(na - alza.notna().values > 0, na - alza.notna().values, np.nan), index=LP.index, columns=meses)
    # abastecimiento nacional del producto (todas las centrales con registro de toneladas, con o sin precio)
    Ta = B.pivot_table(index="alimento", columns="mes", values="ton", aggfunc="sum").reindex(columns=meses).astype(float)
    LTn = np.log(Ta.clip(lower=0.1))
    tn1 = LTn.diff(axis=1); tnr = LTn - LTn.shift(1, axis=1).T.rolling(12, min_periods=9).mean().T
    al = LP.index.get_level_values("alimento")
    F["cambio_ton_nacional_1m"] = pd.DataFrame(tn1.reindex(al).values, index=LP.index, columns=meses)
    F["ton_nacional_rel_12m"] = pd.DataFrame(tnr.reindex(al).values, index=LP.index, columns=meses)
    F["participacion_central"] = pd.DataFrame(W("ton").astype(float).values / Ta.reindex(al).values, index=LP.index, columns=meses)
    F["dias_registro_rel"] = DI - DI.shift(1, axis=1).T.rolling(12, min_periods=6).mean().T   # días con registro frente a su promedio
    F["meses_obs_12m"] = LPo.notna().astype(float).T.rolling(12, min_periods=1).sum().T
    Y = LPo.shift(-1, axis=1) - LPo
    largo = lambda X, nm: X.stack(future_stack=True).rename(nm)
    P = pd.concat([largo(Y, "y")] + [largo(v, k) for k, v in F.items()], axis=1).reset_index()
    P = P[P.set_index(["mercado", "alimento"]).index.isin(series)]
    P = P[P.cambio_12m.notna() & (P.mes >= "2019-01-01") & (P.mes < meses[-1]) & (P.y.notna() | (P.obs_t == 1))].copy()
    g = b.drop_duplicates(["mercado", "alimento"]).set_index(["mercado", "alimento"]).grupo
    P["grupo"] = g.reindex(pd.MultiIndex.from_frame(P[["mercado", "alimento"]])).values.astype(str)
    P["ciudad"] = P.mercado.map(ciudad); P["perecibilidad"] = P.grupo.map(PERECIBILIDAD)
    P["mes_obj"] = P.mes + pd.DateOffset(months=1); c = P.mes_obj.dt.month
    P["mes_sin"], P["mes_cos"] = np.sin(2 * np.pi * c / 12), np.cos(2 * np.pi * c / 12)
    pas = pd.to_datetime(PASCUA)
    P["semana_santa"] = P.mes_obj.isin(pd.to_datetime(dict(year=pas.year, month=pas.month, day=1))).astype(int)
    P["diciembre"] = (c == 12).astype(int)
    H = R1.stack(future_stack=True).rename("r").reset_index(); H.columns = ["mercado", "alimento", "mes", "r"]; H = H.dropna()
    H["ano"], H["m"] = H.mes.dt.year, H.mes.dt.month; H["alza"] = (H.r > UMBRAL).astype(int)
    fa = H.groupby(["alimento", "m", "ano"]).agg(s=("alza", "sum"), n=("alza", "size")).reset_index().sort_values("ano")
    fa[["cs", "cn"]] = fa.groupby(["alimento", "m"])[["s", "n"]].cumsum() - fa[["s", "n"]].values
    fa["frec_alza_hist"] = (fa.cs + 1) / (fa.cn + 6)
    em = H.groupby(["mercado", "alimento", "m", "ano"]).r.mean().reset_index().sort_values("ano")
    em["cambio_estacional_hist"] = em.groupby(["mercado", "alimento", "m"]).r.transform(lambda s: s.shift().expanding().mean())
    P["ano_obj"], P["m_obj"] = P.mes_obj.dt.year, c
    P = P.merge(fa[["alimento", "m", "ano", "frec_alza_hist"]].rename(columns={"m": "m_obj", "ano": "ano_obj"}), how="left", on=["alimento", "m_obj", "ano_obj"])
    P = P.merge(em[["mercado", "alimento", "m", "ano", "cambio_estacional_hist"]].rename(columns={"m": "m_obj", "ano": "ano_obj"}), how="left", on=["mercado", "alimento", "m_obj", "ano_obj"])
    o = oni()
    P["oni"] = (P.mes - pd.DateOffset(months=rezago_oni)).map(o)
    P["oni_cambio_3m"] = P.oni - (P.mes - pd.DateOffset(months=rezago_oni + 3)).map(o)
    for k in ("grupo", "ciudad", "mercado", "alimento"):
        P[k + "_c"] = P[k].astype("category").cat.codes
    P["alza"] = (P.y > UMBRAL).astype(int)
    P["muestra"] = np.where(P.mes_obj <= "2023-12-01", "entrenamiento", np.where(P.mes_obj <= "2024-12-01", "validacion", "prueba"))
    P = P.drop(columns=["ano_obj", "m_obj"])
    sin = P[P.y.isna()].drop(columns=["alza"]).copy()     # p_t observado y p_{t+1} faltante
    P = P[P.y.notna()].copy()
    if guardar:
        P.to_parquet(DATOS / "panel.parquet"); sin.to_parquet(DATOS / "panel_sin_objetivo.parquet")
    return P



if __name__ == "__main__":
    P = construir()
    print("panel:", P.shape, P.groupby("muestra").size().to_dict(), "series:", P[["mercado", "alimento"]].drop_duplicates().shape[0])
