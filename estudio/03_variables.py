"""Paso 3. Selección de variables con criterios verificables dentro de la validación temporal (la prueba no se usa).
Cada configuración se evalúa con dos cortes (ajuste hasta 2022 y predicción de 2023; ajuste hasta 2023 y predicción de 2024),
con LightGBM y el promedio de tres semillas; las predicciones de 2023 y 2024 se reúnen (24 meses). Las diferencias
entre configuraciones se miden sobre las mismas observaciones y su incertidumbre con bootstrap de bloques móviles de meses
(L = 3, B = 500); «significativo» = intervalo al 95 % que excluye el cero.
Etapa 1 - Fuga: controles estructurales en 01_panel.py.
Etapa 2 - Bloques: un bloque candidato entra si mejora significativamente una tarea y no empeora significativamente la otra;
          un bloque original sale si retirarlo no empeora significativamente ninguna tarea.
Etapa 3 - Informatividad: importancia por permutación en los cortes 2023 y 2024; una variable es informativa si su importancia
          media supera dos desviaciones típicas en alguna tarea. Las no informativas se retiran si el retiro no empeora significativamente.
Etapa 4 - Redundancia: en pares con |rho de Spearman| >= 0,85 se retira la de menor importancia, con el mismo criterio de retiro."""
import warnings, time
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.metrics import average_precision_score
from sklearn.inspection import permutation_importance
from comun import *
warnings.filterwarnings("ignore")
P = cargar_panel(); tr, va = P[P.muestra == "entrenamiento"], P[P.muestra == "validacion"]
CORTES = [(P[P.mes_obj <= a], P[(P.mes_obj > a) & (P.mes_obj <= b)]) for a, b in CORTES_CV[1:]]
T0 = time.time(); log = lambda *a: print(f"[{time.time() - T0:4.0f}s]", *a, flush=True)
REG = dict(objective="l1", n_estimators=200, learning_rate=.05, num_leaves=17, min_child_samples=120, subsample=.9, subsample_freq=1, colsample_bytree=.8, reg_lambda=8)
CLF = dict(n_estimators=500, learning_rate=.04, num_leaves=48, min_child_samples=60, subsample=.8, subsample_freq=1, colsample_bytree=.7)
UMBRAL_RHO, B = .85, 500
EV = pd.concat([b for _, b in CORTES]); yv, zv, mv = EV.y.values, EV.alza.values, EV.mes_obj.values


def predecir(cols, semillas=(0, 1, 2)):
    """Predicciones fuera de muestra de 2023 y 2024 (dos cortes), promedio de tres semillas."""
    r = np.concatenate([np.mean([lgb.LGBMRegressor(**REG, n_jobs=NUCLEOS, random_state=s, verbose=-1).fit(a[cols], a.y).predict(b[cols]) for s in semillas], axis=0) for a, b in CORTES])
    c = np.concatenate([np.mean([lgb.LGBMClassifier(**CLF, n_jobs=NUCLEOS, random_state=s, verbose=-1).fit(a[cols], a.alza).predict_proba(b[cols])[:, 1] for s in semillas], axis=0) for a, b in CORTES])
    return r, c


def comparar(base, otra):
    """Diferencia (otra - base) en MAE (p. p.; negativo = mejor) y en PR-AUC (positivo = mejor), con IC bootstrap por bloques."""
    (rb, cb), (ro, co) = base, otra
    eb, eo = np.abs(yv - rb), np.abs(yv - ro)
    dm, rm = bootstrap_metrica(mv, lambda i: (eo[i].mean() - eb[i].mean()) * 100, B=B)
    dp, rp = bootstrap_metrica(mv, lambda i: average_precision_score(zv[i], co[i]) - average_precision_score(zv[i], cb[i]), B=B)
    return dict(d_mae=dm, mae_lo=ic(rm)[0], mae_hi=ic(rm)[1], d_pr=dp, pr_lo=ic(rp)[0], pr_hi=ic(rp)[1],
                mae=float(np.abs(yv - ro).mean() * 100), pr=float(average_precision_score(zv, co)))


peor = lambda c: c["mae_lo"] > 0 or c["pr_hi"] < 0          # empeora significativamente alguna tarea
mejor = lambda c: c["mae_hi"] < 0 or c["pr_lo"] > 0         # mejora significativamente alguna tarea

# ---------- etapa 2: bloques ----------
PB = predecir(BASE); filas = [dict(config="Base (38 variables)", n=len(BASE), **comparar(PB, PB))]
for k, v in BLOQUES_NUEVOS.items():
    filas.append(dict(config=f"+ {k}", n=len(BASE) + len(v), bloque=k, tipo="nuevo", **comparar(PB, predecir(BASE + v))))
for k, v in BLOQUES_BASE.items():
    if k not in ("Historia del precio", "Producto y lugar"):
        filas.append(dict(config=f"− {k}", n=len(BASE) - len(v), bloque=k, tipo="original", **comparar(PB, predecir([c for c in BASE if c not in v]))))
log("bloques evaluados")
D = pd.DataFrame(filas)
anadir = [r.bloque for r in D[D.tipo == "nuevo"].itertuples() if mejor(r._asdict()) and not peor(r._asdict())]
quitar = [r.bloque for r in D[D.tipo == "original"].itertuples() if not peor(r._asdict())]
cols2 = [c for c in BASE if not any(c in BLOQUES_BASE[q] for q in quitar)] + sum((BLOQUES_NUEVOS[k] for k in anadir), [])
P2 = predecir(cols2); c2 = comparar(PB, P2); log("etapa 2:", anadir, quitar, len(cols2))

# ---------- etapa 3: informatividad ----------
imps = []
for k, (a, b) in enumerate(CORTES):
    r = lgb.LGBMRegressor(**REG, n_jobs=NUCLEOS, random_state=0, verbose=-1).fit(a[cols2], a.y)
    c = lgb.LGBMClassifier(**CLF, n_jobs=NUCLEOS, random_state=0, verbose=-1).fit(a[cols2], a.alza)
    ir = permutation_importance(r, b[cols2], b.y, scoring="neg_mean_absolute_error", n_repeats=5, random_state=0)
    ic_ = permutation_importance(c, b[cols2], b.alza, scoring="average_precision", n_repeats=5, random_state=0)
    imps.append(pd.DataFrame(dict(var=cols2, corte=[2023, 2024][k], reg=ir.importances_mean * 100, reg_sd=ir.importances_std * 100, clf=ic_.importances_mean, clf_sd=ic_.importances_std)))
I = pd.concat(imps)
G = I.groupby("var").agg(reg=("reg", "mean"), clf=("clf", "mean"), reg_sd=("reg_sd", lambda s: np.sqrt(np.mean(s ** 2))), clf_sd=("clf_sd", lambda s: np.sqrt(np.mean(s ** 2)))).reindex(cols2)
G["inf_reg"] = G.reg > 2 * G.reg_sd; G["inf_clf"] = G.clf > 2 * G.clf_sd
no_inf = G.index[~G.inf_reg & ~G.inf_clf].tolist()
no_inf = [v for v in no_inf if not (v in ("mes_sin", "mes_cos") and ({"mes_sin", "mes_cos"} - set(no_inf)))]
cols3 = [c for c in cols2 if c not in no_inf]
P3 = predecir(cols3) if no_inf else P2; c3 = comparar(P2, P3)
acepta3 = bool(no_inf) and not peor(c3)
if not acepta3: cols3, P3 = cols2, P2
log("etapa 3:", no_inf, acepta3)

# ---------- etapa 4: redundancia ----------
num = [c for c in cols3 if not c.endswith("_c")]
Cr = tr[num].corr(method="spearman").abs()
G["imp_norm"] = G.reg.clip(lower=0) / G.reg.clip(lower=0).max() + G.clf.clip(lower=0) / G.clf.clip(lower=0).max()
pares = sorted([(a_, b_, Cr.loc[a_, b_]) for i, a_ in enumerate(num) for b_ in num[i + 1:] if Cr.loc[a_, b_] >= UMBRAL_RHO], key=lambda t: -t[2])
redund, decisiones = [], []
for a_, b_, rho in pares:
    if a_ in redund or b_ in redund or {a_, b_} == {"mes_sin", "mes_cos"}: continue
    sale = a_ if G.loc[a_, "imp_norm"] < G.loc[b_, "imp_norm"] else b_
    redund.append(sale); decisiones.append(dict(par=f"{a_} / {b_}", rho=float(rho), sale=sale, queda=b_ if sale == a_ else a_))
cols4 = [c for c in cols3 if c not in redund]
P4 = predecir(cols4) if redund else P3; c4 = comparar(P3, P4)
acepta4 = bool(redund) and not peor(c4)
if not acepta4: cols4, P4 = cols3, P3
log("etapa 4:", redund, acepta4)

todas = BASE + sum(BLOQUES_NUEVOS.values(), [])
pasos = [dict(paso="Base (38 variables)", n=len(BASE), **comparar(PB, PB)), dict(paso="Todas las candidatas", n=len(todas), **comparar(PB, predecir(todas))),
         dict(paso="Etapa 2: bloques", n=len(cols2), **c2), dict(paso="Etapa 3: sin no informativas", n=len(cols3), **comparar(PB, P3)),
         dict(paso="Etapa 4: sin redundancias (final)", n=len(cols4), **comparar(PB, P4))]
D.to_csv(RES / "seleccion_bloques.csv", index=False); G.reset_index().to_csv(RES / "importancia_permutacion.csv", index=False)
guardar_json(dict(variables=cols4, bloques_anadidos=anadir, bloques_retirados=quitar, no_informativas=no_inf, acepta_etapa3=acepta3, etapa3=c3,
                  redundancia=decisiones, acepta_etapa4=acepta4, etapa4=c4, umbral_rho=UMBRAL_RHO, pasos=pasos), "variables_finales.json")

# ---------- figuras ----------
b = D.iloc[1:]
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.5), sharey=True)
y_ = np.arange(len(b))
for a, d, lo, hi, tit, lab in ((axs[0], b.d_mae, b.mae_lo, b.mae_hi, "Regresión", "Cambio del MAE en 2023-2024 (p. p.; negativo = mejor)"),
                               (axs[1], b.d_pr, b.pr_lo, b.pr_hi, "Clasificación", "Cambio de la PR-AUC en 2023-2024 (positivo = mejor)")):
    a.errorbar(d, y_, xerr=[d - lo, hi - d], fmt="o", color=VERDE, ms=4, capsize=2, lw=1); a.axvline(0, color=SUAVE, lw=.8)
    a.set_title(tit); a.set_xlabel(lab, fontsize=8); a.grid(axis="y", visible=False)
axs[0].set_yticks(y_, b.config, fontsize=7.5); axs[0].invert_yaxis()
fig.suptitle("Efecto de añadir (+) o quitar (−) bloques frente a la base, con IC bootstrap al 95 %", x=.01, ha="left", fontweight="bold", fontsize=10)
fig.tight_layout(); guardar(fig, "var_bloques")
Gs = G.assign(nombre=G.index.map(NOMBRES)).sort_values("reg")
cr = [VERDE if (v not in no_inf and v not in redund) else (OCRE if v in redund else GRIS) for v in Gs.index]
cc = [NARANJA if (v not in no_inf and v not in redund) else (OCRE if v in redund else GRIS) for v in Gs.index]
fig, axs = plt.subplots(1, 2, figsize=(7.4, 7.0), sharey=True)
axs[0].barh(Gs.nombre, Gs.reg, xerr=2 * Gs.reg_sd, color=cr, alpha=.85, error_kw=dict(lw=.6)); axs[0].set_xlabel("Aumento del MAE al permutar (p. p.)"); axs[0].set_title("Regresión")
axs[1].barh(Gs.nombre, Gs.clf, xerr=2 * Gs.clf_sd, color=cc, alpha=.85, error_kw=dict(lw=.6)); axs[1].set_xlabel("Caída de la PR-AUC al permutar"); axs[1].set_title("Clasificación")
for a in axs: a.axvline(0, color=SUAVE, lw=.8); a.grid(axis="y", visible=False); a.tick_params(axis="y", labelsize=6.8)
fig.suptitle("Importancia por permutación, promedio de 2023 y 2024 (gris: no informativa; ocre: redundante)", x=.01, ha="left", fontweight="bold", fontsize=10)
fig.tight_layout(); guardar(fig, "var_permutacion")
log("variables finales:", len(cols4))
