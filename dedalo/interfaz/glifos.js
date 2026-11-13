// La escena. Todo lo que se dibuja sale del estado que devuelve la consola: cada carácter es una
// solicitud HTTP que ocurrió. No hay ilustración: si el dato cambia, el dibujo cambia.
(function () {
'use strict';
const T = window.TEXTOS;
// Negro Olbers · Tiza · Regolito · Aurora (solo eventos) · Egeo (Alice) · Olivo (Bob) · Ámbar (tú, el visitante)
// Azogue (el espejo y su token) · Hilo de Ariadna (el laberinto)
const C = { fondo: '#050505', tiza: '#ececec', regolito: '#8d8d8d', tenue: '#4a4a4a', aurora: '#ff6b9a',
  alice: '#7fb2e0', bob: '#a9d18e', visitor: '#f2b33d', azogue: '#9fdcd9', hilo: '#cf84e6' };
const PIX = '"VT323","Share Tech Mono",monospace', MONO = '"Share Tech Mono",ui-monospace,monospace';
const ACTORES = ['alice', 'bob', 'visitor'];
const SALAS = ['/archive', '/archive/project', '/archive/export', '/archive/index'];
const DOCS = [['alice-note', 'alice'], ['bob-note', 'bob'], ['visitor-note', 'visitor']];
const PASILLOS = [[0, 1], [1, 2], [2, 3], [3, 1]];
const AUREO = 2.39996, ARENA = '#*+=%@&$:;';
const quieto = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);

let cv, ctx, W = 0, H = 0, K = 1, P = null, est = null, recibido = 0, rol = 'visitor';
let viajes = [], flechas = [], caidas = {}, destellos = [], toques = [], sobre = null, portada = null, alTocar = null;

const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const ease = u => u * u * (3 - 2 * u);
const mez = (p, q, u) => [p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u];
const pon = (s, o) => s.replace(/\{(\w+)\}/g, (_, k) => (o[k] == null ? '' : o[k]));
const nombre = a => T.actores[a] || '';

function txt(s, x, y, color, font, align, alfa) {
  ctx.globalAlpha = alfa == null ? 1 : alfa;
  ctx.fillStyle = color; ctx.font = font; ctx.textAlign = align || 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(s, x, y);
  ctx.globalAlpha = 1;
}

function componer() {
  const v = W < 620, R = v ? Math.min(W * 0.3, H * 0.12) : Math.min(W * 0.125, H * 0.2);
  if (v) {
    P = { v, R, actor: { alice: [W * 0.17, H * 0.075], bob: [W * 0.5, H * 0.075], visitor: [W * 0.8, H * 0.075] },
      puerta: [W * 0.03, H * 0.25, W * 0.97, H * 0.25],
      docs: [[W * 0.18, H * 0.345], [W * 0.5, H * 0.345], [W * 0.82, H * 0.345]],
      app: [W * 0.5, H * 0.345], espejo: [W * 0.5, H * 0.495], lab: [W * 0.5, H * 0.765] };
  } else {
    P = { v, R, actor: { alice: [W * 0.12, H * 0.15], bob: [W * 0.12, H * 0.47], visitor: [W * 0.12, H * 0.79] },
      puerta: [W * 0.33, H * 0.04, W * 0.33, H * 0.96],
      docs: [[W * 0.56, H * 0.17], [W * 0.72, H * 0.17], [W * 0.88, H * 0.17]],
      app: [W * 0.72, H * 0.17], espejo: [W * 0.47, H * 0.56], lab: [W * 0.76, H * 0.62] };
  }
  P.r0 = v ? 26 : clamp(H * 0.085, 26, 46);
  const [lx, ly] = P.lab;
  P.salas = [[lx - R, ly], [lx, ly - R * 0.72], [lx + R, ly], [lx, ly + R * 0.72]];
}

function medir() {
  const r = cv.getBoundingClientRect(), d = Math.min(window.devicePixelRatio || 1, 2);
  // en pantallas grandes (un proyector) el dibujo crece entero; la letra nunca baja de su tamaño base
  K = r.width < 620 ? 1 : clamp(Math.min(r.width / 840, r.height / 440), 1, 1.8);
  W = Math.max(280, r.width) / K; H = Math.max(260, r.height) / K;
  cv.width = Math.round(W * K * d); cv.height = Math.round(H * K * d);
  ctx.setTransform(d * K, 0, 0, d * K, 0, 0);
  componer();
}

// ---- lo que el estado dice del laberinto
function etapa() { return est.senuelos.reduce((m, s) => Math.max(m, s.sala), 0); }
function posSala(i) { return est.modo === 'static' ? P.lab : P.salas[i]; }
function indiceSala(ruta) { return SALAS.indexOf(ruta.split('?')[0]); }
function salaConocida(i) {
  if (!est.senuelos.length) return false;
  return est.modo === 'static' ? i === 0 : i <= etapa();
}
function salaVisitada(i) {
  if (est.modo === 'static') return i === 0 && est.libro.some(e => e.motivo === 'static_decoy');
  return i < 3 ? i < etapa() : est.libro.some(e => e.motivo === 'maze_loop');
}

// adónde va una solicitud, según el motivo que anotó el motor
function destino(e) {
  const m = e.motivo;
  if (e.via === 'senuelo' && m !== 'method_denied') {
    if (m === 'decoy_budget') return { p: posSala(0), cerrado: true };
    const i = indiceSala(e.ruta);
    return { p: i >= 0 && (est.modo !== 'static' || i === 0) ? posSala(i) : P.lab };
  }
  if (m === 'decoy_issued' || m === 'maintenance') return { p: P.espejo };
  if (m === 'document_allowed' || m === 'document_denied') {
    const k = DOCS.findIndex(d => '/api/documents/' + d[0] === e.ruta);
    return { p: k >= 0 ? P.docs[k] : P.app };
  }
  if (m === 'list_allowed') return { p: P.app };
  return { rebota: true };                      // revocada, credencial desconocida, ruta que no existe
}
function cruce(a, b) {
  const g = P.puerta;
  if (P.v) { const u = (g[1] - a[1]) / ((b[1] - a[1]) || 1); return [a[0] + (b[0] - a[0]) * u, g[1]]; }
  const u = (g[0] - a[0]) / ((b[0] - a[0]) || 1); return [g[0], a[1] + (b[1] - a[1]) * u];
}
function enCamino(pts, u) {
  if (pts.length === 2) return mez(pts[0], pts[1], u);
  const d1 = Math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]), d2 = Math.hypot(pts[2][0] - pts[1][0], pts[2][1] - pts[1][1]);
  const k = d1 / ((d1 + d2) || 1);
  return u < k ? mez(pts[0], pts[1], u / k) : mez(pts[1], pts[2], (u - k) / ((1 - k) || 1));
}

// ---- piezas
function puerta(ahora) {
  const g = P.puerta, n = Math.floor(Math.hypot(g[2] - g[0], g[3] - g[1]) / 13);
  for (let i = 0; i <= n; i++) { const p = mez([g[0], g[1]], [g[2], g[3]], i / n); txt(P.v ? '-' : '¦', p[0], p[1], C.regolito, `13px ${MONO}`, 'center', 0.55); }
  const dispara = flechas.length > 0;
  if (P.v) {
    txt(T.escena.pasarela, g[0], g[1] - 12, C.regolito, `11px ${MONO}`, 'left');
    txt(T.escena.arqueros, g[2], g[1] - 12, dispara ? C.aurora : C.regolito, `11px ${MONO}`, 'right');
  } else {
    txt(T.escena.arqueros, g[0], g[1] - 2, dispara ? C.aurora : C.regolito, `11px ${MONO}`);
    txt(T.escena.pasarela, g[0], g[3] + 4, C.regolito, `11px ${MONO}`);
  }
}

function brillo(p, ahora) {
  let b = 0;
  for (const d of destellos) if (d.p === p) b = Math.max(b, 1 - (ahora - d.ini) / 700);
  return clamp(b, 0, 1);
}

function documentos(ahora) {
  if (!P.v) txt(T.escena.aplicacion + ' · ' + T.escena.documentos, P.docs[0][0] - 30, P.docs[0][1] - 50, C.regolito, `11px ${MONO}`, 'left');
  DOCS.forEach(([id, dueno], k) => {
    const [x, y] = P.docs[k], ruta = '/api/documents/' + id;
    const lect = est.libro.filter(e => e.via === 'sesion' && e.ruta === ruta);
    const si = lect.filter(e => e.estado === 200).length, b = brillo(P.docs[k], ahora);
    for (let r = 0; r < 3; r++) for (let c = 0; c < 5; c++)
      txt(dueno[0], x + (c - 2) * 11, y + (r - 1) * 13 - 6, C[dueno], `14px ${MONO}`, 'center', 0.32 + 0.68 * b + (si ? 0.2 : 0));
    txt(id.toUpperCase(), x, y + 30, C[dueno], `12px ${MONO}`);
    txt(pon(P.v ? T.escena.leidoCorto : T.escena.leido, { s: si, n: lect.length - si }), x, y + 45, C.regolito, `11px ${MONO}`);
    toques.push({ x, y: y + 8, r: 46, obj: { tipo: 'pedir', ruta, via: 'sesion' } });
  });
}

function espejo(ahora) {
  const [x, y] = P.espejo, vivo = est.modo !== 'control', col = vivo ? C.azogue : C.tenue, b = brillo(P.espejo, ahora);
  const a = 0.6 + 0.4 * b;
  txt('/\\', x, y - 9, col, `20px ${MONO}`, 'center', a); txt('\\/', x, y + 9, col, `20px ${MONO}`, 'center', a);
  txt(T.escena.espejo, x, y + 32, col, `12px ${MONO}`);
  txt(vivo ? pon(T.escena.entregados, { n: est.senuelos.length }) : T.escena.apagado, x, y + 46, C.regolito, `11px ${MONO}`);
  toques.push({ x, y: y + 8, r: 44, obj: { tipo: 'pedir', ruta: '/api/maintenance', via: 'sesion' } });
}

function sala(i, ahora) {
  const [x, y] = posSala(i), conocida = salaConocida(i), vista = salaVisitada(i), b = brillo(posSala(i), ahora);
  if (!conocida) { txt('?', x, y, C.regolito, `18px ${MONO}`, 'center', 0.5); return; }
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++)
    txt(vista ? '#' : '·', x + (c - 1) * 10, y + (r - 1) * 11, C.hilo, `14px ${MONO}`, 'center', (vista ? 0.75 : 0.5) + 0.25 * b);
  // los nombres van donde no pasa ningún pasillo
  const col = vista ? C.hilo : C.regolito, f = `11px ${MONO}`;
  if (est.modo === 'static' || i === 3) txt(T.escena.salas[i], x, y + 27, col, f);
  else if (i === 0) txt(T.escena.salas[i], x + 14, y - 26, col, f, 'right');
  else if (i === 2) txt(T.escena.salas[i], x - 14, y - 26, col, f, 'left');
  else txt(T.escena.salas[i], x, y - 26, col, f);
  toques.push({ x, y, r: 30, obj: { tipo: 'pedir', ruta: SALAS[i], via: 'senuelo' } });
}

function laberinto(ahora) {
  const [lx, ly] = P.lab, R = P.R, arriba = ly - R * 0.72 - 50;
  const hilado = est.modo === 'maze' && est.libro.some(e => e.via === 'senuelo' && e.estado === 200);
  txt(T.escena.laberinto + (hilado ? ' · ' + T.escena.hilo : ''), lx, arriba, est.modo === 'control' ? C.regolito : C.hilo, `12px ${MONO}`);
  if (est.modo === 'control') {
    for (let i = 0; i < 28; i++) { const a = i / 28 * Math.PI * 2; txt('·', lx + Math.cos(a) * R, ly + Math.sin(a) * R * 0.72, C.tenue, `13px ${MONO}`); }
    txt(T.escena.sinLaberinto, lx, ly, C.regolito, `12px ${MONO}`);
    return;
  }
  if (est.modo === 'static') { sala(0, ahora); txt(T.escena.unEspejo, lx, ly + 44, C.regolito, `11px ${MONO}`); presupuesto(ly + 70, ahora); return; }
  // el hilo: cuántas veces se recorrió cada pasillo, leído del libro
  const cuenta = {}, ultimo = {};
  for (const e of est.libro) {
    if (e.via !== 'senuelo' || e.estado !== 200) continue;
    const i = indiceSala(e.ruta); if (i < 0) continue;
    const de = e.de || e.actor;
    if (ultimo[de] != null && ultimo[de] !== i) cuenta[ultimo[de] + '>' + i] = (cuenta[ultimo[de] + '>' + i] || 0) + 1;
    ultimo[de] = i;
  }
  for (const [a, b] of PASILLOS) {
    if (!salaConocida(a) || !salaConocida(b)) continue;
    const n = cuenta[a + '>' + b] || 0, p = P.salas[a], q = P.salas[b], largo = Math.hypot(q[0] - p[0], q[1] - p[1]), m = Math.floor(largo / 9);
    for (let k = 3; k < m - 2; k++) { const s = mez(p, q, k / m); txt('·', s[0], s[1], n ? C.hilo : C.tenue, `13px ${MONO}`, 'center', n ? 0.95 : 0.7); }
    if (n > 1) {                                   // la cuenta va del lado de afuera del pasillo, lejos de los nombres
      const s = mez(p, q, 0.5), nx = -(q[1] - p[1]) / largo, ny = (q[0] - p[0]) / largo, fuera = (s[0] - lx) * nx + (s[1] - ly + 1) * ny >= 0 ? 1 : -1;
      txt('×' + n, s[0] + nx * fuera * 16, s[1] + ny * fuera * 16, C.hilo, `17px ${PIX}`);
    }
  }
  for (let i = 0; i < 4; i++) sala(i, ahora);
  for (const de in ultimo) { const s = P.salas[ultimo[de]]; ctx.fillStyle = C.fondo; ctx.fillRect(s[0] - 6, s[1] - 7, 12, 13); txt('@', s[0], s[1], C.tiza, `18px ${PIX}`); }
  presupuesto(ly + R * 0.72 + 52, ahora);
}

function presupuesto(y, ahora) {
  const lx = P.lab[0], lim = est.limites;
  est.senuelos.slice(-2).forEach((s, f) => {
    const total = lim.pasos + s.rechazadas, lado = 9, paso = 12, x0 = lx - (total * paso - 3) / 2, yy = y + f * 34;
    for (let i = 0; i < total; i++) {
      const x = x0 + i * paso;
      if (i < s.servidas) { ctx.fillStyle = C.hilo; ctx.fillRect(x, yy - lado / 2, lado, lado); }
      else if (i < lim.pasos) { ctx.strokeStyle = C.tenue; ctx.lineWidth = 1; ctx.strokeRect(x + 0.5, yy - lado / 2 + 0.5, lado - 1, lado - 1); }
      else { ctx.fillStyle = C.aurora; ctx.fillRect(x, yy - lado / 2, lado, lado); }
    }
    const queda = Math.ceil(lim.vigencia - s.edad - (ahora - recibido) / 1000), vencido = queda <= 0;
    const linea = `${s.ref.toUpperCase()} · ${nombre(s.de)} · ${T.escena.presupuesto} ${s.servidas}/${lim.pasos} · ` +
      (vencido ? T.escena.vencido : `${T.escena.vigencia} ${queda} S`);
    txt(linea, lx, yy + 15, vencido || s.rechazadas ? C.aurora : C.regolito, `11px ${MONO}`);
  });
}

function actor(a, ahora) {
  const [x, y] = P.actor[a], s = est.sesiones[a], col = s.revocada ? C.aurora : C[a], mio = a === rol;
  const todas = est.libro.filter(e => e.actor === a), mias = todas.slice(-40);
  const caida = s.revocada ? ease(clamp((ahora - (caidas[a] || 0)) / 900, 0, 1)) : 0;
  const giro = s.revocada || quieto ? 0 : ahora * 0.00012;            // una sesión revocada no se mueve
  const r0 = P.r0;
  for (let i = 0; i < 18; i++) { const g = i / 18 * Math.PI * 2 - giro * 0.5; txt(mio ? '+' : '·', x + Math.cos(g) * r0, y + Math.sin(g) * r0, col, `12px ${MONO}`, 'center', mio ? 0.75 : 0.35); }
  mias.forEach((e, i) => {
    const g = i * AUREO + giro, r = (4 + r0 * 0.13 * Math.sqrt(i + 0.6)) * (1 + 0.55 * caida);
    const ok = e.estado < 300, senuelo = e.via === 'senuelo';
    txt(String(e.estado)[0], x + Math.cos(g) * r, y + Math.sin(g) * r, s.revocada ? C.aurora : senuelo ? C.azogue : ok ? col : C.regolito,
      `13px ${MONO}`, 'center', s.revocada ? 0.55 : 0.95);
  });
  const ly = y + r0 + 16;
  txt((mio ? T.tu + ' · ' : '') + nombre(a), x, ly, col, `${P.v ? 17 : 20}px ${PIX}`);
  const linea = s.revocada ? T.escena.revocada : s.ventana ? `${T.escena.ventana} ${s.ventana.hits_left}` : s.marcada ? T.escena.marcada : pon(T.escena.pedidos, { n: todas.length });
  txt(linea, x, ly + 15, s.revocada ? C.aurora : C.regolito, `11px ${MONO}`);
  const ref = est.hallados[a];
  if (ref) {
    const usado = est.senuelos.some(d => d.ref === ref && d.servidas + d.rechazadas > 0), tx = x + r0 + 16, ty = y - r0 + 4;
    txt('<>', tx, ty, C.azogue, `20px ${PIX}`, 'center', usado ? 1 : 0.7);
    txt(ref.toUpperCase(), tx, ty + 14, C.azogue, `11px ${MONO}`);
  }
  if (a !== 'bob') toques.push({ x, y, r: r0 + 6, obj: { tipo: 'rol', actor: a } });
}

function viaje(v, ahora) {
  const u = (ahora - v.ini) / v.dur;
  if (u >= 0.5 && !v.hecho) aplicar(v, ahora);
  if (u >= 1) return false;
  const e = v.e, a = P.actor[e.actor], d = destino(e), g = cruce(a, d.p || P.app), pts = d.rebota ? [a, g] : [a, g, d.p];
  const col = e.via === 'senuelo' ? C.azogue : C[e.actor];
  if (u < 0.46) {
    const q = enCamino(pts, ease(u / 0.46));
    txt('>', q[0], q[1], col, `22px ${PIX}`);
    txt(e.ruta.length > 28 ? e.ruta.slice(0, 27) + '…' : e.ruta, q[0], q[1] - 15, col, `11px ${MONO}`);
  } else if (u > 0.54) {
    const q = enCamino(pts, 1 - ease((u - 0.54) / 0.46)), evento = e.accion === 'revoked';
    txt(String(e.estado), q[0], q[1], evento ? C.aurora : e.estado < 300 ? col : C.regolito, `26px ${PIX}`);
  } else {
    const q = pts[pts.length - 1];
    txt(d.cerrado ? T.escena.cerrado : '*', q[0], q[1] - 20, d.cerrado ? C.aurora : col, `${d.cerrado ? 12 : 20}px ${MONO}`);
  }
  return true;
}

// la respuesta llegó: recién ahí cambia lo que se ve
function aplicar(v, ahora) {
  v.hecho = true;
  const antes = est;
  est = v.estado; recibido = v.rec;
  const d = destino(v.e);
  if (d.p) destellos.push({ p: d.p, ini: ahora });
  for (const a of ACTORES) if (est.sesiones[a].revocada && !(antes && antes.episodio === est.episodio && antes.sesiones[a].revocada)) {
    if (quieto) caidas[a] = ahora - 2000; else { flechas.push({ a, ini: ahora, dur: 620 }); caidas[a] = ahora + 620; }
  }
}

function flecha(f, ahora) {
  const u = (ahora - f.ini) / f.dur;
  if (u >= 1) return false;
  const g = P.puerta, desde = P.v ? [g[2], g[1]] : [g[0], g[1]], hasta = P.actor[f.a], ang = Math.atan2(hasta[1] - desde[1], hasta[0] - desde[0]);
  for (let k = 0; k < 9; k++) {
    const w = u - k * 0.035; if (w <= 0) continue;
    const p = mez(desde, hasta, ease(w));
    ctx.save(); ctx.translate(p[0], p[1]); ctx.rotate(ang);
    txt(k ? '-' : '>', 0, 0, C.aurora, `${k ? 16 : 26}px ${PIX}`, 'center', k ? 0.8 - k * 0.07 : 1);
    ctx.restore();
  }
  return true;
}

// la portada: la palabra se arma con caracteres. Menos de dos segundos, cualquier tecla la termina.
function armarPortada() {
  const hoja = document.createElement('canvas'), hc = hoja.getContext('2d', { willReadFrequently: true });
  const px = clamp(W * 0.2, 70, 190), f = `${px}px ${PIX}`;
  hc.font = f; const w = Math.ceil(hc.measureText(T.portada).width) + 20, h = Math.ceil(px * 1.25);
  hoja.width = w; hoja.height = h; hc.font = f; hc.fillStyle = '#fff'; hc.textBaseline = 'top'; hc.fillText(T.portada, 10, px * 0.12);
  const d = hc.getImageData(0, 0, w, h).data, paso = Math.max(5, Math.round(px / 22)), celdas = [];
  for (let y = 0; y < h; y += paso) for (let x = 0; x < w; x += paso)
    if (d[((y + (paso >> 1)) * w + x + (paso >> 1)) * 4 + 3] > 110)
      celdas.push({ x: x - w / 2, y: y - h / 2, ox: (Math.random() - 0.5) * W, oy: (Math.random() - 0.5) * H, t: x / w * 0.45 + Math.random() * 0.1, ch: ARENA[(x + y) % ARENA.length] });
  portada = { celdas, paso, ini: performance.now(), dur: 1300, queda: 650 };
}
function pintarPortada(ahora) {
  const u = (ahora - portada.ini) / portada.dur;
  if (u > 1 + portada.queda / portada.dur) { portada = null; return; }
  const cx = W / 2, cy = H * 0.46;
  for (const c of portada.celdas) {
    const w = ease(clamp((u - c.t) / 0.45, 0, 1));
    txt(w < 1 ? ARENA[(Math.random() * ARENA.length) | 0] : c.ch, cx + c.ox + (c.x - c.ox) * w, cy + c.oy + (c.y - c.oy) * w, C.tiza, `${portada.paso + 5}px ${MONO}`, 'center', 0.25 + 0.75 * w);
  }
  if (u > 1) txt(T.lema, cx, cy + clamp(W * 0.2, 70, 190) * 0.62, C.regolito, `12px ${MONO}`);
}

function cuadro(ahora) {
  requestAnimationFrame(cuadro);
  if (!ctx) return;
  ctx.fillStyle = C.fondo; ctx.fillRect(0, 0, W, H);
  if (portada) { pintarPortada(ahora); if (portada) return; }
  if (!est) return;
  toques = [];
  destellos = destellos.filter(d => ahora - d.ini < 700);
  puerta(ahora); documentos(ahora); espejo(ahora); laberinto(ahora);
  for (const a of ACTORES) actor(a, ahora);
  viajes = viajes.filter(v => viaje(v, ahora));
  flechas = flechas.filter(f => flecha(f, ahora));
  if (sobre) { txt('[', sobre.x - sobre.r, sobre.y, C.tiza, `22px ${PIX}`); txt(']', sobre.x + sobre.r, sobre.y, C.tiza, `22px ${PIX}`); }
}

function bajo(ev) {
  const r = cv.getBoundingClientRect(), x = (ev.clientX - r.left) / K, y = (ev.clientY - r.top) / K;
  return toques.find(t => Math.hypot(t.x - x, t.y - y) <= t.r) || null;
}

window.GLIFOS = {
  colores: C,
  iniciar(lienzo, tocar) {
    cv = lienzo; ctx = cv.getContext('2d'); alTocar = tocar;
    medir();
    if (window.ResizeObserver) new ResizeObserver(medir).observe(cv); else window.addEventListener('resize', medir);
    cv.addEventListener('mousemove', ev => { sobre = portada ? null : bajo(ev); cv.style.cursor = sobre ? 'pointer' : 'default'; });
    cv.addEventListener('mouseleave', () => { sobre = null; });
    cv.addEventListener('click', ev => { if (portada) { portada = null; return; } const t = bajo(ev); if (t && alTocar) alTocar(t.obj); });
    requestAnimationFrame(cuadro);
  },
  portada() { if (!quieto) armarPortada(); },
  saltar() { const habia = !!portada; portada = null; return habia; },
  rol(a) { rol = a; },
  // estado nuevo sin solicitud (arranque, sondeo, operador): se muestra en el acto
  poner(nuevo) {
    const otro = !est || est.episodio !== nuevo.episodio;
    if (otro) { viajes = []; flechas = []; caidas = {}; destellos = []; }
    if (viajes.some(v => !v.hecho)) return;         // hay una respuesta en camino: ella trae su estado
    const ahora = performance.now();
    if (est && !otro) for (const a of ACTORES) if (nuevo.sesiones[a].revocada && !est.sesiones[a].revocada) caidas[a] = ahora;
    est = nuevo; recibido = ahora;
  },
  // una solicitud que ocurrió: viaja, y al volver trae el estado
  entrada(e, nuevo) {
    const ahora = performance.now(), v = { e, estado: nuevo, rec: ahora, ini: ahora, dur: quieto ? 1 : 950, hecho: false };
    if (!est) { est = nuevo; recibido = ahora; }
    viajes.push(v);
  },
};
})();
