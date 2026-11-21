'use client';

import { useEffect } from 'react';
import { useDatos } from '../../lib/datos';
import AvisoBoletin from '../../components/AvisoBoletin';
import { useJson } from '../../lib/useJson';
import { montarPanorama } from '../../lib/panorama';
import { HTML_PANORAMA } from '../../lib/panorama-html';

export default function Panorama() {
  const { datos, error } = useDatos();
  const extra = useJson('extra.json');
  const ev = useJson('evaluacion.json');
  useEffect(() => {
    if (datos && extra.datos && (ev.datos || ev.error)) montarPanorama(datos, extra.datos, ev.datos);
  }, [datos, extra.datos, ev.datos, ev.error]);
  const fallo = error || extra.error;
  return (
    <main className="contenido pz">
      {fallo && <p className="estado">{fallo}. Intente de nuevo en unos minutos.</p>}
      {!fallo && (!datos || !extra.datos) && <p className="estado">Cargando los pronósticos…</p>}
      {datos && <AvisoBoletin datos={datos} />}
      <div dangerouslySetInnerHTML={{ __html: HTML_PANORAMA }} />
    </main>
  );
}
