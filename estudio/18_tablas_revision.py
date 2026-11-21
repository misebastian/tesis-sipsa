"""Paso 18. Tablas, cifras y figuras de la revisión (se ejecuta después de 08_latex.py, 15_revision.py y 17_atipicos.py).
Escribe en ../tesis/Tablas: tab_muestras, tab_embudo, tab_sarima_error, tab_adf, tab_reg_extra, tab_clf_extra, tab_lineales,
tab_cobertura, tab_robustez (agrega filas) y cifras_revision.tex; y las figuras fig_busqueda y fig_cobertura."""
import sys, json, shutil, re
from pathlib import Path
import numpy as np, pandas as pd
from comun import *
from estilo import ACENTO, OSCURO, CLARO, SUAVE as SUAVE_, ANCHO, eje_coma, coma
import estilo
DEST = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ.parent / "tesis"
TAB, FIGD = DEST / "Tablas", DEST / "Figures"
S = leer_json("revision.json"); R = leer_json("resultados.json"); RS, CS = leer_json("reg_seleccion.json"), leer_json("clf_seleccion.json")
EX = leer_json("explicaciones.json"); AT = leer_json("atipicos_sensibilidad.json"); CP = leer_json("complementos.json"); EC_ = leer_json("eda_calidad.json")
ER, EC = RS["elegido"], CS["elegido"]; P = cargar_panel()


def n(x, d=2):
    if x is None or (isinstance(x, float) and np.isnan(x)): return "--"
    s = f"{abs(x):,.{d}f}".replace(",", "X").replace(".", "{,}").replace("X", ".")
    return ("\\ensuremath{-}" + s) if x < 0 and float(s.replace(".", "").replace("{,}", ".")) != 0 else s


esc = lambda s: str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
ici = lambda a, k=100, d=1: f"[{n(a[0] * k, d)}; {n(a[1] * k, d)}]"


def escribir(nombre, texto):
    if r"\begin{tabular}" in texto and "adjustbox" not in texto:
        texto = texto.replace(r"\begin{tabular}", r"\begin{adjustbox}{max width=\textwidth}\begin{tabular}", 1).replace(r"\end{tabular}", r"\end{tabular}\end{adjustbox}", 1)
    (TAB / f"{nombre}.tex").write_text(texto, encoding="utf-8")


cif = {}
# ---------- muestras ----------
M = S["muestras"]; f = [f"Desarrollo & feb-2019 a dic-2024 & {n(M['desarrollo']['n'], 0)} & {n(M['desarrollo']['alza'] * 100, 1)} \\\\"]
for a in M["validacion"]:
    f.append(f"\\quad Validación {a['ano']} (ajuste hasta dic-{a['ano'] - 1}) & ene-{a['ano']} a dic-{a['ano']} & {n(a['n'], 0)} & {n(a['alza'] * 100, 1)} \\\\")
f.append(f"Prueba & ene-2025 a sep-2026 & {n(M['prueba']['n'], 0)} & {n(M['prueba']['alza'] * 100, 1)} \\\\")
escribir("tab_muestras", r"""\begin{table}[htbp]\centering\small
\caption{Muestras del estudio según el mes pronosticado. Todas las decisiones usan la muestra de desarrollo, con validación por origen móvil en 2022, 2023 y 2024 (en cada año, los modelos se estiman con los meses anteriores); la prueba se evalúa una sola vez.}\label{tab:muestras}
\begin{tabular}{llrr}\toprule
Muestra & Meses pronosticados & Observaciones & Alzas mayores al 15\,\% (\%)\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")

# ---------- embudo ----------
B = pd.read_parquet(DATOS / "base_unida_mensual.parquet"); co = EC_["composicion"]
bk = B[B.unidad == "$/kg"]; ser = lambda d: d[["mercado", "alimento"]].drop_duplicates().shape[0]
f = [("Registros de la base unida (2018--2026)", n(len(B), 0), n(ser(B), 0)),
     ("\\quad Sin precio (solo abastecimiento)", n(co["Solo abastecimiento"], 0), n(ser(B[B.precio.isna()]), 0)),
     ("\\quad Precio en otra unidad (atado, docena, bulto, etc.)", n(co["Precio en otra unidad"], 0), n(ser(B[B.precio.notna() & (B.unidad != "$/kg")]), 0)),
     ("Con precio en pesos por kilogramo", n(len(bk), 0), n(ser(bk), 0)),
     ("Series con al menos 48 meses con precio hasta 2024", n(int(bk.merge(P[["mercado", "alimento"]].drop_duplicates()).shape[0]), 0), n(ser(P), 0)),
     ("Con precio observado en $t$, $t+1$ y $t-12$ (panel)", n(len(P), 0), n(ser(P), 0))]
escribir("tab_embudo", r"""\begin{table}[htbp]\centering\small
\caption{De la base del SIPSA al panel de análisis. Una serie puede aparecer en varias filas, porque un mismo producto puede tener meses con y sin precio. Las carnes no se incluyen en la base unida (sección~\ref{sec:carga}).}\label{tab:embudo}
\begin{tabular}{lrr}\toprule
Paso & Registros & Series\\ \midrule
""" + "\n".join(f"{a} & {b} & {c} \\\\" for a, b, c in f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")

# ---------- SARIMA: misma definición que la tabla principal ----------
SA = pd.read_parquet(RES / "sarima.parquet"); SA["mes_obj"] = pd.to_datetime(SA.mes_obj)
filas_g, filas_a = {}, []
def err(b, corte):
    s = SA[SA.corte == corte].set_index(["mercado", "alimento", "mes_obj"]).pred
    ps = np.nan_to_num(s.reindex(pd.MultiIndex.from_frame(b[["mercado", "alimento", "mes_obj"]])).values)
    return b.assign(es=np.abs(b.y - ps), er=np.abs(b.y), g=b.grupo.map(GRUPOS))
V_ = [err(P[(P.mes_obj > x) & (P.mes_obj <= y_)], f"cv{k}") for k, (x, y_) in enumerate(CORTES_CV)]
T_ = err(P[P.muestra == "prueba"], "prueba")
gv = pd.concat([v.groupby("g")[["es", "er"]].mean() for v in V_]).groupby(level=0).mean(); gt = T_.groupby("g")[["es", "er"]].mean()
tv = pd.DataFrame([v[["es", "er"]].mean() for v in V_]).mean(); tt = T_[["es", "er"]].mean()
red = lambda a: n((1 - a.es / a.er) * 100, 1)
f = [f"Todo el panel & {n(tv.er * 100, 2)} & {n(tv.es * 100, 2)} & {red(tv)} & {n(tt.er * 100, 2)} & {n(tt.es * 100, 2)} & {red(tt)} \\\\ \\midrule"]
for g in gt.sort_values("er", ascending=False).index:
    f.append(f"{esc(g)} & {n(gv.loc[g].er * 100, 2)} & {n(gv.loc[g].es * 100, 2)} & {red(gv.loc[g])} & {n(gt.loc[g].er * 100, 2)} & {n(gt.loc[g].es * 100, 2)} & {red(gt.loc[g])} \\\\")
f.append(r"\midrule \multicolumn{7}{l}{\emph{Validación por año (todo el panel)}}\\")
for k, v in enumerate(V_):
    a = v[["es", "er"]].mean(); f.append(f"\\quad {2022 + k} & {n(a.er * 100, 2)} & {n(a.es * 100, 2)} & {red(a)} & & & \\\\")
escribir("tab_sarima_error", r"""\begin{table}[htbp]\centering\small
\caption{MAE (puntos porcentuales) del último precio y del SARIMA y reducción del error del SARIMA (\%). Validación: promedio de los MAE de 2022, 2023 y 2024, con la misma definición que la tabla~\ref{tab:reg} (donde el SARIMA no pudo estimarse se usa el último precio).}\label{tab:sarima_error}
\begin{tabular}{lrrrrrr}\toprule
& \multicolumn{3}{c}{Validación} & \multicolumn{3}{c}{Prueba}\\ \cmidrule(lr){2-4}\cmidrule(lr){5-7}
Grupo & Últ. precio & SARIMA & Reducción & Últ. precio & SARIMA & Reducción\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
for k, a in enumerate(S["sarima_ano"]): cif[f"sar{['a', 'b', 'c'][k]}"] = n((1 - a["mae_sarima"] / a["mae_rw"]) * 100, 1)
cif["sardisp"] = n(S["sarima_ano"][0]["disponible"] * 100, 1)
cif["saraabs"] = n(abs(1 - S["sarima_ano"][0]["mae_sarima"] / S["sarima_ano"][0]["mae_rw"]) * 100, 1)   # para "un X % mayor"

# ---------- ADF y KPSS ----------
K = S["kpss"]; A = EX["adf"]
escribir("tab_adf", r"""\begin{table}[htbp]\centering\small
\caption{Pruebas de raíz unitaria (Dickey--Fuller aumentada, $H_0$: raíz unitaria) y de estacionariedad (KPSS, $H_0$: estacionariedad) en las """ + n(A["series"], 0) + r""" series con al menos cinco años de datos, al 5\,\% y sin ajuste por multiplicidad}\label{tab:adf}
\begin{tabular}{llr}\toprule
Serie y prueba & Componentes & Series (\%)\\ \midrule
\multicolumn{3}{l}{\emph{Logaritmo del precio}}\\
\quad ADF: no rechaza la raíz unitaria & constante y tendencia & """ + n((1 - A["rechaza_nivel"]) * 100, 1) + r""" \\
\quad KPSS: rechaza la estacionariedad & constante y tendencia & """ + n(K["kpss_rech"] * 100, 1) + r""" \\
\quad Ambas indican raíz unitaria & & """ + n(K["ambas_raiz"] * 100, 1) + r""" \\
\quad Ambas indican estacionariedad alrededor de una tendencia & & """ + n(K["ambas_est"] * 100, 1) + r""" \\
\multicolumn{3}{l}{\emph{Cambio mensual}}\\
\quad ADF: rechaza la raíz unitaria & constante & """ + n(A["rechaza_cambio"] * 100, 1) + r""" \\
\quad KPSS: rechaza la estacionariedad & constante & """ + n(K["kpss_rech_cambio"] * 100, 1) + r""" \\
\bottomrule\end{tabular}\end{table}
""")
cif.update(kpssrech=n(K["kpss_rech"] * 100, 1), kpssambas=n(K["ambas_raiz"] * 100, 1), kpssest=n(K["ambas_est"] * 100, 1), adfno=n((1 - A["rechaza_nivel"]) * 100, 1))

# ---------- métricas complementarias de regresión ----------
TR = pd.DataFrame(R["reg_tabla"]).set_index("modelo"); RX = S["reg_extra"]
f = []
for m in ["Paseo aleatorio", "AR estacional", "SARIMA"] + RS["modelos"]:
    r, x = TR.loc[m], RX[m]
    f.append(f"{esc(m)}" + (r"$^\ast$" if m == ER else "") + f" & {n(r.mae * 100, 2)} & {n(r.rmse * 100, 2)} & {n(r.mase, 3)} & {n(x['avgrelmae'], 3)} & {n(x['reduccion_media_grupos'] * 100, 1)} & " + ("--" if m == "Paseo aleatorio" else n(r.series_gana * 100, 0)) + " \\\\")
    if m == "SARIMA": f.append(r"\midrule")
E = S["ensamble"]; IR = S["intervalos_resumen"]
f.append(r"\midrule")
f.append(f"Promedio de XGBoost, LightGBM y CatBoost & {n(E['mae'], 2)} & -- & -- & -- & -- & -- \\\\")
f.append(f"LightGBM cuantílico (mediana) & {n(IR['mae_mediana'], 2)} & -- & -- & -- & -- & -- \\\\")
escribir("tab_reg_extra", r"""\begin{table}[htbp]\centering\small
\caption{Métricas complementarias del pronóstico del cambio en la prueba: MAE y RMSE (puntos porcentuales), MASE (escala: MAE del último precio de cada serie en entrenamiento), media geométrica del MAE relativo al último precio por serie (AvgRelMAE; menor que 1 indica mejora en la serie típica), promedio simple de las reducciones del error por grupo (\%) y porcentaje de series en que el modelo tiene menor MAE que el último precio. $^\ast$Modelo elegido.}\label{tab:reg_extra}
\begin{tabular}{lrrrrrr}\toprule
Modelo & MAE & RMSE & MASE & AvgRelMAE & Red. media por grupo & Series que gana\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
cif.update(avgrel=n(RX[ER]["avgrelmae"], 3), redgrupos=n(RX[ER]["reduccion_media_grupos"] * 100, 1), redgruposlin=n(RX["Regresión cuantílica"]["reduccion_media_grupos"] * 100, 1),
           razongrupos=n(RX[ER]["razon_medias_grupos"] * 100, 1), razongruposlin=n(RX["Regresión cuantílica"]["razon_medias_grupos"] * 100, 1),
           rmsecat=n(RX[ER]["rmse"], 2), rmserw=n(RX["Paseo aleatorio"]["rmse"], 2), ensmae=n(E["mae"], 2), ensred=n(E["reduccion"] * 100, 1), ensredic=ici(E["ic"]),
           ensap=n(E["ap"], 3), ensapic=ici(E["ap_ic"], 1, 3), ensdif=n(E["d_mae_vs_cat"], 3), ensdific=ici(E["d_mae_ic"], 1, 3), qmae=n(IR["mae_mediana"], 2),
           qred=n(IR["mae_mediana_reduccion"] * 100, 1), pinball=n(IR["pinball"], 2), cruces=n(IR["cruces"] * 100, 1))

# ---------- calibración y reglas de puntuación ----------
CX = S["clf_extra"]; f = []
for m in CS["modelos"] + ["SARIMA", "Frecuencia histórica", "Logística autorregresiva"]:
    x = CX[m]
    if m == "SARIMA": f.append(r"\midrule")
    f.append(f"{esc(m)}" + (r"$^\ast$" if m == EC else "") + f" & {n(x['brier'], 4)} {ici(x['brier_ic'], 1, 4)} & " + ("--" if m == "Frecuencia histórica" else f"{n(x['bss'] * 100, 1)} {ici(x['bss_ic'])}") +
             f" & {n(x['logloss'], 3)} & {n(x['intercepto'], 2)} & {n(x['pendiente'], 2)} {ici(x['pendiente_ic'], 1, 2)} & {n(x['ece'] * 100, 1)} \\\\")
escribir("tab_clf_extra", r"""\begin{table}[htbp]\centering\small
\caption{Reglas de puntuación propias y calibración de las probabilidades en la prueba: puntaje de Brier, \emph{Brier skill score} frente a la frecuencia histórica (BSS, \%), pérdida logarítmica, intercepto (con pendiente fija en 1) y pendiente de calibración, y error esperado de calibración por deciles (ECE, puntos porcentuales). Entre corchetes, intervalos bootstrap por bloques de meses al 95\,\%. $^\ast$Modelo elegido.}\label{tab:clf_extra}
\begin{tabular}{lrrrrrr}\toprule
Modelo & Brier & BSS (\%) & Log-loss & Intercepto & Pendiente & ECE\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
x = CX[EC]; cif.update(brier=n(x["brier"], 4), bss=n(x["bss"] * 100, 1), bssic=ici(x["bss_ic"]), pend=n(x["pendiente"], 2), pendic=ici(x["pendiente_ic"], 1, 2),
                       intercal=n(x["intercepto"], 2), ece=n(x["ece"] * 100, 1), logloss=n(x["logloss"], 3), brierfh=n(CX["Frecuencia histórica"]["brier"], 4),
                       pendsar=n(CX["SARIMA"]["pendiente"], 2))

# ---------- modelos lineales y red con otra codificación ----------
L = pd.DataFrame(S["lineales"]); f = []
for cfg in L.config.unique():
    d = L[L.config == cfg].set_index(["tarea", "modelo"])
    g = lambda t, m, k: (f"{n(d.loc[(t, m), k] * (100 if k == 'reduccion' else 1), 1 if k == 'reduccion' else 3)}" if (t, m) in d.index else "--")
    f.append(f"{esc(cfg)} & {int(d.columnas.iloc[0])} & {g('Cambio', 'Regresión cuantílica', 'reduccion')} & {g('Cambio', 'MLP', 'reduccion')} & {g('Alzas', 'Regresión logística', 'ap')} & {g('Alzas', 'MLP', 'ap')} \\\\")
TC = pd.DataFrame(R["clf_tabla"]).set_index("modelo")
f.append(r"\midrule")
f.append(f"Referencia: {esc(ER)} y {esc(EC)} & -- & \\multicolumn{{2}}{{c}}{{{n(TR.loc[ER].mejora * 100, 1)}}} & \\multicolumn{{2}}{{c}}{{{n(TC.loc[EC].pr_auc, 3)}}} \\\\")
escribir("tab_lineales", r"""\begin{table}[htbp]\centering\small
\caption{Robustez de los modelos lineales y de la red neuronal en la prueba, con los hiperparámetros elegidos en validación: reducción del error frente al último precio (\%) y AP. Las variables categóricas entran como indicadores (\emph{one-hot}); las numéricas, estandarizadas con los datos de ajuste.}\label{tab:lineales}
\begin{tabular}{lrrrrr}\toprule
& & \multicolumn{2}{c}{Reducción del error (\%)} & \multicolumn{2}{c}{AP}\\ \cmidrule(lr){3-4}\cmidrule(lr){5-6}
Especificación & Columnas & Reg. cuantílica & MLP & Reg. logística & MLP\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
gl = lambda cfg, t, m, k: float(L[(L.config.str.startswith(cfg)) & (L.tarea == t) & (L.modelo == m)][k].iloc[0])
cif.update(linoh=n(gl("Indicadores de grupo, producto, central y ciudad; 24", "Cambio", "Regresión cuantílica", "reduccion") * 100, 1),
           lincand=n(gl("Indicadores de grupo, producto, central y ciudad; 52", "Cambio", "Regresión cuantílica", "reduccion") * 100, 1),
           lininter=n(gl("Interacciones", "Cambio", "Regresión cuantílica", "reduccion") * 100, 1),
           lininterap=n(gl("Interacciones", "Alzas", "Regresión logística", "ap"), 3),
           mlpoh=n(gl("Indicadores de grupo, producto, central y ciudad; 24", "Cambio", "MLP", "reduccion") * 100, 1))

# ---------- cobertura por volatilidad ----------
CV = pd.read_csv(RES / "revision_cobertura_volatilidad.csv"); f = []
w = CV.pivot(index="decil", columns="intervalo", values="cobertura"); a_ = CV.pivot(index="decil", columns="intervalo", values="ancho"); vm = CV.groupby("decil").vol_media.first()
for d in w.index:
    f.append(f"{d} & {n(vm[d], 1)} & {n(w.loc[d, 'Cuantiles 90'] * 100, 1)} & {n(w.loc[d, 'CQR por grupo 90'] * 100, 1)} & {n(a_.loc[d, 'CQR por grupo 90'], 1)} & {n(w.loc[d, 'Cuantiles 80'] * 100, 1)} & {n(w.loc[d, 'CQR por grupo 80'] * 100, 1)} \\\\")
I = S["intervalos"]
f.append(r"\midrule" + f" Todos & -- & {n(I['Cuantiles 90']['cobertura'] * 100, 1)} & {n(I['CQR por grupo 90']['cobertura'] * 100, 1)} & {n(I['CQR por grupo 90']['ancho'], 1)} & {n(I['Cuantiles 80']['cobertura'] * 100, 1)} & {n(I['CQR por grupo 80']['cobertura'] * 100, 1)} \\\\")
f.append(f"Puntaje de intervalo & -- & {n(I['Cuantiles 90']['puntaje'], 1)} & {n(I['CQR por grupo 90']['puntaje'], 1)} & -- & {n(I['Cuantiles 80']['puntaje'], 1)} & {n(I['CQR por grupo 80']['puntaje'], 1)} \\\\")
escribir("tab_cobertura", r"""\begin{table}[htbp]\centering\small
\caption{Cobertura condicional de los intervalos en la prueba por decil de volatilidad de los últimos doce meses (1 = series más estables): volatilidad media (p.~p.), cobertura (\%) de los cuantiles estimados y de la calibración conforme por grupo, y ancho medio del intervalo conforme del 90\,\% (p.~p.). La última fila da el puntaje de intervalo de \citet{gneiting2007} (menor es mejor).}\label{tab:cobertura}
\begin{tabular}{lrrrrrr}\toprule
& & \multicolumn{3}{c}{Intervalo del 90\,\%} & \multicolumn{2}{c}{Intervalo del 80\,\%}\\ \cmidrule(lr){3-5}\cmidrule(lr){6-7}
Decil & Volatilidad & Cuantiles & Conforme & Ancho & Cuantiles & Conforme\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
cif.update(cobdecuno=n(w.loc[1, "CQR por grupo 90"] * 100, 1), cobdecdiez=n(w.loc[10, "CQR por grupo 90"] * 100, 1), anchdecuno=n(a_.loc[1, "CQR por grupo 90"], 1), anchdecdiez=n(a_.loc[10, "CQR por grupo 90"], 1))

# ---------- robustez: filas nuevas ----------
H2, WK, BT = S["horizonte2"], S["working"], S["bootstrap"]
nuevas = [("Bootstrap estacionario ($B=10\\,000$)", ici(BT["estacionario_10000"]), "--"),
          (f"Frente a la referencia $\\hat y=0{{,}}25\\,r_t$ (Working)", f"{n(WK['red_cat_vs_ar025'] * 100, 1)} {ici(WK['red_cat_vs_ar025_ic'])}", "--"),
          ("Promedio de XGBoost, LightGBM y CatBoost", f"{n(E['reduccion'] * 100, 1)} {ici(E['ic'])}", f"{n(E['ap'], 3)} {ici(E['ap_ic'], 1, 3)}"),
          ("Cambio de $t+1$ a $t+2$ con información de $t$", f"{n(H2['reduccion'] * 100, 1)} {ici(H2['reduccion_ic'])}", f"{n(H2['ap'], 3)} {ici(H2['ap_ic'], 1, 3)}")]
t = (TAB / "tab_robustez.tex").read_text()
t = re.sub(r"\\midrule\nBootstrap estacionario.*?(?=\\bottomrule)", "", t, flags=re.S)   # quita filas de una corrida anterior
t = t.replace("\\bottomrule", "\\midrule\n" + "\n".join(f"{a} & {b} & {c} \\\\" for a, b, c in nuevas) + "\n\\bottomrule", 1)
(TAB / "tab_robustez.tex").write_text(t)
cif.update(hdosred=n(H2["reduccion"] * 100, 1), hdosredic=ici(H2["reduccion_ic"]), hdosap=n(H2["ap"], 3), hdosapic=ici(H2["ap_ic"], 1, 3), hdosfrec=n(H2["ap_frec"], 3),
           hdosdif=n(H2["d_ap_frec"], 3), hdosdific=ici(H2["d_ap_frec_ic"], 1, 3), hdostasa=n(H2["tasa"] * 100, 1), hdosauc=n(H2["auc"], 3),
           hdosfru=n(H2["por_grupo"]["Frutas"] * 100, 1), hdosver=n(H2["por_grupo"]["Verduras y hortalizas"] * 100, 1),
           wkar=n(WK["red_ar025"] * 100, 1), wkarabs=n(-WK["red_ar025"] * 100, 1), wkcat=n(WK["red_cat_vs_ar025"] * 100, 1), wkcatic=ici(WK["red_cat_vs_ar025_ic"]), wkpropio=n(WK["corr_propio"], 3),
           wknac=n(WK["corr_nacional"], 3), wkparcial=n(WK["corr_parcial_nacional"], 3),
           btbloq=ici(BT["bloques_10000"]), btest=ici(BT["estacionario_10000"]))

# ---------- deriva, atípicos, ONI, variedades, casos ----------
AD = S["adversaria"]; cif.update(advy=n(AD["solo_y"], 3), advx=n(AD["auc"], 2))
ks = S["ks"]; cif.update(ksfru=n(ks["Frutas"]["ks"], 3), ksver=n(ks["Verduras y hortalizas"]["ks"], 3), ksgra=n(ks["Granos y cereales"]["ks"], 3),
                         sdfrudes=n(ks["Frutas"]["sd_des"], 1), sdfrupru=n(ks["Frutas"]["sd_pru"], 1), sdverdes=n(ks["Verduras y hortalizas"]["sd_des"], 1), sdverpru=n(ks["Verduras y hortalizas"]["sd_pru"], 1))
sd = S["sd_ene_sep"]; cif.update(sdveinticinco=n(sd["2025"], 1), sdveintiseis=n(sd["2026"], 1), sdmin=n(min(v for k, v in sd.items() if k < "2025"), 1), sdmax=n(max(v for k, v in sd.items() if k < "2025"), 1))
cif.update(atcentdos=n(AT["centrada_2"]["casos"], 0), atcentdosais=n(AT["centrada_2"]["aislados"], 0), atcenttres=n(AT["centrada_3"]["casos"], 0), atcenttresais=n(AT["centrada_3"]["aislados"], 0),
           atcaustres=n(AT["causal_3"]["casos"], 0), atcaustresais=n(AT["causal_3"]["aislados"], 0), atcauscuatro=n(AT["causal_4"]["casos"], 0))
VA = S["variedades"]; cif.update(varser=n(VA["series_equivalencia"], 0), varpct=n(VA["series_equivalencia"] / VA["series"] * 100, 1), varprod=n(len(VA["productos"]), 0))
cif.update(mangomax=n(S["mango_feb25"]["por_debajo_max"] * 100, 0), apiorw=n(S["apio"]["mae_rw"], 1), apiocat=n(S["apio"]["mae_cat"], 1), apiodes=n(S["apio"]["mae_rw_des"], 1))
s_ = CP["sarima"]; cif["lbesperado"] = n(95 - s_["lb12"] * 100, 1); cif["lbdoce"] = n(s_["lb12"] * 100, 1)
(TAB / "cifras_revision.tex").write_text("% Cifras de la revisión, generadas por 18_tablas_revision.py\n" + "\n".join(f"\\newcommand{{\\rv{k}}}{{{v}}}" for k, v in cif.items()) + "\n", encoding="utf-8")

# ---------- figura: convergencia de la búsqueda ----------
import matplotlib.pyplot as plt
rb, cb = leer_json("reg_busqueda.json"), leer_json("clf_busqueda.json")
fig, axs = plt.subplots(1, 2, figsize=(ANCHO, 2.6))
tonos = [OSCURO, "#6b7b8c", "#9aa59f", "#c9a27e", ACENTO, "#7a4f2a"]
for ax, d, k, tit in ((axs[0], rb, 100, "a) Regresión: mejor MAE (p. p.)"), (axs[1], cb, 1, "b) Clasificación: mejor AP")):
    for (m, v), c in zip(d.items(), tonos):
        cur = np.array(v["curva"]) * k; ax.plot(np.arange(1, len(cur) + 1), cur, color=c, lw=1.2, label=m)
    ax.set_title(tit); ax.set_xlabel("Configuraciones evaluadas"); eje_coma(ax, "y", 2 if k == 100 else 3)
axs[1].legend(fontsize=6.5, loc="lower right", ncol=1)
fig.tight_layout(w_pad=1.2); estilo.guardar(fig, "fig_busqueda")
shutil.copy(FIG / "fig_busqueda.pdf", FIGD / "fig_busqueda.pdf")
print(len(cif), "cifras de revisión")
