// Estructura HTML de las páginas nuevas; lib/panorama.js la llena con los datos.
export const HTML_PANORAMA = `<div class="vista">

  <section class="titular">
    <span class="cinta" id="cinta">Pronóstico para octubre de 2026</span>
    <h1>Así se ven los precios del próximo mes en el país</h1>
    <p>Cada punto es un alimento en una central de abasto. El color indica si el modelo espera que el precio suba o baje y qué tan probable es un alza fuerte, de más del 15 %.</p>
  </section>

  <div class="filtros" role="group" aria-label="Grupo de alimentos" id="filtros"><span>Grupo de alimentos</span></div>

  <section class="kpis" id="kpis" aria-label="Resumen"></section>

  <section class="tarjeta" aria-labelledby="t-mapa">
    <div class="tarjeta__cab">
      <div><h2 id="t-mapa">Mapa de las centrales</h2><p>El tamaño del círculo es el número de alimentos que se siguen en la ciudad. Toque una ciudad para ver sus alertas.</p></div>
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
      <div><h2 id="t-calor">Dónde sube y dónde baja</h2><p>Cambio esperado de octubre frente a septiembre, en la mediana de los alimentos de cada grupo y ciudad.</p></div>
      <div class="leyenda" id="leyenda-calor"></div>
    </div>
    <div class="desliza"><table class="calor" id="calor"></table></div>
  </section>

  <section class="tarjeta" aria-labelledby="t-disp">
    <div class="tarjeta__cab">
      <div><h2 id="t-disp">Probabilidad de alza frente al cambio esperado</h2><p>Arriba están los alimentos con más riesgo de un alza fuerte; a la derecha, los que el modelo espera que suban más. Toque un punto para ver ese alimento en todo el país.</p></div>
      <div class="leyenda"><span><i style="background:var(--alto)"></i>Riesgo alto</span><span><i style="background:var(--medio)"></i>Medio</span><span><i style="background:var(--bajo)"></i>Bajo</span></div>
    </div>
    <div class="desliza"><svg class="grafica disp" id="disp" viewBox="0 0 1000 420" role="img" aria-label="Diagrama de dispersión de la probabilidad de alza fuerte frente al cambio esperado"></svg></div>
  </section>

  <section class="tarjeta" aria-labelledby="t-red">
    <div class="tarjeta__cab">
      <div><h2 id="t-red">Red de centrales</h2><p>Dos centrales quedan unidas cuando los precios de los mismos alimentos suben y bajan juntos, mes a mes, desde 2018. Las líneas más gruesas son las más parecidas. Toque una central para ver a cuáles se parece.</p></div>
      <div style="min-width:220px">
        <label class="nota" for="umbral-red">Mostrar uniones desde <b id="umbral-txt">0,60</b></label>
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
      <div><h2 id="t-prod">Un alimento en todo el país</h2><p>Los precios de un mismo alimento se mueven juntos entre centrales. Compare dónde estará más barato en octubre.</p></div>
      <div class="panel__cab"><label for="sel-prod" class="nota">Alimento</label> <select id="sel-prod"></select></div>
    </div>
    <div class="dos">
      <div>
        <svg class="grafica" id="lineas" viewBox="0 0 640 330" role="img" aria-label="Precio mensual del alimento en cada central"></svg>
        <p class="nota" id="nota-lineas"></p>
      </div>
      <div class="panel">
        <h3 style="font-size:16px">Precio esperado en octubre, de menor a mayor</h3>
        <ul class="ranking" id="ranking"></ul>
      </div>
    </div>
    <div class="panel" style="gap:10px">
      <h3 style="font-size:16px" id="t-cal">Calendario</h3>
      <div class="cal" id="cal"></div>
      <div class="cal-ley"><span>Color: cambio típico de cada mes frente al anterior (2018 a 2026).</span><span>Barrita: parte de los años con alza fuerte en ese mes.</span><span>Recuadro: el mes que se pronostica.</span></div>
      <p class="nota" id="nota-cal"></p>
    </div>
  </section>

</div>
<div class="tip" id="tip" hidden></div>`;

export const HTML_CIUDAD = `<div class="vista" >
  <section class="titular">
    <span class="cinta">Mi ciudad · abastecimiento de octubre de 2025 a septiembre de 2026</span>
    <h1>De dónde llega la comida de su ciudad y qué se espera para octubre</h1>
    <p>El DANE registra el departamento de origen de cada carga que entra a las centrales. Con eso se ve de dónde viene cada alimento y cuáles tienen riesgo de alza el próximo mes.</p>
  </section>
  <div class="filtros"><label for="sel-ciudad2" class="nota" style="margin-right:6px">Ciudad</label><select id="sel-ciudad2" class="sel-grande"></select></div>
  <section class="kpis" id="kpis-ciudad" aria-label="Resumen de la ciudad"></section>
  <section class="tarjeta" aria-labelledby="t-flujo">
    <div class="tarjeta__cab">
      <div><h2 id="t-flujo">De dónde llega</h2><p>Cada línea va del departamento de origen a la ciudad; su grosor es la parte de las toneladas que aporta. Toque un departamento para ver qué alimentos llegan principalmente de allí.</p></div>
    </div>
    <div class="mapa-grid">
      <div><svg class="mapa" id="mapa-flujo" role="img" aria-label="Mapa de los departamentos de origen de los alimentos que llegan a la ciudad"></svg></div>
      <div class="panel">
        <h3 style="font-size:16px">Principales orígenes</h3>
        <ul class="origen-lista" id="origenes"></ul>
        <p class="nota" id="nota-import"></p>
      </div>
    </div>
  </section>
  <section class="tarjeta" aria-labelledby="t-tabla-ciudad">
    <div class="tarjeta__cab">
      <div><h2 id="t-tabla-ciudad">Alimentos de la ciudad en octubre</h2><p id="sub-tabla-ciudad">Ordenados por probabilidad de alza fuerte.</p></div>
      <button type="button" class="btn" id="limpiar-origen" hidden>Ver todos los orígenes</button>
    </div>
    <div class="tabla-wrap"><table class="tabla" id="tabla-ciudad"></table></div>
    <p class="nota">El modelo no usa el origen para pronosticar; esta información describe de dónde llegó el alimento en los últimos 12 meses.</p>
  </section>
</div>
<div class="tip" id="tip" hidden></div>`;

export const HTML_CANASTA = `<div class="vista" >
  <section class="titular">
    <span class="cinta">Mi canasta · precios mayoristas por kilo</span>
    <h1>¿Cuánto costará su compra en la central el próximo mes?</h1>
    <p>Elija su central, los alimentos que compra y cuántos kilos. La página suma el costo con los precios de septiembre y con los esperados para octubre.</p>
  </section>
  <div class="filtros"><label for="sel-central" class="nota" style="margin-right:6px">Central</label><select id="sel-central" class="sel-grande"></select></div>
  <section class="canasta-total" id="canasta-total" aria-live="polite"></section>
  <section class="tarjeta" aria-labelledby="t-canasta">
    <div class="tarjeta__cab">
      <div><h2 id="t-canasta">Su lista</h2><p id="sub-canasta">Canasta de ejemplo; cámbiela a su gusto.</p></div>
      <div class="agregar"><label for="sel-agregar" class="nota">Agregar</label><select id="sel-agregar"></select><button type="button" class="btn btn--prim" id="btn-agregar">Agregar</button></div>
    </div>
    <div class="tabla-wrap"><table class="tabla" id="tabla-canasta"></table></div>
    <p class="nota">Son precios mayoristas promedio de la central, no precios de tienda. El rango total suma los rangos de cada alimento, así que es aproximado.</p>
  </section>
</div>
<div class="tip" id="tip" hidden></div>`;
