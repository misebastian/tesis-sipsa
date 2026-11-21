"""Unifica las series históricas de precios mayoristas SIPSA-P (DANE) 2018-2025.
Formatos encontrados:
  2018        una hoja '2018'; columnas Fecha, Grupo, Producto, Fuente, Precio
  2019-2023   una hoja por mes; columna de mercado 'Fuente' (2019) o 'Mercado' (2020+)
  2024-2025   una hoja larga; 2025 agrega 'Código CPC'
En todos los casos el encabezado se detecta buscando la fila cuya primera celda es 'Fecha'.
Uso: python precios_unify.py <carpeta_con_xlsx> <carpeta_salida>"""
import sys, glob, os, re, unicodedata
import openpyxl, pandas as pd, numpy as np

SRC, OUT = sys.argv[1], sys.argv[2]


def norm_txt(s):
    s = unicodedata.normalize("NFKC", str(s)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def col_key(h):
    h = norm_txt(h).lower()
    if h.startswith("fecha"): return "fecha"
    if h.startswith("grupo"): return "grupo"
    if h.startswith("producto"): return "producto"
    if h.startswith("código cpc") or h.startswith("codigo cpc"): return "cod_cpc"
    if h.startswith("mercado") or h.startswith("fuente"): return "mercado"
    if h.startswith("precio"): return "precio"
    return None


def read_sheet(ws, fname):
    rows = ws.iter_rows(values_only=True); cols = None; out = []
    for r in rows:
        if cols is None:
            if r and isinstance(r[0], str) and norm_txt(r[0]).lower() == "fecha":
                cols = {i: col_key(h) for i, h in enumerate(r) if h is not None and col_key(h)}
            continue
        if r[0] is None or isinstance(r[0], str):   # filas vacías o notas al pie
            continue
        out.append({k: r[i] for i, k in cols.items() if i < len(r)})
    if cols is None: return None
    d = pd.DataFrame(out); d["archivo"] = os.path.basename(fname); d["hoja"] = ws.title
    return d


parts, log = [], []
for f in sorted(glob.glob(os.path.join(SRC, "*.xlsx"))):
    wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
    for ws in wb.worksheets:
        if ws.title.lower() in ("índice", "indice", "cpc"): continue
        d = read_sheet(ws, f)
        if d is None or d.empty: log.append((os.path.basename(f), ws.title, 0)); continue
        parts.append(d); log.append((os.path.basename(f), ws.title, len(d)))
P = pd.concat(parts, ignore_index=True)

# --- limpieza
P["fecha"] = pd.to_datetime(P["fecha"], errors="coerce")
for c in ["grupo", "producto", "mercado"]: P[c] = P[c].map(norm_txt)
P["grupo"] = P["grupo"].str.upper()
P["precio_raw"] = P["precio"]
P["precio"] = pd.to_numeric(P["precio"].astype(str).str.replace(r"[^\d.,-]", "", regex=True).str.replace(",", "."), errors="coerce")
P["cod_cpc"] = P.get("cod_cpc", pd.Series(index=P.index, dtype=object)).astype("string").str.strip()
P["unidad"] = np.where(P.producto.str.contains(r"^Huevo|Bocadillo", case=False), "$/unidad",
              np.where(P.producto.str.contains(r"Aceite|Vinagre|Jugo", case=False), "$/litro", "$/kg"))
# mercado: separar ciudad y nombre de la central ("Bogotá, D.C., Corabastos" -> ciudad "Bogotá, D.C.", central "Corabastos")
def split_m(m):
    if "," not in m: return m, ""
    if m.startswith("Bogotá, D.C."): return "Bogotá, D.C.", m[len("Bogotá, D.C."):].lstrip(", ").strip()
    a, b = m.split(",", 1); return a.strip(), b.strip()
P[["ciudad", "central"]] = P.mercado.apply(lambda m: pd.Series(split_m(m)))
P["anio"] = P.fecha.dt.year; P["mes"] = P.fecha.dt.month
P = P[["fecha", "anio", "mes", "grupo", "producto", "cod_cpc", "mercado", "ciudad", "central", "precio", "unidad", "precio_raw", "archivo", "hoja"]]
P.to_parquet(os.path.join(OUT, "sipsa_p_precios_raw_union.parquet"), index=False)
pd.DataFrame(log, columns=["archivo", "hoja", "filas"]).to_csv(os.path.join(OUT, "sipsa_p_log_lectura.csv"), index=False)
print(P.shape); print(pd.DataFrame(log, columns=["archivo", "hoja", "filas"]).groupby("archivo").filas.agg(["count", "sum"]))
