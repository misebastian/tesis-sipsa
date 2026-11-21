"""Configuración común: rutas, periodos, listas de variables, estilo de gráficas y utilidades."""
import os, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parent
DATOS, RES, FIG = RAIZ / "datos", RAIZ / "resultados", RAIZ / "figuras"
for d in (RES, FIG):
    d.mkdir(exist_ok=True)
NUCLEOS = int(os.environ.get("NUCLEOS", os.cpu_count() or 2))   # núcleos a usar en el ajuste
SEMILLA = 0
UMBRAL = float(np.log(1.15))                                       # alza fuerte: cambio mensual > 15 %
FIN_ENTRENAMIENTO, FIN_VALIDACION = "2023-12-01", "2024-12-01"     # por mes pronosticado
CORTES_CV = [("2021-12-01", "2022-12-01"), ("2022-12-01", "2023-12-01"), ("2023-12-01", "2024-12-01")]   # (fin de ajuste, fin de evaluación)

# ---------- variables ----------
HIST = ["cambio_1m", "cambio_2m", "cambio_3m", "cambio_6m", "cambio_12m", "cambio_mes_rez1", "cambio_mes_rez2", "cambio_mes_rez3",
        "vol_3m", "vol_6m", "vol_12m", "z_precio_12m", "dist_max_12m", "dist_min_12m", "alzas_12m", "meses_desde_alza"]
EST = ["mes_sin", "mes_cos", "frec_alza_hist", "cambio_estacional_hist"]
ABAST = ["cambio_ton_1m", "cambio_ton_12m", "ton_rel_12m", "log_municipios", "departamentos", "dias_registro"]
RED = ["brecha_nacional", "cambio_nacional_1m", "prop_centrales_alza"]
CAL = ["semana_santa", "diciembre"]
LUGAR = ["perecibilidad", "grupo_c", "ciudad_c", "mercado_c", "alimento_c"]
ONI = ["oni", "oni_cambio_3m"]
BASE = HIST + EST + ABAST + RED + CAL + LUGAR + ONI
BLOQUES_BASE = {"Historia del precio": HIST, "Estacionalidad": EST, "Abastecimiento local": ABAST, "Red de centrales": RED,
                "Calendario": CAL, "Producto y lugar": LUGAR, "El Niño (ONI)": ONI}
BLOQUES_NUEVOS = {
    "Promedios móviles": ["desv_ma3", "desv_ma6"],
    "Año anterior": ["cambio_mismo_mes_ano_ant", "cambio_nacional_mismo_mes_ano_ant"],
    "Red ampliada": ["cambio_nacional_2m", "cambio_nacional_12m", "brecha_nacional_cambio"],
    "Grupo en la central": ["cambio_grupo_central", "alzas_grupo_central"],
    "Abastecimiento nacional": ["cambio_ton_nacional_1m", "ton_nacional_rel_12m", "participacion_central"],
    "Calidad del dato": ["meses_obs_12m", "dias_registro_rel"],
}
NOMBRES = {
    "cambio_1m": "Cambio del precio, 1 mes", "cambio_2m": "Cambio del precio, 2 meses", "cambio_3m": "Cambio del precio, 3 meses",
    "cambio_6m": "Cambio del precio, 6 meses", "cambio_12m": "Cambio del precio, 12 meses", "cambio_mes_rez1": "Cambio mensual hace 1 mes",
    "cambio_mes_rez2": "Cambio mensual hace 2 meses", "cambio_mes_rez3": "Cambio mensual hace 3 meses", "vol_3m": "Volatilidad 3 meses",
    "vol_6m": "Volatilidad 6 meses", "vol_12m": "Volatilidad 12 meses", "z_precio_12m": "Posición del precio en el año (z)",
    "dist_max_12m": "Distancia al máximo anual", "dist_min_12m": "Distancia al mínimo anual", "alzas_12m": "Alzas fuertes en el último año",
    "meses_desde_alza": "Meses desde la última alza", "mes_sin": "Mes del año (seno)", "mes_cos": "Mes del año (coseno)",
    "frec_alza_hist": "Frecuencia histórica de alzas en el mes", "cambio_estacional_hist": "Cambio histórico en el mes",
    "cambio_ton_1m": "Cambio de toneladas, 1 mes", "cambio_ton_12m": "Cambio de toneladas, 12 meses", "ton_rel_12m": "Toneladas frente a su promedio anual",
    "log_municipios": "Municipios de origen (log)", "departamentos": "Departamentos de origen", "dias_registro": "Días con registro",
    "brecha_nacional": "Brecha con las demás centrales", "cambio_nacional_1m": "Cambio en las demás centrales, 1 mes",
    "prop_centrales_alza": "Demás centrales con alza en t", "semana_santa": "Semana Santa", "diciembre": "Diciembre", "perecibilidad": "Perecibilidad",
    "grupo_c": "Grupo (código)", "ciudad_c": "Ciudad (código)", "mercado_c": "Central (código)", "alimento_c": "Producto (código)",
    "oni": "ONI", "oni_cambio_3m": "Cambio del ONI, 3 meses", "desv_ma3": "Desviación de la media móvil 3m", "desv_ma6": "Desviación de la media móvil 6m",
    "cambio_mismo_mes_ano_ant": "Cambio del mismo mes, año anterior", "cambio_nacional_mismo_mes_ano_ant": "Cambio en las demás centrales, mismo mes del año anterior",
    "cambio_nacional_2m": "Cambio en las demás centrales, 2 meses", "cambio_nacional_12m": "Cambio en las demás centrales, 12 meses",
    "brecha_nacional_cambio": "Cambio de la brecha con las demás centrales", "cambio_grupo_central": "Cambio del grupo en la central",
    "alzas_grupo_central": "Alzas del grupo en la central", "cambio_ton_nacional_1m": "Cambio de toneladas en todas las centrales",
    "ton_nacional_rel_12m": "Toneladas en todas las centrales frente al año", "participacion_central": "Participación de la central en las toneladas",
    "meses_obs_12m": "Meses con precio en el año", "dias_registro_rel": "Días con registro frente al año",
}
GRUPOS = {"FRUTAS": "Frutas", "VERDURAS Y HORTALIZAS": "Verduras y hortalizas", "TUBERCULOS, RAICES Y PLATANOS": "Tubérculos y plátanos",
          "LACTEOS Y HUEVOS": "Lácteos y huevos", "GRANOS Y CEREALES": "Granos y cereales", "PROCESADOS": "Procesados", "PESCADOS": "Pescados", "CARNES": "Carnes"}

# ---------- estilo ----------
TINTA, SUAVE, REJILLA = "#1f2a24", "#5f6b64", "#e3e7e3"
VERDE, NARANJA, OCRE, AZUL, GRIS, MORADO, TEAL, VINO = "#2c6e49", "#c4581f", "#b7862b", "#3b6ea8", "#9aa59f", "#7a4f9a", "#3f9c9a", "#a23b5b"
PALETA = [VERDE, NARANJA, AZUL, OCRE, MORADO, TEAL, VINO, GRIS]
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "savefig.bbox": "tight", "font.size": 9.5, "font.family": "DejaVu Sans",
                     "axes.edgecolor": SUAVE, "axes.labelcolor": TINTA, "axes.titlesize": 10.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": REJILLA, "grid.linewidth": .7,
                     "xtick.color": SUAVE, "ytick.color": SUAVE, "legend.frameon": False, "axes.prop_cycle": matplotlib.cycler(color=PALETA)})


def guardar(fig, nombre):
    fig.savefig(FIG / f"{nombre}.png"); plt.close(fig)


def ejes_fecha(ax):
    import matplotlib.dates as md
    ax.xaxis.set_major_locator(md.MonthLocator(bymonth=[1, 7])); ax.xaxis.set_major_formatter(md.DateFormatter("%m/%Y"))


def guardar_json(obj, nombre):
    json.dump(obj, open(RES / nombre, "w"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


def leer_json(nombre):
    return json.load(open(RES / nombre))


def cargar_panel():
    import pandas as pd
    return pd.read_parquet(DATOS / "panel.parquet")


def variables_finales():
    return leer_json("variables_finales.json")["variables"]


# ---------- bootstrap por bloques móviles de meses (Künsch, 1989) ----------
LONG_BLOQUE = 3


def remuestras_meses(n_meses, B=1000, L=LONG_BLOQUE, semilla=SEMILLA):
    """Índices de meses para B réplicas: bloques móviles de longitud L concatenados hasta completar n_meses."""
    rng = np.random.default_rng(semilla); k = int(np.ceil(n_meses / L)); out = []
    for _ in range(B):
        ini = rng.integers(0, n_meses - L + 1, size=k)
        out.append(np.concatenate([np.arange(s, s + L) for s in ini])[:n_meses])
    return out


def bootstrap_metrica(meses, funcion, B=1000, L=LONG_BLOQUE, semilla=SEMILLA):
    """meses: arreglo con el mes de cada observación. funcion(idx) -> valor de la métrica sobre las filas idx.
    Devuelve (estimación puntual, réplicas)."""
    meses = np.asarray(meses); u = np.unique(meses); pos = {m: np.where(meses == m)[0] for m in u}
    reps = np.array([funcion(np.concatenate([pos[u[j]] for j in r])) for r in remuestras_meses(len(u), B, L, semilla)])
    return funcion(np.arange(len(meses))), reps


def ic(reps, a=.05):
    return float(np.nanpercentile(reps, 100 * a / 2)), float(np.nanpercentile(reps, 100 * (1 - a / 2)))


def holm(pvals):
    """Valores p ajustados por Holm (1979)."""
    p = np.asarray(pvals, float); o = np.argsort(p); m = len(p); adj = np.empty(m); run = 0
    for r, i in enumerate(o):
        run = max(run, min(1, (m - r) * p[i])); adj[i] = run
    return adj
