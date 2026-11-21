"""Genera los datos de las páginas Panorama y Mi ciudad:
  public/data/extra.json   calendario (cambio típico de cada mes del año por central y alimento) y red de centrales
                           (correlación del cambio mensual entre centrales, mismos alimentos y meses), con la base mensual.
  public/data/origen.json  departamento de origen de lo que llega a cada central en los últimos 12 meses, con los
                           microdatos de abastecimiento (SIPSA-A) del DANE.
Uso (desde esta carpeta, después de generar_pronosticos.py):
  python scripts/generar_panorama.py ../estudio --base datos/base_mensual_web.parquet \
      --abastecimiento <archivos SIPSA-A que cubran los últimos 12 meses (.csv, .dta o .xlsx)>
"""
import argparse, json, sys
from pathlib import Path
import numpy as np, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument('estudio'); ap.add_argument('--abastecimiento', nargs='+', required=True)
ap.add_argument('--base', help='base mensual (por defecto, la del estudio)')
ap.add_argument('--preparacion', default='../preparacion_datos'); ap.add_argument('--salida', default='public/data')
a = ap.parse_args()
sys.path.insert(0, a.preparacion)
from agregar_meses import leer_abastecimiento, fold  # mismas reglas de lectura que la base de la tesis

sal = Path(a.salida)
P = json.load(open(sal / 'pronosticos.json'))
ser = P['series']; pares = {(s['central'], s['producto']) for s in ser}; ciudad_de = {s['central']: s['ciudad'] for s in ser}
fin = pd.Timestamp(P['ultimo_mes'] + '-01') + pd.offsets.MonthBegin(1); ini = fin - pd.DateOffset(months=12)

# ---------- calendario y red, con la base mensual
B = pd.read_parquet(a.base or Path(a.estudio) / 'datos' / 'base_unida_mensual.parquet')
B = B[np.array([(m, al) in pares for m, al in zip(B.mercado, B.alimento)]) & B.precio.notna()].sort_values(['mercado', 'alimento', 'mes'])
g = B.groupby(['mercado', 'alimento'])
seguido = (B.mes - pd.DateOffset(months=1)) == g.mes.shift()
B['cambio'] = np.where(seguido, 100 * (B.precio / g.precio.shift() - 1), np.nan)
C = B[B.cambio.notna()].copy(); C['m'] = C.mes.dt.month
cal = {}
for (m, al), x in C.groupby(['mercado', 'alimento']):
    med = x.groupby('m').cambio.median().reindex(range(1, 13))
    fa = x.assign(f=x.cambio > 15).groupby('m').f.mean().reindex(range(1, 13))
    n = x.groupby('m').size().reindex(range(1, 13)).fillna(0)
    cal[f'{m}|{al}'] = [[None if pd.isna(v) else round(float(v), 1) for v in med], [None if pd.isna(v) else round(float(v), 2) for v in fa], [int(v) for v in n]]
W = C.pivot_table(index=['alimento', 'mes'], columns='mercado', values='cambio')
cents = sorted(W.columns); red = []
for i, x in enumerate(cents):
    for y in cents[i + 1:]:
        z = W[[x, y]].dropna()
        k = z.index.get_level_values(0).nunique()
        if len(z) >= 200 and k >= 8: red.append([x, y, round(float(z[x].corr(z[y])), 3), int(len(z)), int(k)])
red.sort(key=lambda r: -r[2])
json.dump(dict(desde=C.mes.min().strftime('%Y-%m'), hasta=C.mes.max().strftime('%Y-%m'), calendario=cal, red=red),
          open(sal / 'extra.json', 'w'), ensure_ascii=False, separators=(',', ':'))

# ---------- orígenes, con los microdatos de abastecimiento
A = pd.concat([leer_abastecimiento(r)[0] for r in a.abastecimiento], ignore_index=True)
A = A[(A.fecha >= ini) & (A.fecha < fin)]
canon_m = {fold(m): m for m in B.mercado.unique()}; canon_a = {fold(x): x for x in B.alimento.unique()}
A['mercado'] = A.mercado.map(lambda m: canon_m.get(fold(m), m)); A['alimento'] = A.alimento.map(lambda x: canon_a.get(fold(x), x))
A = A[[(m, al) in pares for m, al in zip(A.mercado, A.alimento)]].copy()
A['depto_proc'] = A.depto_proc.str.upper().str.strip()
imp = A.cod_depto.eq('00') | A.depto_proc.eq('N.A.')
NOM = {'BOGOTÁ, D.C.': 'Bogotá D.C.', 'NORTE DE SANTANDER': 'Norte de Santander', 'VALLE DEL CAUCA': 'Valle del Cauca', 'LA GUAJIRA': 'La Guajira'}
A['origen'] = np.where(imp, 'Importado', A.depto_proc.map(lambda o: NOM.get(o, str(o).title())))
A['pais'] = np.where(imp, A.mpio_proc.str.title(), '')
por_serie = {}
for (m, al), x in A.groupby(['mercado', 'alimento']):
    t = x.groupby('origen').cant_kg.sum().sort_values(ascending=False); tot = t.sum()
    por_serie[f'{m}|{al}'] = dict(t=round(float(tot / 1000), 1), o=[[o, round(float(v / tot), 3)] for o, v in t.head(3).items()], n=int((t / tot >= 0.01).sum()))
A['ciudad'] = A.mercado.map(ciudad_de); por_ciudad = {}
for c, x in A.groupby('ciudad'):
    t = x.groupby('origen').cant_kg.sum().sort_values(ascending=False); tot = t.sum()
    ip = x[x.origen == 'Importado'].groupby('pais').cant_kg.sum().sort_values(ascending=False)
    por_ciudad[c] = dict(ton=round(float(tot / 1000)), origenes=[[o, round(float(v / tot), 4)] for o, v in t.items() if v / tot >= 0.002],
                         importado=[[p, round(float(v / tot), 4)] for p, v in ip.head(4).items()])
json.dump(dict(periodo=[ini.strftime('%Y-%m'), (fin - pd.DateOffset(months=1)).strftime('%Y-%m')], serie=por_serie, ciudad=por_ciudad),
          open(sal / 'origen.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print(f'extra.json: {len(cal)} calendarios, {len(red)} pares de centrales; origen.json: {len(por_serie)} series, {len(por_ciudad)} ciudades')
