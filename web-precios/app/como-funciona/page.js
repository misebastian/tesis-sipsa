export const metadata = { title: 'Cómo funciona · Precios de la central' };

export default function ComoFunciona() {
  return (
    <main className="contenido">
      <section className="titular">
        <h1>Cómo funciona</h1>
        <p>Una explicación corta de qué muestra esta página y cómo leerla.</p>
      </section>
      <section className="texto-largo">
        <h2>¿De dónde salen los datos?</h2>
        <p>
          Del Sistema de Información de Precios y Abastecimiento del Sector Agropecuario (SIPSA) del DANE. Cada mes, el DANE
          publica el precio mayorista promedio de cada alimento en las principales centrales de abasto del país y las toneladas
          que llegan a cada una.
        </p>
        <h2>¿Qué es el precio esperado?</h2>
        <p>
          Es el precio por kilo que el modelo considera más probable para el mes siguiente al último boletín. El rango que lo
          acompaña muestra dónde cae el precio real en 8 de cada 10 meses.
        </p>
        <h2>¿Qué es una alerta de alza fuerte?</h2>
        <p>
          Indica qué tan probable es que el precio suba más del 15 % el mes siguiente. «62 de cada 100» quiere decir que, en
          situaciones parecidas del pasado, 62 de cada 100 terminaron en un alza de ese tamaño. Riesgo alto es 6 o más de cada
          10; riesgo medio, entre 3 y 6.
        </p>
        <h2>¿Cómo se calcula?</h2>
        <p>
          Con un modelo de aprendizaje automático (CatBoost) entrenado con los precios de 2019 a 2024 de 1.260 combinaciones de
          producto y central. El modelo tiene en cuenta la temporada, lo que pasa con el mismo producto en las demás centrales,
          qué tan alto o bajo está el precio frente al último año y el abastecimiento del país. Las razones que aparecen debajo de
          cada pronóstico son las que más pesaron en ese caso.
        </p>
        <h2>¿Qué tan confiable es?</h2>
        <p>
          Se probó con los precios de enero de 2025 a septiembre de 2026, que el modelo no había visto. Se equivocó en promedio un
          12 % menos que suponer que el precio no cambia. De cada 10 alzas fuertes, avisó de unas 7; de cada 10 alertas, unas 4
          se cumplieron. Funciona mejor en frutas y verduras; en granos y productos procesados el precio casi no cambia y el
          pronóstico aporta poco.
        </p>
        <h2>Límites</h2>
        <p>
          Es un pronóstico estadístico, no una garantía. No conoce eventos que no aparecen en los datos, como un paro, un cierre de
          vías o una helada, y se actualiza solo cuando el DANE publica un nuevo boletín.
        </p>
      </section>
    </main>
  );
}
