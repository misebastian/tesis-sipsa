"""Paso 8. Genera las tablas (Tablas/*.tex) y las cifras (Tablas/cifras.tex) del documento LaTeX a partir de los resultados.
Uso: python 08_latex.py <carpeta del proyecto LaTeX>"""
import sys, json, shutil
from pathlib import Path
import numpy as np, pandas as pd
from comun import *
DEST = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ.parent / "tesis"
TAB, FIGD = DEST / "Tablas", DEST / "Figures"; TAB.mkdir(parents=True, exist_ok=True); FIGD.mkdir(exist_ok=True)
J = lambda f: leer_json(f) if (RES / f).exists() else {}
EG, EC_, VF, RS, CS, R, CO = J("eda_general.json"), J("eda_calidad.json"), J("variables_finales.json"), J("reg_seleccion.json"), J("clf_seleccion.json"), J("resultados.json"), J("complementarios.json")


def n(x, d=2):
    """Número con coma decimal y punto de miles para LaTeX."""
    if x is None or (isinstance(x, float) and np.isnan(x)): return "--"
    s = f"{abs(x):,.{d}f}".replace(",", "X").replace(".", "{,}").replace("X", ".")
    return ("\\ensuremath{-}" + s) if x < 0 and float(s.replace(".", "").replace("{,}", ".")) != 0 else s


def esc(s): return str(s).replace("−", "--").replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace('"', "")


def pv(p):
    if p is None or np.isnan(p): return "--"
    return "$<0{,}001$" if p < .001 else n(p, 3)


cif = {}
def C(nombre, valor): cif[nombre] = valor


def escribir(nombre, texto):
    if r"\begin{tabular}" in texto and "adjustbox" not in texto:   # ajusta al ancho de página
        texto = texto.replace(r"\begin{tabular}", r"\begin{adjustbox}{max width=\textwidth}\begin{tabular}", 1).replace(r"\end{tabular}", r"\end{tabular}\end{adjustbox}", 1)
    (TAB / f"{nombre}.tex").write_text(texto, encoding="utf-8")


# ---------- caracterización de variables ----------
P = cargar_panel(); tr = P[P.muestra == "entrenamiento"]
final = set(VF["variables"]); noinf = set(VF["no_informativas"]) if VF["acepta_etapa3"] else set()
redu = {d["sale"] for d in VF["redundancia"]} if VF["acepta_etapa4"] else set()
filas = []
for b, vs in {**BLOQUES_BASE, **BLOQUES_NUEVOS}.items():
    for v in vs:
        if v in final: est = "Sí"
        elif b in VF["bloques_retirados"]: est = "No (bloque)"
        elif b in BLOQUES_NUEVOS and b not in VF["bloques_anadidos"]: est = "No (no entra)"
        elif v in noinf: est = "No (no inform.)"
        elif v in redu: est = "No (redundante)"
        else: est = "No"
        x = tr[v]
        filas.append(f"{esc(b) if v == vs[0] else ''} & {esc(NOMBRES[v])} & {n(x.mean(), 3)} & {n(x.std(), 3)} & {n(x.isna().mean() * 100, 1)} & {est} \\\\")
    filas.append(r"\addlinespace[2pt]")
escribir("tab_variables", r"""\footnotesize
\begin{longtable}{p{2.2cm}p{4.4cm}rrrl}
\caption{Variables candidatas: media, desviación típica y porcentaje de faltantes en entrenamiento, y decisión de la selección}\label{tab:variables}\\
\toprule Bloque & Variable & Media & D.\,t. & \% falt. & Final\\ \midrule\endfirsthead
\toprule Bloque & Variable & Media & D.\,t. & \% falt. & Final\\ \midrule\endhead
\bottomrule\endfoot
""" + "\n".join(filas) + "\n\\end{longtable}\n\\normalsize\n")

# ---------- selección de bloques ----------
f = [f"{esc(p['paso'])} & {p['n']} & {n(p['mae'], 3)} & {n(p['d_mae'], 3)} [{n(p['mae_lo'], 3)}; {n(p['mae_hi'], 3)}] & {n(p['pr'], 4)} & {n(p['d_pr'], 4)} [{n(p['pr_lo'], 4)}; {n(p['pr_hi'], 4)}] \\\\" for p in VF["pasos"]]
escribir("tab_pasos", r"""\begin{table}[htbp]\centering\small
\caption{Resultado de cada etapa de la selección en validación (predicciones fuera de muestra de 2023 y 2024; LightGBM, promedio de tres semillas); diferencias frente a la base con IC al 95\,\%}\label{tab:pasos}
\begin{tabular}{lrrrrr}\toprule
Paso & Var. & MAE & $\Delta$ [IC 95\,\%] & PR-AUC & $\Delta$ [IC 95\,\%] \\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
C("nfinal", len(VF["variables"]))
pasos = {p["paso"]: p for p in VF["pasos"]}
D = pd.read_csv(RES / "seleccion_bloques.csv").set_index("config")
C("selmaelo", n(D.iloc[1:7].d_mae.min(), 3)); C("selmaehi", n(D.iloc[1:7].d_mae.max(), 3))

if R:
    ER, EC = RS["elegido"], CS["elegido"]; MR, MC = RS["modelos"], CS["modelos"]
    # ---------- regresión ----------
    T = pd.DataFrame(R["reg_tabla"]).set_index("modelo")
    orden = ["Paseo aleatorio", "AR estacional", "SARIMA"] + MR; T = T.loc[orden].reset_index()
    f = []
    for r in T.itertuples():
        nom = esc(r.modelo) + (r"$^\dagger$" if r.modelo == ER else "")
        mej = "--" if r.modelo == "Paseo aleatorio" else f"{n(r.mejora * 100, 1)} [{n(r.mejora_lo * 100, 1)}; {n(r.mejora_hi * 100, 1)}]"
        f.append(f"{nom} & {n(r.mae_val * 100, 2)} & {n(r.mae * 100, 2)} & {n(r.rmse * 100, 2)} & {n(r.mase, 3)} & {mej} & {n(r.mejora_macro * 100, 1) if r.modelo != 'Paseo aleatorio' else '--'} & {pv(getattr(r, 'p_holm', np.nan))} & {n(r.series_gana * 100, 0) if r.modelo != 'Paseo aleatorio' else '--'} \\\\")
        if r.modelo == "SARIMA": f.append(r"\midrule")
    escribir("tab_reg", r"""\begin{table}[htbp]\centering\small
\caption{Regresión del cambio del mes siguiente: MAE promedio de validación (2022--2024) y métricas en prueba (ene-2025 a sep-2026). Mejora = reducción del MAE frente al paseo aleatorio (\%) con IC bootstrap al 95\,\%; Mejora por grupo = misma medida con igual peso para los siete grupos de alimentos; $p$ de Diebold--Mariano frente al paseo aleatorio ajustado por Holm; Series = \% de series con MAE menor que el paseo aleatorio. $^\dagger$Modelo elegido en validación.}\label{tab:reg}
\begin{tabular}{lrrrrrrrr}\toprule
& MAE val. & MAE & RMSE & MASE & Mejora (\%) [IC 95\,\%] & Mejora por grupo (\%) & $p_{\mathrm{Holm}}$ & Series (\%)\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    t = T.set_index("modelo")
    for m, k in ((ER, "e"), ("Paseo aleatorio", "rw"), ("AR estacional", "ar"), ("SARIMA", "sar"), ("Regresión cuantílica", "lin"), ("MLP", "mlp"), ("Random Forest", "rf"),
                 ("XGBoost", "xgb"), ("LightGBM", "lgb"), ("CatBoost", "cat")):
        if m not in t.index: continue
        C(f"mae_{k}", n(t.loc[m, "mae"] * 100, 2)); C(f"mase_{k}", n(t.loc[m, "mase"], 3))
        if m != "Paseo aleatorio":
            C(f"mej_{k}", n(t.loc[m, "mejora"] * 100, 1)); C(f"mejlo_{k}", n(t.loc[m, "mejora_lo"] * 100, 1)); C(f"mejhi_{k}", n(t.loc[m, "mejora_hi"] * 100, 1))
            C(f"macro_{k}", n(t.loc[m, "mejora_macro"] * 100, 1))
        if m != ER:
            C(f"d_{k}", n(t.loc[m, "d_vs_elegido"], 2)); C(f"dlo_{k}", n(t.loc[m, "d_lo"], 2)); C(f"dhi_{k}", n(t.loc[m, "d_hi"], 2))
            C(f"dlob_{k}", n(t.loc[m, "d_lo_bonf"], 2)); C(f"dhib_{k}", n(t.loc[m, "d_hi_bonf"], 2))
    C("series_e", n(t.loc[ER, "series_gana"] * 100, 0)); C("dir_e", n(t.loc[ER, "direccion"] * 100, 1)); C("phol_e", pv(t.loc[ER, "p_holm"]).replace("$", ""))
    C("meses_gana", R["reg_meses_gana"]); C("n_meses", R["n_meses"]); C("bonf_m", R["bonf_m"])
    # diferencias frente al elegido con IC simultáneos (Bonferroni)
    f = []
    for r in T.itertuples():
        if r.modelo == ER: continue
        f.append(f"{esc(r.modelo)} & {n(r.d_vs_elegido, 2)} & [{n(r.d_lo, 2)}; {n(r.d_hi, 2)}] & [{n(r.d_lo_bonf, 2)}; {n(r.d_hi_bonf, 2)}] \\\\")
    TCd = pd.DataFrame(R["clf_tabla"]).set_index("modelo")
    g_ = []
    for m in TCd.index:
        if m == EC: continue
        rr_ = TCd.loc[m]; g_.append(f"{esc(m)} & {n(rr_.dpr_vs_elegido, 3)} & [{n(rr_.dpr_lo, 3)}; {n(rr_.dpr_hi, 3)}] & [{n(rr_.dpr_lo_bonf, 3)}; {n(rr_.dpr_hi_bonf, 3)}] \\\\")
    escribir("tab_dif", r"""\begin{table}[htbp]\centering\small
\caption{Diferencias frente al modelo elegido en prueba, con IC bootstrap al 95\,\% individuales y simultáneos (Bonferroni). Regresión: MAE del modelo menos MAE de """ + esc(ER) + r""" (p.\,p.; positivo = peor). Clasificación: PR-AUC del modelo menos PR-AUC de """ + esc(EC) + r""" (negativo = peor).}\label{tab:dif}
\begin{tabular}{lrrr}\toprule
\multicolumn{4}{l}{\textit{Regresión}}\\
Modelo & $\Delta$MAE & IC 95\,\% & IC simultáneo\\ \midrule
""" + "\n".join(f) + r"""
\midrule\multicolumn{4}{l}{\textit{Clasificación}}\\
Modelo & $\Delta$PR-AUC & IC 95\,\% & IC simultáneo\\ \midrule
""" + "\n".join(g_) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    G = pd.DataFrame(R["reg_grupo"]).T
    f = [f"{esc(g)} & {int(r.n)} & {n(r.rw * 100, 2)} & {n(r.m * 100, 2)} & {n(r.mejora * 100, 1)} & {pv(r.p_holm)} \\\\" for g, r in G.sort_values("n", ascending=False).iterrows()]
    escribir("tab_reg_grupo", r"""\begin{table}[htbp]\centering\small
\caption{Regresión por grupo de alimentos en prueba: MAE (p.\,p.) del paseo aleatorio y del modelo elegido, mejora relativa y $p$ de Diebold--Mariano ajustado por Holm sobre los siete grupos}\label{tab:reg_grupo}
\begin{tabular}{lrrrrr}\toprule
Grupo & Pronósticos & MAE PA & MAE modelo & Mejora (\%) & $p_{\mathrm{Holm}}$\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    for g, r in G.iterrows():
        k = {"Frutas": "fru", "Verduras y hortalizas": "ver", "Tubérculos y plátanos": "tub", "Granos y cereales": "gra", "Procesados": "pro", "Lácteos y huevos": "lac", "Pescados": "pes"}[g]
        C(f"g_{k}", n(r.mejora * 100, 1)); C(f"gn_{k}", int(r.n)); C(f"gp_{k}", pv(r.p_holm).replace("$", ""))
    # error valorado
    VA = pd.DataFrame(R["valorado"]).set_index("modelo").loc[orden]
    f = [f"{esc(m)} & {n(r.error_mm, 1)} & " + ("--" if m == "Paseo aleatorio" else f"{n(r.mejora * 100, 1)} [{n(r.lo * 100, 1)}; {n(r.hi * 100, 1)}]") + r" \\" for m, r in VA.iterrows()]
    escribir("tab_valorado", r"""\begin{table}[htbp]\centering\small
\caption{Error de pronóstico valorado en prueba: suma de $|\hat p_{t+1}-p_{t+1}|\times q_{t+1}$ (miles de millones de pesos, con $q$ las toneladas ingresadas) y reducción frente al paseo aleatorio con IC bootstrap al 95\,\%. Medida ilustrativa, no un costo de decisión.}\label{tab:valorado}
\begin{tabular}{lrr}\toprule
Modelo & Error valorado & Reducción (\%) [IC 95\,\%]\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    C("val_e", n(VA.loc[ER, "mejora"] * 100, 1)); C("vallo_e", n(VA.loc[ER, "lo"] * 100, 1)); C("valhi_e", n(VA.loc[ER, "hi"] * 100, 1))
    C("val_rw", n(VA.loc["Paseo aleatorio", "error_mm"], 1)); C("val_cob", n(R["valorado_cobertura"] * 100, 1))
    vg = R["valorado_grupo"]; C("valg_fru", n(vg.get("Frutas", np.nan) * 100, 1)); C("valg_ver", n(vg.get("Verduras y hortalizas", np.nan) * 100, 1))
    # búsqueda
    f = []
    for tarea, sel, k_ in (("Reg.", RS, "mae_cv"), ("Clas.", CS, "pr_cv")):
        for m in sel["modelos"]:
            r = sel["mejores"][m]; f.append(f"{tarea} & {esc(m)} & {r['n_ensayos']} & {'Sí' if r['convergio'] else 'No'} & {n(r[k_] * (100 if k_ == 'mae_cv' else 1), 3)} \\\\")
    if CO.get("cuantiles_busqueda"):
        cq = CO["cuantiles_busqueda"]; f.append(f"Cuant. & LightGBM cuantílico & {cq['n_ensayos']} & {'Sí' if cq['convergio'] else 'No'} & {n(cq['pinball_cv'] * 100, 3)} \\\\")
    escribir("tab_busqueda", r"""\begin{table}[htbp]\centering\small
\caption{Búsqueda aleatoria: configuraciones evaluadas, convergencia (mejora menor que la tolerancia en las últimas 10 configuraciones) y mejor resultado promedio de validación (MAE en p.\,p., PR-AUC o pérdida de pinball en p.\,p.)}\label{tab:busqueda}
\begin{tabular}{llrlr}\toprule
Tarea & Modelo & Configuraciones & Convergió & Mejor resultado\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    C("nmaxens", max([RS["mejores"][m]["n_ensayos"] for m in MR] + [CS["mejores"][m]["n_ensayos"] for m in MC]))
    C("nminens", min([RS["mejores"][m]["n_ensayos"] for m in MR] + [CS["mejores"][m]["n_ensayos"] for m in MC]))
    C("todosconv", "todos" if all(RS["mejores"][m]["convergio"] for m in MR) and all(CS["mejores"][m]["convergio"] for m in MC) else "no todos")

    # ---------- clasificación ----------
    TC = TCd
    REFC = ["Logística autorregresiva", "SARIMA", "Frecuencia histórica"]
    f = []
    for m in MC + REFC:
        r = TC.loc[m]; nom = esc(m) + (r"$^\dagger$" if m == EC else "")
        if m == REFC[0]: f.append(r"\midrule")
        base = f"{nom} & {n(r.pr_val, 3) if m in MC else '--'} & {n(r.pr_auc, 3)} [{n(r.pr_lo, 3)}; {n(r.pr_hi, 3)}] & {n(r.roc_auc, 3)} [{n(r.roc_lo, 3)}; {n(r.roc_hi, 3)}] & {n(r.brier, 3)}"
        base += f" & {n(r.umbral, 2)} & {n(r.precision * 100, 1)} & {n(r.recall * 100, 1)} & {n(r.f1 * 100, 1)} \\\\" if m in MC else r" & -- & -- & -- & -- \\"
        f.append(base)
    escribir("tab_clf", r"""\begin{table}[htbp]\centering\small
\caption{Clasificación de alzas mayores al 15\,\%: PR-AUC fuera de muestra en validación (2022--2024) y métricas en prueba con IC bootstrap al 95\,\%. Precisión, exhaustividad y $F_1$ (\%) con el umbral $u$ elegido en validación. $^\dagger$Modelo elegido en validación.}\label{tab:clf}
\begin{tabular}{lrrrrrrrr}\toprule
& PR-AUC val. & PR-AUC [IC 95\,\%] & AUC-ROC [IC 95\,\%] & Brier & $u$ & Prec. & Exh. & $F_1$\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    r = TC.loc[EC]
    for k, v in dict(pr_e=r.pr_auc, prlo_e=r.pr_lo, prhi_e=r.pr_hi, roc_e=r.roc_auc, roclo_e=r.roc_lo, rochi_e=r.roc_hi).items(): C(k, n(v, 3))
    C("u_e", n(r.umbral, 2)); C("prec_e", n(r.precision * 100, 1)); C("rec_e", n(r.recall * 100, 1)); C("funo_e", n(r.f1 * 100, 1)); C("alertas_e", n(r.alertas * 100, 1))
    C("costo_e", n((1 - r.umbral) / r.umbral, 1))
    for m, k in (("Frecuencia histórica", "frec"), ("Logística autorregresiva", "arl"), ("SARIMA", "sar")):
        C(f"pr_{k}", n(TC.loc[m, "pr_auc"], 3)); C(f"roc_{k}", n(TC.loc[m, "roc_auc"], 3))
        C(f"dpr_{k}", n(TC.loc[m, "dpr_vs_elegido"], 3)); C(f"dprlo_{k}", n(TC.loc[m, "dpr_lo"], 3)); C(f"dprhi_{k}", n(TC.loc[m, "dpr_hi"], 3))
    C("tasa_prueba", n(R["tasa_prueba"] * 100, 1)); C("corr_mes", n(R["corr_tasa_pr_mes"], 2))
    cm = R["confusion"]; C("vp", f"{cm[1][1]:,}".replace(",", ".")); C("fp", f"{cm[0][1]:,}".replace(",", ".")); C("fn", f"{cm[1][0]:,}".replace(",", ".")); C("vn", f"{cm[0][0]:,}".replace(",", "."))
    dz = R["decision"]; C("bn_lo", n(dz["rango_util_prueba"][0], 2)); C("bn_hi", n(dz["rango_util_prueba"][1], 2))
    BV = pd.read_csv(RES / "clf_balanceo_val.csv")
    piv = BV[BV.modelo.isin(MC)].pivot(index="modelo", columns="balanceo", values="pr_auc").reindex(MC)[["Sin balanceo", "Pesos de clase", "Submuestreo"]]
    pm_ = BV[BV.modelo.isin(MC)].pivot(index="modelo", columns="balanceo", values="prob_media").reindex(MC)
    f = [f"{esc(m)} & " + " & ".join(n(v, 3) for v in r) + f" & {n(pm_.loc[m, 'Submuestreo'] * 100, 1)} & {esc(CS['balanceo'][m])} \\\\" for m, r in piv.iterrows()]
    escribir("tab_balanceo", r"""\begin{table}[htbp]\centering\small
\caption{PR-AUC fuera de muestra en validación (2022--2024) según la estrategia de balanceo, probabilidad media con submuestreo (\%; tasa real """ + n(BV.tasa_real.iloc[0] * 100, 1) + r"""\,\%) y estrategia adoptada (solo si supera a «sin balanceo» en más de 0,005)}\label{tab:balanceo}
\begin{tabular}{lrrrrl}\toprule
Modelo & Sin balanceo & Pesos & Submuestreo & Prob. media sub. & Adoptada\\ \midrule
""" + "\n".join(f).replace("nan", "--") + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    C("probsub_e", n(pm_.loc[EC, "Submuestreo"] * 100, 1)); C("tasaval", n(BV.tasa_real.iloc[0] * 100, 1))
    rc_ = CS["recalibracion"]
    f = [f"{esc(m)} & {n(v['intercepto'], 3)} & {n(v['brier_antes'], 4)} & {n(v['brier_despues'], 4)} & {n(v['media_antes'] * 100, 1)} & {n(v['media_despues'] * 100, 1)} \\\\" for m, v in rc_.items()]
    escribir("tab_calibracion", r"""\begin{table}[htbp]\centering\small
\caption{Recalibración del intercepto con las predicciones fuera de muestra de validación (2022--2024): intercepto estimado, Brier y probabilidad media (\%) antes y después; tasa real """ + n(BV.tasa_real.iloc[0] * 100, 1) + r"""\,\%}\label{tab:calibracion}
\begin{tabular}{lrrrrr}\toprule
Modelo & Intercepto & Brier antes & Brier después & Media antes & Media después\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    C("recint_e", n(rc_[EC]["intercepto"], 3))
    f = [f"{esc(m)} & {n(TC.loc[m, 'brier'], 4)} & {n(TC.loc[m, 'logloss'], 4)} & {n(TC.loc[m, 'cal_intercepto'], 3)} & {n(TC.loc[m, 'cal_pendiente'], 3)} & {n(TC.loc[m, 'ece'] * 100, 2)} & {n(TC.loc[m, 'prob_media'] * 100, 1)} \\\\"
         for m in MC + REFC]
    escribir("tab_calib_prueba", r"""\begin{table}[htbp]\centering\small
\caption{Calidad probabilística en prueba (probabilidades recalibradas): Brier, pérdida logarítmica, intercepto (con pendiente fija en 1) y pendiente de calibración (ideales 0 y 1), error de calibración esperado (ECE, p.\,p.) y probabilidad media (\%); tasa real de alzas: """ + n(R["tasa_prueba"] * 100, 1) + r"""\,\%}\label{tab:calib_prueba}
\begin{tabular}{lrrrrrr}\toprule
Modelo & Brier & Log-loss & Intercepto & Pendiente & ECE & Prob. media\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    r = TC.loc[EC]; C("calint", n(r.cal_intercepto, 3)); C("calpend", n(r.cal_pendiente, 3)); C("ece", n(r.ece * 100, 2)); C("probmedia", n(r.prob_media * 100, 1)); C("logloss", n(r.logloss, 4))
    C("calintcrudo", n(r.cal_intercepto_crudo, 3)); C("ececrudo", n(r.ece_crudo * 100, 2))
    bi = R["bn_ic"]
    f = [f"{n(float(k_), 2)} & {n(v['bn'] * 100, 2)} & {n(v['d_mejor_extremo'] * 100, 2)} [{n(v['ic1'][0] * 100, 2)}; {n(v['ic1'][1] * 100, 2)}] & {n(v['d_frec'] * 100, 2)} [{n(v['ic2'][0] * 100, 2)}; {n(v['ic2'][1] * 100, 2)}] \\\\" for k_, v in sorted(bi.items(), key=lambda t: float(t[0]))]
    escribir("tab_bn", r"""\begin{table}[htbp]\centering\small
\caption{Beneficio neto del modelo elegido en prueba (alzas netas por cada 100 casos) y su diferencia con la mejor estrategia extrema (alertar todo o no alertar) y con la frecuencia histórica, con IC bootstrap al 95\,\%}\label{tab:bn}
\begin{tabular}{rrrr}\toprule
Umbral $u$ & BN & $-$ mejor extremo [IC 95\,\%] & $-$ frecuencia histórica [IC 95\,\%]\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    v = bi["0.25"]; C("bnvc", n(v["bn"] * 100, 2)); C("bndfrec", n(v["d_frec"] * 100, 2)); C("bndfreclo", n(v["ic2"][0] * 100, 2)); C("bndfrechi", n(v["ic2"][1] * 100, 2))
    sb = R["sens_bloque"]
    f = [f"{k_} & [{n(v['mejora'][0] * 100, 1)}; {n(v['mejora'][1] * 100, 1)}] & [{n(v['pr'][0], 3)}; {n(v['pr'][1], 3)}] \\\\" for k_, v in sb.items()]
    escribir("tab_sens_bloque", r"""\begin{table}[htbp]\centering\small
\caption{Sensibilidad de los IC al 95\,\% a la longitud de bloque $L$ (meses): mejora de """ + esc(ER) + r""" frente al paseo aleatorio (\%) y PR-AUC de """ + esc(EC) + r"""}\label{tab:sens_bloque}
\begin{tabular}{rrr}\toprule
$L$ & Mejora (\%) & PR-AUC\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    C("senslo", n(min(v["mejora"][0] for v in sb.values()) * 100, 1)); C("senshi", n(max(v["mejora"][0] for v in sb.values()) * 100, 1))
    C("rocmeslo", n(R["roc_mes"][0], 2)); C("rocmeshi", n(R["roc_mes"][1], 2)); C("corrroc", n(R["corr_tasa_roc_mes"], 2)); C("corrprob", n(R["corr_prob_tasa_mes"], 2))
    cg = pd.DataFrame(R["clf_grupo"]).T
    for g, k in (("Frutas", "fru"), ("Verduras y hortalizas", "ver"), ("Tubérculos y plátanos", "tub")):
        C(f"rec_{k}", n(cg.loc[g, "recall"] * 100, 0)); C(f"prc_{k}", n(cg.loc[g, "precision"] * 100, 0))
    otros = cg.loc[["Granos y cereales", "Procesados", "Lácteos y huevos", "Pescados"]]; C("alzasotros", int(otros.alzas.sum()))
    C("detotros", int(round((otros.recall.fillna(0) * otros.alzas).sum())))
    cmes = pd.DataFrame(R["clf_mes"]).T; C("prmeslo", n(cmes.pr.min(), 2)); C("prmeshi", n(cmes.pr.max(), 2))
    cce = pd.DataFrame(R["clf_central"]).T; cce = cce[cce.alzas >= 40]; C("ncent", len(cce)); C("reccentlo", n(cce.recall.min() * 100, 0)); C("reccenthi", n(cce.recall.max() * 100, 0)); C("reccentmed", n(cce.recall.median() * 100, 0))
    C("centlo", esc(cce.recall.idxmin().split(",")[0])); C("centhi", esc(cce.recall.idxmax()))
    IB = pd.DataFrame(R["importancia_bloques"]).T
    for b_, k in (("Historia del precio", "hist"), ("Estacionalidad", "est"), ("Red de centrales", "red"), ("Producto y lugar", "lug")):
        if b_ in IB.index: C(f"ibr_{k}", n(IB.loc[b_, "reg"], 2)); C(f"ibc_{k}", n(IB.loc[b_, "clf"], 3))

if CO:
    om, di, fa = CO["origen_movil"], CO["distribucional"], CO["faltantes"]
    C("om_fijo", n(om["mae_fijo"], 2)); C("om_movil", n(om["mae_movil"], 2)); C("om_d", n(om["d_mae"], 2)); C("om_dlo", n(om["d_mae_ic"][0], 2)); C("om_dhi", n(om["d_mae_ic"][1], 2))
    C("om_prf", n(om["pr_fijo"], 3)); C("om_prm", n(om["pr_movil"], 3)); C("om_dp", n(om["d_pr"], 3)); C("om_dplo", n(om["d_pr_ic"][0], 3)); C("om_dphi", n(om["d_pr_ic"][1], 3))
    C("om_ar", n(om["mae_ar_movil"], 2)); C("om_arf", n(om["mae_ar_fijo"], 2)); C("om_sar", n(om["mae_sarima_movil"], 2)); C("om_sarf", n(om["mae_sarima_fijo"], 2))
    C("dq_pr", n(di["pr_auc"], 3)); C("dq_roc", n(di["roc_auc"], 3)); C("dq_brier", n(di["brier"], 4)); C("dq_brierc", n(di["brier_clf"], 4)); C("dq_rho", n(di["spearman_clf"], 2))
    C("dq_d", n(di["d_pr_vs_clf"], 3)); C("dq_dlo", n(di["d_pr_ic"][0], 3)); C("dq_dhi", n(di["d_pr_ic"][1], 3)); C("dq_pin", n(di["pinball"], 2)); C("dq_pinc", n(di["pinball_incondicional"], 2))
    C("dq_mae", n(di["mae_mediana"], 2)); C("dq_cruces", n(di["cruces"] * 100, 1))
    nm_ = {"Cuantiles (ajuste 2019-2024)": "Cuantiles, ajuste 2019--2024", "Cuantiles (ajuste 2019-2023)": "Cuantiles, ajuste 2019--2023", "CQR global": "CQR global", "CQR por grupo": "CQR por grupo"}
    f = []
    for niv in ("90", "80"):
        for k_, v in di["intervalos"][niv].items():
            f.append(f"{niv}\\,\\% & {nm_[k_]} & {n(v['cobertura'] * 100, 1)} [{n(v['ic'][0] * 100, 1)}; {n(v['ic'][1] * 100, 1)}] & {n(v['por_grupo']['Perecederos'] * 100, 1)} & {n(v['por_grupo']['No perecederos'] * 100, 1)} & {n(v['ancho'], 1)} \\\\")
        f.append(r"\midrule")
    escribir("tab_cqr", r"""\begin{table}[htbp]\centering\small
\caption{Intervalos de pronóstico en prueba: cobertura (\%) con IC bootstrap al 95\,\%, cobertura por grupo y ancho medio (p.\,p.). CQR: cuantiles ajustados hasta 2023 y calibrados con 2024.}\label{tab:cqr}
\begin{tabular}{llrrrr}\toprule
Nivel & Método & Cobertura [IC 95\,\%] & Perecederos & No perecederos & Ancho\\ \midrule
""" + "\n".join(f[:-1]) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    for niv, k_ in (("90", "nov"), ("80", "och")):
        for met, km in (("Cuantiles (ajuste 2019-2024)", "q"), ("CQR global", "cg"), ("CQR por grupo", "cp")):
            v = di["intervalos"][niv][met]; C(f"cob{k_}{km}", n(v["cobertura"] * 100, 1)); C(f"cob{k_}{km}lo", n(v["ic"][0] * 100, 1)); C(f"cob{k_}{km}hi", n(v["ic"][1] * 100, 1))
            C(f"cob{k_}{km}per", n(v["por_grupo"]["Perecederos"] * 100, 1)); C(f"cob{k_}{km}noper", n(v["por_grupo"]["No perecederos"] * 100, 1)); C(f"ancho{k_}{km}", n(v["ancho"], 1))
    C("fa_tasa", n(fa["tasa_falta"] * 100, 1)); C("fa_n", f"{fa['n']:,}".replace(",", "."))
    e = {r["falta"]: r for r in fa["por_estado"]}
    C("fa_prop_f", n(e[True]["prop_alza_otras"] * 100, 1)); C("fa_prop_o", n(e[False]["prop_alza_otras"] * 100, 1))
    C("fa_cam_f", n(e[True]["cambio_otras"] * 100, 2)); C("fa_cam_o", n(e[False]["cambio_otras"] * 100, 2))
    if "sensibilidad" in fa:
        nm = {"observados": "Solo casos observados", "imputando con las demás centrales": "Faltantes con el cambio de las demás centrales",
              "faltantes = todos alzas": "Faltantes: todos alzas", "faltantes = ninguna alza": "Faltantes: ninguna alza"}
        f = [f"{nm[k_]} & {n(v['mejora'] * 100, 1) if 'todos' not in k_ else '--'} & {n(v['pr_auc'], 3)} & {n(v['recall'] * 100, 1)} & {n(v['precision'] * 100, 1)} \\\\" for k_, v in fa["sensibilidad"].items()]
        escribir("tab_faltantes", r"""\begin{table}[htbp]\centering\small
\caption{Sensibilidad de las métricas de prueba a los """ + str(fa["n_prueba"]) + r""" casos con precio en $t$ y sin precio en $t+1$ (""" + n(fa["tasa_prueba"] * 100, 1) + r"""\,\% del periodo de prueba)}\label{tab:faltantes}
\begin{tabular}{lrrrr}\toprule
Supuesto & Mejora vs. PA (\%) & PR-AUC & Exhaustividad (\%) & Precisión (\%)\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
        se = fa["sensibilidad"]; C("fapro", n(se["observados"]["pr_auc"], 3)); C("faprt", n(se["faltantes = todos alzas"]["pr_auc"], 3))
        C("fareco", n(se["observados"]["recall"] * 100, 1)); C("farect", n(se["faltantes = todos alzas"]["recall"] * 100, 1))
        C("faprobf", n(fa["prob_media_faltantes"] * 100, 1)); C("faprobo", n(fa["prob_media_obs"] * 100, 1)); C("fanprueba", fa["n_prueba"]); C("fatasap", n(fa["tasa_prueba"] * 100, 1))
    C("fa_or_prop", n(fa["or_por_de"]["prop"], 2)); C("fa_or_cam", n(fa["or_por_de"]["cam"], 2)); C("fa_or_abs", n(fa["or_por_de"]["abs_r_t"], 2))

SR = J("sarima_resumen.json")
if SR: C("sar_series", SR["series_prueba"]); C("sar_estac", n(SR["prop_estacional"] * 100, 0)); C("sar_panel", SR["series_panel"])
if RS.get("sarima_cobertura") is not None: C("sar_cob", n(RS["sarima_cobertura"] * 100, 1))
VE = J("verificacion.json")
if VE:
    q_, g_, si, rf = VE["cuantilica"], VE["gradientes"], VE["simulacion"], VE["random_forest"]
    filas_v = [r"Regresión cuantílica & MAE (p.\,p.) solución exacta / descenso de gradiente & " + f"{n(q_['mae_exacta'], 2)} / {n(q_['mae_sgd'], 2)}" + r" \\",
               r" & Correlación de predicciones / de coeficientes & " + f"{n(q_['corr_pred'], 4)} / {n(q_['corr_coef'], 3)}" + r" \\",
               r"MLP (error absoluto) & Error relativo del gradiente, mediana / máximo & " + f"${n(g_['error_relativo_mediano'] * 1e9, 1)}\\cdot10^{{-9}}$ / ${n(g_['error_relativo_max'] * 1e6, 1)}\\cdot10^{{-6}}$" + r" \\",
               r" & Simulación: distancia a la mediana / a la media (pérdida absoluta) & " + f"{n(si['dist_mediana_L1'], 3)} / {n(si['dist_media_L1'], 3)}" + r" \\",
               r" & Simulación: distancia a la mediana / a la media (pérdida cuadrática) & " + f"{n(si['dist_mediana_L2'], 3)} / {n(si['dist_media_L2'], 3)}" + r" \\",
               r"Random Forest & MAE (p.\,p.) LightGBM / scikit-learn / paseo aleatorio & " + f"{n(rf['mae_lightgbm'], 2)} / {n(rf['mae_sklearn'], 2)} / {n(rf['mae_paseo'], 2)}" + r" \\",
               r" & Correlación de predicciones & " + f"{n(rf['corr_pred'], 3)}" + r" \\"]
    escribir("tab_verificacion", r"""\begin{table}[htbp]\centering\footnotesize
\caption{Verificación de las implementaciones no estándar (submuestras de 6\,000 y 3\,000 filas de entrenamiento, 4\,000 de validación; simulación con ruido exponencial centrado en la mediana)}\label{tab:verificacion}
\begin{tabular}{llr}\toprule
Implementación & Comprobación & Resultado\\ \midrule
""" + "\n".join(filas_v) + "\n\\bottomrule\\end{tabular}\\end{table}\n")

# ---------- hiperparámetros ----------
if RS and CS:
    ESP = {"alpha": r"$\alpha$", "capas": "capas", "lr": "tasa", "prof": "prof.", "hoja": "hoja mín.", "mf": "frac. var.",
           "n": "árboles", "mcw": "peso mín.", "ss": "submuestra", "cs": "frac. col.", "hojas": "hojas", "mcs": "obs. hoja", "l2": r"$\lambda$", "C": "$C$", "pen": "penal."}
    CAPAS = ["(32)", "(64)", "(64, 32)", "(128, 64)"]
    def fmt(k, v):
        if k == "capas": return CAPAS[int(v)]
        if isinstance(v, str): return v.upper() if k == "pen" else v
        if isinstance(v, float) and not float(v).is_integer():
            if abs(v) < 1e-3:
                e = int(np.floor(np.log10(abs(v)))); return f"${n(v / 10 ** e, 1)}\\cdot10^{{{e}}}$"
            return n(v, 4) if abs(v) < .01 else n(v, 3)
        return str(int(v))
    f = []
    for tarea, sel in (("Reg.", RS), ("Clas.", CS)):
        for m in sel["modelos"]:
            h = sel["mejores"][m]["params"]
            f.append(f"{tarea} & {esc(m)} & {sel['mejores'][m]['n_ensayos']} & " + "; ".join(f"{ESP.get(k, k)} {fmt(k, v)}" for k, v in sorted(h.items())) + r" \\")
        f.append(r"\midrule")
    if CO.get("cuantiles_busqueda"):
        cq = CO["cuantiles_busqueda"]; f.insert(-1, f"Cuant. & LightGBM & {cq['n_ensayos']} & " + "; ".join(f"{ESP.get(k, k)} {fmt(k, v)}" for k, v in sorted(cq["params"].items())) + r" \\")
    igual = [m for m in RS["modelos"] if m in CS["modelos"] and RS["mejores"][m]["params"] == CS["mejores"][m]["params"]]
    nota = ("" if not igual else "; en " + " y ".join(igual) + (", la misma configuración resultó la mejor en ambas tareas, por lo que sus valores coinciden"
                                                               if len(igual) == 1 else ", la misma configuración resultó la mejor en ambas tareas, por lo que sus valores coinciden"))
    escribir("tab_hiper", r"""\footnotesize
\begin{longtable}{llrp{7.4cm}}
\caption{Hiperparámetros elegidos por búsqueda aleatoria (número de configuraciones evaluadas en la tercera columna). Las dos búsquedas de cada modelo usaron la misma semilla y, por tanto, la misma secuencia de configuraciones""" + nota + r""".}\label{tab:hiper}\\
\toprule Tarea & Modelo & $N$ & Valores elegidos\\ \midrule\endfirsthead
\toprule Tarea & Modelo & $N$ & Valores elegidos\\ \midrule\endhead
\bottomrule\endfoot
""" + "\n".join(f[:-1]) + "\n\\end{longtable}\n\\normalsize\n")

# ---------- tiempos y memoria (resultados/tiempos.csv) ----------
DESC = {"01_panel": "Panel supervisado y variables candidatas", "02_eda": "Análisis exploratorio y calidad", "03_variables": "Selección de variables (validación)",
        "sarima": "SARIMA por serie (todos los cortes)", "04_regresion": "Búsqueda y prueba de los modelos de regresión", "05_clasificacion": "Búsqueda, balanceo, recalibración, umbral y prueba de los clasificadores",
        "06_resultados": "Métricas, bootstrap, pruebas, figuras e importancia", "07_complementarios": "Origen móvil, cuantiles, CQR y faltantes", "09_verificacion": "Verificación de implementaciones"}
if (RES / "tiempos.csv").exists():
    TT = pd.read_csv(RES / "tiempos.csv")
    f = [f"\\texttt{{{esc(r.paso)}.py}} & {DESC.get(r.paso, '')} & {n(r.minutos, 1)} & {n(r.memoria_gb, 2)} \\\\" for r in TT.itertuples()]
    f.append(r"\midrule Total & & " + n(TT.minutos.sum(), 0) + " & " + n(TT.memoria_gb.max(), 2) + r" \\")
    escribir("tab_tiempos", r"""\begin{table}[htbp]\centering\footnotesize
\caption{Tiempo de ejecución y memoria residente máxima por programa, medidos con \texttt{medir.py} en la corrida de referencia (""" + esc(str(TT.equipo.dropna().iloc[-1])) + r""")}\label{tab:tiempos}
\begin{tabular}{lp{6.4cm}rr}\toprule
Programa & Qué hace & Minutos & Memoria (GB)\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    C("tiempototal", n(TT.minutos.sum(), 0)); C("memmax", n(TT.memoria_gb.max(), 1))

for k, v in {"registros": f"{EG['registros_base']:,}".replace(",", "."), "series": f"{EG['series_panel']:,}".replace(",", "."), "filas": f"{EG['filas_panel']:,}".replace(",", "."),
             "centrales": EG["centrales"], "ciudades": EG["ciudades"], "alimentos": EG["alimentos"],
             "ntr": f"{EG['filas_muestra']['entrenamiento']:,}".replace(",", "."), "nva": f"{EG['filas_muestra']['validacion']:,}".replace(",", "."), "nte": f"{EG['filas_muestra']['prueba']:,}".replace(",", "."),
             "alzatr": n(EG["tasa_alza"]["entrenamiento"] * 100, 1), "alzava": n(EG["tasa_alza"]["validacion"] * 100, 1), "alzate": n(EG["tasa_alza"]["prueba"] * 100, 1),
             "sdcambio": n(EG["sd_cambio"] * 100, 1), "medabs": n(EG["mediana_abs"] * 100, 1), "curtosis": n(EG["kurtosis"], 1), "faltante": n(EG["faltante_total"] * 100, 1),
             "acfuno": n(EG["acf"]["1"], 2), "acfdos": n(EG["acf"]["2"], 2), "acfdoce": n(EG["acf"]["12"], 2), "corrpt": n(EG["corr_precio_ton_mismo"], 2), "corrpts": n(EG["corr_precio_ton_sig"], 2),
             "corroni": n(EG["corr_oni_alza"], 3), "huecosdos": n(EC_["rachas"]["hasta2"] * 100, 0), "solabast": f"{EC_['composicion']['Solo abastecimiento']:,}".replace(",", "."),
             "preciokg": f"{EC_['composicion']['Precio en $/kg']:,}".replace(",", "."), "otraunidad": f"{EC_['composicion']['Precio en otra unidad']:,}".replace(",", "."),
             "mercadosbase": EC_["mercados_base"], "alimentosbase": EC_["alimentos_base"]}.items():
    C(k, v)
# ---------- tablas compactas del documento ----------
if R:
    T2 = pd.DataFrame(R["reg_tabla"]).set_index("modelo").loc[["Paseo aleatorio", "AR estacional", "SARIMA"] + MR]
    f = []
    for m, r in T2.iterrows():
        nom = esc(m) + (r"$^\ast$" if m == ER else "")
        mej = "--" if m == "Paseo aleatorio" else f"{n(r.mejora * 100, 1)} [{n(r.mejora_lo * 100, 1)}; {n(r.mejora_hi * 100, 1)}]"
        dif = "--" if m == ER else f"{n(r.d_vs_elegido, 2)} [{n(r.d_lo_bonf, 2)}; {n(r.d_hi_bonf, 2)}]"
        f.append(f"{nom} & {n(r.mae_val * 100, 2)} & {n(r.mae * 100, 2)} & {mej} & {dif} \\\\")
        if m == "SARIMA": f.append(r"\midrule")
    escribir("tab_reg", r"""\begin{table}[htbp]\centering\small
\caption{Pronóstico del cambio del mes siguiente. Error absoluto medio (MAE, en puntos porcentuales) en validación (2022--2024) y en prueba (enero de 2025 a septiembre de 2026), reducción del error frente al último precio y diferencia de MAE con """ + esc(ER) + r""" (positiva: peor que """ + esc(ER) + r"""). Entre corchetes, intervalos al 95\,\%; los de la última columna están ajustados por comparaciones múltiples. $^\ast$Modelo elegido.}\label{tab:reg}
\begin{tabular}{lrrrr}\toprule
& \multicolumn{2}{c}{MAE} & Reducción del & Diferencia \\ \cmidrule(lr){2-3}
Modelo & Validación & Prueba & error (\%) & con """ + esc(ER) + r"""\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    TC2 = pd.DataFrame(R["clf_tabla"]).set_index("modelo")
    f = []
    for m in MC + ["SARIMA", "Frecuencia histórica", "Logística autorregresiva"]:
        r = TC2.loc[m]; nom = esc(m) + (r"$^\ast$" if m == EC else "")
        if m == "SARIMA": f.append(r"\midrule")
        dif = "--" if m == EC else f"{n(r.dpr_vs_elegido, 3)} [{n(r.dpr_lo_bonf, 3)}; {n(r.dpr_hi_bonf, 3)}]"
        pr_ = f"{n(r.precision * 100, 0)} & {n(r.recall * 100, 0)}" if m in MC else "-- & --"
        f.append(f"{nom} & {n(r.pr_val, 3) if m in MC else '--'} & {n(r.pr_auc, 3)} [{n(r.pr_lo, 3)}; {n(r.pr_hi, 3)}] & {n(r.roc_auc, 3)} & {dif} & {pr_} \\\\")
    escribir("tab_clf", r"""\begin{table}[htbp]\centering\small
\caption{Anticipación de alzas mayores al 15\,\%. Área bajo la curva de precisión y exhaustividad (AP) en validación y en prueba, área bajo la curva ROC (AUC) en prueba, diferencia de AP con """ + esc(EC) + r""" (negativa: peor) y, con el umbral fijado en validación, precisión y exhaustividad en prueba (\%). Intervalos al 95\,\%; los de la diferencia, ajustados por comparaciones múltiples. $^\ast$Modelo elegido.}\label{tab:clf}
\begin{tabular}{lrrrrrr}\toprule
& \multicolumn{2}{c}{AP} & & Diferencia & & \\ \cmidrule(lr){2-3}
Modelo & Validación & Prueba & AUC & con """ + esc(EC) + r""" & Precisión & Exhaustividad\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
if CO.get("distribucional"):
    di = CO["distribucional"]["intervalos"]; f = []
    for k_, nom in (("Cuantiles (ajuste 2019-2024)", "Cuantiles estimados"), ("CQR global", "Conforme, global"), ("CQR por grupo", "Conforme, por grupo")):
        a, b = di["90"][k_], di["80"][k_]
        f.append(f"{nom} & {n(a['cobertura'] * 100, 1)} & {n(a['por_grupo']['Perecederos'] * 100, 1)} & {n(a['por_grupo']['No perecederos'] * 100, 1)} & {n(a['ancho'], 1)} & {n(b['cobertura'] * 100, 1)} & {n(b['ancho'], 1)} \\\\")
    escribir("tab_cqr", r"""\begin{table}[htbp]\centering\small
\caption{Intervalos de pronóstico en prueba: porcentaje de casos cuyo cambio observado cae dentro del intervalo (cobertura) y ancho medio en puntos porcentuales. Perecederos: frutas, verduras y tubérculos.}\label{tab:cqr}
\begin{tabular}{lrrrrrr}\toprule
& \multicolumn{4}{c}{Intervalo del 90\,\%} & \multicolumn{2}{c}{Intervalo del 80\,\%}\\ \cmidrule(lr){2-5}\cmidrule(lr){6-7}
Método & Cobertura & Perecederos & No perec. & Ancho & Cobertura & Ancho\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
# bloques de variables
CONT = {"Historia del precio": "cambios acumulados y rezagados, volatilidad, posición en el rango anual",
        "Estacionalidad": "mes del año, frecuencia y cambio histórico del mismo mes",
        "Abastecimiento local": "toneladas ingresadas, municipios de origen, días con registro",
        "Red de centrales": "precio del producto en las demás centrales",
        "Calendario": "Semana Santa, diciembre", "Producto y lugar": "grupo, producto, central, ciudad, perecibilidad",
        "El Niño (ONI)": "índice ONI y su cambio", "Promedios móviles": "distancia a medias móviles", "Año anterior": "cambio del mismo mes un año antes",
        "Red ampliada": "otros cambios del precio nacional", "Grupo en la central": "cambio y alzas del grupo en la central",
        "Abastecimiento nacional": "toneladas nacionales y participación de la central", "Calidad del dato": "meses y días con registro"}
fin = set(VF["variables"]); f = []
for b, vs in {**BLOQUES_BASE, **BLOQUES_NUEVOS}.items():
    k_ = sum(v in fin for v in vs)
    if b in VF["bloques_retirados"]: dec = "Sale"
    elif b in BLOQUES_NUEVOS and b not in VF["bloques_anadidos"]: dec = "No entra"
    elif k_ == 0: dec = "Entra; luego salen sus variables"
    elif k_ < len(vs): dec = "Queda en parte"
    else: dec = "Queda"
    f.append(f"{esc(b)} & {esc(CONT.get(b, ''))} & {len(vs)} & {k_} & {dec} \\\\")
    if b == list(BLOQUES_BASE)[-1]: f.append(r"\midrule")
escribir("tab_bloques", r"""\begin{table}[htbp]\centering\small
\caption{Bloques de variables candidatas y resultado de la selección. Arriba, los bloques de partida; abajo, los bloques adicionales evaluados.}\label{tab:bloques}
\begin{tabular}{l>{\raggedright\arraybackslash}p{5.6cm}rrl}\toprule
Bloque & Contenido & Candidatas & Finales & Decisión\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")

# descriptivos por grupo
Pg = cargar_panel(); Pg["g"] = Pg.grupo.map(GRUPOS)
dg = Pg.groupby("g").agg(series=("alimento", lambda s: Pg.loc[s.index, ["mercado", "alimento"]].drop_duplicates().shape[0]), nprod=("alimento", "nunique"), obs=("y", "size"),
                         med=("y", lambda s: s.abs().median() * 100), sd=("y", lambda s: s.std() * 100), alza=("alza", "mean"), baja=("y", lambda s: (s < -np.log(1.15)).mean())).sort_values("obs", ascending=False)
f = [f"{esc(g)} & {int(r.nprod)} & {int(r.series)} & {n(r.obs, 0)} & {n(r.med, 1)} & {n(r.sd, 1)} & {n(r.alza * 100, 1)} & {n(r.baja * 100, 1)} \\\\" for g, r in dg.iterrows()]
escribir("tab_grupos", r"""\begin{table}[htbp]\centering\small
\caption{Panel por grupo de alimentos, 2019--2026: productos, series, observaciones, mediana del cambio mensual absoluto y desviación típica del cambio (puntos porcentuales), y porcentaje de meses con alzas y con bajas de más del 15\,\%}\label{tab:grupos}
\begin{tabular}{lrrrrrrr}\toprule
& & & & \multicolumn{2}{c}{Cambio mensual} & \multicolumn{2}{c}{Meses (\%)}\\ \cmidrule(lr){5-6}\cmidrule(lr){7-8}
Grupo & Productos & Series & Observ. & Mediana $|y|$ & Desv. típica & Alza $>15\,\%$ & Baja $>15\,\%$\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
# uso de las alertas según la razón de costos
if R:
    Cp = pd.read_parquet(RES / "clf_predicciones_prueba.parquet"); ya_, pp_ = Cp.alza.values, Cp[CS["elegido"]].values; nn_, nm_ = len(Cp), Cp.mes_obj.nunique()
    f = []
    for razon, uu in (("1:1", .5), ("1:2", 1 / 3), ("1:3", .25), ("1:5", 1 / 6), ("1:9", .1)):
        a_ = pp_ >= uu; vp_ = (a_ & (ya_ == 1)).sum(); fp_ = (a_ & (ya_ == 0)).sum()
        f.append(f"{razon} & {n(uu, 2)} & {int(round(a_.sum() / nm_))} & {n(a_.mean() * 100, 1)} & {n(vp_ / a_.sum() * 100, 1)} & {n(vp_ / ya_.sum() * 100, 1)} & {n((vp_ / nn_ - fp_ / nn_ * uu / (1 - uu)) * 100, 2)} \\\\")
    escribir("tab_alertas", r"""\begin{table}[htbp]\centering\small
\caption{Alertas de """ + esc(CS["elegido"]) + r""" en la prueba según la razón de costos entre una falsa alarma y un alza no alertada. Umbral $u=c_{FP}/(c_{FP}+c_{FN})$; alertas promedio por mes (de unos """ + str(int(round(nn_ / nm_))) + r""" pronósticos mensuales, con """ + str(int(round(ya_.sum() / nm_))) + r""" alzas en promedio); porcentaje de casos alertados; precisión y exhaustividad (\%), y beneficio neto (alzas netas por cada 100 casos)}\label{tab:alertas}
\begin{tabular}{lrrrrrr}\toprule
Razón $c_{FP}:c_{FN}$ & Umbral & Alertas al mes & Casos alertados & Precisión & Exhaustividad & Beneficio neto\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")

# mejora por grupo para todos los modelos
if R:
    Op = pd.read_parquet(RES / "reg_predicciones_prueba.parquet"); Op["g"] = Op.grupo.map(GRUPOS)
    ordg = ["Frutas", "Verduras y hortalizas", "Tubérculos y plátanos", "Procesados", "Granos y cereales", "Lácteos y huevos", "Pescados"]
    abre = {"Frutas": "Frutas", "Verduras y hortalizas": "Verduras", "Tubérculos y plátanos": "Tubérc.", "Procesados": "Proces.", "Granos y cereales": "Granos", "Lácteos y huevos": "Lácteos", "Pescados": "Pescados"}
    erw = Op.assign(e=Op.y.abs()).groupby("g").e.mean()
    f = []
    for m in ["AR estacional", "SARIMA"] + MR:
        em_ = Op.assign(e=(Op.y - Op[m]).abs()).groupby("g").e.mean(); mej = (1 - em_ / erw) * 100
        f.append(f"{esc(m)}" + (r"$^\ast$" if m == ER else "") + " & " + " & ".join(n(mej[g], 1) for g in ordg) + " \\\\")
        if m == "SARIMA": f.append(r"\midrule")
    escribir("tab_grupos_modelos", r"""\begin{table}[htbp]\centering\small
\caption{Reducción del error frente al último precio (\%) por grupo de alimentos y modelo en la prueba. Valores negativos: más error que el último precio. $^\ast$Modelo elegido.}\label{tab:grupos_modelos}
\begin{tabular}{lrrrrrrr}\toprule
Modelo & """ + " & ".join(abre[g] for g in ordg) + r"""\\ \midrule
""" + "\n".join(f) + "\n\\midrule\nPronósticos & " + " & ".join(n(int((Op.g == g).sum()), 0) for g in ordg) + " \\\\\n\\bottomrule\\end{tabular}\\end{table}\n")
# etapas de la selección
f = [f"{esc(p['paso'])} & {p['n']} & {n(p['mae'], 2)} & {n(p['d_mae'], 3)} [{n(p['mae_lo'], 3)}; {n(p['mae_hi'], 3)}] & {n(p['pr'], 3)} & {n(p['d_pr'], 3)} [{n(p['pr_lo'], 3)}; {n(p['pr_hi'], 3)}] \\\\" for p in VF["pasos"]]
escribir("tab_pasos", r"""\begin{table}[htbp]\centering\small
\caption{Desempeño de LightGBM en las predicciones de 2023 y 2024 después de cada etapa de la selección, y diferencia frente a las 38 variables de partida con su intervalo del 95\,\%}\label{tab:pasos}
\begin{tabular}{lrrrrr}\toprule
Etapa & Variables & MAE & Diferencia & AP & Diferencia\\ \midrule
""" + "\n".join(f).replace("Base (38 variables)", "Partida").replace("Etapa 2: bloques", "Etapa 1: bloques").replace("Etapa 3: sin no informativas", "Etapa 2: sin poco informativas").replace("Etapa 4: sin redundancias (final)", "Etapa 3: sin redundancias (final)") + "\n\\bottomrule\\end{tabular}\\end{table}\n")
# robustez
if R and CO:
    sb_ = {str(k): v for k, v in R["sens_bloque"].items()} if isinstance(R["sens_bloque"], dict) else {}
    om_, fa_ = CO["origen_movil"], CO["faltantes"]["sensibilidad"]
    VAe = pd.DataFrame(R["valorado"]).set_index("modelo").loc[ER]
    TT_ = pd.DataFrame(R["reg_tabla"]).set_index("modelo").loc[ER]; TC_ = pd.DataFrame(R["clf_tabla"]).set_index("modelo").loc[EC]
    filas_ = [("Resultado principal", f"{n(TT_.mejora * 100, 1)} [{n(TT_.mejora_lo * 100, 1)}; {n(TT_.mejora_hi * 100, 1)}]", f"{n(TC_.pr_auc, 3)} [{n(TC_.pr_lo, 3)}; {n(TC_.pr_hi, 3)}]")]
    for L_ in ("1", "6"):
        if L_ in sb_:
            v = sb_[L_]; filas_.append((f"Bloques de {L_} mes" + ("" if L_ == "1" else "es") + " en el bootstrap", f"[{n(v['mejora'][0] * 100, 1)}; {n(v['mejora'][1] * 100, 1)}]", f"[{n(v['pr'][0], 3)}; {n(v['pr'][1], 3)}]"))
    filas_.append(("Reajuste trimestral", n(om_["mejora_movil"] * 100, 1), n(om_["pr_movil"], 3)))
    filas_.append(("Faltantes: cambio de las demás centrales", n(fa_["imputando con las demás centrales"]["mejora"] * 100, 1), n(fa_["imputando con las demás centrales"]["pr_auc"], 3)))
    filas_.append(("Faltantes: todos alzas", n(fa_["faltantes = todos alzas"]["mejora"] * 100, 1), n(fa_["faltantes = todos alzas"]["pr_auc"], 3)))
    filas_.append(("Faltantes: ninguna alza", n(fa_["faltantes = ninguna alza"]["mejora"] * 100, 1), n(fa_["faltantes = ninguna alza"]["pr_auc"], 3)))
    filas_.append(("Error valorado en pesos", f"{n(VAe.mejora * 100, 1)} [{n(VAe.lo * 100, 1)}; {n(VAe.hi * 100, 1)}]", "--"))
    escribir("tab_robustez", r"""\begin{table}[htbp]\centering\small
\caption{Robustez de los resultados principales: reducción del error de """ + esc(ER) + r""" frente al último precio (\%) y AP de """ + esc(EC) + r""" en la prueba bajo cada variante; entre corchetes, intervalos del 95\,\%}\label{tab:robustez}
\begin{tabular}{lrr}\toprule
Variante & Reducción del error (\%) & AP\\ \midrule
""" + "\n".join(f"{a} & {b} & {c} \\\\" for a, b, c in filas_) + "\n\\bottomrule\\end{tabular}\\end{table}\n")

# costo computacional: complejidad teórica y tiempo medido de la búsqueda (registros de 04 y 05)
import re as _re
def _tiempos(arch, clave):
    t, prev = {}, 0
    for l in (RES / arch).read_text().splitlines():
        m_ = _re.match(r"\[\s*(\d+)s\] (.+?) " + clave, l)
        if m_: t[m_.group(2)] = int(m_.group(1)) - prev; prev = int(m_.group(1))
    return t
if (RES / "log_04_regresion.txt").exists():
    tr_, tc_ = _tiempos("log_04_regresion.txt", "MAE CV"), _tiempos("log_05_clasificacion.txt", "PR-AUC CV")
    CX = {"Regresión cuantílica": ("Regresión logística", r"$O(E\,n\,p)$", "pasadas $E$ sobre los datos"),
          "MLP": ("MLP", r"$O(E\,n\,p\,h)$", "$h$ neuronas por capa"),
          "Random Forest": ("Random Forest", r"reg.: $O(B\,n\,p)$; clas.: $O(B\,m\,n\log n)$", "reg.: bosque de LightGBM con histogramas; clas.: scikit-learn, $m$ variables por división"),
          "XGBoost": ("XGBoost", r"$O(M\,n\,p)$", "$M$ árboles, cortes por histogramas"),
          "LightGBM": ("LightGBM", r"$O(M\,n\,p)$", "$M$ árboles, cortes por histogramas"),
          "CatBoost": ("CatBoost", r"$O(M\,n\,p)$", "$M$ árboles simétricos")}
    f = []
    for m, (mc, cx, nota) in CX.items():
        nom = "Regresión cuantílica / logística" if m == "Regresión cuantílica" else m
        f.append(f"{nom} & {cx} & {nota} & {tr_.get(m, 0)} & {tc_.get(mc, 0)} \\\\")
    escribir("tab_costo", r"""\begin{table}[htbp]\centering\small
\caption{Costo computacional. Complejidad aproximada de un ajuste ($n$ observaciones, $p$ variables) y tiempo medido de la búsqueda de hiperparámetros en segundos (40 configuraciones $\times$ 3 cortes = 120 ajustes, salvo las que se ampliaron según la tabla~\ref{tab:hiper}, en paralelo con 10 núcleos).}\label{tab:costo}
\begin{tabular}{llp{4.3cm}rr}\toprule
& & & \multicolumn{2}{c}{Tiempo de búsqueda (s)}\\ \cmidrule(lr){4-5}
Modelo & Complejidad & Parámetros & Regresión & Clasificación\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")

XP = json.loads((RES / "explicaciones.json").read_text()) if (RES / "explicaciones.json").exists() else {}
if XP:
    cif["adfseries"] = n(XP["adf"]["series"], 0); cif["adfnivel"] = n((1 - XP["adf"]["rechaza_nivel"]) * 100, 0); cif["adfcambio"] = n(XP["adf"]["rechaza_cambio"] * 100, 0)
# ---------- tablas de la estructura final ----------
from scipy import stats as _st
Bb = pd.read_parquet(DATOS / "base_unida_mensual.parquet"); bk = Bb[Bb.unidad == "$/kg"]
nser_kg = bk[["mercado", "alimento"]].drop_duplicates().shape[0]
f = [("Registros de la base unida (2018--2026)", n(len(Bb), 0), n(Bb[["mercado", "alimento"]].drop_duplicates().shape[0], 0)),
     ("Con precio en pesos por kilogramo", n(len(bk), 0), n(nser_kg, 0)),
     ("Series con al menos 48 meses con precio hasta 2024", n(int(bk.merge(Pg[["mercado", "alimento"]].drop_duplicates()).shape[0]), 0), n(Pg[["mercado", "alimento"]].drop_duplicates().shape[0], 0)),
     ("Con precio observado en $t$, $t+1$ y $t-12$ (panel)", n(len(Pg), 0), n(Pg[["mercado", "alimento"]].drop_duplicates().shape[0], 0))]
escribir("tab_embudo", r"""\begin{table}[htbp]\centering\small
\caption{De la base del SIPSA al panel de análisis}\label{tab:embudo}
\begin{tabular}{lrr}\toprule
Paso & Registros & Series\\ \midrule
""" + "\n".join(f"{a} & {b} & {c} \\\\" for a, b, c in f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
# resumen de la variable objetivo
def _res(s):
    s = s * 100; return [n(len(s), 0), n(s.mean(), 2), n(s.std(), 1), n(s.min(), 0), n(s.quantile(.25), 1), n(s.median(), 1), n(s.quantile(.75), 1), n(s.max(), 0), n(_st.skew(s), 2), n(_st.kurtosis(s), 1)]
f = ["Todo el panel & " + " & ".join(_res(Pg.y)) + r" \\ \midrule"] + [f"{esc(g)} & " + " & ".join(_res(Pg.y[Pg.g == g])) + " \\\\" for g in dg.index]
escribir("tab_resumen_y", r"""\begin{table}[htbp]\centering\small
\caption{Resumen del cambio mensual del precio del mes siguiente ($100\,y$, puntos porcentuales) por grupo: observaciones, media, desviación típica, mínimo, cuartiles, máximo, asimetría y curtosis en exceso}\label{tab:resumen_y}
\begin{tabular}{lrrrrrrrrrr}\toprule
Grupo & $n$ & Media & D.\,t. & Mín. & Q1 & Mediana & Q3 & Máx. & Asim. & Curt.\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
# variables explicativas principales
VX = [("cambio_1m", 100, "p. p."), ("cambio_12m", 100, "p. p."), ("vol_12m", 100, "p. p."), ("dist_max_12m", 100, "p. p."), ("frec_alza_hist", 100, "\\%"),
      ("cambio_estacional_hist", 100, "p. p."), ("cambio_nacional_1m", 100, "p. p."), ("prop_centrales_alza", 100, "\\%"), ("cambio_ton_1m", 100, "p. p."), ("oni", 1, "°C")]
Ptr = Pg[Pg.muestra == "entrenamiento"]; f = []
for v, k_, u_ in VX:
    s = Ptr[v] * k_; rho = _st.spearmanr(Ptr[v], Ptr.y, nan_policy="omit")[0]
    f.append(f"{esc(NOMBRES.get(v, v))} & {u_} & {n(s.isna().mean() * 100, 1)} & {n(s.median(), 1)} & {n(s.quantile(.25), 1)} & {n(s.quantile(.75), 1)} & {n(rho, 3)} \\\\")
escribir("tab_explicativas", r"""\begin{table}[htbp]\centering\small
\caption{Variables explicativas principales en entrenamiento: porcentaje de faltantes, mediana, cuartiles y correlación de Spearman con el cambio del mes siguiente}\label{tab:explicativas}
\begin{tabular}{llrrrrr}\toprule
Variable & Unidad & Faltantes (\%) & Mediana & Q1 & Q3 & $\rho_S$ con $y$\\ \midrule
""" + "\n".join(f).replace("°C", r"\textdegree C") + "\n\\bottomrule\\end{tabular}\\end{table}\n")
if XP:
    escribir("tab_adf", r"""\begin{table}[htbp]\centering\small
\caption{Prueba de Dickey--Fuller aumentada en las """ + n(XP["adf"]["series"], 0) + r""" series con al menos cinco años de datos (5\,\% de significancia)}\label{tab:adf}
\begin{tabular}{llr}\toprule
Serie & Componentes de la prueba & Rechaza la raíz unitaria (\%)\\ \midrule
Logaritmo del precio & constante y tendencia & """ + n(XP["adf"]["rechaza_nivel"] * 100, 1) + r""" \\
Cambio mensual & constante & """ + n(XP["adf"]["rechaza_cambio"] * 100, 1) + r""" \\
\bottomrule\end{tabular}\end{table}
""")
    dl_ = XP["delong"]; f = [f"{esc(m)} & {n(v['dif'], 4)} & {('<0,001' if v['p_holm'] < .001 else n(v['p_holm'], 3))} \\\\" for m, v in sorted(dl_.items(), key=lambda kv: kv[1]['dif'])]
    escribir("tab_delong", r"""\begin{table}[htbp]\centering\small
\caption{Prueba de DeLong: diferencia de AUC entre """ + esc(EC) + r""" y cada clasificador en la prueba (positiva: """ + esc(EC) + r""" mejor) y valor $p$ ajustado por Holm}\label{tab:delong}
\begin{tabular}{lrr}\toprule
Clasificador & Diferencia de AUC & $p$ (Holm)\\ \midrule
""" + "\n".join(f).replace("<0,001", "$<0{,}001$") + "\n\\bottomrule\\end{tabular}\\end{table}\n")
# balanceo
BL = pd.read_csv(RES / "clf_balanceo_val.csv")
f = []
for m in MC:
    r_ = BL[BL.modelo == m].set_index("balanceo")
    f.append(f"{esc(m)} & " + " & ".join(n(r_.loc[b, "pr_auc"], 3) for b in ("Sin balanceo", "Pesos de clase", "Submuestreo")) + " & " + " & ".join(n(r_.loc[b, "prob_media"] * 100, 1) for b in ("Sin balanceo", "Pesos de clase", "Submuestreo")) + " \\\\")
escribir("tab_balanceo", r"""\begin{table}[htbp]\centering\small
\caption{Efecto del balanceo de clases en las predicciones reunidas de validación (2022--2024; tasa real de alzas del """ + n(BL.tasa_real.iloc[0] * 100, 1) + r"""\,\%): AP y probabilidad media pronosticada}\label{tab:balanceo}
\begin{tabular}{lrrrrrr}\toprule
& \multicolumn{3}{c}{AP} & \multicolumn{3}{c}{Probabilidad media (\%)}\\ \cmidrule(lr){2-4}\cmidrule(lr){5-7}
Modelo & Sin balanceo & Pesos & Submuestreo & Sin balanceo & Pesos & Submuestreo\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
# SARIMA: error por grupo en validación y prueba
SA = pd.read_parquet(RES / "sarima.parquet"); SA["mes_obj"] = pd.to_datetime(SA.mes_obj)
Py = Pg[["mercado", "alimento", "mes_obj", "y", "g"]].copy(); Py["mes_obj"] = pd.to_datetime(Py.mes_obj)
def _err(cortes):
    d = SA[SA.corte.isin(cortes)].merge(Py, on=["mercado", "alimento", "mes_obj"])
    return d.assign(es=(d.y - d.pred).abs(), er=d.y.abs()).groupby("g")[["es", "er"]].mean(), d.assign(es=(d.y - d.pred).abs(), er=d.y.abs())[["es", "er"]].mean()
gv_, tv_ = _err(["cv0", "cv1", "cv2"]); gt_, tt_ = _err(["prueba"])
f = [f"Todo el panel & {n(tv_.er * 100, 2)} & {n(tv_.es * 100, 2)} & {n((1 - tv_.es / tv_.er) * 100, 1)} & {n(tt_.er * 100, 2)} & {n(tt_.es * 100, 2)} & {n((1 - tt_.es / tt_.er) * 100, 1)} \\\\ \\midrule"]
for g in dg.index:
    a, b2 = gv_.loc[g], gt_.loc[g]
    f.append(f"{esc(g)} & {n(a.er * 100, 2)} & {n(a.es * 100, 2)} & {n((1 - a.es / a.er) * 100, 1)} & {n(b2.er * 100, 2)} & {n(b2.es * 100, 2)} & {n((1 - b2.es / b2.er) * 100, 1)} \\\\")
escribir("tab_sarima_error", r"""\begin{table}[htbp]\centering\small
\caption{MAE (puntos porcentuales) del último precio y de SARIMA en validación (2022--2024) y en prueba, y reducción del error de SARIMA (\%)}\label{tab:sarima_error}
\begin{tabular}{lrrrrrr}\toprule
& \multicolumn{3}{c}{Validación} & \multicolumn{3}{c}{Prueba}\\ \cmidrule(lr){2-4}\cmidrule(lr){5-7}
Grupo & Últ. precio & SARIMA & Reducción & Últ. precio & SARIMA & Reducción\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
CP = json.loads((RES / "complementos.json").read_text()) if (RES / "complementos.json").exists() else {}
if CP and R:
    s_ = CP["sarima"]; f = [f"Series estimadas & {n(s_['series'], 0)} \\\\", f"Con una diferencia regular ($d\\ge1$) & {n(s_['d1'] * 100, 1)}\\,\\% \\\\",
                            f"Con diferencia estacional ($D\\ge1$) & {n(s_['D1'] * 100, 1)}\\,\\% \\\\", f"Con algún término estacional & {n(s_['estac'] * 100, 1)}\\,\\% \\\\",
                            f"Residuos sin autocorrelación (Ljung--Box, 12 rezagos, $p>0{{,}}05$) & {n(s_['lb12'] * 100, 1)}\\,\\% \\\\",
                            f"Residuos sin autocorrelación (Ljung--Box, 24 rezagos, $p>0{{,}}05$) & {n(s_['lb24'] * 100, 1)}\\,\\% \\\\", r"\midrule", r"\multicolumn{2}{l}{Órdenes más frecuentes $(p,d,q)(P,D,Q)_{12}$} \\"]
    f += [f"\\quad {o} & {n(c / s_['series'] * 100, 1)}\\,\\% \\\\" for o, c in s_["ordenes"].items()]
    escribir("tab_sarima", r"""\begin{table}[htbp]\centering\small
\caption{Modelos SARIMA estimados con datos hasta 2024 (corte de la prueba): órdenes elegidos y diagnóstico de residuos}\label{tab:sarima}
\begin{tabular}{lr}\toprule
Característica & Valor\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    TT2 = pd.DataFrame(R["reg_tabla"]).set_index("modelo"); TC3 = pd.DataFrame(R["clf_tabla"]).set_index("modelo"); f = []
    for m in ["Paseo aleatorio", "AR estacional"] + MR:
        f.append(f"{esc(m)}" + (r"$^\ast$" if m == ER else "") + f" & {n(CP['reg_entrenamiento'][m] * 100, 2)} & {n(TT2.loc[m, 'mae_val'] * 100, 2)} & {n(TT2.loc[m, 'mae'] * 100, 2)} \\\\")
    f2 = []
    for m in ["Logística autorregresiva"] + MC:
        pv_ = n(TC3.loc[m, "pr_val"], 3) if m in MC else "--"
        f2.append(f"{esc(m)}" + (r"$^\ast$" if m == EC else "") + f" & {n(CP['clf_entrenamiento'][m], 3)} & {pv_} & {n(TC3.loc[m, 'pr_auc'], 3)} \\\\")
    escribir("tab_entrenamiento", r"""\begin{table}[htbp]\centering\small
\caption{Desempeño en entrenamiento (ajuste y evaluación con 2019--2024), validación (promedio de 2022--2024 en regresión; predicciones reunidas en clasificación) y prueba. Una diferencia grande entre entrenamiento y prueba indica sobreajuste. Las cifras de validación son optimistas, porque esa muestra se usó para varias decisiones; la única evaluación imparcial es la de prueba.}\label{tab:entrenamiento}
\begin{tabular}{lrrr}\toprule
Modelo & Entrenamiento & Validación & Prueba\\ \midrule
\multicolumn{4}{l}{\emph{Cambio del mes siguiente: MAE (p. p.)}}\\
""" + "\n".join(f) + r"""
\midrule
\multicolumn{4}{l}{\emph{Alzas mayores al 15\,\%: AP}}\\
""" + "\n".join(f2) + "\n\\bottomrule\\end{tabular}\\end{table}\n")

# ---------- tablas del EDA complementario (paso 14) ----------
if (RES / "eda2.json").exists():
    E2 = json.loads((RES / "eda2.json").read_text())
    cif["faltserie"] = n(E2["falt_total"], 1); cif["nhuecos"] = n(E2["huecos"]["n"], 0)
    for k_, nm in (("1 mes", "uno"), ("2 meses", "dos"), ("3 a 6 meses", "tres"), ("Más de 6", "largo")):
        cif["hueco" + nm] = n(E2["huecos"]["pct"][k_], 0); cif["huecomes" + nm] = n(E2["huecos"]["pct_meses"][k_], 0)
    fo = E2["falt_objetivo"]; ob, fa = fo["por_estado"][0], fo["por_estado"][1]
    escribir("tab_falt_mecanismo", r"""\begin{table}[htbp]\centering\small
\caption{¿Faltan al azar los precios del mes siguiente? Pares serie--mes con precio observado en $t$ según falte o no el precio en $t+1$, y lo que pasó con el mismo producto en las demás centrales en $t+1$}\label{tab:falt_mecanismo}
\begin{tabular}{lrrr}\toprule
Precio en $t+1$ & Casos & Cambio medio en las demás centrales (\%) & Alzas en las demás centrales (\%)\\ \midrule
Observado & """ + n(ob["n"], 0) + " & " + n(ob["cambio_otras"] * 100, 1) + " & " + n(ob["prop_alza_otras"] * 100, 1) + r""" \\
Faltante & """ + n(fa["n"], 0) + " & " + n(fa["cambio_otras"] * 100, 1) + " & " + n(fa["prop_alza_otras"] * 100, 1) + r""" \\ \bottomrule
\end{tabular}\end{table}
""")
    CT_ = pd.read_csv(RES / "eda2_centrales.csv")
    f = [f"{esc(r.central)} & {esc(r.ciudad)} & {r.series} & {n(r.con_precio, 1)} & {n(r.mediana_abs, 1)} & {n(r.alza, 1)} \\\\" for r in CT_.itertuples()]
    escribir("tab_centrales", r"""\begin{table}[htbp]\centering\scriptsize
\caption{Cobertura por central: series en el panel, porcentaje de meses con precio desde que empieza cada serie, mediana del cambio mensual absoluto (p.~p.) y porcentaje de alzas mayores al 15\,\%}\label{tab:centrales}
\begin{tabular}{llrrrr}\toprule
Central & Ciudad & Series & Con precio (\%) & Cambio típico & Alzas (\%)\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    PE_ = pd.read_csv(RES / "eda2_persistencia.csv")
    f = [f"{esc(r.estado)} & {n(r.n, 0)} & {n(r.p_alza * 100, 1)} & {n(r.p_baja * 100, 1)} \\\\" for r in PE_.itertuples()]
    escribir("tab_persistencia", r"""\begin{table}[htbp]\centering\small
\caption{Persistencia de los movimientos fuertes en entrenamiento: probabilidad de un alza o una baja de más del 15\,\% en el mes siguiente según lo que pasó en el mes actual}\label{tab:persistencia}
\begin{tabular}{lrrr}\toprule
Mes actual & Casos & Alza en $t+1$ (\%) & Baja en $t+1$ (\%)\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    VO_ = pd.read_csv(RES / "eda2_volatiles.csv")
    a_ = VO_[VO_.lado == "más"].reset_index(drop=True); b_ = VO_[VO_.lado == "menos"].reset_index(drop=True)
    f = [f"{esc(a_.alimento[i])} & {n(a_.med[i], 1)} & {n(a_.alza[i] * 100, 0)} & {esc(b_.alimento[i])} & {n(b_.med[i], 1)} & {n(b_.alza[i] * 100, 0)} \\\\" for i in range(10)]
    escribir("tab_volatiles", r"""\begin{table}[htbp]\centering\small
\caption{Los diez productos con mayor y menor cambio mensual típico (mediana del cambio absoluto, p.~p.) y su porcentaje de alzas mayores al 15\,\%, entre los """ + str(E2["n_productos_vol"]) + r""" productos con al menos 300 observaciones}\label{tab:volatiles}
\begin{tabular}{lrrlrr}\toprule
\multicolumn{3}{c}{Más volátiles} & \multicolumn{3}{c}{Menos volátiles}\\ \cmidrule(lr){1-3}\cmidrule(lr){4-6}
Producto & Cambio & Alzas & Producto & Cambio & Alzas\\ \midrule
""" + "\n".join(f) + "\n\\bottomrule\\end{tabular}\\end{table}\n")

assert not any(ch.isdigit() for k in cif for ch in k), [k for k in cif if any(ch.isdigit() for ch in k)]
(TAB / "cifras.tex").write_text("% Cifras generadas por 08_latex.py\n" + "\n".join(f"\\newcommand{{\\c{k.replace('_', '')}}}{{{v}}}" for k, v in cif.items()) + "\n", encoding="utf-8")

USADAS = ["fig_datos", "fig_tiempo", "fig_autocorrelacion", "fig_bloques", "fig_modelos", "fig_grupos", "fig_productos", "fig_mensual", "fig_caso", "fig_roc_pr", "fig_calibracion", "fig_importancia", "fig_roc_modelos", "fig_shap", "fig_shap_casos", "fig_residuos", "fig_nemenyi", "fig_stl", "fig_distribucion", "fig_faltantes", "fig_cajas", "fig_correlaciones", "fig_pred_obs", "fig_confusion", "fig_sarima_ejemplo", "fig_sarima_residuos", "fig_anos", "fig_estacional_productos", "fig_abastecimiento", "fig_oni", "fig_acf_ejemplo"] + [k for k in ("fig_busqueda",) if (FIG / f"{k}.pdf").exists()]
for p_ in FIGD.glob("*"): p_.unlink()
for k in USADAS: shutil.copy(FIG / f"{k}.pdf", FIGD / f"{k}.pdf")
TABLAS = {"cifras", "tab_falt_mecanismo", "tab_centrales", "tab_persistencia", "tab_volatiles", "tab_embudo", "tab_resumen_y", "tab_explicativas", "tab_adf", "tab_delong", "tab_balanceo", "tab_sarima_error", "tab_sarima", "tab_entrenamiento", "tab_costo", "tab_grupos", "tab_alertas", "tab_grupos_modelos", "tab_pasos", "tab_robustez", "tab_reg", "tab_clf", "tab_cqr", "tab_bloques", "tab_hiper", "tab_tiempos", "tab_verificacion", "tab_muestras", "tab_reg_extra", "tab_clf_extra", "tab_lineales", "tab_cobertura", "tab_variables", "cifras_revision"}
for p_ in TAB.glob("*.tex"):
    if p_.stem not in TABLAS: p_.unlink()
print(len(cif), "cifras;", sorted(p.name for p in TAB.glob("*.tex")))
