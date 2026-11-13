"""La consola local: llave por arranque, solo loopback, credenciales que no salen del proceso."""
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from dedalo.consola import ARCHIVOS, Consola, servidor


class ConsolaTests(unittest.TestCase):
    def setUp(self):
        self.consola = Consola()
        self.srv = servidor(self.consola)
        self.hilo = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.hilo.start()
        self.base = f"http://127.0.0.1:{self.srv.server_port}"
        self.abrir = build_opener(ProxyHandler({})).open

    def tearDown(self):
        self.srv.shutdown()
        self.hilo.join(timeout=3)
        self.srv.server_close()
        self.consola.cerrar()

    def http(self, ruta, cuerpo=None, clave=True, cabeceras=None, crudo=None):
        cab = {"X-Consola-Clave": self.consola.clave} if clave else {}
        datos = crudo
        if cuerpo is not None:
            datos = json.dumps(cuerpo).encode()
        if datos is not None:
            cab["Content-Type"] = "application/json"
        cab.update(cabeceras or {})
        try:
            with self.abrir(Request(self.base + ruta, data=datos, headers=cab), timeout=5) as r:
                return r.status, r.read(), r.headers
        except HTTPError as e:
            return e.code, e.read(), e.headers

    def pedir(self, actor, ruta, via="sesion", de=None):
        estado, cuerpo, _ = self.http("/consola/pedir", {"actor": actor, "via": via, "de": de, "ruta": ruta})
        return estado, json.loads(cuerpo)

    def estado(self):
        return json.loads(self.http("/consola/estado")[1])

    def secretos(self):
        lab = self.consola.banco.lab
        return [*lab.credentials.values(), *lab.honey]

    def test_la_pagina_se_sirve_con_politica_estricta(self):
        for ruta in ARCHIVOS:
            with self.subTest(ruta=ruta):
                estado, cuerpo, cab = self.http(ruta, clave=False)
                self.assertEqual(estado, 200)
                self.assertTrue(cuerpo)
                self.assertIn("default-src 'none'", cab["Content-Security-Policy"])
                self.assertEqual(cab["X-Content-Type-Options"], "nosniff")
        pagina = self.http("/", clave=False)[1].decode()
        self.assertNotIn("<script>", pagina)          # ningún código en línea: la política no lo dejaría correr
        self.assertNotIn("style=", pagina)

    def test_nada_fuera_de_la_lista(self):
        for ruta in ("/../core.py", "/fuentes/../app.js", "/consola.py", "/fuentes/", "/app.js.map", "/%2e%2e/core.py"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.http(ruta, clave=False)[0], 404)

    def test_sin_clave_no_hay_consola(self):
        self.assertEqual(self.http("/consola/estado", clave=False)[0], 403)
        self.assertEqual(self.http("/consola/estado", clave=False, cabeceras={"X-Consola-Clave": "x" * 24})[0], 403)
        self.assertEqual(self.http("/consola/pedir", {"actor": "visitor", "ruta": "/api/documents"}, clave=False)[0], 403)
        self.assertEqual(self.consola.banco.pedidos, 0)

    def test_solo_local_y_mismo_origen(self):
        for cab in ({"Host": "evil.test"}, {"Host": f"localhost:{self.srv.server_port}"}, {"Origin": "https://evil.test"}):
            with self.subTest(cab=cab):
                self.assertEqual(self.http("/consola/estado", cabeceras=cab)[0], 403)
                self.assertEqual(self.http("/", clave=False, cabeceras=cab)[0], 403)
        self.assertEqual(self.http("/consola/estado", cabeceras={"Origin": self.base})[0], 200)

    def test_cuerpos_malformados(self):
        self.assertEqual(self.http("/consola/pedir", crudo=b"{" + b" " * 3000 + b"}")[0], 413)
        self.assertEqual(self.http("/consola/pedir", crudo=b"no es json")[0], 400)
        self.assertEqual(self.http("/consola/pedir", crudo=b"[1]")[0], 400)
        self.assertEqual(self.http("/consola/pedir", crudo=b"{}", cabeceras={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.http("/consola/otra", {})[0], 404)

    def test_rutas_que_no_salen_del_laboratorio(self):
        for ruta in ("https://example.com/", "//example.com/x", "archive", "/a b", "/a\\b", "/á", "/" + "a" * 200, None, 7):
            with self.subTest(ruta=ruta):
                estado, cuerpo = self.pedir("visitor", ruta)
                self.assertEqual((estado, cuerpo), (400, {"error": "ruta"}))
        self.assertEqual(self.pedir("mallory", "/api/documents")[0], 400)
        self.assertEqual(self.pedir("visitor", "/api/documents", via="admin")[0], 400)
        self.assertEqual(self.consola.banco.pedidos, 0)

    def test_permisos_y_marcador(self):
        estado, r = self.pedir("alice", "/api/documents/alice-note")
        self.assertEqual((estado, r["estado"]), (200, 200))
        self.assertIn("PROTECTED", r["cuerpo"]["content"])        # su dueña sí lo lee
        _, r = self.pedir("visitor", "/api/documents/alice-note")
        self.assertEqual((r["estado"], r["entrada"]["motivo"], r["entrada"]["fuga"]), (404, "document_denied", False))
        self.assertEqual(self.estado()["cuenta"], {"pedidos": 2, "fugas": 0, "eventos": 2})

    def test_el_token_nunca_llega_al_navegador(self):
        _, r = self.pedir("visitor", "/api/maintenance")
        self.assertEqual(r["cuerpo"]["archive_token"], "token decoy-1 (tachado)")
        _, r2 = self.pedir("visitor", "/archive?eco=1", via="senuelo")
        todo = json.dumps([r, r2, self.estado()])
        for secreto in self.secretos():
            self.assertNotIn(secreto, todo)
        self.assertEqual(self.estado()["hallados"], {"visitor": "decoy-1"})

    def test_sin_token_no_hay_laberinto(self):
        self.assertEqual(self.pedir("visitor", "/archive", via="senuelo"), (409, {"error": "sin_senuelo"}))
        self.assertEqual(self.pedir("visitor", "/archive", via="senuelo", de=["alice"])[0], 409)
        self.assertEqual(self.pedir(["visitor"], "/archive")[0], 400)

    def test_recorrido_completo_revoca_solo_al_origen(self):
        self.pedir("visitor", "/api/maintenance")
        ruta, pasos = "/archive", []
        for _ in range(10):
            _, r = self.pedir("visitor", ruta, via="senuelo")
            pasos.append(r["estado"])
            if r["estado"] != 200:
                break
            ruta = r["cuerpo"]["next"]
        self.assertEqual(pasos, [200] * 8 + [429])
        e = self.estado()
        self.assertTrue(e["sesiones"]["visitor"]["revocada"])
        self.assertFalse(e["sesiones"]["alice"]["revocada"])
        self.assertEqual((e["senuelos"][0]["servidas"], e["senuelos"][0]["rechazadas"], e["senuelos"][0]["sala"]), (8, 1, 3))
        self.assertEqual(self.pedir("visitor", "/api/documents/visitor-note")[1]["estado"], 403)
        self.assertEqual(self.pedir("alice", "/api/documents/alice-note")[1]["estado"], 200)
        primero = next(x for x in e["libro"] if x["via"] == "senuelo")
        self.assertEqual((primero["accion"], primero["afectado"]), ("revoked", "visitor"))

    def test_token_filtrado_tumba_a_su_duena(self):
        # Limitación conocida (reviews/claude.md, H3): la interfaz la deja ver, no la esconde.
        self.pedir("alice", "/api/maintenance")
        _, r = self.pedir("visitor", "/archive", via="senuelo", de="alice")
        self.assertEqual(r["entrada"]["afectado"], "alice")
        e = self.estado()
        self.assertTrue(e["sesiones"]["alice"]["revocada"])
        self.assertFalse(e["sesiones"]["visitor"]["revocada"])

    def test_operador_ventana_restaurar_y_reiniciar(self):
        self.assertEqual(self.http("/consola/operar", {"accion": "ventana", "actor": "alice"})[0], 200)
        self.assertEqual(self.estado()["sesiones"]["alice"]["ventana"]["hits_left"], 3)
        self.pedir("alice", "/api/maintenance")
        _, r = self.pedir("alice", "/archive", via="senuelo")
        self.assertEqual(r["entrada"]["accion"], "audit_acknowledged")
        self.assertFalse(self.estado()["sesiones"]["alice"]["revocada"])
        self.pedir("visitor", "/api/maintenance")
        self.pedir("visitor", "/archive", via="senuelo")
        self.http("/consola/operar", {"accion": "restaurar", "actor": "visitor"})
        self.assertFalse(self.estado()["sesiones"]["visitor"]["revocada"])
        antes = self.estado()["episodio"]
        estado, cuerpo, _ = self.http("/consola/operar", {"accion": "reiniciar", "mode": "static", "response": "observe"})
        nuevo = json.loads(cuerpo)
        self.assertEqual((estado, nuevo["modo"], nuevo["respuesta"], nuevo["libro"]), (200, "static", "observe", []))
        self.assertNotEqual(nuevo["episodio"], antes)

    def test_operador_rechaza_lo_que_no_conoce(self):
        for cuerpo in ({"accion": "borrar"}, {"accion": "ventana", "actor": "mallory"}, {"accion": "restaurar"},
                       {"accion": "reiniciar", "mode": "abierto"}, {"accion": "reiniciar", "max_steps": 10_000},
                       {"accion": "reiniciar", "ttl": "siempre"}):
            with self.subTest(cuerpo=cuerpo):
                self.assertEqual(self.http("/consola/operar", cuerpo)[0], 400)
        self.assertEqual(self.estado()["modo"], "maze")           # el episodio anterior sigue vivo

    def test_la_foto_del_motor_trae_limites_y_edad(self):
        self.pedir("visitor", "/api/maintenance")
        e = self.estado()
        self.assertEqual(e["limites"], {"pasos": 8, "vigencia": 120})
        self.assertGreaterEqual(e["senuelos"][0]["edad"], 0)


if __name__ == "__main__":
    unittest.main()
