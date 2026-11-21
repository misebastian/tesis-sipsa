"""Paso 5. Clasificación de alzas fuertes (> 15 %) con las variables seleccionadas.
1) Hiperparámetros: búsqueda aleatoria con la regla común de presupuesto y convergencia, PR-AUC promedio de tres cortes
   (evaluación en 2022, 2023 y 2024), sin balanceo.
2) Balanceo: sin balanceo, pesos de clase y submuestreo, evaluados con las predicciones fuera de muestra de los tres cortes
   reunidas (36 meses). Se adopta solo si mejora la PR-AUC reunida en más de 0,005.
3) Recalibración del intercepto: con las predicciones fuera de muestra, logit p* = a + logit p (pendiente fija en 1).
4) Umbral: el que maximiza F1 en las predicciones fuera de muestra recalibradas. Modelo elegido: mayor PR-AUC fuera de muestra.
Cada modelo se reajusta con 2019-2024 y se evalúa una sola vez en la prueba. Referencias: frecuencia histórica, logística
autorregresiva y SARIMA (probabilidad con residuos empíricos)."""
import time, warnings, joblib
import numpy as np, pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss, precision_recall_curve
from imblearn.under_sampling import RandomUnderSampler
from comun import *
from modelos import CLASIFICACION, CON_PESO_MUESTRAL, matrices, ajustar_ar, limpiar
from busqueda import buscar
warnings.filterwarnings("ignore")
P = cargar_panel(); V = variables_finales(); GRP = sorted(P.grupo.unique())
T0 = time.time(); log = lambda *a: print(f"[{time.time() - T0:5.0f}s]", *a, flush=True)
BALANCEO = ["Sin balanceo", "Pesos de clase", "Submuestreo"]
cortes = [(P[P.mes_obj <= x], P[(P.mes_obj > x) & (P.mes_obj <= y)]) for x, y in CORTES_CV]
EV = pd.concat([b for _, b in cortes]); zv = EV.alza.values
SAR = pd.read_parquet(RES / "sarima.parquet")
logit = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
expit = lambda x: 1 / (1 + np.exp(-x))


def ajustar_proba(nombre, h, bal, Xa, y, Xb, guardar_en=None):
    f = CLASIFICACION[nombre][1]; w = 1.0; sw = None
    if bal == "Pesos de clase":
        w = float((1 - y.mean()) / y.mean())
        if nombre in CON_PESO_MUESTRAL: sw = np.where(y == 1, w, 1.0); w = 1.0
    elif bal == "Submuestreo": Xa, y = RandomUnderSampler(random_state=SEMILLA).fit_resample(Xa, y)
    m = f(h, w); m.fit(Xa, y, sample_weight=sw) if sw is not None else m.fit(Xa, y)
    if guardar_en is not None: (RES / "modelos").mkdir(exist_ok=True); joblib.dump(m, RES / "modelos" / guardar_en)   # modelo final guardado
    return m.predict_proba(Xb)[:, 1]


def evaluar(h, datos):
    return [float(average_precision_score(zb, ajustar_proba(datos["nombre"], h, "Sin balanceo", Xa, za, Xb))) for Xa, za, Xb, zb in datos["cortes"]]


def intercepto(p, z):
    lp = logit(p); return float(minimize_scalar(lambda a: -np.sum(z * (a + lp) - np.log1p(np.exp(a + lp))), bounds=(-5, 5), method="bounded").x)


def sarima_prob(d, corte):
    s = SAR[SAR.corte == corte].set_index(["mercado", "alimento", "mes_obj"])
    return s.prob.reindex(pd.MultiIndex.from_frame(d[["mercado", "alimento", "mes_obj"]])).values


busq, mejores, MAT = {}, {}, {}
for nombre, (tipo, f, esp) in CLASIFICACION.items():
    M = [matrices(V, GRP, tipo, a, b, imputar_arbol=True) for a, b in cortes]; MAT[nombre] = M
    datos = dict(nombre=nombre, cortes=[(Xa, a.alza.values, Xb, b.alza.values) for (Xa, Xb), (a, b) in zip(M, cortes)])
    r = buscar(esp, evaluar, datos, sentido=-1, tol=0.002)
    mejores[nombre] = dict(params=limpiar(r["params"]), pr_cv=r["puntaje"], pr_cortes=r["por_corte"], n_ensayos=r["n_ensayos"], convergio=r["convergio"])
    busq[nombre] = dict(curva=r["curva"], ensayos=[dict(h=limpiar(e["h"]), p=e["p"]) for e in r["ensayos"]])
    log(nombre, "PR-AUC CV", round(r["puntaje"], 4), "ensayos", r["n_ensayos"], "convergió" if r["convergio"] else "NO convergió")
guardar_json(busq, "clf_busqueda.json")

# ---------- balanceo con predicciones fuera de muestra reunidas ----------
filas, OOS = [], {}
for nombre in CLASIFICACION:
    for bal in BALANCEO:
        p = np.concatenate([ajustar_proba(nombre, mejores[nombre]["params"], bal, Xa, a.alza.values, Xb) for (Xa, Xb), (a, b) in zip(MAT[nombre], cortes)])
        OOS[(nombre, bal)] = p
        filas.append(dict(modelo=nombre, balanceo=bal, pr_auc=average_precision_score(zv, p), roc_auc=roc_auc_score(zv, p), brier=brier_score_loss(zv, p), prob_media=float(p.mean())))
    log("balanceo", nombre)
ref = np.concatenate([b.frec_alza_hist.fillna(a.alza.mean()).values for a, b in cortes])
ref2 = np.concatenate([ajustar_ar(a, b, "clf") for a, b in cortes])
ref3 = np.concatenate([sarima_prob(b, f"cv{k}") for k, (a, b) in enumerate(cortes)]); ref3 = np.where(np.isnan(ref3), ref, ref3)
for nm, p in (("Frecuencia histórica", ref), ("Logística autorregresiva", ref2), ("SARIMA", ref3)):
    filas.append(dict(modelo=nm, balanceo="—", pr_auc=average_precision_score(zv, p), roc_auc=roc_auc_score(zv, p), brier=brier_score_loss(zv, p), prob_media=float(p.mean())))
Bv = pd.DataFrame(filas); Bv["tasa_real"] = zv.mean(); Bv.to_csv(RES / "clf_balanceo_val.csv", index=False)
eleccion_bal = {}
for nombre in CLASIFICACION:
    d = Bv[Bv.modelo == nombre].set_index("balanceo"); mejor = d.pr_auc.idxmax()
    eleccion_bal[nombre] = mejor if d.loc[mejor, "pr_auc"] > d.loc["Sin balanceo", "pr_auc"] + .005 else "Sin balanceo"

# ---------- recalibración del intercepto y umbral ----------
recal, umbral, pr_val, PVAL = {}, {}, {}, {}
for nombre in CLASIFICACION:
    p = OOS[(nombre, eleccion_bal[nombre])]; a = intercepto(p, zv); pr_ = expit(a + logit(p))
    recal[nombre] = dict(intercepto=a, brier_antes=brier_score_loss(zv, p), brier_despues=brier_score_loss(zv, pr_), media_antes=float(p.mean()), media_despues=float(pr_.mean()))
    pr_val[nombre] = float(average_precision_score(zv, pr_)); PVAL[nombre] = pr_
    pr, rc, th = precision_recall_curve(zv, pr_); f1 = 2 * pr * rc / np.clip(pr + rc, 1e-9, None)
    umbral[nombre] = float(th[np.nanargmax(f1[:-1])])
elegido = max(pr_val, key=pr_val.get)
pd.DataFrame(PVAL).assign(alza=zv, mes_obj=EV.mes_obj.values, **{"Frecuencia histórica": ref}).to_parquet(RES / "clf_predicciones_val.parquet")
log("elegido:", elegido, {k: round(v, 3) for k, v in umbral.items()})

ent, te = P[P.muestra != "prueba"], P[P.muestra == "prueba"]
O = te[["mercado", "alimento", "grupo", "ciudad", "mes_obj", "y", "alza"]].copy()
O["Frecuencia histórica"] = te.frec_alza_hist.fillna(ent.alza.mean()).values; O["Logística autorregresiva"] = ajustar_ar(ent, te, "clf")
ps = sarima_prob(te, "prueba"); O["SARIMA"] = np.where(np.isnan(ps), O["Frecuencia histórica"], ps)
for nombre, (tipo, f, esp) in CLASIFICACION.items():
    Xa, Xb = matrices(V, GRP, tipo, ent, te, imputar_arbol=True)
    p = ajustar_proba(nombre, mejores[nombre]["params"], eleccion_bal[nombre], Xa, ent.alza.values, Xb, guardar_en=f"clf_{nombre}.joblib")
    O[nombre + " (sin recalibrar)"] = p; O[nombre] = expit(recal[nombre]["intercepto"] + logit(p))
    log("prueba", nombre, round(average_precision_score(O.alza, O[nombre]), 4))
O.to_parquet(RES / "clf_predicciones_prueba.parquet")
guardar_json(dict(mejores=mejores, balanceo=eleccion_bal, recalibracion=recal, umbral=umbral, pr_val=pr_val, elegido=elegido, modelos=list(CLASIFICACION)), "clf_seleccion.json")
log("fin")
