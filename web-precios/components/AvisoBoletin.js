'use client';

import { useEffect, useState } from 'react';
import { nombreMes, soloMes } from '../lib/datos';

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
/** "2026-11-10" → "10 de noviembre de 2026" */
const fechaLarga = (f) => { const [a, m, d] = f.split('-').map(Number); return `${d} de ${MESES[m - 1]} de ${a}`; };

/**
 * Dice de qué boletín salen los pronósticos, cuándo se publicó y qué se pronostica (el promedio de todo el mes,
 * aunque una parte ya haya pasado al publicarse el boletín). Si el mes pronosticado ya terminó, avisa que el
 * pronóstico venció. La fecha de hoy se lee en el navegador para que el aviso no dependa de cuándo se publicó la página.
 */
export default function AvisoBoletin({ datos }) {
  const [vencido, setVencido] = useState(false);
  useEffect(() => {
    const [a, m] = datos.mes_pronostico.split('-').map(Number);
    setVencido(new Date() >= new Date(a, m, 1));          // primer día del mes siguiente al pronosticado
  }, [datos.mes_pronostico]);
  const mp = soloMes(datos.mes_pronostico), mu = soloMes(datos.ultimo_mes);
  const sig = (() => { const [a, m] = datos.mes_pronostico.split('-').map(Number); return MESES[m % 12]; })();
  return (
    <div className="pz-aviso-wrap">
      {vencido && (
        <div className="aviso-boletin aviso-boletin--vencido" role="status">
          <strong>Este pronóstico era para {nombreMes(datos.mes_pronostico)} y ese mes ya terminó.</strong> Se actualizará
          cuando el DANE publique el boletín de {mp}, con el pronóstico de {sig}.
        </div>
      )}
      <div className="aviso-boletin">
        Pronósticos hechos con el boletín de {nombreMes(datos.ultimo_mes)}
        {datos.boletin_publicado ? <>, que el DANE publicó el <strong>{fechaLarga(datos.boletin_publicado)}</strong></> : null}.
        Cada pronóstico es el precio promedio de todo {mp}, incluidos los días de {mp} que ya habían pasado cuando salió el
        boletín de {mu}.
      </div>
    </div>
  );
}
