import { DiagramaArquitectura, DiagramaDAG, DiagramaDbt, DiagramaCampeon } from '../../components/Diagramas';

export const metadata = { title: 'Arquitectura MLOps · Precios de la central' };

const ETAPAS = [
  {
    n: 1, titulo: 'Ingesta', herramienta: 'Airflow',
    texto: 'Un trabajo programado espera a que el DANE publique el boletín del mes y descarga los precios, el abastecimiento y el índice ONI de la NOAA.',
    icono: <><path d="M12 3v12" /><path d="M7 10l5 5 5-5" /><path d="M4 21h16" /></>,
  },
  {
    n: 2, titulo: 'Almacenamiento', herramienta: 'Data lake + almacén',
    texto: 'Los archivos originales se guardan sin cambios, con fecha y huella SHA-256 (capa bronce), y se cargan a un almacén de datos.',
    icono: <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5" /><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" /></>,
  },
  {
    n: 3, titulo: 'Transformación', herramienta: 'dbt',
    texto: 'Modelos SQL versionados limpian los datos, unen precio y abastecimiento, eligen la variedad de referencia y calculan las 52 variables, con pruebas de calidad.',
    icono: <><path d="M4 6h16" /><path d="M7 12h10" /><path d="M10 18h4" /></>,
  },
  {
    n: 4, titulo: 'Entrenamiento', herramienta: 'Python + MLflow',
    texto: 'Cada trimestre, o si se detecta deriva, se reentrenan los modelos candidatos con validación por origen móvil y se registran sus métricas.',
    icono: <><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1" /></>,
  },
  {
    n: 5, titulo: 'Campeón', herramienta: 'Registro de modelos',
    texto: 'Un candidato reemplaza al modelo en uso solo si mejora de forma clara y significativa. Si no, se mantiene el campeón actual.',
    icono: <><path d="M8 21h8" /><path d="M12 17v4" /><path d="M7 4h10v5a5 5 0 0 1-10 0V4z" /><path d="M17 5h3a3 3 0 0 1-3 4M7 5H4a3 3 0 0 0 3 4" /></>,
  },
  {
    n: 6, titulo: 'Pronóstico y publicación', herramienta: 'GitHub + Vercel',
    texto: 'El campeón calcula el pronóstico del mes siguiente para todas las series y publica el archivo que lee esta página.',
    icono: <><rect x="3" y="4" width="18" height="14" rx="2" /><path d="M8 21h8" /><path d="M7 12l3-3 3 3 4-4" /></>,
  },
];

const TAREAS = [
  ['esperar_boletin', 'Sensor que revisa cada día si el DANE ya publicó el anexo del mes (unos ocho días después del cierre).'],
  ['descargar_precios · descargar_abastecimiento · descargar_oni', 'Descargan los archivos en paralelo y los guardan en la capa bronce con su huella SHA-256.'],
  ['validar_archivos', 'Revisa columnas, unidades y número de registros frente a meses anteriores; si algo no cuadra, se detiene y avisa.'],
  ['dbt_run · dbt_test', 'Ejecuta los modelos de transformación y sus pruebas (sin duplicados, sin precios negativos, cobertura por central).'],
  ['decidir_reentreno', 'Rama: reentrena si toca el trimestre o si el monitoreo detectó deriva; si no, pasa directo al pronóstico.'],
  ['entrenar_candidatos → evaluar → elegir_campeon', 'Reentrena CatBoost, LightGBM y XGBoost, los compara con el campeón y actualiza el alias «champion» en MLflow.'],
  ['pronosticar', 'Carga el modelo con alias «champion» y calcula precio esperado, rango del 80 % y probabilidad de alza.'],
  ['publicar', 'Escribe el JSON de pronósticos y lo sube a GitHub; Vercel publica la página nueva.'],
  ['monitorear', 'Compara el pronóstico del mes anterior con el precio real que acaba de llegar y actualiza el tablero de error.'],
];


const REGLAS = [
  'Se evalúa con origen móvil sobre los últimos 12 meses, con las métricas de la tesis: error absoluto medio del cambio, precisión media (AP) de las alzas y calibración.',
  'Un retador reemplaza al campeón solo si reduce el error en al menos un 2 % y el intervalo bootstrap por bloques de meses no incluye el cero.',
  'No puede empeorar la AP en más de 0,01 ni salirse de una pendiente de calibración entre 0,8 y 1,2.',
  'Siempre debe superar al último precio. Si ningún modelo lo hace, la página publica el último precio y lo indica.',
  'El campeón anterior queda guardado en el registro para volver a él con un clic.',
];

const STACK = [
  ['Orquestación', 'Apache Airflow (DAG mensual)'],
  ['Almacenamiento', 'Objetos en S3 o Google Cloud Storage (bronce) y un almacén: DuckDB, PostgreSQL o BigQuery'],
  ['Transformación y calidad', 'dbt con pruebas; Great Expectations para validar archivos de entrada'],
  ['Entrenamiento', 'Python en contenedores Docker: CatBoost, LightGBM, XGBoost'],
  ['Experimentos y registro', 'MLflow Tracking y Model Registry (alias «champion» y «challenger»)'],
  ['Monitoreo', 'Evidently para deriva de datos y un tablero con el error mensual'],
  ['Publicación', 'GitHub (versiona el JSON) y Vercel (página web)'],
];

const ESTADO = [
  ['Descarga de datos', 'Manual, desde la página del DANE', 'Automática, con Airflow'],
  ['Preparación de la base', 'Scripts de Python ejecutados a mano', 'Modelos dbt versionados y probados'],
  ['Reentrenamiento', 'Una vez, para la tesis (2019–2024)', 'Trimestral o cuando hay deriva'],
  ['Elección del modelo', 'Validación de la tesis', 'Reglas automáticas campeón–retador'],
  ['Pronóstico', 'Script mensual en el computador', 'Tarea del DAG con el modelo campeón'],
  ['Seguimiento del error', 'Solo en la prueba de la tesis', 'Cada mes, con alertas'],
];

const CODIGO = `from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.sensors.python import PythonSensor
from cosmos import DbtTaskGroup              # dbt dentro de Airflow
import pendulum

with DAG("sipsa_mensual",
         schedule="0 6 * * *",              # revisa a diario si salió el boletín
         start_date=pendulum.datetime(2026, 11, 1, tz="America/Bogota"),
         catchup=False, max_active_runs=1) as dag:

    esperar = PythonSensor(task_id="esperar_boletin", python_callable=boletin_nuevo,
                           mode="reschedule", poke_interval=6 * 3600)
    descargas = [PythonOperator(task_id=f"descargar_{f}", python_callable=descargar, op_args=[f])
                 for f in ("precios", "abastecimiento", "oni")]
    validar = PythonOperator(task_id="validar_archivos", python_callable=validar_archivos)
    dbt = DbtTaskGroup(group_id="dbt", project_config=proyecto_dbt)       # run + test
    decidir = BranchPythonOperator(task_id="decidir_reentreno", python_callable=toca_reentrenar)
    entrenar = PythonOperator(task_id="entrenar_y_elegir_campeon", python_callable=entrenar_candidatos)
    pronosticar = PythonOperator(task_id="pronosticar", python_callable=pronosticar_con_campeon,
                                 trigger_rule="none_failed_min_one_success")
    publicar = PythonOperator(task_id="publicar", python_callable=subir_json_a_github)
    monitorear = PythonOperator(task_id="monitorear", python_callable=comparar_con_real)

    esperar >> descargas >> validar >> dbt >> decidir >> [entrenar, pronosticar]
    entrenar >> pronosticar >> publicar >> monitorear`;

export default function Arquitectura() {
  return (
    <main className="contenido">
      <section className="titular">
        <span className="insignia insignia--propuesta" style={{ alignSelf: 'flex-start' }}>Propuesta</span>
        <h1>Cómo funcionaría de forma automática</h1>
        <p>
          Hoy los pronósticos se calculan una vez al mes en un computador. Esta es la propuesta para que todo el proceso, desde
          la descarga de los datos del DANE hasta la publicación en esta página, ocurra solo, con modelos que se reentrenan y se
          reemplazan únicamente cuando mejoran.
        </p>
      </section>

      <section aria-labelledby="t-flujo" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <h2 id="t-flujo" style={{ fontSize: 20 }}>Arquitectura completa</h2>
        <p className="pista-movil">Deslice el diagrama hacia los lados para verlo completo.</p>
        <DiagramaArquitectura />
        <ol className="flujo flujo--compacto">
          {ETAPAS.map((e) => (
            <li key={e.n} className="flujo__paso">
              <div className="flujo__cab">
                <span className="flujo__n">Paso {e.n}</span>
                <span className="flujo__herr">{e.herramienta}</span>
              </div>
              <h3>{e.titulo}</h3>
              <p>{e.texto}</p>
            </li>
          ))}
        </ol>
        <div className="monitoreo">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0 }}><path d="M3 12h4l3-8 4 16 3-8h4" /></svg>
          <div>
            <strong>Monitoreo continuo.</strong> Cada mes, cuando llega el precio real, se compara con lo que se pronosticó. Si el
            error sube o los datos cambian de comportamiento (deriva), se avisa al equipo y se adelanta el reentrenamiento.
          </div>
        </div>
      </section>

      <section className="tarjeta" aria-labelledby="t-dag" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div>
          <h2 id="t-dag" style={{ fontSize: 18 }}>El trabajo mensual en Airflow</h2>
          <p style={{ margin: '6px 0 0', fontSize: 15, color: 'var(--texto-3)' }}>Un DAG llamado <code>sipsa_mensual</code> encadena estas tareas. Si una falla, las siguientes no se ejecutan y la página sigue mostrando el último pronóstico válido.</p>
        </div>
        <DiagramaDAG />
        <details className="codigo">
          <summary>Ver qué hace cada tarea</summary>
          <div className="tabla-caja" style={{ marginTop: 10 }}>
            <table className="tabla tabla--simple">
              <thead><tr><th scope="col">Tarea</th><th scope="col">Qué hace</th></tr></thead>
              <tbody>
                {TAREAS.map(([t, d]) => (
                  <tr key={t}><td><code>{t}</code></td><td>{d}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
        <details className="codigo">
          <summary>Ver un esquema del DAG en Python</summary>
          <pre><code>{CODIGO}</code></pre>
        </details>
      </section>

        <section className="tarjeta" aria-labelledby="t-dbt" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h2 id="t-dbt" style={{ fontSize: 18 }}>Transformación con dbt</h2>
          <p style={{ margin: 0, fontSize: 15, color: 'var(--texto-3)' }}>Las reglas de la tesis pasan a modelos SQL versionados, con pruebas que se corren en cada carga.</p>
          <DiagramaDbt />
        </section>

        <section className="tarjeta" aria-labelledby="t-campeon" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h2 id="t-campeon" style={{ fontSize: 18 }}>Cómo se elige el modelo campeón</h2>
          <DiagramaCampeon />
          <details className="codigo">
            <summary>Ver las reglas completas</summary>
            <ol className="reglas" style={{ marginTop: 10 }}>
              {REGLAS.map((r, i) => <li key={i}>{r}</li>)}
            </ol>
          </details>
        </section>

      <section className="tarjeta" aria-labelledby="t-stack" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h2 id="t-stack" style={{ fontSize: 18 }}>Herramientas propuestas</h2>
        <div className="tabla-caja">
          <table className="tabla tabla--simple">
            <tbody>
              {STACK.map(([a, b]) => (
                <tr key={a}><th scope="row" style={{ width: '28%' }}>{a}</th><td>{b}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="tarjeta" aria-labelledby="t-estado" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h2 id="t-estado" style={{ fontSize: 18 }}>Hoy y con la propuesta</h2>
        <div className="tabla-caja">
          <table className="tabla tabla--simple">
            <thead><tr><th scope="col">Parte del proceso</th><th scope="col">Hoy</th><th scope="col">Con la propuesta</th></tr></thead>
            <tbody>
              {ESTADO.map(([a, b, c]) => (
                <tr key={a}><td style={{ fontWeight: 600 }}>{a}</td><td>{b}</td><td>{c}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <p style={{ margin: 0, fontSize: 14, color: 'var(--texto-3)', maxWidth: 760, lineHeight: 1.55 }}>
        Esta sección describe una propuesta de trabajo futuro. Las reglas de selección y la frecuencia de reentrenamiento parten de
        lo evaluado en la tesis (reestimación trimestral, validación por origen móvil e intervalos bootstrap por meses).
      </p>
    </main>
  );
}
