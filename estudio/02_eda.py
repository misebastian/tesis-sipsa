"""Paso 2. Análisis exploratorio: cobertura, faltantes, distribución, estacionalidad, atípicos, abastecimiento,
dependencia temporal, ONI y asociación univariada de cada variable con los dos objetivos (solo entrenamiento)."""
import json, warnings
import numpy as np, pandas as pd
from comun import *
warnings.filterwarnings("ignore")
R = RAIZ
NUMERICAS = HIST + EST + ABAST + RED + ONI
GRUPOS_EDA = {k: v for k, v in GRUPOS.items() if k != "CARNES"}

# ===================== Parte A: panorama general =====================

P = pd.read_parquet(DATOS / "panel.parquet")
B = pd.read_parquet(DATOS / "base_unida_mensual.parquet")
S = {}
S["registros_base"] = int(len(B)); S["series_panel"] = int(P[["mercado", "alimento"]].drop_duplicates().shape[0])
S["filas_panel"] = int(len(P)); S["filas_muestra"] = P.groupby("muestra").size().to_dict()
S["centrales"] = int(P.mercado.nunique()); S["ciudades"] = int(P.ciudad.nunique()); S["alimentos"] = int(P.alimento.nunique())
S["tasa_alza"] = P.groupby("muestra").alza.mean().round(4).to_dict()
S["sd_cambio"] = float(P.y.std()); S["mediana_abs"] = float(P.y.abs().median())
S["kurtosis"] = float(P.y.kurt()); S["asimetria"] = float(P.y.skew())

# 1. faltantes: % de meses con precio por grupo y año (series en $/kg del panel)
ser = P[["mercado", "alimento", "grupo"]].drop_duplicates()
meses = pd.date_range("2018-01-01", B.mes.max(), freq="MS")
Wp = B[B.unidad == "$/kg"].pivot_table(index=["mercado", "alimento"], columns="mes", values="precio").reindex(columns=meses)
Wp = Wp.reindex(pd.MultiIndex.from_frame(ser[["mercado", "alimento"]]))
L = Wp.notna().stack().rename("tiene").reset_index(); L.columns = ["mercado", "alimento", "mes", "tiene"]
L = L.merge(ser, on=["mercado", "alimento"]); L["ano"] = L.mes.dt.year
cob = L.groupby([L.grupo.map(GRUPOS), "ano"]).tiene.mean().unstack()
b = L.rename(columns={"tiene": "precio"}).assign(precio=lambda d: d.precio.where(d.precio))
fig, ax = plt.subplots(figsize=(7.2, 3.2))
im = ax.imshow(cob.values, cmap="Greens", vmin=0.5, vmax=1, aspect="auto")
ax.set_xticks(range(cob.shape[1]), cob.columns); ax.set_yticks(range(cob.shape[0]), cob.index); ax.grid(False)
for i in range(cob.shape[0]):
    for j in range(cob.shape[1]):
        ax.text(j, i, f"{cob.values[i, j] * 100:.0f}", ha="center", va="center", fontsize=8, color="white" if cob.values[i, j] > .8 else TINTA)
ax.set_title("Porcentaje de meses con precio registrado, por grupo y año")
guardar(fig, "eda_faltantes"); S["cobertura_ano"] = cob.mean().round(3).to_dict()
S["faltante_total"] = float(1 - b.precio.notna().mean())

# 2. distribución del cambio mensual por grupo
orden = P.groupby("grupo").y.std().sort_values(ascending=False).index
fig, ax = plt.subplots(figsize=(7.2, 3.4))
d = [P.loc[P.grupo == g, "y"].clip(-.6, .6) * 100 for g in orden]
bp = ax.boxplot(d, vert=False, widths=.55, showfliers=False, patch_artist=True, medianprops=dict(color=TINTA))
for p_, c in zip(bp["boxes"], PALETA): p_.set_facecolor(c); p_.set_alpha(.35); p_.set_edgecolor(c)
ax.set_yticks(range(1, len(orden) + 1), [GRUPOS[g] for g in orden]); ax.invert_yaxis()
ax.axvline(15, color=NARANJA, ls="--", lw=1); ax.text(15.5, .6, "alza fuerte (15 %)", color=NARANJA, fontsize=8)
ax.set_xlabel("Cambio del precio de un mes al siguiente (%)"); ax.set_title("Distribución del cambio mensual del precio por grupo")
guardar(fig, "eda_distribucion")
S["por_grupo"] = P.groupby("grupo").agg(sd=("y", "std"), alza=("alza", "mean"), n=("y", "size")).round(4).rename(index=GRUPOS).to_dict("index")

# 3. ciudades
cd = P.groupby("ciudad").agg(alza=("alza", "mean"), n=("y", "size")).sort_values("alza")
fig, ax = plt.subplots(figsize=(7.2, 4.6))
ax.barh(cd.index, cd.alza * 100, color=VERDE, alpha=.8)
for i, v in enumerate(cd.alza * 100): ax.text(v + .2, i, f"{v:.0f}", va="center", fontsize=7.5, color=SUAVE)
ax.set_xlabel("Meses con alza mayor al 15 % (%)"); ax.set_title("Frecuencia de alzas fuertes por ciudad"); ax.grid(axis="y", visible=False)
guardar(fig, "eda_ciudades"); S["ciudades_alza"] = cd.alza.round(3).to_dict()

# 4. estacionalidad: % de alzas por grupo y mes objetivo
P["m"] = P.mes_obj.dt.month
est = P.groupby([P.grupo.map(GRUPOS), "m"]).alza.mean().unstack().loc[[GRUPOS[g] for g in orden]]
fig, ax = plt.subplots(figsize=(7.2, 3.2))
ax.imshow(est.values, cmap="Oranges", vmin=0, vmax=.35, aspect="auto"); ax.grid(False)
ax.set_xticks(range(12), ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]); ax.set_yticks(range(len(est)), est.index)
for i in range(est.shape[0]):
    for j in range(12):
        ax.text(j, i, f"{est.values[i, j] * 100:.0f}", ha="center", va="center", fontsize=7.5, color="white" if est.values[i, j] > .25 else TINTA)
ax.set_title("Porcentaje de alzas fuertes según el mes, por grupo")
guardar(fig, "eda_estacionalidad"); S["mes_alza"] = P.groupby("m").alza.mean().round(3).to_dict()

# 5. precio y abastecimiento
q = P.dropna(subset=["cambio_ton_1m"]).copy()
q["dec"] = pd.qcut(q.cambio_ton_1m, 10, labels=False, duplicates="drop")
q["per"] = q.perecibilidad.map({2: "Perecederos", 1: "Semiperecederos", 0: "Almacenables"})
# relación contemporánea: cambio del precio en t vs cambio de toneladas en t
r = q.groupby(["per", "dec"]).agg(x=("cambio_ton_1m", "median"), yc=("cambio_1m", "mean"), yn=("y", "mean")).reset_index()
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
for per, c in zip(["Perecederos", "Semiperecederos", "Almacenables"], [NARANJA, OCRE, VERDE]):
    t = r[r.per == per]
    axs[0].plot(t.x * 100, t.yc * 100, "o-", color=c, ms=3.5, label=per)
    axs[1].plot(t.x * 100, t.yn * 100, "o-", color=c, ms=3.5, label=per)
axs[0].set_title("Mismo mes"); axs[1].set_title("Mes siguiente")
axs[0].set_xlabel("Cambio de toneladas (%)"); axs[1].set_xlabel("Cambio de toneladas (%)"); axs[0].set_ylabel("Cambio medio del precio (%)")
axs[0].legend(fontsize=7.5); fig.suptitle("Precio y abastecimiento por decil del cambio de toneladas", x=0.01, ha="left", fontweight="bold", fontsize=10.5)
guardar(fig, "eda_precio_abasto")
S["corr_precio_ton_mismo"] = float(q[["cambio_1m", "cambio_ton_1m"]].corr(method="spearman").iloc[0, 1])
S["corr_precio_ton_sig"] = float(q[["y", "cambio_ton_1m"]].corr(method="spearman").iloc[0, 1])

# 6. autocorrelación del cambio mensual
W = B[B.unidad == "$/kg"].merge(P[["mercado", "alimento"]].drop_duplicates()).pivot_table(index=["mercado", "alimento"], columns="mes", values="precio")
Rm = np.log(W).diff(axis=1)
ac = {k: [] for k in range(1, 13)}
for _, s in Rm.iterrows():
    s = s.dropna()
    if len(s) >= 48:
        for k in ac: ac[k].append(s.autocorr(k))
acm = pd.DataFrame({k: [np.nanmedian(v), np.nanpercentile(v, 25), np.nanpercentile(v, 75)] for k, v in ac.items()}, index=["med", "p25", "p75"]).T
fig, ax = plt.subplots(figsize=(7.2, 2.8))
ax.bar(acm.index, acm.med, color=VERDE, alpha=.8, width=.6)
ax.vlines(acm.index, acm.p25, acm.p75, color=TINTA, lw=1)
ax.axhline(0, color=SUAVE, lw=.8); ax.set_xticks(range(1, 13)); ax.set_xlabel("Rezago (meses)"); ax.set_ylabel("Autocorrelación")
ax.set_title("Autocorrelación del cambio mensual del precio (mediana y rango intercuartil entre series)")
guardar(fig, "eda_autocorrelacion"); S["acf"] = acm.med.round(3).to_dict()

# 7. ONI y alzas en perecederos
o = P[P.perecibilidad == 2].groupby("mes_obj").agg(alza=("alza", "mean"), oni=("oni", "first"))
fig, ax = plt.subplots(figsize=(7.2, 2.9))
ax.plot(o.index, o.alza.rolling(3, center=True).mean() * 100, color=NARANJA, lw=1.6, label="Alzas fuertes en perecederos (%)")
ax.set_ylabel("Alzas fuertes (%)", color=NARANJA)
a2 = ax.twinx(); a2.fill_between(o.index, o.oni, 0, where=o.oni > 0, color="#d9534f", alpha=.18); a2.fill_between(o.index, o.oni, 0, where=o.oni < 0, color=AZUL, alpha=.18)
a2.plot(o.index, o.oni, color=SUAVE, lw=1); a2.set_ylabel("ONI (°C)"); a2.grid(False); a2.spines["right"].set_visible(True)
ax.set_title("Alzas fuertes en perecederos e Índice Oceánico de El Niño (rojo: El Niño, azul: La Niña)")
guardar(fig, "eda_oni")
S["corr_oni_alza"] = float(o[["alza", "oni"]].corr().iloc[0, 1])

# 8. correlación entre variables
C = P[NUMERICAS].corr(method="spearman")
fig, ax = plt.subplots(figsize=(7.4, 6.4))
im = ax.imshow(C.values, cmap="RdBu_r", vmin=-1, vmax=1); ax.grid(False)
ax.set_xticks(range(len(C)), C.columns, rotation=90, fontsize=6.5); ax.set_yticks(range(len(C)), C.columns, fontsize=6.5)
fig.colorbar(im, ax=ax, shrink=.7); ax.set_title("Correlación de Spearman entre variables numéricas")
guardar(fig, "eda_correlacion")
alta = [(a, b_, round(C.loc[a, b_], 2)) for i, a in enumerate(C) for b_ in C.columns[i + 1:] if abs(C.loc[a, b_]) > .8]
S["pares_alta_corr"] = alta

# 9. extremos (cambio > 50 % y |z robusto| > 5 dentro de la serie)
med = P.groupby(["mercado", "alimento"]).y.transform("median")
mad = P.groupby(["mercado", "alimento"]).y.transform(lambda s: (s - s.median()).abs().median()) * 1.4826
z = (P.y - med) / mad.replace(0, np.nan)
ext = (z.abs() > 5) & (P.y.abs() > np.log(1.5))
S["extremos"] = int(ext.sum()); S["extremos_pct"] = float(ext.mean())
S["extremos_grupo"] = P[ext].grupo.map(GRUPOS).value_counts().to_dict()
json.dump(S, open(RES / "eda_general.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: v for k, v in S.items() if k not in ("ciudades_alza",)}, ensure_ascii=False, default=float)[:3000])

# ===================== Parte B: calidad, variabilidad y asociación =====================

S = {}
B = pd.read_parquet(DATOS / "base_unida_mensual.parquet")
P = pd.read_parquet(DATOS / "panel.parquet")
GR = GRUPOS
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# 1. composición de la base: registros con precio y solo con abastecimiento
B["tipo"] = np.where(B.precio.isna(), "Solo abastecimiento", np.where((B.unidad == "$/kg").fillna(False).astype(bool), "Precio en $/kg", "Precio en otra unidad"))
c = B.groupby([B.grupo.map(GR), "tipo"]).size().unstack(fill_value=0)
c = c.loc[c.sum(1).sort_values().index]
fig, ax = plt.subplots(figsize=(7.2, 3.2)); left = np.zeros(len(c))
for k, col in zip(["Precio en $/kg", "Precio en otra unidad", "Solo abastecimiento"], [VERDE, OCRE, GRIS]):
    ax.barh(c.index, c[k] / 1000, left=left, color=col, alpha=.85, label=k); left += c[k].values / 1000
ax.set_xlabel("Registros producto-central-mes (miles)"); ax.legend(fontsize=7.5, loc="lower right"); ax.grid(axis="y", visible=False)
ax.set_title("Composición de la base mensual unida (2018-2026)")
guardar(fig, "eda_composicion")
S["composicion"] = B.tipo.value_counts().to_dict(); S["registros"] = len(B); S["mercados_base"] = int(B.mercado.nunique()); S["alimentos_base"] = int(B.alimento.nunique())

# 2. cobertura por central y año (series del panel)
ser = P[["mercado", "alimento"]].drop_duplicates()
meses = pd.date_range("2018-01-01", B.mes.max(), freq="MS")
Wp = B[B.unidad == "$/kg"].pivot_table(index=["mercado", "alimento"], columns="mes", values="precio").reindex(columns=meses).reindex(pd.MultiIndex.from_frame(ser))
L = Wp.notna().stack().rename("tiene").reset_index(); L.columns = ["mercado", "alimento", "mes", "tiene"]
cv = L.groupby(["mercado", L.mes.dt.year]).tiene.mean().unstack()
ns = ser.groupby("mercado").size()
cv = cv.loc[cv.mean(1).sort_values().index]
etiq = [f"{m.replace(chr(34), '')[:38]} ({ns[m]})" for m in cv.index]
fig, ax = plt.subplots(figsize=(7.4, 7.0))
ax.imshow(cv.values, cmap="Greens", vmin=.4, vmax=1, aspect="auto"); ax.grid(False)
ax.set_xticks(range(cv.shape[1]), cv.columns); ax.set_yticks(range(len(cv)), etiq, fontsize=6.8)
for i in range(cv.shape[0]):
    for j in range(cv.shape[1]):
        v = cv.values[i, j]; ax.text(j, i, "" if np.isnan(v) else f"{v * 100:.0f}", ha="center", va="center", fontsize=6, color="white" if v > .8 else TINTA)
ax.set_title("Porcentaje de meses con precio por central y año\n(entre paréntesis, número de series en el panel)")
guardar(fig, "eda_cobertura_central")
S["cobertura_central"] = cv.mean(1).round(3).to_dict(); S["series_central"] = ns.to_dict()

# 3. huecos: longitud de rachas de meses sin precio dentro de cada serie
rachas = []
for _, s in Wp.iterrows():
    v = s.notna().values; ini = np.argmax(v); fin = len(v) - np.argmax(v[::-1])
    v = v[ini:fin]; k = 0
    for x in v:
        if not x: k += 1
        elif k: rachas.append(k); k = 0
r = pd.Series(rachas)
S["rachas"] = dict(n=len(r), hasta2=float((r <= 2).mean()), media=float(r.mean()), mas6=float((r > 6).mean()))
fig, ax = plt.subplots(figsize=(7.2, 2.7))
vc = r.clip(upper=12).value_counts().sort_index()
ax.bar(vc.index, vc.values / len(r) * 100, color=[VERDE if i <= 2 else GRIS for i in vc.index], alpha=.85)
ax.set_xticks(range(1, 13), [str(i) for i in range(1, 12)] + ["12+"]); ax.set_xlabel("Meses consecutivos sin precio"); ax.set_ylabel("% de los huecos")
ax.set_title(f"Duración de los huecos dentro de las series (verde: se rellenan, {S['rachas']['hasta2'] * 100:.0f} % del total)")
guardar(fig, "eda_huecos")

# 4. distribución en el tiempo: observaciones y tasa de alzas por mes objetivo
t = P.groupby("mes_obj").agg(n=("y", "size"), alza=("alza", "mean"), sd=("y", "std"))
fig, axs = plt.subplots(2, 1, figsize=(7.2, 4.2), sharex=True)
for a in axs:
    a.axvspan(pd.Timestamp("2024-01-01"), pd.Timestamp("2024-12-31"), color=OCRE, alpha=.12); a.axvspan(pd.Timestamp("2025-01-01"), t.index.max(), color=NARANJA, alpha=.10)
axs[0].bar(t.index, t.n, width=25, color=VERDE, alpha=.8); axs[0].set_ylabel("Observaciones")
axs[0].set_title("Observaciones y alzas fuertes por mes pronosticado (ocre: validación; naranja: prueba)")
axs[1].plot(t.index, t.alza * 100, color=NARANJA, lw=1.4); axs[1].plot(t.index, t.alza.rolling(12, center=True).mean() * 100, color=TINTA, lw=1, ls="--")
axs[1].set_ylabel("Alzas > 15 % (%)")
guardar(fig, "eda_tiempo")
S["alza_ano"] = P.groupby(P.mes_obj.dt.year).alza.mean().round(4).to_dict(); S["n_ano"] = P.groupby(P.mes_obj.dt.year).size().to_dict()

# 5. variabilidad por producto: los 25 productos con más observaciones
pa = P.groupby("alimento").agg(sd=("y", "std"), alza=("alza", "mean"), n=("y", "size"), centrales=("mercado", "nunique"), g=("grupo", "first"))
S["productos_n"] = int(len(pa)); S["productos_centrales_mediana"] = float(pa.centrales.median())
top = pa.sort_values("sd", ascending=False)
fig, axs = plt.subplots(1, 2, figsize=(7.4, 5.0), gridspec_kw=dict(width_ratios=[1, 1]))
for a, d, tit in ((axs[0], top.head(15), "Los 15 más volátiles"), (axs[1], top.tail(15), "Los 15 más estables")):
    a.barh(d.index[::-1], d.sd[::-1] * 100, color=[NARANJA if p_ in ("VERDURAS Y HORTALIZAS", "FRUTAS", "TUBERCULOS, RAICES Y PLATANOS") else VERDE for p_ in d.g[::-1]], alpha=.85)
    a.set_title(tit); a.set_xlabel("Desviación del cambio mensual (p. p.)"); a.tick_params(axis="y", labelsize=7); a.grid(axis="y", visible=False)
fig.suptitle("Variabilidad del cambio mensual por producto (naranja: perecederos)", x=.01, ha="left", fontweight="bold", fontsize=10.5)
fig.tight_layout(); guardar(fig, "eda_productos")
S["prod_mas_volatiles"] = top.head(5).sd.round(3).to_dict(); S["prod_mas_estables"] = top.tail(5).sd.round(3).to_dict()

# 6. variabilidad por central: mismo producto, distinta central (efecto central controlando producto)
P["y_rel"] = P.y.abs() - P.groupby(["alimento", "mes"]).y.transform(lambda s: s.abs().mean())
ce = P.groupby("mercado").agg(rel=("y_rel", "mean"), sd=("y", "std"), n=("y", "size")).sort_values("rel")
fig, ax = plt.subplots(figsize=(7.2, 5.6))
ax.barh([m.replace('"', "")[:40] for m in ce.index], ce.rel * 100, color=[NARANJA if v > 0 else VERDE for v in ce.rel], alpha=.85)
ax.axvline(0, color=SUAVE, lw=.8); ax.tick_params(axis="y", labelsize=6.8); ax.grid(axis="y", visible=False)
ax.set_xlabel("Cambio absoluto frente al de las demás centrales, mismo producto y mes (p. p.)")
ax.set_title("Qué tanto más (o menos) se mueven los precios en cada central")
guardar(fig, "eda_centrales"); S["central_rel"] = ce.rel.round(4).to_dict()

# 7. abastecimiento: variabilidad de toneladas y su relación con la del precio por serie
q = P.groupby(["mercado", "alimento"]).agg(vt=("cambio_ton_1m", "std"), vp=("y", "std"), g=("grupo", "first"), ton=("participacion_central", "mean")).dropna()
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.1))
for gname, col in zip(["VERDURAS Y HORTALIZAS", "FRUTAS", "TUBERCULOS, RAICES Y PLATANOS", "GRANOS Y CEREALES", "PROCESADOS"], [NARANJA, OCRE, MORADO, AZUL, VERDE]):
    d = q[q.g == gname]; axs[0].scatter(d.vt.clip(upper=2) * 100, d.vp * 100, s=6, alpha=.5, color=col, label=GRUPOS[gname])
axs[0].set_xlabel("Desviación del cambio de toneladas (p. p.)"); axs[0].set_ylabel("Desviación del cambio de precio (p. p.)"); axs[0].legend(fontsize=6.3, markerscale=2)
axs[0].set_title("Volatilidad por serie")
cvg = P.groupby(P.grupo.map(GRUPOS)).cambio_ton_1m.apply(lambda s: s.abs().median()).sort_values()
axs[1].barh(cvg.index, cvg * 100, color=AZUL, alpha=.85); axs[1].set_xlabel("Mediana del cambio absoluto de toneladas (p. p.)"); axs[1].set_title("Variación típica del abastecimiento")
axs[1].tick_params(axis="y", labelsize=7.5); axs[1].grid(axis="y", visible=False)
fig.tight_layout(); guardar(fig, "eda_abastecimiento")
S["corr_vol_ton_precio"] = float(q[["vt", "vp"]].corr(method="spearman").iloc[0, 1]); S["ton_mediana_cambio"] = cvg.round(3).to_dict()

# 8. atípicos: cambios de más del 50 % (en log, |y| > ln 1,5) y saltos extremos de nivel
P["extremo"] = P.y.abs() > np.log(1.5); P["muy_extremo"] = P.y.abs() > np.log(3)
ex = P.groupby([P.grupo.map(GRUPOS)]).agg(ext=("extremo", "mean"), muy=("muy_extremo", "sum"), n=("y", "size")).sort_values("ext")
S["extremos"] = dict(total=int(P.extremo.sum()), pct=float(P.extremo.mean()), muy=int(P.muy_extremo.sum()))
S["extremos_grupo"] = ex.round(4).to_dict("index")
mx = P.loc[P.y.abs().nlargest(8).index, ["mercado", "alimento", "mes", "y"]]; mx["cambio_pct"] = (np.exp(mx.y) - 1) * 100
S["mayores_saltos"] = mx.assign(mes=mx.mes.dt.strftime("%Y-%m")).round(2).to_dict("records")
fig, ax = plt.subplots(figsize=(7.2, 2.7))
ax.barh(ex.index, ex.ext * 100, color=NARANJA, alpha=.85); ax.grid(axis="y", visible=False)
for i, (v, m_) in enumerate(zip(ex.ext * 100, ex.muy)): ax.text(v + .1, i, f"{v:.1f} %" + (f" · {m_} > ×3" if m_ else ""), va="center", fontsize=7.5, color=SUAVE)
ax.set_xlabel("Meses con cambio mayor al 50 % en valor absoluto (%)"); ax.set_title("Cambios extremos por grupo")
guardar(fig, "eda_atipicos")

# 9. asociación univariada con los objetivos (solo entrenamiento)
tr = P[P.muestra == "entrenamiento"]
VARS = [v for g in BLOQUES_BASE.values() for v in g if v not in ("grupo_c", "ciudad_c", "mercado_c", "alimento_c")] + sum(BLOQUES_NUEVOS.values(), [])
NOM = {**NOMBRES, "desv_ma3": "Desviación de la media móvil 3m", "desv_ma6": "Desviación de la media móvil 6m", "cambio_mismo_mes_ano_ant": "Cambio del mismo mes el año anterior",
       "cambio_nacional_mismo_mes_ano_ant": "Cambio nacional, mismo mes año anterior", "cambio_nacional_2m": "Cambio nacional, 2 meses", "cambio_nacional_12m": "Cambio nacional, 12 meses",
       "brecha_nacional_cambio": "Cambio de la brecha nacional", "cambio_grupo_central": "Cambio del grupo en la central", "alzas_grupo_central": "Alzas del grupo en la central",
       "cambio_ton_nacional_1m": "Cambio de toneladas nacional", "ton_nacional_rel_12m": "Toneladas nacionales frente al año", "participacion_central": "Participación de la central",
       "meses_obs_12m": "Meses con precio en el año", "dias_registro_rel": "Días con registro frente al año"}
A = []
for v in VARS:
    x = tr[v]; ok = x.notna()
    rho = x[ok].corr(tr.y[ok], method="spearman")
    try:
        qq = pd.qcut(x[ok].rank(method="first"), 5, labels=False); al = tr.alza[ok].groupby(qq).mean(); lift = al.iloc[-1] - al.iloc[0]
    except Exception: lift = np.nan
    A.append(dict(var=v, nombre=NOM[v], rho=rho, dif_alza=lift, faltante=float(1 - ok.mean())))
A = pd.DataFrame(A); A.to_csv(RES / "asociacion.csv", index=False)
A["abs"] = A.rho.abs(); a = A.sort_values("abs").tail(22)
fig, axs = plt.subplots(1, 2, figsize=(7.4, 5.4), sharey=True)
axs[0].barh(a.nombre, a.rho, color=[NARANJA if v > 0 else AZUL for v in a.rho], alpha=.85); axs[0].axvline(0, color=SUAVE, lw=.8)
axs[0].set_xlabel("Correlación de Spearman con el cambio\ndel mes siguiente"); axs[0].tick_params(axis="y", labelsize=7); axs[0].set_title("Regresión")
axs[1].barh(a.nombre, a.dif_alza * 100, color=[NARANJA if v > 0 else AZUL for v in a.dif_alza], alpha=.85); axs[1].axvline(0, color=SUAVE, lw=.8)
axs[1].set_xlabel("Diferencia en la tasa de alzas entre el\nquintil más alto y el más bajo (p. p.)"); axs[1].set_title("Clasificación")
for x_ in axs: x_.grid(axis="y", visible=False)
fig.suptitle("Asociación de cada variable con los objetivos (entrenamiento, 22 más fuertes)", x=.01, ha="left", fontweight="bold", fontsize=10.5)
fig.tight_layout(); guardar(fig, "eda_asociacion")
json.dump(S, open(RES / "eda_calidad.json", "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: v for k, v in S.items() if k not in ("cobertura_central", "series_central", "central_rel")}, ensure_ascii=False, default=str)[:4000])

# ===================== Parte C: nivel de precios y alcance de productos =====================
Bk = B[(B.unidad == "$/kg") & B.precio.notna()].merge(P[["mercado", "alimento"]].drop_duplicates())
orden_g = Bk.groupby("grupo").precio.median().sort_values().index
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.2), gridspec_kw=dict(width_ratios=[1.4, 1]))
axs[0].boxplot([Bk.loc[Bk.grupo == g, "precio"] for g in orden_g], vert=False, showfliers=False, widths=.55, patch_artist=True,
               boxprops=dict(facecolor="#dfeae2", edgecolor=VERDE), medianprops=dict(color=TINTA))
axs[0].set_xscale("log"); axs[0].set_yticks(range(1, len(orden_g) + 1), [GRUPOS[g] for g in orden_g], fontsize=7.5)
axs[0].set_xlabel("Precio mayorista ($/kg, escala logarítmica)"); axs[0].set_title("Nivel de precios por grupo"); axs[0].grid(axis="y", visible=False)
cent = P.groupby("alimento").mercado.nunique()
axs[1].hist(cent, bins=range(1, cent.max() + 2), color=AZUL, alpha=.8); axs[1].set_xlabel("Centrales en que se cotiza el producto"); axs[1].set_ylabel("Productos")
axs[1].set_title("Alcance de cada producto")
fig.tight_layout(); guardar(fig, "eda_precios")
S2 = json.load(open(RES / "eda_calidad.json"))
S2["precio_mediana_grupo"] = Bk.groupby(Bk.grupo.map(GRUPOS)).precio.median().round(0).to_dict()
S2["precio_rango"] = [float(Bk.precio.quantile(.01)), float(Bk.precio.quantile(.99))]
S2["centrales_por_producto"] = dict(mediana=float(cent.median()), max=int(cent.max()), uno=int((cent == 1).sum()))
json.dump(S2, open(RES / "eda_calidad.json", "w"), ensure_ascii=False, indent=1, default=str)

# ---------- Parte D: búsqueda de precios aislados y contraste con las demás centrales ----------
# Regla: |ln p_t - mediana móvil centrada de 7 meses| > ln 4. Para cada caso se mira el cambio del mismo producto en las
# demás centrales ese mes: un pico acompañado por el mercado es verosímil; uno aislado sugiere error de registro.
bk = B[B.unidad == "$/kg"]
Wl = np.log(bk.pivot_table(index=["mercado", "alimento"], columns="mes", values="precio"))
med = Wl.T.rolling(7, center=True, min_periods=3).median().T
Dv = (Wl - med); cand = Dv.stack(); cand = cand[cand.abs() > np.log(4)]
Rl = Wl.diff(axis=1); picos = []
for (m, a, t), v in cand.items():
    otras = Rl.xs(a, level="alimento")[t].drop(m, errors="ignore").dropna()
    picos.append(dict(mercado=m, alimento=a, mes=str(t.date())[:7], razon=float(np.exp(v)), n_otras=int(len(otras)),
                      cambio_propio=float(Rl.loc[(m, a), t]) if pd.notna(Rl.loc[(m, a), t]) else None,
                      mediana_otras=float(otras.median()) if len(otras) else None,
                      prop_mismo_signo=float((np.sign(otras) == np.sign(v)).mean()) if len(otras) else None))
S2["picos"] = picos
json.dump(S2, open(RES / "eda_calidad.json", "w"), ensure_ascii=False, indent=1, default=str)
print("picos:", picos)
