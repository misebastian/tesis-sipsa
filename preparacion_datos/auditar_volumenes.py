"""Auditoría de los microdatos SIPSA-A (abastecimiento): esquema, codificación, fechas, formato de cantidades,
nulos y duplicados, archivo por archivo. Guarda las filas normalizadas (texto sin interpretar + columnas tipadas)
en un parquet por archivo para la unión posterior."""
import json, os, re, sys, unicodedata
import numpy as np, pandas as pd

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
os.makedirs(SALIDA, exist_ok=True)
STD = ["mercado", "fecha", "cod_depto", "cod_mpio", "depto_proc", "mpio_proc", "grupo", "cod_cpc", "alimento", "cant_kg"]


def clave(c):
    c = unicodedata.normalize("NFKC", str(c)).replace("﻿", "").strip().lower()
    if "mercado" in c or c == "fuente": return "mercado"
    if "fecha" in c: return "fecha"
    if ("depto" in c or "departamento" in c) and ("cod" in c or "divipola" in c or "código" in c): return "cod_depto"
    if "municipio" in c and ("cod" in c or "divipola" in c or "código" in c): return "cod_mpio"
    if c.startswith("departamento"): return "depto_proc"
    if c.startswith("municipio"): return "mpio_proc"
    if c == "grupo": return "grupo"
    if "cpc" in c: return "cod_cpc"
    if c in ("ali", "alimento"): return "alimento"
    if "kg" in c: return "cant_kg"
    return None


def leer(ruta):
    if ruta.lower().endswith(".dta"):
        d = pd.read_stata(ruta, convert_categoricals=False)
        return d.astype(str).replace({"nan": None, "": None}), "stata"
    raw = open(ruta, "rb").read(4)
    enc = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "latin-1"
    d = pd.read_csv(ruta, sep=";", dtype=str, encoding=enc, quoting=3, keep_default_na=False)
    return d, enc


PAT = {"entero": r"^\d+$", "miles_punto": r"^\d{1,3}(\.\d{3})+$", "miles_punto_coma_dec": r"^\d{1,3}(\.\d{3})*,\d+$",
       "coma_decimal": r"^\d+,\d+$", "punto_dec_ambiguo": r"^\d+\.\d{1,2}$|^\d{4,}\.\d+$|^\d+\.\d{4,}$",
       "decimal_stata": r"^\d+\.0$"}


def patrones(s):
    s = s.dropna().astype(str).str.strip()
    out = {k: int(s.str.match(p).sum()) for k, p in PAT.items()}
    usados = np.zeros(len(s), bool)
    for p in PAT.values(): usados |= s.str.match(p).to_numpy()
    out["otro"] = int((~usados).sum()); out["ejemplos_otro"] = s[~usados].unique()[:8].tolist()
    return out


def a_numero(s, formato):
    s = s.astype("string").str.strip()
    if formato == "stata":
        return pd.to_numeric(s, errors="coerce")
    return pd.to_numeric(s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")


informe = []
for f in sorted(os.listdir(ENTRADA)):
    ruta = os.path.join(ENTRADA, f)
    if not (f.endswith(".csv") or f.endswith(".dta")): continue
    d, enc = leer(ruta)
    cols = list(d.columns)
    mapa = {c: clave(c) for c in cols}
    vacias = [c for c, k in mapa.items() if k is None]
    # columnas sin nombre deben estar vacías
    extra_no_vacias = {c: int((d[c].astype(str).str.strip().replace({"None": "", "nan": ""}) != "").sum()) for c in vacias}
    usadas = {c: k for c, k in mapa.items() if k}
    assert len(set(usadas.values())) == len(usadas), (f, usadas)
    d = d[list(usadas)].rename(columns=usadas)
    for c in STD:
        if c not in d: d[c] = None
    d = d[STD].apply(lambda s: s.astype("string").str.strip())
    n = len(d)
    blanca = d.drop(columns=["cant_kg"]).isna().all(axis=1) | (d.fillna("").drop(columns=["cant_kg"]) == "").all(axis=1)
    pat = patrones(d.cant_kg[~blanca])
    d = d[~blanca].copy()
    f_txt = d.fecha.fillna("")
    fecha = pd.to_datetime(f_txt, format="%d/%m/%Y", errors="coerce")
    if enc == "stata" and fecha.isna().mean() > .5:
        fecha = pd.to_datetime(f_txt, errors="coerce")
    d["fecha"] = fecha
    d["cant_kg"] = a_numero(d.cant_kg, "col")  # en los .dta la cantidad también es texto en formato colombiano
    for c in ["cod_depto", "cod_mpio", "cod_cpc"]:
        d[c] = d[c].str.replace("'", "", regex=False).str.strip()
    nul = {c: int((d[c].isna() | (d[c].astype("string") == "")).sum()) for c in STD}
    dup = int(d.duplicated().sum())
    meses = d.fecha.dt.to_period("M").value_counts().sort_index()
    informe.append(dict(archivo=f, codificacion=enc, columnas_originales=cols, mapeo=usadas, columnas_sin_nombre_con_datos=extra_no_vacias,
                        filas=n, filas_en_blanco=int(blanca.sum()), filas_utiles=len(d), fechas_invalidas=int(d.fecha.isna().sum()),
                        desde=str(d.fecha.min().date()), hasta=str(d.fecha.max().date()), meses={str(k): int(v) for k, v in meses.items()},
                        patrones_kg=pat, nulos=nul, duplicados_exactos=dup,
                        kg_min=float(d.cant_kg.min()), kg_p50=float(d.cant_kg.median()), kg_p99=float(d.cant_kg.quantile(.99)),
                        kg_max=float(d.cant_kg.max()), kg_cero=int((d.cant_kg == 0).sum()), kg_neg=int((d.cant_kg < 0).sum()),
                        toneladas=float(d.cant_kg.sum() / 1000)))
    d["archivo"] = f
    d.to_parquet(os.path.join(SALIDA, f.rsplit(".", 1)[0] + ".parquet"), index=False)
    print(f, n, len(d), enc, flush=True)
json.dump(informe, open(os.path.join(SALIDA, "informe_volumenes.json"), "w"), ensure_ascii=False, indent=1, default=str)
