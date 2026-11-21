"""Base unida MENSUAL de todos los alimentos: abastecimiento (SIPSA-A) + precio mayorista (SIPSA-P).
Llave: central x alimento x mes. El abastecimiento se suma por mes; el precio se une cuando el nombre del alimento
coincide (sin distinguir mayúsculas ni tildes) en la misma central y el mismo mes. Se agregan equivalencias manuales
para nombres que difieren entre las dos operaciones.
Uso: python m_base_unida.py <carpeta>"""
import polars as pl, pandas as pd, numpy as np, sys, unicodedata
S = sys.argv[1]; O = f"{S}/out"
def fold(s): return unicodedata.normalize("NFKD", str(s).casefold()).encode("ascii", "ignore").decode().strip()
A = (pl.scan_parquet(f"{O}/sipsa_a_unificado_2018_2025_v2.parquet")
       .with_columns(pl.col("fecha").dt.truncate("1mo").alias("mes"),
                     pl.col("mercado").str.replace("Pereira, La 41-Impala", "Pereira, La 41", literal=True))
       .group_by(["mercado", "grupo", "alimento", "mes"])
       .agg((pl.col("cant_kg").sum() / 1000).alias("ton"), pl.col("cod_mpio").n_unique().alias("municipios_origen"),
            pl.col("depto_proc").n_unique().alias("departamentos_origen"), pl.col("fecha").n_unique().alias("dias_con_registro"))
       .collect().to_pandas())
A["mes"] = pd.to_datetime(A.mes)
Q = pd.read_parquet(f"{O}/sipsa_p_precios_2018_2025.parquet")
Q = Q[Q.en_abastecimiento].copy()
Q["mercado"] = Q.mercado_sipsa_a.str.replace("Pereira, La 41-Impala", "Pereira, La 41", regex=False)
Q["mes"] = Q.fecha
# equivalencias abastecimiento -> precio. Cuando el abastecimiento registra una categoría que en precios tiene varias
# variedades, se usa como precio de referencia la variedad con más meses de precio en esa central (en orden de preferencia).
# Las carnes no se cruzan: el abastecimiento registra la canal o el animal y los precios, cortes al detal.
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
covq = Q.groupby(["mercado", "producto"]).mes.nunique()
def ref(mkt, al):
    c = [v for v in EQ.get(al, []) if (mkt, v) in covq.index]
    return max(c, key=lambda v: covq[(mkt, v)]) if c else (EQ[al][0] if al in EQ else al)
pairs = A[["mercado", "alimento"]].drop_duplicates()
pairs["producto_precio"] = [ref(m, a) for m, a in zip(pairs.mercado, pairs.alimento)]
pairs["tipo_cruce"] = np.where(pairs.alimento.isin(list(EQ)), "variedad de referencia", "mismo nombre")
A = A.merge(pairs, on=["mercado", "alimento"])
A["k"] = A.producto_precio.map(fold); Q["k"] = Q.producto.map(fold)
B = A.merge(Q[["mercado", "mes", "k", "producto", "precio", "unidad"]].rename(columns={"producto": "producto_precio_sipsa_p"}),
            on=["mercado", "mes", "k"], how="left").drop(columns=["k"])
B = B.sort_values(["mes", "mercado", "grupo", "alimento"]).reset_index(drop=True)
B["valor_millones"] = np.where(B.unidad.eq("$/kg"), B.ton * 1000 * B.precio / 1e6, np.nan)
B.to_parquet(f"{O}/base_unida_mensual_2018_2025.parquet", index=False)
B.to_csv(f"{O}/base_unida_mensual_2018_2025.csv", index=False, encoding="utf-8-sig")
tot = B.ton.sum(); con = B[B.precio.notna()].ton.sum()
print(B.shape, f"toneladas con precio: {con / tot:.1%}", "| filas con precio:", B.precio.notna().mean().round(3))
print(B.groupby("grupo").apply(lambda g: pd.Series(dict(ton=g.ton.sum(), pct_ton_con_precio=g[g.precio.notna()].ton.sum() / g.ton.sum()))).round(3).to_string())
top = B.groupby("alimento").agg(ton=("ton", "sum"), con_precio=("precio", lambda s: s.notna().mean())).sort_values("ton", ascending=False).head(25)
print(top.round(3).to_string())
