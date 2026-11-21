"""Auditoría de los anexos SIPSA-P (precios mayoristas): recorre todas las hojas de cada libro, detecta la fila de
encabezado, normaliza columnas y registra filas, nulos, duplicados y meses por hoja."""
import json, os, sys, unicodedata
import pandas as pd, openpyxl

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
os.makedirs(SALIDA, exist_ok=True)


def clave(c):
    c = unicodedata.normalize("NFKC", str(c)).strip().lower()
    if c == "fecha": return "fecha"
    if c == "grupo": return "grupo"
    if c == "producto": return "producto"
    if c in ("mercado", "fuente"): return "mercado"
    if "cpc" in c: return "cod_cpc"
    if c.startswith("precio"): return "precio"
    return None  # Departamento, municipio y sus códigos (solo 2026) describen la central: se ignoran


informe, partes = [], []
for f in sorted(os.listdir(ENTRADA)):
    if not f.endswith(".xlsx"): continue
    wb = openpyxl.load_workbook(os.path.join(ENTRADA, f), read_only=True, data_only=True)
    for ws in wb.worksheets:
        filas = list(ws.iter_rows(values_only=True))
        enc = next((i for i, r in enumerate(filas[:30]) if r and "Fecha" in [str(x).strip() for x in r if x is not None]
                    and any(str(x).strip() == "Producto" for x in r if x is not None)), None)
        if enc is None:
            informe.append(dict(archivo=f, hoja=ws.title, usada=False, motivo="sin encabezado de precios", filas=len(filas)))
            continue
        cab = filas[enc]
        idx = {clave(x): i for i, x in enumerate(cab) if x is not None and clave(x)}
        ignoradas = [str(x).strip() for x in cab if x is not None and not clave(x)]
        cuerpo = [r for r in filas[enc + 1:] if r and any(v is not None for v in r)]
        d = pd.DataFrame({k: [r[i] if i < len(r) else None for r in cuerpo] for k, i in idx.items()})
        if "cod_cpc" not in d: d["cod_cpc"] = None
        n = len(d)
        es_fecha = d.fecha.map(lambda v: hasattr(v, "year"))
        pie = d[~es_fecha]  # notas al pie (fuente, asteriscos)
        d = d[es_fecha].copy()
        d["fecha"] = pd.to_datetime(d.fecha)
        precio_txt = d.precio.astype(str)
        d["precio"] = pd.to_numeric(d.precio, errors="coerce")
        for c in ["grupo", "producto", "mercado", "cod_cpc"]:
            d[c] = d[c].astype("string").str.strip()
        meses = d.fecha.dt.to_period("M").value_counts().sort_index()
        dia1 = bool((d.fecha.dt.day == 1).all())
        informe.append(dict(archivo=f, hoja=ws.title, usada=True, fila_encabezado=enc + 1, encabezado=[str(x).strip() for x in cab if x is not None],
                            columnas_ignoradas=ignoradas, filas=n, filas_pie=len(pie), ejemplos_pie=[str(v)[:80] for v in pie.fecha.head(3)],
                            filas_datos=len(d), meses={str(k): int(v) for k, v in meses.items()}, fechas_dia_1=dia1,
                            precio_no_numerico=int(d.precio.isna().sum()),
                            ejemplos_precio_no_numerico=precio_txt[d.precio.isna()].unique()[:6].tolist(),
                            precio_min=float(d.precio.min()), precio_max=float(d.precio.max()), precio_cero=int((d.precio == 0).sum()),
                            nulos={c: int(d[c].isna().sum()) for c in ["grupo", "producto", "mercado", "cod_cpc"]},
                            duplicados_clave=int(d.duplicated(["fecha", "producto", "mercado"]).sum()),
                            duplicados_exactos=int(d.duplicated(["fecha", "producto", "mercado", "precio"]).sum())))
        d["archivo"], d["hoja"] = f, ws.title
        partes.append(d[["fecha", "grupo", "producto", "cod_cpc", "mercado", "precio", "archivo", "hoja"]])
        print(f, ws.title, n, flush=True)
pd.concat(partes, ignore_index=True).to_parquet(os.path.join(SALIDA, "precios_filas.parquet"), index=False)
json.dump(informe, open(os.path.join(SALIDA, "informe_precios.json"), "w"), ensure_ascii=False, indent=1, default=str)
