import { pesos, redondear, soloMes } from '../lib/datos';

const ICONO = {
  alto: <><path d="M12 9v4" /><path d="M12 17h.01" /><path d="M10.3 3.9L2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></>,
  medio: <><circle cx="12" cy="12" r="9" /><path d="M12 8v5" /><path d="M12 16h.01" /></>,
  bajo: <><circle cx="12" cy="12" r="9" /><path d="M8 12.5l2.5 2.5L16 9.5" /></>,
};
const ESTILO = {
  alto: { icono: 'var(--alto)', texto: 'var(--alto-texto)', consejo: '#fbf3ee', nivel: 'Riesgo alto' },
  medio: { icono: 'var(--medio)', texto: 'var(--medio-texto)', consejo: '#fdf7ea', nivel: 'Riesgo medio' },
  bajo: { icono: 'var(--bajo)', texto: 'var(--bajo-texto)', consejo: '#f1f7f3', nivel: 'Riesgo bajo' },
};

export function TarjetaPrecio({ serie, ultimoMes }) {
  const esperado = redondear(serie.precio_esperado);
  const [lo, hi] = serie.rango.map(redondear);
  const c = serie.cambio_pct;
  const sentido = c >= 2 ? 'sube' : c <= -2 ? 'baja' : 'igual';
  // posición de la banda y la marca en una escala que va un poco más allá del rango
  const a = Math.min(lo, serie.precio_actual) * 0.85, b = Math.max(hi, serie.precio_actual) * 1.1;
  const pos = (v) => `${(((v - a) / (b - a)) * 100).toFixed(1)}%`;
  return (
    <article className="tarjeta tarjeta-res">
      <div className="etiqueta">Precio esperado</div>
      <div className="cifra">
        <span className="cifra__n">{pesos(esperado)}</span>
        <span className="cifra__u">por kilo</span>
      </div>
      <div className={`chip chip--${sentido}`}>
        {sentido !== 'igual' && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
            {sentido === 'sube' ? <><path d="M12 19V5" /><path d="M5 12l7-7 7 7" /></> : <><path d="M12 5v14" /><path d="M19 12l-7 7-7-7" /></>}
          </svg>
        )}
        {sentido === 'igual'
          ? `Casi igual que en ${soloMes(ultimoMes)}`
          : `${sentido === 'sube' ? 'Sube' : 'Baja'} cerca de ${Math.round(Math.abs(c))} % frente a ${soloMes(ultimoMes)}`}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ fontSize: 15, color: 'var(--texto-2)' }}>
          Lo más probable es que quede <strong>entre {pesos(lo)} y {pesos(hi)}</strong>.
        </div>
        <div className="barra-rango" aria-hidden="true">
          <div className="barra-rango__banda" style={{ left: pos(lo), width: `calc(${pos(hi)} - ${pos(lo)})` }} />
          <div className="barra-rango__marca" style={{ left: pos(esperado) }} />
        </div>
        <div className="escala" aria-hidden="true"><span>{pesos(lo)}</span><span>{pesos(esperado)}</span><span>{pesos(hi)}</span></div>
        <div className="pie">En 8 de cada 10 meses el precio real cae dentro de este rango.</div>
      </div>
    </article>
  );
}

export function TarjetaAlerta({ serie, mesPronostico }) {
  const r = serie.riesgo;
  const e = ESTILO[r];
  const n = Math.round(serie.prob_alza * 100);
  const consejo = {
    alto: `Si compra este producto para revender o para un comedor, considere planear sus compras de ${soloMes(mesPronostico)} con anticipación.`,
    medio: 'Hay una posibilidad real de alza. Vale la pena revisar el precio de nuevo cuando salga el próximo boletín.',
    bajo: 'No se esperan alzas fuertes el próximo mes.',
  }[r];
  return (
    <article className={`tarjeta tarjeta-res alerta alerta--${r}`}>
      <div className="etiqueta">Alerta de alza fuerte</div>
      <div className="alerta__fila">
        <div className="alerta__icono" style={{ background: e.icono }}>
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{ICONO[r]}</svg>
        </div>
        <div>
          <div className="alerta__nivel" style={{ color: e.texto }}>{e.nivel}</div>
          <div style={{ fontSize: 15, color: 'var(--texto-2)' }}>{n} de cada 100 casos parecidos terminaron en un alza de más del 15 %.</div>
        </div>
      </div>
      <div className="semaforo" role="img" aria-label={`Escala de riesgo: bajo, medio, alto. Nivel actual: ${r}`}>
        <div style={{ background: r === 'bajo' ? 'var(--bajo)' : '#d7e7dd' }} />
        <div style={{ background: r === 'medio' ? 'var(--medio)' : '#f3d9a4' }} />
        <div style={{ background: r === 'alto' ? 'var(--alto)' : '#f2c9b3' }} />
      </div>
      <div className="escala" aria-hidden="true">
        <span style={r === 'bajo' ? { color: e.texto, fontWeight: 600 } : null}>Bajo</span>
        <span style={r === 'medio' ? { color: e.texto, fontWeight: 600 } : null}>Medio</span>
        <span style={r === 'alto' ? { color: e.texto, fontWeight: 600 } : null}>Alto</span>
      </div>
      <div className="consejo" style={{ background: e.consejo }}>{consejo}</div>
    </article>
  );
}

const ICONOS_RAZON = [
  <><rect x="3" y="4" width="18" height="17" rx="2" /><path d="M3 9h18M8 2v4M16 2v4" /></>,
  <><circle cx="6" cy="12" r="3" /><circle cx="18" cy="6" r="3" /><circle cx="18" cy="18" r="3" /><path d="M8.6 10.7l6.8-3.4M8.6 13.3l6.8 3.4" /></>,
  <><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 4v5h5" /></>,
];

export function Razones({ serie }) {
  if (!serie.razones?.length) return null;
  return (
    <section aria-labelledby="t-razones" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <h2 id="t-razones" style={{ fontSize: 18 }}>¿Por qué este pronóstico?</h2>
      <div className="razones">
        {serie.razones.map((r, i) => (
          <div className="razon" key={i}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--acento-oscuro)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0 }}>
              {ICONOS_RAZON[i % ICONOS_RAZON.length]}
            </svg>
            <div><strong>{r.titulo}</strong> {r.texto}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function Confianza() {
  return (
    <section className="confianza" aria-label="Confiabilidad y fuente">
      <div>
        <h2>¿Qué tan confiable es?</h2>
        <p>
          Probado con los precios de enero de 2025 a septiembre de 2026, el pronóstico se equivocó en promedio un 12 % menos
          que suponer que el precio no cambia. De cada 10 alzas fuertes, avisó de 7; de cada 10 alertas, unas 4 se cumplieron.
        </p>
      </div>
      <div>
        <h2>De dónde salen los datos</h2>
        <p>
          Precios y abastecimiento publicados cada mes por el DANE (SIPSA). Es un pronóstico estadístico: ayuda a planear,
          pero no es una garantía.
        </p>
      </div>
    </section>
  );
}
