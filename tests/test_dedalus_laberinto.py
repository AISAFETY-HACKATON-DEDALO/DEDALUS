"""El laberinto generativo: coherente, sin fondo para el atacante, finito y barato para nosotros."""
import json
import time
import unittest

from dedalus.cnosos import Cnosos
from dedalus.laberinto import Laberinto
from dedalus.semilla import MARCADOR


class Generador(unittest.TestCase):
    def test_coherente_la_misma_pregunta_da_la_misma_respuesta(self):
        a, b = Laberinto("semilla"), Laberinto("semilla")
        self.assertEqual(a.responder("h1", 2, "/api/archivos/207", {})[:2], b.responder("h1", 2, "/api/archivos/207", {})[:2])
        self.assertNotEqual(Laberinto("otra").contenido(2, 207), a.contenido(2, 207))

    def test_siempre_hay_otra_pagina_y_otro_servidor(self):
        l = Laberinto("s")
        _, datos, _ = l.responder("h1", 0, "/api/archivos", {"pagina": ["9999"]})
        self.assertEqual(datos["siguiente"], "/api/archivos?pagina=10000")
        _, config, _ = l.responder("h1", 4, "/.env", {})
        self.assertEqual(config["llave"], l.hiedra("h1", 5))
        self.assertNotEqual(l.hiedra("h1", 5), l.hiedra("h2", 5))     # cada entrada trepa por su propia hiedra

    def test_nunca_sale_el_secreto_y_cuesta_microsegundos(self):
        l = Laberinto()
        t0 = time.perf_counter()
        textos = [json.dumps(l.responder("h", n % 7, r, {})[1]) for n in range(300)
                  for r in ("/api/archivos", "/api/archivos/5", "/api/admin", "/.env", "/api/tiquetes")]
        por_paso_ms = (time.perf_counter() - t0) * 1000 / len(textos)
        self.assertFalse(any(MARCADOR in t for t in textos))
        self.assertLess(por_paso_ms, 2.0)


class EnCnosos(unittest.TestCase):
    def setUp(self):
        self.c = Cnosos(pasos_laberinto=6)

    def tearDown(self):
        self.c.almacen.cerrar()

    def get(self, ruta, token):
        return self.c.solicitud("GET", ruta, {"Authorization": "Bearer " + token})

    def entrar(self):
        _, d = self.c.solicitud("POST", "/api/login", {}, json.dumps(self.c.cuenta_de_prueba("tomas.mejia")).encode())
        clave = self.get("/api/config/respaldo", d["token"])[1]["clave"]
        _, d2 = self.c.solicitud("POST", "/api/login", {}, json.dumps({"usuario": "svc-respaldo", "clave": clave}).encode())
        return d["token"], d2["token"]

    def test_la_hiedra_trepa_y_no_revoca_mas_de_una_vez(self):
        real, falso = self.entrar()
        llave = self.get("/api/config", falso)[1]["llave"]
        self.assertEqual(self.get("/api/admin/usuarios", llave)[0], 200)
        e = self.c.ariadna[-1]
        self.assertEqual((e["accion"], e["nivel"], e["laberinto"]), ("trepa", 1, True))
        revocadas = [s for s in self.c.foto()["sesiones"] if s["revocada"]]
        self.assertEqual(len(revocadas), 1)                         # solo la sesión real del contratista
        self.assertEqual(self.get("/api/perfil", real)[0], 401)

    def test_el_presupuesto_es_por_hiedra_aunque_trepe(self):
        _, falso = self.entrar()
        llave = self.get("/api/config", falso)[1]["llave"]           # paso 2 del laberinto (el login fue el 1)
        estados = [self.get("/api/archivos", llave)[0] for _ in range(6)]
        self.assertEqual(estados, [200, 200, 200, 200, 200, 401])    # 6 pasos en total, sin importar el nivel
        foto = self.c.foto()["laberinto"]
        self.assertEqual(foto["nivel_max"], 1)
        self.assertGreater(foto["costo_ms"], 0)
        self.assertEqual(self.c.fugas, 0)


if __name__ == "__main__":
    unittest.main()
