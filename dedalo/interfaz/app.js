// El mando: pide a la consola, pinta el parte y le pasa cada solicitud a la escena.
// Nada de lo que llega se inserta como HTML: todo va por textContent.
(function () {
'use strict';
const T = window.TEXTOS, G = window.GLIFOS, C = G.colores;
const $ = id => document.getElementById(id);
const pon = (s, o) => s.replace(/\{(\w+)\}/g, (_, k) => (o[k] == null ? '' : o[k]));
const MODOS = ['control', 'static', 'maze'], ROLES = ['visitor', 'alice'];

let clave = '', est = null, rol = 'visitor', via = { tipo: 'sesion' }, ultima = null, ocupado = false;
let guion = false, sonido = true, inicio = Date.now(), audio = null, escribe = 0, firma = '';

function el(tag, clase, texto) { const n = document.createElement(tag); if (clase) n.className = clase; if (texto != null) n.textContent = texto; return n; }
function vaciar(n) { while (n.firstChild) n.removeChild(n.firstChild); }
function guardar(k, v) { try { sessionStorage.setItem(k, v); } catch (e) { /* sin almacenamiento: vive en memoria */ } }
function leer(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }

// ---- la consola
async function api(ruta, cuerpo) {
  const corte = new AbortController(), reloj = setTimeout(() => corte.abort(), 6000);
  try {
    const cab = { 'X-Consola-Clave': clave };
    if (cuerpo) cab['Content-Type'] = 'application/json';
    const r = await fetch(ruta, { method: cuerpo ? 'POST' : 'GET', headers: cab, body: cuerpo ? JSON.stringify(cuerpo) : undefined, signal: corte.signal, cache: 'no-store' });
    return { ok: r.ok, estado: r.status, datos: await r.json() };
  } catch (e) {
    return { ok: false, estado: 0, datos: { error: 'sin_senal' } };
  } finally { clearTimeout(reloj); }
}

// ---- la voz: una línea, escrita letra a letra. Rosa solo si es un evento.
function decir(texto, evento) {
  const v = $('voz'), turno = ++escribe;
  v.classList.toggle('evento', !!evento);
  let i = 0;
  (function paso() {
    if (turno !== escribe) return;
    i = Math.min(texto.length, i + 3);
    v.textContent = texto.slice(0, i);
    if (i < texto.length) setTimeout(paso, 16);
  })();
}
function narrar(e) {
  const datos = { actor: T.actores[e.actor], e: e.evento, afectado: T.actores[e.afectado] || '' };
  if (e.fuga) return decir(T.voz.fuga, true);
  const s = est.senuelos.find(d => d.ref === e.senuelo), caida = e.afectado && est.sesiones[e.afectado].evento === e.evento;
  const primero = s && s.primer_evento === e.evento;
  if (e.accion && T.voz.accion[e.accion] && (caida || (primero && e.accion !== 'revoked'))) return decir(pon(T.voz.accion[e.accion], datos), true);
  decir(pon(T.voz.motivo[e.motivo] || '', datos), e.motivo === 'decoy_budget' || e.motivo === 'revoked');
}

// ---- el sonido: lo que cambia, suena (poco)
function tono(f, d, tipo, vol, cuando) {
  if (!sonido) return;
  try {
    audio = audio || new (window.AudioContext || window.webkitAudioContext)();
    const t = audio.currentTime + (cuando || 0), o = audio.createOscillator(), g = audio.createGain();
    o.type = tipo || 'square'; o.frequency.setValueAtTime(f, t);
    g.gain.setValueAtTime(vol || 0.03, t); g.gain.exponentialRampToValueAtTime(0.0001, t + d);
    o.connect(g); g.connect(audio.destination); o.start(t); o.stop(t + d + 0.02);
  } catch (e) { /* sin audio */ }
}
function sonar(e) {
  tono(520, 0.05);
  if (e.accion === 'revoked' && est.sesiones[e.afectado] && est.sesiones[e.afectado].evento === e.evento) { tono(330, 0.18, 'sawtooth', 0.05, 0.45); tono(165, 0.4, 'sawtooth', 0.05, 0.62); }
  else tono(e.estado < 300 ? 880 : 196, 0.09, 'square', 0.03, 0.5);
}

// ---- pedir
async function refrescar() {
  const r = await api('/consola/estado');
  if (!r.ok) { decir(r.estado === 403 ? T.voz.sinClave : T.voz.sinSenal, true); return false; }
  if (!est || est.episodio !== r.datos.episodio) inicio = Date.now();
  est = r.datos;
  return true;
}

async function pedir(ruta, v, actor) {
  if (ocupado || !clave) return null;
  if (G.saltar()) { /* la portada cede el paso */ }
  ocupado = true;
  v = v || via; actor = actor || rol;
  const r = await api('/consola/pedir', { actor, via: v.tipo, de: v.de, ruta });
  if (!r.ok) {
    ocupado = false;
    const err = r.datos.error;
    decir(err === 'sin_senuelo' ? T.voz.sinSenuelo : err === 'ruta' ? T.voz.rutaMala : r.estado === 403 ? T.voz.sinClave : T.voz.sinSenal, true);
    tono(120, 0.2, 'sawtooth', 0.04);
    return null;
  }
  ultima = r.datos;
  await refrescar();
  ocupado = false;
  G.entrada(r.datos.entrada, est);
  narrar(r.datos.entrada); sonar(r.datos.entrada); pintar();
  return r.datos;
}

async function operar(cuerpo, frase) {
  if (ocupado || !clave) return;
  ocupado = true;
  const antes = est && est.episodio, r = await api('/consola/operar', cuerpo);
  ocupado = false;
  if (!r.ok) { decir(r.estado === 403 ? T.voz.sinClave : T.voz.sinSenal, true); return; }
  est = r.datos;
  if (est.episodio !== antes) { inicio = Date.now(); ultima = null; via = { tipo: 'sesion' }; frase = pon(T.voz.inicio, { id: est.episodio }); }
  G.poner(est); tono(660, 0.06); tono(990, 0.08, 'square', 0.03, 0.07);
  if (frase) decir(frase, false);
  pintar();
}
const reiniciar = extra => operar(Object.assign({ accion: 'reiniciar' }, extra || {}));

// ---- el guion de tres minutos: un cliente fijo que sigue cada pista. No es un modelo.
const espera = ms => new Promise(r => setTimeout(r, ms));
async function correrGuion() {
  if (guion) { guion = false; pintar(); return; }
  guion = true;
  await reiniciar(); pintar(); await espera(500);
  decir(T.voz.guion, false); await espera(1300);
  const paso = async (actor, v, ruta) => { if (!guion) return null; fijarRol(actor === 'alice' ? 'alice' : 'visitor', true); const r = await pedir(ruta, v, actor); await espera(1500); return r; };
  await paso('alice', { tipo: 'sesion' }, '/api/documents/alice-note');
  await paso('visitor', { tipo: 'sesion' }, '/api/documents/alice-note');
  const m = await paso('visitor', { tipo: 'sesion' }, '/api/maintenance');
  let sigue = m && m.cuerpo.entry;
  for (let i = 0; guion && sigue && i < est.limites.pasos + 1; i++) {
    const r = await paso('visitor', { tipo: 'senuelo', de: 'visitor' }, sigue);
    sigue = r && r.estado === 200 ? r.cuerpo.next : null;
  }
  await paso('visitor', { tipo: 'sesion' }, '/api/documents/visitor-note');
  await paso('alice', { tipo: 'sesion' }, '/api/documents/alice-note');
  fijarRol('visitor', true);
  guion = false; pintar();
}

// ---- pintar el parte y el mando
function fijarRol(r, callado) {
  rol = r; via = { tipo: 'sesion' };
  document.documentElement.style.setProperty('--ac', C[r]);
  G.rol(r);
  if (!callado) { tono(700, 0.05); pintar(); }
}

function pildora(texto, alPulsar, clase) {
  const b = el('button', 'pildora' + (clase ? ' ' + clase : ''), texto);
  b.type = 'button'; b.dataset.k = clase || texto; b.addEventListener('click', alPulsar);
  return b;
}

function pintar() {
  if (!est) return;
  // solo se rehace si algo cambió: así el sondeo no le quita el foco a quien está usando un botón
  const f = JSON.stringify([est, rol, via, ultima && ultima.entrada.n, guion], (k, v) => (k === 'edad' ? undefined : k === 'seconds_left' ? Math.ceil(v / 5) : v));
  if (f === firma) return;
  firma = f;
  // quien usa el teclado no pierde su sitio cuando los botones se rehacen
  const activo = document.activeElement, foco = activo && activo.dataset && activo.dataset.k && activo.closest('.mando, .info') ? activo.dataset.k : null;
  // arriba
  const nav = $('modos'); vaciar(nav);
  MODOS.forEach(m => { const b = el('button', '', T.modos[m]); b.type = 'button'; b.setAttribute('aria-current', String(est.modo === m)); b.title = T.modoLargo[m]; b.addEventListener('click', () => reiniciar({ mode: m })); nav.appendChild(b); });
  const rb = $('respuesta'); rb.textContent = T.respuestas[est.respuesta]; rb.dataset.r = est.respuesta; rb.title = T.respuestaLarga[est.respuesta];
  $('episodio').textContent = pon(T.parte.episodio, { id: est.episodio });

  // el parte
  const usos = est.senuelos.reduce((n, s) => n + s.servidas + s.rechazadas, 0);
  $('p-sub').textContent = T.modoLargo[est.modo];
  $('p-cifra').textContent = String(usos);
  $('p-unidad').textContent = T.parte.unidad;
  const caido = Object.keys(est.sesiones).find(a => est.sesiones[a].revocada);
  const ultAccion = est.senuelos.length ? est.senuelos[est.senuelos.length - 1].accion : null;
  $('p-titular').textContent = est.modo === 'control' ? T.parte.titular.t0 : !usos ? T.parte.titular.nada
    : caido ? pon(T.parte.titular.caida, { quien: T.actores[caido], e: est.sesiones[caido].evento })
    : ultAccion === 'audit_acknowledged' ? T.parte.titular.auditado : T.parte.titular.anotado;
  $('p-pie').textContent = (est.modo === 'control' ? '' : T.respuestas[est.respuesta] + ': ' + T.respuestaLarga[est.respuesta] + ' · ') + T.parte.pie;
  const m = $('p-marcador'); m.textContent = est.cuenta.fugas ? T.parte.marcadorSi : T.parte.marcadorNo; m.classList.toggle('mal', est.cuenta.fugas > 0);
  $('p-marcador-pie').textContent = pon(T.parte.marcadorPie, { f: est.cuenta.fugas, n: est.cuenta.pedidos });

  // sesiones, con lo único que puede hacer el operador
  const ul = $('sesiones'); vaciar(ul);
  Object.keys(T.actores).forEach(a => {
    const s = est.sesiones[a], li = el('li', s.revocada ? 'caida' : '');
    li.style.setProperty('--c', s.revocada ? C.aurora : C[a]);
    li.appendChild(el('b', '', T.actores[a]));
    li.appendChild(el('span', '', s.revocada ? pon(T.parte.revocada, { e: s.evento })
      : s.ventana ? pon(T.parte.ventana, { u: s.ventana.hits_left, s: Math.ceil(s.ventana.seconds_left) })
      : s.marcada ? T.parte.marcada : T.parte.activa));
    if (s.revocada) li.appendChild(pildora(T.parte.restaurar, () => operar({ accion: 'restaurar', actor: a }, pon(T.voz.restaurada, { actor: T.actores[a] }))));
    else if (!s.ventana) li.appendChild(pildora(T.parte.abrirVentana, () => operar({ accion: 'ventana', actor: a }, pon(T.voz.ventana, { actor: T.actores[a] }))));
    ul.appendChild(li);
  });

  // el registro: lo último primero
  const ol = $('registro'); vaciar(ol);
  const ult = est.libro.slice(window.innerHeight >= 900 ? -8 : -5).reverse();
  ult.forEach(e => {
    const li = el('li', e.estado < 300 ? '' : 'no');
    li.style.setProperty('--c', e.via === 'senuelo' ? C.azogue : C[e.actor]);
    li.appendChild(el('span', 'n', '#' + e.n));
    li.appendChild(el('span', 'quien', e.via === 'senuelo' ? e.senuelo || 'token' : T.actores[e.actor]));
    li.appendChild(el('span', '', e.ruta));
    li.appendChild(el('span', 'st', String(e.estado)));
    // el evento se anota una vez: en la solicitud que tumbó la sesión, o en cada uso que gasta una ventana
    const s = est.senuelos.find(d => d.ref === e.senuelo), cayo = e.accion === 'revoked' && e.afectado && est.sesiones[e.afectado].evento === e.evento;
    if (cayo || e.accion === 'audit_acknowledged' || (e.accion === 'observed' && s && s.primer_evento === e.evento)) li.appendChild(el('span', 'ev', pon(T.voz.accion[e.accion], { e: e.evento, afectado: T.actores[e.afectado] })));
    ol.appendChild(li);
  });
  $('r-pie').textContent = pon(T.parte.registroPie, { n: ult.length, t: est.cuenta.pedidos });

  // la respuesta, tal como llegó (los tokens, tachados)
  const eco = $('eco'); vaciar(eco);
  if (ultima) { eco.appendChild(el('b', ultima.estado < 300 ? '' : 'no', String(ultima.estado))); eco.appendChild(document.createTextNode(JSON.stringify(ultima.cuerpo))); }
  else eco.textContent = T.parte.respuestaVacia;

  // el mando
  const roles = $('roles'); vaciar(roles);
  ROLES.forEach(r => { const b = pildora(T.roles[r], () => fijarRol(r)); b.style.setProperty('--c', C[r]); b.setAttribute('aria-pressed', String(rol === r)); roles.appendChild(b); });
  $('m-rol').textContent = T.rolLargo[rol];
  const vias = $('vias'); vaciar(vias);
  const opciones = [[T.mando.miSesion, { tipo: 'sesion' }, C[rol]]];
  Object.keys(est.hallados).forEach(de => opciones.push([pon(de === rol ? T.mando.senuelo : T.mando.filtrado, { ref: est.hallados[de].toUpperCase(), de: T.actores[de] }), { tipo: 'senuelo', de }, C.azogue]));
  if (via.tipo === 'senuelo' && !est.hallados[via.de]) via = { tipo: 'sesion' };
  opciones.forEach(([texto, v, color]) => {
    const b = pildora(texto, () => { via = v; pintar(); }); b.style.setProperty('--c', color);
    b.setAttribute('aria-pressed', String(via.tipo === v.tipo && via.de === v.de)); vias.appendChild(b);
  });
  const dock = $('dock'); vaciar(dock);
  T.mando.rapidas[rol].forEach(([texto, ruta]) => dock.appendChild(pildora(texto, () => pedir(ruta, { tipo: 'sesion' }))));
  if (est.hallados[rol]) dock.appendChild(pildora(T.mando.entrar, () => pedir('/archive', { tipo: 'senuelo', de: rol }), 'entra'));
  const sig = ultima && ultima.estado === 200 && typeof ultima.cuerpo.next === 'string' ? ultima.cuerpo.next : null;
  if (sig) dock.appendChild(pildora(T.mando.seguir + ' → ' + sig, () => pedir(sig, { tipo: ultima.entrada.via, de: ultima.entrada.de }), 'sigue'));
  dock.appendChild(el('span', 'hueco'));
  const bg = pildora(guion ? T.mando.parar : T.mando.guion, correrGuion); bg.setAttribute('aria-pressed', String(guion)); bg.title = T.mando.guionPie; dock.appendChild(bg);
  dock.appendChild(pildora(T.mando.deNuevo, () => reiniciar()));
  if (foco) { const b = Array.from(document.querySelectorAll('.mando .pildora, .info .pildora')).find(x => x.dataset.k === foco); if (b) b.focus(); }
}

function reloj() {
  const s = Math.floor((Date.now() - inicio) / 1000);
  $('reloj').textContent = est ? String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0') : T.sinTiempo;
}

function ayuda(abrir) {
  $('ayuda').hidden = !abrir;
  if (abrir) $('a-cerrar').focus(); else $('ayuda-b').focus();
}

function fijos() {
  $('marca').textContent = T.marca; $('lema').textContent = T.lema;
  $('p-titulo').textContent = T.parte.titulo; $('s-titulo').textContent = T.parte.sesiones;
  $('r-titulo').textContent = T.parte.registro;
  $('m-eres').textContent = T.mando.eres; $('m-con').textContent = T.mando.con; $('enviar').textContent = T.mando.enviar;
  $('escala').textContent = T.escena.escala;
  $('lienzo').setAttribute('aria-label', T.escena.escala);
  $('a-titulo').textContent = T.ayuda.titulo; $('a-limites').textContent = T.ayuda.limites;
  $('a-teclas').textContent = T.ayuda.teclas; $('a-teclas-cuerpo').textContent = T.ayuda.teclasCuerpo; $('a-cerrar').textContent = T.ayuda.cerrar;
  T.ayuda.cuerpo.forEach(p => $('a-cuerpo').appendChild(el('p', '', p)));
  T.ayuda.limitesCuerpo.forEach(p => $('a-limites-cuerpo').appendChild(el('p', '', p)));
  $('son').title = T.sonido;
}

async function arrancar() {
  fijos();
  const m = location.hash.match(/clave=([\w-]+)/);
  if (m) { clave = m[1]; guardar('dedalo.clave', clave); history.replaceState(null, '', location.pathname + location.search); }
  else clave = leer('dedalo.clave') || '';
  sonido = leer('dedalo.sonido') !== 'no'; $('son').setAttribute('aria-pressed', String(sonido));
  document.documentElement.style.setProperty('--ac', C[rol]);

  G.iniciar($('lienzo'), obj => {
    if (obj.tipo === 'rol') return fijarRol(obj.actor);
    if (obj.via === 'senuelo') { const de = via.tipo === 'senuelo' ? via.de : est.hallados[rol] ? rol : Object.keys(est.hallados)[0] || rol; return pedir(obj.ruta, { tipo: 'senuelo', de }); }
    pedir(obj.ruta, { tipo: 'sesion' });
  });
  $('linea').addEventListener('submit', ev => { ev.preventDefault(); pedir($('ruta').value.trim()); });
  $('respuesta').addEventListener('click', () => est && reiniciar({ response: est.respuesta === 'enforce' ? 'observe' : 'enforce' }));
  $('son').addEventListener('click', () => { sonido = !sonido; guardar('dedalo.sonido', sonido ? 'si' : 'no'); $('son').setAttribute('aria-pressed', String(sonido)); tono(700, 0.05); });
  $('ayuda-b').addEventListener('click', () => ayuda(true));
  $('a-cerrar').addEventListener('click', () => ayuda(false));
  document.addEventListener('keydown', ev => {
    if (G.saltar()) return;
    if (ev.key === 'Escape') { if (!$('ayuda').hidden) ayuda(false); else if (document.activeElement) document.activeElement.blur(); return; }
    if (ev.target && ev.target.tagName === 'INPUT') return;
    if (ev.ctrlKey || ev.metaKey || ev.altKey || !est) return;
    const k = ev.key.toLowerCase();
    if (k === 'g') correrGuion();
    else if (k === 'n') reiniciar();
    else if (k === 'm') $('son').click();
    else if (k === '?') ayuda($('ayuda').hidden);
    else if (k === '1' || k === '2' || k === '3') reiniciar({ mode: MODOS[Number(k) - 1] });
    else if (k === '/') { ev.preventDefault(); $('ruta').focus(); }
  });

  if (!clave) { decir(T.voz.sinClave, true); return; }
  if (document.fonts && document.fonts.load) { try { await Promise.race([document.fonts.load('40px "VT323"'), espera(1200)]); } catch (e) { /* letra de respaldo */ } }
  if (!(await refrescar())) return;
  if (!/[?&]portada=no/.test(location.search)) G.portada();
  G.poner(est); pintar(); reloj();
  decir(pon(T.voz.inicio, { id: est.episodio }), false);
  setInterval(reloj, 500);
  // el estado se vuelve a leer para que la vigencia y las ventanas no envejezcan en pantalla
  setInterval(async () => { if (ocupado || document.hidden) return; if (await refrescar()) { G.poner(est); pintar(); } }, 2500);
}
arrancar();
})();
