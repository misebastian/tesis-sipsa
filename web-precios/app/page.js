'use client';

import { useEffect, useMemo, useState } from 'react';
import { useDatos, nombreMes, pesos, partesCentral } from '../lib/datos';
import Grafica from '../components/Grafica';
import { TarjetaPrecio, TarjetaAlerta, Razones, Confianza } from '../components/Tarjetas';

const INICIAL = { producto: 'Limón Tahití', central: 'Medellín, Central Mayorista de Antioquia' };

export default function Consultar() {
  const { datos, error } = useDatos();
  const [producto, setProducto] = useState(INICIAL.producto);
  const [central, setCentral] = useState(INICIAL.central);

  // permite abrir un producto desde la página de alertas (?producto=…&central=…)
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    if (q.get('producto')) setProducto(q.get('producto'));
    if (q.get('central')) setCentral(q.get('central'));
  }, []);

  const productos = useMemo(() => (datos ? [...new Set(datos.series.map((s) => s.producto))].sort((a, b) => a.localeCompare(b, 'es')) : []), [datos]);
  const centrales = useMemo(
    () => (datos ? datos.series.filter((s) => s.producto === producto).map((s) => s.central).sort((a, b) => a.localeCompare(b, 'es')) : []),
    [datos, producto]
  );
  const centralValida = centrales.includes(central) ? central : centrales[0];
  const serie = datos?.series.find((s) => s.producto === producto && s.central === centralValida);

  if (error) return <main className="contenido"><p className="estado">{error}. Intente de nuevo en unos minutos.</p></main>;
  if (!datos) return <main className="contenido"><p className="estado">Cargando los pronósticos…</p></main>;

  const pc = serie ? partesCentral(serie.central) : null;

  return (
    <main className="contenido">
      <section className="titular">
        <h1>¿Qué pasará con el precio el próximo mes?</h1>
        <p>Pronósticos calculados con el último boletín del DANE ({nombreMes(datos.ultimo_mes)}). Elija un producto y una central para ver el precio esperado en {nombreMes(datos.mes_pronostico)} y si hay riesgo de un alza fuerte.</p>
      </section>

      <section className="resumen" aria-label="Resumen del último boletín">
        <div className="tarjeta resumen__item">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--texto-3)" strokeWidth="2" strokeLinecap="round" aria-hidden="true" style={{ flexShrink: 0 }}><circle cx="12" cy="12" r="9" /><path d="M12 8v4l3 2" /></svg>
          <div><div style={{ fontSize: 15, fontWeight: 600 }}>Datos hasta {nombreMes(datos.ultimo_mes)}</div><div className="resumen__t">Pronóstico para {nombreMes(datos.mes_pronostico)}</div></div>
        </div>
        <div className="tarjeta resumen__item">
          <span className="punto" style={{ background: 'var(--acento)' }} />
          <div><div className="resumen__n">{datos.series.length.toLocaleString('es-CO')}</div><div className="resumen__t">productos y centrales con pronóstico</div></div>
        </div>
        <div className="tarjeta resumen__item">
          <span className="punto" style={{ background: 'var(--alto)' }} />
          <div><div className="resumen__n">{datos.series.filter((x) => x.riesgo === 'alto').length}</div><div className="resumen__t">con riesgo alto de alza</div></div>
        </div>
      </section>

      <section className="tarjeta" aria-label="Elegir producto">
        <form className="formulario" onSubmit={(e) => e.preventDefault()}>
          <div className="campo">
            <label htmlFor="producto">Producto</label>
            <select id="producto" value={producto} onChange={(e) => setProducto(e.target.value)}>
              {productos.map((p) => <option key={p}>{p}</option>)}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="central">Central de abasto</label>
            <select id="central" value={centralValida} onChange={(e) => setCentral(e.target.value)}>
              {centrales.map((c) => {
                const p = partesCentral(c);
                return <option key={c} value={c}>{p.ciudad} · {p.nombre}</option>;
              })}
            </select>
          </div>
          {serie && (
            <p className="nota-dato">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 8v4l3 2" /></svg>
              Último precio publicado por el DANE: <strong style={{ color: 'var(--texto)' }}>{pesos(serie.precio_actual)} por kilo</strong> ({nombreMes(datos.ultimo_mes)}).
            </p>
          )}
        </form>
      </section>

      {serie ? (
        <>
          <section aria-labelledby="t-res" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h2 id="t-res" style={{ fontSize: 20 }}>{serie.producto} en {pc.ciudad} · pronóstico para {nombreMes(datos.mes_pronostico)}</h2>
            <div className="resultados" aria-live="polite">
              <TarjetaPrecio serie={serie} ultimoMes={datos.ultimo_mes} />
              <TarjetaAlerta serie={serie} mesPronostico={datos.mes_pronostico} />
            </div>
          </section>
          <Grafica serie={serie} mesPronostico={datos.mes_pronostico} />
          <Razones serie={serie} />
        </>
      ) : (
        <p className="estado">No hay pronóstico para esta combinación.</p>
      )}

      <Confianza />
    </main>
  );
}
