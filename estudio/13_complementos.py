"""Paso 13. Cálculos complementarios para el documento:
A) Diagnóstico de los SARIMA del corte de prueba: órdenes elegidos y prueba de Ljung-Box sobre los residuos de cada serie,
   más el detalle de una serie de ejemplo (ajuste, residuos y pronósticos de un paso con intervalo empírico del 80 %).
B) Error de cada modelo en la propia muestra de entrenamiento (2019-2024), para compararlo con validación y prueba.
Escribe resultados/sarima_diagnostico.parquet, sarima_ejemplo.parquet y complementos.json. No interviene en ninguna decisión."""
import time, warnings
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import average_precision_score
from comun import *
from modelos import REGRESION, CLASIFICACION, matrices, ajustar_ar
from sarima import rellenar
warnings.filterwarnings("ignore")
T0 = time.time(); log = lambda *a: print(f"[{time.time() - T0:5.0f}s]", *a, flush=True)
EJEMPLO = ("Medellín, Central Mayorista de Antioquia", "Mango Tommy")


def diagnostico(clave, y, meses, fin_aj, ejemplo=False):
    from statsforecast.models import AutoARIMA
    from statsmodels.stats.diagnostic import acorr_ljungbox
    idx = {m: i for i, m in enumerate(meses)}; n_aj = idx[fin_aj] + 1
    ya = rellenar(y[:n_aj]); ok = ~np.isnan(ya)
    if ok.sum() < 36: return None
    p0 = int(np.argmax(ok)); ya = ya[p0:]
    if np.isnan(ya).any(): ya = ya[:np.where(np.isnan(ya))[0][0]]
    if len(ya) < 36: return None
    try:
        m = AutoARIMA(season_length=12).fit(ya)
    except Exception:
        return None
    a = m.model_["arma"]; p, q, P_, Q_, s, d, D = [int(v) for v in a]
    res = np.asarray(m.model_["residuals"])[13:]; res = res[np.isfinite(res)]
    k = p + q + P_ + Q_
    lb = acorr_ljungbox(res, lags=[12, 24], model_df=k, return_df=True)["lb_pvalue"].values if len(res) > 30 else [np.nan, np.nan]
    fila = dict(mercado=clave[0], alimento=clave[1], p=p, d=d, q=q, P=P_, D=D, Q=Q_, n=len(ya), lb12=float(lb[0]), lb24=float(lb[1]),
                sd_res=float(np.std(res)))
    if not ejemplo: return fila
    yc = rellenar(y)[p0:]
    if np.isnan(yc).any(): yc = yc[:np.where(np.isnan(yc))[0][0]]
    f = m.forward(y=yc, h=1, fitted=True)["fitted"]; r_ = (ya - f[:len(ya)])[13:]; r_ = r_[np.isfinite(r_)]
    lo, hi = np.quantile(r_, [.10, .90])
    E = pd.DataFrame(dict(mes=meses[p0:p0 + len(yc)], y=yc, ajuste=f[:len(yc)]))
    E["dentro"] = np.arange(len(E)) < len(ya); E["lo80"] = E.ajuste + lo; E["hi80"] = E.ajuste + hi
    E["residuo"] = np.where(E.dentro, E.y - E.ajuste, np.nan); E.loc[:13, "residuo"] = np.nan
    return fila, E


if __name__ == "__main__":
    P = cargar_panel(); B = pd.read_parquet(DATOS / "base_unida_mensual.parquet"); b = B[B.unidad == "$/kg"]
    meses = pd.date_range(b.mes.min(), b.mes.max(), freq="MS")
    W = np.log(b.pivot_table(index=["mercado", "alimento"], columns="mes", values="precio", aggfunc="first").reindex(columns=meses))
    import importlib.util
    spec = importlib.util.spec_from_file_location("panel", RAIZ / "01_panel.py"); mp = importlib.util.module_from_spec(spec); spec.loader.exec_module(mp)
    for m_, a_, t_ in mp.ERRORES: W.loc[(m_, a_), pd.Timestamp(t_)] = np.nan
    W = W.ffill(axis=1, limit=2)
    series = list(P[["mercado", "alimento"]].drop_duplicates().itertuples(index=False, name=None))
    fin = pd.Timestamp("2024-12-01")
    filas = Parallel(n_jobs=NUCLEOS)(delayed(diagnostico)(s, W.loc[s].values, list(meses), fin) for s in series)
    D = pd.DataFrame([f for f in filas if f is not None]); D.to_parquet(RES / "sarima_diagnostico.parquet", index=False)
    _, E = diagnostico(EJEMPLO, W.loc[EJEMPLO].values, list(meses), fin, ejemplo=True); E.to_parquet(RES / "sarima_ejemplo.parquet", index=False)
    log("SARIMA:", len(D), "series; Ljung-Box(12) p>0,05:", round(float((D.lb12 > .05).mean()), 3))

    # B) error en entrenamiento
    V = variables_finales(); GRP = sorted(P.grupo.unique())
    RS, CS = leer_json("reg_seleccion.json"), leer_json("clf_seleccion.json")
    ent = P[P.muestra != "prueba"]; S = {"reg_entrenamiento": {}, "clf_entrenamiento": {}}
    S["reg_entrenamiento"]["Paseo aleatorio"] = float(ent.y.abs().mean())
    S["reg_entrenamiento"]["AR estacional"] = float(np.abs(ent.y - ajustar_ar(ent, ent, "reg")).mean())
    for nombre in RS["modelos"]:
        tipo, f, _ = REGRESION[nombre]; h = dict(RS["mejores"][nombre]["params"]); Xa, _ = matrices(V, GRP, tipo, ent, ent.iloc[:1])
        m = f(h); m.fit(Xa, ent.y.values); S["reg_entrenamiento"][nombre] = float(np.abs(ent.y.values - m.predict(Xa)).mean())
        log("entrenamiento", nombre, round(S["reg_entrenamiento"][nombre] * 100, 2))
    S["clf_entrenamiento"]["Logística autorregresiva"] = float(average_precision_score(ent.alza, ajustar_ar(ent, ent, "clf")))
    for nombre in CS["modelos"]:
        tipo, f, _ = CLASIFICACION[nombre]; h = dict(CS["mejores"][nombre]["params"]); Xa, _ = matrices(V, GRP, tipo, ent, ent.iloc[:1], imputar_arbol=True)
        m = f(h, 1.0); m.fit(Xa, ent.alza.values); S["clf_entrenamiento"][nombre] = float(average_precision_score(ent.alza.values, m.predict_proba(Xa)[:, 1]))
        log("entrenamiento", nombre, round(S["clf_entrenamiento"][nombre], 3))
    S["sarima"] = dict(series=int(len(D)), lb12=float((D.lb12 > .05).mean()), lb24=float((D.lb24 > .05).mean()), d1=float((D.d >= 1).mean()),
                       D1=float((D.D >= 1).mean()), estac=float(((D.P + D.Q + D.D) > 0).mean()),
                       ordenes=D.assign(o=D.apply(lambda r: f"({r.p},{r.d},{r.q})({r.P},{r.D},{r.Q})", axis=1)).o.value_counts().head(6).to_dict())
    guardar_json(S, "complementos.json"); log("fin")
