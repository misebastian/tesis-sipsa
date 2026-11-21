"""Paso 15. Análisis pedidos en la revisión del director (noviembre de 2026). No cambia ninguna decisión del estudio:
usa las predicciones ya guardadas y, cuando hace falta reestimar, los hiperparámetros ya elegidos.
 1. Muestras de validación por año y error del SARIMA por año (misma definición que la tabla principal).
 2. Métricas complementarias de regresión (AvgRelMAE, reducción promedio por grupo) y de clasificación
    (Brier, log-loss, Brier skill score, pendiente e intercepto de calibración, ECE).
 3. Intervalos: puntaje de intervalo, pinball, MAE de la mediana cuantílica y cobertura por decil de volatilidad y por grupo.
 4. Efecto de promediar precios (Working, 1960): referencia autorregresiva 0,25 y correlación parcial de la señal de las demás centrales.
 5. Rezago de publicación: pronóstico del cambio entre t+1 y t+2 con la información de t.
 6. Modelos lineales y red neuronal con otra codificación y con las 52 candidatas; regresión cuantílica con interacciones por grupo.
 7. Promedio de los tres modelos de potenciación.
 8. Cambio de distribución entre desarrollo y prueba (Kolmogorov-Smirnov y validación adversaria).
 9. KPSS frente a ADF; episodios de El Niño; series con elección de variedad; bootstrap estacionario.
Escribe resultados/revision.json y resultados/revision_*.csv."""
import time, warnings, json
import numpy as np, pandas as pd
from scipy import stats
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss, log_loss
from comun import *
from modelos import REGRESION, CLASIFICACION, limpiar
warnings.filterwarnings("ignore")
T0 = time.time(); log = lambda *a: print(f"[{time.time() - T0:5.0f}s]", *a, flush=True)
P = cargar_panel(); V = variables_finales(); GRP = sorted(P.grupo.unique())
RS, CS = leer_json("reg_seleccion.json"), leer_json("clf_seleccion.json"); ER, EC = RS["elegido"], CS["elegido"]
OR = pd.read_parquet(RES / "reg_predicciones_prueba.parquet"); OC = pd.read_parquet(RES / "clf_predicciones_prueba.parquet")
y, z, mes = OR.y.values, OR.alza.values, OR.mes_obj.values
S = {}; BR = 2000
PER = ["FRUTAS", "VERDURAS Y HORTALIZAS", "TUBERCULOS, RAICES Y PLATANOS"]
logit = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))

# ---------- 1. muestras por año y SARIMA por año ----------
ent = P[P.muestra != "prueba"]; te = P[P.muestra == "prueba"]
anos = []
for x, y_ in CORTES_CV:
    b = P[(P.mes_obj > x) & (P.mes_obj <= y_)]
    anos.append(dict(ano=pd.Timestamp(y_).year, n=int(len(b)), alza=float(b.alza.mean()), n_ajuste=int((P.mes_obj <= x).sum())))
S["muestras"] = dict(validacion=anos, desarrollo=dict(n=int(len(ent)), alza=float(ent.alza.mean())), prueba=dict(n=int(len(te)), alza=float(te.alza.mean())))
SA = pd.read_parquet(RES / "sarima.parquet")
sar = []
for k, (x, y_) in enumerate(CORTES_CV):
    b = P[(P.mes_obj > x) & (P.mes_obj <= y_)]
    s = SA[SA.corte == f"cv{k}"].set_index(["mercado", "alimento", "mes_obj"]).pred
    ps = s.reindex(pd.MultiIndex.from_frame(b[["mercado", "alimento", "mes_obj"]])).values
    sar.append(dict(ano=pd.Timestamp(y_).year, mae_rw=float(np.abs(b.y).mean() * 100), mae_sarima=float(np.abs(b.y - np.nan_to_num(ps)).mean() * 100),
                    disponible=float(np.mean(~np.isnan(ps))), mae_rw_disp=float(np.abs(b.y[~np.isnan(ps)]).mean() * 100),
                    mae_sarima_disp=float(np.abs(b.y.values[~np.isnan(ps)] - ps[~np.isnan(ps)]).mean() * 100)))
S["sarima_ano"] = sar; log("sarima por año", sar)

# ---------- 2. métricas complementarias ----------
MR = ["Paseo aleatorio", "AR estacional", "SARIMA"] + RS["modelos"]
ser = OR.groupby(["mercado", "alimento"])
mae_s = pd.DataFrame({m: ser.apply(lambda g: np.abs(g.y - g[m]).mean()) for m in MR})
ok = mae_s["Paseo aleatorio"] > 0
reg_extra = {}
for m in MR:
    rel = (mae_s.loc[ok, m] / mae_s.loc[ok, "Paseo aleatorio"])
    g = OR.assign(e=np.abs(y - OR[m]), e0=np.abs(y)).groupby("grupo")[["e", "e0"]].mean()
    reg_extra[m] = dict(avgrelmae=float(np.exp(np.log(rel.clip(lower=1e-9)).mean())), mediana_rel=float(rel.median()),
                        reduccion_media_grupos=float((1 - g.e / g.e0).mean()), razon_medias_grupos=float(1 - g.e.mean() / g.e0.mean()),
                        rmse=float(np.sqrt(np.mean((y - OR[m]) ** 2)) * 100), mae=float(np.mean(np.abs(y - OR[m])) * 100))
S["reg_extra"] = reg_extra; log("AvgRelMAE CatBoost", reg_extra[ER])

MC = ["Frecuencia histórica", "Logística autorregresiva", "SARIMA"] + CS["modelos"]
pf = OC["Frecuencia histórica"].values


def calib(p, zz):
    """Intercepto (con pendiente fija en 1) y pendiente de calibración por máxima verosimilitud (Van Calster et al., 2019)."""
    import statsmodels.api as sm
    lp = logit(p)
    b = sm.GLM(zz, sm.add_constant(lp), family=sm.families.Binomial()).fit().params
    a = sm.GLM(zz, np.ones((len(zz), 1)), family=sm.families.Binomial(), offset=lp).fit().params
    return float(a[0]), float(b[1])


def ece(p, zz, k=10):
    b = pd.qcut(pd.Series(p).rank(method="first"), k, labels=False).values
    return float(sum((b == i).mean() * abs(p[b == i].mean() - zz[b == i].mean()) for i in range(k)))


clf_extra = {}
for m in MC:
    p = OC[m].values
    br, rr = bootstrap_metrica(mes, lambda i: brier_score_loss(z[i], p[i]), B=BR)
    bss, rb = bootstrap_metrica(mes, lambda i: 1 - brier_score_loss(z[i], p[i]) / brier_score_loss(z[i], pf[i]), B=BR)
    ll, rl = bootstrap_metrica(mes, lambda i: log_loss(z[i], np.clip(p[i], 1e-6, 1 - 1e-6)), B=BR)
    a_, b_ = calib(p, z)
    _, rc = bootstrap_metrica(mes, lambda i: calib(p[i], z[i])[1], B=300)
    clf_extra[m] = dict(brier=br, brier_ic=ic(rr), bss=bss, bss_ic=ic(rb), logloss=ll, logloss_ic=ic(rl), intercepto=a_, pendiente=b_, pendiente_ic=ic(rc), ece=ece(p, z))
    log("calibración", m, round(br, 4), round(bss, 3), round(b_, 3))
S["clf_extra"] = clf_extra

# ---------- 3. intervalos ----------
IQ = pd.read_parquet(RES / "intervalos_prueba.parquet")
IQ = IQ.merge(te[["mercado", "alimento", "mes_obj", "vol_12m"]], on=["mercado", "alimento", "mes_obj"], how="left")
yy = IQ.y.values; TAU = [.05, .10, .25, .50, .75, .90, .95]


def iscore(L, U, a):
    return float(np.mean((U - L) + 2 / a * (L - yy) * (yy < L) + 2 / a * (yy - U) * (yy > U)) * 100)


pin = np.mean([np.mean(np.maximum(t * (yy - IQ[f"q{int(t * 100):02d}"]), (t - 1) * (yy - IQ[f"q{int(t * 100):02d}"]))) for t in TAU]) * 100
IQ["dec_vol"] = pd.qcut(IQ.vol_12m.rank(method="first"), 10, labels=False) + 1
IQ["per"] = np.where(IQ.grupo.isin(PER), "Perecederos", "No perecederos")
cob = []
for (lo, hi, nom, a) in (("q10", "q90", "Cuantiles 80", .2), ("lo80", "hi80", "CQR por grupo 80", .2), ("q05", "q95", "Cuantiles 90", .1), ("lo90", "hi90", "CQR por grupo 90", .1)):
    d = (yy >= IQ[lo]) & (yy <= IQ[hi]); w = (IQ[hi] - IQ[lo]) * 100
    for v_, g in IQ.assign(d=d, w=w).groupby("dec_vol"):
        cob.append(dict(intervalo=nom, decil=int(v_), cobertura=float(g.d.mean()), ancho=float(g.w.mean()), vol_media=float(g.vol_12m.mean() * 100)))
    S.setdefault("intervalos", {})[nom] = dict(cobertura=float(d.mean()), ancho=float(w.mean()), puntaje=iscore(IQ[lo].values, IQ[hi].values, a),
                                               por_grupo=IQ.assign(d=d).groupby(IQ.grupo.map(GRUPOS)).d.mean().round(4).to_dict())
pd.DataFrame(cob).to_csv(RES / "revision_cobertura_volatilidad.csv", index=False)
CP = leer_json("complementarios.json")["distribucional"]
S["intervalos_resumen"] = dict(pinball=float(pin), pinball_cv=CP.get("pinball"), mae_mediana=CP["mae_mediana"], cruces=CP["cruces"],
                               mae_mediana_reduccion=float(1 - CP["mae_mediana"] / (np.abs(y).mean() * 100)))
log("intervalos", S["intervalos_resumen"])

# ---------- 4. efecto del promedio mensual (Working, 1960) ----------
r_ = te.cambio_1m.fillna(0).values
for rho in (0.25,):
    e_ar = np.abs(te.y.values - rho * r_)
S["working"] = dict(mae_rw=float(np.abs(te.y).mean() * 100), mae_ar025=float(e_ar.mean() * 100), red_ar025=float(1 - e_ar.mean() / np.abs(te.y).mean()),
                    mae_cat=float(np.abs(y - OR[ER]).mean() * 100))
d_, rr = bootstrap_metrica(mes, lambda i: 1 - np.abs(y[i] - OR[ER].values[i]).mean() / e_ar[i].mean(), B=BR)
S["working"]["red_cat_vs_ar025"] = d_; S["working"]["red_cat_vs_ar025_ic"] = ic(rr)
tr = P[P.muestra == "entrenamiento"].dropna(subset=["cambio_1m", "cambio_nacional_1m"])
res = lambda a, b: a - np.polyval(np.polyfit(b, a, 1), b)
S["working"]["corr_nacional"] = float(np.corrcoef(tr.y, tr.cambio_nacional_1m)[0, 1])
S["working"]["corr_parcial_nacional"] = float(np.corrcoef(res(tr.y.values, tr.cambio_1m.values), res(tr.cambio_nacional_1m.values, tr.cambio_1m.values))[0, 1])
S["working"]["corr_propio"] = float(np.corrcoef(tr.y, tr.cambio_1m)[0, 1])
log("Working", S["working"])

# ---------- 5. horizonte t+2 (rezago de publicación) ----------
Q = P.sort_values(["mercado", "alimento", "mes"]).copy()
sig = Q[["mercado", "alimento", "mes", "y", "frec_alza_hist", "cambio_estacional_hist", "mes_sin", "mes_cos"]].copy()
sig["mes"] = sig.mes - pd.DateOffset(months=1)
sig = sig.rename(columns={"y": "y2", "frec_alza_hist": "frec2", "cambio_estacional_hist": "cest2", "mes_sin": "sin2", "mes_cos": "cos2"})
Q = Q.merge(sig, on=["mercado", "alimento", "mes"], how="inner").dropna(subset=["y2"])
Q["obj2"] = Q.mes + pd.DateOffset(months=2); Q["alza2"] = (Q.y2 > UMBRAL).astype(int)
V2 = [v for v in V if v not in ("frec_alza_hist", "cambio_estacional_hist", "mes_sin", "mes_cos")] + ["frec2", "cest2", "sin2", "cos2"]
a2 = Q[Q.obj2 <= "2024-12-01"]; b2 = Q[(Q.obj2 >= "2025-01-01") & (Q.obj2 <= te.mes_obj.max())]
fr = REGRESION[ER][1](RS["mejores"][ER]["params"]).fit(a2[V2].values.astype(np.float32), a2.y2.values)
pr2 = fr.predict(b2[V2].values.astype(np.float32))
fc = CLASIFICACION[EC][1](CS["mejores"][EC]["params"], 1.0).fit(a2[V2].fillna(-999).values.astype(np.float32), a2.alza2.values)
pc2 = fc.predict_proba(b2[V2].fillna(-999).values.astype(np.float32))[:, 1]
m2 = b2.obj2.values; y2 = b2.y2.values; z2 = b2.alza2.values; f2 = b2.frec2.fillna(a2.alza2.mean()).values
red2, rr2 = bootstrap_metrica(m2, lambda i: 1 - np.abs(y2[i] - pr2[i]).mean() / np.abs(y2[i]).mean(), B=BR)
ap2, ra2 = bootstrap_metrica(m2, lambda i: average_precision_score(z2[i], pc2[i]), B=BR)
dap2, rd2 = bootstrap_metrica(m2, lambda i: average_precision_score(z2[i], pc2[i]) - average_precision_score(z2[i], f2[i]), B=BR)
S["horizonte2"] = dict(n=int(len(b2)), n_ajuste=int(len(a2)), mae_rw=float(np.abs(y2).mean() * 100), mae_cat=float(np.abs(y2 - pr2).mean() * 100), reduccion=red2, reduccion_ic=ic(rr2),
                       tasa=float(z2.mean()), ap=ap2, ap_ic=ic(ra2), ap_frec=float(average_precision_score(z2, f2)), d_ap_frec=dap2, d_ap_frec_ic=ic(rd2),
                       auc=float(roc_auc_score(z2, pc2)), meses=int(len(np.unique(m2))))
g2 = b2.assign(e=np.abs(y2 - pr2), e0=np.abs(y2)).groupby(b2.grupo.map(GRUPOS))[["e", "e0"]].mean()
S["horizonte2"]["por_grupo"] = (1 - g2.e / g2.e0).round(4).to_dict()
log("horizonte 2", S["horizonte2"])

# ---------- 6. modelos lineales y red con otra codificación ----------
NUM52 = [c for c in BASE + sum(BLOQUES_NUEVOS.values(), []) if not c.endswith("_c")]
NUMV = [c for c in V if not c.endswith("_c")]
CATS = ["grupo", "alimento", "mercado", "ciudad"]


def mat_lin(num, a, b, cats=CATS, inter=False):
    mu, sd = a[num].mean(), a[num].std().replace(0, 1)
    def f(d):
        X = ((d[num] - mu) / sd).fillna(0).clip(-6, 6)
        parts = [X] + [pd.get_dummies(d[c].astype(str), prefix=c, dtype=float) for c in cats]
        if inter:
            G = pd.get_dummies(d.grupo, dtype=float)
            parts += [X.mul(G[g], axis=0).add_prefix(f"{g[:4]}_") for g in G.columns]
        return pd.concat(parts, axis=1)
    A, B_ = f(a), f(b); B_ = B_.reindex(columns=A.columns, fill_value=0)
    return A.values.astype(np.float32), B_.values.astype(np.float32)


ent_ = P[P.muestra != "prueba"]; filas = []
def red_reg(p_):
    e = np.abs(y - p_); r, rr = bootstrap_metrica(mes, lambda i: 1 - e[i].mean() / np.abs(y[i]).mean(), B=BR); return r, ic(rr)
configs = [("Indicadores de grupo, 24 variables (original)", NUMV, ["grupo"], False),
           ("Indicadores de grupo, producto, central y ciudad; 24 variables", NUMV, CATS, False),
           ("Indicadores de grupo, producto, central y ciudad; 52 candidatas", NUM52, CATS, False),
           ("Interacciones grupo × variables; 24 variables", NUMV, CATS, True)]
for nom, num, cats, inter in configs:
    Xa, Xb = mat_lin(num, ent_, te, cats, inter)
    for mod in (["Regresión cuantílica", "MLP"] if not inter else ["Regresión cuantílica"]):
        p_ = REGRESION[mod][1](RS["mejores"][mod]["params"]).fit(Xa, ent_.y.values).predict(Xb)
        r, ci = red_reg(p_); fila = dict(config=nom, modelo=mod, tarea="Cambio", mae=float(np.abs(y - p_).mean() * 100), reduccion=r, ic=ci, columnas=int(Xa.shape[1]))
        filas.append(fila); log(fila)
    for mod in (["Regresión logística", "MLP"] if not inter else ["Regresión logística"]):
        p_ = CLASIFICACION[mod][1](CS["mejores"][mod]["params"], 1.0).fit(Xa, ent_.alza.values).predict_proba(Xb)[:, 1]
        ap, ra = bootstrap_metrica(mes, lambda i: average_precision_score(z[i], p_[i]), B=BR)
        fila = dict(config=nom, modelo=mod, tarea="Alzas", ap=ap, ic=ic(ra), columnas=int(Xa.shape[1])); filas.append(fila); log(fila)
pd.DataFrame(filas).to_csv(RES / "revision_lineales.csv", index=False); S["lineales"] = filas

# ---------- 7. promedio de los modelos de potenciación ----------
ENS = ["XGBoost", "LightGBM", "CatBoost"]
pe = OR[ENS].mean(axis=1).values; r, ci = red_reg(pe)
pce = OC[ENS].mean(axis=1).values; ap, ra = bootstrap_metrica(mes, lambda i: average_precision_score(z[i], pce[i]), B=BR)
dce, rd = bootstrap_metrica(mes, lambda i: np.abs(y[i] - OR[ER].values[i]).mean() * 100 - np.abs(y[i] - pe[i]).mean() * 100, B=BR)
S["ensamble"] = dict(mae=float(np.abs(y - pe).mean() * 100), reduccion=r, ic=ci, ap=ap, ap_ic=ic(ra), auc=float(roc_auc_score(z, pce)),
                     d_mae_vs_cat=dce, d_mae_ic=ic(rd), brier=float(brier_score_loss(z, pce)))
log("ensamble", S["ensamble"])

# ---------- 8. cambio de distribución ----------
ks = {}
mm = lambda d: d[d.mes_obj.dt.month <= 9]
for g, d in P.groupby(P.grupo.map(GRUPOS)):
    a_ = mm(d[d.muestra != "prueba"]).y; b_ = mm(d[d.muestra == "prueba"]).y
    if len(b_) > 30:
        k = stats.ks_2samp(a_, b_); ks[g] = dict(ks=float(k.statistic), p=float(k.pvalue), sd_des=float(a_.std() * 100), sd_pru=float(b_.std() * 100), n_pru=int(len(b_)))
S["ks"] = ks
import lightgbm as lgb
from sklearn.model_selection import cross_val_predict, StratifiedKFold
NV = [c for c in NUMV if c not in ("mes_sin", "mes_cos")]
D = pd.concat([mm(ent_).assign(t=0), mm(te).assign(t=1)])
pp = cross_val_predict(lgb.LGBMClassifier(n_estimators=300, learning_rate=.05, num_leaves=31, verbose=-1, random_state=SEMILLA, n_jobs=NUCLEOS),
                       D[NV].values, D.t.values, cv=StratifiedKFold(5, shuffle=True, random_state=SEMILLA), method="predict_proba")[:, 1]
S["adversaria"] = dict(auc=float(roc_auc_score(D.t, pp)), variables=len(NV))
D2 = D[D.mes_obj.dt.year.isin([2023, 2024, 2025, 2026])]
pp2 = cross_val_predict(lgb.LGBMClassifier(n_estimators=300, learning_rate=.05, num_leaves=31, verbose=-1, random_state=SEMILLA, n_jobs=NUCLEOS),
                        D2[NV].values, D2.t.values, cv=StratifiedKFold(5, shuffle=True, random_state=SEMILLA), method="predict_proba")[:, 1]
S["adversaria"]["auc_2023_2024"] = float(roc_auc_score(D2.t, pp2))
# con solo el cambio del mes siguiente (y): mide si cambió la distribución del objetivo, sin el efecto de las variables
# acumulativas (frecuencias e historia estacional), que por construcción distinguen los años recientes
pp3 = cross_val_predict(lgb.LGBMClassifier(n_estimators=300, learning_rate=.05, num_leaves=31, verbose=-1, random_state=SEMILLA, n_jobs=NUCLEOS),
                        D[["y"]].values, D.t.values, cv=StratifiedKFold(5, shuffle=True, random_state=SEMILLA), method="predict_proba")[:, 1]
S["adversaria"]["solo_y"] = float(roc_auc_score(D.t, pp3))
_m = lgb.LGBMClassifier(n_estimators=300, learning_rate=.05, num_leaves=31, verbose=-1, random_state=SEMILLA, n_jobs=NUCLEOS,
                        importance_type="gain").fit(D[NV].values, D.t.values)
_i = pd.Series(_m.feature_importances_, index=NV); _i = (_i / _i.sum()).sort_values(ascending=False).head(6)
S["adversaria"]["importancia"] = {k: round(float(v), 3) for k, v in _i.items()}
dis = P[P.mes_obj.dt.month <= 9].assign(a=P.mes_obj.dt.year, p=P.grupo.isin(PER)).query("p").groupby("a").y.agg(lambda s: float(s.std() * 100))
S["sd_ene_sep"] = dis.round(2).to_dict(); log("deriva", S["ks"], S["adversaria"], S["sd_ene_sep"])

# ---------- 9. KPSS, El Niño, variedades, bootstrap estacionario ----------
from statsmodels.tsa.stattools import adfuller, kpss
B = pd.read_parquet(DATOS / "base_unida_mensual.parquet"); B = B[B.unidad == "$/kg"]
W = B.merge(P[["mercado", "alimento"]].drop_duplicates()).pivot_table(index=["mercado", "alimento"], columns="mes", values="precio")
c = dict(n=0, adf_no=0, kpss_rech=0, ambas_raiz=0, ambas_est=0, kpss_rech_cambio=0)
for _, s in W.iterrows():
    l = np.log(s).interpolate(limit_area="inside").dropna()
    if len(l) < 60: continue
    c["n"] += 1; a_ = adfuller(l.values, regression="ct", autolag="AIC")[1] >= .05
    k_ = kpss(l.values, regression="ct", nlags="auto")[1] < .05
    c["adf_no"] += a_; c["kpss_rech"] += k_; c["ambas_raiz"] += (a_ and k_); c["ambas_est"] += ((not a_) and (not k_))
    c["kpss_rech_cambio"] += kpss(np.diff(l.values), regression="c", nlags="auto")[1] < .05
S["kpss"] = {k: (v / c["n"] if k != "n" else v) for k, v in c.items()}; log("KPSS", S["kpss"])

o = pd.read_csv(DATOS / "oni_v6.csv").melt("year", var_name="s", value_name="oni").dropna()
orden = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
o["k"] = o.year * 12 + o.s.map({s: i for i, s in enumerate(orden)}); o = o.sort_values("k"); o = o[(o.year >= 2017) & (o.year <= 2026)]
ep = []
for signo, nom in ((1, "El Niño"), (-1, "La Niña")):
    on = (o.oni * signo >= .5).values; i = 0
    while i < len(on):
        if on[i]:
            j = i
            while j + 1 < len(on) and on[j + 1]: j += 1
            if j - i + 1 >= 5:
                pico = float((o.oni.values[i:j + 1] * signo).max())
                ep.append(dict(tipo=nom, inicio=f"{o.year.values[i]}-{o.s.values[i]}", fin=f"{o.year.values[j]}-{o.s.values[j]}", pico=pico,
                               fuerza="muy fuerte" if pico >= 2 else "fuerte" if pico >= 1.5 else "moderado" if pico >= 1 else "débil"))
            i = j + 1
        else: i += 1
S["oni_episodios"] = ep; log("ONI", ep)

EQ = ["Papa criolla", "Papa R-12", "Arroz", "Yuca", "Cebolla Cabezona", "Maíz Amarillo", "Maíz Blanco", "Azúcar", "Naranja Valencia y/o Sweet", "Harinas",
      "Manzana importada", "Repollo", "Mora", "Melón", "Panela", "Arracacha", "Lenteja", "Fríjol", "Fríjol verde", "Huevo", "Mojarra", "Aceites"]
sp = P[["mercado", "alimento"]].drop_duplicates()
S["variedades"] = dict(series_equivalencia=int(sp.alimento.isin(EQ).sum()), series=int(len(sp)), productos=sorted(sp.alimento[sp.alimento.isin(EQ)].unique().tolist()))
log("variedades", S["variedades"])


def bootstrap_estacionario(meses, funcion, B=10000, L=3, semilla=SEMILLA):
    """Bootstrap estacionario (Politis y Romano, 1994): bloques de longitud geométrica con media L, circular."""
    meses = np.asarray(meses); u = np.unique(meses); n = len(u); pos = {m: np.where(meses == m)[0] for m in u}
    rng = np.random.default_rng(semilla); reps = []
    for _ in range(B):
        idx = []; i = rng.integers(n)
        while len(idx) < n:
            idx.append(i); i = rng.integers(n) if rng.random() < 1 / L else (i + 1) % n
        reps.append(funcion(np.concatenate([pos[u[j]] for j in idx])))
    return np.array(reps)


e_c, e0 = np.abs(y - OR[ER].values), np.abs(y)
f_ = lambda i: 1 - e_c[i].mean() / e0[i].mean()
_, rb = bootstrap_metrica(mes, f_, B=10000)
re_ = bootstrap_estacionario(mes, f_)
S["bootstrap"] = dict(puntual=float(f_(np.arange(len(y)))), bloques_10000=ic(rb), estacionario_10000=ic(re_), bloques_1000=ic(bootstrap_metrica(mes, f_, B=1000)[1]))
log("bootstrap", S["bootstrap"])

# ---------- 10. detalles de casos ----------
cs = leer_json("casos_shap.json") if (RES / "casos_shap.json").exists() else {}
mg = P[(P.alimento == "Mango Tommy") & P.mercado.str.contains("Central Mayorista de Antioquia") & (P.mes_obj == "2025-02-01")]
S["mango_feb25"] = dict(dist_max=float(mg.dist_max_12m.iloc[0]), por_debajo_max=float(1 - np.exp(mg.dist_max_12m.iloc[0]))) if len(mg) else {}
ap_ = OR[OR.alimento == "Apio"]
S["apio"] = dict(n=int(len(ap_)), mae_rw=float(np.abs(ap_.y).mean() * 100), mae_cat=float(np.abs(ap_.y - ap_[ER]).mean() * 100),
                 tasa_alza=float(ap_.alza.mean()), corr_pred_obs=float(np.corrcoef(ap_.y, ap_[ER])[0, 1]),
                 mae_rw_des=float(np.abs(ent_[ent_.alimento == "Apio"].y).mean() * 100))
tons = B[B.alimento.isin(["Mango Tommy", "Cilantro"])].groupby(["alimento", "mercado"]).ton.sum().sort_values(ascending=False)
S["casos_volumen"] = {a: tons[a].head(3).round(0).to_dict() for a in ("Mango Tommy", "Cilantro")}
log("casos", S["mango_feb25"], S["apio"], S["casos_volumen"])
guardar_json(S, "revision.json"); log("fin")
