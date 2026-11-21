"""Paso 7. Análisis complementarios sobre la prueba (no cambian ninguna decisión de modelado).
A) Origen móvil: reentrenamiento trimestral (ene, abr, jul, oct) con los hiperparámetros ya elegidos, frente al ajuste único;
   incluye el AR estacional y SARIMA (reajustado en cada origen).
B) Pronóstico distribucional: LightGBM cuantílico (tau = 0,05; 0,10; 0,25; 0,50; 0,75; 0,90; 0,95) con hiperparámetros elegidos
   por la pérdida de pinball promedio (misma regla de búsqueda que los demás modelos). Intervalos conformales (CQR, Romano et al.
   2019): ajuste hasta 2023, calibración con 2024, global y por perecederos / no perecederos. P(alza) desde la distribución.
C) Datos faltantes en el objetivo y sensibilidad de las métricas."""
import warnings, time
import numpy as np, pandas as pd, lightgbm as lgb
from scipy import stats
from scipy.stats import loguniform, randint, uniform
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss
from comun import *
from modelos import REGRESION, CLASIFICACION, matrices, ajustar_ar, limpiar, E_LGB
from busqueda import buscar
warnings.filterwarnings("ignore")
T0 = time.time(); log = lambda *a: print(f"[{time.time() - T0:5.0f}s]", *a, flush=True)
P = cargar_panel(); V = variables_finales(); GRP = sorted(P.grupo.unique())
RS, CS = leer_json("reg_seleccion.json"), leer_json("clf_seleccion.json"); ER, EC = RS["elegido"], CS["elegido"]
OR = pd.read_parquet(RES / "reg_predicciones_prueba.parquet"); OC = pd.read_parquet(RES / "clf_predicciones_prueba.parquet")
SAR = pd.read_parquet(RES / "sarima.parquet")
ent, te = P[P.muestra != "prueba"], P[P.muestra == "prueba"]
S = {}
logit = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6))); expit = lambda x: 1 / (1 + np.exp(-x))

# ================= A) ORIGEN MÓVIL =================
origenes = pd.to_datetime(["2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01", "2026-01-01", "2026-04-01", "2026-07-01"])
fr, fc = REGRESION[ER], CLASIFICACION[EC]; bal = CS["balanceo"][EC]; a_rec = CS["recalibracion"][EC]["intercepto"]
rr, rc, ar, ac, sr = (pd.Series(np.nan, index=te.index) for _ in range(5))
for k, o in enumerate(origenes):
    fin = origenes[k + 1] if k + 1 < len(origenes) else te.mes_obj.max() + pd.offsets.MonthBegin(1)
    a = P[P.mes_obj < o]; b = te[(te.mes_obj >= o) & (te.mes_obj < fin)]
    if b.empty: continue
    Xa, Xb = matrices(V, GRP, fr[0], a, b); rr[b.index] = fr[1](RS["mejores"][ER]["params"]).fit(Xa, a.y.values).predict(Xb)
    Xa, Xb = matrices(V, GRP, fc[0], a, b, imputar_arbol=True); w = float((1 - a.alza.mean()) / a.alza.mean()) if bal == "Pesos de clase" else 1.0
    rc[b.index] = expit(a_rec + logit(fc[1](CS["mejores"][EC]["params"], w).fit(Xa, a.alza.values).predict_proba(Xb)[:, 1]))
    ar[b.index] = ajustar_ar(a, b); ac[b.index] = ajustar_ar(a, b, "clf")
    s_ = SAR[SAR.corte == f"movil{k}"].set_index(["mercado", "alimento", "mes_obj"]).pred
    sr[b.index] = np.nan_to_num(s_.reindex(pd.MultiIndex.from_frame(b[["mercado", "alimento", "mes_obj"]])).values); log("origen", o.date(), len(a), len(b))
y, z, mes = te.y.values, te.alza.values, te.mes_obj.values
fijo_r, fijo_c = OR[ER].values, OC[EC].values
assert np.allclose(OR.y.values, y)
ef, em, erw = np.abs(y - fijo_r), np.abs(y - rr.values), np.abs(y)
d, rep = bootstrap_metrica(mes, lambda i: (em[i].mean() - ef[i].mean()) * 100)
dp, repp = bootstrap_metrica(mes, lambda i: average_precision_score(z[i], rc.values[i]) - average_precision_score(z[i], fijo_c[i]))
S["origen_movil"] = dict(mae_fijo=float(ef.mean() * 100), mae_movil=float(em.mean() * 100), mae_ar_fijo=float(np.abs(y - OR["AR estacional"]).mean() * 100),
                         mae_ar_movil=float(np.abs(y - ar.values).mean() * 100), mae_sarima_fijo=float(np.abs(y - OR["SARIMA"]).mean() * 100),
                         mae_sarima_movil=float(np.abs(y - sr.values).mean() * 100), mae_rw=float(erw.mean() * 100), d_mae=d, d_mae_ic=ic(rep),
                         mejora_movil=float(1 - em.mean() / erw.mean()), pr_fijo=float(average_precision_score(z, fijo_c)), pr_movil=float(average_precision_score(z, rc.values)),
                         pr_ar_movil=float(average_precision_score(z, ac.values)), roc_movil=float(roc_auc_score(z, rc.values)), d_pr=dp, d_pr_ic=ic(repp))
mm = pd.DataFrame(dict(mes=mes, f=ef, m=em, rw=erw)).groupby("mes").mean() * 100
fig, ax = plt.subplots(figsize=(7.2, 2.7))
ax.plot(mm.index, mm.rw, color=GRIS, marker="o", ms=3, label="Paseo aleatorio"); ax.plot(mm.index, mm.f, color=NARANJA, marker="o", ms=3, label=f"{ER}, ajuste único (≤ 2024)")
ax.plot(mm.index, mm.m, color=AZUL, marker="s", ms=3, ls="--", label=f"{ER}, reentrenado cada trimestre")
for o in origenes[1:]: ax.axvline(o, color=SUAVE, lw=.5, ls=":")
ax.set_ylabel("MAE (p. p.)"); ax.legend(fontsize=7.5); ejes_fecha(ax); ax.set_title("Ajuste único frente a origen móvil trimestral")
guardar(fig, "res_origen_movil"); log("A listo", S["origen_movil"])

# ================= B) PRONÓSTICO DISTRIBUCIONAL Y CQR =================
TAUS = np.array([.05, .10, .25, .50, .75, .90, .95]); j = {t: i for i, t in enumerate(TAUS)}
qmod = lambda h, t: lgb.LGBMRegressor(objective="quantile", alpha=t, n_estimators=h["n"], learning_rate=h["lr"], num_leaves=h["hojas"], min_child_samples=h["mcs"],
                                      subsample=h["ss"], subsample_freq=1, colsample_bytree=h["cs"], reg_lambda=h["l2"], n_jobs=int(h.get("_hilos", NUCLEOS)), random_state=SEMILLA, verbose=-1)
pinball = lambda yy, q, t: np.mean(np.maximum(t * (yy - q), (t - 1) * (yy - q)))
cortes = [(P[P.mes_obj <= x], P[(P.mes_obj > x) & (P.mes_obj <= y_)]) for x, y_ in CORTES_CV]
def eval_q(h, datos):
    return [float(np.mean([pinball(yb, qmod(h, t).fit(Xa, ya).predict(Xb), t) for t in TAUS])) for Xa, ya, Xb, yb in datos]
datos = [(*matrices(V, GRP, "arbol", a, b)[:1], a.y.values, matrices(V, GRP, "arbol", a, b)[1], b.y.values) for a, b in cortes]
rq = buscar(E_LGB, eval_q, datos, sentido=1, tol=5e-5); hq = limpiar(rq["params"]); log("cuantiles: pinball CV", round(rq["puntaje"] * 100, 4), "ensayos", rq["n_ensayos"])
S["cuantiles_busqueda"] = dict(params=hq, pinball_cv=rq["puntaje"], n_ensayos=rq["n_ensayos"], convergio=rq["convergio"], curva=rq["curva"])
def predq(a, b):
    Xa, Xb = matrices(V, GRP, "arbol", a, b); Q = np.column_stack([qmod(hq, t).fit(Xa, a.y.values).predict(Xb) for t in TAUS])
    return Q, float((np.diff(Q, axis=1) < 0).any(axis=1).mean())
Q, cruces = predq(ent, te); Q = np.sort(Q, axis=1)                   # modelos reajustados con 2019-2024
tr23, va24 = P[P.muestra == "entrenamiento"], P[P.muestra == "validacion"]
Qc, _ = predq(tr23, pd.concat([va24, te])); Qc = np.sort(Qc, axis=1); Qv, Qt = Qc[:len(va24)], Qc[len(va24):]   # ajuste <= 2023 para CQR
grupo_per = lambda d: np.where(d.grupo.isin(["FRUTAS", "VERDURAS Y HORTALIZAS", "TUBERCULOS, RAICES Y PLATANOS"]).values, "Perecederos", "No perecederos")
gv, gt = grupo_per(va24), grupo_per(te); yv = va24.y.values
def cqr(lo_, hi_, alfa, por_grupo):
    """Intervalo conformal [q_lo - Qhat, q_hi + Qhat] con Qhat el cuantil ceil((n+1)(1-alfa))/n de las puntuaciones en 2024."""
    sc = np.maximum(Qv[:, lo_] - yv, yv - Qv[:, hi_]); L, U = Qt[:, lo_].copy(), Qt[:, hi_].copy()
    for g_ in (np.unique(gv) if por_grupo else [None]):
        mv_ = (gv == g_) if por_grupo else np.ones(len(yv), bool); mt_ = (gt == g_) if por_grupo else np.ones(len(y), bool)
        n_ = mv_.sum(); qh = np.quantile(sc[mv_], min(1, np.ceil((n_ + 1) * (1 - alfa)) / n_)); L[mt_] -= qh; U[mt_] += qh
    return L, U
def resumen_int(L, U):
    dentro = ((y >= L) & (y <= U)).astype(float); _, r_ = bootstrap_metrica(mes, lambda i: dentro[i].mean())
    return dict(cobertura=float(dentro.mean()), ic=ic(r_), ancho=float(np.mean(U - L) * 100),
                por_grupo={g_: float(dentro[gt == g_].mean()) for g_ in np.unique(gt)})
ints = {}
for nom, lo_, hi_, al in (("90", j[.05], j[.95], .10), ("80", j[.10], j[.90], .20)):
    ints[nom] = {"Cuantiles (ajuste 2019-2024)": resumen_int(Q[:, lo_], Q[:, hi_]), "Cuantiles (ajuste 2019-2023)": resumen_int(Qt[:, lo_], Qt[:, hi_]),
                 "CQR global": resumen_int(*cqr(lo_, hi_, al, False)), "CQR por grupo": resumen_int(*cqr(lo_, hi_, al, True))}
lo, hi = TAUS[0] / 2, 1 - (1 - TAUS[-1]) / 2
p_q = 1 - np.array([np.interp(UMBRAL, q, TAUS, left=lo, right=hi) for q in Q])
pin = np.mean([pinball(y, Q[:, i], t) for i, t in enumerate(TAUS)]); pin_rw = np.mean([pinball(y, np.quantile(ent.y, t), t) for t in TAUS])
dq, repq = bootstrap_metrica(mes, lambda i: average_precision_score(z[i], p_q[i]) - average_precision_score(z[i], fijo_c[i]))
S["distribucional"] = dict(cruces=cruces, intervalos=ints, pinball=float(pin * 100), pinball_incondicional=float(pin_rw * 100), mae_mediana=float(np.abs(y - Q[:, j[.5]]).mean() * 100),
                           pr_auc=float(average_precision_score(z, p_q)), roc_auc=float(roc_auc_score(z, p_q)), brier=float(brier_score_loss(z, p_q)),
                           brier_clf=float(brier_score_loss(z, fijo_c)), d_pr_vs_clf=dq, d_pr_ic=ic(repq), prob_media=float(p_q.mean()),
                           spearman_clf=float(stats.spearmanr(p_q, fijo_c)[0]), cobertura_tau={str(t): float(np.mean(y <= Q[:, i])) for i, t in enumerate(TAUS)})
fig, axs = plt.subplots(1, 3, figsize=(7.6, 2.9), gridspec_kw=dict(width_ratios=[1, 1.25, 1]))
axs[0].plot([0, 1], [0, 1], color=SUAVE, ls="--", lw=.8); axs[0].plot(TAUS, [np.mean(y <= Q[:, i]) for i in range(len(TAUS))], "o-", color=VERDE, ms=4)
axs[0].set_xlabel("Cuantil nominal τ"); axs[0].set_ylabel("Proporción y ≤ q̂_τ"); axs[0].set_title("Cuantiles", fontsize=9)
nomb = ["Cuantiles (ajuste 2019-2024)", "CQR global", "CQR por grupo"]; xg = np.arange(2)
for k_, nm in enumerate(nomb):
    vals = [ints["90"][nm]["por_grupo"][g_] * 100 for g_ in ("Perecederos", "No perecederos")]
    axs[1].bar(xg + (k_ - 1) * .27, vals, .27, color=[GRIS, AZUL, NARANJA][k_], alpha=.85, label=nm.replace(" (ajuste 2019-2024)", ""))
axs[1].axhline(90, color=TINTA, ls="--", lw=.8); axs[1].set_ylim(70, 100); axs[1].set_xticks(xg, ["Perecederos", "No perecederos"], fontsize=8)
axs[1].set_ylabel("Cobertura del intervalo del 90 % (%)"); axs[1].legend(fontsize=6.3, loc="lower right"); axs[1].set_title("Cobertura por grupo", fontsize=9)
qq = pd.DataFrame(dict(p=p_q, c=fijo_c, y=z)); qq["b"] = pd.qcut(qq.p.rank(method="first"), 10, labels=False); g = qq.groupby("b").mean()
axs[2].plot([0, .8], [0, .8], color=SUAVE, ls="--", lw=.8); axs[2].plot(g.p, g.y, "o-", color=VERDE, ms=4, label="Desde cuantiles")
qq["b2"] = pd.qcut(qq.c.rank(method="first"), 10, labels=False); g2 = qq.groupby("b2").mean(); axs[2].plot(g2.c, g2.y, "s--", color=NARANJA, ms=4, label=f"Clasificador")
axs[2].set_xlabel("Probabilidad (decil)"); axs[2].set_ylabel("Frecuencia observada"); axs[2].legend(fontsize=6.5); axs[2].set_title("P(alza > 15 %)", fontsize=9)
fig.tight_layout(); guardar(fig, "res_distribucional"); log("B listo", {k: v for k, v in S["distribucional"].items() if k != "intervalos"}, ints)

# ================= C) FALTANTES EN EL OBJETIVO =================
B_ = pd.read_parquet(DATOS / "base_unida_mensual.parquet"); b = B_[B_.unidad == "$/kg"]
meses = pd.date_range(b.mes.min(), b.mes.max(), freq="MS")
LPo = np.log(b.pivot_table(index=["mercado", "alimento"], columns="mes", values="precio", aggfunc="first").reindex(columns=meses))
sel = P[["mercado", "alimento"]].drop_duplicates(); LPo = LPo.loc[pd.MultiIndex.from_frame(sel)]
R = LPo.diff(axis=1); A = (R > UMBRAL).astype(float).where(R.notna())
Sa, Na = A.fillna(0).groupby(level="alimento").transform("sum"), A.notna().groupby(level="alimento").transform("sum")
prop_otras = (Sa - A.fillna(0)) / (Na - A.notna()).replace(0, np.nan)   # alzas > 15 % en otras centrales, mes t+1 cuando se desplaza
Sr, Nr = R.fillna(0).groupby(level="alimento").transform("sum"), R.notna().groupby(level="alimento").transform("sum")
cam_otras = (Sr - R.fillna(0)) / (Nr - R.notna()).replace(0, np.nan)
obs_t, obs_t1 = LPo.notna(), LPo.notna().shift(-1, axis=1, fill_value=False)
L = pd.DataFrame(dict(obs_t=obs_t.stack(), falta=~obs_t1.stack(), prop=prop_otras.shift(-1, axis=1).stack(dropna=False),
                      cam=cam_otras.shift(-1, axis=1).stack(dropna=False), r_t=R.stack(dropna=False))).reset_index()
L.columns = ["mercado", "alimento", "mes", "obs_t", "falta", "prop", "cam", "r_t"]
L = L[L.obs_t & (L.mes >= "2019-01-01") & (L.mes < meses[-1])].dropna(subset=["prop", "cam"])
L = L.merge(P[["alimento", "grupo"]].drop_duplicates(), on="alimento")
res = L.groupby("falta").agg(n=("prop", "size"), prop_alza_otras=("prop", "mean"), cambio_otras=("cam", "mean"))
X = pd.concat([L[["prop", "cam"]].reset_index(drop=True), L.r_t.fillna(0).abs().rename("abs_r_t").reset_index(drop=True),
               pd.get_dummies(L.grupo, drop_first=True, dtype=float).reset_index(drop=True)], axis=1)
lg = LogisticRegression(max_iter=2000).fit(X, L.falta.values)
od = {c: float(np.exp(v)) for c, v in zip(X.columns[:3], lg.coef_[0][:3])}
sd = X[["prop", "cam", "abs_r_t"]].std()
S["faltantes"] = dict(tasa_falta=float(L.falta.mean()), n=int(len(L)), por_estado=res.round(5).reset_index().to_dict("records"),
                      or_por_de={c: float(np.exp(lg.coef_[0][i] * sd[c])) for i, c in enumerate(["prop", "cam", "abs_r_t"])},
                      dif_prop=float(res.loc[True, "prop_alza_otras"] - res.loc[False, "prop_alza_otras"]),
                      prueba_t=float(stats.ttest_ind(L.prop[L.falta], L.prop[~L.falta], equal_var=False).pvalue))
log("C listo", S["faltantes"])
# sensibilidad de las métricas de prueba a los casos sin objetivo (p_t observado, p_{t+1} faltante)
SO = pd.read_parquet(DATOS / "panel_sin_objetivo.parquet"); SO = SO[SO.muestra == "prueba"].copy()
if len(SO):
    Xa, Xs = matrices(V, GRP, fr[0], ent, SO); pr_s = fr[1](RS["mejores"][ER]["params"]).fit(Xa, ent.y.values).predict(Xs)
    Xa, Xs = matrices(V, GRP, fc[0], ent, SO, imputar_arbol=True)
    w0 = float((1 - ent.alza.mean()) / ent.alza.mean()) if bal == "Pesos de clase" else 1.0
    pc_s = expit(a_rec + logit(fc[1](CS["mejores"][EC]["params"], w0).fit(Xa, ent.alza.values).predict_proba(Xs)[:, 1]))
    ysup = SO.fut_cambio_otras.fillna(0).values; u_ = CS["umbral"][EC]
    def met(yy, zz, pr_, pc_):
        e, e0 = np.abs(yy - pr_), np.abs(yy); al = pc_ >= u_; tp = (al & (zz == 1)).sum()
        return dict(mejora=float(1 - e.mean() / e0.mean()), pr_auc=float(average_precision_score(zz, pc_)), recall=float(tp / max(zz.sum(), 1)), precision=float(tp / max(al.sum(), 1)))
    base = met(y, z, fijo_r, fijo_c)
    esc = {"observados": base,
           "imputando con las demás centrales": met(np.r_[y, ysup], np.r_[z, (ysup > UMBRAL).astype(int)], np.r_[fijo_r, pr_s], np.r_[fijo_c, pc_s]),
           "faltantes = todos alzas": met(np.r_[y, np.full(len(SO), np.log(1.3))], np.r_[z, np.ones(len(SO), int)], np.r_[fijo_r, pr_s], np.r_[fijo_c, pc_s]),
           "faltantes = ninguna alza": met(np.r_[y, ysup], np.r_[z, np.zeros(len(SO), int)], np.r_[fijo_r, pr_s], np.r_[fijo_c, pc_s])}
    S["faltantes"]["n_prueba"] = int(len(SO)); S["faltantes"]["tasa_prueba"] = float(len(SO) / (len(SO) + len(te)))
    S["faltantes"]["sensibilidad"] = esc; S["faltantes"]["prob_media_faltantes"] = float(pc_s.mean()); S["faltantes"]["prob_media_obs"] = float(fijo_c.mean())
    log("sensibilidad faltantes", esc)

guardar_json(S, "complementarios.json"); log("fin")
