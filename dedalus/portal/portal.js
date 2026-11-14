// El portal de Cnosos (izquierda) y la base que lo sostiene (derecha).
// Reglas: todo texto sale de textos.js, nada entra como HTML (solo textContent), sin estilos en línea.
"use strict";
(() => {
  const T = window.TEXTOS, P = T.portal, B = T.base;
  const $ = id => document.getElementById(id);
  const el = (tag, cls, txt) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt !== undefined && txt !== null) e.textContent = String(txt);
    return e;
  };
  const GLIFO = { publico: "○", interno: "◐", confidencial: "●", secreto: "■" };

  // ═════════════ el portal ═════════════
  const yo = { token: null, perfil: null, seccion: "documentos" };

  async function api(metodo, ruta, cuerpo) {
    const cab = { "Content-Type": "application/json" };
    if (yo.token) cab.Authorization = "Bearer " + yo.token;
    let r;
    try {
      r = await fetch(ruta, { method: metodo, headers: cab, cache: "no-store",
                              body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo) });
    } catch (_) {
      return { estado: 0, datos: { error: "red" } };
    }
    let datos = {};
    try { datos = await r.json(); } catch (_) { /* respuesta vacía */ }
    return { estado: r.status, datos };
  }

  // Una respuesta 401 dentro del portal es una sesión que ya no existe: se vuelve a la puerta.
  function caida(res) {
    if (res.estado !== 401) return false;
    salir(P.errores[res.datos.error] || P.errores.otro);
    return true;
  }

  function salir(mensaje) {
    yo.token = null; yo.perfil = null;
    $("p-quien").hidden = true; $("p-adentro").hidden = true; $("p-entrada").hidden = false;
    $("f-clave").value = "";
    $("f-error").textContent = mensaje || "";
    base.resaltar(null);
    $("f-usuario").focus();
  }

  async function entrar(ev) {
    ev.preventDefault();
    const boton = $("f-entrar");
    boton.disabled = true; boton.textContent = P.entrando; $("f-error").textContent = "";
    const res = await api("POST", "/api/login", { usuario: $("f-usuario").value.trim(), clave: $("f-clave").value });
    boton.disabled = false; boton.textContent = P.entrar;
    if (res.estado !== 200 || !res.datos.token) {
      $("f-error").textContent = P.errores[res.datos.error] || P.errores.otro;
      $("f-clave").value = "";
      return;
    }
    yo.token = res.datos.token;
    const perfil = await api("GET", "/api/perfil");
    if (caida(perfil)) return;
    // Una cuenta de servicio (una hiedra) no tiene perfil de empleado: se muestra lo mínimo.
    yo.perfil = perfil.estado === 200 ? perfil.datos
      : { usuario: $("f-usuario").value.trim(), nombre: $("f-usuario").value.trim(), rol: res.datos.rol, cargo: "" };
    $("f-clave").value = "";
    $("p-nombre").textContent = yo.perfil.nombre;
    $("p-cargo").textContent = yo.perfil.cargo || "";
    $("p-rol").textContent = P.roles[yo.perfil.rol] || yo.perfil.rol;
    $("p-quien").hidden = false; $("p-entrada").hidden = true; $("p-adentro").hidden = false;
    base.resaltar(yo.perfil.usuario);
    ir("documentos");
  }

  function nav() {
    const n = $("p-nav");
    n.replaceChildren();
    for (const [clave, nombre] of P.secciones) {
      const b = el("button", null, nombre);
      b.type = "button";
      b.dataset.seccion = clave;
      b.addEventListener("click", () => ir(clave));
      n.append(b);
    }
  }

  function ir(seccion) {
    yo.seccion = seccion;
    for (const b of $("p-nav").children) {
      if (b.dataset.seccion === seccion) b.setAttribute("aria-current", "page");
      else b.removeAttribute("aria-current");
    }
    ({ documentos, buscar, directorio, tiquetes, admin })[seccion]();
  }

  const vista = (...hijos) => $("p-vista").replaceChildren(...hijos);

  function filaDoc(a) {
    const b = el("button", "p-doc");
    b.type = "button";
    const texto = el("div");
    texto.append(el("b", null, a.titulo), el("small", null, a.ruta));
    b.append(el("span", "g", GLIFO[a.nivel] || "?"), texto, el("span", "p-nivel " + a.nivel, P.niveles[a.nivel] || a.nivel));
    b.addEventListener("click", () => abrir(a.id));
    return b;
  }

  async function documentos() {
    const res = await api("GET", "/api/archivos");
    if (caida(res) || yo.seccion !== "documentos") return;
    const lista = el("div", "p-docs");
    const archivos = res.datos.archivos || [];
    archivos.forEach(a => lista.append(filaDoc(a)));
    vista(el("h3", null, P.documentosTitulo), el("p", "p-sub", P.documentosSub(archivos.length)), lista);
  }

  async function abrir(id) {
    const res = await api("GET", "/api/archivos/" + encodeURIComponent(id));
    if (caida(res)) return;
    const volver = el("button", "p-volver", P.volver);
    volver.type = "button";
    volver.addEventListener("click", () => ir("documentos"));
    const hoja = el("div", "p-hoja");
    if (res.estado === 200) {
      const d = res.datos;
      hoja.append(el("span", "p-nivel " + d.nivel, P.niveles[d.nivel] || d.nivel), el("h3", null, d.titulo),
                  el("small", null, d.ruta), el("pre", null, d.contenido));
    } else {
      hoja.append(el("p", null, P.noExiste));
    }
    const caja = el("div", "p-abierto");
    caja.append(volver, hoja);
    vista(caja);
  }

  function buscar() {
    const form = el("form", "p-buscar");
    const campo = el("input");
    campo.placeholder = P.buscarCampo; campo.maxLength = 200; campo.spellcheck = false;
    const boton = el("button", "p-boton", P.buscarBoton);
    boton.type = "submit";
    form.append(campo, boton);
    const salida = el("div");
    form.addEventListener("submit", async ev => {
      ev.preventDefault();
      const res = await api("GET", "/api/buscar?q=" + encodeURIComponent(campo.value));
      if (caida(res)) return;
      if (res.estado === 400) return salida.replaceChildren(el("p", "p-error", P.buscarInvalida));
      const lista = el("div", "p-docs");
      (res.datos.resultados || []).forEach(a => lista.append(filaDoc(a)));
      salida.replaceChildren(lista.children.length ? lista : el("p", "p-sub", P.buscarVacio));
    });
    vista(el("h3", null, P.buscarTitulo), el("p", "p-sub"), form, salida);
    campo.focus();
  }

  async function directorio() {
    const res = await api("GET", "/api/directorio");
    if (caida(res) || yo.seccion !== "directorio") return;
    const lista = el("div", "p-lista");
    for (const p of res.datos.personas || []) {
      const f = el("div", "p-fila");
      f.append(el("b", null, p.nombre), el("span", null, `${p.cargo} · ${p.departamento}`));
      lista.append(f);
    }
    vista(el("h3", null, P.directorioTitulo), el("p", "p-sub"), lista);
  }

  async function tiquetes() {
    const res = await api("GET", "/api/tiquetes");
    if (caida(res) || yo.seccion !== "tiquetes") return;
    const lista = el("div", "p-lista");
    for (const t of res.datos.tiquetes || []) {
      const f = el("div", "p-fila");
      f.append(el("b", null, `#${t.id} · ${t.asunto}`), el("span", null, P.porAutor(t.autor)), el("p", null, t.texto));
      lista.append(f);
    }
    vista(el("h3", null, P.tiquetesTitulo), el("p", "p-sub"), lista);
  }

  async function admin() {
    const res = await api("GET", "/api/admin/usuarios");
    if (caida(res) || yo.seccion !== "admin") return;
    if (res.estado !== 200) {
      const caja = el("div", "p-negado");
      caja.append(el("b", null, P.adminNegado), el("span", null, P.adminNegadoSub));
      return vista(el("h3", null, P.adminTitulo), el("p", "p-sub"), caja);
    }
    const lista = el("div", "p-lista");
    for (const u of res.datos.usuarios || []) {
      const f = el("div", "p-fila");
      f.append(el("b", null, `${u.nombre} · ${u.usuario}`),
               el("span", null, `${P.roles[u.rol] || u.rol} · ${u.activo ? P.activo : P.inactivo}`));
      lista.append(f);
    }
    vista(el("h3", null, P.adminTitulo), el("p", "p-sub"), lista);
  }

  // ═════════════ la base ═════════════
  const base = (() => {
    let clave = null;
    try {
      const enUrl = new URLSearchParams(location.hash.slice(1)).get("op");
      if (enUrl) sessionStorage.setItem("cnosos-op", enUrl);
      clave = enUrl || sessionStorage.getItem("cnosos-op");
    } catch (_) {
      clave = new URLSearchParams(location.hash.slice(1)).get("op");
    }
    if (location.hash) history.replaceState(null, "", "/");     // la clave no queda en la barra ni en el proyector

    const st = { datos: null, pestana: "matriz", episodio: null, ultimo: 0, tu: null, eventosVistos: 0 };

    async function op(ruta) {
      try {
        const r = await fetch(ruta, { headers: { "X-Operador": clave }, cache: "no-store" });
        const d = await r.json().catch(() => ({}));
        if (r.status === 401) return { error: "clave" };
        if (r.status !== 200) return { error: d.error === "almacen" ? "almacen" : "otro", detalle: d.detalle };
        return d;
      } catch (_) {
        return { error: "red" };
      }
    }

    function aviso(texto, mal) {
      const a = $("b-aviso");
      a.hidden = !texto;
      a.textContent = texto || "";
      a.classList.toggle("mal", Boolean(mal));
    }

    function conteos(c) {
      const p = $("b-conteos");
      p.replaceChildren();
      for (const [tabla, nombre] of Object.entries(B.tablas)) {
        if (!(tabla in c)) continue;
        p.append(nombre, el("b", null, c[tabla]), " ");
      }
    }

    function motor(m) {
      const s = $("b-motor");
      s.textContent = B.motores[m] || m;
      s.classList.toggle("oracle", m === "oracle");
    }

    function pestanas() {
      const n = $("b-pestanas");
      n.replaceChildren();
      for (const [k, nombre] of B.pestanas) {
        const b = el("button", null, nombre);
        b.type = "button";
        b.setAttribute("role", "tab");
        b.setAttribute("aria-selected", String(k === st.pestana));
        b.addEventListener("click", () => { st.pestana = k; pestanas(); panel(); });
        n.append(b);
      }
    }

    function tabla(filas, columnas) {
      const t = el("table");
      const h = el("tr");
      columnas.forEach(([, nombre]) => h.append(el("th", null, nombre)));
      const thead = el("thead"); thead.append(h);
      const tb = el("tbody");
      for (const f of filas) {
        const tr = el("tr");
        for (const [k] of columnas) {
          const v = f[k];
          tr.append(el("td", typeof v === "number" ? "n" : k === "texto" ? "texto" : null, v === null || v === undefined ? "—" : v));
        }
        tb.append(tr);
      }
      t.append(thead, tb);
      return t;
    }

    function matriz() {
      const d = st.datos;
      const t = el("table", "matriz");
      const h = el("tr");
      h.append(el("th", "quien"));
      for (const a of d.archivos) {
        const th = el("th", "col " + a.nivel, a.id);
        th.addEventListener("mouseenter", () => { $("b-detalle").textContent = `#${a.id} · ${a.titulo} · ${a.ruta}`; });
        h.append(th);
      }
      const thead = el("thead"); thead.append(h);
      const tb = el("tbody");
      d.usuarios.forEach((u, i) => {
        const tr = el("tr");
        tr.dataset.usuario = u.usuario;
        if (u.usuario === st.tu) tr.className = "tu";
        const q = el("td", "quien", u.nombre);
        q.append(el("small", null, u.rol));
        q.setAttribute("data-tu", B.tu);
        tr.append(q);
        d.archivos.forEach((a, j) => {
          const r = d.matriz[i][j];
          const td = el("td", r || "nada", r ? GLIFO[a.nivel] : "·");
          td.addEventListener("mouseenter", () => {
            $("b-detalle").textContent = B.detalle(u.nombre, a.titulo, P.niveles[a.nivel] || a.nivel,
                                                   r ? B.razones[r] : B.sinAcceso);
          });
          tr.append(td);
        });
        tb.append(tr);
      });
      t.append(thead, tb);
      const ley = el("div", "leyenda");
      ley.append(el("i", null, B.leyendaNiveles));
      for (const [k, nombre] of Object.entries(B.razones)) ley.append(el("i", k, "■ " + nombre));
      const caja = el("div");
      caja.append(t, ley, el("p", "b-pie", B.matrizPie));
      return caja;
    }

    function panel() {
      const p = $("b-panel");
      $("b-detalle").textContent = "";
      if (!st.datos) return p.replaceChildren();
      const d = st.datos;
      if (st.pestana === "matriz") return p.replaceChildren(matriz());
      if (st.pestana === "permisos") {
        const archivo = Object.fromEntries(d.archivos.map(a => [a.id, a.titulo]));
        const persona = Object.fromEntries(d.usuarios.map(u => [u.id, u.nombre]));
        const filas = d.permisos.map(f => ({ ...f, _archivo: archivo[f.archivo_id], _usuario: persona[f.usuario_id] }));
        return p.replaceChildren(tabla(filas, B.columnas.permisos));
      }
      p.replaceChildren(tabla(d[st.pestana], B.columnas[st.pestana]));
    }

    function resaltar(usuario) {
      st.tu = usuario;
      for (const tr of document.querySelectorAll(".matriz tbody tr")) {
        tr.classList.toggle("tu", tr.dataset.usuario === usuario);
      }
    }

    // ── Ariadna: la tabla eventos, leída de la base por partes
    function evento(e) {
      const li = el("li", "nuevo");
      const que = [];
      if (e.intento) que.push(st.nombres[e.intento] || e.intento);
      if (e.hiedra) que.push(B.hiedra(e.hiedra));
      if (e.accion) que.push(B.acciones[e.accion] || e.accion);
      if (e.laberinto && !e.accion) que.push(B.laberinto);
      if (e.fuga) que.push(B.fuga);
      if (e.intento || e.hiedra || e.accion === "icaro" || e.fuga || e.estado === 403) li.classList.add("alerta");
      if (e.laberinto) li.classList.add("laberinto");
      if (e.fuga) li.classList.add("fuga");
      li.append(el("span", "n", e.n), el("span", null, e.usuario || B.anonimo), el("span", "m", e.metodo),
                el("span", "r", e.ruta), el("span", "e" + String(e.estado)[0] + " e", e.estado), el("span", "que", que.join(" · ")));
      return li;
    }

    async function eventos() {
      if (!st.episodio) return;
      const pedido = st.episodio;
      const d = await op(`/operador/eventos?episodio=${encodeURIComponent(pedido)}&desde=${st.ultimo}`);
      if (d.error || pedido !== st.episodio) return;
      st.nombres = d.nombres_intento || {};
      const ol = $("b-eventos");
      if (st.ultimo === 0) ol.replaceChildren();
      const abajo = ol.scrollHeight - ol.scrollTop - ol.clientHeight < 40;   // si el operador subió a leer, no lo jala
      let llegaron = 0;
      for (const e of d.eventos) {
        if (e.n <= st.ultimo) continue;
        ol.querySelector(".vacio")?.remove();
        ol.append(evento(e));
        st.ultimo = e.n;
        llegaron++;
      }
      while (ol.children.length > 120) ol.firstElementChild.remove();
      if (!ol.children.length) ol.append(el("li", "vacio", B.sinEventos));
      if (llegaron && abajo) ol.scrollTop = ol.scrollHeight;
    }

    function elegir(episodio) {
      st.episodio = episodio; st.ultimo = 0;
      $("b-eventos").replaceChildren();
      eventos();
    }

    async function episodios() {
      const d = await op("/operador/episodios");
      if (d.error) return aviso(d.error === "clave" ? B.clave : `${B.sinSenal}${d.detalle ? " · " + d.detalle : ""}`, true);
      aviso(d.errores_registro ? B.errores(d.errores_registro) : "", Boolean(d.errores_registro));
      motor(d.almacen);
      conteos(d.conteos);
      const s = $("b-episodio");
      const antes = st.episodio || d.actual;
      s.replaceChildren();
      const lista = d.episodios.some(e => e.episodio === d.actual) ? d.episodios : [{ episodio: d.actual, eventos: 0 }, ...d.episodios];
      for (const e of lista) {
        const o = el("option", null, e.episodio === d.actual ? B.episodioActual(e.episodio) : B.episodioOtro(e.episodio, e.eventos));
        o.value = e.episodio;
        s.append(o);
      }
      s.value = antes;
      if (!st.episodio) elegir(d.actual);
    }

    async function iniciar() {
      $("b-titulo").textContent = B.titulo;
      $("b-ar-titulo").textContent = B.ariadna;
      $("b-ar-pie").textContent = B.ariadnaPie;
      if (!clave) {
        aviso(B.sinClave, false);
        return;
      }
      pestanas();
      $("b-episodio").addEventListener("change", ev => elegir(ev.target.value));
      const d = await op("/operador/base");
      if (d.error) {
        aviso(d.error === "clave" ? B.clave : `${B.sinSenal}${d.detalle ? " · " + d.detalle : ""}`, true);
      } else {
        st.datos = d;
        motor(d.almacen);
        conteos(d.conteos);
        panel();
      }
      await episodios();
      setInterval(eventos, 1500);
      setInterval(episodios, 6000);
    }

    return { iniciar, resaltar };
  })();

  // ═════════════ arranque ═════════════
  document.title = T.titulo;
  $("p-marca").textContent = P.marca;
  $("p-lema").textContent = P.lema;
  $("p-titulo").textContent = P.entrarTitulo;
  $("p-sub").textContent = P.entrarSub;
  $("l-usuario").textContent = P.usuario;
  $("l-clave").textContent = P.clave;
  $("f-entrar").textContent = P.entrar;
  $("p-salir").textContent = P.salir;
  $("p-pie").textContent = P.pie;
  $("p-form").addEventListener("submit", entrar);
  $("p-salir").addEventListener("click", () => salir(""));
  nav();
  base.iniciar();
  $("f-usuario").focus();
})();
