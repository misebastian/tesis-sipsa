"""Corrige la regla de la variedad de referencia (observación 13 del tutor).
La base original eligió, para cada central y alimento con varias variedades, la variedad con más meses de precio
contando 2018-2025. Aquí se repite la elección contando solo meses hasta diciembre de 2024 y, en los pares donde
la variedad cambia, se reemplaza el precio de todos los meses por el de la nueva variedad (2018-2025 desde la serie
histórica del SIPSA-P; 2026 desde el anexo de 2026). Donde la nueva variedad no tiene precio, el precio queda vacío.
Uso: python corregir_variedad.py <base_unida_mensual.parquet> <sipsa_p_precios_2018_2025.parquet> <anexo_2026.xlsx> <salida.parquet> <informe.json>"""
import sys, json, re, unicodedata, importlib.util, os
import numpy as np, pandas as pd
base, hist, anexo, salida, informe = sys.argv[1:6]
spec = importlib.util.spec_from_file_location("am", os.path.join(os.path.dirname(os.path.abspath(__file__)), "agregar_meses.py"))
am = importlib.util.module_from_spec(spec); spec.loader.exec_module(am)
EQ, fold = am.EQ, am.fold
CORTE = pd.Timestamp("2024-12-01")
B = pd.read_parquet(base)
H = pd.read_parquet(hist); H = H[H.en_abastecimiento].copy()
H["mercado"] = H.mercado_sipsa_a.str.replace("Pereira, La 41-Impala", "Pereira, La 41", regex=False)
H["mes"] = pd.to_datetime(H.fecha)
def elegir(Q):
    cov = Q.groupby(["mercado", "producto"]).mes.nunique()
    def ref(m, a):
        c = [v for v in EQ[a] if (m, v) in cov.index]
        return max(c, key=lambda v: cov[(m, v)]) if c else EQ[a][0]
    return ref
r_orig, r_corte = elegir(H), elegir(H[H.mes <= CORTE])
pares = B[B.alimento.isin(EQ)][["mercado", "alimento"]].drop_duplicates()
pares["antes"] = [r_orig(m, a) for m, a in zip(pares.mercado, pares.alimento)]
pares["ahora"] = [r_corte(m, a) for m, a in zip(pares.mercado, pares.alimento)]
cambian = pares[pares.antes != pares.ahora]
P = am.leer_precios(anexo).rename(columns={"fecha": "mes"})
canon = {fold(x): x for x in B.mercado.unique()}
P["mercado"] = P.mercado.map(lambda m: canon.get(fold(m), m))
fuente = pd.concat([H[["mercado", "producto", "mes", "precio"]], P.loc[P.mes > H.mes.max(), ["mercado", "producto", "mes", "precio"]]])
fuente["k"] = fuente.producto.map(fold)
fuente = fuente.groupby(["mercado", "k", "mes"], as_index=False).precio.mean()
detalle = []
for _, r in cambian.iterrows():
    sel = (B.mercado == r.mercado) & (B.alimento == r.alimento)
    nuevo = fuente[(fuente.mercado == r.mercado) & (fuente.k == fold(r.ahora))].set_index("mes").precio
    antes_con = int(B.loc[sel, "precio"].notna().sum())
    B.loc[sel, "precio"] = B.loc[sel, "mes"].map(nuevo).values
    B.loc[sel & B.precio.notna(), "unidad"] = "$/kg"
    B.loc[sel & B.precio.isna(), "unidad"] = None
    detalle.append(dict(mercado=r.mercado, alimento=r.alimento, variedad_antes=r.antes, variedad_ahora=r.ahora,
                        meses_con_precio_antes=antes_con, meses_con_precio_ahora=int(B.loc[sel, "precio"].notna().sum()),
                        ultimo_mes_con_precio=str(B.loc[sel & B.precio.notna(), "mes"].max().date())))
B.to_parquet(salida, index=False)
rep = dict(corte=str(CORTE.date()), pares_con_variedad=len(pares), pares_que_cambian=len(cambian), detalle=detalle)
json.dump(rep, open(informe, "w"), ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False, indent=1))
