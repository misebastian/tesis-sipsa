/* Diagramas de la propuesta MLOps, dibujados en SVG (sin librerías). Todos los colores salen de las variables de globals.css. */

const TONOS = {
  fuente: { fondo: '#f1f3ef', borde: '#c9cfc8', titulo: 'var(--texto)' },
  airflow: { fondo: '#e7eef8', borde: '#9db6d6', titulo: '#1d4e89' },
  datos: { fondo: '#fdf4e3', borde: '#e2c189', titulo: '#7a5208' },
  dbt: { fondo: '#fdeee4', borde: '#e7a57f', titulo: '#9a3412' },
  modelo: { fondo: '#e8f0eb', borde: '#9cc4ad', titulo: '#1f5e47' },
  web: { fondo: '#efedff', borde: '#b9b2ea', titulo: '#463a9e' },
  decision: { fondo: '#ffffff', borde: '#1f6f54', titulo: 'var(--texto)' },
  no: { fondo: '#f6f7f4', borde: '#c9cfc8', titulo: 'var(--texto-2)' },
};

function Caja({ x, y, w, h, tono = 'fuente', titulo, lineas = [], etiqueta, r = 10 }) {
  const t = TONOS[tono];
  const altoTexto = 17 + lineas.length * 15;
  const y0 = y + h / 2 - altoTexto / 2 + 13;
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={r} style={{ fill: t.fondo, stroke: t.borde }} strokeWidth="1.5" />
      {etiqueta && (
        <text x={x + 10} y={y + 15} fontSize="10" fontWeight="700" letterSpacing="0.06em" style={{ fill: t.titulo, textTransform: 'uppercase' }}>{etiqueta}</text>
      )}
      <text x={x + w / 2} y={etiqueta ? y0 + 6 : y0} textAnchor="middle" fontSize="13.5" fontWeight="700" style={{ fill: t.titulo }}>{titulo}</text>
      {lineas.map((l, i) => (
        <text key={i} x={x + w / 2} y={(etiqueta ? y0 + 6 : y0) + 17 + i * 15} textAnchor="middle" fontSize="11.5" style={{ fill: 'var(--texto-3)' }}>{l}</text>
      ))}
    </g>
  );
}

function Flecha({ d, discontinua, etiqueta, ex, ey, color = '#7d8a83' }) {
  return (
    <g>
      <path d={d} fill="none" style={{ stroke: color }} strokeWidth="1.8" strokeDasharray={discontinua ? '6 5' : undefined} markerEnd={`url(#punta-${color.replace('#', '')})`} />
      {etiqueta && <text x={ex} y={ey} textAnchor="middle" fontSize="11" fontWeight="600" style={{ fill: color }}>{etiqueta}</text>}
    </g>
  );
}

function Puntas({ colores = ['#7d8a83'] }) {
  return (
    <defs>
      {colores.map((c) => (
        <marker key={c} id={`punta-${c.replace('#', '')}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" style={{ fill: c }} />
        </marker>
      ))}
    </defs>
  );
}

function Lienzo({ ancho, alto, etiqueta, children, minimo = 760 }) {
  return (
    <div className="diagrama">
      <svg viewBox={`0 0 ${ancho} ${alto}`} style={{ width: '100%', minWidth: minimo, height: 'auto', fontFamily: 'Inter, system-ui, sans-serif' }} role="img" aria-label={etiqueta}>
        {children}
      </svg>
    </div>
  );
}

/* ---------- 1. Arquitectura general ---------- */
export function DiagramaArquitectura() {
  const gris = '#7d8a83', azul = '#1d4e89', verde = '#1f6f54';
  return (
    <Lienzo ancho={1160} alto={560} minimo={820}
      etiqueta="Arquitectura propuesta: Airflow orquesta la descarga de los datos del DANE y la NOAA, su almacenamiento en un data lake y un almacén, la transformación con dbt, el entrenamiento y registro de modelos con MLflow, el pronóstico mensual y su publicación en GitHub y Vercel; un monitoreo compara el pronóstico con el precio real y activa el reentrenamiento.">
      <Puntas colores={[gris, azul, verde]} />
      {/* columnas */}
      {[['Fuentes', 20], ['Ingesta', 205], ['Almacenamiento', 375], ['Transformación', 565], ['Modelos', 765], ['Publicación', 970]].map(([t, x]) => (
        <text key={t} x={x} y={22} fontSize="11" fontWeight="700" letterSpacing="0.08em" style={{ fill: 'var(--texto-4)' }}>{t.toUpperCase()}</text>
      ))}
      {/* Airflow */}
      <rect x="195" y="36" width="945" height="40" rx="10" style={{ fill: TONOS.airflow.fondo, stroke: TONOS.airflow.borde }} strokeWidth="1.5" />
      <text x="215" y="61" fontSize="13.5" fontWeight="700" style={{ fill: azul }}>Apache Airflow</text>
      <text x="335" y="61" fontSize="12" style={{ fill: 'var(--texto-3)' }}>DAG «sipsa_mensual»: revisa a diario si salió el boletín y ejecuta todo el flujo en orden</text>
      {[290, 470, 660, 860, 1060].map((x) => (
        <path key={x} d={`M${x} 76 L${x} 104`} style={{ stroke: TONOS.airflow.borde }} strokeWidth="1.5" strokeDasharray="3 4" />
      ))}

      {/* Fuentes */}
      <Caja x={20} y={140} w={150} h={70} titulo="DANE · SIPSA" lineas={['Precios mayoristas', '(anexo mensual)']} />
      <Caja x={20} y={240} w={150} h={70} titulo="DANE · SIPSA" lineas={['Abastecimiento', '(microdatos diarios)']} />

      {/* Ingesta */}
      <Caja x={205} y={170} w={150} h={110} tono="airflow" titulo="Descarga y" lineas={['validación', 'Python + Great', 'Expectations']} />
      <Flecha d="M170 175 C188 175 188 205 203 208" color={gris} />
      <Flecha d="M170 275 C188 275 188 248 203 245" color={gris} />

      {/* Almacenamiento */}
      <Caja x={375} y={110} w={170} h={92} tono="datos" etiqueta="Bronce" titulo="Data lake" lineas={['S3 / Cloud Storage', 'archivos originales', 'con huella SHA-256']} />
      <Caja x={375} y={232} w={170} h={92} tono="datos" etiqueta="Almacén" titulo="Base de datos" lineas={['DuckDB · PostgreSQL', 'o BigQuery', 'tablas crudas']} />
      <Flecha d="M355 200 C365 190 365 165 373 160" color={gris} />
      <Flecha d="M460 202 L460 230" color={gris} />

      {/* dbt */}
      <rect x="565" y="104" width="180" height="250" rx="12" style={{ fill: '#fffaf6', stroke: TONOS.dbt.borde }} strokeWidth="1.5" />
      <text x="580" y="124" fontSize="13.5" fontWeight="700" style={{ fill: TONOS.dbt.titulo }}>dbt</text>
      <text x="610" y="124" fontSize="11" style={{ fill: 'var(--texto-3)' }}>modelos SQL + pruebas</text>
      <Caja x={580} y={136} w={150} h={52} tono="dbt" titulo="staging" lineas={['limpieza y unidades']} r={8} />
      <Caja x={580} y={208} w={150} h={52} tono="dbt" titulo="intermedio" lineas={['variedad y base mensual']} r={8} />
      <Caja x={580} y={280} w={150} h={58} tono="dbt" titulo="marts" lineas={['panel con 29 variables']} r={8} />
      <Flecha d="M655 188 L655 206" color={gris} />
      <Flecha d="M655 260 L655 278" color={gris} />
      <Flecha d="M545 278 C555 278 560 165 578 162" color={gris} />

      {/* Modelos */}
      <Caja x={765} y={104} w={180} h={84} tono="modelo" titulo="Entrenamiento" lineas={['CatBoost · LightGBM', 'XGBoost · origen móvil']} />
      <Caja x={765} y={210} w={180} h={84} tono="modelo" etiqueta="MLflow" titulo="Registro de modelos" lineas={['alias «champion»', 'y «challenger»']} />
      <Caja x={765} y={316} w={180} h={70} tono="modelo" titulo="Pronóstico mensual" lineas={['precio, rango y alerta']} />
      <Flecha d="M745 300 C755 300 752 150 763 146" color={verde} />
      <Flecha d="M855 188 L855 208" color={verde} etiqueta="elige campeón" ex={905} ey={202} />
      <Flecha d="M855 294 L855 314" color={verde} />
      <Flecha d="M745 320 L763 340" color={gris} />

      {/* Publicación */}
      <Caja x={970} y={104} w={170} h={70} tono="web" titulo="pronosticos.json" lineas={['versionado en GitHub']} />
      <Caja x={970} y={196} w={170} h={70} tono="web" titulo="Vercel" lineas={['página web pública']} />
      <Caja x={970} y={288} w={170} h={64} tono="web" titulo="Usuarios" lineas={['comerciantes, comedores…']} />
      <Flecha d="M945 350 C960 350 955 150 968 140" color={gris} />
      <Flecha d="M1055 174 L1055 194" color={gris} />
      <Flecha d="M1055 266 L1055 286" color={gris} />

      {/* Monitoreo */}
      <rect x="565" y="430" width="575" height="96" rx="12" style={{ fill: '#f1f5f9', stroke: '#b8c4d0' }} strokeWidth="1.5" strokeDasharray="6 5" />
      <text x="585" y="458" fontSize="13.5" fontWeight="700" style={{ fill: azul }}>Monitoreo</text>
      <text x="585" y="480" fontSize="12" style={{ fill: 'var(--texto-2)' }}>Cada mes compara el pronóstico anterior con el precio real que acaba de llegar</text>
      <text x="585" y="498" fontSize="12" style={{ fill: 'var(--texto-2)' }}>y vigila la deriva de los datos (Evidently). Si el error sube, avisa y adelanta</text>
      <text x="585" y="516" fontSize="12" style={{ fill: 'var(--texto-2)' }}>el reentrenamiento.</text>
      <Flecha d="M855 386 L855 428" color={gris} />
      <Flecha d="M1055 352 C1055 400 1080 400 1080 428" color={gris} />
      <Flecha d="M565 478 L540 478 L540 92 L830 92 L830 102" color={azul} discontinua />
      <text x={532} y={430} textAnchor="end" fontSize="11" fontWeight="600" style={{ fill: azul }}>si hay deriva:</text>
      <text x={532} y={445} textAnchor="end" fontSize="11" fontWeight="600" style={{ fill: azul }}>reentrenar</text>
    </Lienzo>
  );
}

/* ---------- 2. DAG de Airflow ---------- */
export function DiagramaDAG() {
  const gris = '#7d8a83', verde = '#1f6f54', azul = '#1d4e89';
  const N = (x, y, t, tono = 'airflow', w = 150, h = 46) => <Caja x={x} y={y} w={w} h={h} tono={tono} titulo={t} r={23} />;
  return (
    <Lienzo ancho={1160} alto={330} minimo={860}
      etiqueta="DAG sipsa_mensual: esperar_boletin, luego dos descargas en paralelo, validar_archivos, dbt_run, dbt_test y decidir_reentreno; si toca reentrenar se ejecutan entrenar_candidatos, evaluar y elegir_campeon; en ambos casos se ejecuta pronosticar, después publicar y monitorear.">
      <Puntas colores={[gris, verde, azul]} />
      {N(15, 120, 'esperar_boletin')}
      {N(200, 70, 'descargar_precios', 'datos', 165)}
      {N(200, 170, 'descargar_abasto', 'datos', 165)}
      {N(400, 120, 'validar_archivos')}
      {N(585, 120, 'dbt_run', 'dbt', 120)}
      {N(740, 120, 'dbt_test', 'dbt', 120)}
      <Caja x={895} y={108} w={150} h={70} tono="decision" titulo="decidir_" lineas={['reentreno']} r={14} />
      <Flecha d="M165 138 C182 138 182 93 198 93" color={gris} />
      <Flecha d="M165 148 C182 148 182 193 198 193" color={gris} />
      <Flecha d="M365 93 C382 93 382 138 398 138" color={gris} />
      <Flecha d="M365 193 C382 193 382 148 398 148" color={gris} />
      <Flecha d="M550 143 L583 143" color={gris} />
      <Flecha d="M705 143 L738 143" color={gris} />
      <Flecha d="M860 143 L893 143" color={gris} />
      {/* rama de reentrenamiento */}
      {N(380, 268, 'entrenar_candidatos', 'modelo', 175)}
      {N(590, 268, 'evaluar', 'modelo', 120)}
      {N(745, 268, 'elegir_campeon', 'modelo', 150)}
      <Flecha d="M970 178 C970 300 300 220 378 288" color={verde} etiqueta="sí: toca el trimestre o hay deriva" ex={640} ey={236} />
      <Flecha d="M555 291 L588 291" color={verde} />
      <Flecha d="M710 291 L743 291" color={verde} />
      {/* rama principal */}
      {N(1080 - 20, 40, 'pronosticar', 'modelo', 100)}
      <Flecha d="M1045 128 C1070 128 1070 100 1100 88" color={azul} etiqueta="no" ex={1078} ey={118} />
      <Flecha d="M895 291 C1110 291 1125 160 1112 88" color={verde} />
      <text x="1000" y="24" fontSize="11" style={{ fill: 'var(--texto-4)' }}>después de pronosticar:</text>
      <Caja x={840} y={30} w={95} h={40} tono="web" titulo="publicar" r={20} />
      <Caja x={720} y={30} w={105} h={40} tono="no" titulo="monitorear" r={20} />
      <Flecha d="M1058 50 L937 50" color={gris} />
      <Flecha d="M840 50 L827 50" color={gris} />
    </Lienzo>
  );
}

/* ---------- 3. Linaje de dbt ---------- */
export function DiagramaDbt() {
  return (
    <Lienzo ancho={840} alto={300} minimo={680}
      etiqueta="Linaje de dbt: las tablas crudas de precios y abastecimiento pasan a modelos staging, luego a int_variedad_referencia e int_base_mensual, y terminan en mart_panel_variables y mart_pronosticos.">
      <Puntas colores={['#7d8a83']} />
      {[['CRUDAS', 10], ['STAGING', 185], ['INTERMEDIO', 385], ['MARTS', 625]].map(([t, x]) => (
        <text key={t} x={x} y={18} fontSize="11" fontWeight="700" letterSpacing="0.08em" style={{ fill: 'var(--texto-4)' }}>{t}</text>
      ))}
      <Caja x={10} y={34} w={140} h={50} tono="datos" titulo="precios" r={8} />
      <Caja x={10} y={120} w={140} h={50} tono="datos" titulo="abastecimiento" r={8} />
      <Caja x={185} y={34} w={165} h={50} tono="dbt" titulo="stg_sipsa_precios" r={8} />
      <Caja x={185} y={120} w={165} h={50} tono="dbt" titulo="stg_sipsa_abasto" r={8} />
      <Caja x={385} y={50} w={205} h={58} tono="dbt" titulo="int_variedad_referencia" lineas={['variedad por central']} r={8} />
      <Caja x={385} y={150} w={205} h={58} tono="dbt" titulo="int_base_mensual" lineas={['precio + abasto']} r={8} />
      <Caja x={625} y={90} w={205} h={58} tono="modelo" titulo="mart_panel_variables" lineas={['29 variables del modelo']} r={8} />
      <Caja x={625} y={210} w={205} h={58} tono="web" titulo="mart_pronosticos" lineas={['precio, rango y alerta']} r={8} />
      {[59, 145].map((y) => <Flecha key={y} d={`M150 ${y} L183 ${y}`} />)}
      <Flecha d="M350 59 L383 72" />
      <Flecha d="M350 59 C368 59 368 165 383 168" />
      <Flecha d="M487 108 L487 148" />
      <Flecha d="M350 145 L383 175" />
      <Flecha d="M590 179 C605 179 605 125 623 122" />
      <Flecha d="M727 148 L727 208" />
      <text x={719} y={183} textAnchor="end" fontSize="10.5" style={{ fill: 'var(--texto-4)' }}>modelo campeón</text>
    </Lienzo>
  );
}

/* ---------- 4. Selección del campeón ---------- */
export function DiagramaCampeon() {
  const gris = '#7d8a83', verde = '#1f6f54', rojo = '#9a3412';
  const R = (x, y, w, h, t, l) => <Caja x={x} y={y} w={w} h={h} tono="decision" titulo={t} lineas={l} r={12} />;
  return (
    <Lienzo ancho={760} alto={430} minimo={620}
      etiqueta="Selección del campeón: el retador debe reducir el error al menos 2 por ciento con un intervalo que no incluya cero, no empeorar la AP más de 0,01 con calibración entre 0,8 y 1,2, y superar al último precio; si cumple todo pasa a ser el campeón, si no se mantiene el campeón actual.">
      <Puntas colores={[gris, verde, rojo]} />
      <Caja x={255} y={10} w={250} h={50} tono="modelo" titulo="Retador entrenado" lineas={['evaluado en los últimos 12 meses']} />
      {R(230, 90, 300, 62, '¿Reduce el error ≥ 2 %', ['con intervalo bootstrap sin cero?'])}
      {R(230, 185, 300, 62, '¿AP igual o mejor (−0,01)', ['y calibración entre 0,8 y 1,2?'])}
      {R(230, 280, 300, 62, '¿Supera al último precio?', ['(referencia mínima)'])}
      <Caja x={255} y={370} w={250} h={50} tono="modelo" titulo="Nuevo campeón" lineas={['alias «champion» en MLflow']} />
      <Caja x={575} y={185} w={170} h={70} tono="no" titulo="Se mantiene" lineas={['el campeón actual']} />
      <Flecha d="M380 60 L380 88" color={gris} />
      <Flecha d="M380 152 L380 183" color={verde} etiqueta="sí" ex={395} ey={172} />
      <Flecha d="M380 247 L380 278" color={verde} etiqueta="sí" ex={395} ey={267} />
      <Flecha d="M380 342 L380 368" color={verde} etiqueta="sí" ex={395} ey={360} />
      <Flecha d="M530 121 C560 121 600 150 640 183" color={rojo} etiqueta="no" ex={592} ey={124} />
      <Flecha d="M530 216 L573 216" color={rojo} etiqueta="no" ex={551} ey={208} />
      <Flecha d="M530 311 C565 311 610 290 640 257" color={rojo} etiqueta="no" ex={595} ey={322} />
      <text x={40} y={395} fontSize="11.5" style={{ fill: 'var(--texto-3)' }}>El campeón anterior queda</text>
      <text x={40} y={411} fontSize="11.5" style={{ fill: 'var(--texto-3)' }}>guardado para volver a él.</text>
    </Lienzo>
  );
}
