'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useDatos, nombreMes, partesCentral } from '../../lib/datos';
import AvisoBoletin from '../../components/AvisoBoletin';

export default function Alertas() {
  const { datos, error } = useDatos();
  const [central, setCentral] = useState('Medellín, Central Mayorista de Antioquia');

  const centrales = useMemo(() => (datos ? [...new Set(datos.series.map((s) => s.central))].sort((a, b) => a.localeCompare(b, 'es')) : []), [datos]);
  const lista = useMemo(
    () => (datos ? datos.series.filter((s) => s.central === central && s.riesgo !== 'bajo').sort((a, b) => b.prob_alza - a.prob_alza) : []),
    [datos, central]
  );

  if (error) return <main className="contenido"><p className="estado">{error}. Intente de nuevo en unos minutos.</p></main>;
  if (!datos) return <main className="contenido"><p className="estado">Cargando las alertas…</p></main>;

  const altos = lista.filter((s) => s.riesgo === 'alto').length;
  const medios = lista.length - altos;
  const u = datos.umbrales;

  return (
    <main className="contenido">
      <section className="alertas-cab">
        <div className="titular">
          <h1>Alertas de {nombreMes(datos.mes_pronostico)}</h1>
          <p>Productos con más riesgo de subir más del 15 % el próximo mes en la central que usted elija.</p>
        </div>
        <div className="campo">
          <label htmlFor="central">Central de abasto</label>
          <select id="central" value={central} onChange={(e) => setCentral(e.target.value)}>
            {centrales.map((c) => {
              const p = partesCentral(c);
              return <option key={c} value={c}>{p.ciudad} · {p.nombre}</option>;
            })}
          </select>
        </div>
      </section>

      <AvisoBoletin datos={datos} />

      <section className="resumen" aria-label="Resumen">
        <div className="tarjeta resumen__item">
          <span className="punto" style={{ background: 'var(--alto)' }} />
          <div><div className="resumen__n">{altos}</div><div className="resumen__t">con riesgo alto</div></div>
        </div>
        <div className="tarjeta resumen__item">
          <span className="punto" style={{ background: 'var(--medio)' }} />
          <div><div className="resumen__n">{medios}</div><div className="resumen__t">con riesgo medio</div></div>
        </div>
        <div className="tarjeta resumen__item">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--texto-3)" strokeWidth="2" strokeLinecap="round" aria-hidden="true" style={{ flexShrink: 0 }}><circle cx="12" cy="12" r="9" /><path d="M12 8v4l3 2" /></svg>
          <div>
            <div style={{ fontSize: 15, fontWeight: 600 }}>Datos hasta {nombreMes(datos.ultimo_mes)}</div>
            <div className="resumen__t">Se actualiza con cada boletín del DANE</div>
          </div>
        </div>
      </section>

      <section className="tarjeta" style={{ padding: 0, overflow: 'hidden' }} aria-label="Lista de productos">
        {lista.length === 0 ? (
          <p className="vacio">No hay productos con riesgo alto o medio en esta central para el próximo mes.</p>
        ) : (
          <div className="tabla-caja">
            <table className="tabla">
              <thead>
                <tr>
                  <th scope="col">Producto</th>
                  <th scope="col">Riesgo de alza fuerte</th>
                  <th scope="col" style={{ width: '36%' }}>Probabilidad</th>
                  <th scope="col"><span style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)' }}>Acción</span></th>
                </tr>
              </thead>
              <tbody>
                {lista.map((s) => {
                  const n = Math.round(s.prob_alza * 100);
                  return (
                    <tr key={s.producto}>
                      <td style={{ fontWeight: 600 }}>{s.producto}</td>
                      <td><span className={`insignia insignia--${s.riesgo}`}>{s.riesgo === 'alto' ? 'Alto' : 'Medio'}</span></td>
                      <td>
                        <div className="prob">
                          <div className="prob__pista"><div className="prob__barra" style={{ width: `${n}%`, background: s.riesgo === 'alto' ? 'var(--alto)' : 'var(--medio)' }} /></div>
                          <span style={{ width: 92, fontSize: 14, color: 'var(--texto-2)' }}>{n} de 100</span>
                        </div>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <Link href={`/?producto=${encodeURIComponent(s.producto)}&central=${encodeURIComponent(s.central)}`} style={{ fontWeight: 600, fontSize: 14, textDecoration: 'none', padding: '10px 6px' }}>
                          Ver detalle
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p style={{ margin: 0, fontSize: 14, color: 'var(--texto-3)', maxWidth: 760, lineHeight: 1.55 }}>
        Riesgo alto: {Math.round(u.alto * 10)} o más de cada 10 casos parecidos terminaron en un alza de más del 15 %. Riesgo medio: entre{' '}
        {Math.round(u.medio * 10)} y {Math.round(u.alto * 10)} de cada 10. Los productos con riesgo bajo no se muestran en esta lista.
      </p>
    </main>
  );
}
