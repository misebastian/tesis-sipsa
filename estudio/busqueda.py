"""Búsqueda aleatoria con presupuesto inicial común y criterio de convergencia, igual para todos los modelos.
Se evalúan N0 configuraciones; si en las últimas VENTANA el mejor resultado mejoró más que la tolerancia, se agregan
PASO configuraciones más, hasta NMAX. Los ensayos corren en paralelo (un hilo por ensayo)."""
import os
import numpy as np
from joblib import Parallel, delayed
from sklearn.model_selection import ParameterSampler
from comun import NUCLEOS, SEMILLA

N0 = int(os.environ.get("PRESUPUESTO", 40)); PASO, NMAX, VENTANA = 20, max(100, N0), 10


def mejor_hasta(puntajes, sentido):
    """Mejor puntaje acumulado tras cada ensayo (sentido = 1 si menor es mejor, -1 si mayor es mejor)."""
    return list(np.minimum.accumulate(np.asarray(puntajes) * sentido) * sentido)


def buscar(espacio, evaluar, datos, sentido, tol, semilla=SEMILLA, n_jobs=NUCLEOS):
    """evaluar(h, datos) -> lista de puntajes por corte. Devuelve dict con configuraciones, puntajes, curva y convergencia."""
    nmax = NMAX if N0 >= 10 else N0              # con presupuestos de prueba no se extiende
    confs = [dict(h) for h in ParameterSampler(espacio, n_iter=nmax, random_state=semilla)]
    res, n = [], min(N0, nmax)
    while True:
        res += Parallel(n_jobs=n_jobs)(delayed(evaluar)({**h, "_hilos": 1}, datos) for h in confs[len(res):n])
        media = [float(np.mean(r)) for r in res]; curva = mejor_hasta(media, sentido)
        mejora = abs(curva[-1] - curva[-1 - VENTANA]) if len(curva) > VENTANA else np.inf
        convergio = mejora <= tol
        if convergio or n >= nmax: break
        n = min(n + PASO, nmax)
    i = int(np.argmin(np.asarray(media) * sentido))
    return dict(params=confs[i], puntaje=media[i], por_corte=list(map(float, res[i])), n_ensayos=len(res), convergio=bool(convergio),
                mejora_final=float(mejora) if np.isfinite(mejora) else None, curva=curva, ensayos=[dict(h=h, p=list(map(float, r))) for h, r in zip(confs[:len(res)], res)])
