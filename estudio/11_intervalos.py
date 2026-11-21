"""Paso 11. Guarda, para cada pronóstico de la prueba, los cuantiles estimados y los intervalos conformes por grupo (80 % y 90 %).
Reproduce el ajuste del paso 7 (mismos hiperparámetros, guardados en complementarios.json) y escribe resultados/intervalos_prueba.parquet,
que usa 10_figuras.py para el caso ilustrativo. No interviene en ninguna decisión."""
import numpy as np, pandas as pd
import lightgbm as lgb
from comun import *
from modelos import matrices

P = cargar_panel(); V = variables_finales(); GRP = sorted(P.grupo.unique())
hq = leer_json("complementarios.json")["cuantiles_busqueda"]["params"]
TAUS = np.array([.05, .10, .25, .50, .75, .90, .95]); j = {t: i for i, t in enumerate(TAUS)}
qmod = lambda t: lgb.LGBMRegressor(objective="quantile", alpha=t, n_estimators=hq["n"], learning_rate=hq["lr"], num_leaves=hq["hojas"], min_child_samples=hq["mcs"],
                                   subsample=hq["ss"], subsample_freq=1, colsample_bytree=hq["cs"], reg_lambda=hq["l2"], n_jobs=NUCLEOS, random_state=SEMILLA, verbose=-1)


def predq(a, b):
    Xa, Xb = matrices(V, GRP, "arbol", a, b)
    return np.sort(np.column_stack([qmod(t).fit(Xa, a.y.values).predict(Xb) for t in TAUS]), axis=1)


te = P[P.muestra == "prueba"]; tr23, va24 = P[P.muestra == "entrenamiento"], P[P.muestra == "validacion"]
Qc = predq(tr23, pd.concat([va24, te])); Qv, Qt = Qc[:len(va24)], Qc[len(va24):]
per = lambda d: np.where(d.grupo.isin(["FRUTAS", "VERDURAS Y HORTALIZAS", "TUBERCULOS, RAICES Y PLATANOS"]).values, "Perecederos", "No perecederos")
gv, gt = per(va24), per(te); yv, yt = va24.y.values, te.y.values
out = te[["mercado", "alimento", "grupo", "mes_obj", "y"]].copy().reset_index(drop=True)
for t in TAUS: out[f"q{int(t * 100):02d}"] = Qt[:, j[t]]
for nom, lo_, hi_, alfa in (("90", j[.05], j[.95], .10), ("80", j[.10], j[.90], .20)):
    L, U = Qt[:, lo_].copy(), Qt[:, hi_].copy(); sc = np.maximum(Qv[:, lo_] - yv, yv - Qv[:, hi_])
    for g in np.unique(gv):
        n_ = (gv == g).sum(); qh = np.quantile(sc[gv == g], min(1, np.ceil((n_ + 1) * (1 - alfa)) / n_)); L[gt == g] -= qh; U[gt == g] += qh
    out[f"lo{nom}"], out[f"hi{nom}"] = L, U
    print(nom, "cobertura", round(float(((yt >= L) & (yt <= U)).mean()) * 100, 1))
out.to_parquet(RES / "intervalos_prueba.parquet", index=False)
