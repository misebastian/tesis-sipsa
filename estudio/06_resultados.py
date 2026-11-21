"""Paso 6. Evaluación en prueba: métricas, intervalos bootstrap por bloques de meses, Diebold-Mariano con ajuste de Holm,
MASE, análisis por grupo, ciudad, central y producto, curvas ROC/PR, calibración, curva de decisión e importancia por bloques.
No se toma ninguna decisión de modelado aquí."""
import warnings
import numpy as np, pandas as pd
from scipy import stats
from sklearn.metrics import log_loss, roc_curve, roc_auc_score, precision_recall_curve, average_precision_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score
from comun import *
from modelos import REGRESION, CLASIFICACION, matrices
warnings.filterwarnings("ignore")
S = {}
RS, CS = leer_json("reg_seleccion.json"), leer_json("clf_seleccion.json")
O = pd.read_parquet(RES / "reg_predicciones_prueba.parquet"); C = pd.read_parquet(RES / "clf_predicciones_prueba.parquet")
BV = pd.read_csv(RES / "clf_balanceo_val.csv"); PV = pd.read_parquet(RES / "clf_predicciones_val.parquet")
P = cargar_panel(); V = variables_finales(); GRP = sorted(P.grupo.unique())
MR, MC = RS["modelos"], CS["modelos"]; ER, EC = RS["elegido"], CS["elegido"]
REFR = ["Paseo aleatorio", "AR estacional", "SARIMA"]; REFC = ["Frecuencia histórica", "Logística autorregresiva", "SARIMA"]
y = O.y.values; mes = O.mes_obj.values; BOOT = int(os.environ.get("BOOT", 10000))   # réplicas bootstrap


def dm(e1, e2, meses):
    """Diebold-Mariano (pérdida absoluta) sobre la diferencia promedio mensual; varianza HAC (Bartlett) y corrección HLN, h = 1."""
    d = pd.Series(np.abs(e1) - np.abs(e2)).groupby(np.asarray(meses)).mean(); T = len(d); L = int(np.floor(T ** (1 / 3)))
    g = d.var(ddof=0) + 2 * sum((1 - k / (L + 1)) * np.cov(d[k:], d[:-k], ddof=0)[0, 1] for k in range(1, L + 1))
    st = d.mean() / np.sqrt(g / T) * np.sqrt((T - 1) / T); return float(st), float(2 * stats.t.sf(abs(st), T - 1))


# ================= REGRESIÓN =================
tr = P[P.muestra == "entrenamiento"]
escala = tr.groupby(["mercado", "alimento"]).y.apply(lambda s: s.abs().mean()).rename("escala")
O = O.merge(escala, left_on=["mercado", "alimento"], right_index=True, how="left"); O["escala"] = O.escala.fillna(O.escala.median())
filas = []
erw = np.abs(y)
for m in REFR + MR:
    e = np.abs(y - O[m].values); nz = y != 0
    sk, rs = bootstrap_metrica(mes, lambda i: 1 - e[i].mean() / erw[i].mean(), B=BOOT)
    st, pv = dm(y - O["Paseo aleatorio"].values, y - O[m].values, mes) if m != "Paseo aleatorio" else (np.nan, np.nan)
    ser = O.assign(e=e, erw=erw).groupby(["mercado", "alimento"])[["e", "erw"]].mean()
    filas.append(dict(modelo=m, mae=e.mean(), rmse=np.sqrt(np.mean((y - O[m].values) ** 2)), medae=np.median(e), mase=np.mean(e / O.escala.values),
                      direccion=np.mean(np.sign(O[m].values[nz]) == np.sign(y[nz])) if m != "Paseo aleatorio" else np.nan,
                      mejora=sk, mejora_lo=ic(rs)[0], mejora_hi=ic(rs)[1], dm=st, p_dm=pv, series_gana=float((ser.e < ser.erw).mean()),
                      mae_val=RS["mejores"][m]["mae_cv"] if m in MR else RS["referencias_cv"][m]["mae_cv"]))
T = pd.DataFrame(filas)
mask = T.modelo != "Paseo aleatorio"; T.loc[mask, "p_holm"] = holm(T.loc[mask, "p_dm"].values)
# diferencia con el modelo elegido (MAE modelo - MAE elegido, p. p.) con IC
e_er = np.abs(y - O[ER].values)
M_BONF = len(T) - 1; A_BONF = .05 / M_BONF                 # comparaciones frente al elegido, ajuste de Bonferroni
gq = O.grupo.values
for i, r in T.iterrows():
    e = np.abs(y - O[r.modelo].values)
    d, rr = bootstrap_metrica(mes, lambda k: (e[k].mean() - e_er[k].mean()) * 100, B=BOOT)
    T.loc[i, "d_vs_elegido"], T.loc[i, "d_lo"], T.loc[i, "d_hi"] = d, *ic(rr)
    T.loc[i, "d_lo_bonf"], T.loc[i, "d_hi_bonf"] = ic(rr, A_BONF)
    mg = pd.Series(e).groupby(gq).mean(); mg0 = pd.Series(erw).groupby(gq).mean()
    T.loc[i, "mejora_macro"] = float(1 - mg.mean() / mg0.mean())        # promedio con igual peso por grupo
S["bonf_m"] = M_BONF
T.to_csv(RES / "reg_metricas_prueba.csv", index=False); S["reg_tabla"] = T.to_dict("records")

# ---- error valorado en pesos: |p_hat - p| x toneladas del mes pronosticado (ilustrativo) ----
B_ = pd.read_parquet(DATOS / "base_unida_mensual.parquet")[["mercado", "alimento", "mes", "precio", "ton"]]
B_["mes"] = pd.to_datetime(B_.mes)
Q = O[["mercado", "alimento", "mes_obj", "grupo"]].merge(B_.rename(columns={"mes": "mes_obj"}), on=["mercado", "alimento", "mes_obj"], how="left")
p1 = Q.precio.values; tq = Q.ton.fillna(0).values * 1000; p0 = p1 / np.exp(y)       # p_t a partir de p_{t+1} y del cambio observado
val = {}
for m in REFR + MR:
    err = np.abs(p0 * np.exp(O[m].values) - p1) * tq
    val[m] = err
base_v = val["Paseo aleatorio"]
VA = []
for m in REFR + MR:
    v = val[m]; r_, rr = bootstrap_metrica(mes, lambda k: 1 - np.nansum(v[k]) / np.nansum(base_v[k]), B=BOOT)
    VA.append(dict(modelo=m, error_mm=float(np.nansum(v) / 1e9), mejora=r_, lo=ic(rr)[0], hi=ic(rr)[1]))
VA = pd.DataFrame(VA); VA.to_csv(RES / "reg_error_valorado.csv", index=False); S["valorado"] = VA.to_dict("records")
vg = pd.DataFrame({m: pd.Series(val[m]).groupby(Q.grupo.map(GRUPOS).values).sum() for m in ("Paseo aleatorio", ER)})
S["valorado_grupo"] = (1 - vg[ER] / vg["Paseo aleatorio"]).round(4).to_dict(); S["valorado_total_rw_mm"] = float(np.nansum(base_v) / 1e9)
S["valorado_cobertura"] = float(np.mean(tq > 0))

t = T[T.modelo != "Paseo aleatorio"].sort_values("mejora")
fig, ax = plt.subplots(figsize=(7.2, 4.0))
yy = np.arange(len(t)); col = [GRIS if m in REFR else (NARANJA if m == ER else VERDE) for m in t.modelo]
ax.errorbar(t.mejora * 100, yy, xerr=[(t.mejora - t.mejora_lo) * 100, (t.mejora_hi - t.mejora) * 100], fmt="none", ecolor=SUAVE, lw=1, capsize=2)
ax.scatter(t.mejora * 100, yy, c=col, s=36, zorder=3); ax.axvline(0, color=SUAVE, lw=.8)
ax.set_yticks(yy, t.modelo); ax.grid(axis="y", visible=False)
ax.set_xlabel("Reducción del MAE frente al paseo aleatorio en prueba (%), IC bootstrap al 95 %")
ax.set_title("Regresión: mejora sobre el paseo aleatorio (2025-2026)")
guardar(fig, "res_reg_modelos")

O["e_rw"], O["e_m"] = erw, e_er
mm = O.groupby("mes_obj")[["e_rw", "e_m"]].mean() * 100; S["reg_meses_gana"] = int((mm.e_m < mm.e_rw).sum()); S["n_meses"] = len(mm)
S["signos_p"] = float(stats.binomtest(S["reg_meses_gana"], len(mm), .5, alternative="greater").pvalue)
fig, ax = plt.subplots(figsize=(7.2, 2.7))
ax.plot(mm.index, mm.e_rw, color=GRIS, marker="o", ms=3, label="Paseo aleatorio"); ax.plot(mm.index, mm.e_m, color=NARANJA, marker="o", ms=3, label=ER)
ax.set_ylabel("MAE (p. p.)"); ax.legend(fontsize=8); ejes_fecha(ax); ax.set_title(f"Error absoluto medio por mes de prueba")
guardar(fig, "res_reg_mes")

O["dec"] = pd.qcut(O[ER], 10, labels=False, duplicates="drop")
dd = O.groupby("dec").agg(p=(ER, "median"), o=("y", "median"), q1=("y", lambda s: s.quantile(.25)), q3=("y", lambda s: s.quantile(.75)), alza=("alza", "mean"))
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9))
axs[0].errorbar(dd.p * 100, dd.o * 100, yerr=[(dd.o - dd.q1) * 100, (dd.q3 - dd.o) * 100], fmt="o", color=VERDE, ms=4, capsize=2)
lim = [dd.p.min() * 100 - 1, dd.p.max() * 100 + 1]; axs[0].plot(lim, lim, color=SUAVE, ls="--", lw=.8)
axs[0].set_xlabel("Cambio pronosticado (%)"); axs[0].set_ylabel("Cambio observado (%)"); axs[0].set_title("Mediana y rango intercuartil")
axs[1].bar(range(1, len(dd) + 1), dd.alza * 100, color=NARANJA, alpha=.85); axs[1].set_xlabel("Decil del cambio pronosticado"); axs[1].set_ylabel("Alzas > 15 % (%)")
axs[1].set_title("Alzas fuertes observadas por decil"); axs[1].set_xticks(range(1, 11))
guardar(fig, "res_reg_deciles"); S["reg_deciles"] = dd.round(4).to_dict("list")


def por(by):
    g = O.groupby(by).agg(rw=("e_rw", "mean"), m=("e_m", "mean"), n=("y", "size")); g["mejora"] = 1 - g.m / g.rw; return g


gg = por(O.grupo.map(GRUPOS)); dmg = {k: dm(q.y - q["Paseo aleatorio"], q.y - q[ER], q.mes_obj) for k, q in O.groupby(O.grupo.map(GRUPOS))}
gg["dm"] = [dmg[k][0] for k in gg.index]; gg["p"] = [dmg[k][1] for k in gg.index]; gg["p_holm"] = holm(gg.p.values)
S["reg_grupo"] = gg.round(4).to_dict("index")
gc = por("ciudad").sort_values("mejora"); gce = por("mercado").sort_values("mejora")
S["reg_ciudad"] = gc.round(4).to_dict("index"); S["reg_central"] = gce.round(4).to_dict("index")
fig, axs = plt.subplots(1, 2, figsize=(7.4, 5.6), gridspec_kw=dict(width_ratios=[1, 1.35]))
axs[0].barh([f"{c} ({n})" for c, n in zip(gc.index, gc.n)], gc.mejora * 100, color=[NARANJA if v < 0 else VERDE for v in gc.mejora], alpha=.85); axs[0].set_title("Por ciudad")
axs[1].barh([f"{m.replace(chr(34), '')[:30]} ({n})" for m, n in zip(gce.index, gce.n)], gce.mejora * 100, color=[NARANJA if v < 0 else AZUL for v in gce.mejora], alpha=.85); axs[1].set_title("Por central")
for a in axs: a.axvline(0, color=SUAVE, lw=.8); a.grid(axis="y", visible=False); a.tick_params(axis="y", labelsize=6.5); a.set_xlabel("Reducción del MAE vs. paseo aleatorio (%)")
fig.suptitle(f"Mejora de {ER} frente al paseo aleatorio (entre paréntesis, pronósticos)", x=.01, ha="left", fontweight="bold", fontsize=10)
fig.tight_layout(); guardar(fig, "res_reg_lugar")
gp = por("alimento").sort_values("n", ascending=False).head(20).sort_values("mejora"); S["reg_producto"] = gp.round(4).to_dict("index")
fig, ax = plt.subplots(figsize=(7.2, 4.4)); yy = np.arange(len(gp))
ax.barh(yy + .2, gp.rw * 100, .4, color=GRIS, alpha=.8, label="Paseo aleatorio"); ax.barh(yy - .2, gp.m * 100, .4, color=NARANJA, alpha=.85, label=ER)
ax.set_yticks(yy, gp.index, fontsize=7.5); ax.legend(fontsize=7.5, loc="lower right"); ax.grid(axis="y", visible=False)
ax.set_xlabel("MAE en prueba (p. p.)"); ax.set_title("Error por producto: los 20 con más pronósticos en prueba")
guardar(fig, "res_reg_producto")

# ================= CLASIFICACIÓN =================
def calibracion(yv, p, nb=10):
    """Intercepto y pendiente de calibración (regresión logística de y sobre logit p; ideal 0 y 1) y error de calibración
    esperado (ECE) con deciles de probabilidad."""
    from sklearn.linear_model import LogisticRegression
    lp = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    pend = LogisticRegression(C=1e6, max_iter=1000).fit(lp[:, None], yv); b = float(pend.coef_[0, 0])
    import scipy.optimize as so
    f = lambda a: -np.sum(yv * (a + lp) - np.log1p(np.exp(a + lp)))          # intercepto con pendiente fija en 1
    a = float(so.minimize_scalar(f, bounds=(-5, 5), method="bounded").x)
    q = pd.qcut(pd.Series(p).rank(method="first"), nb, labels=False).values
    ece = float(sum(np.mean(q == k) * abs(yv[q == k].mean() - p[q == k].mean()) for k in range(nb)))
    return dict(cal_intercepto=a, cal_pendiente=b, ece=ece)


ya = C.alza.values; mc_ = C.mes_obj.values; S["tasa_prueba"] = float(ya.mean())
MODS = MC + REFC
COLC = [AZUL, MORADO, VERDE, TEAL, NARANJA, VINO]
colc = dict(zip(MC, COLC)); colc["Frecuencia histórica"] = GRIS; colc["Logística autorregresiva"] = "#b0b8b3"; colc["SARIMA"] = "#6b7a72"
filas = []
for m in MODS:
    p = C[m].values
    pr, rpr = bootstrap_metrica(mc_, lambda i: average_precision_score(ya[i], p[i]), B=BOOT)
    ro, rro = bootstrap_metrica(mc_, lambda i: roc_auc_score(ya[i], p[i]), B=BOOT)
    r = dict(modelo=m, roc_auc=ro, roc_lo=ic(rro)[0], roc_hi=ic(rro)[1], pr_auc=pr, pr_lo=ic(rpr)[0], pr_hi=ic(rpr)[1], brier=brier_score_loss(ya, p), prob_media=float(p.mean()),
             logloss=log_loss(ya, np.clip(p, 1e-6, 1 - 1e-6)), **calibracion(ya, p))
    if m in MC:
        u = CS["umbral"][m]; yh = (p >= u).astype(int)
        r.update(umbral=u, alertas=float(yh.mean()), precision=precision_score(ya, yh), recall=recall_score(ya, yh), f1=f1_score(ya, yh), pr_val=CS["pr_val"][m],
                 logloss_crudo=log_loss(ya, np.clip(C[m + " (sin recalibrar)"].values, 1e-6, 1 - 1e-6)), **{k + "_crudo": v for k, v in calibracion(ya, C[m + " (sin recalibrar)"].values).items()})
    filas.append(r)
TC = pd.DataFrame(filas)
pe = C[EC].values
A_BONF_C = .05 / (len(TC) - 1)
for i, r in TC.iterrows():
    p = C[r.modelo].values
    d, rr = bootstrap_metrica(mc_, lambda k: average_precision_score(ya[k], p[k]) - average_precision_score(ya[k], pe[k]), B=BOOT)
    TC.loc[i, "dpr_vs_elegido"], TC.loc[i, "dpr_lo"], TC.loc[i, "dpr_hi"] = d, *ic(rr)
    TC.loc[i, "dpr_lo_bonf"], TC.loc[i, "dpr_hi_bonf"] = ic(rr, A_BONF_C)
TC.to_csv(RES / "clf_metricas_prueba.csv", index=False); S["clf_tabla"] = TC.to_dict("records")

fig, ax = plt.subplots(figsize=(5.6, 4.6))
for m in MODS:
    fpr, tpr, _ = roc_curve(ya, C[m]); ax.plot(fpr, tpr, color=colc[m], lw=2.0 if m == EC else 1.2, ls="--" if m in REFC else "-", label=f"{m} ({roc_auc_score(ya, C[m]):.3f})".replace(".", ","))
ax.plot([0, 1], [0, 1], color=SUAVE, lw=.8, ls=":"); ax.set_xlabel("Tasa de falsos positivos"); ax.set_ylabel("Tasa de verdaderos positivos")
ax.legend(fontsize=6.8, loc="lower right", title="AUC-ROC", title_fontsize=7); ax.set_title("Curvas ROC en prueba"); ax.set_aspect("equal")
guardar(fig, "res_clf_roc")
nf = int(np.ceil(len(MODS) / 4)); fig, axs = plt.subplots(nf, 4, figsize=(7.6, 2.05 * nf + .5), sharex=True, sharey=True)
fr0, tr0, _ = roc_curve(ya, C["Frecuencia histórica"])
for a, m in zip(axs.flat, MODS):
    fpr, tpr, _ = roc_curve(ya, C[m]); a.fill_between(fpr, tpr, color=colc[m], alpha=.12); a.plot(fpr, tpr, color=colc[m], lw=1.6)
    if m != "Frecuencia histórica": a.plot(fr0, tr0, color=GRIS, lw=1, ls="--")
    a.plot([0, 1], [0, 1], color=SUAVE, lw=.7, ls=":"); r = TC.set_index("modelo").loc[m]
    a.set_title(f"{m}\nAUC {r.roc_auc:.3f} [{r.roc_lo:.3f}; {r.roc_hi:.3f}]".replace(".", ","), fontsize=7); a.set_aspect("equal")
for a in list(axs.flat)[len(MODS):]: a.axis("off")
for a in axs[-1]: a.set_xlabel("Falsos positivos", fontsize=8)
for a in axs[:, 0]: a.set_ylabel("Verdaderos positivos", fontsize=8)
fig.suptitle("Curva ROC de cada modelo en prueba, AUC con IC bootstrap al 95 % (gris discontinua: frecuencia histórica)", x=.01, ha="left", fontweight="bold", fontsize=9.5)
fig.tight_layout(); guardar(fig, "res_clf_roc_modelos")

tcs = TC.sort_values("pr_auc"); fig, ax = plt.subplots(figsize=(7.2, 3.8)); yy = np.arange(len(tcs))
ax.errorbar(tcs.pr_auc, yy, xerr=[tcs.pr_auc - tcs.pr_lo, tcs.pr_hi - tcs.pr_auc], fmt="none", ecolor=SUAVE, lw=1, capsize=2)
ax.scatter(tcs.pr_auc, yy, c=[GRIS if m in REFC else (NARANJA if m == EC else VERDE) for m in tcs.modelo], s=36, zorder=3)
ax.axvline(ya.mean(), color=SUAVE, ls=":", lw=1); ax.text(ya.mean() + .004, -.6, "sin información", fontsize=7, color=SUAVE)
ax.set_yticks(yy, tcs.modelo); ax.grid(axis="y", visible=False); ax.set_xlabel("PR-AUC en prueba, IC bootstrap al 95 %"); ax.set_title("Clasificación: área bajo la curva de precisión y exhaustividad")
guardar(fig, "res_clf_pr_ic")
fig, ax = plt.subplots(figsize=(7.2, 3.6))
for m in [EC] + [m for m in MODS if m != EC]:
    pr, rc, _ = precision_recall_curve(ya, C[m]); ax.plot(rc, pr, color=colc[m], lw=2.0 if m == EC else 1.0, ls="--" if m in REFC else "-", alpha=1 if m == EC else .7, label=m)
ax.axhline(ya.mean(), color=SUAVE, ls=":", lw=1)
pe_ = TC.set_index("modelo").loc[EC]; ax.scatter([pe_.recall], [pe_.precision], color=colc[EC], s=40, zorder=4, edgecolor="white"); ax.annotate("umbral elegido", (pe_.recall, pe_.precision), xytext=(6, 6), textcoords="offset points", fontsize=7.5)
ax.set_xlabel("Exhaustividad"); ax.set_ylabel("Precisión"); ax.legend(fontsize=6.5, loc="upper right", ncol=2); ax.set_title("Curvas de precisión y exhaustividad en prueba")
guardar(fig, "res_clf_pr")

u = CS["umbral"][EC]; cm = confusion_matrix(ya, pe >= u); S["confusion"] = cm.tolist()
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw=dict(width_ratios=[1, 1.5]))
axs[0].imshow(cm, cmap="Oranges"); axs[0].grid(False)
for i in range(2):
    for j in range(2):
        axs[0].text(j, i, f"{cm[i, j]:,}".replace(",", ".") + f"\n({cm[i, j] / cm[i].sum() * 100:.0f} % de la fila)".replace(".", ","), ha="center", va="center", fontsize=8, color="white" if cm[i, j] > cm.max() / 2 else TINTA)
axs[0].set_xticks([0, 1], ["Sin alerta", "Alerta"]); axs[0].set_yticks([0, 1], ["Sin alza", "Alza > 15 %"]); axs[0].set_title(f"Matriz de confusión, {EC}")
tm = TC[TC.modelo.isin(MC)].set_index("modelo"); x = np.arange(len(tm))
for k_, (c_, col) in enumerate(zip(["precision", "recall", "f1"], [AZUL, NARANJA, VERDE])):
    axs[1].bar(x + (k_ - 1) * .27, tm[c_] * 100, .27, color=col, alpha=.85, label={"precision": "Precisión", "recall": "Exhaustividad", "f1": "F1"}[c_])
axs[1].set_xticks(x, [m.replace("Regresión logística", "Logística").replace("Random Forest", "R. Forest") for m in tm.index], fontsize=6.8, rotation=35, ha="right")
axs[1].set_ylabel("%"); axs[1].legend(fontsize=7, ncol=3, loc="upper center"); axs[1].set_ylim(0, 85); axs[1].set_title("Métricas con el umbral de cada modelo")
fig.tight_layout(); guardar(fig, "res_clf_confusion")

# diagrama de calibración del clasificador elegido: validación reunida y prueba (deciles de probabilidad)
def _deciles(p, yv, nb=10):
    q = pd.qcut(p, nb, duplicates="drop"); g = pd.DataFrame(dict(p=p, y=yv)).groupby(q, observed=True); return g.p.mean().values, g.y.mean().values, g.size().values
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.3), sharey=True)
for a, (tit, series) in zip(axs, (("Validación reunida (2022-2024)", [(PV[EC].values, PV.alza.values, colc[EC], "-", EC)]),
                                  ("Prueba (2025-2026)", [(C[EC + " (sin recalibrar)"].values, ya, GRIS, "--", "Sin recalibrar"), (pe, ya, colc[EC], "-", "Recalibrado")]))):
    for p_, y_, col, ls, lab in series:
        xm, ym, n_ = _deciles(p_, y_); a.plot(xm, ym, color=col, ls=ls, marker="o", ms=3.5, lw=1.4, label=lab)
    a.plot([0, 1], [0, 1], color=SUAVE, lw=.7, ls=":"); a.set_xlim(0, .8); a.set_ylim(0, .8); a.set_aspect("equal")
    a.set_xlabel("Probabilidad pronosticada (media del decil)"); a.set_title(tit, fontsize=9); a.legend(fontsize=7, loc="upper left")
axs[0].set_ylabel("Frecuencia observada de alzas")
fig.suptitle(f"Calibración de {EC} por deciles de probabilidad", x=.01, ha="left", fontweight="bold", fontsize=10.5); fig.tight_layout(); guardar(fig, "res_clf_calibracion")

# curva de decisión (beneficio neto) en validación y prueba
def beneficio(p, yv, us):
    n_ = len(yv); return np.array([((p >= uu) & (yv == 1)).sum() / n_ - ((p >= uu) & (yv == 0)).sum() / n_ * uu / (1 - uu) for uu in us])
us = np.round(np.arange(.05, .61, .01), 2); pv_, yv_ = PV[EC].values, PV.alza.values
nb_v, nb_t = beneficio(pv_, yv_, us), beneficio(pe, ya, us)
todo_v = yv_.mean() - (1 - yv_.mean()) * us / (1 - us); todo_t = ya.mean() - (1 - ya.mean()) * us / (1 - us)
nb_f = beneficio(C["Frecuencia histórica"].values, ya, us)
S["decision"] = dict(u=us.tolist(), nb_val=nb_v.tolist(), nb_prueba=nb_t.tolist(), nb_frec=nb_f.tolist(), todo_prueba=todo_t.tolist(),
                     rango_util_prueba=[float(us[(nb_t > np.maximum(todo_t, 0)) & (nb_t > 0)].min()), float(us[(nb_t > np.maximum(todo_t, 0)) & (nb_t > 0)].max())])
pf = C["Frecuencia histórica"].values; S["bn_ic"] = {}
for uu in (.10, .20, .25, round(u, 2), .40, .50):
    w_ = uu / (1 - uu); bn_ = lambda pp, k: ((pp[k] >= uu) & (ya[k] == 1)).mean() - ((pp[k] >= uu) & (ya[k] == 0)).mean() * w_
    d1, r1 = bootstrap_metrica(mc_, lambda k: bn_(pe, k) - max(ya[k].mean() - (1 - ya[k].mean()) * w_, 0.0), B=BOOT)
    d2, r2 = bootstrap_metrica(mc_, lambda k: bn_(pe, k) - bn_(pf, k), B=BOOT)
    S["bn_ic"][str(uu)] = dict(bn=float(bn_(pe, np.arange(len(ya)))), d_mejor_extremo=d1, ic1=ic(r1), d_frec=d2, ic2=ic(r2))
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.0), sharey=True)
for a, nb, td, tit in ((axs[0], nb_v, todo_v, "Validación (2022-2024)"), (axs[1], nb_t, todo_t, "Prueba (2025-2026)")):
    a.plot(us, nb * 100, color=colc[EC], lw=1.8, label=EC); a.plot(us, td * 100, color=GRIS, lw=1.2, ls="--", label="Alertar todo"); a.axhline(0, color=TINTA, lw=.8, label="No alertar")
    if tit.startswith("Prueba"): a.plot(us, nb_f * 100, color=OCRE, lw=1.2, label="Frecuencia histórica")
    a.axvline(u, color=SUAVE, ls=":", lw=.8); a.set_xlabel("Umbral u (equivale a c_FP / (c_FP + c_FN))"); a.set_title(tit); a.set_ylim(-2, max(nb_v.max(), nb_t.max()) * 100 + 2)
axs[0].set_ylabel("Beneficio neto (alzas netas por 100 casos)"); axs[1].legend(fontsize=7)
fig.suptitle("Curva de decisión: beneficio neto según el umbral", x=.01, ha="left", fontweight="bold", fontsize=10.5); fig.tight_layout(); guardar(fig, "res_clf_decision")

Ug = []
for uu in np.round(np.arange(.05, .71, .01), 2):
    yh = pv_ >= uu; tp = (yh & (yv_ == 1)).sum(); Ug.append(dict(u=uu, alertas=yh.mean(), precision=tp / max(yh.sum(), 1), recall=tp / yv_.sum()))
Ug = pd.DataFrame(Ug); Ug["f1"] = 2 * Ug.precision * Ug.recall / (Ug.precision + Ug.recall); Ug.to_csv(RES / "clf_umbral_val.csv", index=False)

C["alerta"] = (pe >= u).astype(int)
def res(q_):
    a = q_.alza.sum(); al = q_.alerta.sum(); tp = (q_.alerta * q_.alza).sum()
    return pd.Series(dict(n=len(q_), alzas=a, tasa=q_.alza.mean(), precision=tp / al if al else np.nan, recall=tp / a if a else np.nan, pr=average_precision_score(q_.alza, q_[EC]) if 0 < a < len(q_) else np.nan))
cg = C.groupby(C.grupo.map(GRUPOS)).apply(res); S["clf_grupo"] = cg.round(4).to_dict("index")
cmes = C.groupby(C.mes_obj.dt.to_period("M")).apply(res); S["clf_mes"] = {str(k_): v for k_, v in cmes.round(4).to_dict("index").items()}
S["corr_tasa_pr_mes"] = float(cmes[["tasa", "pr"]].corr().iloc[0, 1])
rocm = C.groupby(C.mes_obj.dt.to_period("M")).apply(lambda q_: roc_auc_score(q_.alza, q_[EC]))
S["roc_mes"] = [float(rocm.min()), float(rocm.max())]; S["corr_tasa_roc_mes"] = float(np.corrcoef(cmes.tasa.values, rocm.values)[0, 1])
S["pr_rel_mes"] = [float((cmes.pr / cmes.tasa).min()), float((cmes.pr / cmes.tasa).max())]; S["corr_tasa_prrel_mes"] = float(np.corrcoef(cmes.tasa, cmes.pr / cmes.tasa)[0, 1])
S["corr_prob_tasa_mes"] = float(np.corrcoef(C.groupby(C.mes_obj).alza.mean(), C.groupby(C.mes_obj)[EC].mean())[0, 1])
cc = C.groupby("ciudad").apply(res); S["clf_ciudad"] = cc.round(4).to_dict("index")
cce = C.groupby("mercado").apply(res); S["clf_central"] = cce.round(4).to_dict("index")
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw=dict(width_ratios=[1.6, 1]))
xs = cmes.index.to_timestamp()
axs[0].bar(xs, cmes.pr, width=20, color=colc[EC], alpha=.75, label="PR-AUC del mes"); axs[0].plot(xs, cmes.tasa, color=TINTA, marker="o", ms=3, lw=1, label="Tasa de alzas del mes")
axs[0].set_ylim(0, .9); axs[0].legend(fontsize=7, loc="upper right"); ejes_fecha(axs[0]); axs[0].set_title("PR-AUC y tasa de alzas por mes")
cgp = cg[cg.alzas >= 100]
axs[1].bar(range(len(cgp)), cgp.recall * 100, .38, color=NARANJA, alpha=.85, label="Exhaustividad"); axs[1].bar(np.arange(len(cgp)) + .38, cgp.precision * 100, .38, color=AZUL, alpha=.85, label="Precisión")
axs[1].set_xticks(np.arange(len(cgp)) + .19, [g_.split(" ")[0] for g_ in cgp.index], fontsize=7.5); axs[1].set_ylabel("%"); axs[1].legend(fontsize=7); axs[1].set_title("Por grupo (≥ 100 alzas)")
fig.tight_layout(); guardar(fig, "res_clf_mes_grupo")
cce2 = cce[cce.alzas >= 40].sort_values("recall")
fig, ax = plt.subplots(figsize=(7.2, 5.0)); yy = np.arange(len(cce2))
ax.barh(yy - .2, cce2.recall * 100, .4, color=NARANJA, alpha=.85, label="Exhaustividad"); ax.barh(yy + .2, cce2.precision * 100, .4, color=AZUL, alpha=.85, label="Precisión")
ax.set_yticks(yy, [f"{m.replace(chr(34), '')[:36]} ({int(a)})" for m, a in zip(cce2.index, cce2.alzas)], fontsize=6.8); ax.legend(fontsize=7.5, loc="lower right"); ax.grid(axis="y", visible=False)
ax.set_xlabel("%"); ax.set_title(f"Alertas por central (entre paréntesis, alzas observadas; mínimo 40)")
guardar(fig, "res_clf_central")

# ================= IMPORTANCIA POR PERMUTACIÓN DE BLOQUES =================
BLOQ = {**BLOQUES_BASE, **BLOQUES_NUEVOS}
bloques = {k: [v for v in vs if v in V] for k, vs in BLOQ.items()}; bloques = {k: v for k, v in bloques.items() if v}
ent, te = P[P.muestra != "prueba"], P[P.muestra == "prueba"]
sm = te.sample(8000, random_state=SEMILLA)
Xa, Xs = matrices(V, GRP, "arbol", ent, sm); mr = REGRESION[ER][1](RS["mejores"][ER]["params"]).fit(Xa, ent.y.values)
Xa2, Xs2 = matrices(V, GRP, "arbol", ent, sm, imputar_arbol=True); mcl = CLASIFICACION[EC][1](CS["mejores"][EC]["params"], 1.0).fit(Xa2, ent.alza.values)
base_r = np.mean(np.abs(sm.y.values - mr.predict(Xs))); base_c = average_precision_score(sm.alza.values, mcl.predict_proba(Xs2)[:, 1])
rng = np.random.default_rng(SEMILLA); imp = []
for k, vs in bloques.items():
    idx = [V.index(v) for v in vs]; ir, icl = [], []
    for _ in range(10):
        perm = rng.permutation(len(sm)); A, A2 = Xs.copy(), Xs2.copy(); A[:, idx] = Xs[perm][:, idx]; A2[:, idx] = Xs2[perm][:, idx]
        ir.append((np.mean(np.abs(sm.y.values - mr.predict(A))) - base_r) * 100); icl.append(base_c - average_precision_score(sm.alza.values, mcl.predict_proba(A2)[:, 1]))
    imp.append(dict(bloque=k, n=len(vs), reg=np.mean(ir), reg_sd=np.std(ir), clf=np.mean(icl), clf_sd=np.std(icl)))
IB = pd.DataFrame(imp).sort_values("reg"); IB.to_csv(RES / "importancia_bloques.csv", index=False); S["importancia_bloques"] = IB.set_index("bloque").round(5).to_dict("index")
fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.9), sharey=True)
axs[0].barh(IB.bloque, IB.reg, xerr=IB.reg_sd, color=VERDE, alpha=.85); axs[0].set_xlabel("Aumento del MAE al permutar el bloque (p. p.)"); axs[0].set_title(f"Regresión ({ER})")
axs[1].barh(IB.bloque, IB.clf, xerr=IB.clf_sd, color=NARANJA, alpha=.85); axs[1].set_xlabel("Caída de la PR-AUC al permutar el bloque"); axs[1].set_title(f"Clasificación ({EC})")
for a in axs: a.grid(axis="y", visible=False); a.tick_params(axis="y", labelsize=7.5)
fig.suptitle("Importancia por permutación conjunta de cada bloque de variables (prueba)", x=.01, ha="left", fontweight="bold", fontsize=10); fig.tight_layout(); guardar(fig, "res_importancia")
sens = {}
for L_ in (1, 2, 3, 4, 6):
    _, r1 = bootstrap_metrica(mes, lambda i: 1 - e_er[i].mean() / erw[i].mean(), B=BOOT, L=L_)
    _, r2 = bootstrap_metrica(mc_, lambda i: average_precision_score(ya[i], pe[i]), B=BOOT, L=L_)
    sens[L_] = dict(mejora=ic(r1), pr=ic(r2))
S["sens_bloque"] = sens
# ---- convergencia de la búsqueda aleatoria ----
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.0))
for a, arch, k_, tit, lab in ((axs[0], "reg_busqueda.json", "mae", "Regresión", "MAE promedio de validación (p. p.)"), (axs[1], "clf_busqueda.json", "pr", "Clasificación", "PR-AUC promedio de validación")):
    bq = leer_json(arch)
    for j, (m, v) in enumerate(bq.items()):
        c = np.asarray(v["curva"]) * (100 if k_ == "mae" else 1); a.plot(np.arange(1, len(c) + 1), c, color=COLC[j % len(COLC)], lw=1.4, label=m)
    a.set_xlabel("Configuraciones evaluadas"); a.set_ylabel(lab); a.set_title(tit)
axs[1].legend(fontsize=6.8); fig.suptitle("Mejor resultado acumulado de la búsqueda aleatoria", x=.01, ha="left", fontweight="bold", fontsize=10.5)
fig.tight_layout(); guardar(fig, "res_busqueda")
guardar_json(S, "resultados.json")
print(T[["modelo", "mae", "mase", "mejora", "mejora_lo", "mejora_hi", "p_holm", "series_gana"]].round(4).to_string()); print(TC[["modelo", "roc_auc", "roc_lo", "roc_hi", "pr_auc", "pr_lo", "pr_hi", "dpr_lo", "dpr_hi"]].round(4).to_string())
print(IB.round(4).to_string(), S["decision"]["rango_util_prueba"], S["signos_p"])
