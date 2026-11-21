'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const ENLACES = [
  { href: '/', texto: 'Consultar' },
  { href: '/alertas', texto: 'Alertas del mes' },
  { href: '/como-funciona', texto: 'Cómo funciona' },
  { href: '/arquitectura', texto: 'Arquitectura MLOps' },
];

export default function Encabezado() {
  const ruta = usePathname();
  return (
    <header className="encabezado">
      <div className="encabezado__in">
        <Link href="/" className="marca">
          <span className="marca__icono">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M3 17l6-6 4 4 8-8" />
              <path d="M14 7h7v7" />
            </svg>
          </span>
          <span>
            <span className="marca__nombre" style={{ display: 'block' }}>Precios de la central</span>
            <span className="marca__sub">Pronóstico de precios mayoristas de alimentos</span>
          </span>
        </Link>
        <nav className="nav" aria-label="Principal">
          {ENLACES.map((e) => (
            <Link key={e.href} href={e.href} aria-current={ruta === e.href ? 'page' : undefined}>
              {e.texto}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
