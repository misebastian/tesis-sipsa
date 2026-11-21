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
| `app/` | Páginas: consultar (`page.js`), alertas del mes (`alertas/`), cómo funcionaría de forma automática (`arquitectura/`) y cómo funciona (`como-funciona/`) |
| `components/` | Encabezado, tarjetas de precio y alerta, gráfica y razones |
| `lib/datos.js` | Carga del JSON y formatos (pesos, meses) |
| `public/data/pronosticos.json` | Pronósticos del mes (lo genera el script) |
| `scripts/generar_pronosticos.py` | Calcula los pronósticos con los modelos de la tesis |

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
3. Vercel reconoce que es Next.js; no hay que cambiar nada. Presione **Deploy**.

Cada vez que se suba un cambio a la rama principal, Vercel vuelve a publicar la página sola.

## Actualizar los pronósticos cada mes

Cuando el DANE publique un boletín nuevo:

1. Agregue los meses nuevos a la base del estudio (`preparacion_datos/agregar_meses.py`).
2. Desde esta carpeta, con el entorno de Python del estudio:

   ```bash
   ../entorno/bin/python scripts/generar_pronosticos.py ../estudio
   ```

3. Suba el JSON nuevo:

   ```bash
   git add public/data/pronosticos.json
   git commit -m "Pronósticos con el boletín de <mes>"
   git push
   ```

Vercel publica la versión nueva en uno o dos minutos.

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
