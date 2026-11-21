'use client';

import { useEffect, useState } from 'react';

/** Carga un archivo de public/data (extra.json, origen.json) una sola vez por visita. */
const cache = {};
export function useJson(nombre) {
  const [datos, setDatos] = useState(cache[nombre] || null);
  const [error, setError] = useState(null);
  useEffect(() => {
    if (cache[nombre]) return;
    fetch(`/data/${nombre}`)
      .then((r) => {
        if (!r.ok) throw new Error('No se pudieron cargar los datos');
        return r.json();
      })
      .then((d) => {
        cache[nombre] = d;
        setDatos(d);
      })
      .catch((e) => setError(e.message));
  }, [nombre]);
  return { datos, error };
}
