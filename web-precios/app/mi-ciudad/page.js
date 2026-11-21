'use client';

import { useEffect } from 'react';
import { useDatos } from '../../lib/datos';
import AvisoBoletin from '../../components/AvisoBoletin';
import { useJson } from '../../lib/useJson';
import { montarCiudad } from '../../lib/panorama';
import { HTML_CIUDAD } from '../../lib/panorama-html';

export default function MiCiudad() {
  const { datos, error } = useDatos();
  const origen = useJson('origen.json');
  useEffect(() => {
    if (datos && origen.datos) montarCiudad(datos, origen.datos);
  }, [datos, origen.datos]);
  const fallo = error || origen.error;
  return (
    <main className="contenido pz">
      {fallo && <p className="estado">{fallo}. Intente de nuevo en unos minutos.</p>}
      {!fallo && (!datos || !origen.datos) && <p className="estado">Cargando los pronósticos…</p>}
      {datos && <AvisoBoletin datos={datos} />}
      <div dangerouslySetInnerHTML={{ __html: HTML_CIUDAD }} />
    </main>
  );
}
