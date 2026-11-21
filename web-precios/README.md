# Precios de la central

Página web para consultar el pronóstico del precio mayorista de los alimentos en las centrales de abasto de Colombia y
las alertas de alza fuerte (más del 15 % el mes siguiente). Usa el modelo final de la tesis *Aprendizaje automático para
pronosticar el cambio mensual de los precios mayoristas de alimentos en Colombia* (CatBoost) y los datos del DANE (SIPSA).

La página no pide datos al usuario: muestra los pronósticos calculados con el último boletín disponible. El usuario solo elige qué producto y qué central quiere ver.

## Cómo está armada

La página **no ejecuta el modelo**. Los pronósticos se calculan una vez al mes en el computador del autor (o, más
adelante, en GitHub Actions) y se guardan en `public/data/pronosticos.json`. La página solo lee ese archivo. Así es
rápida, gratuita en Vercel y no necesita un servidor con Python.

```
DANE (SIPSA) ──► estudio de la tesis (datos, modelos guardados)
                     │
                     ▼
        scripts/generar_pronosticos.py  ──►  public/data/pronosticos.json
                                                     │  (git push)
                                                     ▼
                                    GitHub ──► Vercel (publica la página)
```

| Carpeta | Contenido |
|---|---|
| `app/` | Páginas: consultar (`page.js`), panorama del país (`panorama/`), mi ciudad (`mi-ciudad/`), mi canasta (`mi-canasta/`), alertas del mes (`alertas/`), cómo funcionaría de forma automática (`arquitectura/`) y cómo funciona (`como-funciona/`) |
| `components/` | Encabezado, tarjetas de precio y alerta, gráfica y razones |
| `lib/datos.js` | Carga del JSON y formatos (pesos, meses) |
| `lib/panorama.js`, `lib/panorama-html.js`, `lib/geo.json` | Mapas, mapa de calor, dispersión, red de centrales, calendario, orígenes y canasta (SVG hecho a mano, sin librerías); contorno de Colombia de Natural Earth (paquete `world-atlas`) |
| `public/data/pronosticos.json` | Pronósticos del mes (lo genera `generar_pronosticos.py`) |
| `public/data/extra.json`, `origen.json` | Calendario por alimento, red de centrales y orígenes del abastecimiento (los genera `generar_panorama.py`) |
| `scripts/generar_pronosticos.py` | Calcula los pronósticos con los modelos de la tesis |
| `scripts/generar_panorama.py` | Calcula el calendario, la red de centrales y los orígenes |
| `scripts/evaluar_mes_pasado.py` | Compara el pronóstico del mes anterior con el precio real (`public/data/evaluacion.json`) |

## Probarla en el computador

Requiere Node.js 20 o posterior.

```bash
npm install
npm run dev
```

y abrir <http://localhost:3000>.

## Publicarla en Vercel

1. Suba esta carpeta a un repositorio de GitHub (por ejemplo, `precios-central`).
2. En <https://vercel.com>, entre con su cuenta de GitHub, elija **Add New › Project** e importe el repositorio.
3. Vercel reconoce que es Next.js. Si la página está dentro de un repositorio más grande, en **Root Directory** elija la carpeta `web-precios`. Presione **Deploy**.

Cada vez que se suba un cambio a la rama principal, Vercel vuelve a publicar la página sola.

## Actualizar los pronósticos cada mes

La base de la tesis (`estudio/datos/base_unida_mensual.parquet`) llega a septiembre de 2026 y no se modifica, para que la
tesis siga siendo reproducible. Los meses publicados después se agregan a una copia propia de la página,
`datos/base_mensual_web.parquet` (hoy llega a octubre de 2026).

Cuando el DANE publique un boletín nuevo (por ejemplo, el de noviembre):

1. Descargue la serie histórica de precios mayoristas del año (`anex-SIPSA-SerieHistoricaMayorista-<año>.xlsx`) y los
   microdatos de abastecimiento (`anex-Microdato-abastecimiento-<año>.xlsx`) de la página del SIPSA.
2. Convierta el mes nuevo en filas de la base con las reglas de la tesis (`--desde` y `--hasta` dejan fuera los meses
   que el archivo trae incompletos) y péguelas a la base de la página:

   ```bash
   ../entorno/bin/python ../preparacion_datos/agregar_meses.py --base <base completa con producto_precio> \
       --precios_hist <sipsa_p_precios_2018_2025.parquet> --abastecimiento anex-Microdato-abastecimiento-2026.xlsx \
       --precios anex-SIPSA-SerieHistoricaMayorista-2026.xlsx --desde 2026-11 --hasta 2026-11 --salida mes_nuevo.parquet
   ```

   Luego aplique a esas filas la variedad corregida (`preparacion_datos/informe_variedad.json`) y agréguelas al final de
   `datos/base_mensual_web.parquet` con las mismas columnas.
3. Antes de reemplazar los pronósticos, guarde los vigentes y compárelos con los precios reales del mes que acaba de
   publicarse (sección "¿Cómo le fue al pronóstico del mes pasado?" del Panorama y línea de cada producto en Consultar):

   ```bash
   cp public/data/pronosticos.json public/data/historial/pronosticos_2026-11.json   # el mes que se había pronosticado
   ../entorno/bin/python scripts/evaluar_mes_pasado.py datos/base_mensual_web.parquet
   ```

4. Genere los pronósticos (indique la fecha en que el DANE publicó el boletín) y los datos de las páginas nuevas:

   ```bash
   ../entorno/bin/python scripts/generar_pronosticos.py ../estudio --base datos/base_mensual_web.parquet --publicado 2026-12-10
   ../entorno/bin/python scripts/generar_panorama.py ../estudio --base datos/base_mensual_web.parquet \
       --abastecimiento <archivos SIPSA-A que cubran los últimos 12 meses>
   ```

5. Suba los archivos nuevos:

   ```bash
   git add datos/ public/data/
   git commit -m "Pronósticos con el boletín de <mes>"
   git push
   ```

Vercel publica la versión nueva en uno o dos minutos. Si el mes pronosticado termina sin que se haya actualizado, la
página lo avisa sola.

### Qué hace el script

- Construye las variables del último mes publicado con el mismo código del panel de la tesis (`01_panel.py`).
- En el mes que se pronostica todavía no existe el mes objetivo, así que la frecuencia histórica de alzas y el cambio
  medio de ese mes se calculan con todos los años anteriores (en el panel de la tesis quedarían vacías).
- Carga los modelos guardados (`resultados/modelos/reg_CatBoost.joblib` y `clf_CatBoost.joblib`), aplica la
  recalibración del intercepto de la tesis y calcula el rango del 80 % con cuantiles y calibración conforme por grupo.
- Escribe tres razones en lenguaje sencillo a partir de los valores de Shapley del clasificador.
- Riesgo **alto** desde 0,60 de probabilidad y **medio** desde 0,30 (constantes `ALTO` y `MEDIO` del script).

## Próximos pasos (MLOps)

La pestaña **Arquitectura MLOps** de la página describe la propuesta completa: ingesta programada con Airflow, almacenamiento de los archivos originales, transformación con dbt, reentrenamiento con MLflow y selección automática del modelo campeón. En resumen:


- Descargar automáticamente los boletines del DANE y agregar los meses nuevos.
- Ejecutar el script en GitHub Actions una vez al mes y hacer `git push` del JSON, sin intervención manual.
- Reentrenar los modelos cada trimestre y vigilar el error de los últimos meses.
- Usar los boletines semanales para actualizar el pronóstico con más frecuencia.
- Avisos por correo o WhatsApp cuando un producto pase a riesgo alto.

## Aviso

Es un pronóstico estadístico basado en datos públicos. Ayuda a planear, pero no es una garantía.
