"""Paso 14. Análisis exploratorio complementario para el documento: datos faltantes, cobertura por central, cambio por año,
persistencia de las alzas, productos más y menos volátiles, estacionalidad por producto, abastecimiento, transmisión entre
centrales, ONI y autocorrelación de una serie de ejemplo. Solo describe datos; no interviene en ninguna decisión.
Escribe figuras en figuras/ y tablas en resultados/eda2_*.csv y resultados/eda2.json."""
import json
import numpy as np, pandas as pd
import matplotlib.dates as mdates
from statsmodels.tsa.stattools import acf, pacf
from comun import *
from estilo import *

P = cargar_panel(); P["g"] = P.grupo.map(GRUPOS); P["mes_obj"] = pd.to_datetime(P.mes_obj); P["mes"] = pd.to_datetime(P.mes)
B = pd.read_parquet(DATOS / "base_unida_mensual.parquet"); B["mes"] = pd.to_datetime(B.mes)
bk = B[B.unidad == "$/kg"]; pares = P[["mercado", "alimento", "grupo", "ciudad"]].drop_duplicates()
meses = pd.date_range(bk.mes.min(), bk.mes.max(), freq="MS")
W = bk.merge(pares[["mercado", "alimento"]]).pivot_table(index=["mercado", "alimento"], columns="mes", values="precio", aggfunc="first").reindex(columns=meses)
S = {}
ABR = {"Frutas": "Frutas", "Verduras y hortalizas": "Verduras", "Tubérculos y plátanos": "Tubérculos", "Procesados": "Procesados",
       "Granos y cereales": "Granos", "Lácteos y huevos": "Lácteos", "Pescados": "Pescados"}

# ---------- 1. datos faltantes ----------
# faltante desde el primer mes con precio de cada serie (no se cuentan los meses antes de que la serie empiece)
obs = W.notna(); inicio = obs.values.argmax(axis=1)
viva = np.arange(W.shape[1])[None, :] >= inicio[:, None]
F = pd.DataFrame(np.where(viva, ~obs.values, np.nan), index=W.index, columns=W.columns)
gser = pares.set_index(["mercado", "alimento"]).grupo.map(GRUPOS).reindex(W.index)
falt = F.T.groupby(F.columns.year).mean().T.groupby(gser.values).mean() * 100
falt = falt.loc[[g for g in ["Frutas", "Verduras y hortalizas", "Tubérculos y plátanos", "Procesados", "Granos y cereales", "Lácteos y huevos", "Pescados"] if g in falt.index]]
S["falt_total"] = float(np.nanmean(F.values) * 100)
huecos = []
for v in F.values:
    v = v[~np.isnan(v)]; k = 0
    for x in np.r_[v, 0]:
        if x == 1: k += 1
        elif k: huecos.append(k); k = 0
h = pd.Series(huecos); cat = pd.cut(h, [0, 1, 2, 6, 1000], labels=["1 mes", "2 meses", "3 a 6 meses", "Más de 6"])
dist = cat.value_counts(normalize=True).reindex(["1 mes", "2 meses", "3 a 6 meses", "Más de 6"]) * 100
mesesf = h.groupby(cat, observed=False).sum() / h.sum() * 100
S["huecos"] = dict(n=int(len(h)), pct=dist.round(1).to_dict(), pct_meses=mesesf.round(1).to_dict())
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 2.7), gridspec_kw=dict(width_ratios=[1.75, 1]))
ax = axs[0]; cm_ = matplotlib.colors.LinearSegmentedColormap.from_list("f", ["#f7f5f2", ACENTO])
ax.imshow(falt.values, cmap=cm_, vmin=0, vmax=max(20, np.nanmax(falt.values)), aspect="auto"); ax.grid(False)
for i in range(falt.shape[0]):
    for j in range(falt.shape[1]):
        ax.text(j, i, coma(falt.values[i, j], 0), ha="center", va="center", fontsize=7, color=TINTA)
ax.set_xticks(range(falt.shape[1]), falt.columns, fontsize=7.5); ax.set_yticks(range(falt.shape[0]), [ABR[g] for g in falt.index], fontsize=7.5)
for s_ in ax.spines.values(): s_.set_visible(False)
ax.set_title("a) Meses sin precio (%) por grupo y año")
ax = axs[1]; yy = np.arange(4)[::-1]
ax.barh(yy + .18, dist.values, height=.36, color=OSCURO, label="Huecos"); ax.barh(yy - .18, mesesf.values, height=.36, color=ACENTO, label="Meses faltantes")
ax.set_yticks(yy, dist.index, fontsize=7.5); ax.grid(axis="y", visible=False); ax.set_xlabel("%"); ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(.45, -.22), ncol=2, handlelength=1)
ax.set_title("b) Duración de los huecos")
fig.tight_layout(w_pad=1.2); guardar(fig, "fig_faltantes")
CO = leer_json("complementarios.json")["faltantes"]; S["falt_objetivo"] = {k: v for k, v in CO.items() if k != "sensibilidad"}

# ---------- 2. cobertura por central ----------
ct = []
for (mc, ciu), g in pares.groupby(["mercado", "ciudad"]):
    idx = list(zip(g.mercado, g.alimento)); f_ = F.loc[idx]
    pm = P[P.mercado == mc]
    ct.append(dict(central=mc.split(", ")[-1].replace('"', ""), ciudad=ciu, series=len(g), con_precio=100 - float(np.nanmean(f_.values) * 100),
                   obs=len(pm), alza=float(pm.alza.mean() * 100), mediana_abs=float(pm.y.abs().median() * 100)))
CT = pd.DataFrame(ct).sort_values("series", ascending=False); CT.to_csv(RES / "eda2_centrales.csv", index=False)

# ---------- 3. cambio por año ----------
P["ano"] = P.mes_obj.dt.year; per = P.grupo.isin(["FRUTAS", "VERDURAS Y HORTALIZAS", "TUBERCULOS, RAICES Y PLATANOS"])
fig, ax = plt.subplots(figsize=(ANCHO, 2.4)); anos = sorted(P.ano.unique())
bp = ax.boxplot([P.y[(P.ano == a) & per] * 100 for a in anos], positions=np.arange(len(anos)), widths=.5, patch_artist=True, showfliers=False,
                medianprops=dict(color=ACENTO, lw=1.4), whiskerprops=dict(color=SUAVE), capprops=dict(color=SUAVE))
for bx in bp["boxes"]: bx.set(facecolor=REJILLA, edgecolor=SUAVE)
tasa_ano = P[per].groupby("ano").alza.mean() * 100
ax2 = ax.twinx(); ax2.plot(np.arange(len(anos)), tasa_ano.values, "o-", color=OSCURO, ms=3, lw=1); ax2.set_ylabel("Alzas >15 % (%)", fontsize=8, color=OSCURO)
ax2.set_ylim(0, 40); ax2.grid(False); ax2.spines["right"].set_visible(True)
ax.set_xticks(np.arange(len(anos)), anos); ax.set_ylabel("Cambio mensual (p. p.)"); ax.axhline(0, color=SUAVE, lw=.5)
fig.tight_layout(); guardar(fig, "fig_anos")
S["anos"] = dict(iqr={int(a): float((P.y[(P.ano == a) & per].quantile(.75) - P.y[(P.ano == a) & per].quantile(.25)) * 100) for a in anos}, tasa=tasa_ano.round(1).to_dict())

# ---------- 4. persistencia de las alzas ----------
T = P[P.muestra == "entrenamiento"].copy()
T["estado"] = np.select([T.cambio_1m > UMBRAL, T.cambio_1m < -UMBRAL], ["Alza mayor al 15 %", "Baja mayor al 15 %"], "Cambio menor")
pe_ = T.groupby("estado").agg(n=("alza", "size"), p_alza=("alza", "mean"), p_baja=("y", lambda s: (s < -UMBRAL).mean()))
pe_ = pe_.loc[["Alza mayor al 15 %", "Cambio menor", "Baja mayor al 15 %"]]; pe_.to_csv(RES / "eda2_persistencia.csv")
S["persistencia"] = pe_.round(4).reset_index().to_dict(orient="records")

# ---------- 5. productos más y menos volátiles ----------
pv = P.groupby("alimento").agg(g=("g", "first"), n=("y", "size"), series=("mercado", "nunique"), med=("y", lambda s: s.abs().median() * 100), alza=("alza", "mean"))
pv = pv[pv.n >= 300].sort_values("med", ascending=False)
pd.concat([pv.head(10).assign(lado="más"), pv.tail(10).iloc[::-1].assign(lado="menos")]).to_csv(RES / "eda2_volatiles.csv")
S["n_productos_vol"] = int(len(pv))

# ---------- 6. estacionalidad por producto ----------
top = P.groupby("alimento").size().sort_values(ascending=False).index[:16]
H = (P[P.alimento.isin(top)].pivot_table(index="alimento", columns=P.mes_obj.dt.month, values="alza", aggfunc="mean") * 100)
H = H.loc[H.max(axis=1).sort_values(ascending=False).index]
fig, ax = plt.subplots(figsize=(ANCHO, 3.6))
ax.imshow(H.values, cmap=cm_, vmin=0, vmax=60, aspect="auto"); ax.grid(False)
for i in range(H.shape[0]):
    for j in range(12):
        ax.text(j, i, coma(H.values[i, j], 0), ha="center", va="center", fontsize=6.5, color=TINTA if H.values[i, j] < 45 else "white")
ax.set_xticks(range(12), ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"], fontsize=7.5)
ax.set_yticks(range(H.shape[0]), [a.replace(" y/o Sweet", "") for a in H.index], fontsize=7.5)
for s_ in ax.spines.values(): s_.set_visible(False)
fig.tight_layout(); guardar(fig, "fig_estacional_productos")
S["estac_prod"] = {a: dict(max=float(H.loc[a].max()), mes=int(H.loc[a].idxmax()), min=float(H.loc[a].min())) for a in H.index}

# ---------- 7. abastecimiento ----------
Bt = B.merge(pares[["mercado", "alimento"]]); Bt["g"] = Bt.grupo.map(GRUPOS)
tg = Bt.groupby(["g", "mes"]).ton.sum().unstack(0) / 1000
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 2.8))
ax = axs[0]
for g, c, ls in (("Verduras y hortalizas", ACENTO, "-"), ("Frutas", OSCURO, "-"), ("Tubérculos y plátanos", OSCURO, "--"), ("Granos y cereales", CLARO, "-")):
    ax.plot(tg.index, tg[g].rolling(3, center=True).mean(), color=c, ls=ls, lw=1.1, label=ABR[g])
ax.set_ylabel("Miles de toneladas al mes"); ax.set_title("a) Toneladas por grupo"); ax.xaxis.set_major_locator(mdates.YearLocator(2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.legend(fontsize=7, ncol=4, loc="upper center", bbox_to_anchor=(.5, -.12), handlelength=1.4, columnspacing=.6)
ax = axs[1]
# correlación cruzada mediana por serie entre el cambio de toneladas en t+k y el cambio del precio en t
Wt = Bt.pivot_table(index=["mercado", "alimento"], columns="mes", values="ton", aggfunc="first").reindex(columns=meses)
Wp = np.log(W).diff(axis=1); Wtt = np.log(Wt.where(Wt > 0)).diff(axis=1).reindex(Wp.index)
Wo = Wp.copy() * np.nan
prom = Wp.groupby(level=1).transform("sum"); cnt = Wp.notna().groupby(level=1).transform("sum")
otras = (prom - Wp.fillna(0)) / (cnt - Wp.notna().astype(int)).replace(0, np.nan)
lags = range(-3, 4); cc_t, cc_o = {}, {}
for k in lags:
    a_, b_ = [], []
    for idx in Wp.index:
        p_ = Wp.loc[idx]; t_ = Wtt.loc[idx].shift(-k); o_ = otras.loc[idx].shift(-k)
        m1 = p_.notna() & t_.notna(); m2 = p_.notna() & o_.notna()
        if m1.sum() > 30: a_.append(np.corrcoef(p_[m1], t_[m1])[0, 1])
        if m2.sum() > 30: b_.append(np.corrcoef(p_[m2], o_[m2])[0, 1])
    cc_t[k], cc_o[k] = float(np.nanmedian(a_)), float(np.nanmedian(b_))
ax.plot(list(lags), [cc_o[k] for k in lags], "o-", color=ACENTO, ms=3.5, lw=1.3, label="Precio en las demás centrales")
ax.plot(list(lags), [cc_t[k] for k in lags], "s--", color=OSCURO, ms=3.5, lw=1.2, label="Toneladas en la central")
ax.axhline(0, color=SUAVE, lw=.6); ax.axvline(0, color=SUAVE, lw=.5, ls=":"); ax.set_xticks(list(lags))
ax.set_xlabel("Rezago $k$ (meses)"); ax.set_ylabel("Correlación mediana"); ax.set_title("b) Correlación con el cambio del precio"); ax.legend(fontsize=7, loc="upper right")
eje_coma(ax, "y", 1); fig.tight_layout(w_pad=1.3); guardar(fig, "fig_abastecimiento")
S["cc_ton"] = cc_t; S["cc_otras"] = cc_o
est_ton = Bt.assign(m=Bt.mes.dt.month).groupby(["g", "m"]).ton.sum().unstack(1); est_ton = (est_ton.div(est_ton.mean(axis=1), axis=0) * 100)
S["est_ton"] = {g: dict(max=float(est_ton.loc[g].max()), mes_max=int(est_ton.loc[g].idxmax()), min=float(est_ton.loc[g].min()), mes_min=int(est_ton.loc[g].idxmin())) for g in ["Frutas", "Verduras y hortalizas", "Tubérculos y plátanos"]}

# ---------- 8. ONI y alzas ----------
oni = pd.read_csv(DATOS / "oni_v6.csv"); oni = oni.melt(id_vars="year", var_name="tri", value_name="oni")
orden = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]; oni["m"] = oni.tri.map({t: i + 1 for i, t in enumerate(orden)})
oni["mes"] = pd.to_datetime(dict(year=oni.year, month=oni.m, day=1)); oni = oni.sort_values("mes").set_index("mes").oni
oni = oni[(oni.index >= "2018-01-01") & (oni.index <= meses.max())]
ta = P.groupby("mes_obj").alza.mean() * 100
fig, ax = plt.subplots(figsize=(ANCHO, 2.4))
ax.fill_between(oni.index, 0, oni.values, where=oni.values >= 0, color=ACENTO, alpha=.35, lw=0, step="mid")
ax.fill_between(oni.index, 0, oni.values, where=oni.values < 0, color=OSCURO, alpha=.35, lw=0, step="mid")
ax.axhline(.5, color=ACENTO, lw=.5, ls=":"); ax.axhline(-.5, color=OSCURO, lw=.5, ls=":"); ax.set_ylabel("ONI (°C)"); eje_coma(ax, "y", 1)
ax2 = ax.twinx(); ax2.plot(ta.index, ta.rolling(3, center=True).mean(), color=TINTA, lw=1.1); ax2.set_ylabel("Alzas >15 % (%)", fontsize=8); ax2.grid(False); ax2.spines["right"].set_visible(True)
ax2.set_ylim(0, 40); ax.xaxis.set_major_locator(mdates.YearLocator(1)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.tight_layout(); guardar(fig, "fig_oni")
S["corr_oni_tasa"] = {str(k): float(pd.concat([oni.shift(k), ta], axis=1).dropna().corr().iloc[0, 1]) for k in (0, 2, 4, 6)}

# ---------- 9. ACF y PACF de la serie de ejemplo ----------
s_ = bk[(bk.mercado == "Medellín, Central Mayorista de Antioquia") & (bk.alimento == "Mango Tommy")].set_index("mes").precio.sort_index().asfreq("MS")
r_ = np.log(s_).interpolate(limit_area="inside").diff().dropna()
a_ = acf(r_, nlags=24)[1:]; p_ = pacf(r_, nlags=24)[1:]; lim_ = 1.96 / np.sqrt(len(r_))
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 2.2), sharey=True)
for ax, v, t in ((axs[0], a_, "a) Autocorrelación"), (axs[1], p_, "b) Autocorrelación parcial")):
    ax.axhspan(-lim_, lim_, color=REJILLA, lw=0, zorder=0); ax.bar(range(1, 25), v, width=.6, color=[ACENTO if k in (12, 24) else OSCURO for k in range(1, 25)], zorder=2)
    ax.axhline(0, color=SUAVE, lw=.5); ax.set_title(t); ax.set_xlabel("Rezago (meses)"); eje_coma(ax, "y", 1)
fig.tight_layout(w_pad=1); guardar(fig, "fig_acf_ejemplo")
S["acf_mango"] = dict(r1=float(a_[0]), r12=float(a_[11]), r6=float(a_[5]))
(RES / "eda2.json").write_text(json.dumps(S, indent=1, ensure_ascii=False, default=float))
print(json.dumps(S, ensure_ascii=False, default=float)[:3000])
