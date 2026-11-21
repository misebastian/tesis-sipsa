# Pronóstico de precios mayoristas de alimentos en Colombia (SIPSA)

Código, datos procesados y documento del trabajo de profundización *Aprendizaje automático para pronosticar el cambio
mensual de los precios mayoristas de alimentos en Colombia y anticipar sus alzas fuertes*, de Miguel Herrera
(Maestría en Estadística Aplicada, Universidad del Norte; tutor: Carlos Mario de Oro Aguado).

Incluye también una página web que muestra, para cada producto y central de abasto, el pronóstico del mes siguiente
y la alerta de alza fuerte calculados con el modelo final (CatBoost).

## Contenido

| Carpeta | Qué hay |
|---|---|
| `estudio/` | Programas del estudio (pasos 01 a 18), datos procesados, resultados y modelos guardados. Ver `estudio/LEEME.md` |
| `preparacion_datos/` | Programas que leen los archivos del DANE, los auditan, los unen en la base mensual y corrigen la variedad de referencia |
| `datos_fuentes/` | Instrucciones para obtener los archivos originales del DANE (no se incluyen por su tamaño) |
| `tesis/` | Documento en LaTeX; las tablas y cifras las escribe el estudio |
| `web-precios/` | Página web en Next.js (pronósticos y alertas del mes, y propuesta de arquitectura MLOps) |

## Reproducir los resultados

Requiere macOS o Linux, 8 GB de RAM y unos 2 GB de disco.

```bash
bash preparar.sh   # una vez: crea ./entorno con las versiones exactas de las librerías
bash correr.sh     # corre todo el estudio (1,5 a 2 horas) y actualiza las tablas y figuras de tesis/
```

`estudio/datos/SHA256SUMS.txt` permite comprobar que los datos de entrada son los mismos usados en el documento.

## Fuentes de datos

- DANE, Sistema de Información de Precios y Abastecimiento del Sector Agropecuario (SIPSA): precios mayoristas
  mensuales (SIPSA-P) y abastecimiento (SIPSA-A), 2018 a 2026.
- NOAA, Índice Oceánico El Niño (ONI), versión 6.
