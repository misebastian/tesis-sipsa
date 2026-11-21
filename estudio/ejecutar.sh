#!/usr/bin/env bash
# Ejecuta el estudio completo en orden y mide tiempo y memoria de cada paso (resultados/tiempos.csv).
# Uso: bash ejecutar.sh   (opcional: NUCLEOS=4 bash ejecutar.sh; TESIS=ruta para la carpeta del documento LaTeX)
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-./entorno/bin/python}"
[ -x "$PY" ] || PY=python3
TESIS="${TESIS:-../tesis}"
for paso in 01_panel 02_eda 03_variables sarima 04_regresion 05_clasificacion 06_resultados 07_complementarios 09_verificacion; do
  echo "=== $paso  $(date +%H:%M:%S)"
  "$PY" medir.py "$paso"
done
echo "=== 11_intervalos"; "$PY" 11_intervalos.py
echo "=== 12_explicaciones"; "$PY" 12_explicaciones.py
echo "=== 13_complementos"; "$PY" 13_complementos.py
echo "=== 14_eda"; "$PY" 14_eda.py
echo "=== 15_revision"; "$PY" 15_revision.py
echo "=== 17_atipicos"; "$PY" 17_atipicos.py
echo "=== 10_figuras"; "$PY" 10_figuras.py
if [ -d "$TESIS" ]; then
  echo "=== 08_latex"; "$PY" 08_latex.py "$TESIS"
  echo "=== 16_tabla_variables"; "$PY" 16_tabla_variables.py
  echo "=== 18_tablas_revision"; "$PY" 18_tablas_revision.py "$TESIS"
fi
echo "=== Listo $(date +%H:%M:%S). Resultados en resultados/, figuras en figuras/."
