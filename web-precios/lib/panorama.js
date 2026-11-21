// Dibujo de las páginas Panorama, Mi ciudad y Mi canasta (SVG y tablas hechos a mano, sin librerías).
// Cada página llama a su función montar…() cuando ya cargó los datos de public/data.
import GEO from './geo.json';
import { LEY_CAMBIO } from './panorama-html';


const COORD = {
  'Medellín':[6.2442,-75.5812],'Cali':[3.4516,-76.532],'Bogotá':[4.711,-74.0721],'Barranquilla':[10.9685,-74.7813],
  'Bucaramanga':[7.1193,-73.1227],'Cúcuta':[7.8939,-72.5078],'Villavicencio':[4.142,-73.6266],'Pereira':[4.8133,-75.6961],
  'Neiva':[2.9273,-75.2819],'Manizales':[5.0703,-75.5138],'Tunja':[5.5353,-73.3678],'Armenia':[4.5339,-75.6811],
  'Ibagué':[4.4389,-75.2322],'Sincelejo':[9.3047,-75.3978],'Montería':[8.7479,-75.8814],'Cartagena':[10.391,-75.4794],
  'Popayán':[2.4448,-76.6147],'Pasto':[1.2136,-77.2811],'Valledupar':[10.4631,-73.2532],'Santa Marta':[11.2408,-74.199],'Ipiales':[0.8303,-77.644]
};
// dirección de la etiqueta: [dx, dy, anchor]
const ETQ = {'Barranquilla':[-12,-8,'end'],'Santa Marta':[10,-8,'start'],'Cartagena':[-12,4,'end'],'Valledupar':[12,4,'start'],
  'Sincelejo':[-10,4,'end'],'Montería':[-12,4,'end'],'Cúcuta':[12,4,'start'],'Bucaramanga':[13,4,'start'],'Medellín':[-16,4,'end'],
  'Tunja':[11,4,'start'],'Bogotá':[15,4,'start'],'Villavicencio':[12,10,'start'],'Manizales':[-12,-6,'end'],'Pereira':[-14,0,'end'],
  'Armenia':[-13,8,'end'],'Ibagué':[12,6,'start'],'Neiva':[11,5,'start'],'Cali':[-14,4,'end'],'Popayán':[-11,5,'end'],
  'Pasto':[-11,2,'end'],'Ipiales':[9,10,'start']};
const GRUPOS = [['', 'Todos'], ['FRUTAS', 'Frutas'], ['VERDURAS Y HORTALIZAS', 'Verduras'], ['TUBERCULOS, RAICES Y PLATANOS', 'Tubérculos y plátano'], ['PROCESADOS', 'Procesados'], ['GRANOS Y CEREALES', 'Granos'], ['LACTEOS Y HUEVOS', 'Lácteos y huevos']];
const MESES = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
const MC = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
const $ = (s) => document.querySelector(s);
const NS = 'http://www.w3.org/2000/svg';
const el = (t, a = {}, txt) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (txt != null) e.textContent = txt; return e; };
const fmt = new Intl.NumberFormat('es-CO');
const pesos = (v) => '$' + fmt.format(Math.round(v));
const pct = (v, d = 1) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toLocaleString('es-CO', { maximumFractionDigits: d, minimumFractionDigits: d }) + ' %';
const mediana = (a) => { const s = [...a].sort((x, y) => x - y); const n = s.length; return n ? (n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2) : NaN; };
const nomMes = (m) => MESES[+m.slice(5, 7) - 1];
const centralCorta = (c) => { const i = c.indexOf(','); return i < 0 ? c : c.slice(i + 1).replace(/^ *D\.C\., */, '').replace(/"/g, '').trim(); };
const proj = ([la, lo]) => [(lo - GEO.lon0) * GEO.k * GEO.sx, (GEO.lat1 - la) * GEO.sx];
const claseCambio = (v) => v <= -8 ? 'd1' : v <= -2 ? 'd2' : v < 2 ? 'd3' : v < 8 ? 'd4' : 'd5';
const claseRiesgo = (p) => p < 5 ? 's1' : p < 10 ? 's2' : p < 15 ? 's3' : 's4';
const colRiesgo = { alto: 'var(--alto)', medio: 'var(--medio)', bajo: 'var(--bajo)' };
const txtRiesgo = { alto: 'Alto', medio: 'Medio', bajo: 'Bajo' };
const uni = (s) => (s && s.unidad) || 'kg';                     // unidad del precio de cada serie (hoy todas en kilos)
const pu = (v, s) => `${pesos(v)}/${uni(s)}`;                    // "$3.212/kg"
const MP = () => nomMes(D.mes_pronostico), MU = () => nomMes(D.ultimo_mes);
const corto = (m) => m.slice(0, 3) + '.';
function rellenarMeses() {
  document.querySelectorAll('.pz .mes-p').forEach((e) => { e.textContent = MP(); });
  document.querySelectorAll('.pz .mes-u').forEach((e) => { e.textContent = MU(); });
  const us = [...new Set(D.series.map(uni))]; document.querySelectorAll('.pz .uni').forEach((e) => { e.textContent = us.map((u) => '$/' + u).join(', '); });
}

function mostrarTip(ev, html) {
  const tip = $('#tip'); if (!tip) return;
  tip.innerHTML = html; tip.hidden = false;
  const r = tip.getBoundingClientRect(); let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - 14;
  if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - 14;
  tip.style.left = Math.max(8, x) + 'px'; tip.style.top = Math.max(8, y) + 'px';
}
const ocultarTip = () => { const tip = $('#tip'); if (tip) tip.hidden = true; };

let D, estado = { grupo: '', modo: 'riesgo', ciudad: 'Medellín', producto: 'Limón Tahití' };
const serie = () => D.series.filter((s) => !estado.grupo || s.grupo === estado.grupo);

/* separa círculos que se superponen sin alejarlos mucho de su lugar */
function relajar(nodos, it = 120) {
  for (let k = 0; k < it; k++) {
    for (let i = 0; i < nodos.length; i++) for (let j = i + 1; j < nodos.length; j++) {
      const a = nodos[i], b = nodos[j]; let dx = b.x - a.x, dy = b.y - a.y; let d = Math.hypot(dx, dy) || 0.01;
      const min = a.r + b.r + 1.5; if (d < min) { const m = (min - d) / 2; dx /= d; dy /= d; a.x -= dx * m; a.y -= dy * m; b.x += dx * m; b.y += dy * m; }
    }
    for (const n of nodos) { n.x += (n.x0 - n.x) * 0.04; n.y += (n.y0 - n.y) * 0.04; }
  }
}

function dibujarBase(svg, etiquetasPais = true) {
  svg.setAttribute('viewBox', `20 0 ${GEO.W - 20} ${GEO.H - 30}`);
  svg.replaceChildren(el('rect', { x: 0, y: 0, width: GEO.W, height: GEO.H, style: 'fill:var(--mar)', rx: 12 }));
  for (const p of ['ven', 'ecu', 'pan', 'per', 'bra']) svg.append(el('path', { d: GEO.paths[p], class: 'vec' }));
  svg.append(el('path', { d: GEO.paths.col, class: 'col' }));
  if (etiquetasPais) {
    [['VENEZUELA', 345, 150], ['ECUADOR', 40, 505], ['PERÚ', 175, 528], ['BRASIL', 365, 445]].forEach(([t, x, y]) => svg.append(el('text', { x, y, class: 'pais' }, t)));
    svg.append(el('text', { x: 120, y: 40, class: 'mar' }, 'Mar Caribe'));
    svg.append(el('text', { x: 28, y: 440, class: 'mar' }, 'Océano'));
    svg.append(el('text', { x: 28, y: 453, class: 'mar' }, 'Pacífico'));
  }
}

function filtros() {
  const cont = $('#filtros'); cont.querySelectorAll('.chip').forEach((c) => c.remove());
  GRUPOS.forEach(([v, t]) => {
    const b = document.createElement('button'); b.type = 'button'; b.className = 'chip'; b.textContent = t; b.dataset.g = v;
    b.setAttribute('aria-pressed', v === estado.grupo); b.onclick = () => { estado.grupo = v; cont.querySelectorAll('.chip').forEach((c) => c.setAttribute('aria-pressed', c.dataset.g === v)); todo(); };
    cont.append(b);
  });
}

function kpis() {
  const s = serie(), n = s.length, a = s.filter((x) => x.riesgo === 'alto').length, m = s.filter((x) => x.riesgo === 'medio').length;
  const sube = s.filter((x) => x.cambio_pct >= 2).length, baja = s.filter((x) => x.cambio_pct <= -2).length, igual = n - sube - baja;
  const w = (k) => (100 * k / n).toFixed(1) + '%';
  $('#kpis').innerHTML = `
    <div class="kpi"><b class="num">${fmt.format(n)}</b><span>alimentos en ${new Set(s.map((x) => x.central)).size} centrales</span></div>
    <div class="kpi kpi--alto"><b class="num">${a}</b><span>con riesgo alto de alza fuerte (probabilidad de 60 % o más de subir más del 15 %)</span></div>
    <div class="kpi kpi--medio"><b class="num">${m}</b><span>con riesgo medio (probabilidad entre 30 % y 60 %)</span></div>
    <div class="kpi"><b class="num">${Math.round(100 * baja / n)} % <small style="font-size:15px;color:var(--texto-4);font-weight:600">bajarían</small></b>
      <span>más del 2 %; ${Math.round(100 * sube / n)} % subirían más del 2 % y ${Math.round(100 * igual / n)} % quedarían estables (entre −2 % y +2 %)</span>
      <div class="barrita" aria-hidden="true"><i style="width:${w(baja)};background:var(--d1)"></i><i style="width:${w(igual)};background:var(--d3)"></i><i style="width:${w(sube)};background:var(--d5)"></i></div></div>`;
}

function porCiudad() {
  const g = {}; for (const s of serie()) (g[s.ciudad] ||= []).push(s);
  return Object.entries(g).map(([c, v]) => ({ ciudad: c, v, n: v.length, riesgo: 100 * v.filter((x) => x.riesgo !== 'bajo').length / v.length, cambio: mediana(v.map((x) => x.cambio_pct)) }));
}

function mapa() {
  const svg = $('#mapa'); dibujarBase(svg);
  const datos = porCiudad();
  const nodos = datos.map((d) => { const [x, y] = proj(COORD[d.ciudad]); return { ...d, x, y, x0: x, y0: y, r: 3.5 + Math.sqrt(d.n) * 0.95 }; });
  relajar(nodos);
  nodos.sort((a, b) => b.r - a.r);
  for (const n of nodos) {
    const fill = estado.modo === 'riesgo' ? `var(--${claseRiesgo(n.riesgo)})` : `var(--${claseCambio(n.cambio)})`;
    const c = el('circle', { cx: n.x, cy: n.y, r: n.r, class: 'nodo' + (n.ciudad === estado.ciudad ? ' sel' : ''), style: `fill:${fill}`, tabindex: 0, role: 'button', 'aria-label': `${n.ciudad}: ${n.n} alimentos` });
    c.onmousemove = (ev) => mostrarTip(ev, `<b>${n.ciudad}</b>${n.n} alimentos<br>${n.riesgo.toFixed(0)} % de sus alimentos en riesgo medio o alto<br>Cambio típico esperado: ${pct(n.cambio)}`);
    c.onmouseleave = ocultarTip;
    c.onclick = c.onkeydown = (ev) => { if (ev.type === 'keydown' && ev.key !== 'Enter') return; estado.ciudad = n.ciudad; mapa(); panel(); };
    svg.append(c);
  }
  for (const n of nodos) { const [dx, dy, an] = ETQ[n.ciudad] || [10, 4, 'start']; svg.append(el('text', { x: n.x + dx, y: n.y + dy, 'text-anchor': an }, n.ciudad)); }
  const ley = $('#leyenda-mapa');
  ley.innerHTML = estado.modo === 'riesgo'
    ? '<span style="width:100%">Parte de los alimentos de la ciudad con riesgo medio o alto (probabilidad de alza fuerte de 30 % o más)</span><span><i style="background:var(--s1)"></i>menos de 5 %</span><span><i style="background:var(--s2)"></i>5 a 10 %</span><span><i style="background:var(--s3)"></i>10 a 15 %</span><span><i style="background:var(--s4)"></i>15 % o más</span>'
    : `<span style="width:100%">Cambio típico esperado en la ciudad, de ${MU()} a ${MP()}</span>${LEY_CAMBIO}`;
}

function panel() {
  const datos = porCiudad(); let d = datos.find((x) => x.ciudad === estado.ciudad);
  if (!d) { d = datos.sort((a, b) => b.n - a.n)[0]; estado.ciudad = d.ciudad; }
  const top = [...d.v].sort((a, b) => b.prob_alza - a.prob_alza).slice(0, 7);
  const opciones = [...datos].sort((a, b) => a.ciudad.localeCompare(b.ciudad)).map((x) => `<option ${x.ciudad === d.ciudad ? 'selected' : ''}>${x.ciudad}</option>`).join('');
  $('#panel').innerHTML = `
    <div class="panel__cab"><h3>${d.ciudad}</h3><select id="sel-ciudad" aria-label="Elegir ciudad">${opciones}</select></div>
    <div class="cifras">
      <div><b class="num">${d.n}</b><span>alimentos</span></div>
      <div><b class="num">${d.v.filter((x) => x.riesgo === 'alto').length} / ${d.v.filter((x) => x.riesgo === 'medio').length}</b><span>riesgo alto / medio</span></div>
      <div><b class="num ${d.cambio > 0 ? 'sube' : d.cambio < 0 ? 'baja' : ''}">${pct(d.cambio)}</b><span>cambio típico esperado</span></div>
    </div>
    <span class="nota">Alimentos con mayor probabilidad de alza fuerte en ${MP()} (precio de ${MU()} → esperado)</span>
    <ul class="lista">${top.map((s) => `<li data-p="${s.producto}" title="Ver ${s.producto} en todo el país">
      <div style="min-width:0"><div class="p">${s.producto}</div><div class="c">${centralCorta(s.central)} · ${pu(s.precio_actual, s)} → ${pu(s.precio_esperado, s)}</div></div>
      <span class="num ${s.cambio_pct > 0 ? 'sube' : 'baja'}" style="text-align:right;font-weight:600">${pct(s.cambio_pct)}</span>
      <span class="pill pill--${s.riesgo}">${Math.round(100 * s.prob_alza)} %</span></li>`).join('')}</ul>
    <p class="nota">Primera cifra: cambio esperado del precio. Cifra de color: probabilidad de que el precio suba más del 15 %.</p>`;
  $('#sel-ciudad').onchange = (e) => { estado.ciudad = e.target.value; mapa(); panel(); };
  $('#panel').querySelectorAll('li').forEach((li) => li.onclick = () => irProducto(li.dataset.p));
}

function calor() {
  const ciudades = Object.entries(D.series.reduce((a, s) => (a[s.ciudad] = (a[s.ciudad] || 0) + 1, a), {})).sort((a, b) => b[1] - a[1]).map(([c]) => c);
  const filas = GRUPOS.slice(1);
  let h = '<thead><tr><th></th>' + ciudades.map((c) => `<th scope="col">${c}</th>`).join('') + '</tr></thead><tbody>';
  for (const [g, t] of filas) {
    h += `<tr><th scope="row">${t}</th>`;
    for (const c of ciudades) {
      const v = D.series.filter((s) => s.grupo === g && s.ciudad === c);
      if (v.length < 2) { h += '<td class="vacio">·</td>'; continue; }
      const m = mediana(v.map((s) => s.cambio_pct));
      h += `<td class="${claseCambio(m)}" data-t="${t}" data-c="${c}" data-n="${v.length}" data-m="${m}">${Math.round(m) === 0 ? '0' : (m > 0 ? '+' : '−') + Math.abs(Math.round(m))}</td>`;
    }
    h += '</tr>';
  }
  $('#calor').innerHTML = h + '</tbody>';
  $('#calor').querySelectorAll('td[data-m]').forEach((td) => {
    td.onmousemove = (ev) => mostrarTip(ev, `<b>${td.dataset.t} en ${td.dataset.c}</b>Cambio típico esperado: ${pct(+td.dataset.m)}<br>Mediana de ${td.dataset.n} alimentos`);
    td.onmouseleave = ocultarTip;
  });
}

function dispersion() {
  const svg = $('#disp'); svg.replaceChildren();
  const W = 1000, H = 420, m = { l: 56, r: 20, t: 14, b: 44 };
  const x = (v) => m.l + (v + 35) / 70 * (W - m.l - m.r), y = (v) => H - m.b - v * (H - m.t - m.b);
  for (const t of [-30, -20, -10, 0, 10, 20, 30]) { svg.append(el('line', { x1: x(t), x2: x(t), y1: m.t, y2: H - m.b, class: t ? 'rej' : 'eje' })); svg.append(el('text', { x: x(t), y: H - m.b + 18, 'text-anchor': 'middle' }, (t > 0 ? '+' : t < 0 ? '−' : '') + Math.abs(t) + ' %')); }
  for (const t of [0, .2, .4, .6, .8, 1]) { svg.append(el('line', { x1: m.l, x2: W - m.r, y1: y(t), y2: y(t), class: 'rej' })); svg.append(el('text', { x: m.l - 8, y: y(t) + 4, 'text-anchor': 'end' }, Math.round(t * 100) + ' %')); }
  svg.append(el('line', { x1: m.l, x2: W - m.r, y1: y(.6), y2: y(.6), class: 'umbral', style: 'stroke:var(--alto)' }));
  svg.append(el('line', { x1: m.l, x2: W - m.r, y1: y(.3), y2: y(.3), class: 'umbral', style: 'stroke:var(--medio)' }));
  svg.append(el('text', { x: W - m.r - 4, y: y(.6) - 6, 'text-anchor': 'end', style: 'fill:var(--alto-texto);font-weight:600' }, 'riesgo alto'));
  svg.append(el('text', { x: W - m.r - 4, y: y(.3) - 6, 'text-anchor': 'end', style: 'fill:var(--medio-texto);font-weight:600' }, 'riesgo medio'));
  svg.append(el('text', { x: (m.l + W - m.r) / 2, y: H - 6, 'text-anchor': 'middle' }, `Cambio esperado del precio, de ${MU()} a ${MP()}`));
  svg.append(el('text', { x: 14, y: (H - m.b + m.t) / 2, transform: `rotate(-90 14 ${(H - m.b + m.t) / 2})`, 'text-anchor': 'middle' }, 'Probabilidad de alza fuerte'));
  const s = [...serie()].sort((a, b) => (a.riesgo === 'bajo' ? 0 : 1) - (b.riesgo === 'bajo' ? 0 : 1));
  for (const d of s) {
    const c = el('circle', { cx: x(Math.max(-35, Math.min(35, d.cambio_pct))), cy: y(d.prob_alza), r: d.riesgo === 'bajo' ? 3.2 : 4.6, class: 'pz-punto', style: `fill:${colRiesgo[d.riesgo]};fill-opacity:${d.riesgo === 'bajo' ? .45 : .9}` });
    c.onmousemove = (ev) => mostrarTip(ev, `<b>${d.producto}</b>${d.ciudad}, ${centralCorta(d.central)}<br>${pu(d.precio_actual, d)} → ${pu(d.precio_esperado, d)} (${pct(d.cambio_pct)})<br>Probabilidad de alza fuerte: ${Math.round(100 * d.prob_alza)} %`);
    c.onmouseleave = ocultarTip; c.onclick = () => irProducto(d.producto);
    svg.append(c);
  }
}

function productos() {
  const sel = $('#sel-prod'); const ps = [...new Set(D.series.map((s) => s.producto))].sort((a, b) => a.localeCompare(b, 'es'));
  sel.innerHTML = ps.map((p) => `<option ${p === estado.producto ? 'selected' : ''}>${p}</option>`).join('');
  sel.onchange = () => { estado.producto = sel.value; producto(); };
}
function irProducto(p) { estado.producto = p; $('#sel-prod').value = p; producto(); $('#sec-prod').scrollIntoView({ behavior: 'smooth', block: 'start' }); }

function producto() {
  const v = D.series.filter((s) => s.producto === estado.producto);
  const svg = $('#lineas'); svg.replaceChildren();
  const W = 640, H = 330, m = { l: 62, r: 16, t: 12, b: 34 };
  const meses = [...v[0].historia.map((h) => h[0]), D.mes_pronostico];
  const todos = v.flatMap((s) => [...s.historia.map((h) => h[1]), s.precio_esperado]);
  let lo = Math.min(...todos), hi = Math.max(...todos); const pad = (hi - lo) * 0.08; lo = Math.max(0, lo - pad); hi += pad;
  const paso = Math.pow(10, Math.floor(Math.log10((hi - lo) / 4))); const st = [1, 2, 2.5, 5, 10].map((k) => k * paso).find((k) => (hi - lo) / k <= 5);
  const x = (i) => m.l + i / (meses.length - 1) * (W - m.l - m.r), y = (p) => H - m.b - (p - lo) / (hi - lo) * (H - m.t - m.b);
  for (let t = Math.ceil(lo / st) * st; t <= hi; t += st) { svg.append(el('line', { x1: m.l, x2: W - m.r, y1: y(t), y2: y(t), class: 'rej' })); svg.append(el('text', { x: m.l - 8, y: y(t) + 4, 'text-anchor': 'end' }, pesos(t))); }
  svg.append(el('text', { x: m.l - 8, y: m.t - 2, 'text-anchor': 'end', style: 'font-weight:600' }, `$/${uni(v[0])}`));
  meses.forEach((mm, i) => { if (i % 2 === 0 || i === meses.length - 1) svg.append(el('text', { x: x(i), y: H - m.b + 18, 'text-anchor': 'middle', style: i === meses.length - 1 ? 'font-weight:700;fill:var(--acento)' : '' }, MC[+mm.slice(5, 7) - 1] + (mm.endsWith('-01') || i === 0 ? ' ' + mm.slice(2, 4) : ''))); });
  svg.append(el('rect', { x: x(meses.length - 2), y: m.t, width: x(meses.length - 1) - x(meses.length - 2) + 8, height: H - m.t - m.b, style: 'fill:var(--acento-suave)', rx: 6 }));
  svg.append(el('text', { x: x(meses.length - 1) - 4, y: m.t + 14, 'text-anchor': 'end', style: 'fill:var(--acento);font-weight:600' }, 'pronóstico'));
  const grupos = [];
  for (const s of v) {
    const pts = s.historia.map((h, i) => [x(i), y(h[1])]);
    const g = el('g');
    g.append(el('path', { d: 'M' + pts.map((p) => p.join(' ')).join('L'), class: 'linea-h' }));
    const ult = pts[pts.length - 1];
    g.append(el('path', { d: `M${ult[0]} ${ult[1]}L${x(meses.length - 1)} ${y(s.precio_esperado)}`, class: 'linea-h', 'stroke-dasharray': '4 3' }));
    const fin = el('circle', { cx: x(meses.length - 1), cy: y(s.precio_esperado), r: 3.5, style: 'fill:var(--linea)' });
    g.append(fin); g.s = s; g.fin = fin; svg.append(g); grupos.push(g);
  }
  const lbl = el('text', { x: m.l + 6, y: m.t + 14, style: 'fill:var(--texto);font-weight:700;font-size:13px' }); svg.append(lbl);
  const resaltar = (central) => {
    grupos.forEach((g) => { const on = g.s.central === central; g.querySelectorAll('path').forEach((p) => p.classList.toggle('on', on)); g.fin.style.fill = on ? 'var(--acento)' : 'var(--linea)'; g.fin.setAttribute('r', on ? 5 : 3.5); if (on) svg.append(g); });
    svg.append(lbl);
    const s = v.find((q) => q.central === central); lbl.textContent = s ? `${s.ciudad} · ${centralCorta(s.central)}: ${pu(s.precio_actual, s)} en ${corto(MU())} → ${pu(s.precio_esperado, s)} en ${corto(MP())}` : '';
    $('#ranking').querySelectorAll('li').forEach((li) => li.classList.toggle('on', li.dataset.c === central));
    if (s) calendario(central, estado.producto);
  };
  grupos.forEach((g) => { g.style.cursor = 'pointer'; g.onmouseenter = () => resaltar(g.s.central); g.onclick = () => resaltar(g.s.central); });
  const orden = [...v].sort((a, b) => a.precio_esperado - b.precio_esperado); const max = orden[orden.length - 1].precio_esperado;
  $('#ranking').innerHTML = orden.map((s) => `<li data-c="${s.central.replace(/"/g, '&quot;')}"><span class="nom" title="${s.central.replace(/"/g, '&quot;')}">${s.ciudad}${v.filter((q) => q.ciudad === s.ciudad).length > 1 ? ' · ' + centralCorta(s.central) : ''}</span><span class="pista"><i style="width:${(100 * s.precio_esperado / max).toFixed(1)}%"></i></span><span class="v">${pesos(s.precio_esperado)}</span></li>`).join('');
  $('#ranking').querySelectorAll('li').forEach((li) => { li.onmouseenter = li.onclick = () => resaltar(li.dataset.c); });
  const barato = orden[0], caro = orden[orden.length - 1];
  $('#nota-lineas').textContent = `Precio mayorista mensual en pesos por ${uni(v[0]) === 'kg' ? 'kilo' : uni(v[0])}, en ${v.length} centrales. En ${MP()}, ${barato.ciudad} sería la más barata (${pu(barato.precio_esperado, barato)}) y ${caro.ciudad} la más cara (${pu(caro.precio_esperado, caro)}). Pase el cursor por una línea o por la lista.`;
  resaltar(orden[0].central);
}

/* ================= datos adicionales ================= */
let X, O;
const DEP = {'Amazonas':[-1.4,-71.6],'Antioquia':[7.0,-75.4],'Arauca':[6.6,-71.0],'Atlántico':[10.7,-74.95],'Bogotá D.C.':[4.62,-74.12],
  'Bolívar':[8.9,-74.4],'Boyacá':[5.8,-73.0],'Caldas':[5.35,-75.25],'Caquetá':[1.0,-74.2],'Casanare':[5.3,-71.7],'Cauca':[2.4,-76.8],
  'Cesar':[9.6,-73.5],'Chocó':[5.8,-76.75],'Córdoba':[8.4,-75.8],'Cundinamarca':[5.05,-74.3],'Guainía':[2.6,-68.6],'Guaviare':[2.1,-72.6],
  'Huila':[2.5,-75.6],'La Guajira':[11.35,-72.6],'Magdalena':[10.2,-74.15],'Meta':[3.5,-73.0],'Nariño':[1.5,-77.8],'Norte de Santander':[8.1,-72.9],
  'Putumayo':[0.6,-76.0],'Quindío':[4.45,-75.75],'Risaralda':[5.1,-75.95],'Santander':[6.8,-73.4],'Sucre':[9.0,-75.2],'Tolima':[3.95,-75.15],
  'Valle del Cauca':[3.85,-76.4],'Vaupés':[0.6,-70.5],'Vichada':[4.7,-69.5]};
const LOCAL = {'Medellín':['Antioquia'],'Cali':['Valle del Cauca'],'Bogotá':['Bogotá D.C.','Cundinamarca'],'Barranquilla':['Atlántico'],'Bucaramanga':['Santander'],
  'Cúcuta':['Norte de Santander'],'Villavicencio':['Meta'],'Pereira':['Risaralda'],'Neiva':['Huila'],'Manizales':['Caldas'],'Tunja':['Boyacá'],'Armenia':['Quindío'],
  'Ibagué':['Tolima'],'Sincelejo':['Sucre'],'Montería':['Córdoba'],'Cartagena':['Bolívar'],'Popayán':['Cauca'],'Pasto':['Nariño'],'Valledupar':['Cesar'],
  'Santa Marta':['Magdalena'],'Ipiales':['Nariño']};
const REGION = {'Barranquilla':1,'Cartagena':1,'Santa Marta':1,'Valledupar':1,'Sincelejo':1,'Montería':1,'Medellín':2,'Manizales':2,'Pereira':2,'Armenia':2,
  'Bogotá':3,'Tunja':3,'Villavicencio':3,'Bucaramanga':3,'Cúcuta':3,'Ibagué':3,'Neiva':3,'Cali':4,'Popayán':4,'Pasto':4,'Ipiales':4};
const NOMREG = {1:'Caribe',2:'Antioquia y Eje Cafetero',3:'Centro y oriente',4:'Suroccidente'};
const ciudadDe = (c) => D.series.find((s) => s.central === c)?.ciudad;
const CORTO = { 'Central Mayorista de Antioquia': 'Mayorista', 'Plaza Minorista José María Villa': 'Minorista' };
const nombreCentral = (c) => { const ci = ciudadDe(c); const n = new Set(D.series.filter((s) => s.ciudad === ci).map((s) => s.central)).size; const k = centralCorta(c); return n > 1 ? `${ci} · ${CORTO[k] || k}` : ci; };
const mesLargo = (m) => `${nomMes(m)} de ${m.slice(0, 4)}`;
const fmt1 = (v) => v.toLocaleString('es-CO', { maximumFractionDigits: 2, minimumFractionDigits: 2 });

/* ================= red ================= */
let RED = null;
function red() {
  const cents = [...new Set(D.series.map((s) => s.central))];
  const nSer = {}; for (const s of D.series) nSer[s.central] = (nSer[s.central] || 0) + 1;
  const W = 760, H = 520;
  const ANCLA = { 1: [400, 80], 2: [190, 250], 3: [560, 300], 4: [250, 450] };
  const nodos = cents.map((c, i) => { const ci = ciudadDe(c); const [gx, gy] = proj(COORD[ci]); const reg = REGION[ci]; return { c, ci, reg, x: ANCLA[reg][0] + (gx - 230) * 0.5 + (i % 3) * 6, y: ANCLA[reg][1] + (gy - 300) * 0.25 + (i % 2) * 6, vx: 0, vy: 0, r: 5 + Math.sqrt(nSer[c]) * 0.9 }; });
  const idx = Object.fromEntries(nodos.map((n, i) => [n.c, i]));
  const aristas = X.red.filter((r) => idx[r[0]] != null && idx[r[1]] != null).map((r) => ({ a: idx[r[0]], b: idx[r[1]], w: r[2], n: r[3], k: r[4] }));
  // disposición por fuerzas (determinista; parte de la posición geográfica)
  for (let it = 0; it < 500; it++) {
    const t = 1 - it / 500;
    for (let i = 0; i < nodos.length; i++) for (let j = i + 1; j < nodos.length; j++) {
      const A = nodos[i], B = nodos[j]; let dx = B.x - A.x, dy = B.y - A.y, d2 = dx * dx + dy * dy + 0.01, d = Math.sqrt(d2);
      const f = 3400 / d2; A.vx -= dx / d * f; A.vy -= dy / d * f; B.vx += dx / d * f; B.vy += dy / d * f;
    }
    for (const e of aristas) if (e.w >= 0.6) {
      const A = nodos[e.a], B = nodos[e.b]; const dx = B.x - A.x, dy = B.y - A.y, d = Math.hypot(dx, dy) || 0.1;
      const L = 50 + 260 * (1 - e.w); const f = (d - L) * 0.006 * e.w; A.vx += dx / d * f; A.vy += dy / d * f; B.vx -= dx / d * f; B.vy -= dy / d * f;
    }
    for (const n of nodos) { n.vx += (ANCLA[n.reg][0] - n.x) * 0.02; n.vy += (ANCLA[n.reg][1] - n.y) * 0.02; n.x += Math.max(-20, Math.min(20, n.vx)) * t; n.y += Math.max(-20, Math.min(20, n.vy)) * t; n.vx *= 0.5; n.vy *= 0.5; }
  }
  const xs = nodos.map((n) => n.x), ys = nodos.map((n) => n.y), mx = Math.min(...xs), Mx = Math.max(...xs), my = Math.min(...ys), My = Math.max(...ys);
  for (const n of nodos) { n.x = 175 + (n.x - mx) / (Mx - mx) * (W - 340); n.y = 28 + (n.y - my) / (My - my) * (H - 56); }
  relajar(nodos.map((n) => Object.assign(n, { x0: n.x, y0: n.y, r: n.r + 9 })), 200); nodos.forEach((n) => { n.r -= 9; });
  const svg = $('#red'); svg.replaceChildren();
  const gL = el('g'), gN = el('g'); svg.append(gL, gN);
  for (const e of aristas) { e.el = el('line', { x1: nodos[e.a].x, y1: nodos[e.a].y, x2: nodos[e.b].x, y2: nodos[e.b].y, 'stroke-width': 0.5 + Math.pow(Math.max(0, e.w - 0.4), 1.6) * 14 }); gL.append(e.el); }
  for (const n of nodos) {
    const g = el('g'); n.g = g;
    const c = el('circle', { cx: n.x, cy: n.y, r: n.r, style: `fill:var(--r${n.reg})`, tabindex: 0, role: 'button', 'aria-label': nombreCentral(n.c) });
    const lado = n.x > W / 2 ? 1 : -1;
    g.append(c, el('text', { x: n.x + lado * (n.r + 4), y: n.y + 4, 'text-anchor': lado > 0 ? 'start' : 'end' }, nombreCentral(n.c)));
    c.onclick = c.onkeydown = (ev) => { if (ev.type === 'keydown' && ev.key !== 'Enter') return; RED.sel = n.c; pintar(); };
    c.onmousemove = (ev) => mostrarTip(ev, `<b>${n.c}</b>${NOMREG[n.reg]} · ${nSer[n.c]} alimentos`); c.onmouseleave = ocultarTip;
    gN.append(g);
  }
  $('#ley-red').innerHTML = Object.entries(NOMREG).map(([k, t]) => `<span><i style="background:var(--r${k})"></i>${t}</span>`).join('') + '<span>Tamaño del círculo: número de alimentos de la central</span>';
  if (X.desde) $('#red-desde').textContent = X.desde.slice(0, 4);
  // resumen dentro y entre regiones
  const dentro = [], entre = [];
  for (const e of aristas) (nodos[e.a].reg === nodos[e.b].reg ? dentro : entre).push(e.w);
  const prom = (a) => a.reduce((x, y) => x + y, 0) / a.length;
  const pintar = () => {
    const u = +$('#umbral-red').value / 100; $('#umbral-txt').textContent = fmt1(u);
    const sel = RED.sel, vecinos = new Set([sel]);
    for (const e of aristas) {
      const vis = e.w >= u; const toca = sel && (nodos[e.a].c === sel || nodos[e.b].c === sel);
      e.el.style.display = vis ? '' : 'none';
      e.el.setAttribute('class', sel ? (toca ? 'on' : 'off') : '');
      if (vis && toca) { vecinos.add(nodos[e.a].c); vecinos.add(nodos[e.b].c); }
    }
    for (const n of nodos) { n.g.setAttribute('class', sel && !vecinos.has(n.c) ? 'off' : ''); n.g.querySelector('circle').setAttribute('stroke', n.c === sel ? 'var(--texto)' : ''); n.g.querySelector('circle').style.strokeWidth = n.c === sel ? 3 : ''; }
    if (!sel) {
      const pares = [...aristas].sort((a, b) => b.w - a.w).filter((e) => nodos[e.a].ci !== nodos[e.b].ci).slice(0, 7);
      $('#panel-red').innerHTML = `<div class="panel__cab"><h3>Las centrales más parecidas</h3></div>
        <p class="nota" style="margin:0">Pares de ciudades distintas cuyos precios se mueven más juntos (1 = siempre igual; 0 = sin relación).</p>
        <ul class="ranking">${pares.map((e) => `<li data-c="${nodos[e.a].c.replace(/"/g, '&quot;')}"><span class="nom">${nodos[e.a].ci} y ${nodos[e.b].ci}</span><span class="pista"><i style="width:${(100 * e.w).toFixed(0)}%;background:var(--r${nodos[e.a].reg})"></i></span><span class="v">${fmt1(e.w)}</span></li>`).join('')}</ul>
        <div class="aviso" style="font-size:13px">Las centrales de una misma región se parecen más: ${fmt1(prom(dentro))} en promedio dentro de la región, frente a ${fmt1(prom(entre))} entre regiones distintas. Por eso el modelo usa los precios de las demás centrales como pista.</div>`;
      $('#panel-red').querySelectorAll('li').forEach((li) => li.onclick = () => { RED.sel = li.dataset.c; pintar(); });
      return;
    }
    const lista = aristas.filter((e) => nodos[e.a].c === sel || nodos[e.b].c === sel).map((e) => ({ o: nodos[e.a].c === sel ? nodos[e.b].c : nodos[e.a].c, w: e.w, k: e.k })).sort((a, b) => b.w - a.w);
    const max = 1;
    $('#panel-red').innerHTML = `
      <div class="panel__cab"><h3>${nombreCentral(sel)}</h3><button type="button" class="btn" id="red-todas">Ver toda la red</button></div>
      <p class="nota" style="margin:0">Qué tan juntos se mueven sus precios con los de otras centrales (1 = siempre igual; 0 = sin relación).</p>
      <ul class="ranking">${lista.slice(0, 8).map((x) => `<li data-c="${x.o.replace(/"/g, '&quot;')}"><span class="nom">${nombreCentral(x.o)}</span><span class="pista"><i style="width:${Math.max(0, 100 * x.w / max).toFixed(0)}%;background:var(--r${REGION[ciudadDe(x.o)]})"></i></span><span class="v">${fmt1(x.w)}</span></li>`).join('')}</ul>
      <div class="aviso" style="font-size:13px">Las centrales de una misma región se parecen más: ${fmt1(prom(dentro))} en promedio dentro de la región, frente a ${fmt1(prom(entre))} entre regiones distintas. Por eso el modelo usa los precios de las demás centrales como pista.</div>`;
    $('#panel-red').querySelectorAll('li').forEach((li) => li.onclick = () => { RED.sel = li.dataset.c; pintar(); });
    $('#red-todas').onclick = () => { RED.sel = null; pintar(); };
  };
  $('#umbral-red').oninput = pintar;
  RED = { sel: null, pintar }; pintar();
}

/* ================= calendario ================= */
function calendario(central, producto) {
  const k = `${central}|${producto}`; const c = X.calendario[k]; const mesP = +D.mes_pronostico.slice(5, 7);
  $('#t-cal').textContent = `Calendario de ${producto} en ${nombreCentral(central)}`;
  if (!c) { $('#cal').innerHTML = ''; $('#nota-cal').textContent = 'Sin historia suficiente.'; return; }
  const [med, fa, n] = c;
  if (X.desde) $('#cal-anios').textContent = `${X.desde.slice(0, 4)} a ${X.hasta.slice(0, 4)}`;
  $('#cal').innerHTML = med.map((v, i) => `<div class="${v == null ? '' : claseCambio(v)} ${i + 1 === mesP ? 'hoy' : ''}" title="${MESES[i]}: cambio típico frente al mes anterior ${v == null ? 'sin dato' : pct(v)}; alza fuerte en ${fa[i] == null ? 0 : Math.round(fa[i] * n[i])} de ${n[i]} años">
     <b>${MC[i]}</b><span>${v == null ? '·' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(Math.round(v))}</span><i><em style="width:${Math.round(100 * (fa[i] || 0))}%"></em></i></div>`).join('');
  const ok = med.map((v, i) => [v, i]).filter((p) => p[0] != null);
  const sube = ok.reduce((a, b) => (b[0] > a[0] ? b : a)), baja = ok.reduce((a, b) => (b[0] < a[0] ? b : a));
  const i = mesP - 1;
  $('#nota-cal').textContent = `Frente al mes anterior, suele subir más en ${MESES[sube[1]]} (${pct(sube[0])}) y bajar más en ${MESES[baja[1]]} (${pct(baja[0])}). En ${MESES[i]} tuvo alza fuerte en ${Math.round((fa[i] || 0) * n[i])} de ${n[i]} años.`;
}

/* ================= mi ciudad ================= */
let CIU = { ciudad: 'Bogotá', origen: null };
function miCiudad() {
  const sel = $('#sel-ciudad2');
  if (!sel.options.length) { sel.innerHTML = Object.keys(O.ciudad).sort((a, b) => a.localeCompare(b, 'es')).map((c) => `<option>${c}</option>`).join(''); sel.onchange = () => { CIU = { ciudad: sel.value, origen: null }; miCiudad(); }; $('#limpiar-origen').onclick = () => { CIU.origen = null; miCiudad(); }; }
  sel.value = CIU.ciudad;
  const c = CIU.ciudad, info = O.ciudad[c];
  const [p0, p1] = O.periodo || []; if (p0) $('#cinta-ciudad').textContent = `Mi ciudad · abastecimiento de ${nomMes(p0)} de ${p0.slice(0, 4)} a ${nomMes(p1)} de ${p1.slice(0, 4)}`;
  const ser = D.series.filter((s) => s.ciudad === c).map((s) => ({ ...s, org: O.serie[`${s.central}|${s.producto}`] }));
  const local = info.origenes.filter(([o]) => (LOCAL[c] || []).includes(o)).reduce((a, [, v]) => a + v, 0);
  const imp = info.origenes.find(([o]) => o === 'Importado')?.[1] || 0;
  const nDep = info.origenes.filter(([o]) => o !== 'Importado').length;
  const depend = ser.filter((s) => s.org && s.org.o[0][1] >= 0.7).length;
  const top = info.origenes.filter(([o]) => !(LOCAL[c] || []).includes(o) && o !== 'Importado')[0];
  $('#kpis-ciudad').innerHTML = `
    <div class="kpi"><b class="num">${fmt.format(info.ton)}</b><span>toneladas de estos alimentos llegaron a sus centrales en 12 meses</span></div>
    <div class="kpi"><b class="num">${Math.round(100 * local)} %</b><span>de esas toneladas viene de ${(LOCAL[c] || []).join(' y ')}</span></div>
    <div class="kpi"><b class="num">${nDep}</b><span>departamentos aportan carga${imp ? `; además, ${Math.round(100 * imp)} % es importado` : ''}</span></div>
    <div class="kpi kpi--medio"><b class="num">${depend}</b><span>de ${ser.length} alimentos reciben 70 % o más de un solo departamento</span></div>`;
  // mapa de flujos
  const svg = $('#mapa-flujo'); dibujarBase(svg);
  const [cx, cy] = proj(COORD[c]);
  const og = info.origenes.filter(([o, v]) => DEP[o] && v >= 0.004).sort((a, b) => a[1] - b[1]);
  const gF = el('g'), gD = el('g'), gT = el('g'); svg.append(gF, gD, gT);
  for (const [o, v] of og) {
    const [x, y] = proj(DEP[o]); const d = Math.hypot(cx - x, cy - y);
    const on = CIU.origen ? (CIU.origen === o ? ' on' : ' off') : '';
    if (d > 10) { const mx = (x + cx) / 2 - (cy - y) * 0.22, my = (y + cy) / 2 + (cx - x) * 0.22; gF.append(el('path', { d: `M${x} ${y}Q${mx} ${my} ${cx} ${cy}`, class: 'pz-flujo' + on, 'stroke-width': 1.2 + v * 30 })); }
    const dc = el('circle', { cx: x, cy: y, r: 3 + Math.sqrt(v) * 22, class: 'dep', style: CIU.origen && CIU.origen !== o ? 'opacity:.25' : '' });
    dc.onmousemove = (ev) => mostrarTip(ev, `<b>${o}</b>${pct(100 * v, 1).replace('+', '')} de las toneladas que llegan a ${c}`); dc.onmouseleave = ocultarTip;
    dc.onclick = () => { CIU.origen = CIU.origen === o ? null : o; miCiudad(); };
    gD.append(dc);
  }
  for (const [o, v] of og.slice(-6)) { const [x, y] = proj(DEP[o]); gT.append(el('text', { x: x, y: y - 6 - Math.sqrt(v) * 22, 'text-anchor': 'middle' }, o)); }
  gT.append(el('circle', { cx, cy, r: 7, class: 'destino' }));
  gT.append(el('text', { x: cx + 11, y: cy + 4, style: 'font-size:13px;font-weight:700' }, c));
  // lista de orígenes
  const maxV = info.origenes[0][1];
  $('#origenes').innerHTML = info.origenes.slice(0, 10).map(([o, v]) => `<li data-o="${o}" class="${CIU.origen === o ? 'on' : ''}"><span class="nom">${o}</span><span class="pista"><i style="width:${(100 * v / maxV).toFixed(0)}%;${o === 'Importado' ? 'background:var(--texto-4)' : ''}"></i></span><span class="v">${Math.round(100 * v) || '<1'} %</span></li>`).join('');
  $('#origenes').querySelectorAll('li').forEach((li) => li.onclick = () => { CIU.origen = CIU.origen === li.dataset.o ? null : li.dataset.o; miCiudad(); });
  $('#nota-import').textContent = info.importado.length ? `Lo importado llega sobre todo de ${info.importado.slice(0, 3).map((p) => p[0].replace('Estados Unidos De América', 'Estados Unidos')).join(', ')}.` : '';
  // tabla
  const filas = ser.filter((s) => !CIU.origen || (s.org && s.org.o[0][0] === CIU.origen)).sort((a, b) => b.prob_alza - a.prob_alza);
  const variasCentrales = new Set(ser.map((s) => s.central)).size > 1;
  $('#limpiar-origen').hidden = !CIU.origen;
  $('#sub-tabla-ciudad').textContent = CIU.origen ? `${filas.length} alimentos que ${CIU.origen === 'Importado' ? 'son principalmente importados' : 'llegan principalmente de ' + CIU.origen}, ordenados por probabilidad de alza fuerte.` : `${filas.length} alimentos, ordenados por probabilidad de alza fuerte.`;
  $('#tabla-ciudad').innerHTML = `<thead><tr><th>Alimento</th><th>Llega de</th><th class="n">${MU()[0].toUpperCase() + MU().slice(1)} ($/kg)</th><th class="n">${MP()[0].toUpperCase() + MP().slice(1)} esperado ($/kg)</th><th class="n">Cambio esperado</th><th>Riesgo · prob. de alza fuerte</th></tr></thead><tbody>${filas.slice(0, 40).map((s) => `<tr>
      <td><b>${s.producto}</b>${variasCentrales ? `<div class="nota">${centralCorta(s.central)}</div>` : ''}</td>
      <td><div class="chips-o">${s.org ? s.org.o.filter(([, v]) => v >= 0.01).slice(0, 2).map(([o, v]) => `<span class="chip-o">${o} ${Math.round(100 * v)} %</span>`).join('') : ''}</div></td>
      <td class="n">${pesos(s.precio_actual)}</td><td class="n"><b>${pesos(s.precio_esperado)}</b></td>
      <td class="n ${s.cambio_pct > 0 ? 'sube' : 'baja'}">${pct(s.cambio_pct)}</td>
      <td><span class="pill pill--${s.riesgo}">${txtRiesgo[s.riesgo]} · ${Math.round(100 * s.prob_alza)} %</span></td></tr>`).join('')}</tbody>`;
}

/* ================= mi canasta ================= */
const EJEMPLO = [['Papa parda pastusa', 20], ['Arroz', 10], ['Plátano hartón verde', 8], ['Tomate chonto', 6], ['Zanahoria', 4], ['Panela', 4], ['Fríjol', 3], ['Limón Tahití', 3]];
let CAN = { central: 'Bogotá, D.C., Corabastos', items: EJEMPLO.map(([p, k]) => ({ p, k })), ejemplo: true };
const guardar = () => { try { localStorage.setItem('canasta', JSON.stringify({ central: CAN.central, items: CAN.items })); } catch (e) {} };
function miCanasta() {
  const sc = $('#sel-central');
  if (!sc.options.length) {
    const cs = [...new Set(D.series.map((s) => s.central))].sort((a, b) => nombreCentral(a).localeCompare(nombreCentral(b), 'es'));
    sc.innerHTML = cs.map((c) => `<option value="${c.replace(/"/g, '&quot;')}">${nombreCentral(c)}</option>`).join('');
    sc.onchange = () => { CAN.central = sc.value; CAN.ejemplo = false; guardar(); miCanasta(); };
    $('#btn-agregar').onclick = () => { const p = $('#sel-agregar').value; if (p) { CAN.items.push({ p, k: 1 }); CAN.ejemplo = false; guardar(); miCanasta(); } };
  }
  sc.value = CAN.central;
  const disp = Object.fromEntries(D.series.filter((s) => s.central === CAN.central).map((s) => [s.producto, s]));
  const fuera = CAN.items.filter((it) => !disp[it.p]).map((it) => it.p);
  const items = CAN.items.filter((it) => disp[it.p]);
  let tS = 0, tO = 0, tLo = 0, tHi = 0; let mayor = null;
  const filas = items.map((it, i) => {
    const s = disp[it.p]; const cS = s.precio_actual * it.k, cO = s.precio_esperado * it.k;
    tS += cS; tO += cO; tLo += s.rango[0] * it.k; tHi += s.rango[1] * it.k;
    if (!mayor || cO - cS > mayor.d) mayor = { p: it.p, d: cO - cS };
    return `<tr><td><b>${it.p}</b></td><td class="n"><input class="kg" type="number" min="0" step="0.5" value="${it.k}" data-i="${CAN.items.indexOf(it)}" aria-label="Cantidad en ${uni(s)} de ${it.p}" id="kg-${i}"></td>
      <td class="n">${pesos(s.precio_actual)}</td><td class="n">${pesos(s.precio_esperado)}</td><td class="n">${pesos(cS)}</td><td class="n"><b>${pesos(cO)}</b></td>
      <td class="n ${cO > cS ? 'sube' : 'baja'}">${pct(s.cambio_pct)}</td><td><span class="pill pill--${s.riesgo}">${txtRiesgo[s.riesgo]}</span></td>
      <td><button type="button" class="quitar" data-i="${CAN.items.indexOf(it)}" aria-label="Quitar ${it.p}">×</button></td></tr>`;
  });
  const dif = tO - tS, dpct = tS ? 100 * dif / tS : 0;
  $('#canasta-total').innerHTML = `
    <div><b class="num">${pesos(tS)}</b><span>costo con los precios de ${MU()}</span></div>
    <div><b class="num ${dif > 0 ? 'sube' : 'baja'}">${pesos(tO)}</b><span>costo esperado en ${MP()} (${pct(dpct)}, ${dif >= 0 ? '+' : '−'}${pesos(Math.abs(dif))})</span></div>
    <div><b class="num" style="font-size:20px">${pesos(tLo)} a ${pesos(tHi)}</b><span>rango probable en ${MP()} (80 % de probabilidad, aproximado)</span></div>`;
  $('#sub-canasta').textContent = (CAN.ejemplo ? 'Canasta de ejemplo; cámbiela a su gusto. ' : '') + (mayor && mayor.d > 0 ? `Lo que más encarece la compra es ${mayor.p} (+${pesos(mayor.d)}).` : 'Ningún alimento de la lista sube.') + (fuera.length ? ` No disponible en esta central: ${fuera.join(', ')}.` : '');
  $('#tabla-canasta').innerHTML = `<thead><tr><th>Alimento</th><th class="n">Cantidad (kg)</th><th class="n">${corto(MU())} $/kg</th><th class="n">${corto(MP())} $/kg esperado</th><th class="n">Costo ${corto(MU())}</th><th class="n">Costo ${corto(MP())}</th><th class="n">Cambio</th><th>Riesgo</th><th></th></tr></thead><tbody>${filas.join('')}</tbody>`;
  $('#tabla-canasta').querySelectorAll('.kg').forEach((inp) => inp.onchange = () => { CAN.items[+inp.dataset.i].k = Math.max(0, +inp.value || 0); CAN.ejemplo = false; guardar(); miCanasta(); });
  $('#tabla-canasta').querySelectorAll('.quitar').forEach((b) => b.onclick = () => { CAN.items.splice(+b.dataset.i, 1); CAN.ejemplo = false; guardar(); miCanasta(); });
  const yaEsta = new Set(CAN.items.map((it) => it.p));
  $('#sel-agregar').innerHTML = Object.keys(disp).filter((p) => !yaEsta.has(p)).sort((a, b) => a.localeCompare(b, 'es')).map((p) => `<option>${p}</option>`).join('');
}

function todo() { kpis(); mapa(); panel(); dispersion(); }


export function montarPanorama(d, x) {
  D = d; X = x; rellenarMeses();
  $('#cinta').textContent = `Pronóstico para ${nomMes(d.mes_pronostico)} de ${d.mes_pronostico.slice(0, 4)} · datos hasta ${nomMes(d.ultimo_mes)}`;
  $('#m-riesgo').onclick = () => { estado.modo = 'riesgo'; $('#m-riesgo').setAttribute('aria-pressed', 'true'); $('#m-cambio').setAttribute('aria-pressed', 'false'); mapa(); };
  $('#m-cambio').onclick = () => { estado.modo = 'cambio'; $('#m-cambio').setAttribute('aria-pressed', 'true'); $('#m-riesgo').setAttribute('aria-pressed', 'false'); mapa(); };
  filtros(); calor(); productos(); producto(); todo(); red();
}

export function montarCiudad(d, o) { D = d; O = o; rellenarMeses(); miCiudad(); }

export function montarCanasta(d) {
  D = d; rellenarMeses();
  try { const g = JSON.parse(localStorage.getItem('canasta') || 'null'); if (g && g.central && Array.isArray(g.items)) CAN = { ...g, ejemplo: false }; } catch (e) {}
  miCanasta();
}
