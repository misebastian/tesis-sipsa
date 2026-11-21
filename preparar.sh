#!/usr/bin/env bash
# Instala el entorno de Python del estudio dentro de esta carpeta (no toca el resto del sistema ni pide clave).
# Uso:  bash preparar.sh        (una sola vez; 3-6 minutos según la conexión)
set -euo pipefail
cd "$(dirname "$0")"
AQUI="$PWD"
export MAMBA_ROOT_PREFIX="$AQUI/herramientas/mamba"
MM="$AQUI/herramientas/micromamba"
xattr -d com.apple.quarantine "$MM" 2>/dev/null || true
mkdir -p herramientas
chmod +x "$MM" 2>/dev/null || true
if ! "$MM" --version >/dev/null 2>&1; then
  echo "Descargando micromamba desde conda-forge..."
  curl -Ls https://conda.anaconda.org/conda-forge/osx-arm64/micromamba-2.10.0-0.tar.bz2 | tar -xj -C herramientas bin/micromamba
  mv herramientas/bin/micromamba "$MM"; rmdir herramientas/bin
fi
echo "micromamba $("$MM" --version)"
"$MM" create -y -p "$AQUI/entorno" -f entorno.yml
"$AQUI/entorno/bin/python" - <<'PY'
import lightgbm, statsforecast, pandas, numpy, sklearn, statsmodels, scipy, matplotlib, openpyxl, pyarrow, joblib, os
print("Entorno listo:", {m.__name__: m.__version__ for m in [lightgbm, statsforecast, pandas, numpy, sklearn, statsmodels, scipy]})
print("Núcleos disponibles:", os.cpu_count())
PY
"$MM" env export -p "$AQUI/entorno" --explicit > entorno_bloqueado.txt   # versiones exactas instaladas
echo "Listo. Siguiente paso:  bash correr.sh"
