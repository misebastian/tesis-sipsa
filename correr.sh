#!/usr/bin/env bash
# Corre todo el estudio y regenera las tablas, cifras y figuras de la tesis (carpeta tesis/).
# Uso:  bash preparar.sh   (una vez)   y luego   bash correr.sh
# Tarda entre 1,5 y 2 horas en un Mac con chip Apple.
set -euo pipefail
cd "$(dirname "$0")"
AQUI="$PWD"
PY="${PY:-$AQUI/entorno/bin/python}"
LOG="$AQUI/registro.txt"
echo "Inicio: $(date)" | tee "$LOG"
( cd estudio/datos && shasum -a 256 -c SHA256SUMS.txt ) 2>&1 | tee -a "$LOG"
if command -v caffeinate >/dev/null; then C="caffeinate -i"; else C=""; fi
$C env PY="$PY" TESIS="$AQUI/tesis" bash estudio/ejecutar.sh 2>&1 | tee -a "$LOG"
echo "Fin: $(date)" | tee -a "$LOG"
