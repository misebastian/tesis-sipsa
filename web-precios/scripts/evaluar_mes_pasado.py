"""Compara el pronóstico del mes anterior con el precio que el DANE publicó después y escribe public/data/evaluacion.json.
Cada mes, antes de generar los pronósticos nuevos, guarde el pronosticos.json vigente en public/data/historial/
como pronosticos_<mes pronosticado>.json (por ejemplo, pronosticos_2026-11.json).
Uso: python scripts/evaluar_mes_pasado.py datos/base_mensual_web.parquet [public/data/historial/pronosticos_2026-10.json]
     (sin el segundo argumento toma el archivo del historial cuyo mes es el último de la base)."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd

AQUI = Path(__file__).resolve().parents[1] / "public" / "data"
B = pd.read_parquet(sys.argv[1]); ult = B.mes.max().strftime("%Y-%m")
arch = Path(sys.argv[2]) if len(sys.argv) > 2 else AQUI / "historial" / f"pronosticos_{ult}.json"
F = json.load(open(arch)); mes = F["mes_pronostico"]
R = B[(B.mes == mes + "-01") & B.precio.notna() & B.unidad.eq("$/kg")].set_index(["mercado", "alimento"]).precio
filas = []
for s in F["series"]:
    k = (s["central"], s["producto"])
    if k not in R.index: continue
    real = float(R[k]); p0 = s["precio_actual"]
    filas.append(dict(central=s["central"], ciudad=s["ciudad"], producto=s["producto"], grupo=s["grupo"], antes=p0,
                      esperado=s["precio_esperado"], lo=s["rango"][0], hi=s["rango"][1], real=round(real), prob=s["prob_alza"], riesgo=s["riesgo"],
                      y=np.log(real / p0), yhat=np.log(s["precio_esperado"] / p0)))
D = pd.DataFrame(filas)
D["err_m"] = (D.y - D.yhat).abs(); D["err_n"] = D.y.abs(); D["dentro"] = (D.real >= D.lo) & (D.real <= D.hi); D["alza"] = D.y > np.log(1.15)
red = lambda d: round(100 * (1 - d.err_m.mean() / d.err_n.mean()), 1)
grupos = [dict(grupo=g, n=int(len(d)), reduccion=red(d), err_modelo=round(100 * d.err_m.mean(), 1), err_ultimo=round(100 * d.err_n.mean(), 1))
          for g, d in D.groupby("grupo") if len(d) >= 20]
alertas = lambda r: dict(n=int((D.riesgo == r).sum()), aciertos=int(((D.riesgo == r) & D.alza).sum()))
salida = dict(
    mes=mes, pronostico_hecho_con=F["ultimo_mes"], n=int(len(D)),
    err_modelo=round(100 * D.err_m.mean(), 1), err_ultimo=round(100 * D.err_n.mean(), 1), reduccion=red(D),
    cobertura=round(100 * D.dentro.mean(), 1), alzas=int(D.alza.sum()),
    alzas_con_alerta=int((D.alza & D.riesgo.isin(["alto", "medio"])).sum()),
    alto=alertas("alto"), medio=alertas("medio"), grupos=sorted(grupos, key=lambda g: -g["reduccion"]),
    alertas_altas=[dict(central=r.central, ciudad=r.ciudad, producto=r.producto, antes=r.antes, esperado=r.esperado, real=r.real,
                        prob=r.prob, cambio_real=round(100 * float(np.expm1(r.y)), 1), alza=bool(r.alza))
                   for r in D[D.riesgo == "alto"].sort_values("prob", ascending=False).itertuples()],
    series={f"{r.central}|{r.producto}": [r.antes, r.esperado, r.lo, r.hi, r.real] for r in D.itertuples()},
)
json.dump(salida, open(AQUI / "evaluacion.json", "w"), ensure_ascii=False, separators=(",", ":"))
print({k: v for k, v in salida.items() if k not in ("series", "alertas_altas", "grupos")}); print(salida["grupos"])
