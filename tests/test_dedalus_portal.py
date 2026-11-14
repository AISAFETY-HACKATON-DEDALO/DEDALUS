"""El portal visual y la vista de la base: misma regla de acceso, nada sensible hacia el navegador, y la clave del
operador como única puerta a /operador/*."""
import json
import re
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from dedalus.cnosos import ESTATICOS, Cnosos, servidor
from dedalus.semilla import MARCADOR, USUARIOS

PORTAL = Path(__file__).parent.parent / "dedalus" / "portal"


class Vistas(unittest.TestCase):
    def setUp(self):
        self.c = Cnosos()

    def tearDown(self):
        self.c.almacen.cerrar()

    def test_la_matriz_usa_la_misma_regla_que_el_portal(self):
        v = self.c.vista_base()
        for i, u in enumerate(v["usuarios"]):
            sesion = type("S", (), {"rol": u["rol"], "uid": u["id"], "departamento": u["departamento_id"]})()
            for j, a in enumerate(v["archivos"]):
                self.assertEqual(bool(v["matriz"][i][j]), self.c._puede_ver(sesion, self.c._archivo(a["id"])),
                                 (u["usuario"], a["id"]))

    def test_casos_de_la_demo(self):
        v = self.c.vista_base()
        fila = {u["usuario"]: v["matriz"][i] for i, u in enumerate(v["usuarios"])}
        planos = next(j for j, a in enumerate(v["archivos"]) if a["nivel"] == "secreto")
        self.assertIsNone(fila["tomas.mejia"][planos])
        self.assertEqual(fila["ana.rios"][planos], "permiso")
        self.assertEqual(fila["ines.vargas"][planos], "administracion")
        self.assertEqual(sum(r is not None for r in fila["tomas.mejia"]), 6)
        self.assertEqual(v["conteos"]["usuarios"], len(USUARIOS))

    def test_la_vista_no_entrega_claves_sales_ni_contenidos(self):
        crudo = json.dumps(self.c.vista_base())
        self.assertNotIn(MARCADOR, crudo)
        self.assertNotIn('"sal"', crudo)
        self.assertNotIn('"contenido"', crudo)
        for clave in self.c._claves.values():
            self.assertNotIn(clave, crudo)
        for u in self.c.almacen.consultar("SELECT sal, clave_hash FROM usuarios"):
            self.assertNotIn(u["sal"], crudo)
            self.assertNotIn(u["clave_hash"], crudo)

    def test_eventos_salen_de_la_base_por_partes(self):
        self.c.solicitud("GET", "/api/perfil")
        self.c.solicitud("GET", "/api/admin")
        todos = self.c.vista_eventos(self.c.episodio)["eventos"]
        self.assertEqual([e["n"] for e in todos], [1, 2])
        self.assertEqual([e["n"] for e in self.c.vista_eventos(self.c.episodio, 1)["eventos"]], [2])
        self.assertEqual(self.c.vista_episodios()["episodios"][0]["episodio"], self.c.episodio)
        for malo in ("x' OR '1'='1", "", "A" * 30):
            with self.assertRaises(ValueError):
                self.c.vista_eventos(malo)


class Http(unittest.TestCase):
    def setUp(self):
        self.c = Cnosos()
        self.srv = servidor(self.c, operador="clave-del-operador")
        self.hilo = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.hilo.start()
        self.abrir = build_opener(ProxyHandler({})).open
        self.base = f"http://127.0.0.1:{self.srv.server_port}"

    def tearDown(self):
        self.srv.shutdown()
        self.hilo.join(timeout=3)
        self.srv.server_close()
        self.c.almacen.cerrar()

    def http(self, ruta, cab=None):
        try:
            with self.abrir(Request(self.base + ruta, headers=cab or {}), timeout=5) as r:
                return r.status, r.headers, r.read()
        except HTTPError as e:
            return e.code, e.headers, e.read()

    def test_sirve_el_portal_con_politica_estricta_y_sin_registrarlo(self):
        for ruta in ESTATICOS:
            estado, cab, cuerpo = self.http(ruta)
            self.assertEqual(estado, 200, ruta)
            self.assertIn("script-src 'self'", cab["Content-Security-Policy"])
            self.assertTrue(cuerpo)
        self.assertEqual(self.c.n, 0)             # servir la página no es actividad en Cnosos
        self.assertEqual(self.http("/portal/../almacen.py")[0], 401)

    def test_operador_solo_con_su_clave(self):
        self.assertEqual(self.http("/operador/base")[0], 401)
        self.assertEqual(self.http("/operador/base", {"X-Operador": "otra"})[0], 401)
        self.assertEqual(self.c.n, 2)             # sin clave es una ruta más de Cnosos: queda en Ariadna
        estado, _, cuerpo = self.http("/operador/base", {"X-Operador": "clave-del-operador"})
        self.assertEqual(estado, 200)
        self.assertEqual(json.loads(cuerpo)["almacen"], "sqlite")
        self.assertEqual(self.http("/operador/eventos?episodio=zz", {"X-Operador": "clave-del-operador"})[0], 400)
        self.assertEqual(self.c.n, 2)             # mirar la base no se registra como actividad

    def test_sin_operador_no_hay_vista(self):
        srv = servidor(self.c)
        hilo = threading.Thread(target=srv.serve_forever, daemon=True)
        hilo.start()
        try:
            req = Request(f"http://127.0.0.1:{srv.server_port}/operador/base", headers={"X-Operador": ""})
            with self.assertRaises(HTTPError) as e:
                self.abrir(req, timeout=5)
            self.assertEqual(e.exception.code, 401)
        finally:
            srv.shutdown()
            hilo.join(timeout=3)
            srv.server_close()


class Interfaz(unittest.TestCase):
    def test_nada_entra_como_html_ni_hay_estilos_en_linea(self):
        js = (PORTAL / "portal.js").read_text(encoding="utf-8")
        self.assertNotRegex(js, r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|\.style\.|setAttribute\(\"style")
        html = (PORTAL / "index.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r"<script>|\sstyle=|\son[a-z]+=")

    def test_el_texto_visible_vive_en_textos(self):
        js = (PORTAL / "portal.js").read_text(encoding="utf-8")
        sin_comentarios = re.sub(r"//.*", "", js)
        # Una frase en español dentro de portal.js sería texto visible fuera de textos.js.
        self.assertNotRegex(sin_comentarios, r"\"[A-ZÁÉÍÓÚ][a-záéíóúñ]+ [a-záéíóúñ]+")


if __name__ == "__main__":
    unittest.main()
