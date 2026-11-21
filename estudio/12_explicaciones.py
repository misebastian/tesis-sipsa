"""Paso 12. Valores de Shapley (SHAP) de los modelos elegidos en la prueba, residuos y pruebas de Friedman, Nemenyi y DeLong.
Reajusta los dos CatBoost elegidos con 2019-2024 (mismos hiperparámetros y semilla) y verifica que reproducen las predicciones
guardadas. Escribe resultados/shap_reg.parquet, shap_clf.parquet y explicaciones.json. No interviene en ninguna decisión."""
import json, time
import numpy as np, pandas as pd
from scipy import stats
from catboost import Pool
from sklearn.metrics import average_precision_score, roc_auc_score
from statsmodels.tsa.stattools import adfuller
from comun import *
from modelos import REGRESION, CLASIFICACION, matrices, limpiar

T0 = time.time(); log = lambda *a: print(f"[{time.time() - T0:5.0f}s]", *a, flush=True)
P = cargar_panel(); V = variables_finales(); GRP = sorted(P.grupo.unique())
RS, CS = leer_json("reg_seleccion.json"), leer_json("clf_seleccion.json"); ER, EC = RS["elegido"], CS["elegido"]
ent, te = P[P.muestra != "prueba"], P[P.muestra == "prueba"]
S = {}

# ---------- 1. SHAP ----------
Op = pd.read_parquet(RES / "reg_predicciones_prueba.parquet"); Cp = pd.read_parquet(RES / "clf_predicciones_prueba.parquet")
for tarea, dic, nombre, imp in (("reg", REGRESION, ER, False), ("clf", CLASIFICACION, EC, True)):
    h = dict(RS["mejores"][nombre]["params"] if tarea == "reg" else CS["mejores"][nombre]["params"]); h["_hilos"] = NUCLEOS
    Xa, Xb = matrices(V, GRP, "arbol", ent, te, imputar_arbol=imp)
    m = dic[nombre][1](h) if tarea == "reg" else dic[nombre][1](h, 1.0)
    m.fit(Xa, ent.y.values if tarea == "reg" else ent.alza.values)
    (RES / "modelos").mkdir(exist_ok=True); ruta = RES / "modelos" / f"catboost_{tarea}.cbm"; m.save_model(str(ruta))
    m = type(m)(); m.load_model(str(ruta))          # los valores de Shapley se calculan sobre el modelo guardado
    sv = m.get_feature_importance(Pool(Xb), type="ShapValues")
    pred = m.predict(Xb) if tarea == "reg" else m.predict_proba(Xb)[:, 1]
    ref = Op[nombre].values if tarea == "reg" else Cp[nombre + " (sin recalibrar)"].values
    S[f"repro_{tarea}"] = float(np.corrcoef(pred, ref)[0, 1]); S[f"repro_{tarea}_dif"] = float(np.abs(pred - ref).max())
    D = pd.DataFrame(sv[:, :-1], columns=V); D["_base"] = sv[:, -1]; D["_pred"] = pred
    for c in ("mercado", "alimento", "grupo", "mes_obj", "y", "alza"): D[c] = te[c].values
    for v in V: D["x_" + v] = te[v].values
    D.to_parquet(RES / f"shap_{tarea}.parquet", index=False)
    imp_ = D[V].abs().mean().sort_values(ascending=False); S[f"shap_{tarea}"] = (imp_ / imp_.sum()).round(4).to_dict()
    log(tarea, "reproducción r =", round(S[f"repro_{tarea}"], 5), "dif. máx.", S[f"repro_{tarea}_dif"])

# ---------- 2. residuos de regresión ----------
r = (Op.y - Op[ER]).values; Op["res"] = r; Op["mes_obj"] = pd.to_datetime(Op.mes_obj)
S["res"] = dict(media=float(r.mean() * 100), mediana=float(np.median(r) * 100), asimetria=float(stats.skew(r)), curtosis=float(stats.kurtosis(r)),
                p05=float(np.quantile(r, .05) * 100), p95=float(np.quantile(r, .95) * 100))
ac = []
for _, g in Op.sort_values("mes_obj").groupby(["mercado", "alimento"]):
    s = g.set_index("mes_obj").res.asfreq("MS")
    if s.notna().sum() >= 15: ac.append([s.autocorr(k) for k in (1, 2, 3)])
ac = np.array(ac); S["res"]["acf_med"] = np.nanmedian(ac, axis=0).round(3).tolist(); S["res"]["n_series_acf"] = int(len(ac))
# sesgo por decil del pronóstico
q = pd.qcut(Op[ER].rank(method="first"), 10, labels=False); S["res"]["sesgo_decil"] = (Op.groupby(q).res.median() * 100).round(2).tolist()
# relación con la volatilidad pasada
S["res"]["corr_abs_vol"] = float(stats.spearmanr(np.abs(r), te.vol_12m.values, nan_policy="omit")[0])
log("residuos listos")

# ---------- 3. Friedman, Nemenyi y DeLong ----------
MR = RS["modelos"] + ["AR estacional", "SARIMA", "Paseo aleatorio"]; MC = CS["modelos"] + ["Frecuencia histórica", "Logística autorregresiva", "SARIMA"]
Op["mes"] = Op.mes_obj.dt.strftime("%Y-%m"); Cp["mes"] = pd.to_datetime(Cp.mes_obj).dt.strftime("%Y-%m")
E = pd.DataFrame({m: Op.assign(e=(Op.y - (0 if m == "Paseo aleatorio" else Op[m])).abs()).groupby("mes").e.mean() for m in MR})
A = pd.DataFrame({m: Cp.groupby("mes")[["alza", m]].apply(lambda d: average_precision_score(d.alza, d[m])) for m in MC})
QA = {3: 2.343, 4: 2.569, 5: 2.728, 6: 2.850, 7: 2.949, 8: 3.031, 9: 3.102, 10: 3.164}   # q_0,05 de Nemenyi (Demšar, 2006)
for nom, M, menor in (("reg", E, True), ("clf", A, False)):
    rk = M.rank(axis=1, ascending=menor); k, N = M.shape[1], M.shape[0]
    chi, p = stats.friedmanchisquare(*[M[c] for c in M])
    S[f"friedman_{nom}"] = dict(chi2=float(chi), p=float(p), k=k, N=N, rangos=rk.mean().sort_values().round(3).to_dict(), cd=float(QA[k] * np.sqrt(k * (k + 1) / (6 * N))))
    log("Friedman", nom, round(chi, 1), p)


def delong(y, a, b):
    """Prueba de DeLong para dos AUC correlacionadas (algoritmo de Sun y Xu, 2014)."""
    pos, neg = a[y == 1], a[y == 0]; posb, negb = b[y == 1], b[y == 0]; m_, n_ = len(pos), len(neg)

    def comp(p_, n__):
        todo = np.concatenate([p_, n__]); rt = stats.rankdata(todo); rp = stats.rankdata(p_); rn = stats.rankdata(n__)
        auc = (rt[:m_].sum() - m_ * (m_ + 1) / 2) / (m_ * n_)
        v10 = (rt[:m_] - rp) / n_; v01 = 1 - (rt[m_:] - rn) / m_
        return auc, v10, v01
    a1, v10a, v01a = comp(pos, neg); a2, v10b, v01b = comp(posb, negb)
    s10 = np.cov(np.vstack([v10a, v10b])); s01 = np.cov(np.vstack([v01a, v01b]))
    var = (s10[0, 0] + s10[1, 1] - 2 * s10[0, 1]) / m_ + (s01[0, 0] + s01[1, 1] - 2 * s01[0, 1]) / n_
    z = (a1 - a2) / np.sqrt(var); return float(a1 - a2), float(2 * stats.norm.sf(abs(z)))


ya = Cp.alza.values; dl = {}
for m in MC:
    if m != EC: d_, p_ = delong(ya, Cp[EC].values, Cp[m].values); dl[m] = dict(dif=d_, p=p_)
ks = list(dl); ph = holm([dl[m]["p"] for m in ks])
for m, v in zip(ks, ph): dl[m]["p_holm"] = float(v)
S["delong"] = dl; log("DeLong listo")

# ---------- 4. raíz unitaria (ADF) en nivel y en cambio ----------
B = pd.read_parquet(DATOS / "base_unida_mensual.parquet"); B = B[B.unidad == "$/kg"]
W = B.merge(P[["mercado", "alimento"]].drop_duplicates()).pivot_table(index=["mercado", "alimento"], columns="mes", values="precio")
rn, rc, nn = 0, 0, 0
for _, s in W.iterrows():
    l = np.log(s).interpolate(limit_area="inside").dropna()
    if len(l) < 60: continue
    nn += 1; rn += adfuller(l.values, regression="ct", autolag="AIC")[1] < .05; rc += adfuller(np.diff(l.values), regression="c", autolag="AIC")[1] < .05
S["adf"] = dict(series=nn, rechaza_nivel=rn / nn, rechaza_cambio=rc / nn); log("ADF", S["adf"])
(RES / "explicaciones.json").write_text(json.dumps(S, indent=1, ensure_ascii=False))
log("fin")
