"""Limpieza final del archivo unificado: nombres de mercado y departamento homogéneos."""
import polars as pl, sys
S = sys.argv[1]
lf = pl.scan_parquet(f"{S}/parts/*.parquet")
lf = lf.with_columns(
    pl.col("mercado").str.strip_chars('"').str.replace_all('""', '"')
      .str.replace("Cali, Santa Helena", "Cali, Santa Elena", literal=True),
    pl.when(pl.col("cod_depto").is_in(["n.a.", "00"])).then(pl.lit("00")).otherwise(pl.col("cod_depto")).alias("cod_depto"),
)
# nombre canónico de departamento por código (el más frecuente)
canon = (lf.group_by(["cod_depto", "depto_proc"]).agg(pl.len().alias("n")).sort("n", descending=True)
           .group_by("cod_depto").agg(pl.col("depto_proc").first().alias("depto_std")).collect())
canon = canon.with_columns(pl.when(pl.col("cod_depto") == "00").then(pl.lit("OTRO / SIN DATO"))
                           .when(pl.col("cod_depto") == "11").then(pl.lit("BOGOTÁ, D.C.")).otherwise(pl.col("depto_std")).alias("depto_std"))
lf = lf.join(canon.lazy(), on="cod_depto", how="left").with_columns(pl.col("depto_std").alias("depto_proc")).drop("depto_std")
lf = lf.sort(["fecha", "mercado"])
lf.sink_parquet(f"{S}/out/sipsa_a_unificado_2018_2025_v2.parquet")
d = pl.read_parquet(f"{S}/out/sipsa_a_unificado_2018_2025_v2.parquet", columns=["mercado","depto_proc"])
print(d.height, d["mercado"].n_unique(), d["depto_proc"].n_unique())
pl.scan_parquet(f"{S}/out/sipsa_a_unificado_2018_2025_v2.parquet").sink_csv(f"{S}/out/sipsa_a_unificado_2018_2025_v2.csv", separator=";", date_format="%Y-%m-%d")
