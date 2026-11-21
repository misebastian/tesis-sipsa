"""Modelos, espacios de búsqueda y preparación de matrices. Lo usan 04, 05, 06 y 07.
Cada entrada: (tipo de matriz, constructor(h[, w]), espacio de búsqueda).
Comparación equitativa: todos los modelos de una tarea minimizan la misma pérdida (absoluta en regresión, logarítmica en
clasificación) y su búsqueda aleatoria sigue la misma regla de presupuesto y convergencia (busqueda.py).
El número de hilos de cada ajuste se toma de h["_hilos"] (la búsqueda usa 1 por ensayo y corre ensayos en paralelo).
tipo 'lineal': numéricas estandarizadas + indicadores de grupo; tipo 'arbol': variables tal cual."""
import numpy as np, pandas as pd, lightgbm as lgb, xgboost as xgb
from scipy.stats import loguniform, randint, uniform
from sklearn.linear_model import SGDRegressor, LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from catboost import CatBoostRegressor, CatBoostClassifier
from comun import NUCLEOS, SEMILLA
from redes import MLPL1

CAPAS = [(32,), (64,), (64, 32), (128, 64)]
_h = lambda h: int(h.get("_hilos", NUCLEOS))
E_MLP = dict(capas=randint(0, 4), alpha=loguniform(1e-6, 1e-2), lr=loguniform(1e-4, 3e-3))
E_RF = dict(prof=randint(8, 20), hoja=randint(10, 150), mf=uniform(.3, .5))
E_XGB = dict(n=randint(150, 600), lr=loguniform(.02, .12), prof=randint(3, 9), mcw=loguniform(1, 60), ss=uniform(.6, .4), cs=uniform(.4, .6))
E_LGB = dict(n=randint(150, 700), lr=loguniform(.02, .12), hojas=randint(8, 97), mcs=randint(20, 400), ss=uniform(.6, .4), cs=uniform(.4, .6), l2=loguniform(1e-3, 10))
E_CAT = dict(n=randint(250, 550), prof=randint(4, 9), lr=loguniform(.02, .12), l2=loguniform(1, 10))

REGRESION = {
    "Regresión cuantílica": ("lineal", lambda h: SGDRegressor(loss="epsilon_insensitive", epsilon=0.0, penalty=h["pen"], alpha=h["alpha"], max_iter=60, tol=None,
                                                              average=True, random_state=SEMILLA),
                             dict(alpha=loguniform(1e-7, 1e-2), pen=["l2", "l1"])),
    "MLP": ("lineal", lambda h: MLPL1(capas=CAPAS[h["capas"]], alpha=h["alpha"], lr=h["lr"], semilla=SEMILLA), E_MLP),
    "Random Forest": ("arbol", lambda h: lgb.LGBMRegressor(boosting_type="rf", objective="l1", n_estimators=200, subsample=.5, subsample_freq=1,
                                                             feature_fraction_bynode=h["mf"], max_depth=h["prof"], num_leaves=min(2 ** h["prof"], 8192),
                                                             min_child_samples=h["hoja"], n_jobs=_h(h), random_state=SEMILLA, verbose=-1), E_RF),
    "XGBoost": ("arbol", lambda h: xgb.XGBRegressor(objective="reg:absoluteerror", tree_method="hist", n_estimators=h["n"], learning_rate=h["lr"], max_depth=h["prof"],
                                                       min_child_weight=h["mcw"], subsample=h["ss"], colsample_bytree=h["cs"], n_jobs=_h(h), random_state=SEMILLA, verbosity=0), E_XGB),
    "LightGBM": ("arbol", lambda h: lgb.LGBMRegressor(objective="l1", n_estimators=h["n"], learning_rate=h["lr"], num_leaves=h["hojas"], min_child_samples=h["mcs"], subsample=h["ss"],
                                                        subsample_freq=1, colsample_bytree=h["cs"], reg_lambda=h["l2"], n_jobs=_h(h), random_state=SEMILLA, verbose=-1), E_LGB),
    "CatBoost": ("arbol", lambda h: CatBoostRegressor(loss_function="MAE", iterations=h["n"], depth=h["prof"], learning_rate=h["lr"], l2_leaf_reg=h["l2"], thread_count=_h(h),
                                                        random_seed=SEMILLA, verbose=0, allow_writing_files=False), E_CAT),
}

# w: peso de la clase positiva (1 = sin ponderar)
CLASIFICACION = {
    "Regresión logística": ("lineal", lambda h, w: LogisticRegression(C=h["C"], penalty=h["pen"], solver="liblinear", max_iter=3000, class_weight={0: 1, 1: w}),
                            dict(C=loguniform(1e-3, 10), pen=["l1", "l2"])),
    "MLP": ("lineal", lambda h, w: MLPClassifier(hidden_layer_sizes=CAPAS[h["capas"]], alpha=h["alpha"], learning_rate_init=h["lr"], batch_size=512, max_iter=80,
                                                  early_stopping=True, n_iter_no_change=8, random_state=SEMILLA), E_MLP),
    "Random Forest": ("arbol", lambda h, w: RandomForestClassifier(criterion="log_loss", n_estimators=250, max_depth=h["prof"], min_samples_leaf=h["hoja"], max_features=h["mf"],
                                                                     max_samples=.5, class_weight={0: 1, 1: w}, n_jobs=_h(h), random_state=SEMILLA), E_RF),
    "XGBoost": ("arbol", lambda h, w: xgb.XGBClassifier(n_estimators=h["n"], learning_rate=h["lr"], max_depth=h["prof"], min_child_weight=h["mcw"], subsample=h["ss"],
                                                       colsample_bytree=h["cs"], scale_pos_weight=w, tree_method="hist", n_jobs=_h(h), random_state=SEMILLA, verbosity=0), E_XGB),
    "LightGBM": ("arbol", lambda h, w: lgb.LGBMClassifier(n_estimators=h["n"], learning_rate=h["lr"], num_leaves=h["hojas"], min_child_samples=h["mcs"], subsample=h["ss"], subsample_freq=1,
                                                         colsample_bytree=h["cs"], reg_lambda=h["l2"], scale_pos_weight=w, n_jobs=_h(h), random_state=SEMILLA, verbose=-1), E_LGB),
    "CatBoost": ("arbol", lambda h, w: CatBoostClassifier(iterations=h["n"], depth=h["prof"], learning_rate=h["lr"], l2_leaf_reg=h["l2"], class_weights=[1, w], thread_count=_h(h),
                                                         random_seed=SEMILLA, verbose=0, allow_writing_files=False), E_CAT),
}
CON_PESO_MUESTRAL = {"MLP"}   # pesos de clase vía sample_weight


def limpiar(h):
    """Hiperparámetros sin claves internas (para guardar)."""
    return {k: v for k, v in h.items() if not k.startswith("_")}


def matrices(V, grupos, tipo, a, b, imputar_arbol=False):
    """Devuelve (Xa, Xb). En 'lineal' estandariza con estadísticos de a (sin fuga) e imputa con la media (0 tras estandarizar)."""
    if tipo == "arbol":
        f = (lambda d: d[V].fillna(-999)) if imputar_arbol else (lambda d: d[V])
        return f(a).values.astype(np.float32), f(b).values.astype(np.float32)
    num = [c for c in V if not c.endswith("_c")]
    mu, sd = a[num].mean(), a[num].std().replace(0, 1)
    g = lambda d: pd.concat([((d[num] - mu) / sd).fillna(0).clip(-6, 6), pd.get_dummies(d.grupo, dtype=float).reindex(columns=grupos, fill_value=0)], axis=1).values.astype(np.float32)
    return g(a), g(b)


# ---------- referencia estadística: autorregresivo estacional en panel ----------
AR_VARS = ["cambio_1m", "cambio_mes_rez1", "cambio_mes_rez2", "cambio_mismo_mes_ano_ant"]


def diseno_ar(d):
    """y_{t+1} = sum_g 1{grupo=g} (a_{g,m(t+1)} + sum_j b_{g,j} r_{t-j} + c_g r_{t-11}): rezagos 0-2 del cambio mensual y el
    cambio del mismo mes un año antes, con coeficientes por grupo de alimento y efectos de mes por grupo. Regresión: LAD; clasificación: logística (L2, C = 1)."""
    import itertools
    g = d.grupo.values; m = d.mes_obj.dt.month.values; cols = {}
    for gg in sorted(set(GRUPOS_AR)):
        ig = (g == gg).astype(float)
        for mm in range(1, 13): cols[f"{gg}_m{mm}"] = ig * (m == mm)
        for v in AR_VARS: cols[f"{gg}_{v}"] = ig * d[v].fillna(0).values
    return np.column_stack(list(cols.values()))


GRUPOS_AR = ["FRUTAS", "VERDURAS Y HORTALIZAS", "TUBERCULOS, RAICES Y PLATANOS", "LACTEOS Y HUEVOS", "GRANOS Y CEREALES", "PROCESADOS", "PESCADOS"]


def ajustar_ar(a, b, tarea="reg"):
    from sklearn.linear_model import QuantileRegressor, LogisticRegression
    Xa, Xb = diseno_ar(a), diseno_ar(b)
    if tarea == "reg":   # mediana condicional (LAD), coherente con la pérdida absoluta
        return QuantileRegressor(quantile=.5, alpha=0.0, fit_intercept=False, solver="highs").fit(Xa, a.y.values).predict(Xb)
    return LogisticRegression(C=1.0, max_iter=3000, fit_intercept=False).fit(Xa, a.alza.values).predict_proba(Xb)[:, 1]
