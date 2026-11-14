// Lo que pasa detrás. Todo se dibuja a partir del estado que devuelve el servidor: cada carácter que viaja es
// una solicitud real que recibió Cnosos. Nada se inventa en el navegador.
(function () {
'use strict';
const $ = id => document.getElementById(id);
const C = { fondo: '#050505', tiza: '#ececec', regolito: '#8d8d8d', tenue: '#3a3a3a', aurora: '#ff6b9a',
  hilo: '#cf84e6', azogue: '#9fdcd9', ambar: '#f2b33d', olivo: '#a9d18e' };
const PIX = '"VT323","Share Tech Mono",monospace', MONO = '"Share Tech Mono",ui-monospace,monospace';
const NODOS = { LOGIN: [0.24, 0.2], PERFIL: [0.24, 0.5], DIRECTORIO: [0.24, 0.8], ARCHIVOS: [0.42, 0.2], BUSCAR: [0.42, 0.5],
  DESCARGAS: [0.42, 0.8], ADMIN: [0.6, 0.2], CONFIG: [0.6, 0.5], TIQUETES: [0.6, 0.8] };
const quieto = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);

let clave = '', desde = 0, est = null, eventos = [], viajes = [], destellos = {}, episodio = null, ultimoIcaro = 0;
let cv, ctx, W = 0, H = 0, escribe = 0;

function el(tag, texto, clase) { const n = document.createElement(tag); if (texto != null) n.textContent = texto; if (clase) n.className = clase; return n; }
function vaciar(n) { while (n.firstChild) n.removeChild(n.firstChild); }
function guardar(k, v) { try { sessionStorage.setItem(k, v); } catch (e) { /* sin almacenamiento */ } }
function leer(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }

async function api(ruta, cuerpo) {
  const cab = { 'X-Panel-Clave': clave };
  if (cuerpo) cab['Content-Type'] = 'application/json';
  try {
    const r = await fetch(ruta, { method: cuerpo ? 'POST' : 'GET', headers: cab, body: cuerpo ? JSON.stringify(cuerpo) : undefined, cache: 'no-store' });
    return { ok: r.ok, estado: r.status, datos: await r.json() };
  } catch (e) { return { ok: false, estado: 0, datos: { error: 'sin_senal' } }; }
}

function decir(texto, evento) {
  const v = $('voz'), turno = ++escribe; v.classList.toggle('evento', !!evento);
  let i = 0;
  (function paso() { if (turno !== escribe) return; i = Math.min(texto.length, i + 3); v.textContent = texto.slice(0, i); if (i < texto.length) setTimeout(paso, 14); })();
}

// ---------------------------------------------------------------- de la ruta al nodo
function nodo(e) {
  const r = (e.ruta || '').split('?')[0];
  if (r.startsWith('/api/login')) return 'LOGIN';
  if (r.startsWith('/api/perfil')) return 'PERFIL';
  if (r.startsWith('/api/archivos')) return 'ARCHIVOS';
  if (r.startsWith('/api/buscar')) return 'BUSCAR';
  if (r.startsWith('/api/descargas')) return 'DESCARGAS';
  if (r.startsWith('/api/admin')) return 'ADMIN';
  if (r.startsWith('/api/config') || r === '/.env' || r.startsWith('/backup')) return 'CONFIG';
  if (r.startsWith('/api/tiquetes')) return 'TIQUETES';
  if (r.startsWith('/api/directorio')) return 'DIRECTORIO';
  return null;
}

function geometria() {
  const lab = [W * 0.86, H * 0.5], R = Math.min(W * 0.12, H * 0.42);
  return { lab, R, puerta: [W * 0.07, H * 0.5] };
}
function posNodo(n) { const p = NODOS[n]; return [p[0] * W, p[1] * H]; }
function posAnillo(nivel, k) {
  const g = geometria(), r = g.R * (0.3 + 0.7 * Math.min(1, (nivel + 1) / Math.max(4, nivelMax() + 2)));
  const a = (k * 2.39996) % (Math.PI * 2);
  return [g.lab[0] + Math.cos(a) * r, g.lab[1] + Math.sin(a) * r];
}
function nivelMax() { return est ? est.laberinto.nivel_max : 0; }
function posSesion(ref) {
  const reales = (est ? est.sesiones : []).filter(s => !s.laberinto);
  const i = Math.max(0, reales.findIndex(s => s.ref === ref));
  const n = Math.max(1, reales.length);
  return [W * 0.07, H * (0.15 + 0.7 * (n === 1 ? 0.5 : i / (n - 1)))];
}

function txt(s, x, y, color, font, align, alfa) {
  ctx.globalAlpha = alfa == null ? 1 : alfa; ctx.fillStyle = color; ctx.font = font; ctx.textAlign = align || 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(s, x, y); ctx.globalAlpha = 1;
}

// ---------------------------------------------------------------- la escena
function cuadro(ahora) {
  requestAnimationFrame(cuadro);
  if (!ctx) return;
  ctx.fillStyle = C.fondo; ctx.fillRect(0, 0, W, H);
  if (!est) { txt('SIN SEÑAL · ABRE LA DIRECCIÓN QUE IMPRIMIÓ EL PANEL', W / 2, H / 2, C.regolito, `14px ${MONO}`); return; }
  const g = geometria();
  // la puerta
  for (let y = 12; y < H - 8; y += 12) txt('¦', W * 0.14, y, C.tenue, `12px ${MONO}`);
  txt('ENTRADA', W * 0.14, 8, C.regolito, `10px ${MONO}`);
  // las sesiones reales
  est.sesiones.filter(s => !s.laberinto).forEach(s => {
    const [x, y] = posSesion(s.ref), caida = s.revocada;
    for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2 + (caida || quieto ? 0 : ahora * 0.0004); txt(caida ? '×' : '·', x + Math.cos(a) * 14, y + Math.sin(a) * 14, caida ? C.aurora : C.ambar, `11px ${MONO}`, 'center', 0.8); }
    txt(s.usuario, x, y + 26, caida ? C.aurora : C.tiza, `14px ${PIX}`);
    txt(caida ? 'REVOCADA · ÍCARO' : s.rol.toUpperCase(), x, y + 39, caida ? C.aurora : C.regolito, `9.5px ${MONO}`);
  });
  // los nodos de la infraestructura real
  const cuenta = {};
  eventos.forEach(e => { if (!e.laberinto) { const n = nodo(e); if (n) { cuenta[n] = cuenta[n] || [0, 0]; cuenta[n][0]++; if (e.intento) cuenta[n][1]++; } } });
  Object.keys(NODOS).forEach(n => {
    const [x, y] = posNodo(n), brillo = destellos[n] ? Math.max(0, 1 - (ahora - destellos[n]) / 900) : 0;
    const c = cuenta[n] || [0, 0], col = brillo > 0 && destellos[n + ':int'] ? C.aurora : C.tiza;
    txt(`[ ${n} ]`, x, y, col, `16px ${PIX}`, 'center', 0.55 + 0.45 * Math.max(brillo, c[0] ? 0.6 : 0));
    txt(`${c[0]} SOLIC · ${c[1]} INTENTOS`, x, y + 15, c[1] ? C.aurora : C.regolito, `9.5px ${MONO}`, 'center', 0.9);
  });
  // ícaro
  const icaroB = ultimoIcaro ? Math.max(0, 1 - (ahora - ultimoIcaro) / 2500) : 0;
  txt('ÍCARO', W * 0.74, 14, icaroB > 0 ? C.aurora : C.regolito, `16px ${PIX}`, 'center', 0.6 + 0.4 * icaroB);
  // el laberinto
  const niveles = Math.max(1, nivelMax() + 1);
  for (let k = 0; k < niveles; k++) {
    const r = g.R * (0.3 + 0.7 * Math.min(1, (k + 1) / Math.max(4, nivelMax() + 2))), m = Math.max(16, Math.floor(r / 3));
    for (let i = 0; i < m; i++) { const a = i / m * Math.PI * 2; txt(i % 7 === 0 ? '#' : '·', g.lab[0] + Math.cos(a) * r, g.lab[1] + Math.sin(a) * r, C.hilo, `11px ${MONO}`, 'center', 0.35 + 0.5 * (k === niveles - 1 ? 1 : 0.4)); }
  }
  ctx.fillStyle = C.fondo; ctx.fillRect(g.lab[0] - 52, g.lab[1] - 16, 104, 32);
  txt('LABERINTO', g.lab[0], g.lab[1] - 6, C.hilo, `16px ${PIX}`);
  txt(`NIVEL ${nivelMax()} · ${est.laberinto.pasos} PASOS`, g.lab[0], g.lab[1] + 9, C.hilo, `9.5px ${MONO}`);
  // las solicitudes que viajan
  viajes = viajes.filter(v => {
    const u = (ahora - v.ini) / v.dur; if (u >= 1) return false;
    const w = u * u * (3 - 2 * u), x = v.de[0] + (v.a[0] - v.de[0]) * w, y = v.de[1] + (v.a[1] - v.de[1]) * w;
    txt(v.ch, x, y, v.col, `18px ${PIX}`);
    if (v.etq && u > 0.6) txt(v.etq, v.a[0], v.a[1] - 16, v.col, `10px ${MONO}`, 'center', 1 - (u - 0.6) / 0.4);
    return true;
  });
}

function medir() {
  const r = cv.getBoundingClientRect(), d = Math.min(window.devicePixelRatio || 1, 2);
  W = Math.max(300, r.width); H = Math.max(180, r.height);
  cv.width = Math.round(W * d); cv.height = Math.round(H * d); ctx.setTransform(d, 0, 0, d, 0, 0);
}

// ---------------------------------------------------------------- llega un evento
function recibir(e, ahora, nombres) {
  const n = nodo(e), de = e.sesion ? posSesion(e.sesion) : geometria().puerta;
  let a = n ? posNodo(n) : geometria().puerta, col = e.estado < 300 ? C.tiza : C.regolito, etq = null;
  if (e.laberinto) { a = posAnillo(e.nivel || 0, e.n); col = C.hilo; }
  if (e.intento) { col = C.aurora; etq = (nombres[e.intento] || e.intento).toUpperCase(); destellos[n + ':int'] = ahora; }
  if (n) destellos[n] = ahora;
  if (!quieto) viajes.push({ de: e.laberinto ? geometria().puerta : de, a, col, ch: String(e.estado)[0], etq, ini: ahora, dur: 650 });
  if (e.accion === 'icaro') { ultimoIcaro = ahora; decir(`ÍCARO · USARON LA HIEDRA DE ${e.afectada} · SU SESIÓN REAL CAE · SIGUE EN EL LABERINTO`, true); }
  else if (e.accion === 'observado') decir(`HIEDRA USADA · ${e.afectada} QUEDA MARCADA (OBSERVAR)`, true);
  else if (e.accion === 'trepa') decir(`LA HIEDRA TREPA · NIVEL ${e.nivel} DEL LABERINTO`, false);
  else if (e.intento) decir(`${(nombres[e.intento] || e.intento).toUpperCase()} · EL MURO AGUANTA`, true);
  if (e.fuga) decir('EL SECRETO SALIÓ. ESTO ES UN FALLO DE LA DEFENSA.', true);
}

function lineaHilo(e) {
  const li = el('li');
  li.appendChild(el('span', String(e.n).padStart(4, ' ') + ' ', 'n'));
  li.appendChild(document.createTextNode(`${(e.usuario || 'anónimo').slice(0, 12).padEnd(12)} ${e.metodo.padEnd(5)} ${e.ruta.slice(0, 30).padEnd(30)} ${e.estado} `));
  if (e.accion === 'icaro') li.appendChild(el('span', ` ÍCARO revoca ${e.afectada} `, 'icaro'));
  else if (e.accion === 'trepa') li.appendChild(el('span', `trepa → nivel ${e.nivel}`, 'lab'));
  else if (e.laberinto) li.appendChild(el('span', `laberinto · nivel ${e.nivel}`, 'lab'));
  if (e.intento) li.appendChild(el('span', ' ' + ((est.nombres_intento || {})[e.intento] || e.intento), 'int'));
  return li;
}

// ---------------------------------------------------------------- el parte
function pintar() {
  if (!est) return;
  const a = $('almacen'); a.textContent = 'ALMACÉN ' + est.almacen.toUpperCase(); a.classList.toggle('oracle', est.almacen === 'oracle');
  $('episodio').textContent = 'EPISODIO ' + est.episodio;
  const intentos = est.sesiones.reduce((t, s) => t + Object.values(s.intentos).reduce((x, y) => x + y, 0), 0);
  const icaros = est.sesiones.filter(s => s.revocada).length;
  const cifras = [[est.eventos, 'solicitudes', ''], [intentos, 'intentos detectados', intentos ? 'mal' : ''], [icaros, 'sesiones cortadas', icaros ? 'mal' : ''],
    [`${est.laberinto.pasos}/${est.laberinto.nivel_max}`, 'laberinto pasos/nivel', 'hilo'], [est.tokens_atacante, 'tokens del atacante', 'hilo'],
    [est.laberinto.costo_ms.toFixed(2) + ' ms', 'nuestro costo · 0 tokens', 'ok'], [est.fugas, 'secretos filtrados', est.fugas ? 'mal' : 'ok']];
  const c = $('cifras'); vaciar(c);
  cifras.forEach(([v, t, k]) => { const d = el('div', null, 'cifra ' + k); d.appendChild(el('b', String(v))); d.appendChild(el('span', t)); c.appendChild(d); });
  const m = est.tareas.minotauro, d = est.tareas.dedalo;
  $('m-correr').disabled = !!m.activo; $('m-correr').textContent = m.activo ? 'ATACANDO…' : 'ATACAR';
  $('d-correr').disabled = !!d.activo; $('d-correr').textContent = d.activo ? 'PARCHANDO…' : 'PARCHAR MUROS';
  const ul = $('muros'); vaciar(ul);
  Object.keys(est.casos).forEach(k => {
    const r = (d.resultados || []).find(x => x.caso === k), li = el('li');
    li.appendChild(el('span', r ? (r.verificado ? '✔' : '✘') : '·', r ? (r.verificado ? 'si' : 'no') : 'pend'));
    const t = el('span', est.casos[k].titulo); t.appendChild(el('small', r ? r.veredicto : 'sin parchar todavía')); li.appendChild(t);
    li.appendChild(el('span', r ? (r.cwe || '—') : est.casos[k].cwe, r ? (r.cwe_correcta ? 'si' : 'no') : 'pend'));
    if (r) li.addEventListener('click', () => hoja(r));
    ul.appendChild(li);
  });
}

function hoja(r) {
  $('h-titulo').textContent = `${r.titulo} · ${r.cwe || '—'} (esperada ${r.cwe_esperada}) · ${r.intentos} intento(s)`;
  $('h-veredicto').textContent = `TALOS: ${r.veredicto}. ${r.explicacion || ''}`;
  $('h-antes').textContent = r.original; $('h-despues').textContent = r.parche || '(sin parche)';
  $('hoja').hidden = false;
}

let avisoMinotauro = null, avisoDedalo = 0;
async function sondear() {
  const r = await api('/panel/estado?desde=' + desde);
  if (!r.ok) { if (r.estado === 403) decir('SIN CLAVE · ABRE LA DIRECCIÓN QUE IMPRIMIÓ EL PANEL', true); return; }
  if (episodio !== r.datos.episodio) { episodio = r.datos.episodio; eventos = []; viajes = []; vaciar($('hilo')); }
  est = r.datos;
  const ahora = performance.now(), hilo = $('hilo');
  est.eventos_nuevos.forEach(e => { if (e.n > desde) { eventos.push(e); recibir(e, ahora, est.nombres_intento || {}); hilo.appendChild(lineaHilo(e)); desde = e.n; } });
  while (hilo.children.length > 400) hilo.removeChild(hilo.firstChild);
  if (eventos.length > 2000) eventos = eventos.slice(-2000);
  hilo.scrollTop = hilo.scrollHeight;
  $('hilo-pie').textContent = `· ${est.eventos} solicitudes · también en ${est.almacen}`;
  const m = est.tareas.minotauro;
  if (m.resumen && avisoMinotauro !== m.resumen.episodio + m.inicio) {
    avisoMinotauro = m.resumen.episodio + m.inicio;
    const s = m.resumen;
    decir(`MINOTAURO (${s.modelo}) TERMINÓ · DETECTADO ${s.paso_deteccion ? 'EN EL PASO ' + s.paso_deteccion : 'NO'} · NIVEL ${s.nivel_max} · ${s.tokens_atacante_en_laberinto} TOKENS PERDIDOS EN EL LABERINTO`, !s.paso_deteccion);
  }
  if (m.error) decir('MINOTAURO: ' + m.error, true);
  const d = est.tareas.dedalo;
  if (!d.activo && d.resultados && d.resultados.length && avisoDedalo !== d.resultados.length + d.proveedor) {
    avisoDedalo = d.resultados.length + d.proveedor;
    const ok = d.resultados.filter(x => x.verificado).length;
    decir(`DÉDALO (${d.proveedor}) PARCHÓ ${ok}/${d.resultados.length} MUROS · TALOS LOS VERIFICÓ SIN IA`, ok < d.resultados.length);
  }
  pintar();
}

async function arrancar() {
  const m = location.hash.match(/clave=([\w-]+)/);
  if (m) { clave = m[1]; guardar('dedalo.panel', clave); history.replaceState(null, '', location.pathname); } else clave = leer('dedalo.panel') || '';
  cv = $('lienzo'); ctx = cv.getContext('2d'); medir();
  if (window.ResizeObserver) new ResizeObserver(medir).observe(cv); else window.addEventListener('resize', medir);
  requestAnimationFrame(cuadro);
  $('m-correr').addEventListener('click', async () => {
    const r = await api('/panel/minotauro', { proveedor: $('m-proveedor').value, pasos: 25 });
    decir(r.ok ? 'EL MINOTAURO ENTRA CON LA CUENTA DEL CONTRATISTA' : 'NO ARRANCÓ: ' + (r.datos.error || r.estado), !r.ok);
  });
  $('d-correr').addEventListener('click', async () => {
    const r = await api('/panel/dedalo', { proveedor: $('d-proveedor').value });
    decir(r.ok ? 'DÉDALO LEE LOS SEIS MUROS Y PROPONE PARCHES · TALOS LOS PRUEBA' : 'NO ARRANCÓ: ' + (r.datos.error || r.estado), !r.ok);
  });
  $('cuenta').addEventListener('click', () => {
    if (!est) return;
    $('portal').contentWindow.postMessage(Object.assign({ tipo: 'cuenta' }, est.cuenta_atacante), location.origin);
    decir('CUENTA DEL CONTRATISTA EN EL LOGIN · ATACA A MANO DESDE LA FACHADA', false);
  });
  $('nuevo').addEventListener('click', async () => {
    const r = await api('/panel/nuevo', {});
    if (r.ok) { desde = 0; $('portal').src = '/portal'; decir('EPISODIO NUEVO · LA ORGANIZACIÓN SE VOLVIÓ A SEMBRAR', false); }
    else decir('NO SE PUDO: ' + (r.datos.error || r.estado), true);
  });
  $('h-cerrar').addEventListener('click', () => { $('hoja').hidden = true; });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') $('hoja').hidden = true; });
  if (!clave) { decir('SIN CLAVE · ABRE LA DIRECCIÓN QUE IMPRIMIÓ EL PANEL', true); return; }
  decir('CNOSOS INGENIERÍA EN LÍNEA · NADA HA PASADO', false);
  await sondear();
  setInterval(() => { if (!document.hidden) sondear(); }, 700);
}
arrancar();
})();
