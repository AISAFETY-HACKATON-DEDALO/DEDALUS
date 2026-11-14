// El portal de Cnosos. Un cliente normal de la API: lo que un empleado (o un intruso) ve y usa.
// Todo lo que llega del servidor se pinta con textContent: nada se interpreta como HTML.
(function () {
'use strict';
const $ = id => document.getElementById(id);
let token = null, vista = 'inicio';

function el(tag, texto, clase) { const n = document.createElement(tag); if (texto != null) n.textContent = texto; if (clase) n.className = clase; return n; }
function vaciar(n) { while (n.firstChild) n.removeChild(n.firstChild); }

async function api(metodo, ruta, cuerpo, cabeceras) {
  const cab = Object.assign({}, cabeceras || {});
  if (token && !Object.keys(cab).some(k => k.toLowerCase() === 'authorization')) cab.Authorization = 'Bearer ' + token;
  if (cuerpo !== undefined) cab['Content-Type'] = 'application/json';
  try {
    const r = await fetch(ruta, { method: metodo, headers: cab, body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined, cache: 'no-store' });
    let datos = {};
    try { datos = await r.json(); } catch (e) { /* sin cuerpo */ }
    if (r.status === 401 && datos.error === 'sesion_expirada' && !(cabeceras && cabeceras.Authorization)) expirada();
    return { estado: r.status, datos };
  } catch (e) {
    return { estado: 0, datos: { error: 'sin_conexion' } };
  }
}

function expirada() {
  token = null;
  $('vista-app').hidden = true; $('quien').hidden = true; $('vista-login').hidden = false;
  $('error-login').textContent = 'Su sesión ha expirado. Ingrese de nuevo.';
}

async function entrar(usuario, clave) {
  const r = await api('POST', '/api/login', { usuario, clave });
  if (r.estado === 200 && r.datos.token) {
    token = r.datos.token;
    $('error-login').textContent = '';
    $('vista-login').hidden = true; $('vista-app').hidden = false; $('quien').hidden = false;
    $('quien-nombre').textContent = (r.datos.nombre || usuario) + ' · ' + (r.datos.rol || '');
    mostrar('inicio');
  } else {
    $('error-login').textContent = r.estado === 429 ? 'Cuenta bloqueada temporalmente por intentos fallidos.' : 'Usuario o contraseña incorrectos.';
  }
}

function tablaArchivos(lista, alAbrir) {
  const t = el('table');
  const h = el('tr'); ['#', 'Título', 'Ruta', 'Nivel'].forEach(x => h.appendChild(el('th', x))); t.appendChild(h);
  lista.forEach(a => {
    const tr = el('tr', null, 'clic');
    tr.appendChild(el('td', String(a.id))); tr.appendChild(el('td', a.titulo)); tr.appendChild(el('td', a.ruta));
    const td = el('td'); td.appendChild(el('span', a.nivel, 'nivel ' + a.nivel)); tr.appendChild(td);
    tr.addEventListener('click', () => alAbrir(a.id));
    t.appendChild(tr);
  });
  return t;
}

async function abrirArchivo(id, destino) {
  const r = await api('GET', '/api/archivos/' + encodeURIComponent(id));
  vaciar(destino);
  if (r.estado === 200) { destino.appendChild(el('b', r.datos.titulo || ('Archivo ' + id))); destino.appendChild(el('div', r.datos.contenido, 'doc')); }
  else destino.appendChild(el('div', 'No se encontró el archivo o no tiene permiso.', 'aviso'));
}

async function mostrar(v) {
  vista = v;
  document.querySelectorAll('#pestanas button').forEach(b => b.classList.toggle('activa', b.dataset.v === v));
  const c = $('contenido'); vaciar(c);
  if (v === 'inicio') {
    const r = await api('GET', '/api/perfil');
    if (r.estado !== 200) return;
    c.appendChild(el('h2', 'Hola, ' + (r.datos.nombre || r.datos.usuario)));
    c.appendChild(el('p', [r.datos.cargo, r.datos.departamento, r.datos.organizacion].filter(Boolean).join(' · '), 'suave'));
    c.appendChild(el('p', 'Recuerde: no comparta credenciales y reporte a TI cualquier actividad sospechosa.'));
  } else if (v === 'archivos') {
    const r = await api('GET', '/api/archivos');
    c.appendChild(el('h2', 'Mis archivos'));
    const visor = el('div');
    if (r.estado === 200) c.appendChild(tablaArchivos(r.datos.archivos || [], id => abrirArchivo(id, visor)));
    const f = el('form', null, 'fila'); f.style.marginTop = '12px';
    const i = el('input'); i.placeholder = 'Abrir archivo por número'; f.appendChild(i);
    const b = el('button', 'Abrir', 'principal'); b.type = 'submit'; f.appendChild(b);
    f.addEventListener('submit', e => { e.preventDefault(); abrirArchivo(i.value.trim(), visor); });
    c.appendChild(f);
    const f2 = el('form', null, 'fila'); f2.style.marginTop = '8px';
    const i2 = el('input'); i2.placeholder = 'Descargar por ruta, p. ej. /contratistas/orden-118.pdf'; f2.appendChild(i2);
    const b2 = el('button', 'Descargar', 'principal'); b2.type = 'submit'; f2.appendChild(b2);
    f2.addEventListener('submit', async e => {
      e.preventDefault();
      const r2 = await api('GET', '/api/descargas?nombre=' + encodeURIComponent(i2.value.trim()));
      vaciar(visor);
      visor.appendChild(r2.estado === 200 ? el('div', r2.datos.contenido, 'doc') : el('div', 'No se pudo descargar.', 'aviso'));
    });
    c.appendChild(f2); c.appendChild(visor);
  } else if (v === 'buscar') {
    c.appendChild(el('h2', 'Buscar documentos'));
    const f = el('form', null, 'fila');
    const i = el('input'); i.placeholder = 'Título del documento'; f.appendChild(i);
    const b = el('button', 'Buscar', 'principal'); b.type = 'submit'; f.appendChild(b);
    const res = el('div');
    f.addEventListener('submit', async e => {
      e.preventDefault();
      const r = await api('GET', '/api/buscar?q=' + encodeURIComponent(i.value));
      vaciar(res);
      if (r.estado === 200) res.appendChild(tablaArchivos(r.datos.resultados || [], id => abrirArchivo(id, res)));
      else res.appendChild(el('div', 'La búsqueda no es válida.', 'aviso'));
    });
    c.appendChild(f); c.appendChild(res);
  } else if (v === 'tiquetes') {
    const r = await api('GET', '/api/tiquetes');
    c.appendChild(el('h2', 'Mesa de ayuda'));
    (r.datos.tiquetes || []).forEach(t => {
      const d = el('div', null, 'tiq'); d.appendChild(el('b', '#' + t.id + ' · ' + t.asunto));
      d.appendChild(el('span', t.autor ? t.autor + ': ' : '', 'suave')); d.appendChild(el('span', t.texto)); c.appendChild(d);
    });
  } else if (v === 'directorio') {
    const r = await api('GET', '/api/directorio');
    c.appendChild(el('h2', 'Directorio'));
    const t = el('table'); const h = el('tr'); ['Nombre', 'Cargo', 'Departamento'].forEach(x => h.appendChild(el('th', x))); t.appendChild(h);
    (r.datos.personas || []).forEach(p => { const tr = el('tr'); [p.nombre, p.cargo, p.departamento].forEach(x => tr.appendChild(el('td', x))); t.appendChild(tr); });
    c.appendChild(t);
  } else if (v === 'admin') {
    const r = await api('GET', '/api/admin/usuarios');
    c.appendChild(el('h2', 'Administración'));
    if (r.estado !== 200) { c.appendChild(el('div', 'Acceso restringido al equipo de Tecnología.', 'aviso')); return; }
    const t = el('table'); const h = el('tr'); ['Usuario', 'Nombre', 'Rol'].forEach(x => h.appendChild(el('th', x))); t.appendChild(h);
    (r.datos.usuarios || []).forEach(u => { const tr = el('tr'); [u.usuario, u.nombre || '', u.rol].forEach(x => tr.appendChild(el('td', x))); t.appendChild(tr); });
    c.appendChild(t);
  }
}

$('form-login').addEventListener('submit', e => { e.preventDefault(); entrar($('usuario').value.trim(), $('clave').value); });
$('salir').addEventListener('click', () => { token = null; expirada(); $('error-login').textContent = ''; });
document.querySelectorAll('#pestanas button').forEach(b => b.addEventListener('click', () => mostrar(b.dataset.v)));

// La consola: solicitudes a mano, como en una herramienta de pruebas.
$('form-consola').addEventListener('submit', async e => {
  e.preventDefault();
  let cab = {}, cuerpo;
  try { cab = JSON.parse($('c-cabeceras').value || '{}'); } catch (x) { $('c-respuesta').textContent = 'Cabeceras: JSON inválido'; return; }
  const texto = $('c-cuerpo').value.trim();
  if (texto) { try { cuerpo = JSON.parse(texto); } catch (x) { $('c-respuesta').textContent = 'Cuerpo: JSON inválido'; return; } }
  let ruta = $('c-ruta').value.trim();
  if (!ruta.startsWith('/')) ruta = '/' + ruta;
  const r = await api($('c-metodo').value, ruta, cuerpo, cab);
  if (r.datos && r.datos.token && ruta.startsWith('/api/login')) token = r.datos.token;
  $('c-respuesta').textContent = 'HTTP ' + r.estado + '\n' + JSON.stringify(r.datos, null, 2);
});

// El panel puede llenar el login con la cuenta de prueba (misma página de origen).
window.addEventListener('message', e => {
  if (e.origin !== location.origin || !e.data || e.data.tipo !== 'cuenta') return;
  $('usuario').value = e.data.usuario; $('clave').value = e.data.clave;
});
})();
