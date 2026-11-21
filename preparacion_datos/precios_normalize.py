"""Normaliza la unión cruda de precios SIPSA-P y deja una base lista para cruzar con SIPSA-A.
Decisiones (todas documentadas en el Excel de control):
 1. Mercados: se unifican variantes de mayúsculas y renombres sin solapamiento en el tiempo.
 2. Productos: se unifican variantes que solo difieren en mayúsculas.
 3. Grupo: sin tildes y en mayúsculas (2021 venía con tildes).
 4. Duplicados (fecha, producto, mercado): 12 casos de enlatados en nov-dic 2021; se promedian y se marca n_registros.
 5. Código CPC: solo viene en 2025; se asigna a los demás años por nombre de producto.
 6. producto_red: Papa / Plátano hartón / Tomate chonto con la misma regla usada para la red de abastecimiento.
Uso: python precios_normalize.py <carpeta out>"""
import sys, os, unicodedata, pandas as pd, numpy as np, polars as pl
O = sys.argv[1]
P = pd.read_parquet(f"{O}/sipsa_p_precios_raw_union.parquet")

def fold(s): return unicodedata.normalize("NFKD", s.casefold()).encode("ascii", "ignore").decode()

# --- 1. mercados
RENOMBRES = {  # nombre antiguo -> nombre vigente (verificado: no se solapan en el tiempo)
    "Cali, Santa Helena": "Cali, Santa Elena",
    "Duitama (Boyacá)": "Duitama (Boyacá), Mercaplaza",
    "San Vicente (Antioquia)": "San Vicente Ferrer (Antioquia)",
    "Pereira, La 41-Impala": "Pereira, La 41",
    "Malambo, Atlantico": "Malambo (Atlántico), Carnes y carnes",
    "Bogotá, D.C., Frigorífico Ble Ltda,": "Bogotá, D.C., Frigorífico Ble Ltda.",
    "San Sebastián de Mariquita (Tolima), panela": "San Sebastián de Mariquita (Tolima)",
}
cnt = P.mercado.value_counts()
canon = {}
for m in cnt.index:                                  # variantes de mayúsculas -> forma más frecuente
    k = fold(m); canon.setdefault(k, m)
m1 = P.mercado.map(lambda m: canon[fold(m)])
P["mercado_original"] = P.mercado
P["mercado"] = m1.replace(RENOMBRES)
cambios_m = (P[P.mercado != P.mercado_original].groupby(["mercado_original", "mercado"])
             .agg(filas=("precio", "size"), desde=("fecha", "min"), hasta=("fecha", "max")).reset_index())
cambios_m["motivo"] = np.where(cambios_m.mercado_original.map(fold) == cambios_m.mercado.map(fold), "Mayúsculas", "Renombre sin solapamiento")
cambios_m.loc[cambios_m.mercado_original.eq("Malambo, Atlantico"), "motivo"] = "Mismo mercado: en nov-2021 se reportó con dos nombres y precios casi iguales; se promedian"

# --- 2. productos
pc = P.producto.value_counts(); pcanon = {}
for p in pc.index: pcanon.setdefault(fold(p), p)
P["producto_original"] = P.producto
P["producto"] = P.producto.map(lambda p: pcanon[fold(p)])
cambios_p = P[P.producto != P.producto_original].groupby(["producto_original", "producto"]).size().rename("filas").reset_index()

# --- 3. grupo
P["grupo"] = P.grupo.map(lambda g: unicodedata.normalize("NFKD", g).encode("ascii", "ignore").decode().upper())

# --- 4. duplicados
k = ["fecha", "producto", "mercado"]
dups = P[P.duplicated(k, keep=False)].sort_values(k)[k + ["precio", "hoja"]]
agg = dict(precio=("precio", "mean"), n_registros=("precio", "size"))
first = ["anio", "mes", "grupo", "cod_cpc", "unidad", "mercado_original", "producto_original", "archivo", "hoja"]
for c in first: agg[c] = (c, "first")
Q = P.groupby(k, as_index=False).agg(**agg)
Q["precio"] = Q.precio.round(0)

# --- 5. CPC
cpc = P.dropna(subset=["cod_cpc"]).groupby("producto").cod_cpc.agg(lambda s: s.mode().iat[0])
Q["cod_cpc"] = Q.producto.map(cpc)

# --- ciudad / central
def split_m(m):
    if m.startswith("Bogotá, D.C."): return "Bogotá, D.C.", m[len("Bogotá, D.C."):].lstrip(", ").strip()
    if "," not in m: return m, ""
    a, b = m.split(",", 1); return a.strip(), b.strip()
cc = Q.mercado.map(split_m); Q["ciudad"] = cc.str[0]; Q["central"] = cc.str[1]

# --- 6. producto de la red y cruce de mercados con abastecimiento
Q["producto_red"] = np.select([Q.producto.str.match(r"^Papa ") & ~Q.producto.str.startswith("Papaya"),
                               Q.producto.eq("Plátano hartón verde"), Q.producto.eq("Tomate chonto")],
                              ["Papa", "Plátano hartón", "Tomate chonto"], default=None)
A_m = (pl.scan_parquet(f"{O}/sipsa_a_unificado_2018_2025_v2.parquet").select("mercado").unique().collect().to_series().to_list())
A_std = {}
for m in sorted(A_m): A_std.setdefault(fold(m.replace('"', "")).replace("-impala", ""), m)   # prefiere "Pereira, La 41"
Q["mercado_sipsa_a"] = Q.mercado.map(lambda m: A_std.get(fold(m.replace('"', ""))))
Q["en_abastecimiento"] = Q.mercado_sipsa_a.notna()

cols = ["fecha", "anio", "mes", "grupo", "producto", "cod_cpc", "producto_red", "mercado", "ciudad", "central",
        "mercado_sipsa_a", "en_abastecimiento", "precio", "unidad", "n_registros", "mercado_original", "producto_original", "archivo", "hoja"]
Q = Q[cols].sort_values(["fecha", "grupo", "producto", "mercado"]).reset_index(drop=True)
Q.to_parquet(f"{O}/sipsa_p_precios_2018_2025.parquet", index=False)
Q.drop(columns=["archivo", "hoja"]).to_csv(f"{O}/sipsa_p_precios_2018_2025.csv", index=False, encoding="utf-8-sig")

# --- control de calidad
cob = Q.pivot_table(index="mercado", columns="anio", values="precio", aggfunc="size", fill_value=0)
cob.insert(0, "en_abastecimiento", Q.groupby("mercado").en_abastecimiento.first())
red = (Q.dropna(subset=["producto_red"]).groupby(["producto_red", "producto"])
       .agg(filas=("precio", "size"), mercados=("mercado", "nunique"), desde=("fecha", "min"), hasta=("fecha", "max"),
            precio_mediano=("precio", "median")).reset_index())
pres = Q.groupby("producto").agg(grupo=("grupo", "first"), unidad=("unidad", "first"), cod_cpc=("cod_cpc", "first"),
                                 anios=("anio", lambda s: "".join("X" if y in set(s) else "." for y in range(2018, 2026))),
                                 filas=("precio", "size"), mercados=("mercado", "nunique")).reset_index()
res = Q.groupby("anio").agg(filas=("precio", "size"), meses=("mes", "nunique"), productos=("producto", "nunique"),
                            mercados=("mercado", "nunique"), precio_mediano=("precio", "median")).reset_index()
log = pd.read_csv(f"{O}/sipsa_p_log_lectura.csv")
with pd.ExcelWriter(f"{O}/sipsa_p_control_unificacion.xlsx") as xw:
    pd.DataFrame({"Hoja": ["resumen_anual", "lectura", "cambios_mercado", "cambios_producto", "duplicados", "cobertura_mercado_anio", "productos", "productos_red"],
                  "Contenido": ["Filas, meses, productos y mercados por año", "Filas leídas por archivo y hoja (96 hojas)",
                                "Nombres de mercado unificados y motivo", "Nombres de producto unificados (solo mayúsculas)",
                                "Registros repetidos (fecha, producto, mercado) antes de promediar. Nota: los saltos de precio de mayo-2021 en Cali y Buenaventura son reales (paro nacional), no se corrigen",
                                "Número de precios por mercado y año; marca si el mercado está en SIPSA-A",
                                "Catálogo de productos: grupo, unidad, código CPC y años en que aparece",
                                "Variedades de papa, plátano hartón y tomate chonto con precio"]}).to_excel(xw, "LEEME", index=False)
    res.to_excel(xw, "resumen_anual", index=False); log.to_excel(xw, "lectura", index=False)
    cambios_m.to_excel(xw, "cambios_mercado", index=False); cambios_p.to_excel(xw, "cambios_producto", index=False)
    dups.to_excel(xw, "duplicados", index=False); cob.to_excel(xw, "cobertura_mercado_anio")
    pres.to_excel(xw, "productos", index=False); red.to_excel(xw, "productos_red", index=False)
print(Q.shape); print(res.to_string()); print(cambios_m.to_string()); print(cambios_p.to_string())
print("mercados con abastecimiento:", Q[Q.en_abastecimiento].mercado.nunique(), "de", Q.mercado.nunique())
print("mercados SIPSA-A sin precio:", sorted(set(A_m) - set(Q.mercado_sipsa_a.dropna())))
print(red.to_string())
