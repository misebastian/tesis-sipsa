"""Paso 17. Sensibilidad de la regla de atípicos (revisión): umbrales 2, 3 y 4 con la mediana centrada de 7 meses (retrospectiva)
y con una mediana solo hacia atrás (regla causal, utilizable en tiempo real). Para cada caso se mira si el mismo producto se movió
en la misma dirección en las demás centrales. Escribe resultados/atipicos_sensibilidad.json."""
import numpy as np, pandas as pd
from comun import *
B = pd.read_parquet(DATOS / "base_unida_mensual.parquet"); B = B[B.unidad == "$/kg"]
P = cargar_panel(); B = B.merge(P[["mercado", "alimento"]].drop_duplicates())
Wl = np.log(B.pivot_table(index=["mercado", "alimento"], columns="mes", values="precio"))
Rl = Wl.diff(axis=1); out = {}
for nombre, med in (("centrada", Wl.T.rolling(7, center=True, min_periods=3).median().T),
                    ("causal", Wl.T.shift(1).rolling(6, min_periods=3).median().T)):
    D = (Wl - med).stack()
    for f in (2, 3, 4):
        c = D[D.abs() > np.log(f)]; ais = 0
        for (m, a, t), v in c.items():
            o = Rl.xs(a, level="alimento")[t].drop(m, errors="ignore").dropna()
            if len(o) and (np.sign(o) == np.sign(v)).mean() < .5: ais += 1
        out[f"{nombre}_{f}"] = dict(casos=int(len(c)), aislados=int(ais), pct=float(len(c) / Wl.notna().sum().sum()))
print(out); guardar_json(out, "atipicos_sensibilidad.json")
