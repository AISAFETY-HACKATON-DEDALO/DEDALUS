"""El panel: sirve la fachada y el operador, exige clave para operar y deja atacar el portal."""
import json
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from dedalus.panel import ARCHIVOS, Panel, servidor


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.panel = Panel()
        self.srv = servidor(self.panel)
        self.hilo = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.hilo.start()
        self.base = f"http://127.0.0.1:{self.srv.server_port}"
        self.abrir = build_opener(ProxyHandler({})).open

    def tearDown(self):
        self.srv.shutdown()
        self.hilo.join(timeout=3)
        self.srv.server_close()
        self.panel.cnosos.almacen.cerrar()

    def http(self, metodo, ruta, cuerpo=None, cab=None):
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = Request(self.base + ruta, data=datos, method=metodo, headers={"Content-Type": "application/json", **(cab or {})})
        try:
            with self.abrir(req, timeout=5) as r:
                return r.status, r.read(), r.headers
        except HTTPError as e:
            return e.code, e.read(), e.headers

    def operar(self, ruta, cuerpo=None):
        estado, datos, _ = self.http("POST" if cuerpo is not None else "GET", ruta, cuerpo, {"X-Panel-Clave": self.panel.clave})
        return estado, json.loads(datos)

    def test_sirve_la_fachada_y_el_panel_con_politica_estricta(self):
        for ruta in ARCHIVOS:
            with self.subTest(ruta=ruta):
                estado, cuerpo, cab = self.http("GET", ruta)
                self.assertEqual(estado, 200)
                self.assertIn("default-src 'none'", cab["Content-Security-Policy"])
        for pagina in ("/", "/portal"):
            html = self.http("GET", pagina)[1].decode()
            self.assertNotIn("<script>", html)
            self.assertNotIn("style=", html)

    def test_el_operador_exige_clave_y_el_portal_no(self):
        self.assertEqual(self.http("GET", "/panel/estado")[0], 403)
        self.assertEqual(self.http("POST", "/panel/minotauro", {})[0], 403)
        self.assertEqual(self.http("GET", "/api/salud")[0], 200)
        self.assertEqual(self.http("GET", "/api/perfil", cab={"Host": "evil.test"})[0], 403)

    def test_atacar_a_mano_queda_en_el_hilo(self):
        cuenta = self.panel.cnosos.cuenta_de_prueba("tomas.mejia")
        token = json.loads(self.http("POST", "/api/login", cuenta)[1])["token"]
        self.assertEqual(self.http("GET", "/api/archivos/6", cab={"Authorization": "Bearer " + token})[0], 404)
        estado, e = self.operar("/panel/estado?desde=0")
        self.assertEqual(estado, 200)
        self.assertEqual([x["intento"] for x in e["eventos_nuevos"]], [None, "idor"])
        self.assertEqual(self.operar("/panel/estado?desde=2")[1]["eventos_nuevos"], [])
        self.assertNotIn(token, json.dumps(e))

    def test_minotauro_dedalo_y_episodio_nuevo(self):
        self.assertEqual(self.operar("/panel/minotauro", {"proveedor": "guion"})[0], 200)
        self.assertEqual(self.operar("/panel/dedalo", {"proveedor": "guion"})[0], 200)
        limite = time.time() + 60
        while time.time() < limite:
            t = self.operar("/panel/estado")[1]["tareas"]
            if not t["minotauro"]["activo"] and not t["dedalo"]["activo"]:
                break
            time.sleep(0.3)
        e = self.operar("/panel/estado")[1]
        self.assertEqual(e["tareas"]["minotauro"]["resumen"]["paso_deteccion"], 6)
        self.assertEqual(sum(1 for r in e["tareas"]["dedalo"]["resultados"] if r["verificado"]), 6)
        self.assertEqual(e["fugas"], 0)
        anterior = e["episodio"]
        estado, r = self.operar("/panel/nuevo", {})
        self.assertEqual(estado, 200)
        self.assertNotEqual(r["episodio"], anterior)

    def test_sin_clave_de_modelo_lo_dice(self):
        import os
        if os.environ.get("GROQ_API_KEY"):
            self.skipTest("hay clave de Groq en el entorno")
        estado, r = self.operar("/panel/minotauro", {"proveedor": "groq"})
        self.assertEqual(estado, 400)
        self.assertIn("GROQ_API_KEY", r["error"])
        self.assertEqual(self.operar("/panel/minotauro", {"proveedor": "otro"})[1], {"error": "parametros"})


if __name__ == "__main__":
    unittest.main()
