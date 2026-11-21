"""Convierte archivos nuevos del DANE (SIPSA-A: microdatos de abastecimiento en CSV o Stata; SIPSA-P: anexo de precios
mayoristas en Excel) en filas de la base unida mensual (central x alimento x mes), con las MISMAS reglas que construyeron
la base 2018-2025 (unify.py, clean_v2.py, precios_unify.py, precios_normalize.py y m_base_unida.py):
  - cantidades en formato colombiano (punto = miles, coma = decimal); filas sin fecha se descartan;
  - nombres de central y de producto llevados a la forma canónica de la base histórica (sin distinguir mayúsculas ni tildes);
  - abastecimiento sumado por mes: toneladas, municipios y departamentos de origen distintos, días con registro;
  - precio unido por central, mes y producto de referencia (misma tabla de equivalencias de m_base_unida.py).
Uso:
  python agregar_meses.py --base base_unida_mensual.parquet --precios_hist sipsa_p_precios_2018_2025.parquet \
      --abastecimiento a1.dta a2.csv ... --precios anexo_2026.xlsx --salida meses_nuevos.parquet [--informe informe.json]"""
import argparse, json, os, re, unicodedata
import numpy as np, pandas as pd, openpyxl

fold = lambda s: unicodedata.normalize("NFKD", str(s).casefold()).encode("ascii", "ignore").decode().strip()
norm_txt = lambda s: re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s)).replace("\xa0", " ")).strip()
STD = ["mercado", "fecha", "cod_depto", "cod_mpio", "depto_proc", "mpio_proc", "grupo", "cod_cpc", "alimento", "cant_kg"]
EQ = {"Papa criolla": ["Papa criolla limpia"], "Papa R-12": ["Papa R-12 negra", "Papa R-12 roja"],
      "Arroz": ["Arroz de primera", "Arroz excelso", "Arroz de segunda"], "Yuca": ["Yuca llanera", "Yuca ICA", "Yuca chirosa", "Yuca criolla"],
      "Cebolla Cabezona": ["Cebolla cabezona blanca bogotana", "Cebolla cabezona blanca", "Cebolla cabezona blanca pastusa"],
      "Maíz Amarillo": ["Maíz amarillo trillado", "Maíz amarillo cáscara"], "Maíz Blanco": ["Maíz blanco trillado", "Maíz blanco cáscara", "Maíz blanco retrillado"],
      "Azúcar": ["Azúcar refinada", "Azúcar sulfitada", "Azúcar morena"], "Naranja Valencia y/o Sweet": ["Naranja Valencia", "Naranja Sweet"],
      "Harinas": ["Harina de trigo", "Harina precocida de maíz"], "Manzana importada": ["Manzana roja importada", "Manzana royal gala importada", "Manzana verde importada"],
      "Repollo": ["Repollo blanco", "Repollo blanco bogotano", "Repollo verde"], "Mora": ["Mora de Castilla"], "Melón": ["Melón Cantalup"],
      "Panela": ["Panela redonda morena", "Panela cuadrada morena", "Panela en pastilla"], "Arracacha": ["Arracacha amarilla", "Arracacha blanca"],
      "Lenteja": ["Lenteja importada"], "Fríjol": ["Fríjol cargamanto rojo", "Fríjol calima", "Fríjol radical"],
      "Fríjol verde": ["Fríjol verde cargamanto", "Fríjol verde bolo", "Fríjol verde en vaina"], "Huevo": ["Huevo rojo AA", "Huevo rojo A", "Huevo blanco AA"],
      "Mojarra": ["Mojarra lora entera fresca", "Mojarra lora entera congelada"], "Aceites": ["Aceite vegetal mezcla", "Aceite soya"]}
RENOMBRES = {"Cali, Santa Helena": "Cali, Santa Elena", "Duitama (Boyacá)": "Duitama (Boyacá), Mercaplaza",
             "San Vicente (Antioquia)": "San Vicente Ferrer (Antioquia)", "Pereira, La 41-Impala": "Pereira, La 41",
             "Malambo, Atlantico": "Malambo (Atlántico), Carnes y carnes", "Bogotá, D.C., Frigorífico Ble Ltda,": "Bogotá, D.C., Frigorífico Ble Ltda.",
             "San Sebastián de Mariquita (Tolima), panela": "San Sebastián de Mariquita (Tolima)"}


def clave(c):
    c = c.strip().lower()
    if "mercado" in c or c == "fuente": return "mercado"
    if "fecha" in c: return "fecha"
    if "depto" in c and ("cod" in c or "divipola" in c) or c.startswith("código departamento"): return "cod_depto"
    if "municipio" in c and ("cod" in c or "divipola" in c or "código" in c): return "cod_mpio"
    if c.startswith("departamento"): return "depto_proc"
    if c.startswith("municipio"): return "mpio_proc"
    if c == "grupo": return "grupo"
    if "cpc" in c: return "cod_cpc"
    if c in ("ali", "alimento"): return "alimento"
    if "kg" in c: return "cant_kg"
    return None


def leer_abastecimiento(ruta):
    if ruta.lower().endswith(".dta"):
        d = pd.read_stata(ruta, convert_categoricals=False).astype(str)
    else:
        try:
            d = pd.read_csv(ruta, sep=";", dtype=str, encoding="utf-8", quoting=3)
        except UnicodeDecodeError:
            d = pd.read_csv(ruta, sep=";", dtype=str, encoding="latin-1", quoting=3)
    ren = {c: clave(c) for c in d.columns if clave(c)}
    assert len(set(ren.values())) == len(ren), ren
    d = d[list(ren)].rename(columns=ren)
    for c in STD:
        if c not in d: d[c] = None
    d = d[STD].apply(lambda s: s.astype("string").str.strip())
    n0 = len(d)
    d = d[d.fecha.notna() & (d.fecha != "") & (d.fecha != "nan")]
    d["fecha"] = pd.to_datetime(d.fecha, format="%d/%m/%Y")
    d["cod_depto"] = d.cod_depto.str.replace("'", "").str.strip().str.zfill(2)
    d["cod_mpio"] = d.cod_mpio.str.replace("'", "").str.strip()
    d["cant_kg"] = pd.to_numeric(d.cant_kg.str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")
    d["mercado"] = (d.mercado.str.strip('"').str.replace('""', '"', regex=False)
                    .str.replace("Cali, Santa Helena", "Cali, Santa Elena", regex=False)
                    .str.replace("Pereira, La 41-Impala", "Pereira, La 41", regex=False))
    d.loc[d.cod_depto.isin(["n.a.", "00", "N.A."]), "cod_depto"] = "00"
    return d, dict(archivo=os.path.basename(ruta), filas=n0, filas_con_fecha=len(d), kg_nulos=int(d.cant_kg.isna().sum()),
                   desde=str(d.fecha.min().date()), hasta=str(d.fecha.max().date()))


def leer_precios(ruta):
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True); out = []
    for ws in wb.worksheets:
        cols = None
        for r in ws.iter_rows(values_only=True):
            if cols is None:
                if r and isinstance(r[0], str) and norm_txt(r[0]).lower() == "fecha":
                    cols = {}
                    for i, h in enumerate(r):
                        h = norm_txt(h).lower() if h is not None else ""
                        k = ("fecha" if h.startswith("fecha") else "grupo" if h.startswith("grupo") else "producto" if h.startswith("producto")
                             else "mercado" if h.startswith("mercado") or h.startswith("fuente") else "precio" if h.startswith("precio") else None)
                        if k: cols[i] = k
                continue
            if r[0] is None or isinstance(r[0], str): continue
            out.append({k: r[i] for i, k in cols.items() if i < len(r)})
    P = pd.DataFrame(out)
    P["fecha"] = pd.to_datetime(P.fecha).dt.to_period("M").dt.to_timestamp()
    for c in ["grupo", "producto", "mercado"]: P[c] = P[c].map(norm_txt)
    P["precio"] = pd.to_numeric(P.precio, errors="coerce")
    P["unidad"] = np.where(P.producto.str.contains(r"^Huevo|Bocadillo", case=False), "$/unidad",
                  np.where(P.producto.str.contains(r"Aceite|Vinagre|Jugo", case=False), "$/litro", "$/kg"))
    return P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--precios_hist", required=True)
    ap.add_argument("--abastecimiento", nargs="+", required=True); ap.add_argument("--precios", required=True)
    ap.add_argument("--salida", required=True); ap.add_argument("--informe")
    a = ap.parse_args()
    B = pd.read_parquet(a.base); H = pd.read_parquet(a.precios_hist)
    # --- abastecimiento
    partes, inf = [], []
    for r in a.abastecimiento:
        d, i = leer_abastecimiento(r); partes.append(d); inf.append(i)
    A = pd.concat(partes, ignore_index=True)
    canon_m = {fold(m): m for m in B.mercado.unique()}
    A["mercado"] = A.mercado.map(lambda m: canon_m.get(fold(m), m))
    A["mes"] = A.fecha.dt.to_period("M").dt.to_timestamp()
    g = A.groupby(["mercado", "grupo", "alimento", "mes"])
    M = pd.DataFrame(dict(ton=g.cant_kg.sum(min_count=1) / 1000, municipios_origen=g.cod_mpio.nunique(),
                          departamentos_origen=g.cod_depto.nunique(), dias_con_registro=g.fecha.nunique())).reset_index()
    # --- precios
    P = leer_precios(a.precios)
    canon_p = {fold(p): p for p in H.producto.value_counts().index[::-1]}           # el más frecuente gana
    P["producto"] = P.producto.map(lambda p: canon_p.get(fold(p), p))
    canon_pm = {fold(m): m for m in H.mercado.value_counts().index[::-1]}
    P["mercado"] = P.mercado.map(lambda m: canon_pm.get(fold(m), m)).replace(RENOMBRES)
    a_std = {}
    for m in sorted(B.mercado.unique()): a_std.setdefault(fold(m.replace('"', "")).replace("-impala", ""), m)
    P["mercado"] = P.mercado.map(lambda m: a_std.get(fold(m.replace('"', ""))))
    P = P[P.mercado.notna()]
    # --- producto de referencia por central y alimento (mismo criterio y tabla que la base histórica)
    pares = B[["mercado", "alimento", "producto_precio", "tipo_cruce"]].drop_duplicates(["mercado", "alimento"])
    M = M.merge(pares, on=["mercado", "alimento"], how="left")
    Hq = H[H.en_abastecimiento].assign(mercado=H.mercado_sipsa_a)
    covq = pd.concat([Hq[["mercado", "producto", "fecha"]], P[["mercado", "producto", "fecha"]]]).groupby(["mercado", "producto"]).fecha.nunique()
    def ref(m, al):
        c = [v for v in EQ.get(al, []) if (m, v) in covq.index]
        return max(c, key=lambda v: covq[(m, v)]) if c else (EQ[al][0] if al in EQ else al)
    nuevo = M.producto_precio.isna()
    M.loc[nuevo, "producto_precio"] = [ref(m, al) for m, al in zip(M.mercado[nuevo], M.alimento[nuevo])]
    M.loc[nuevo, "tipo_cruce"] = np.where(M.alimento[nuevo].isin(list(EQ)), "variedad de referencia", "mismo nombre")
    M["k"] = M.producto_precio.map(fold); P["k"] = P.producto.map(fold)
    P = P.groupby(["mercado", "fecha", "k"], as_index=False).agg(producto_precio_sipsa_p=("producto", "first"), precio=("precio", "mean"), unidad=("unidad", "first"))
    M = M.merge(P.rename(columns={"fecha": "mes"}), on=["mercado", "mes", "k"], how="left").drop(columns="k")
    M["valor_millones"] = np.where(M.unidad.eq("$/kg"), M.ton * 1000 * M.precio / 1e6, np.nan)
    M = M[B.columns].sort_values(["mes", "mercado", "grupo", "alimento"]).reset_index(drop=True)
    M.to_parquet(a.salida, index=False)
    rep = dict(archivos_abastecimiento=inf, filas_salida=len(M), meses=sorted(M.mes.dt.strftime("%Y-%m").unique().tolist()),
               centrales_nuevas=sorted(set(M.mercado) - set(B.mercado)), alimentos_nuevos=int((~M.alimento.isin(B.alimento.unique())).sum()),
               filas_con_precio=int(M.precio.notna().sum()), pares_nuevos=int(nuevo.sum()))
    if a.informe: json.dump(rep, open(a.informe, "w"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
