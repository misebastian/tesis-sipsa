"""Paso 4. Regresión del cambio de precio al mes siguiente con las variables seleccionadas.
Modelos (modelos.py), todos con pérdida absoluta. Referencias: paseo aleatorio, AR estacional en panel (LAD) y SARIMA por serie.
Hiperparámetros: búsqueda aleatoria con la regla común de presupuesto y convergencia (busqueda.py), evaluando el MAE promedio
de tres cortes (ajuste hasta 2021, 2022 y 2023; evaluación en 2022, 2023 y 2024). Se elige el modelo de menor MAE promedio.
Cada modelo se reajusta con 2019-2024 y se evalúa una sola vez en la prueba (ene-2025 a sep-2026)."""
import time, warnings, joblib
import numpy as np, pandas as pd
from comun import *
from modelos import REGRESION, matrices, ajustar_ar, limpiar
from busqueda import buscar
warnings.filterwarnings("ignore")
P = cargar_panel(); V = variables_finales(); GRP = sorted(P.grupo.unique())
T0 = time.time(); log = lambda *a: print(f"[{time.time() - T0:5.0f}s]", *a, flush=True)
cortes = [(P[P.mes_obj <= x], P[(P.mes_obj > x) & (P.mes_obj <= y)]) for x, y in CORTES_CV]
SAR = pd.read_parquet(RES / "sarima.parquet")


def evaluar(h, datos):
    f = REGRESION[datos["nombre"]][1]
    return [float(np.mean(np.abs(yb - f(h).fit(Xa, ya).predict(Xb)))) for Xa, ya, Xb, yb in datos["cortes"]]


def sarima_en(d, corte):
    """Pronóstico SARIMA alineado con las filas de d; donde no hay ajuste se usa el paseo aleatorio (0)."""
    s = SAR[SAR.corte == corte].set_index(["mercado", "alimento", "mes_obj"])
    k = pd.MultiIndex.from_frame(d[["mercado", "alimento", "mes_obj"]])
    return s.pred.reindex(k).values, s.prob.reindex(k).values


busq, mejores = {}, {}
for nombre, (tipo, f, esp) in REGRESION.items():
    M = [matrices(V, GRP, tipo, a, b) for a, b in cortes]
    datos = dict(nombre=nombre, cortes=[(Xa, a.y.values, Xb, b.y.values) for (Xa, Xb), (a, b) in zip(M, cortes)])
    r = buscar(esp, evaluar, datos, sentido=1, tol=1e-4)
    mejores[nombre] = dict(params=limpiar(r["params"]), mae_cv=r["puntaje"], mae_cortes=r["por_corte"], n_ensayos=r["n_ensayos"], convergio=r["convergio"])
    busq[nombre] = dict(curva=r["curva"], ensayos=[dict(h=limpiar(e["h"]), p=e["p"]) for e in r["ensayos"]])
    log(nombre, "MAE CV", round(r["puntaje"] * 100, 3), "ensayos", r["n_ensayos"], "convergió" if r["convergio"] else "NO convergió")
guardar_json(busq, "reg_busqueda.json")

ref_cv = {"Paseo aleatorio": [], "AR estacional": [], "SARIMA": []}
for k, (a, b) in enumerate(cortes):
    ref_cv["Paseo aleatorio"].append(float(np.mean(np.abs(b.y))))
    ref_cv["AR estacional"].append(float(np.mean(np.abs(b.y - ajustar_ar(a, b)))))
    ps, _ = sarima_en(b, f"cv{k}"); ref_cv["SARIMA"].append(float(np.mean(np.abs(b.y - np.nan_to_num(ps)))))
ref_cv = {k: dict(mae_cv=float(np.mean(v)), mae_cortes=v) for k, v in ref_cv.items()}
elegido = min(mejores, key=lambda k: mejores[k]["mae_cv"]); log("elegido:", elegido, {k: round(v["mae_cv"] * 100, 3) for k, v in ref_cv.items()})

ent, te = P[P.muestra != "prueba"], P[P.muestra == "prueba"]
O = te[["mercado", "alimento", "grupo", "ciudad", "mes_obj", "y", "alza"]].copy()
O["Paseo aleatorio"] = 0.0; O["AR estacional"] = ajustar_ar(ent, te)
ps, _ = sarima_en(te, "prueba"); O["SARIMA"] = np.nan_to_num(ps); O["sarima_disponible"] = ~np.isnan(ps)
for nombre, (tipo, f, esp) in REGRESION.items():
    Xa, Xb = matrices(V, GRP, tipo, ent, te); mod = f(mejores[nombre]["params"]).fit(Xa, ent.y.values); O[nombre] = mod.predict(Xb)
    (RES / "modelos").mkdir(exist_ok=True); joblib.dump(mod, RES / "modelos" / f"reg_{nombre}.joblib")   # modelo final guardado
    log("prueba", nombre, round(float(np.mean(np.abs(O.y - O[nombre]))) * 100, 3))
O.to_parquet(RES / "reg_predicciones_prueba.parquet")
guardar_json(dict(mejores=mejores, referencias_cv=ref_cv, elegido=elegido, modelos=list(REGRESION), sarima_cobertura=float(O.sarima_disponible.mean())), "reg_seleccion.json")
log("fin")
