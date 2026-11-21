"""Unifica los CSV de SIPSA-A (abastecimiento) en un solo archivo armonizado."""
import polars as pl, glob, os, sys
S = sys.argv[1]
STD = ["mercado", "fecha", "cod_depto", "cod_mpio", "depto_proc", "mpio_proc", "grupo", "cod_cpc", "alimento", "cant_kg"]

def key(c):
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

parts, log = [], []
for f in sorted(glob.glob(f"{S}/utf8/*.csv")):
    df = pl.read_csv(f, separator=";", infer_schema=False, quote_char=None, truncate_ragged_lines=True)
    ren = {c: key(c) for c in df.columns if key(c)}
    assert len(set(ren.values())) == len(ren), (f, ren)
    df = df.select(list(ren)).rename(ren)
    for c in STD:
        if c not in df.columns: df = df.with_columns(pl.lit(None, dtype=pl.Utf8).alias(c))
    df = df.select(STD).with_columns(pl.all().str.strip_chars())
    n0 = df.height
    df = df.filter(pl.col("fecha").is_not_null() & (pl.col("fecha") != ""))
    raw_q = df["cant_kg"]
    df = df.with_columns(
        pl.col("fecha").str.to_date("%d/%m/%Y"),
        pl.col("cod_depto").str.replace_all("'", "").str.strip_chars().str.zfill(2),
        pl.col("cod_mpio").str.replace_all("'", "").str.strip_chars(),
        pl.col("cod_cpc").str.replace_all("'", ""),
        # formato colombiano: punto = miles, coma = decimal
        pl.col("cant_kg").str.replace_all(r"\.", "").str.replace(",", ".").cast(pl.Float64, strict=False),
        pl.lit(os.path.basename(f)[:-4]).alias("archivo_origen"),
    )
    bad_dot = raw_q.str.contains(r"\.\d{1,2}$").sum()
    log.append((os.path.basename(f), n0, df.height, df["cant_kg"].null_count(), int(bad_dot), str(df["fecha"].min()), str(df["fecha"].max())))
    os.makedirs(f"{S}/parts", exist_ok=True)
    df.write_parquet(f"{S}/parts/{os.path.basename(f)[:-4]}.parquet")
    del df

for l in log: print(l)
lf = pl.scan_parquet(f"{S}/parts/*.parquet")
lf.sort(["fecha", "mercado"]).sink_parquet(f"{S}/out/sipsa_a_unificado_2018_2025.parquet")
lf2 = pl.scan_parquet(f"{S}/out/sipsa_a_unificado_2018_2025.parquet")
print(lf2.select(pl.len(), pl.col("fecha").min().alias("fmin"), pl.col("fecha").max().alias("fmax"), pl.col("cant_kg").null_count().alias("kg_nulos"), (pl.col("cant_kg")<=0).sum().alias("kg_no_pos"), pl.col("cant_kg").sum().alias("kg_total")).collect())
lf2.sink_csv(f"{S}/out/sipsa_a_unificado_2018_2025.csv", separator=";", date_format="%Y-%m-%d")
