"""Desvío por ataque: la sesión que ataca pasa al laberinto sin tocar una hiedra. Apagado por defecto."""
import json
import unittest

from dedalus.agentes import Guion, episodio
from dedalus.cnosos import Cnosos
from dedalus.semilla import MARCADOR

CONTRATISTA = "tomas.mejia"
INYECCION = "/api/buscar?q=%27%20OR%201%3D1--"


class Base(unittest.TestCase):
    desvio, respuesta = 3, "contener"

    def setUp(self):
        self.c = Cnosos(desvio=self.desvio, respuesta=self.respuesta, pasos_laberinto=6)

    def tearDown(self):
        self.c.almacen.cerrar()

    def token(self, usuario=CONTRATISTA):
        cuerpo = json.dumps({"usuario": usuario, "clave": self.c._claves[usuario]}).encode()
        return self.c.solicitud("POST", "/api/login", {}, cuerpo)[1]["token"]

    def get(self, ruta, token, cab=None):
        return self.c.solicitud("GET", ruta, {**(cab or {}), "Authorization": "Bearer " + token})

    def real(self, usuario=CONTRATISTA):
        return next(s for s in self.c.foto()["sesiones"] if s["usuario"] == usuario and not s["laberinto"])


class Apagado(Base):
    desvio = None

    def test_por_defecto_nada_cambia(self):
        t = self.token()
        self.assertEqual(self.get(INYECCION, t)[0], 400)
        self.assertEqual(self.get("/api/descargas?nombre=../../etc/passwd", t)[0], 400)
        self.assertEqual(self.get("/api/admin/usuarios", t, {"X-Rol": "administrador"})[0], 403)
        estado = self.real()
        self.assertFalse(estado["revocada"] or estado["marcada"])
        self.assertEqual(self.c.foto()["desviadas"], 0)


class Desvio(Base):
    def test_un_ataque_inequivoco_basta_y_parece_funcionar(self):
        for ruta, cab in ((INYECCION, None), ("/api/descargas?nombre=../../etc/passwd", None),
                          ("/api/perfil", {"X-Rol": "administrador"})):
            with self.subTest(ruta=ruta):
                c = Cnosos(desvio=3)
                self.addCleanup(c.almacen.cerrar)
                self.c, t = c, None
                t = self.token()
                estado, _ = self.get(ruta, t, cab)
                e = self.c.ariadna[-1]
                self.assertEqual((estado, e["accion"], e["laberinto"], e["afectada"]), (200, "desvio", True, "s1"))
                self.assertTrue(self.real()["revocada"])

    def test_tras_el_desvio_todo_lo_que_ve_es_falso_y_no_hay_fuga(self):
        t = self.token()
        self.get(INYECCION, t)
        estado, planos = self.get("/api/archivos/6", t)          # los planos secretos, por número
        self.assertEqual(estado, 200)
        self.assertNotIn(MARCADOR, json.dumps(planos))
        self.assertIn("siguiente", self.get("/api/archivos", t)[1])   # la lista interminable del laberinto
        self.assertEqual(self.get("/api/admin/usuarios", t)[0], 200)
        self.assertEqual(self.c.fugas, 0)
        self.assertTrue(all(e["laberinto"] for e in list(self.c.ariadna)[2:]))

    def test_su_perfil_no_delata_el_cambio(self):
        t = self.token()
        antes = self.get("/api/perfil", t)[1]
        self.get(INYECCION, t)
        self.assertEqual(self.get("/api/perfil", t)[1], antes)

    def test_lo_ambiguo_necesita_repetirse(self):
        t = self.token()
        self.assertEqual(self.get("/api/archivos/6", t)[0], 404)          # un documento ajeno: puede ser un error
        self.assertEqual(self.get("/api/admin/usuarios", t)[0], 403)      # dos
        self.assertFalse(self.real()["revocada"])
        self.assertEqual(self.get("/api/archivos/9", t)[0], 200)          # tres: desviado
        self.assertEqual(self.c.ariadna[-1]["accion"], "desvio")
        self.assertTrue(self.real()["revocada"])
        self.assertEqual(self.real()["intentos"], {"idor": 2, "escalada": 1})

    def test_el_usuario_honesto_que_se_equivoca_no_cae(self):
        ana = self.token("ana.rios")
        self.assertEqual(self.get("/api/admin/usuarios", ana)[0], 403)    # un clic en un enlace que no era
        self.assertEqual(self.get("/api/archivos/9", ana)[0], 404)        # un enlace viejo
        for ruta in ("/api/perfil", "/api/archivos", "/api/tiquetes", "/api/buscar?q=planos", "/api/archivos/6"):
            self.assertEqual(self.get(ruta, ana)[0], 200)
        estado = self.real("ana.rios")
        self.assertFalse(estado["revocada"] or estado["marcada"])
        self.assertIn(MARCADOR, json.dumps(self.get("/api/archivos/6", ana)[1]))   # sigue viendo lo suyo, de verdad

    def test_un_apostrofo_no_es_un_ataque(self):
        ana = self.token("ana.rios")
        self.get("/api/buscar?q=O%27Brien", ana)                           # cuenta como duda, no como inyección
        self.assertFalse(self.real("ana.rios")["revocada"])
        self.assertEqual(self.get("/api/archivos/6", ana)[0], 200)

    def test_limite_tres_errores_honestos_tambien_desvian(self):
        # Falso positivo posible, a la vista: el umbral no distingue tres descuidos de tres sondas.
        ana = self.token("ana.rios")
        for ruta in ("/api/admin/usuarios", "/api/archivos/9", "/api/buscar?q=O%27Brien"):
            self.get(ruta, ana)
        self.assertTrue(self.real("ana.rios")["revocada"])

    def test_nadie_desvia_a_otro(self):
        intruso, ana = self.token(), self.token("ana.rios")
        self.get(INYECCION, intruso)
        self.get("/api/perfil", intruso, {"X-Forwarded-User": "ana.rios"})
        for _ in range(5):
            self.c.solicitud("GET", "/api/archivos/6", {"Authorization": "Bearer inventado"})
        self.assertTrue(self.real()["revocada"])
        self.assertFalse(self.real("ana.rios")["revocada"] or self.real("ana.rios")["marcada"])
        self.assertEqual(self.get("/api/archivos/6", ana)[0], 200)

    def test_el_laberinto_del_desvio_tambien_se_acaba(self):
        t = self.token()
        estados = [self.get(INYECCION, t)[0]] + [self.get("/api/archivos", t)[0] for _ in range(7)]
        self.assertEqual(estados[:6], [200] * 6)
        self.assertEqual(estados[-1], 401)                                 # se cierra como una sesión vencida

    def test_la_hiedra_sigue_funcionando(self):
        t = self.token()
        clave = self.get("/.env", t)[1]["clave"]                           # ambiguo: uno solo no desvía
        self.assertFalse(self.real()["revocada"])
        cuerpo = json.dumps({"usuario": "svc-respaldo", "clave": clave}).encode()
        self.assertEqual(self.c.solicitud("POST", "/api/login", {}, cuerpo)[0], 200)
        self.assertEqual(self.c.ariadna[-1]["accion"], "icaro")
        self.assertTrue(self.real()["revocada"])

    def test_el_agente_de_guion_cae_antes(self):
        _, sin = episodio(Cnosos(), Guion(), salida=lambda *_: None)
        _, con = episodio(self.c, Guion(), salida=lambda *_: None)
        self.assertIsNotNone(sin["paso_deteccion"])
        self.assertLess(con["paso_deteccion"], sin["paso_deteccion"])
        self.assertEqual((sin["fugas"], con["fugas"]), (0, 0))

    def test_configuracion_invalida(self):
        for malo in (0, 21, True, "3"):
            with self.subTest(malo=malo), self.assertRaises(ValueError):
                Cnosos(desvio=malo)


class Observar(Base):
    respuesta = "observar"

    def test_observar_anota_y_no_desvia(self):
        t = self.token()
        self.assertEqual(self.get(INYECCION, t)[0], 400)
        estado = self.real()
        self.assertEqual((estado["marcada"], estado["revocada"]), (True, False))
        self.assertEqual(self.c.ariadna[-1]["accion"], "observado")
        self.assertEqual(self.get("/api/perfil", t)[0], 200)


if __name__ == "__main__":
    unittest.main()
