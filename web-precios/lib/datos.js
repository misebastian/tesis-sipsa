'use client';

import { useEffect, useState } from 'react';

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** Carga public/data/pronosticos.json una sola vez por visita. */
let cache = null;
export function useDatos() {
  const [datos, setDatos] = useState(cache);
  const [error, setError] = useState(null);
  useEffect(() => {
    if (cache) return;
    fetch('/data/pronosticos.json')
      .then((r) => {
        if (!r.ok) throw new Error('No se pudieron cargar los pronósticos');
        return r.json();
      })
      .then((d) => {
        cache = d;
        setDatos(d);
      })
      .catch((e) => setError(e.message));
  }, []);
  return { datos, error };
}

/** "2026-10" → "octubre de 2026" */
export function nombreMes(ym) {
  const [a, m] = ym.split('-').map(Number);
  return `${MESES[m - 1]} de ${a}`;
}

/** "2026-10" → "octubre" */
export function soloMes(ym) {
  return MESES[Number(ym.split('-')[1]) - 1];
}

/** "2026-10" → "oct 26" */
export function mesCorto(ym) {
  const [a, m] = ym.split('-');
  return `${MESES_CORTOS[Number(m) - 1]} ${a.slice(2)}`;
}

/** 3109 → "$3.109" */
export function pesos(n) {
  return '$' + Math.round(n).toLocaleString('es-CO');
}

/** Redondea un precio para mostrarlo (a 50 pesos si es menor de 10.000; a 100 si es mayor). */
export function redondear(n) {
  const paso = n < 10000 ? 50 : 100;
  return Math.round(n / paso) * paso;
}

/** "Medellín, Central Mayorista de Antioquia" → { ciudad: "Medellín", nombre: "Central Mayorista de Antioquia" } */
export function partesCentral(central) {
  const i = central.indexOf(',');
  if (i < 0) return { ciudad: central, nombre: central };
  return { ciudad: central.slice(0, i).trim(), nombre: central.slice(i + 1).trim() };
}

export const TEXTO_RIESGO = { alto: 'Riesgo alto', medio: 'Riesgo medio', bajo: 'Riesgo bajo' };
