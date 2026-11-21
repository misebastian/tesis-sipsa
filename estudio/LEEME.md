# Pronóstico del cambio mensual de precios mayoristas de alimentos (SIPSA)

Código del trabajo de profundización *Aprendizaje automático para pronosticar el cambio mensual de los precios mayoristas de alimentos en Colombia y anticipar sus alzas fuertes* (Maestría en Estadística Aplicada, Universidad del Norte). Reproduce todos los resultados, figuras y tablas del documento LaTeX (`../tesis`).

## Requisitos
- macOS 13 o posterior (chip Apple o Intel) o Linux; 8 GB de RAM (pico medido: 1,2 GB); unos 2 GB de disco.
- Internet solo para instalar. No requiere Homebrew, GPU ni servicios pagos.

## Pasos
```bash
cd ruta/a/estudio_final
bash preparar.sh      # una vez (3-6 min): descarga micromamba y crea ./entorno con versiones fijas
bash ejecutar.sh      # corre todos los pasos y genera tablas y cifras de ../tesis con 08_latex.py
```
Con conda o mamba: `conda env create -f entorno.yml && conda activate sipsa-final && PY=python bash ejecutar.sh`.
Limitar núcleos: `NUCLEOS=4 bash ejecutar.sh`. Otra carpeta para el documento: `TESIS=ruta bash ejecutar.sh`.

## Programas (tiempos y memoria medidos con `medir.py` en un Mac con chip Apple de 10 núcleos)
| Paso | Qué hace | Min | Memoria |
|---|---|---|---|
| 01_panel.py | Panel supervisado, 52 variables candidatas y casos sin objetivo | 0,1 | 0,7 GB |
| 02_eda.py | Análisis exploratorio, calidad de datos y revisión de precios aislados | 0,2 | 0,7 GB |
| 03_variables.py | Selección de variables en 4 etapas (predicciones reunidas de 2023 y 2024, bootstrap de bloques de meses) | 8,5 | 0,7 GB |
| sarima.py | SARIMA por serie (AutoARIMA) en los cortes de validación, prueba y origen móvil | 16,4 | 0,5 GB |
| 04_regresion.py | 6 modelos de regresión con pérdida absoluta, búsqueda con regla de convergencia en 3 cortes, y referencias | 10,9 | 0,9 GB |
| 05_clasificacion.py | 6 clasificadores, búsqueda en 3 cortes, balanceo, recalibración del intercepto, umbral y referencias | 18,1 | 0,9 GB |
| 06_resultados.py | Métricas, IC bootstrap individuales y Bonferroni, Diebold-Mariano con Holm, error valorado, calibración, curva de decisión, importancia | 1,9 | 0,6 GB |
| 07_complementarios.py | Origen móvil, pronóstico cuantílico y CQR, faltantes y sensibilidad | 16,5 | 1,1 GB |
| 09_verificacion.py | Verificación de la regresión cuantílica, la MLP con error absoluto y el Random Forest de LightGBM | 0,1 | 1,2 GB |
| 11_intervalos.py | Intervalos conformes por pronóstico (para el caso ilustrativo) | 0,5 | — |
| 12_explicaciones.py | Valores de Shapley, residuos, Friedman-Nemenyi, DeLong y ADF | 0,5 | — |
| 13_complementos.py | Diagnóstico SARIMA (órdenes, Ljung-Box, serie de ejemplo) y error en entrenamiento | 8,6 (nube) | — |
| 14_eda.py | EDA complementario: faltantes, centrales, persistencia, estacionalidad, abastecimiento, ONI | 0,2 (nube) | — |
| 15_revision.py | Análisis de la revisión: SARIMA por año, métricas complementarias, calibración, intervalos por volatilidad, efecto del promedio, horizonte t+2, lineales con otra codificación, ensamble, deriva, KPSS, ONI | 8,5 (nube) | — |
| 16_tabla_variables.py | Tabla del apéndice con la definición de las 52 variables candidatas | < 0,1 | — |
| 17_atipicos.py | Sensibilidad de la regla de atípicos (umbrales 2, 3 y 4; regla centrada y causal) | 0,5 (nube) | — |
| 18_tablas_revision.py | Tablas, cifras y figura de convergencia de la revisión (después de 08_latex.py) | < 0,1 | — |
| 10_figuras.py | Figuras del documento (PDF vectorial, estilo común) | < 1 | — |
| 08_latex.py | Tablas y cifras del documento LaTeX | < 1 | — |

Total: unos 73 minutos; pico de memoria 1,2 GB.

Comparación equitativa: todos los modelos de una tarea minimizan la misma pérdida (absoluta en regresión, logarítmica en clasificación) y siguen la misma regla de búsqueda (`busqueda.py`): 40 configuraciones iniciales (`PRESUPUESTO`), extensiones de 20 hasta 100 y parada cuando las últimas 10 no mejoran más que la tolerancia. `modelos.py` define los modelos y sus espacios de búsqueda; `redes.py`, la red neuronal con pérdida absoluta; `comun.py`, rutas, periodos, variables y utilidades (bootstrap de bloques, Holm). Semillas fijas (0). Para una prueba rápida: `PRESUPUESTO=2 bash ejecutar.sh`.

La base `datos/base_unida_mensual.parquet` se construyó en una etapa previa con los programas de `../preparacion_datos` a partir de los archivos del DANE. Después se aplicó `../preparacion_datos/corregir_variedad.py`, que elige la variedad de referencia de cada central y alimento contando solo los meses con precio hasta diciembre de 2024 (cambió una de 662 combinaciones: la panela del Mercado del Sur de Montería); su informe está en `../preparacion_datos/informe_variedad.json`. Uso:

```
python ../preparacion_datos/corregir_variedad.py base_sin_corregir.parquet sipsa_p_precios_2018_2025.parquet anex-SIPSA-SerieHistoricaMayorista-2026.xlsx datos/base_unida_mensual.parquet informe_variedad.json
```

## Datos de entrada
- `datos/base_unida_mensual.parquet`: base mensual unida del SIPSA (precios y abastecimiento, 2018-01 a 2026-09).
- `datos/oni_v6.csv`: Índice Oceánico de El Niño (NOAA CPC).

## Diseño
Hiperparámetros: tres cortes (ajuste hasta 2021, 2022 y 2023; evaluación en 2022, 2023 y 2024). Selección de variables: cortes de 2023 y 2024. Prueba: ene-2025 a sep-2026, con reajuste en 2019-2024. Todas las decisiones usan datos hasta 2024; la prueba se evalúa una sola vez.

## Documento
`../tesis/main.tex` (clase MastersDoctoralThesis si está presente; si no, diseño equivalente en `fallback_thesis.tex`). Compilar: `pdflatex main && bibtex main && pdflatex main && pdflatex main`, o subir la carpeta a Overleaf.

## Revisión de noviembre de 2026

- `06_resultados.py` usa ahora 10 000 réplicas bootstrap (variable de entorno `BOOT` para cambiarlo).
- `04_regresion.py`, `05_clasificacion.py` y `12_explicaciones.py` guardan los modelos finales en `resultados/modelos/`.
- `datos/SHA256SUMS.txt` contiene las sumas SHA-256 de los archivos de entrada.
- Los nombres de las variables (`comun.NOMBRES`) son los mismos en tablas y figuras.
