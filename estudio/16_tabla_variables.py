"""Paso 16. Tabla del apéndice con la definición operativa de las 52 variables candidatas (bloque, fórmula, ventana)
y si quedaron en el modelo final. Las fórmulas reproducen las de 01_panel.py. Escribe ../tesis/Tablas/tab_variables.tex."""
from pathlib import Path
from comun import *

# notación: l_t = ln p_t (con el último precio repetido en huecos de hasta 2 meses); r_t = l_t - l_{t-1};
# a_t = 1{r_t > ln 1,15}; o_t = promedio de l_t en las demás centrales que cotizan el producto; T_t = ln toneladas.
DEF = {
    "cambio_1m": r"$l_t-l_{t-1}$", "cambio_2m": r"$l_t-l_{t-2}$", "cambio_3m": r"$l_t-l_{t-3}$", "cambio_6m": r"$l_t-l_{t-6}$", "cambio_12m": r"$l_t-l_{t-12}$",
    "cambio_mes_rez1": r"$r_{t-1}$", "cambio_mes_rez2": r"$r_{t-2}$", "cambio_mes_rez3": r"$r_{t-3}$",
    "vol_3m": r"desv. típica de $r$ en $t-2,\dots,t$", "vol_6m": r"desv. típica de $r$ en $t-5,\dots,t$", "vol_12m": r"desv. típica de $r$ en $t-11,\dots,t$",
    "z_precio_12m": r"$(l_t-\bar l_{12})/s_{12}$, media y desv. de $l$ en 12 meses", "dist_max_12m": r"$l_t-\max_{12}l$", "dist_min_12m": r"$l_t-\min_{12}l$",
    "alzas_12m": r"$\sum_{k=0}^{11}a_{t-k}$", "meses_desde_alza": r"meses desde el último $a=1$ (tope 24)",
    "mes_sin": r"$\sin(2\pi m_{t+1}/12)$", "mes_cos": r"$\cos(2\pi m_{t+1}/12)$",
    "frec_alza_hist": r"$(k+1)/(n+6)$: alzas $k$ del producto en el mes $m_{t+1}$ en $n$ registros de años anteriores",
    "cambio_estacional_hist": r"media de $r$ de la serie en el mes $m_{t+1}$ en años anteriores",
    "cambio_ton_1m": r"$T_t-T_{t-1}$", "cambio_ton_12m": r"$T_t-T_{t-12}$", "ton_rel_12m": r"$T_t-$ media de $T$ en $t-12,\dots,t-1$",
    "log_municipios": r"$\ln(1+$municipios de origen$)$", "departamentos": "departamentos de origen", "dias_registro": "días con registro de toneladas",
    "brecha_nacional": r"$l_t-o_t$", "cambio_nacional_1m": r"$o_t-o_{t-1}$", "prop_centrales_alza": r"proporción de las demás centrales con $a_t=1$",
    "semana_santa": r"1 si Semana Santa cae en $t+1$", "diciembre": r"1 si $t+1$ es diciembre",
    "perecibilidad": "0 granos y procesados; 1 tubérculos, lácteos y pescados; 2 frutas y verduras",
    "grupo_c": "código entero del grupo", "ciudad_c": "código entero de la ciudad", "mercado_c": "código entero de la central", "alimento_c": "código entero del producto",
    "oni": r"ONI de $t-2$", "oni_cambio_3m": r"ONI$_{t-2}-$ONI$_{t-5}$",
    "desv_ma3": r"$l_t-$ media de $l$ en 3 meses", "desv_ma6": r"$l_t-$ media de $l$ en 6 meses",
    "cambio_mismo_mes_ano_ant": r"$r_{t-10}$ (cambio del mes objetivo un año antes)", "cambio_nacional_mismo_mes_ano_ant": r"$o_{t-10}-o_{t-11}$",
    "cambio_nacional_2m": r"$o_t-o_{t-2}$", "cambio_nacional_12m": r"$o_t-o_{t-12}$", "brecha_nacional_cambio": r"$(l_t-o_t)-(l_{t-1}-o_{t-1})$",
    "cambio_grupo_central": r"media de $r_t$ de los demás productos del grupo en la central", "alzas_grupo_central": r"proporción de $a_t=1$ en los demás productos del grupo en la central",
    "cambio_ton_nacional_1m": r"cambio de $\ln$ toneladas del producto en todas las centrales", "ton_nacional_rel_12m": r"$\ln$ toneladas en todas las centrales frente a su media de 12 meses",
    "participacion_central": "toneladas de la central / toneladas en todas las centrales", "dias_registro_rel": "días con registro frente a su media de 12 meses",
    "meses_obs_12m": "meses con precio observado en $t-11,\\dots,t$",
}
fin = set(variables_finales())
bloques = {**BLOQUES_BASE, **BLOQUES_NUEVOS}
filas = []
for b, vs in bloques.items():
    for i, v in enumerate(vs):
        filas.append(f"{b if i == 0 else ''} & {NOMBRES[v]} & {DEF[v]} & {'Sí' if v in fin else 'No'} \\\\")
    filas.append(r"\addlinespace[2pt]")
assert sum(len(v) for v in bloques.values()) == 52 and fin <= set(DEF)
tex = r"""\footnotesize
\begin{longtable}{>{\raggedright\arraybackslash}p{2.3cm}>{\raggedright\arraybackslash}p{4.1cm}>{\raggedright\arraybackslash}p{6.2cm}c}
\caption{Definición de las 52 variables candidatas. Notación: $l_t=\ln p_t$ con el último precio repetido en huecos de hasta dos meses; $r_t=l_t-l_{t-1}$; $a_t=1\{r_t>\ln 1{,}15\}$; $o_t$, promedio de $l_t$ en las demás centrales que cotizan el producto; $T_t$, logaritmo de las toneladas; $m_{t+1}$, mes del año pronosticado. Las ventanas móviles exigen al menos tres cuartas partes de los meses. Final: variable incluida en los modelos.}\label{tab:variables}\\
\toprule Bloque & Variable & Definición & Final\\ \midrule\endfirsthead
\toprule Bloque & Variable & Definición & Final\\ \midrule\endhead
\bottomrule\endfoot
""" + "\n".join(filas[:-1]) + "\n\\end{longtable}\n\\normalsize\n"
Path(RAIZ.parent / "tesis" / "Tablas" / "tab_variables.tex").write_text(tex)
print("tab_variables lista:", len(filas))
