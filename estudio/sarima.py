"""Referencia SARIMA por serie (paso intermedio entre 03 y 04). Para cada serie producto-central se ajusta un SARIMA sobre el
logaritmo del precio con órdenes elegidos automáticamente por AICc (AutoARIMA, Hyndman y Khandakar, 2008; estacionalidad 12)
con los datos hasta el corte, y se pronostica un mes adelante con parámetros fijos actualizando con cada dato nuevo.
La probabilidad de alza usa los residuos de un paso de la propia serie en el periodo de ajuste (sin suponer normalidad).
Cortes: los tres de validación, el de la prueba y los siete del origen móvil. Salida: resultados/sarima.parquet."""
import os, time, warnings
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from comun import *
warnings.filterwarnings("ignore")
ORIGENES = pd.to_datetime(["2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01", "2026-01-01", "2026-04-01", "2026-07-01"])


def cortes_sarima(ultimo):
    """(nombre, último mes pronosticado en el ajuste, primer y último mes pronosticado a evaluar)."""
    c = [(f"cv{k}", pd.Timestamp(a), pd.Timestamp(a) + pd.DateOffset(months=1), pd.Timestamp(b)) for k, (a, b) in enumerate(CORTES_CV)]
    c.append(("prueba", pd.Timestamp("2024-12-01"), pd.Timestamp("2025-01-01"), ultimo))
    for k, o in enumerate(ORIGENES):
        fin = ORIGENES[k + 1] - pd.DateOffset(months=1) if k + 1 < len(ORIGENES) else ultimo
        c.append((f"movil{k}", o - pd.DateOffset(months=1), o, fin))
    return c


def rellenar(v):
    """Huecos interiores por interpolación lineal (el arrastre de 2 meses ya se aplicó); no extrapola."""
    return pd.Series(v).interpolate(limit_area="inside").values


def una_serie(clave, y, meses, cortes):
    """y: log precio con arrastre de hasta 2 meses. El relleno del periodo de ajuste usa solo datos hasta el corte; en el
    tramo de pronóstico, todo hueco anterior a un origen t termina a más tardar en t (el precio de t es observado)."""
    from statsforecast.models import AutoARIMA
    out = []; idx = {m: i for i, m in enumerate(meses)}; ycomp = rellenar(y)
    for nombre, fin_aj, ini, fin in cortes:
        n_aj = idx[fin_aj] + 1                                  # precio del mes fin_aj es el último usado
        ya = rellenar(y[:n_aj]); ok = ~np.isnan(ya)
        if ok.sum() < 36: continue
        p0 = int(np.argmax(ok)); ya = ya[p0:]
        if np.isnan(ya).any(): ya = ya[:np.where(np.isnan(ya))[0][0]]       # hueco abierto al final del ajuste
        if len(ya) < 36: continue
        try:
            m = AutoARIMA(season_length=12).fit(ya)
            yy = ycomp[p0:]
            if np.isnan(yy).any(): yy = yy[:np.where(np.isnan(yy))[0][0]]
            f = m.forward(y=yy, h=1, fitted=True)["fitted"]
        except Exception:
            continue
        res = (ya - f[:len(ya)])[13:]; res = res[np.isfinite(res)]
        if len(res) < 12: continue
        arma = m.model_["arma"]; estac = int(arma[2] + arma[3] + arma[6] > 0)
        for t_obj in pd.date_range(ini, fin, freq="MS"):
            i = idx[t_obj] - p0                                  # posición del mes pronosticado
            if i < 1 or i >= len(yy): continue
            pred = float(f[i] - yy[i - 1])                       # cambio pronosticado respecto del último precio
            out.append((nombre, *clave, t_obj, pred, float(np.mean(pred + res > UMBRAL)), estac))
    return out


if __name__ == "__main__":
    T0 = time.time()
    P = cargar_panel(); B = pd.read_parquet(DATOS / "base_unida_mensual.parquet"); b = B[B.unidad == "$/kg"]
    meses = pd.date_range(b.mes.min(), b.mes.max(), freq="MS")
    W = np.log(b.pivot_table(index=["mercado", "alimento"], columns="mes", values="precio", aggfunc="first").reindex(columns=meses))
    import importlib.util
    spec = importlib.util.spec_from_file_location("panel", RAIZ / "01_panel.py"); mp = importlib.util.module_from_spec(spec); spec.loader.exec_module(mp)
    for m_, a_, t_ in mp.ERRORES: W.loc[(m_, a_), pd.Timestamp(t_)] = np.nan
    series = list(P[["mercado", "alimento"]].drop_duplicates().itertuples(index=False, name=None))
    if os.environ.get("LIMITE_SERIES"): series = series[:int(os.environ["LIMITE_SERIES"])]      # solo para pruebas
    W = W.ffill(axis=1, limit=2)                                                # huecos: arrastre de hasta 2 meses
    cortes = cortes_sarima(P.mes_obj.max())
    filas = Parallel(n_jobs=NUCLEOS)(delayed(una_serie)(s, W.loc[s].values, list(meses), cortes) for s in series)
    S = pd.DataFrame([r for f in filas for r in f], columns=["corte", "mercado", "alimento", "mes_obj", "pred", "prob", "estacional"])
    S.to_parquet(RES / "sarima.parquet")
    resumen = S[S.corte == "prueba"].drop_duplicates(["mercado", "alimento"])
    guardar_json(dict(series_prueba=int(len(resumen)), series_panel=int(P[["mercado", "alimento"]].drop_duplicates().shape[0]),
                      prop_estacional=float(resumen.estacional.mean())), "sarima_resumen.json")
    print(f"[{time.time() - T0:.0f}s] SARIMA: {len(S)} pronósticos; series en prueba {len(resumen)}; con términos estacionales {resumen.estacional.mean():.1%}")
