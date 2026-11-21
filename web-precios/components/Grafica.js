'use client';

import { useEffect, useState } from 'react';
import { mesCorto, pesos, redondear } from '../lib/datos';

/** Precio de los últimos 13 meses, el pronóstico y su rango probable, dibujado en SVG (sin librerías). */
export default function Grafica({ serie, mesPronostico }) {
  // en pantallas angostas se muestran solo los últimos 7 meses para que la gráfica se lea sin desplazarse
  const [angosta, setAngosta] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 600px)');
    const f = () => setAngosta(mq.matches);
    f(); mq.addEventListener('change', f);
    return () => mq.removeEventListener('change', f);
  }, []);
  const hist = angosta ? serie.historia.slice(-7) : serie.historia; // [[mes, precio], ...]
  const W = angosta ? 400 : 780, H = 260, x0 = 52, x1 = W - 20, y0 = 20, y1 = 220;
  const maximo = Math.max(...hist.map((h) => h[1]), serie.rango[1], serie.precio_esperado);
  const paso = escala(maximo);
  const tope = Math.ceil(maximo / paso) * paso;
  const n = hist.length; // el pronóstico va en la posición n
  const x = (i) => x0 + (i * (x1 - 30 - x0)) / n;
  const y = (p) => y1 - (p / tope) * (y1 - y0);
  const marcas = [];
  for (let v = 0; v <= tope + 1; v += paso) marcas.push(v);
  const puntos = hist.map((h, i) => `${x(i).toFixed(1)},${y(h[1]).toFixed(1)}`).join(' ');
  const xf = x(n), yf = y(serie.precio_esperado);
  const cada = angosta ? 2 : 3;
  const fs = angosta ? 13 : 11;
  const etiquetasX = hist.map((h, i) => ({ i, t: mesCorto(h[0]) })).filter((e) => (n - 1 - e.i) % cada === 0);
  const resumen = `Precio por kilo de ${serie.producto} entre ${mesCorto(hist[0][0])} y ${mesCorto(hist[n - 1][0])}, de ${pesos(Math.min(...hist.map((h) => h[1])))} a ${pesos(Math.max(...hist.map((h) => h[1])))}, y pronóstico de ${pesos(redondear(serie.precio_esperado))} para ${mesCorto(mesPronostico)}, con rango de ${pesos(redondear(serie.rango[0]))} a ${pesos(redondear(serie.rango[1]))}.`;

  return (
    <section className="tarjeta" aria-labelledby="t-grafica" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="grafica__cab">
        <h2 id="t-grafica" style={{ fontSize: 18 }}>Precio de los últimos {n} meses y pronóstico</h2>
        <div className="leyenda">
          <span><span style={{ width: 16, height: 3, background: 'var(--texto)', display: 'inline-block' }} />Precio real</span>
          <span><span style={{ width: 12, height: 12, borderRadius: '50%', background: 'var(--acento)', display: 'inline-block' }} />Pronóstico</span>
          <span><span style={{ width: 14, height: 12, background: 'var(--rango)', display: 'inline-block' }} />Rango probable</span>
        </div>
      </div>
      <div className="grafica__caja">
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }} role="img" aria-label={resumen}>
          {marcas.map((v) => (
            <g key={v}>
              <line x1={x0} x2={x1} y1={y(v)} y2={y(v)} stroke="var(--pista)" />
              <text x={x0 - 6} y={y(v) + 4} textAnchor="end" fontSize={fs} fill="var(--texto-4)">{pesos(v)}</text>
            </g>
          ))}
          <rect x={xf - 24} y={y(serie.rango[1])} width="48" height={Math.max(4, y(serie.rango[0]) - y(serie.rango[1]))} rx="6" fill="var(--rango)" />
          <line x1={x(n - 1)} y1={y(hist[n - 1][1])} x2={xf} y2={yf} stroke="var(--acento)" strokeWidth="2.5" strokeDasharray="5 4" />
          <polyline points={puntos} fill="none" stroke="var(--texto)" strokeWidth="2.5" strokeLinejoin="round" />
          <circle cx={x(n - 1)} cy={y(hist[n - 1][1])} r="4" fill="var(--texto)" />
          <circle cx={xf} cy={yf} r="7" fill="var(--acento)" stroke="#fff" strokeWidth="2" />
          <text x={xf} y={Math.max(14, y(serie.rango[1]) - 8)} textAnchor="middle" fontSize={fs + 1} fontWeight="700" fill="var(--acento-oscuro)">
            {pesos(redondear(serie.precio_esperado))}
          </text>
          {etiquetasX.map((e) => (
            <text key={e.i} x={x(e.i)} y={244} textAnchor="middle" fontSize={fs} fill="var(--texto-4)">{e.t}</text>
          ))}
          <text x={xf} y={258} textAnchor="middle" fontSize={fs} fontWeight="700" fill="var(--acento-oscuro)">{mesCorto(mesPronostico)}</text>
        </svg>
      </div>
    </section>
  );
}

function escala(maximo) {
  const bruto = maximo / 4;
  const pot = Math.pow(10, Math.floor(Math.log10(bruto)));
  const f = bruto / pot;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * pot;
}
