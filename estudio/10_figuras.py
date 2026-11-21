"""Paso 10. Figuras del documento, en PDF vectorial y con un estilo común, a partir de los resultados de los pasos 1 a 7.
No estima nada: solo lee resultados/ y datos/panel.parquet."""
import json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from sklearn.metrics import roc_curve, precision_recall_curve, roc_auc_score, average_precision_score
from comun import RES, FIG, DATOS, GRUPOS, leer_json

from estilo import *

RS, CS = leer_json("reg_seleccion.json"), leer_json("clf_seleccion.json")
ER, EC = RS["elegido"], CS["elegido"]
REFR = ["Paseo aleatorio", "AR estacional", "SARIMA"]; REFC = ["Frecuencia histórica", "Logística autorregresiva", "SARIMA"]
R = json.loads((RES / "resultados.json").read_text())
CORTO = {"Regresión cuantílica": "Regresión cuantílica", "Regresión logística": "Regresión logística", "Logística autorregresiva": "Logística autorreg."}


def color(m, refs, elegido):
    return ACENTO if m == elegido else (CLARO if m in refs else OSCURO)


# ---------- 1. datos: alzas por grupo y estacionalidad ----------
P = pd.read_parquet(DATOS / "panel.parquet", columns=["grupo", "y", "alza", "mes_obj"])
P["g"] = P.grupo.map(GRUPOS)
gr = P.groupby("g").agg(alza=("alza", "mean"), abs_=("y", lambda s: s.abs().median()), n=("y", "size")).sort_values("alza")
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 2.6), gridspec_kw=dict(width_ratios=[1, 1.1]))
ax = axs[0]; yy = np.arange(len(gr))
ax.barh(yy, gr.alza * 100, color=OSCURO, height=.62)
for k, v in enumerate(gr.alza * 100): ax.text(v + .6, k, coma(v), va="center", fontsize=7.5, color=TINTA)
ax.set_yticks(yy, gr.index); ax.grid(axis="y", visible=False); ax.set_xlim(0, gr.alza.max() * 100 * 1.25)
ax.set_xlabel("Casos con alza mayor al 15 % (%)"); ax.set_title("a) Por grupo")
ax = axs[1]
P["mes"] = pd.to_datetime(P.mes_obj).dt.month
for g, c, ls in (("Verduras y hortalizas", ACENTO, "-"), ("Frutas", OSCURO, "-"), ("Tubérculos y plátanos", OSCURO, "--")):
    s = P[P.g == g].groupby("mes").alza.mean() * 100; ax.plot(s.index, s.values, color=c, ls=ls, lw=1.4, marker="o", ms=2.5, label=g)
ax.set_xticks(range(1, 13), list("EFMAMJJASOND")); ax.set_ylabel("Alzas mayores al 15 % (%)"); ax.set_ylim(0, None)
ax.legend(loc="upper center", bbox_to_anchor=(.5, -.2), ncol=3, handlelength=1.6, columnspacing=.8, fontsize=7); ax.set_title("b) Por mes del año")
fig.tight_layout(w_pad=1.5); guardar(fig, "fig_datos")

# ---------- 2. comparación de modelos ----------
TR = pd.read_csv(RES / "reg_metricas_prueba.csv"); TC = pd.read_csv(RES / "clf_metricas_prueba.csv")
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 2.9))
ax = axs[0]; t = TR[TR.modelo != "Paseo aleatorio"].sort_values("mejora"); yy = np.arange(len(t))
for k, (_, r) in enumerate(t.iterrows()):
    c = color(r.modelo, REFR, ER); ax.plot([r.mejora_lo * 100, r.mejora_hi * 100], [k, k], color=c, lw=1.4, solid_capstyle="butt")
    ax.plot(r.mejora * 100, k, "o", color=c, ms=4.5, mec="white", mew=.6)
ax.axvline(0, color=SUAVE, lw=.7); ax.set_yticks(yy, [CORTO.get(m, m) for m in t.modelo]); ax.grid(axis="y", visible=False)
ax.set_xlabel("Reducción del error frente al último precio (%)"); ax.set_title("a) Cambio del mes siguiente")
ax = axs[1]; t = TC.sort_values("pr_auc"); yy = np.arange(len(t))
for k, (_, r) in enumerate(t.iterrows()):
    c = color(r.modelo, REFC, EC); ax.plot([r.pr_lo, r.pr_hi], [k, k], color=c, lw=1.4, solid_capstyle="butt")
    ax.plot(r.pr_auc, k, "o", color=c, ms=4.5, mec="white", mew=.6)
tasa = R["tasa_prueba"]
ax.set_yticks(yy, [CORTO.get(m, m) for m in t.modelo]); ax.grid(axis="y", visible=False); eje_coma(ax, "x", 2)
ax.set_xlabel("Área bajo la curva PR"); ax.set_title("b) Alzas mayores al 15 %"); ax.set_xlim(.33, .57)
fig.tight_layout(w_pad=1.2); guardar(fig, "fig_modelos")

# ---------- 3. mejora por grupo y ciudad ----------
g = pd.DataFrame(R["reg_grupo"]).T.sort_values("mejora"); c_ = pd.DataFrame(R["reg_ciudad"]).T.sort_values("mejora")
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 3.3), gridspec_kw=dict(width_ratios=[1, 1]))
ax = axs[0]; yy = np.arange(len(g))
ax.barh(yy, g.mejora * 100, color=[ACENTO if p < .05 else CLARO for p in g.p_holm], height=.62)
ax.set_yticks(yy, [f"{i} ({int(n):,})".replace(",", ".") for i, n in zip(g.index, g.n)]); ax.axvline(0, color=SUAVE, lw=.7); ax.grid(axis="y", visible=False)
ax.set_xlabel("Reducción del error (%)"); ax.set_title("a) Por grupo (pronósticos)")
ax = axs[1]; yy = np.arange(len(c_))
ax.barh(yy, c_.mejora * 100, color=[OSCURO if v > 0 else CLARO for v in c_.mejora], height=.62)
ax.set_yticks(yy, c_.index, fontsize=7); ax.axvline(0, color=SUAVE, lw=.7); ax.grid(axis="y", visible=False)
ax.set_xlabel("Reducción del error (%)"); ax.set_title("b) Por ciudad")
fig.tight_layout(w_pad=1.5); guardar(fig, "fig_grupos")

# ---------- 4. curvas ROC y PR ----------
C = pd.read_parquet(RES / "clf_predicciones_prueba.parquet"); ya = C.alza.values
MODS = CS["modelos"] + REFC
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 2.75))
orden = [m for m in MODS if m != EC] + [EC]
for m in orden:
    c = color(m, REFC, EC); lw = 1.6 if m == EC else .8; ls = "--" if m in REFC else "-"; z = 3 if m == EC else 2
    f, t_, _ = roc_curve(ya, C[m]); axs[0].plot(f, t_, color=c, lw=lw, ls=ls, zorder=z)
    p, r, _ = precision_recall_curve(ya, C[m]); axs[1].plot(r, p, color=c, lw=lw, ls=ls, zorder=z)
axs[0].plot([0, 1], [0, 1], color=SUAVE, lw=.6, ls=":"); axs[1].axhline(tasa, color=SUAVE, lw=.6, ls=":")
axs[0].set_xlabel("Tasa de falsas alarmas"); axs[0].set_ylabel("Alzas detectadas"); axs[0].set_title("a) Curva ROC"); axs[0].set_aspect("equal")
axs[1].set_xlabel("Exhaustividad (alzas detectadas)"); axs[1].set_ylabel("Precisión"); axs[1].set_title("b) Curva de precisión y exhaustividad")
for a in axs: eje_coma(a, "x", 1); eje_coma(a, "y", 1)
from matplotlib.lines import Line2D
hs = [Line2D([], [], color=ACENTO, lw=1.6, label=EC), Line2D([], [], color=OSCURO, lw=.8, label="Otros modelos"), Line2D([], [], color=CLARO, lw=.8, ls="--", label="Referencias")]
axs[1].legend(handles=hs, loc="upper right")
fig.tight_layout(w_pad=1.5); guardar(fig, "fig_roc_pr")

# ---------- 5. calibración y curva de decisión ----------
pe = C[EC].values
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 2.6))
q = pd.qcut(pe, 10, duplicates="drop"); d = pd.DataFrame(dict(p=pe, y=ya)).groupby(q, observed=True).mean()
ax = axs[0]; ax.plot([0, .7], [0, .7], color=SUAVE, lw=.6, ls=":"); ax.plot(d.p, d.y, "o-", color=ACENTO, lw=1.3, ms=3.5)
ax.set_xlim(0, .7); ax.set_ylim(0, .7); ax.set_aspect("equal"); ax.set_xlabel("Probabilidad pronosticada"); ax.set_ylabel("Frecuencia observada")
ax.set_title("a) Calibración (deciles)"); eje_coma(ax, "x", 1); eje_coma(ax, "y", 1)
D = R["decision"]; us = np.array(D["u"]); ax = axs[1]
ax.plot(us, np.array(D["nb_prueba"]) * 100, color=ACENTO, lw=1.5, label=EC)
ax.plot(us, np.array(D["nb_frec"]) * 100, color=OSCURO, lw=1, ls="--", label="Frecuencia histórica")
ax.plot(us, np.array(D["todo_prueba"]) * 100, color=CLARO, lw=1, label="Alertar todo"); ax.axhline(0, color=SUAVE, lw=.7)
ax.set_ylim(-1, max(D["nb_prueba"]) * 100 + 1.5); ax.set_xlim(.05, .6); eje_coma(ax, "x", 1); eje_coma(ax, "y", 0)
ax.set_xlabel("Umbral de alerta $u$"); ax.set_ylabel("Alzas netas por cada 100 casos"); ax.set_title("b) Beneficio neto"); ax.legend(loc="upper right")
fig.tight_layout(w_pad=1.5); guardar(fig, "fig_calibracion")

# ---------- 6. importancia por bloque ----------
I = pd.DataFrame(R["importancia_bloques"]).T.sort_values("reg")
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 1.75), sharey=True)
yy = np.arange(len(I))
axs[0].barh(yy, I.reg, xerr=I.reg_sd, color=OSCURO, height=.6, error_kw=dict(lw=.7, capsize=1.5, ecolor=TINTA))
axs[1].barh(yy, I.clf, xerr=I.clf_sd, color=OSCURO, height=.6, error_kw=dict(lw=.7, capsize=1.5, ecolor=TINTA))
axs[0].set_yticks(yy, I.index); [a.grid(axis="y", visible=False) for a in axs]
axs[0].set_xlabel("Aumento del error (p. p.)"); axs[1].set_xlabel("Caída del área bajo la curva PR")
axs[0].set_title("a) Cambio del mes siguiente"); axs[1].set_title("b) Alzas mayores al 15 %"); eje_coma(axs[0], "x", 1); eje_coma(axs[1], "x", 2)
fig.tight_layout(w_pad=1.5); guardar(fig, "fig_importancia")

# ---------- 7. apéndice: ROC de cada clasificador ----------
fig, axs = plt.subplots(3, 3, figsize=(4.3, 3.0), sharex=True, sharey=True)
f0, t0, _ = roc_curve(ya, C["Frecuencia histórica"])
for a, m in zip(axs.flat, CS["modelos"] + REFC):
    f, t_, _ = roc_curve(ya, C[m]); a.plot(f, t_, color=color(m, REFC, EC) if m != EC else ACENTO, lw=1.1)
    if m != "Frecuencia histórica": a.plot(f0, t0, color=CLARO, lw=.7, ls="--")
    a.plot([0, 1], [0, 1], color=SUAVE, lw=.5, ls=":"); r = TC.set_index("modelo").loc[m]
    a.set_title(f"{CORTO.get(m, m)} (AUC {coma(r.roc_auc, 3)})", fontsize=6.8, pad=2)
    a.set_xticks([0, .5, 1]); a.set_yticks([0, .5, 1]); a.tick_params(labelsize=6.3, length=2, pad=1.5)
    eje_coma(a, "x", 1); eje_coma(a, "y", 1)
fig.supxlabel("Tasa de falsas alarmas", fontsize=7, y=.02); fig.supylabel("Exhaustividad", fontsize=7, x=.02)
fig.tight_layout(h_pad=.5, w_pad=.5, rect=(.03, .03, 1, 1)); guardar(fig, "fig_roc_modelos")
print("figuras listas;", FUENTE)


# =================== figuras adicionales ===================
P = pd.read_parquet(DATOS / "panel.parquet"); P["g"] = P.grupo.map(GRUPOS); P["mes_obj"] = pd.to_datetime(P.mes_obj)
import matplotlib.dates as mdates
def ejes_fecha(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator(2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
INI_VAL, INI_TE = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-01-01")

# ---------- 8. evolución en el tiempo ----------
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 2.8))
ax = axs[0]
for g, c, ls in (("Verduras y hortalizas", ACENTO, "-"), ("Frutas", OSCURO, "-"), ("Tubérculos y plátanos", OSCURO, "--"), ("Granos y cereales", CLARO, "-")):
    s = P[P.g == g].groupby("mes_obj").y.mean(); idx = 100 * np.exp(s.cumsum()); ax.plot(idx.index, idx.values, color=c, ls=ls, lw=1.2, label=g)
ax.set_ylabel("Índice (enero de 2019 = 100)"); ax.set_title("a) Índice de precios por grupo"); ejes_fecha(ax)
ax.legend(fontsize=6.8, loc="upper center", bbox_to_anchor=(.5, -.17), ncol=2, columnspacing=.8, handlelength=1.6)
ax = axs[1]; t = P.groupby("mes_obj").alza.mean() * 100
ax.axvspan(INI_VAL, INI_TE, color=REJILLA, alpha=.9, lw=0); ax.axvspan(INI_TE, t.index.max() + pd.Timedelta(days=20), color=REJILLA, alpha=.45, lw=0)
ax.plot(t.index, t.values, color=OSCURO, lw=1); ax.plot(t.index, t.rolling(12).mean(), color=ACENTO, lw=1.5)
ax.set_ylabel("Alzas mayores al 15 % (%)"); ax.set_title("b) Tasa mensual de alzas fuertes"); ejes_fecha(ax); ax.set_ylim(0, None)
fig.tight_layout(w_pad=1.5); guardar(fig, "fig_tiempo")

# ---------- 9. autocorrelación y abastecimiento ----------
B_ = pd.read_parquet(DATOS / "base_unida_mensual.parquet"); B_ = B_[B_.unidad == "$/kg"]
W = B_.merge(P[["mercado", "alimento"]].drop_duplicates()).pivot_table(index=["mercado", "alimento"], columns="mes", values="precio")
Rm = np.log(W).diff(axis=1); ac = {k: [] for k in range(1, 13)}
for _, s in Rm.iterrows():
    s = s.dropna()
    if len(s) >= 48:
        for k in ac: ac[k].append(s.autocorr(k))
acm = pd.DataFrame({k: [np.nanmedian(v), np.nanpercentile(v, 25), np.nanpercentile(v, 75)] for k, v in ac.items()}, index=["med", "p25", "p75"]).T
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 2.4))
ax = axs[0]; ax.bar(acm.index, acm.med, color=[ACENTO if k in (1, 12) else OSCURO for k in acm.index], width=.6)
ax.vlines(acm.index, acm.p25, acm.p75, color=TINTA, lw=.8); ax.axhline(0, color=SUAVE, lw=.7)
ax.set_xticks(range(1, 13)); ax.set_xlabel("Rezago (meses)"); ax.set_ylabel("Autocorrelación"); ax.set_title("a) Autocorrelación del cambio"); eje_coma(ax, "y", 1)
ax = axs[1]; q = P.dropna(subset=["cambio_ton_1m"]).copy(); q["d"] = pd.qcut(q.cambio_ton_1m.rank(method="first"), 10, labels=False) + 1
m_ = q.groupby("d")[["cambio_1m", "y"]].mean() * 100
ax.plot(m_.index, m_.cambio_1m, "o-", color=OSCURO, lw=1.2, ms=3, label="mismo mes"); ax.plot(m_.index, m_.y, "s--", color=ACENTO, lw=1.2, ms=3, label="mes siguiente")
ax.axhline(0, color=SUAVE, lw=.7); ax.set_xticks(range(1, 11)); ax.set_xlabel("Decil del cambio de toneladas"); ax.set_ylabel("Cambio medio del precio (%)")
ax.set_title("b) Precio y abastecimiento"); ax.legend(loc="upper right"); eje_coma(ax, "y", 1)
fig.tight_layout(w_pad=1.5); guardar(fig, "fig_autocorrelacion")

# ---------- 10. evidencia de la selección por bloques ----------
SB = pd.read_csv(RES / "seleccion_bloques.csv").dropna(subset=["bloque"])
SB["et"] = np.where(SB.tipo == "nuevo", "+ ", "− ") + SB.bloque; SB = SB.iloc[::-1]
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 2.6), sharey=True); yy = np.arange(len(SB))
for ax, c, lo, hi, signo, tit in ((axs[0], "d_mae", "mae_lo", "mae_hi", 1, "a) Cambio en el MAE (p. p.)"), (axs[1], "d_pr", "pr_lo", "pr_hi", -1, "b) Cambio en la AP")):
    for k, (_, r) in enumerate(SB.iterrows()):
        sig = (r[lo] > 0 or r[hi] < 0); mejora = (r[c] * signo < 0)
        col = ACENTO if sig and mejora else (OSCURO if sig else CLARO)
        ax.plot([r[lo], r[hi]], [k, k], color=col, lw=1.3); ax.plot(r[c], k, "o", color=col, ms=3.8, mec="white", mew=.5)
    ax.axvline(0, color=SUAVE, lw=.7); ax.grid(axis="y", visible=False); ax.set_title(tit)
axs[0].set_yticks(yy, SB.et); eje_coma(axs[0], "x", 2); eje_coma(axs[1], "x", 2)
fig.tight_layout(w_pad=1.2); guardar(fig, "fig_bloques")

# ---------- 11. error y AP por mes en la prueba ----------
O = pd.read_parquet(RES / "reg_predicciones_prueba.parquet"); O["mes_obj"] = pd.to_datetime(O.mes_obj)
em = O.assign(rw=O.y.abs(), m=(O.y - O[ER]).abs(), ar=(O.y - O["AR estacional"]).abs()).groupby("mes_obj")[["rw", "ar", "m"]].mean() * 100
C["mes_obj"] = pd.to_datetime(C.mes_obj)
pm = C.groupby("mes_obj")[["alza", EC]].apply(lambda d: pd.Series(dict(ap=average_precision_score(d.alza, d[EC]), tasa=d.alza.mean())))
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 2.8))
ax = axs[0]; ax.plot(em.index, em.rw, color=CLARO, lw=1.3, marker="o", ms=2.5, label="Último precio")
ax.plot(em.index, em.ar, color=OSCURO, lw=1, ls="--", label="AR estacional"); ax.plot(em.index, em.m, color=ACENTO, lw=1.5, marker="o", ms=2.5, label=ER)
ax.set_ylabel("MAE (p. p.)"); ax.set_title("a) Error por mes"); ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(.5, -.14), ncol=3, columnspacing=.7, handlelength=1.5); ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7])); ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
ax = axs[1]; ax.bar(pm.index, pm.ap, width=20, color=OSCURO, label="AP del mes"); ax.plot(pm.index, pm.tasa, color=ACENTO, marker="o", ms=2.5, lw=1.2, label="Tasa de alzas")
ax.set_title("b) Alertas por mes"); ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(.5, -.14), ncol=2); ax.set_ylim(0, .75); eje_coma(ax, "y", 1)
ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7])); ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
fig.tight_layout(w_pad=1.5); guardar(fig, "fig_mensual")

# ---------- 12. productos ----------
pr_ = pd.DataFrame(R["reg_producto"]).T.sort_values("mejora")
fig, ax = plt.subplots(figsize=(ANCHO, 3.3)); yy = np.arange(len(pr_))
ax.barh(yy, pr_.mejora * 100, color=[ACENTO if v > 0 else CLARO for v in pr_.mejora], height=.65)
ax.set_yticks(yy, [i.replace(" y/o Sweet", "") for i in pr_.index], fontsize=7.5); ax.axvline(0, color=SUAVE, lw=.7); ax.grid(axis="y", visible=False)
for k, (i, r) in enumerate(pr_.iterrows()):
    ax.text(max(r.mejora * 100, 0) + .4, k, f"{coma(r.rw * 100)} → {coma(r.m * 100)}", va="center", fontsize=6.5, color=SUAVE)
ax.set_xlabel("Reducción del error frente al último precio (%)"); ax.set_xlim(pr_.mejora.min() * 100 - 1, pr_.mejora.max() * 100 + 9)
fig.tight_layout(); guardar(fig, "fig_productos")

# ---------- 13. caso ilustrativo ----------
I_ = pd.read_parquet(RES / "intervalos_prueba.parquet"); I_["mes_obj"] = pd.to_datetime(I_.mes_obj)
casos = [("Medellín, Central Mayorista de Antioquia", "Mango Tommy"), ("Bogotá, D.C., Corabastos", "Cilantro")]
u = CS["umbral"][EC]; c_ = np.log(1.15) * 100
fig, axs = plt.subplots(2, 1, figsize=(ANCHO, 4.6), sharex=True)
for ax, (mc, al) in zip(axs, casos):
    o = O[(O.mercado == mc) & (O.alimento == al)].sort_values("mes_obj"); i_ = I_[(I_.mercado == mc) & (I_.alimento == al)].sort_values("mes_obj")
    p_ = C[(C.mercado == mc) & (C.alimento == al)].sort_values("mes_obj")
    ax.fill_between(i_.mes_obj, i_.lo80 * 100, i_.hi80 * 100, color=REJILLA, lw=0, label="Intervalo del 80 %")
    ax.axhline(c_, color=SUAVE, lw=.6, ls=":"); ax.axhline(0, color=SUAVE, lw=.5)
    ax.plot(o.mes_obj, o.y * 100, color=TINTA, lw=1.1, marker="o", ms=2.8, label="Cambio observado")
    ax.plot(o.mes_obj, o[ER] * 100, color=ACENTO, lw=1.3, marker="s", ms=2.5, label=f"Pronóstico de {ER}")
    al_ = p_[p_[EC] >= u]; ax.plot(al_.mes_obj, np.full(len(al_), ax.get_ylim()[1] * .92 if False else (i_.hi80.max() * 100 + 6)), "v", color=ACENTO, ms=4.5, label="Alerta")
    e1, e2 = o.y.abs().mean() * 100, (o.y - o[ER]).abs().mean() * 100
    ax.set_title(f"{al} en {mc.split(', ', 1)[-1].replace('D.C., ', '')} (MAE: último precio {coma(e1)}; {ER} {coma(e2)})", fontsize=8.5)
    ax.set_ylabel("Cambio mensual (%)")
h_, l_ = axs[0].get_legend_handles_labels(); fig.legend(h_, l_, fontsize=7.5, ncol=4, loc="upper center", bbox_to_anchor=(.5, 1.03))
axs[1].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10])); axs[1].xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
fig.tight_layout(h_pad=1, rect=(0, 0, 1, .96)); guardar(fig, "fig_caso")
print("adicionales listas")


# =================== interpretabilidad, residuos, comparación estadística y EDA adicional ===================
from comun import NOMBRES
NOM = dict(NOMBRES)   # mismos nombres que en las tablas
X_ = json.loads((RES / "explicaciones.json").read_text())
Vf = list(X_["shap_reg"].keys())


def enjambre(ax, D, tarea, k=12):
    imp = D[Vf].abs().mean().sort_values(ascending=False).index[:k][::-1]
    rng = np.random.default_rng(0); cm = matplotlib.colors.LinearSegmentedColormap.from_list("c", [OSCURO, "#d9d4cc", ACENTO])
    sub = D.sample(min(len(D), 6000), random_state=0)
    for j, v in enumerate(imp):
        s = sub[v].values * (100 if tarea == "reg" else 1); x = sub["x_" + v]
        r_ = x.rank(pct=True).fillna(.5).values
        ax.scatter(s, j + rng.normal(0, .11, len(s)).clip(-.3, .3), c=r_, cmap=cm, s=1.2, alpha=.6, linewidths=0, rasterized=True)
    ax.set_yticks(range(len(imp)), [NOM.get(v, v) for v in imp], fontsize=7.5); ax.axvline(0, color=SUAVE, lw=.6); ax.grid(axis="y", visible=False)
    return cm


Dr = pd.read_parquet(RES / "shap_reg.parquet"); Dc = pd.read_parquet(RES / "shap_clf.parquet")
fig, axs = plt.subplots(2, 1, figsize=(ANCHO, 6.8), gridspec_kw=dict(hspace=.42))
cm = enjambre(axs[0], Dr, "reg"); axs[0].set_title("a) Cambio del mes siguiente"); axs[0].set_xlabel("Aporte al pronóstico del cambio (p. p.)")
enjambre(axs[1], Dc, "clf"); axs[1].set_title("b) Alzas mayores al 15 %"); axs[1].set_xlabel("Aporte al riesgo de alza (escala logit)"); eje_coma(axs[0], "x", 0); eje_coma(axs[1], "x", 1)
sm = matplotlib.cm.ScalarMappable(cmap=cm); cb = fig.colorbar(sm, ax=axs, shrink=.35, pad=.02, aspect=18)
cb.set_ticks([0, 1], labels=["bajo", "alto"]); cb.set_label("Valor de la variable", fontsize=7.5); cb.ax.tick_params(labelsize=7); cb.outline.set_visible(False)
guardar(fig, "fig_shap")

# dos casos del clasificador: un alza anticipada y una que se escapó
Dc["mes_obj"] = pd.to_datetime(Dc.mes_obj)
a_ = Dc[(Dc.alimento == "Mango Tommy") & (Dc.mercado == "Medellín, Central Mayorista de Antioquia") & (Dc.alza == 1)].sort_values("_pred").iloc[-1]
b_ = Dc[(Dc.alza == 1) & (Dc.grupo.isin(["VERDURAS Y HORTALIZAS", "FRUTAS"])) & (Dc._pred < .08)].sort_values("y").iloc[-1]
CASOS_SHAP = []
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 3.4))
for ax, c, tit in ((axs[0], a_, "a) Alza anticipada"), (axs[1], b_, "b) Alza no anticipada")):
    s = c[Vf].astype(float); top = s.abs().sort_values(ascending=False).index[:7]; resto = s.drop(top).sum()
    vals = list(s[top].values) + [resto]; nombres = [NOM.get(v, v) for v in top] + ["Otras 17 variables"]
    pos = c._base
    for j, (vv, nn_) in enumerate(zip(vals[::-1], nombres[::-1])):
        pass
    cum = c._base; ys = np.arange(len(vals))[::-1]
    for y_, vv in zip(ys, vals):
        ax.barh(y_, vv, left=cum, color=ACENTO if vv > 0 else OSCURO, height=.6); cum += vv
    ax.axvline(c._base, color=SUAVE, lw=.6, ls=":"); ax.set_yticks(ys, nombres, fontsize=7); ax.grid(axis="y", visible=False)
    p0, p1 = 1 / (1 + np.exp(-c._base)), 1 / (1 + np.exp(-cum))
    lugar = c.mercado.split(", ", 1)[-1].replace("D.C., ", "")
    MESES_ = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    ax.set_title(f"{tit}: {c.alimento.lower().replace('tommy', 'Tommy')}\n{lugar}, {MESES_[c.mes_obj.month - 1]} de {c.mes_obj.year}", fontsize=8)
    ax.set_xlabel(f"Riesgo (logit): de {coma(p0 * 100, 0)} % a {coma(p1 * 100, 0)} %; subió {coma((np.exp(c.y) - 1) * 100, 0)} %", fontsize=7.5); eje_coma(ax, "x", 1)
    CASOS_SHAP.append(dict(alimento=c.alimento, mercado=c.mercado, mes=str(c.mes_obj.date()), p0=float(p0), p1=float(p1), alza=float(np.exp(c.y) - 1),
                           top=[(NOM.get(v, v), float(s[v])) for v in top[:4]]))
fig.tight_layout(w_pad=1.5); guardar(fig, "fig_shap_casos")
(RES / "casos_shap.json").write_text(json.dumps(CASOS_SHAP, indent=1, ensure_ascii=False))

# residuos
res_ = (O.y - O[ER]).values * 100; vol_ = Dr["x_vol_12m"].values
fig, axs = plt.subplots(1, 3, figsize=(ANCHO, 2.3))
ax = axs[0]; ax.hist(res_.clip(-80, 80), bins=80, color=OSCURO, density=True)
from scipy.stats import gaussian_kde
xx = np.linspace(-80, 80, 300); ax.plot(xx, gaussian_kde(res_.clip(-80, 80))(xx), color=ACENTO, lw=1.2)
ax.set_xlabel("Error (p. p.)"); ax.set_yticks([]); ax.set_title("a) Distribución")
ax = axs[1]; q_ = pd.qcut(pd.Series(O[ER].values).rank(method="first"), 10, labels=False) + 1; g_ = pd.Series(res_).groupby(q_.values)
ax.fill_between(range(1, 11), g_.quantile(.25), g_.quantile(.75), color=REJILLA); ax.plot(range(1, 11), g_.median(), "o-", color=ACENTO, ms=3, lw=1.2)
ax.axhline(0, color=SUAVE, lw=.6); ax.set_xticks(range(1, 11)); ax.set_xlabel("Decil del pronóstico"); ax.set_title("b) Error según el pronóstico")
ax = axs[2]; q2 = pd.qcut(pd.Series(vol_).rank(method="first"), 10, labels=False) + 1
ax.plot(range(1, 11), pd.Series(np.abs(res_)).groupby(q2.values).mean(), "o-", color=OSCURO, ms=3, lw=1.2)
ax.set_xticks(range(1, 11)); ax.set_xlabel("Decil de volatilidad pasada"); ax.set_ylabel("Error absoluto medio"); ax.set_title("c) Error según la volatilidad")
fig.tight_layout(w_pad=1); guardar(fig, "fig_residuos")


# diagrama de diferencia crítica (Nemenyi)
def dif_critica(ax, F, elegido):
    rk = pd.Series(F["rangos"]).sort_values(); k = len(rk); cd = F["cd"]
    ax.set_xlim(.6, k + .4); ax.set_ylim(-.2, 1.12); ax.axis("off"); ax.plot([1, k], [.8, .8], color=TINTA, lw=.8)
    for i in range(1, k + 1): ax.plot([i, i], [.8, .84], color=TINTA, lw=.8); ax.text(i, .88, str(i), ha="center", fontsize=7.5)
    ax.plot([1, 1 + cd], [1.0, 1.0], color=ACENTO, lw=1.5); ax.text(1 + cd + .1, 1.0, f"diferencia crítica = {coma(cd, 2)}", ha="left", va="center", fontsize=7.5, color=ACENTO)
    izq = rk.iloc[:(k + 1) // 2]; der = rk.iloc[(k + 1) // 2:]
    for j, (m, r) in enumerate(izq.items()):
        y = .62 - j * .14; ax.plot([r, r, .9], [.8, y, y], color=ACENTO if m == elegido else TINTA, lw=.7)
        ax.text(.85, y, f"{CORTO.get(m, m)} ({coma(r, 2)})", ha="right", va="center", fontsize=7.5, color=ACENTO if m == elegido else TINTA)
    for j, (m, r) in enumerate(der.iloc[::-1].items()):
        y = .62 - j * .14; ax.plot([r, r, k + .1], [.8, y, y], color=ACENTO if m == elegido else TINTA, lw=.7)
        ax.text(k + .15, y, f"({coma(r, 2)}) {CORTO.get(m, m)}", ha="left", va="center", fontsize=7.5, color=ACENTO if m == elegido else TINTA)
    # grupos sin diferencia significativa
    gr_ = []; rv = rk.values
    for i in range(k):
        j = max(jj for jj in range(k) if rv[jj] - rv[i] <= cd)
        if j > i and not any(a <= i and j <= b for a, b in gr_): gr_.append((i, j))
    for n_, (i, j) in enumerate(gr_):
        y = .74 - n_ * .045; ax.plot([rv[i] - .03, rv[j] + .03], [y, y], color=SUAVE, lw=2.2, solid_capstyle="round")


fig, axs = plt.subplots(2, 1, figsize=(ANCHO, 4.2))
dif_critica(axs[0], X_["friedman_reg"], ER); axs[0].set_title("a) Cambio del mes siguiente (rango según el MAE mensual)", loc="left", pad=2)
dif_critica(axs[1], X_["friedman_clf"], EC); axs[1].set_title("b) Alzas mayores al 15 % (rango según la AP mensual)", loc="left")
fig.tight_layout(h_pad=.5); guardar(fig, "fig_nemenyi")

# descomposición de una serie y distribución del cambio
from statsmodels.tsa.seasonal import STL
B_ = pd.read_parquet(DATOS / "base_unida_mensual.parquet")
s_ = B_[(B_.mercado == "Medellín, Central Mayorista de Antioquia") & (B_.alimento == "Mango Tommy") & (B_.unidad == "$/kg")].set_index("mes").precio.sort_index()
s_.index = pd.to_datetime(s_.index); s_ = np.log(s_.asfreq("MS").interpolate(limit_area="inside")).dropna()
st = STL(s_, period=12, robust=True).fit()
fig, axs = plt.subplots(4, 1, figsize=(ANCHO, 4.3), sharex=True)
for ax, (v, t_) in zip(axs, ((s_, "Logaritmo del precio"), (st.trend, "Tendencia"), (st.seasonal, "Estacionalidad"), (st.resid, "Residuo"))):
    ax.plot(v.index, v.values, color=ACENTO if t_ == "Estacionalidad" else OSCURO, lw=1.1); ax.set_ylabel(t_, fontsize=7.5); eje_coma(ax, "y", 1)
axs[-1].axhline(0, color=SUAVE, lw=.5); ejes_fecha(axs[-1]); axs[-1].xaxis.set_major_locator(mdates.YearLocator(1))
fig.tight_layout(h_pad=.3); guardar(fig, "fig_stl")
VARZ = dict(estac=float(1 - st.resid.var() / (st.seasonal + st.resid).var()))
fig, ax = plt.subplots(figsize=(ANCHO, 2.3))
perec = P.grupo.isin(["FRUTAS", "VERDURAS Y HORTALIZAS", "TUBERCULOS, RAICES Y PLATANOS"])
xx = np.linspace(-80, 80, 400)
for msk, col, lab in ((perec, ACENTO, "Perecederos"), (~perec, OSCURO, "No perecederos")):
    v = (P.y[msk] * 100).clip(-80, 80); ax.hist(v, bins=160, density=True, color=col, alpha=.25); ax.plot(xx, gaussian_kde(v.sample(min(len(v), 20000), random_state=0))(xx), color=col, lw=1.3, label=lab)
ax.axvline(np.log(1.15) * 100, color=SUAVE, lw=.7, ls=":"); ax.text(np.log(1.15) * 100 + 1.5, ax.get_ylim()[1] * .85, "alza del 15 %", fontsize=7, color=SUAVE)
ax.set_xlabel("Cambio mensual del precio (p. p., recortado en ±80)"); ax.set_yticks([]); ax.legend(); ax.set_xlim(-80, 80)
fig.tight_layout(); guardar(fig, "fig_distribucion")
(RES / "eda_extra.json").write_text(json.dumps(VARZ))
print("explicaciones listas")


# =================== figuras de la estructura final ===================
# cajas del cambio por grupo
ordg_ = P.groupby("g").y.apply(lambda s: s.abs().median()).sort_values().index
fig, ax = plt.subplots(figsize=(ANCHO, 2.6))
bp = ax.boxplot([P.y[P.g == g] * 100 for g in ordg_], vert=False, widths=.55, patch_artist=True, showfliers=True,
                flierprops=dict(marker=".", ms=1, alpha=.25, mec=CLARO), medianprops=dict(color=ACENTO, lw=1.4), whiskerprops=dict(color=SUAVE), capprops=dict(color=SUAVE))
for bx in bp["boxes"]: bx.set(facecolor=REJILLA, edgecolor=SUAVE)
ax.set_yticks(range(1, len(ordg_) + 1), ordg_); ax.set_xlim(-100, 100); ax.axvline(np.log(1.15) * 100, color=SUAVE, lw=.6, ls=":")
ax.set_xlabel("Cambio mensual del precio (p. p.; eje recortado en ±100)"); ax.grid(axis="y", visible=False)
fig.tight_layout(); guardar(fig, "fig_cajas")

# correlaciones de Spearman entre el objetivo y las variables principales
VC = ["y", "cambio_1m", "cambio_12m", "vol_12m", "dist_max_12m", "dist_min_12m", "frec_alza_hist", "cambio_estacional_hist", "cambio_nacional_1m", "brecha_nacional", "prop_centrales_alza", "cambio_ton_1m", "oni"]
NC = {"y": "Cambio del mes siguiente", **NOM, "cambio_ton_1m": "Cambio de toneladas, 1 mes", "oni": "ONI"}
cr = P[P.muestra == "entrenamiento"][VC].corr(method="spearman")
fig, ax = plt.subplots(figsize=(ANCHO, 4.6))
cm2 = matplotlib.colors.LinearSegmentedColormap.from_list("d", [OSCURO, "#f4f2ee", ACENTO])
cr2 = cr.iloc[1:, :-1]; mask = np.triu(np.ones_like(cr2, dtype=bool), 1); crm = np.ma.masked_where(mask, cr2.values)
im = ax.imshow(crm, cmap=cm2, vmin=-1, vmax=1); ax.grid(False)
for i in range(cr2.shape[0]):
    for j in range(i + 1):
        ax.text(j, i, coma(cr2.values[i, j], 2).replace("0,", ",").replace("-,", "−,"), ha="center", va="center", fontsize=6, color=TINTA)
ax.set_xticks(range(cr2.shape[1]), [NC.get(v, v) for v in cr2.columns], rotation=55, ha="right", fontsize=7); ax.set_yticks(range(cr2.shape[0]), [NC.get(v, v) for v in cr2.index], fontsize=7)
for s_ in ax.spines.values(): s_.set_visible(False)
cb = fig.colorbar(im, ax=ax, shrink=.6, pad=.02); cb.ax.tick_params(labelsize=7); cb.outline.set_visible(False); cb.ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: coma(v, 1)))
fig.tight_layout(); guardar(fig, "fig_correlaciones")

# pronóstico frente a observado (CatBoost, prueba)
fig, ax = plt.subplots(figsize=(ANCHO * .62, 2.9))
q_ = pd.qcut(O[ER].rank(method="first"), 20, labels=False); g_ = O.groupby(q_)
ax.scatter(O[ER] * 100, O.y * 100, s=1, alpha=.06, color=CLARO, rasterized=True, linewidths=0)
ax.plot(g_[ER].mean() * 100, g_.y.median() * 100, "o-", color=ACENTO, ms=3, lw=1.2, label="Mediana observada (veintiles)")
ax.fill_between(g_[ER].mean() * 100, g_.y.quantile(.25) * 100, g_.y.quantile(.75) * 100, color=ACENTO, alpha=.15, lw=0, label="Rango intercuartil")
ax.plot([-30, 30], [-30, 30], color=SUAVE, lw=.7, ls=":"); ax.set_xlim(-30, 30); ax.set_ylim(-60, 60)
ax.set_xlabel("Cambio pronosticado (p. p.)"); ax.set_ylabel("Cambio observado (p. p.)"); ax.legend(fontsize=7, loc="upper left")
fig.tight_layout(); guardar(fig, "fig_pred_obs")

# matriz de confusión de CatBoost con el umbral elegido
u_ = CS["umbral"][EC]; al_ = C[EC].values >= u_
mc_ = np.array([[((~al_) & (ya == 0)).sum(), (al_ & (ya == 0)).sum()], [((~al_) & (ya == 1)).sum(), (al_ & (ya == 1)).sum()]])
fig, ax = plt.subplots(figsize=(ANCHO * .5, 2.4))
ax.imshow(mc_ / mc_.sum(axis=1, keepdims=True), cmap=matplotlib.colors.LinearSegmentedColormap.from_list("m", ["#f7f5f2", ACENTO]), vmin=0, vmax=1); ax.grid(False)
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{mc_[i, j]:,}".replace(",", ".") + f"\n({coma(mc_[i, j] / mc_[i].sum() * 100, 0)} %)", ha="center", va="center", fontsize=8, color=TINTA)
ax.set_xticks([0, 1], ["Sin alerta", "Alerta"]); ax.set_yticks([0, 1], ["Sin alza", "Alza"]); ax.set_xlabel("Pronóstico"); ax.set_ylabel("Observado")
for s_ in ax.spines.values(): s_.set_visible(False)
fig.tight_layout(); guardar(fig, "fig_confusion")

# SARIMA: serie de ejemplo y diagnóstico de residuos
if (RES / "sarima_ejemplo.parquet").exists():
    from statsmodels.tsa.stattools import acf
    E = pd.read_parquet(RES / "sarima_ejemplo.parquet"); E["mes"] = pd.to_datetime(E.mes)
    fig, ax = plt.subplots(figsize=(ANCHO, 2.5)); fu = E[~E.dentro]
    ax.plot(E.mes, np.exp(E.y) / 1000, color=TINTA, lw=1, label="Precio observado")
    ax.plot(E.mes[E.dentro][13:], np.exp(E.ajuste[E.dentro][13:]) / 1000, color=OSCURO, lw=1, ls="--", label="Ajuste en el periodo de estimación")
    ax.fill_between(fu.mes, np.exp(fu.lo80) / 1000, np.exp(fu.hi80) / 1000, color=ACENTO, alpha=.18, lw=0, label="Intervalo del 80 %")
    ax.plot(fu.mes, np.exp(fu.ajuste) / 1000, color=ACENTO, lw=1.4, marker="o", ms=2.5, label="Pronóstico a un mes (prueba)")
    ax.axvline(pd.Timestamp("2025-01-01"), color=SUAVE, lw=.6, ls=":"); ax.set_ylabel("Miles de pesos por kg"); ejes_fecha(ax); ax.xaxis.set_major_locator(mdates.YearLocator(1)); eje_coma(ax, "y", 1)
    ax.legend(fontsize=7, loc="upper left", ncol=2); fig.tight_layout(); guardar(fig, "fig_sarima_ejemplo")
    r_ = E.residuo.dropna()
    fig, axs = plt.subplots(1, 3, figsize=(ANCHO, 2.2))
    axs[0].plot(E.mes[E.residuo.notna()], r_, color=OSCURO, lw=.9); axs[0].axhline(0, color=SUAVE, lw=.6); axs[0].set_title("a) Residuos"); ejes_fecha(axs[0]); eje_coma(axs[0], "y", 2)
    ac_ = acf(r_, nlags=24)[1:]; lim_ = 1.96 / np.sqrt(len(r_))
    axs[1].axhspan(-lim_, lim_, color=REJILLA, lw=0, zorder=0); axs[1].bar(range(1, 25), ac_, color=[ACENTO if k in (12, 24) else OSCURO for k in range(1, 25)], width=.6, zorder=2); axs[1].axhline(0, color=SUAVE, lw=.5)
    axs[1].set_title("b) Autocorrelación"); axs[1].set_xlabel("Rezago"); eje_coma(axs[1], "y", 1)
    axs[2].hist(r_, bins=18, color=OSCURO, density=True); axs[2].set_title("c) Distribución"); axs[2].set_yticks([]); eje_coma(axs[2], "x", 1)
    fig.tight_layout(w_pad=1); guardar(fig, "fig_sarima_residuos")
print("estructura final lista")
