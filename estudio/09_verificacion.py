"""Paso 9. Verificación de las implementaciones que no son de uso estándar en scikit-learn:
a) regresión cuantílica (mediana) por descenso de gradiente estocástico frente a la solución exacta por programación lineal;
b) MLP con error absoluto: gradientes frente a diferencias finitas y recuperación de la mediana condicional en datos simulados;
c) Random Forest con pérdida absoluta (modo bosque de LightGBM) frente al de scikit-learn con criterio de error absoluto."""
import warnings
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.linear_model import SGDRegressor, QuantileRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.ensemble import RandomForestRegressor
from comun import *
from modelos import matrices, REGRESION
from redes import MLPL1
warnings.filterwarnings("ignore")
P = cargar_panel(); V = variables_finales(); GRP = sorted(P.grupo.unique()); RS = leer_json("reg_seleccion.json")
rng = np.random.default_rng(SEMILLA); S = {}
tr, va = P[P.muestra == "entrenamiento"], P[P.muestra == "validacion"]
a = tr.sample(6000, random_state=SEMILLA); b = va.sample(4000, random_state=SEMILLA)

# a) regresión cuantílica: SGD frente a programación lineal (sin penalización)
Xa, Xb = matrices(V, GRP, "lineal", a, b)
exacta = QuantileRegressor(quantile=.5, alpha=0.0, solver="highs").fit(Xa, a.y.values)
sgd = SGDRegressor(loss="epsilon_insensitive", epsilon=0.0, penalty="l2", alpha=1e-7, max_iter=60, tol=None, average=True, random_state=SEMILLA).fit(Xa, a.y.values)
pe, ps = exacta.predict(Xb), sgd.predict(Xb)
S["cuantilica"] = dict(mae_exacta=float(np.mean(np.abs(b.y - pe)) * 100), mae_sgd=float(np.mean(np.abs(b.y - ps)) * 100),
                       corr_pred=float(np.corrcoef(pe, ps)[0, 1]), corr_coef=float(np.corrcoef(exacta.coef_, sgd.coef_)[0, 1]),
                       dif_media_pred=float(np.mean(np.abs(pe - ps)) * 100))

# b1) gradientes de la red con diferencias finitas
red = MLPL1(capas=(8, 4), alpha=1e-3); Xs = rng.normal(size=(200, 5)).astype(np.float64); ys = rng.normal(size=200)
red.fit(Xs.astype(np.float32), ys.astype(np.float32)); W = [(w.astype(np.float64), bb.astype(np.float64)) for w, bb in red.W_]
G = red.gradientes(Xs, ys, W); err = []
for k in range(len(W)):
    for _ in range(10):
        i, jj = rng.integers(W[k][0].shape[0]), rng.integers(W[k][0].shape[1]); hh = 1e-6
        Wp = [(w.copy(), bb.copy()) for w, bb in W]; Wm = [(w.copy(), bb.copy()) for w, bb in W]
        Wp[k][0][i, jj] += hh; Wm[k][0][i, jj] -= hh
        num = (red.perdida(Xs, ys, Wp) - red.perdida(Xs, ys, Wm)) / (2 * hh); err.append(abs(num - G[k][0][i, jj]) / max(1e-8, abs(num) + abs(G[k][0][i, jj])))
S["gradientes"] = dict(error_relativo_mediano=float(np.median(err)), error_relativo_max=float(np.max(err)), n=len(err))

# b2) datos simulados con ruido asimétrico: la red L1 debe estimar la mediana y la red cuadrática la media
n = 20000; x = rng.uniform(-2, 2, size=(n, 2)); f = np.sin(2 * x[:, 0]) + .5 * x[:, 1]; ruido = rng.exponential(1.0, n) - np.log(2)   # mediana 0, media 1-ln2
ysim = f + ruido; xt = rng.uniform(-2, 2, size=(4000, 2)); ft = np.sin(2 * xt[:, 0]) + .5 * xt[:, 1]
m1 = MLPL1(capas=(64, 32), alpha=1e-5, lr=1e-3).fit(x.astype(np.float32), ysim.astype(np.float32)).predict(xt.astype(np.float32))
m2 = MLPRegressor(hidden_layer_sizes=(64, 32), alpha=1e-5, learning_rate_init=1e-3, batch_size=512, max_iter=80, early_stopping=True, random_state=SEMILLA).fit(x, ysim).predict(xt)
S["simulacion"] = dict(dist_mediana_L1=float(np.mean(np.abs(m1 - ft))), dist_media_L1=float(np.mean(np.abs(m1 - (ft + 1 - np.log(2))))),
                       dist_mediana_L2=float(np.mean(np.abs(m2 - ft))), dist_media_L2=float(np.mean(np.abs(m2 - (ft + 1 - np.log(2))))))

# c) Random Forest: LightGBM (modo bosque, pérdida absoluta) frente a scikit-learn (criterio de error absoluto)
Ta, Tb = matrices(V, GRP, "arbol", a.iloc[:3000], b)
Ta, Tb = np.nan_to_num(Ta, nan=-999), np.nan_to_num(Tb, nan=-999)
h = dict(RS["mejores"]["Random Forest"]["params"]) if "Random Forest" in RS.get("mejores", {}) else dict(prof=12, hoja=40, mf=.5)
rf_l = REGRESION["Random Forest"][1](h).fit(Ta, a.y.values[:3000]).predict(Tb)
rf_s = RandomForestRegressor(n_estimators=200, criterion="absolute_error", max_depth=h["prof"], min_samples_leaf=h["hoja"], max_features=h["mf"], max_samples=.5,
                             n_jobs=NUCLEOS, random_state=SEMILLA).fit(Ta, a.y.values[:3000]).predict(Tb)
S["random_forest"] = dict(mae_lightgbm=float(np.mean(np.abs(b.y - rf_l)) * 100), mae_sklearn=float(np.mean(np.abs(b.y - rf_s)) * 100),
                          mae_paseo=float(np.mean(np.abs(b.y)) * 100), corr_pred=float(np.corrcoef(rf_l, rf_s)[0, 1]))
guardar_json(S, "verificacion.json"); print(S)
