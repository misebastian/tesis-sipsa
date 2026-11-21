'use client';

import { useEffect } from 'react';
import { useDatos } from '../../lib/datos';
import { useJson } from '../../lib/useJson';
import { montarPanorama } from '../../lib/panorama';
import { HTML_PANORAMA } from '../../lib/panorama-html';

export default function Panorama() {
  const { datos, error } = useDatos();
  const extra = useJson('extra.json');
  useEffect(() => {
    if (datos && extra.datos) montarPanorama(datos, extra.datos);
  }, [datos, extra.datos]);
  const fallo = error || extra.error;
  return (
    <main className="contenido pz">
      {fallo && <p className="estado">{fallo}. Intente de nuevo en unos minutos.</p>}
      {!fallo && (!datos || !extra.datos) && <p className="estado">Cargando los pronósticos…</p>}
      <div dangerouslySetInnerHTML={{ __html: HTML_PANORAMA }} />
    </main>
  );
}
