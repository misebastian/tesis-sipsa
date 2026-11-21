// Estructura HTML de las páginas nuevas; lib/panorama.js la llena con los datos.
// Los elementos con clase mes-p (mes pronosticado) y mes-u (último mes publicado) se llenan con los meses del JSON.

const GLOSARIO = `
  <details class="glosario">
    <summary>¿Qué significa cada término?</summary>
    <dl>
      <dt>Precio</dt><dd>Precio mayorista promedio del mes en la central, en pesos por kilo ($/kg), según el DANE (SIPSA). No es el precio de tienda.</dd>
      <dt>Cambio esperado</dt><dd>Diferencia en porcentaje entre el precio que el modelo espera para <span class="mes-p">el próximo mes</span> y el último precio publicado (<span class="mes-u">el último mes</span>).</dd>
      <dt>Alza fuerte</dt><dd>Que el precio suba más del 15 % de un mes al siguiente.</dd>
      <dt>Probabilidad de alza fuerte</dt><dd>Qué tan probable es, según el modelo, que haya un alza fuerte. Un 60 % quiere decir que, de cada 10 alimentos con esa probabilidad, se esperaría que unos 6 tuvieran un alza fuerte.</dd>
      <dt>Riesgo alto, medio y bajo</dt><dd>Alto: probabilidad de alza fuerte de 60 % o más. Medio: entre 30 % y 60 %. Bajo: menos de 30 %.</dd>
      <dt>Cambio típico</dt><dd>El cambio del alimento que queda en la mitad cuando se ordenan todos los de un grupo o ciudad, de menor a mayor (la mediana). No lo mueven unos pocos alimentos con cambios muy grandes.</dd>
      <dt>Estable</dt><dd>Cambio esperado entre −2 % y +2 %; en la página se considera que el precio prácticamente no cambia.</dd>
      <dt>Rango</dt><dd>Precios entre los que quedaría el del próximo mes con una probabilidad del 80 %.</dd>
    </dl>
  </details>`;

const LEY_CAMBIO = '<span><i style="background:var(--d1)"></i>baja 8 % o más</span><span><i style="background:var(--d2)"></i>baja entre 2 % y 8 %</span><span><i style="background:var(--d3)"></i>estable (entre −2 % y +2 %)</span><span><i style="background:var(--d4)"></i>sube entre 2 % y 8 %</span><span><i style="background:var(--d5)"></i>sube 8 % o más</span>';
export { LEY_CAMBIO };

export const HTML_PANORAMA = `<div class="vista">

  <section class="titular">
    <span class="cinta" id="cinta">Pronóstico del próximo mes</span>
    <h1>Así se ven los precios del próximo mes en el país</h1>
    <p>Cada punto es un alimento en una central de abasto. El color indica si el modelo espera que el precio suba o baje y qué tan probable es un alza fuerte, de más del 15 %. Todos los precios son mayoristas, en pesos por kilo.</p>
  </section>
  ${GLOSARIO}

  <div class="filtros" role="group" aria-label="Grupo de alimentos" id="filtros"><span>Grupo de alimentos</span></div>

  <section class="kpis" id="kpis" aria-label="Resumen"></section>

  <section class="tarjeta" aria-labelledby="t-mapa">
    <div class="tarjeta__cab">
      <div><h2 id="t-mapa">Mapa de las centrales</h2><p>Un círculo por ciudad; su tamaño es el número de alimentos que se siguen allí. Toque una ciudad para ver sus alimentos con más riesgo.</p></div>
      <div class="seg" role="group" aria-label="Qué mostrar en el mapa">
        <button type="button" id="m-riesgo" aria-pressed="true">Riesgo de alza</button>
        <button type="button" id="m-cambio" aria-pressed="false">Cambio esperado</button>
      </div>
    </div>
    <div class="mapa-grid">
      <div>
        <svg class="mapa" id="mapa" role="img" aria-label="Mapa de Colombia con las ciudades que tienen central de abasto"></svg>
        <div class="leyenda" id="leyenda-mapa"></div>
      </div>
      <div class="panel" id="panel"></div>
    </div>
  </section>

  <section class="tarjeta" aria-labelledby="t-calor">
    <div class="tarjeta__cab">
      <div><h2 id="t-calor">Dónde sube y dónde baja</h2><p>Cada celda es el cambio típico esperado de <span class="mes-u">el último mes</span> a <span class="mes-p">el próximo</span>, en porcentaje, para los alimentos de un grupo en una ciudad. Por ejemplo, +3 quiere decir que el alimento típico de ese grupo subiría 3 %. Un punto (·) indica que hay menos de dos alimentos de ese grupo en la ciudad.</p></div>
    </div>
    <div class="leyenda">${LEY_CAMBIO}</div>
    <div class="desliza"><table class="calor" id="calor"></table></div>
  </section>

  <section class="tarjeta" aria-labelledby="t-disp">
    <div class="tarjeta__cab">
      <div><h2 id="t-disp">Probabilidad de alza fuerte frente al cambio esperado</h2><p>Cada punto es un alimento en una central. Arriba están los que tienen más probabilidad de subir más del 15 %; a la derecha, los que el modelo espera que suban más. Las líneas punteadas marcan dónde empieza el riesgo medio (30 %) y el alto (60 %). Toque un punto para ver ese alimento en todo el país.</p></div>
      <div class="leyenda"><span><i style="background:var(--alto)"></i>Riesgo alto (60 % o más)</span><span><i style="background:var(--medio)"></i>Medio (30 a 60 %)</span><span><i style="background:var(--bajo)"></i>Bajo (menos de 30 %)</span></div>
    </div>
    <div class="desliza"><svg class="grafica disp" id="disp" viewBox="0 0 1000 420" role="img" aria-label="Diagrama de dispersión de la probabilidad de alza fuerte frente al cambio esperado"></svg></div>
  </section>

  <section class="tarjeta" aria-labelledby="t-red">
    <div class="tarjeta__cab">
      <div><h2 id="t-red">Red de centrales</h2><p>Dos centrales quedan unidas cuando los precios de los mismos alimentos suben y bajan juntos, mes a mes, desde <span id="red-desde">2018</span>. El parecido se mide de 0 (sin relación) a 1 (se mueven igual); es la correlación del cambio mensual del precio. Las líneas más gruesas son las más parecidas. Toque una central para ver a cuáles se parece.</p></div>
      <div style="min-width:220px">
        <label class="nota" for="umbral-red">Dibujar solo uniones con parecido de <b id="umbral-txt">0,60</b> o más</label>
        <input type="range" id="umbral-red" min="40" max="90" step="5" value="60">
      </div>
    </div>
    <div class="red-grid">
      <div>
        <svg class="red" id="red" viewBox="0 0 760 520" role="img" aria-label="Red de centrales según qué tanto se mueven juntos sus precios"></svg>
        <div class="leyenda" id="ley-red"></div>
      </div>
      <div class="panel" id="panel-red"></div>
    </div>
  </section>

  <section class="tarjeta" aria-labelledby="t-prod" id="sec-prod">
    <div class="tarjeta__cab">
      <div><h2 id="t-prod">Un alimento en todo el país</h2><p>Precio mensual por kilo de un mismo alimento en cada central durante el último año, y el que se espera para <span class="mes-p">el próximo mes</span> (línea punteada). Compare dónde estará más barato.</p></div>
      <div class="panel__cab"><label for="sel-prod" class="nota">Alimento</label> <select id="sel-prod"></select></div>
    </div>
    <div class="dos">
      <div>
        <svg class="grafica" id="lineas" viewBox="0 0 640 330" role="img" aria-label="Precio mensual del alimento en cada central"></svg>
        <p class="nota" id="nota-lineas"></p>
      </div>
      <div class="panel">
        <h3 style="font-size:16px">Precio esperado en <span class="mes-p">el próximo mes</span>, de menor a mayor (<span class="uni">$/kg</span>)</h3>
        <ul class="ranking" id="ranking"></ul>
      </div>
    </div>
    <div class="panel" style="gap:10px">
      <h3 style="font-size:16px" id="t-cal">Calendario</h3>
      <div class="cal" id="cal"></div>
      <div class="cal-ley"><span>Número y color: cambio típico del precio en ese mes frente al mes anterior, en porcentaje, con los años <span id="cal-anios">2018 a 2026</span>.</span><span>Barrita inferior: parte de los años en que ese mes tuvo un alza fuerte (más del 15 %).</span><span>Recuadro: el mes que se pronostica.</span></div>
      <div class="leyenda">${LEY_CAMBIO}</div>
      <p class="nota" id="nota-cal"></p>
    </div>
  </section>

</div>
<div class="tip" id="tip" hidden></div>`;

export const HTML_CIUDAD = `<div class="vista">
  <section class="titular">
    <span class="cinta" id="cinta-ciudad">Mi ciudad</span>
    <h1>De dónde llega la comida de su ciudad y qué se espera para <span class="mes-p">el próximo mes</span></h1>
    <p>El DANE registra el departamento de origen de cada carga que entra a las centrales de abasto. Con eso se ve de dónde viene cada alimento y cuáles tienen riesgo de alza el próximo mes. Las cifras de origen cuentan solo los alimentos que tienen pronóstico en esta página.</p>
  </section>
  ${GLOSARIO}
  <div class="filtros"><label for="sel-ciudad2" class="nota" style="margin-right:6px">Ciudad</label><select id="sel-ciudad2" class="sel-grande"></select></div>
  <section class="kpis" id="kpis-ciudad" aria-label="Resumen de la ciudad"></section>
  <section class="tarjeta" aria-labelledby="t-flujo">
    <div class="tarjeta__cab">
      <div><h2 id="t-flujo">De dónde llega</h2><p>Cada línea va del departamento de origen a la ciudad. El grosor de la línea y el tamaño del círculo indican qué parte de las toneladas que llegaron en los últimos 12 meses aporta ese departamento. Toque un departamento para ver qué alimentos llegan principalmente de allí.</p></div>
    </div>
    <div class="mapa-grid">
      <div><svg class="mapa" id="mapa-flujo" role="img" aria-label="Mapa de los departamentos de origen de los alimentos que llegan a la ciudad"></svg></div>
      <div class="panel">
        <h3 style="font-size:16px">Principales orígenes (% de las toneladas)</h3>
        <ul class="origen-lista" id="origenes"></ul>
        <p class="nota" id="nota-import"></p>
      </div>
    </div>
  </section>
  <section class="tarjeta" aria-labelledby="t-tabla-ciudad">
    <div class="tarjeta__cab">
      <div><h2 id="t-tabla-ciudad">Alimentos de la ciudad en <span class="mes-p">el próximo mes</span></h2><p id="sub-tabla-ciudad">Ordenados por probabilidad de alza fuerte.</p></div>
      <button type="button" class="btn" id="limpiar-origen" hidden>Ver todos los orígenes</button>
    </div>
    <div class="tabla-wrap"><table class="tabla" id="tabla-ciudad"></table></div>
    <p class="nota">"Llega de" muestra los dos departamentos que más toneladas aportaron en los últimos 12 meses y su porcentaje. El modelo no usa el origen para pronosticar; esta columna solo describe de dónde llegó el alimento. Precios en pesos por kilo.</p>
  </section>
</div>
<div class="tip" id="tip" hidden></div>`;

export const HTML_CANASTA = `<div class="vista">
  <section class="titular">
    <span class="cinta">Mi canasta · precios mayoristas en pesos por kilo</span>
    <h1>¿Cuánto costará su compra en la central el próximo mes?</h1>
    <p>Elija su central, los alimentos que compra y cuántos kilos. La página suma el costo con los precios de <span class="mes-u">el último mes</span> y con los esperados para <span class="mes-p">el próximo mes</span>.</p>
  </section>
  <div class="filtros"><label for="sel-central" class="nota" style="margin-right:6px">Central</label><select id="sel-central" class="sel-grande"></select></div>
  <section class="canasta-total" id="canasta-total" aria-live="polite"></section>
  <section class="tarjeta" aria-labelledby="t-canasta">
    <div class="tarjeta__cab">
      <div><h2 id="t-canasta">Su lista</h2><p id="sub-canasta">Canasta de ejemplo; cámbiela a su gusto.</p></div>
      <div class="agregar"><label for="sel-agregar" class="nota">Agregar</label><select id="sel-agregar"></select><button type="button" class="btn btn--prim" id="btn-agregar">Agregar</button></div>
    </div>
    <div class="tabla-wrap"><table class="tabla" id="tabla-canasta"></table></div>
    <p class="nota">Son precios mayoristas promedio de la central, no precios de tienda. "Riesgo" es la probabilidad de que el precio suba más del 15 %: alto, 60 % o más; medio, de 30 % a 60 %; bajo, menos de 30 %. El rango suma los rangos del 80 % de cada alimento, así que es aproximado: es poco probable que todos queden en su extremo a la vez.</p>
  </section>
</div>
<div class="tip" id="tip" hidden></div>`;
