'use client';

import { useEffect } from 'react';
import { useDatos } from '../../lib/datos';
import AvisoBoletin from '../../components/AvisoBoletin';
import { montarCanasta } from '../../lib/panorama';
import { HTML_CANASTA } from '../../lib/panorama-html';

export default function MiCanasta() {
  const { datos, error } = useDatos();
  useEffect(() => {
    if (datos) montarCanasta(datos);
  }, [datos]);
  return (
    <main className="contenido pz">
      {error && <p className="estado">{error}. Intente de nuevo en unos minutos.</p>}
      {!error && !datos && <p className="estado">Cargando los pronósticos…</p>}
      {datos && <AvisoBoletin datos={datos} />}
      <div dangerouslySetInnerHTML={{ __html: HTML_CANASTA }} />
    </main>
  );
}
