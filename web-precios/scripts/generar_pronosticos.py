"""Genera public/data/pronosticos.json para la página web a partir del estudio de la tesis.

Usa los modelos finales guardados (CatBoost de regresión y de clasificación), construye las variables del último mes
publicado con el mismo código del panel (01_panel.py) y calcula:
  - el precio esperado del mes siguiente y su rango del 80 % (cuantiles con calibración conforme, como el paso 11);
  - la probabilidad de un alza mayor al 15 % (con la recalibración del intercepto de la tesis);
  - tres razones en lenguaje sencillo a partir de los valores de Shapley del clasificador;
  - el precio de los últimos 13 meses de cada serie para la gráfica.

Uso (desde la carpeta web-precios, con el entorno de Python del estudio):
  ../entorno/bin/python scripts/generar_pronosticos.py ../estudio
"""
import sys, os, json, contextlib, io, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd, joblib, lightgbm as lgb
from scipy.special import expit, logit

ESTUDIO = Path(sys.argv[1] if len(sys.argv) > 1 else "../estudio").resolve()
SALIDA = Path(__file__).resolve().parents[1] / "public" / "data" / "pronosticos.json"
os.chdir(ESTUDIO); sys.path.insert(0, str(ESTUDIO))
from comun import *                     # noqa: E402  (DATOS, RES, NUCLEOS, SEMILLA, cargar_panel, variables_finales, leer_json)
from modelos import matrices            # noqa: E402
from catboost import Pool               # noqa: E402

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
ALTO, MEDIO = 0.60, 0.30                # umbrales del semáforo (probabilidad de alza)

# ---------- 1. variables del último mes publicado (mismo código del panel) ----------
src = (Path("01_panel.py").read_text()
       .replace("(P.mes < meses[-1])", "(P.mes <= meses[-1])")          # conservar el último mes, que aún no tiene objetivo
       .replace("    return P\n", "    return P, sin, fa, em\n")
       .replace('if __name__ == "__main__":', "if False:"))
ns = {}
exec(compile(src, "01_panel_web", "exec"), ns)
with contextlib.redirect_stdout(io.StringIO()):
    _, sin, fa, em = ns["construir"](guardar=False)
ult = sin.mes.max()
X = sin[sin.mes == ult].copy()

# En el mes a pronosticar todavía no hay datos del mes objetivo, y las variables estacionales históricas del panel se unen
# por año y mes objetivo: quedarían vacías. Se calculan con todos los años anteriores, que es lo que significan.
fa_t = fa.groupby(["alimento", "m"])[["s", "n"]].sum().reset_index(); fa_t["f_"] = (fa_t.s + 1) / (fa_t.n + 6)
em_t = em.groupby(["mercado", "alimento", "m"]).r.mean().rename("e_").reset_index()
X["m_"] = X.mes_obj.dt.month
X = (X.merge(fa_t[["alimento", "m", "f_"]].rename(columns={"m": "m_"}), how="left", on=["alimento", "m_"])
      .merge(em_t.rename(columns={"m": "m_"}), how="left", on=["mercado", "alimento", "m_"]))
X["frec_alza_hist"] = X.frec_alza_hist.fillna(X.f_)
X["cambio_estacional_hist"] = X.cambio_estacional_hist.fillna(X.e_)
X = X.drop(columns=["m_", "f_", "e_"]).reset_index(drop=True)

P = cargar_panel()
for k in ("grupo", "ciudad", "mercado", "alimento"):           # mismos códigos de categoría que en la tesis
    X[k + "_c"] = X[k].map(dict(zip(P[k], P[k + "_c"])))
V = variables_finales(); GRP = sorted(P.grupo.unique())
_, Xb = matrices(V, GRP, "arbol", P.head(5), X)

# ---------- 2. modelos guardados ----------
reg = joblib.load(RES / "modelos" / "reg_CatBoost.joblib")
clf = joblib.load(RES / "modelos" / "clf_CatBoost.joblib")
a_cal = leer_json("clf_seleccion.json")["recalibracion"]["CatBoost"]["intercepto"]
X["cambio"] = reg.predict(Xb)
X["prob"] = expit(a_cal + logit(np.clip(clf.predict_proba(Xb)[:, 1], 1e-6, 1 - 1e-6)))
SH = clf.get_feature_importance(Pool(Xb), type="ShapValues")[:, :-1]

# ---------- 3. rango del 80 %: cuantiles hasta 2023 y calibración conforme por grupo con 2024 (paso 11) ----------
hq = leer_json("complementarios.json")["cuantiles_busqueda"]["params"]
qmod = lambda t: lgb.LGBMRegressor(objective="quantile", alpha=t, n_estimators=hq["n"], learning_rate=hq["lr"], num_leaves=hq["hojas"],
                                   min_child_samples=hq["mcs"], subsample=hq["ss"], subsample_freq=1, colsample_bytree=hq["cs"],
                                   reg_lambda=hq["l2"], n_jobs=NUCLEOS, random_state=SEMILLA, verbose=-1)
tr, va = P[P.muestra == "entrenamiento"], P[P.muestra == "validacion"]
Xa, Xv = matrices(V, GRP, "arbol", tr, va); _, Xn = matrices(V, GRP, "arbol", tr, X)
q10, q90 = qmod(.10).fit(Xa, tr.y.values), qmod(.90).fit(Xa, tr.y.values)
lv, hv = np.sort(np.column_stack([q10.predict(Xv), q90.predict(Xv)]), axis=1).T
ln, hn = np.sort(np.column_stack([q10.predict(Xn), q90.predict(Xn)]), axis=1).T
PER = ["FRUTAS", "VERDURAS Y HORTALIZAS", "TUBERCULOS, RAICES Y PLATANOS"]
gv, gn = np.where(va.grupo.isin(PER), "P", "N"), np.where(X.grupo.isin(PER), "P", "N")
sc = np.maximum(lv - va.y.values, va.y.values - hv)
for g in ("P", "N"):
    n_ = (gv == g).sum(); qh = np.quantile(sc[gv == g], min(1, np.ceil((n_ + 1) * .8) / n_))
    ln[gn == g] -= qh; hn[gn == g] += qh

# ---------- 4. precios observados ----------
B = pd.read_parquet(DATOS / "base_unida_mensual.parquet")
B = B[B.unidad.eq("$/kg") & B.precio.notna()]
hist_desde = ult - pd.DateOffset(months=12)
H = B[B.mes >= hist_desde].set_index(["mercado", "alimento"])

# ---------- 5. razones en lenguaje sencillo ----------
pct = lambda v: int(round(abs(np.expm1(v)) * 100))


def razon(var, v, mes_obj):
    """Texto de una razón según la variable y su valor; None si la variable no se explica al usuario."""
    if pd.isna(v):
        return None
    m = MESES[mes_obj.month - 1]
    if var == "cambio_estacional_hist":
        return ("Es temporada de subida." if v > 0 else "Es temporada de bajada.",
                f"En {m}, este precio suele {'subir' if v > 0 else 'bajar'} cerca de {pct(v)} % en esta central.")
    if var == "frec_alza_hist":
        return ("Pasa con frecuencia en este mes.", f"En {m}, este producto ha tenido alzas fuertes en cerca del {int(round(v * 100))} % de los casos.")
    if var == "cambio_nacional_1m":
        return ("Se mueve en otras centrales." if abs(v) > .02 else "Está estable en otras centrales.",
                f"El último mes, en las demás centrales el precio {'subió' if v > 0 else 'bajó'} cerca de {pct(v)} %.")
    if var == "prop_centrales_alza":
        return ("Ya sube en otras centrales." if v >= .3 else "Pocas centrales con alzas.",
                f"En {int(round(v * 10))} de cada 10 de las demás centrales el precio subió más del 15 % el último mes.")
    if var == "dist_max_12m":
        return ("Está lejos de su máximo." if v < -.1 else "Está cerca de su máximo.", f"Está {pct(v)} % por debajo de su precio más alto del último año.")
    if var == "dist_min_12m":
        return ("Está lejos de su mínimo." if v > .1 else "Está cerca de su mínimo.", f"Está {pct(v)} % por encima de su precio más bajo del último año.")
    if var == "cambio_1m":
        return (f"{'Subió' if v > 0 else 'Bajó'} el último mes.", f"El último mes el precio {'subió' if v > 0 else 'bajó'} cerca de {pct(v)} %.")
    if var == "cambio_12m":
        return ("Comparado con hace un año.", f"Está {pct(v)} % {'más caro' if v > 0 else 'más barato'} que hace un año.")
    if var == "brecha_nacional":
        return ("Comparado con otras centrales.", f"Está {pct(v)} % {'más caro' if v > 0 else 'más barato'} que en las demás centrales.")
    if var == "z_precio_12m":
        return ("Comparado con su promedio del año.", f"Está {'por encima' if v > 0 else 'por debajo'} de su precio promedio del último año.")
    if var == "vol_12m":
        return ("Es un precio muy variable." if v > .15 else "Es un precio estable.", "Su precio ha cambiado mucho de un mes a otro en el último año." if v > .15 else "Su precio ha cambiado poco de un mes a otro en el último año.")
    if var in ("cambio_ton_nacional_1m", "ton_nacional_rel_12m"):
        return ("Llega más producto al país." if v > 0 else "Llega menos producto al país.",
                f"A las centrales del país está llegando {'más' if v > 0 else 'menos'} producto que lo habitual.")
    return None


# ---------- 6. JSON ----------
series = []
for i, r in X.iterrows():
    try:
        h = H.loc[(r.mercado, r.alimento)].sort_values("mes")
    except KeyError:
        continue
    if h.empty or h.mes.max() != ult:
        continue
    p0 = float(h.precio.iloc[-1])
    orden = np.argsort(-np.abs(SH[i]))
    razones = []
    for j in orden:
        t = razon(V[j], r[V[j]], r.mes_obj)
        if t and t[0] not in [x["titulo"] for x in razones]:
            razones.append({"titulo": t[0], "texto": t[1]})
        if len(razones) == 3:
            break
    prob = float(r.prob)
    series.append({
        "central": r.mercado, "ciudad": r.ciudad, "producto": r.alimento, "grupo": r.grupo,
        "precio_actual": round(p0), "precio_esperado": round(p0 * np.exp(r.cambio)),
        "rango": [round(p0 * np.exp(ln[i])), round(p0 * np.exp(hn[i]))],
        "cambio_pct": round(float(np.expm1(r.cambio)) * 100, 1),
        "prob_alza": round(prob, 3), "riesgo": "alto" if prob >= ALTO else "medio" if prob >= MEDIO else "bajo",
        "razones": razones,
        "unidad": "kg",   # el panel de la tesis solo usa precios por kilo (unidad $/kg en la base)
        "historia": [[d.strftime("%Y-%m"), round(float(v))] for d, v in zip(h.mes, h.precio)],   # [mes, precio por kilo]
    })

salida = {
    "generado": dt.date.today().isoformat(),
    "ultimo_mes": ult.strftime("%Y-%m"),
    "mes_pronostico": (ult + pd.DateOffset(months=1)).strftime("%Y-%m"),
    "umbrales": {"alto": ALTO, "medio": MEDIO},
    "series": sorted(series, key=lambda s: (s["central"], s["producto"])),
}
SALIDA.parent.mkdir(parents=True, exist_ok=True)
SALIDA.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")))
print(f"{len(series)} series · datos hasta {salida['ultimo_mes']} · pronóstico para {salida['mes_pronostico']} → {SALIDA}")
