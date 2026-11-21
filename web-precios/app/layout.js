import './globals.css';
import Encabezado from '../components/Encabezado';

export const metadata = {
  title: 'Precios de la central · Pronóstico de precios mayoristas',
  description: 'Consulte el precio esperado del próximo mes y el riesgo de alza de los alimentos en las centrales de abasto de Colombia, con datos del DANE (SIPSA).',
};

export const viewport = { width: 'device-width', initialScale: 1, themeColor: '#1f6f54' };

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Inter+Tight:wght@600;700&display=swap"
        />
      </head>
      <body>
        <Encabezado />
        {children}
      </body>
    </html>
  );
}
