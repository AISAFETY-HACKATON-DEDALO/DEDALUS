"""El panel: pantalla partida. Izquierda, el portal de Cnosos (lo que se ataca). Derecha, lo que pasa detrás.

    python -m dedalus.panel --abrir          # http://127.0.0.1:8790/#clave=...

- /api/*, /.env, /backup/*  el portal de Cnosos, tal cual: cualquiera en este computador puede atacarlo.
- /panel/*                  el operador: estado, Minotauro, Dédalo, episodio nuevo. Exige la clave del arranque.
Solo 127.0.0.1. Las claves de los modelos se leen de variables de entorno en este proceso; nunca van al navegador.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import hmac
import json
import secrets
import threading
import time
import webbrowser

from .agentes import AGENTES, PROVEEDORES, Guion, Modelo, disponibles, episodio
from .almacen import abrir
from .casos import CASOS
from .cnosos import INTENTOS, Cnosos
from .defensor import GuionDefensor, defender
from .ronda import estadisticas, registrar

RAIZ = Path(__file__).parent / "panel_web"
FUENTES = Path(__file__).parent.parent / "dedalo" / "interfaz" / "fuentes"
ARCHIVOS = {
    "/": (RAIZ / "index.html", "text/html; charset=utf-8"),
    "/portal": (RAIZ / "portal.html", "text/html; charset=utf-8"),
    "/panel.css": (RAIZ / "panel.css", "text/css; charset=utf-8"),
    "/portal.css": (RAIZ / "portal.css", "text/css; charset=utf-8"),
    "/panel.js": (RAIZ / "panel.js", "text/javascript; charset=utf-8"),
    "/portal.js": (RAIZ / "portal.js", "text/javascript; charset=utf-8"),
    "/fuentes/vt323.woff2": (FUENTES / "vt323.woff2", "font/woff2"),
    "/fuentes/share-tech-mono.woff2": (FUENTES / "share-tech-mono.woff2", "font/woff2"),
    "/fuentes/ibm-plex-mono.woff2": (FUENTES / "ibm-plex-mono.woff2", "font/woff2"),
}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; connect-src 'self'; "
       "img-src 'self' data:; frame-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'")
CUERPO_MAX = 4096


class Panel:
    def __init__(self, respuesta="contener", inyeccion=False):
        self.clave = secrets.token_urlsafe(18)
        self.candado = threading.Lock()
        self.respuesta, self.inyeccion = respuesta, inyeccion
        self.cnosos = Cnosos(almacen=abrir(), respuesta=respuesta, inyeccion=inyeccion)
        self.tareas = {"minotauro": {"activo": False}, "dedalo": {"activo": False, "resultados": []}}
        self._modelo = None
        self.estadisticas = self._estadisticas()

    def _estadisticas(self):
        try:
            return estadisticas(self.cnosos.almacen)
        except Exception:               # noqa: BLE001 — sin estadísticas no se cae el panel
            return []

    # ---------- operador
    def estado(self, desde=0):
        c = self.cnosos
        foto = c.foto()
        nuevos = [e for e in foto.pop("ariadna") if e["n"] > desde]
        eventos = nuevos[:300]          # en orden y sin saltos: si hay más, el panel los pide en la siguiente vuelta
        m = self.tareas["minotauro"]
        tokens = getattr(self._modelo, "tokens", 0) if self._modelo else m.get("resumen", {}).get("tokens_atacante", 0)
        return {**foto, "eventos_nuevos": eventos, "pendientes": len(nuevos) - len(eventos), "tareas": self.tareas,
                "tokens_atacante": tokens, "proveedores": disponibles(), "estadisticas": self.estadisticas,
                "casos": {k: {"titulo": v["titulo"], "cwe": v["cwe"]} for k, v in CASOS.items()},
                "cuenta_atacante": c.cuenta_de_prueba("tomas.mejia"), "nombres_intento": INTENTOS}

    def minotauro(self, proveedor="guion", agente="minotauro", pasos=25):
        if self.tareas["minotauro"]["activo"]:
            return {"error": "ya_corre"}
        if agente not in AGENTES or proveedor not in ("guion", *PROVEEDORES) or not 1 <= int(pasos) <= 40:
            return {"error": "parametros"}
        try:
            modelo = Guion(agente) if proveedor == "guion" else Modelo(proveedor)
        except SystemExit as e:
            return {"error": str(e)}
        self._modelo = modelo
        self.tareas["minotauro"] = {"activo": True, "proveedor": modelo.nombre, "agente": agente, "inicio": time.time()}

        def correr():
            try:
                _, r = episodio(self.cnosos, modelo, agente, int(pasos), salida=lambda *_: None)
                try:
                    registrar(self.cnosos.almacen, r, "panel", self.respuesta)
                except Exception as e:  # noqa: BLE001 — la corrida se ve igual aunque no se guarde
                    r["no_guardada"] = f"{type(e).__name__}"[:60]
                self.estadisticas = self._estadisticas()
                self.tareas["minotauro"].update(activo=False, resumen=r)
            except Exception as e:     # noqa: BLE001 — se muestra en el panel en vez de tumbar el servidor
                self.tareas["minotauro"].update(activo=False, error=f"{type(e).__name__}: {e}"[:300])
        threading.Thread(target=correr, daemon=True).start()
        return {"ok": True}

    def dedalo(self, proveedor="guion"):
        if self.tareas["dedalo"]["activo"]:
            return {"error": "ya_corre"}
        if proveedor not in ("guion", *PROVEEDORES):
            return {"error": "parametros"}
        try:
            modelo = GuionDefensor() if proveedor == "guion" else Modelo(proveedor, timeout=60, max_tokens=1200)
        except SystemExit as e:
            return {"error": str(e)}
        self.tareas["dedalo"] = {"activo": True, "proveedor": modelo.nombre, "resultados": []}

        def correr():
            for c in CASOS:
                r = defender(c, modelo, 2, salida=lambda *_: None)
                f = r["final"] or {}
                self.tareas["dedalo"]["resultados"].append({
                    "caso": c, "titulo": r["titulo"], "cwe_esperada": r["cwe_esperada"], "cwe": f.get("cwe"),
                    "cwe_correcta": f.get("cwe_correcta"), "verificado": f.get("verificado"),
                    "veredicto": f.get("veredicto", "sin respuesta"), "intentos": r["intentos"],
                    "explicacion": f.get("explicacion", ""), "parche": f.get("parche", "")[:1500],
                    "original": CASOS[c]["codigo"]})
            self.tareas["dedalo"]["activo"] = False
        threading.Thread(target=correr, daemon=True).start()
        return {"ok": True}

    def nuevo(self):
        if self.tareas["minotauro"]["activo"] or self.tareas["dedalo"]["activo"]:
            return {"error": "hay_tareas"}
        anterior = self.cnosos
        self.cnosos = Cnosos(almacen=abrir(), respuesta=self.respuesta, inyeccion=self.inyeccion)
        anterior.almacen.cerrar()
        self.tareas = {"minotauro": {"activo": False}, "dedalo": {"activo": False, "resultados": []}}
        self._modelo = None
        self.estadisticas = self._estadisticas()
        return {"ok": True, "episodio": self.cnosos.episodio}


class Rechazo(Exception):
    def __init__(self, estado, motivo):
        super().__init__(motivo)
        self.estado, self.motivo = estado, motivo


def servidor(panel, port=0):
    class Manejador(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(8)

        def _responder(self, estado, datos, tipo="application/json; charset=utf-8"):
            if not isinstance(datos, bytes):
                datos = json.dumps(datos).encode()
            self.send_response(estado)
            for k, v in (("Content-Type", tipo), ("Content-Length", str(len(datos))), ("Cache-Control", "no-store"),
                         ("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "no-referrer"),
                         ("Content-Security-Policy", CSP), ("Connection", "close")):
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(datos)
            self.close_connection = True

        def _local(self):
            aqui = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host", "") != aqui or self.headers.get("Origin") not in (None, "http://" + aqui):
                raise Rechazo(403, "solo_local")

        def _cuerpo(self):
            try:
                largo = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                raise Rechazo(411, "largo")
            if not 0 <= largo <= CUERPO_MAX:
                raise Rechazo(413, "largo")
            return self.rfile.read(largo) if largo else b""

        def _operador(self):
            if not hmac.compare_digest(self.headers.get("X-Panel-Clave", "").encode(), panel.clave.encode()):
                raise Rechazo(403, "clave")

        def _atender(self):
            try:
                self._local()
                camino = self.path.split("?", 1)[0]
                if camino.startswith("/panel/"):
                    self._operador()
                    datos = json.loads(self._cuerpo() or b"{}") if self.command == "POST" else {}
                    if not isinstance(datos, dict):
                        raise Rechazo(400, "json")
                    if camino == "/panel/estado":
                        desde = int((self.path.split("desde=", 1) + ["0"])[1].split("&")[0] or 0)
                        return self._responder(200, panel.estado(desde))
                    acciones = {"/panel/minotauro": lambda: panel.minotauro(datos.get("proveedor", "guion"),
                                                                             datos.get("agente", "minotauro"),
                                                                             datos.get("pasos", 25)),
                                "/panel/dedalo": lambda: panel.dedalo(datos.get("proveedor", "guion")),
                                "/panel/nuevo": panel.nuevo}
                    if self.command != "POST" or camino not in acciones:
                        raise Rechazo(404, "no_existe")
                    r = acciones[camino]()
                    return self._responder(400 if "error" in r else 200, r)
                if camino.startswith("/api/") or camino in ("/.env", "/backup/config"):
                    estado, datos = panel.cnosos.solicitud(self.command, self.path, dict(self.headers.items()),
                                                           self._cuerpo())
                    return self._responder(estado, datos)
                archivo = ARCHIVOS.get(camino)
                if archivo is None or self.command != "GET":
                    raise Rechazo(404, "no_existe")
                self._responder(200, archivo[0].read_bytes(), archivo[1])
            except Rechazo as r:
                self._responder(r.estado, {"error": r.motivo})
            except (ValueError, json.JSONDecodeError):
                self._responder(400, {"error": "solicitud"})

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _atender

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Manejador)


def main():
    p = argparse.ArgumentParser(description="DÉDALO · panel: el portal de Cnosos y lo que pasa detrás")
    p.add_argument("--port", type=int, default=8790)
    p.add_argument("--respuesta", choices=Cnosos.RESPUESTAS, default="contener")
    p.add_argument("--inyeccion", action="store_true")
    p.add_argument("--abrir", action="store_true")
    a = p.parse_args()
    panel = Panel(a.respuesta, a.inyeccion)
    with servidor(panel, a.port) as s:
        url = f"http://127.0.0.1:{s.server_port}/#clave={panel.clave}"
        print(f"DÉDALO · panel · almacén {panel.cnosos.almacen.motor} · episodio {panel.cnosos.episodio}")
        print("Cuenta de contratista para atacar a mano:", json.dumps(panel.cnosos.cuenta_de_prueba("tomas.mejia")))
        print("Abre:", url)
        if a.abrir:
            webbrowser.open(url)
        try:
            s.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            panel.cnosos.almacen.cerrar()


if __name__ == "__main__":
    main()
