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
// Una cuenta = un nodo, aunque haya iniciado sesión muchas veces. Así la columna no se llena de copias.
const MAX_CUENTAS = 6;
function cuentas() {
  const g = new Map();
  (est ? est.sesiones : []).filter(s => !s.laberinto).forEach(s => {
    const c = g.get(s.usuario) || { usuario: s.usuario, rol: s.rol, refs: [], cortadas: 0, vivas: 0 };
    c.refs.push(s.ref); if (s.revocada) c.cortadas++; else c.vivas++;
    g.set(s.usuario, c);
  });
  return [...g.values()];
}
function posSesion(ref) {
  const cs = cuentas().slice(0, MAX_CUENTAS);
  const i = Math.max(0, cs.findIndex(c => c.refs.includes(ref)));
  const n = Math.max(1, cs.length);
  return [W * 0.075, H * (0.18 + 0.64 * (n === 1 ? 0.5 : i / (n - 1)))];
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
  const cs = cuentas();
  cs.slice(0, MAX_CUENTAS).forEach(c => {
    const [x, y] = posSesion(c.refs[0]), caida = c.vivas === 0;
    for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2 + (caida || quieto ? 0 : ahora * 0.0004); txt(i < 12 * c.cortadas / c.refs.length ? '×' : '·', x + Math.cos(a) * 14, y + Math.sin(a) * 14, caida ? C.aurora : C.ambar, `11px ${MONO}`, 'center', 0.8); }
    txt(c.usuario, x, y + 26, caida ? C.aurora : C.tiza, `14px ${PIX}`);
    const pie = c.cortadas ? `${c.cortadas} DE ${c.refs.length} CORTADA${c.refs.length > 1 ? 'S' : ''}` : c.rol.toUpperCase();
    txt(pie, x, y + 39, c.cortadas ? C.aurora : C.regolito, `9.5px ${MONO}`);
  });
  if (cs.length > MAX_CUENTAS) txt(`+${cs.length - MAX_CUENTAS} CUENTAS MÁS`, W * 0.07, H * 0.95, C.regolito, `9.5px ${MONO}`);
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

// Etiquetas cortas para que quepan en la línea; la descripción completa queda en el título (al pasar el ratón).
const CORTO = { idor: 'IDOR', inyeccion_sql: 'INYECCIÓN SQL', recorrido: 'RECORRIDO DE RUTA', escalada: 'ESCALADA',
  manipulacion_rol: 'ROL MANIPULADO', fuerza_bruta: 'FUERZA BRUTA', exposicion_config: 'CONFIG EXPUESTA', token_forjado: 'TOKEN FORJADO' };
function lineaHilo(e) {
  const li = el('li'), nombres = (est && est.nombres_intento) || {};
  li.className = 'ev';
  [[String(e.n), 'n'], [e.usuario || 'anónimo', 'u'], [e.metodo, 'm'], [e.ruta, 'r'], [String(e.estado), 'e']].forEach(([t, k]) => li.appendChild(el('span', t, k)));
  const marca = el('span', null, 'marca');
  if (e.intento) { marca.appendChild(el('span', CORTO[e.intento] || e.intento, 'int')); li.classList.add('t-int'); }
  if (e.accion === 'icaro') { marca.appendChild(el('span', `ÍCARO corta ${e.afectada}`, 'icaro')); li.classList.add('t-int', 't-lab'); }
  else if (e.accion === 'trepa') { marca.appendChild(el('span', `trepa → nivel ${e.nivel}`, 'lab')); li.classList.add('t-lab'); }
  else if (e.laberinto) { marca.appendChild(el('span', `laberinto ${e.nivel}`, 'lab')); li.classList.add('t-lab'); }
  if (e.fuga) { marca.appendChild(el('span', 'SECRETO FILTRADO', 'icaro')); li.classList.add('t-int'); }
  li.appendChild(marca);
  li.title = `#${e.n} · ${e.usuario || 'anónimo'} (${e.rol || '—'}) · ${e.metodo} ${e.ruta} → ${e.estado}` +
    (e.intento ? ` · ${nombres[e.intento] || e.intento}` : '') + (e.laberinto ? ` · laberinto nivel ${e.nivel}` : '') +
    (e.accion === 'icaro' ? ` · Ícaro cortó la sesión ${e.afectada}` : '');
  return li;
}

// Avisos del sistema (resúmenes, errores): van al hilo para que no se pierdan cuando la voz cambia.
function nota(texto) {
  const li = el('li', '▸ ' + new Date().toLocaleTimeString('es-CO', { hour12: false }) + ' · ' + texto, 't-nota');
  agregarAlHilo([li]);
}
let sinLeer = 0;
function alFondo() { const h = $('hilo'); return h.scrollHeight - h.scrollTop - h.clientHeight < 40; }
function agregarAlHilo(lis) {
  if (!lis.length) return;
  const h = $('hilo'), pegado = alFondo();
  lis.forEach(li => h.appendChild(li));
  while (h.children.length > 1500) h.removeChild(h.firstChild);
  if (pegado) { h.scrollTop = h.scrollHeight; sinLeer = 0; } else sinLeer += lis.length;
  const b = $('hilo-abajo'); b.hidden = sinLeer === 0; b.textContent = `↓ ${sinLeer} NUEVAS`;
}

// ---------------------------------------------------------------- el parte
function pintar() {
  if (!est) return;
  const a = $('almacen'); a.textContent = 'ALMACÉN ' + est.almacen.toUpperCase(); a.classList.toggle('oracle', est.almacen === 'oracle');
  $('episodio').textContent = 'EPISODIO ' + est.episodio;
  const intentos = est.sesiones.reduce((t, s) => t + Object.values(s.intentos).reduce((x, y) => x + y, 0), 0);
  const icaros = est.sesiones.filter(s => s.revocada).length;
  const m = est.tareas.minotauro, d = est.tareas.dedalo;
  const conModelo = m.proveedor && m.proveedor !== 'guion';
  const tokLab = m.resumen ? m.resumen.tokens_atacante_en_laberinto : 0;
  const cifras = [[est.eventos, 'solicitudes', 'a Cnosos', ''],
    [intentos, 'intentos', 'detectados', intentos ? 'mal' : ''],
    [icaros, 'sesiones cortadas', 'por Ícaro', icaros ? 'mal' : ''],
    [est.laberinto.pasos, 'pasos en laberinto', `nivel ${est.laberinto.nivel_max}`, 'hilo'],
    [conModelo ? est.tokens_atacante : '—', 'tokens atacante', conModelo ? `${tokLab} en el laberinto` : (m.proveedor ? 'guion: sin modelo' : 'aún no ataca'), 'hilo'],
    [est.laberinto.costo_ms.toFixed(2) + ' ms', 'nuestro costo', 'CPU · 0 tokens', 'ok'],
    [est.fugas, 'secretos fuera', est.fugas ? 'la defensa falló' : 'ninguno', est.fugas ? 'mal' : 'ok']];
  const c = $('cifras'); vaciar(c);
  cifras.forEach(([v, t, sub, k]) => { const x = el('div', null, 'cifra ' + k); x.appendChild(el('b', String(v))); x.appendChild(el('span', t)); x.appendChild(el('small', sub)); c.appendChild(x); });
  opciones(est.proveedores || {});
  pintarStats(est.estadisticas || []);
  $('m-correr').disabled = !!m.activo; $('m-correr').textContent = m.activo ? 'ATACANDO…' : 'ATACAR';
  $('d-correr').disabled = !!d.activo; $('d-correr').textContent = d.activo ? 'PARCHANDO…' : 'PARCHAR MUROS';
  const firmaM = JSON.stringify([d.resultados || [], Object.keys(est.casos)]);
  if (firmaM === firmaMuros) return;
  firmaMuros = firmaM;
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

// Los selectores muestran solo modelos con llave puesta en la terminal; por defecto Gemini ataca y Groq defiende.
let opcionesListas = '';
function opciones(prov) {
  const firma = JSON.stringify(prov);
  if (firma === opcionesListas) return;
  opcionesListas = firma;
  [['m-proveedor', ['gemini', 'groq', 'grok', 'openai']], ['d-proveedor', ['groq', 'gemini', 'openai', 'grok']]].forEach(([id, pref]) => {
    const s = $(id), antes = s.value; vaciar(s);
    s.appendChild(el('option', 'guion (sin red)')).value = 'guion';
    Object.keys(prov).forEach(p => { const o = el('option', prov[p] ? p : `${p} (sin llave)`); o.value = p; o.disabled = !prov[p]; s.appendChild(o); });
    const elegido = antes !== 'guion' && prov[antes] ? antes : (pref.find(p => prov[p]) || 'guion');
    s.value = elegido;
  });
}

function wilsonJS(k, n) {
  if (!n) return null;
  const z = 1.96, p = k / n, c = (p + z * z / (2 * n)) / (1 + z * z / n), m = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n);
  return [Math.max(0, c - m), Math.min(1, c + m)];
}
const pct = x => Math.round(x * 100) + ' %';
const miles = v => v == null ? '—' : Number(v).toLocaleString('es-CO');
function corto(m) { return String(m).replace(/^(groq|gemini|xai|openai|anthropic):(models\/)?/, '').replace(/^openai\//, ''); }

// LAS CIFRAS: tres fuentes, de la más robusta a la más viva. Todo sale de la base (Oracle o SQLite).
let firmaStats = '', firmaMuros = '';
function pintarStats(filas) {
  const x = est.experimentos || {}, t = x.titulares;
  const firma = JSON.stringify([filas, t, x.vectores, x.estado]);
  if (firma === firmaStats) return;            // sin cambios: no se redibuja (así no se pierde el scroll)
  firmaStats = firma;
  const caja = $('stats'); vaciar(caja);
  caja.appendChild(el('div', 'MODELOS REALES CONTRA EL SEÑUELO', 'seccion'));
  if (t && t.episodios) {
    const ic = wilsonJS(t.cebo[0], t.cebo[1]);
    const g = el('div', null, 'titulares');
    [[`${t.cebo[0]}/${t.cebo[1]}`, 'mordieron el cebo' + (ic ? ` · IC ${pct(ic[0])}–${pct(ic[1])}` : ''), 'hilo'],
     [`${t.control[0]}/${t.control[1]}`, 'sin cebo (control)', ''],
     [miles(t.tokens_tras_morder), 'tokens del atacante tras morder', 'hilo'],
     [t.defensa_ms + ' ms', 'nuestro costo · 0 tokens', 'ok'],
     [t.fugas, 'secretos fuera', t.fugas ? 'mal' : 'ok']].forEach(([v, r, k]) => {
      const d = el('div', null, k); d.appendChild(el('b', String(v))); d.appendChild(el('span', r)); g.appendChild(d);
    });
    caja.appendChild(g);
    caja.appendChild(el('p', `${t.concluyentes} episodios concluyentes de ${t.episodios} · ${t.modelos} modelos · los inconclusos (cuota, red) no cuentan · guardado en ${x.almacen || est.almacen}`, 'pie'));
    const b = el('button', 'VER TABLA COMPLETA', 'pildora ver'); b.type = 'button'; b.addEventListener('click', numeros); caja.appendChild(b);
  } else caja.appendChild(el('p', x.estado === 'publicando' ? 'Publicando los resultados en la base…' : (x.estado || 'Sin resultados de modelos todavía.'), 'pie'));

  caja.appendChild(el('div', 'VECTORES MITRE (CYBERSECEVAL)', 'seccion'));
  const vs = x.vectores || [];
  if (vs.length) {
    const niveles = [...new Set(vs.map(v => v.nivel))], des = ['contenido', 'detectado', 'prevenido', 'no_cubierto'];
    const tb = el('table'), cab = el('tr');
    ['nivel', 'contenido', 'detectado', 'prevenido', 'no cubierto'].forEach(h => cab.appendChild(el('th', h))); tb.appendChild(cab);
    niveles.forEach(n => {
      const tr = el('tr'); tr.appendChild(el('td', n));
      des.forEach(d => { const v = vs.find(z => z.nivel === n && z.desenlace === d); const k = v ? v.vectores : 0;
        tr.appendChild(el('td', k ? `${k} (${v.casos} casos)` : '0', d === 'contenido' && k ? 'ok' : d === 'no_cubierto' && k ? 'mal' : '')); });
      tb.appendChild(tr);
    });
    caja.appendChild(tb);
    caja.appendChild(el('p', '10 vectores · 157 casos aplicables del conjunto MITRE · contenido = falló, quedó señal y se cortó la sesión', 'pie'));
  } else caja.appendChild(el('p', 'Sin vectores publicados.', 'pie'));

  caja.appendChild(el('div', 'EN VIVO · ATAQUES DE ESTE PANEL A CNOSOS', 'seccion'));
  if (!filas.length) { caja.appendChild(el('p', 'Cada ATACAR guarda una corrida en la tabla corridas.', 'pie')); return; }
  const tbl = el('table'), cab = el('tr');
  ['agente', 'modelo', 'n', 'detect.', 'paso', 'fuga', 'tokens (lab.)', 'costo'].forEach(h => cab.appendChild(el('th', h)));
  tbl.appendChild(cab);
  filas.forEach(f => {
    const tr = el('tr'), honesto = f.agente === 'teseo';
    const celdas = [[f.agente], [corto(f.modelo)], [f.n], [`${f.detectadas}/${f.n}${honesto ? ' falso +' : ''}`, honesto ? (f.detectadas ? 'mal' : 'ok') : (f.detectadas ? 'ok' : 'mal')],
      [f.paso_mediano == null ? '—' : f.paso_mediano], [f.fugas, f.fugas ? 'mal' : 'ok'], [`${f.tokens} (${f.tokens_laberinto})`, 'hilo'], [f.costo_ms.toFixed(2) + ' ms', 'ok']];
    celdas.forEach(([v, k]) => tr.appendChild(el('td', String(v), k || '')));
    tbl.appendChild(tr);
  });
  caja.appendChild(tbl);
}

function numeros() {
  const x = est.experimentos || {}, caja = $('n-tabla'); vaciar(caja);
  $('n-nota').textContent = 'k/n sobre episodios concluyentes · IC de Wilson al 95 % · T0 no tiene señuelo (control) · ingenuo: nadie le avisa · advertido: se le dice que puede haber trampas · fuente: piloto con modelos (laboratorio DÉDALO) y batería (Cnosos)';
  const t = el('table'), cab = el('tr');
  ['modelo', 'nivel', 'condición', 'mordió', 'IC 95 %', 'revocada', 'pasos lab.', 'tokens', 'tras morder', 'defensa', 'fugas', 'inconclusos'].forEach(h => cab.appendChild(el('th', h)));
  t.appendChild(cab);
  const vacias = (x.tabla || []).filter(f => !f.concluyentes);
  (x.tabla || []).filter(f => f.concluyentes).forEach(f => {
    const tr = el('tr'), sin = f.nivel.startsWith('T0');
    [[corto(f.modelo)], [f.nivel], [f.condicion], [`${f.mordio}/${f.concluyentes}`, sin ? 'tenue' : f.mordio ? 'hilo' : ''],
     [f.ic ? `${Math.round(f.ic[0] * 100)}–${pct(f.ic[1])}` : '—', 'tenue'], [`${f.revocadas}`], [f.pasos_laberinto == null ? '—' : f.pasos_laberinto],
     [miles(f.tokens)], [miles(f.tokens_tras_morder), 'hilo'], [f.defensa_ms + ' ms', 'ok'], [f.fugas, f.fugas ? 'mal' : 'ok'],
     [f.n - f.concluyentes, f.n - f.concluyentes ? 'tenue' : '']].forEach(([v, k]) => tr.appendChild(el('td', String(v), k || '')));
    t.appendChild(tr);
  });
  caja.appendChild(t);
  if (vacias.length) caja.appendChild(el('p', `${vacias.length} grupos sin episodios concluyentes (${[...new Set(vacias.map(f => corto(f.modelo)))].join(', ')}: el proveedor no respondió, p. ej. sin cuota). No cuentan en ninguna tasa.`, 'nota-n'));
  $('numeros').hidden = false;
}

function hoja(r) {
  $('h-titulo').textContent = `${r.titulo} · ${r.cwe || '—'} (esperada ${r.cwe_esperada}) · ${r.intentos} intento(s)`;
  $('h-veredicto').textContent = `TALOS: ${r.veredicto}. ${r.explicacion || ''}`;
  $('h-antes').textContent = r.original; $('h-despues').textContent = r.parche || '(sin parche)';
  $('hoja').hidden = false;
}

let avisoMinotauro = null, avisoDedalo = 0, avisoError = null, pegada = false;
async function sondear() {
  if (!clave) return;
  const r = await api('/panel/estado?desde=' + desde);
  if (!r.ok) {
    if (r.estado === 403) {
      decir(pegada ? 'ESA CLAVE NO ES DE ESTE PANEL · ¿HAY OTRO PANEL ABIERTO EN OTRA VENTANA? CIÉRRALOS Y ARRANCA UNO SOLO' : 'ESTE NAVEGADOR TIENE UNA CLAVE VIEJA · PEGA LA DIRECCIÓN DE LA TERMINAL', true);
      $('pegar').hidden = false;
    }
    else if (r.estado === 0) decir('EL PANEL NO RESPONDE · ¿SE CERRÓ LA VENTANA DE POWERSHELL?', true);
    return;
  }
  $('pegar').hidden = true; pegada = false;
  if (episodio !== r.datos.episodio) {
    if (episodio) nota(`episodio nuevo ${r.datos.episodio} · la organización se volvió a sembrar`);
    const habia = desde; episodio = r.datos.episodio; eventos = []; viajes = []; desde = 0;
    if (habia > 0) return sondear();       // esta respuesta venía filtrada con el contador viejo: pedir de cero
  }
  est = r.datos;
  const ahora = performance.now(), lis = [];
  est.eventos_nuevos.forEach(e => { if (e.n > desde) { eventos.push(e); if (est.pendientes < 100) recibir(e, ahora, est.nombres_intento || {}); lis.push(lineaHilo(e)); desde = e.n; } });
  agregarAlHilo(lis);
  if (eventos.length > 2000) eventos = eventos.slice(-2000);
  if (est.pendientes > 0) setTimeout(sondear, 50);       // quedaron eventos: los traemos ya, sin saltarnos ninguno
  $('hilo-pie').textContent = `· ${est.eventos} solicitudes · guardadas en ${est.almacen}`;
  const m = est.tareas.minotauro;
  if (m.resumen && avisoMinotauro !== m.resumen.episodio + m.inicio) {
    avisoMinotauro = m.resumen.episodio + m.inicio;
    const s = m.resumen;
    const texto = `MINOTAURO (${s.modelo}) TERMINÓ · DETECTADO ${s.paso_deteccion ? 'EN EL PASO ' + s.paso_deteccion : 'NO'} · NIVEL ${s.nivel_max} · ${s.tokens_atacante_en_laberinto} TOKENS PERDIDOS EN EL LABERINTO`;
    decir(texto, !s.paso_deteccion);
    nota(`${texto.toLowerCase()} · ${s.pasos} pasos · final: ${(s.final || {}).motivo || '—'}${s.final && s.final.detalle ? ' · ' + s.final.detalle : ''}`);
  }
  if (m.error && avisoError !== m.error) { avisoError = m.error; decir('MINOTAURO: ' + m.error, true); nota('error del minotauro: ' + m.error); }
  const d = est.tareas.dedalo;
  if (!d.activo && d.resultados && d.resultados.length && avisoDedalo !== d.resultados.length + d.proveedor) {
    avisoDedalo = d.resultados.length + d.proveedor;
    const ok = d.resultados.filter(x => x.verificado).length;
    decir(`DÉDALO (${d.proveedor}) PARCHÓ ${ok}/${d.resultados.length} MUROS · TALOS LOS VERIFICÓ SIN IA`, ok < d.resultados.length);
    nota(`dédalo (${d.proveedor}) parchó ${ok}/${d.resultados.length} muros · ` + d.resultados.map(x => `${x.caso}: ${x.verificado ? 'verificado' : x.veredicto}`).join(' · '));
  }
  pintar();
}

async function arrancar() {
  const m = (location.search + location.hash).match(/clave=([\w-]+)/);
  if (m) { clave = m[1]; guardar('dedalo.panel', clave); history.replaceState(null, '', location.pathname); } else clave = leer('dedalo.panel') || '';
  cv = $('lienzo'); ctx = cv.getContext('2d'); medir();
  if (window.ResizeObserver) new ResizeObserver(medir).observe(cv); else window.addEventListener('resize', medir);
  requestAnimationFrame(cuadro);
  $('m-correr').addEventListener('click', async () => {
    const r = await api('/panel/minotauro', { proveedor: $('m-proveedor').value, pasos: 25 });
    decir(r.ok ? 'EL MINOTAURO ENTRA CON LA CUENTA DEL CONTRATISTA' : 'NO ARRANCÓ: ' + (r.datos.error || r.estado), !r.ok);
    nota(r.ok ? `minotauro ataca con ${$('m-proveedor').value}` : 'el minotauro no arrancó: ' + (r.datos.error || r.estado));
  });
  $('d-correr').addEventListener('click', async () => {
    const r = await api('/panel/dedalo', { proveedor: $('d-proveedor').value });
    decir(r.ok ? 'DÉDALO LEE LOS SEIS MUROS Y PROPONE PARCHES · TALOS LOS PRUEBA' : 'NO ARRANCÓ: ' + (r.datos.error || r.estado), !r.ok);
    nota(r.ok ? `dédalo parcha con ${$('d-proveedor').value}` : 'dédalo no arrancó: ' + (r.datos.error || r.estado));
  });
  $('cuenta').addEventListener('click', () => {
    if (!est) return;
    $('portal').contentWindow.postMessage(Object.assign({ tipo: 'cuenta' }, est.cuenta_atacante), location.origin);
    decir('CUENTA DEL CONTRATISTA EN EL LOGIN · ATACA A MANO DESDE LA FACHADA', false);
  });
  $('nuevo').addEventListener('click', async () => {
    const r = await api('/panel/nuevo', {});
    if (r.ok) { $('portal').src = '/portal'; decir('EPISODIO NUEVO · LA ORGANIZACIÓN SE VOLVIÓ A SEMBRAR', false); }
    else decir('NO SE PUDO: ' + (r.datos.error || r.estado), true);
  });
  $('h-cerrar').addEventListener('click', () => { $('hoja').hidden = true; });
  $('n-cerrar').addEventListener('click', () => { $('numeros').hidden = true; });
  $('filtros').addEventListener('click', ev => {
    const b = ev.target.closest('button'); if (!b) return;
    [...$('filtros').children].forEach(x => x.classList.toggle('activo', x === b));
    $('hilo').className = 'hilo' + (b.dataset.f ? ' f-' + b.dataset.f : '');
    $('hilo').scrollTop = $('hilo').scrollHeight;
  });
  $('hilo-abajo').addEventListener('click', () => { $('hilo').scrollTop = $('hilo').scrollHeight; });
  $('hilo').addEventListener('scroll', () => { if (alFondo()) { sinLeer = 0; $('hilo-abajo').hidden = true; } });
  document.querySelector('.pestanas').addEventListener('click', ev => {
    const b = ev.target.closest('button'); if (!b) return;
    [...b.parentNode.children].forEach(x => x.classList.toggle('activo', x === b));
    $('muros').hidden = b.dataset.p !== 'muros'; $('stats').hidden = b.dataset.p !== 'stats';
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') { $('hoja').hidden = true; $('numeros').hidden = true; } });
  $('pegar').addEventListener('submit', ev => {
    ev.preventDefault();
    const t = $('pegar-texto').value.trim(), k = (t.match(/clave=([\w-]+)/) || [null, t.match(/^[\w-]{16,}$/) ? t : ''])[1];
    if (!k) { decir('ESO NO TIENE CLAVE · COPIA LA LÍNEA «ABRE: …#clave=…» COMPLETA', true); return; }
    clave = k; pegada = true; guardar('dedalo.panel', clave); $('pegar-texto').value = ''; sondear();
  });
  setInterval(() => { if (!document.hidden) sondear(); }, 700);
  if (!clave) { decir('SIN CLAVE · PEGA LA DIRECCIÓN QUE IMPRIMIÓ LA TERMINAL', true); $('pegar').hidden = false; return; }
  decir('CNOSOS INGENIERÍA EN LÍNEA · NADA HA PASADO', false);
  await sondear();
}
arrancar();
})();
