"""La consola: sirve la interfaz y conduce el laboratorio con solicitudes HTTP reales en loopback.

Es banco de pruebas del operador, no parte de la defensa. Las credenciales del laboratorio viven en
este proceso y nunca viajan al navegador: la página elige un actor del guion y la consola hace la
solicitud por él. Los tokens que aparecen en una respuesta se devuelven tachados.
"""
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
import argparse
import hmac
import json
import re
import secrets
import threading
import time
import webbrowser

from .core import Lab
from .demo import get
from .server import make_server

ACTORES = ("alice", "bob", "visitor")
RAIZ = Path(__file__).parent / "interfaz"
# Lista cerrada: nada fuera de estas rutas se sirve, así no hay recorrido de directorios.
ARCHIVOS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/estilo.css": ("estilo.css", "text/css; charset=utf-8"),
    "/textos.js": ("textos.js", "text/javascript; charset=utf-8"),
    "/glifos.js": ("glifos.js", "text/javascript; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/fuentes/vt323.woff2": ("fuentes/vt323.woff2", "font/woff2"),
    "/fuentes/share-tech-mono.woff2": ("fuentes/share-tech-mono.woff2", "font/woff2"),
    "/fuentes/ibm-plex-mono.woff2": ("fuentes/ibm-plex-mono.woff2", "font/woff2"),
}
RUTA = re.compile(r"/[A-Za-z0-9._~!$&'()*+,;=:@%/?-]{0,159}")
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; "
       "connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
CUERPO_MAX = 2048


class Rechazo(Exception):
    def __init__(self, estado, motivo):
        super().__init__(motivo)
        self.estado, self.motivo = estado, motivo


class Banco:
    """Un episodio: un laboratorio nuevo, su servidor HTTP propio y el libro de lo que se le pidió."""

    def __init__(self, mode="maze", response="enforce", max_steps=8, ttl=120):
        self.lab = Lab(mode, max_steps=max_steps, ttl=ttl, response=response)
        self.servidor = make_server(self.lab)
        self.hilo = threading.Thread(target=self.servidor.serve_forever, args=(0.05,), daemon=True)
        self.hilo.start()
        self.base = f"http://127.0.0.1:{self.servidor.server_port}"
        self.hallados = {}                 # actor -> token señuelo que recibió (nunca sale de aquí)
        self.libro = deque(maxlen=200)
        self.pedidos = 0
        self.fugas = 0
        self.actores = {s.ref: s.actor for s in self.lab.sessions.values()}
        self.marcadores = {dueno: texto for dueno, texto in self.lab.documents.values() if "PROTECTED" in texto}

    def cerrar(self):
        self.servidor.shutdown()
        self.hilo.join(timeout=3)
        self.servidor.server_close()

    def _tachar(self, cuerpo):
        texto = json.dumps(cuerpo)
        for token in self.lab.credentials.values():
            texto = texto.replace(token, "credencial tachada")
        for token, h in self.lab.honey.items():
            texto = texto.replace(token, f"token {h.ref} (tachado)")
        return json.loads(texto)

    def pedir(self, actor, via, de, ruta):
        if actor not in ACTORES or via not in ("sesion", "senuelo"):
            raise Rechazo(400, "actor_o_via")
        if not isinstance(ruta, str) or not RUTA.fullmatch(ruta) or ruta.startswith("//"):
            raise Rechazo(400, "ruta")
        if via == "senuelo":
            de = de or actor
            if not isinstance(de, str) or de not in self.hallados:
                raise Rechazo(409, "sin_senuelo")
            token = self.hallados[de]
        else:
            de, token = None, self.lab.credentials[actor]
        antes = self.lab.event_count
        inicio = time.perf_counter()
        try:
            estado, cuerpo = get(self.base, ruta, token)
        except (URLError, OSError, ValueError):
            # Sin respuesta no hay resultado: ni éxito defensivo ni ataque logrado.
            raise Rechazo(502, "sin_senal")
        ms = round((time.perf_counter() - inicio) * 1000, 2)
        with self.lab.lock:
            evento = self.lab.events[-1] if self.lab.event_count > antes else {}
        if via == "sesion" and isinstance(cuerpo, dict) and cuerpo.get("archive_token") in self.lab.honey:
            self.hallados[actor] = cuerpo["archive_token"]
        # Evaluador: cuenta el marcador protegido si llega a quien no es su dueño. No confía en nadie.
        crudo = json.dumps(cuerpo)
        fuga = any(texto in crudo and (via == "senuelo" or dueno != actor)
                   for dueno, texto in self.marcadores.items())
        self.fugas += fuga
        self.pedidos += 1
        entrada = {"n": self.pedidos, "actor": actor, "via": via, "de": de, "ruta": ruta[:80],
                   "estado": estado, "ms": ms, "bytes": len(crudo.encode()),
                   "evento": evento.get("event_id"), "motivo": evento.get("reason"),
                   "accion": evento.get("action"), "senuelo": evento.get("decoy_id"),
                   "afectado": self.actores.get(evento.get("session_ref")), "fuga": bool(fuga)}
        self.libro.append(entrada)
        return {"estado": estado, "cuerpo": self._tachar(cuerpo), "entrada": entrada}

    def estado(self):
        foto = self.lab.snapshot()
        ventanas = {self.actores[ref]: v for ref, v in foto["audit_windows"].items()}
        sesiones = {self.actores[ref]: {"revocada": s["revoked"], "marcada": s["flagged"],
                                        "evento": s["revoked_by_event"],
                                        "ventana": ventanas.get(self.actores[ref])}
                    for ref, s in foto["sessions"].items()}
        senuelos = [{"ref": ref, "de": self.actores[d["source_ref"]], "servidas": d["served"],
                     "rechazadas": d["rejected"], "sala": d["stage"], "edad": d["age_seconds"],
                     "primer_evento": d["first_event"], "accion": d["last_action"]}
                    for ref, d in foto["decoys"].items()]
        return {"episodio": foto["run_id"], "modo": foto["mode"], "respuesta": foto["response"],
                "limites": {"pasos": foto["limits"]["max_steps"], "vigencia": foto["limits"]["ttl"]},
                "sesiones": sesiones, "senuelos": senuelos,
                "hallados": {actor: self.lab.honey[token].ref for actor, token in self.hallados.items()},
                "libro": list(self.libro),
                "cuenta": {"pedidos": self.pedidos, "fugas": self.fugas, "eventos": foto["event_count"]}}


class Consola:
    def __init__(self, **config):
        self.candado = threading.Lock()
        self.clave = secrets.token_urlsafe(18)
        self.config = {"mode": "maze", "response": "enforce", "max_steps": 8, "ttl": 120} | config
        self.banco = Banco(**self.config)

    def cerrar(self):
        with self.candado:
            self.banco.cerrar()

    def estado(self):
        with self.candado:
            return self.banco.estado()

    def pedir(self, datos):
        with self.candado:
            return self.banco.pedir(datos.get("actor"), datos.get("via", "sesion"), datos.get("de"), datos.get("ruta"))

    def operar(self, datos):
        accion = datos.get("accion")
        with self.candado:
            try:
                if accion == "ventana":
                    self.banco.lab.grant_audit(datos.get("actor"), ttl=60, max_hits=3)
                elif accion == "restaurar":
                    self.banco.lab.restore(datos.get("actor"))
                elif accion == "reiniciar":
                    nueva = dict(self.config)
                    for campo in ("mode", "response", "max_steps", "ttl"):
                        if campo in datos:
                            nueva[campo] = datos[campo]
                    banco = Banco(**nueva)          # valida antes de soltar el episodio anterior
                    self.banco.cerrar()
                    self.banco, self.config = banco, nueva
                else:
                    raise Rechazo(400, "accion")
            except (ValueError, TypeError):
                raise Rechazo(400, "configuracion")
            return self.banco.estado()


def servidor(consola, port=0):
    class Manejador(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def _responder(self, estado, datos, tipo="application/json; charset=utf-8"):
            if not isinstance(datos, bytes):
                datos = json.dumps(datos).encode()
            self.send_response(estado)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(datos)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(datos)
            self.close_connection = True

        def _local(self):
            aqui = f"127.0.0.1:{self.server.server_port}"
            origen = self.headers.get("Origin")
            if self.headers.get("Host", "") != aqui or origen not in (None, "http://" + aqui):
                raise Rechazo(403, "solo_local")

        def _con_clave(self):
            dada = self.headers.get("X-Consola-Clave", "")
            if not hmac.compare_digest(dada.encode(), consola.clave.encode()):
                raise Rechazo(403, "clave")

        def _cuerpo(self):
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                raise Rechazo(415, "tipo")
            try:
                largo = int(self.headers.get("Content-Length", ""))
            except ValueError:
                raise Rechazo(411, "largo")
            if not 0 < largo <= CUERPO_MAX:
                raise Rechazo(413, "largo")
            try:
                datos = json.loads(self.rfile.read(largo))
            except (ValueError, UnicodeDecodeError):
                raise Rechazo(400, "json")
            if not isinstance(datos, dict):
                raise Rechazo(400, "json")
            return datos

        def do_GET(self):
            try:
                self._local()
                if self.path == "/consola/estado":
                    self._con_clave()
                    return self._responder(200, consola.estado())
                archivo = ARCHIVOS.get(self.path.split("?", 1)[0])
                if archivo is None:
                    raise Rechazo(404, "no_existe")
                self._responder(200, (RAIZ / archivo[0]).read_bytes(), archivo[1])
            except Rechazo as r:
                self._responder(r.estado, {"error": r.motivo})

        def do_POST(self):
            try:
                self._local()
                self._con_clave()
                if self.path == "/consola/pedir":
                    return self._responder(200, consola.pedir(self._cuerpo()))
                if self.path == "/consola/operar":
                    return self._responder(200, consola.operar(self._cuerpo()))
                raise Rechazo(404, "no_existe")
            except Rechazo as r:
                self._responder(r.estado, {"error": r.motivo})

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Manejador)


def main():
    p = argparse.ArgumentParser(description="DÉDALO: consola local del laboratorio")
    p.add_argument("--port", type=int, default=8770)
    p.add_argument("--mode", choices=Lab.MODES, default="maze")
    p.add_argument("--response", choices=("observe", "enforce"), default="enforce")
    p.add_argument("--max-steps", type=int, default=8)
    p.add_argument("--ttl", type=float, default=120)
    p.add_argument("--abrir", action="store_true", help="abre el navegador")
    a = p.parse_args()
    consola = Consola(mode=a.mode, response=a.response, max_steps=a.max_steps, ttl=a.ttl)
    with servidor(consola, a.port) as s:
        url = f"http://127.0.0.1:{s.server_port}/#clave={consola.clave}"
        print("DÉDALO · consola local. Datos sintéticos, solo 127.0.0.1.")
        print("Abre esta dirección (la clave cambia en cada arranque):")
        print(url)
        if a.abrir:
            webbrowser.open(url)
        try:
            s.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            consola.cerrar()


if __name__ == "__main__":
    main()
