"""ARGOS y los cebos: ¿solo hacen sufrir al atacante, o protegen?

Lo que se prueba aquí es lo que se afirma en la presentación:
  1. Un usuario honesto nunca ve un cebo (0 falsos positivos por cebos).
  2. Un sospechoso recibe un cebo según lo que busca, y es suyo: otra sesión no lo puede usar ni adivinar.
  3. Morder detecta y contiene: después, ni una solicitud más de esa cuenta llega al sistema real («desviar»).
  4. El ritmo solo no encierra (con «marcar»); con «laberinto» sí, y eso cuesta un falso positivo medible.
  5. Queda inteligencia: qué buscó, qué técnicas usó, en qué paso se le detectó.
"""
import json
import unittest

from dedalus.argos import Argos
from dedalus.cebos import BASE_ID, Cebos
from dedalus.cnosos import Cnosos
from dedalus.semilla import MARCADOR

CONTRATISTA, INGENIERA = "tomas.mejia", "ana.rios"


class Reloj:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class Base(unittest.TestCase):
    def nuevo(self, **kw):
        self.reloj = Reloj()
        self.c = Cnosos(clock=self.reloj, semilla="prueba", **kw)
        return self.c

    def tearDown(self):
        self.c.almacen.cerrar()

    def login(self, usuario):
        return self.c.solicitud("POST", "/api/login", {},
                                json.dumps({"usuario": usuario, "clave": self.c._claves[usuario]}).encode())

    def get(self, ruta, token, avanzar=15.0):
        self.reloj.t += avanzar          # por defecto, ritmo humano: 4 por minuto
        return self.c.solicitud("GET", ruta, {"Authorization": "Bearer " + token})

    def nivel(self, token):
        return self.c.argos.perfil(self.c.sesiones[token].ref).nivel


class ArgosDeterminista(unittest.TestCase):
    def test_mismas_entradas_mismo_nivel(self):
        a, b = Argos(), Argos()
        for i, s in enumerate(["idor", None, "escalada", None]):
            ra, rb = a.observar("s1", i, i * 10.0, s), b.observar("s1", i, i * 10.0, s)
            self.assertEqual(ra, rb)
        self.assertEqual(a.informe("s1"), b.informe("s1"))
        self.assertEqual(a.informe("s1")["nivel"], "sospechoso")

    def test_el_ritmo_suma_una_vez_por_ventana(self):
        a = Argos(ritmo_max=5, ventana_s=60)
        for i in range(30):
            a.observar("s1", i, i * 0.5)          # 30 solicitudes en 15 s
        self.assertEqual(a.informe("s1")["senales"], {"ritmo": 1})
        self.assertEqual(a.informe("s1")["nivel"], "observado")     # ritmo de máquina, no sospechoso
        self.assertEqual(a.informe("s1")["ritmo_max"], 30)

    def test_cebos_deterministas_y_por_sesion(self):
        c = Cebos("x")
        self.assertEqual(c.archivo("s1", "planos")["id"], Cebos("x").archivo("s1", "planos")["id"])
        self.assertNotEqual(c.archivo("s1", "planos")["id"], c.archivo("s2", "planos")["id"])


class CebosHonestos(Base):
    def test_el_usuario_honesto_nunca_ve_un_cebo(self):
        self.nuevo()
        t = self.login(INGENIERA)[1]["token"]
        for ruta in ("/api/perfil", "/api/archivos", "/api/buscar?q=represa", "/api/buscar?q=planos",
                     "/api/tiquetes", "/api/buscar?q=contraseña"):
            _, datos = self.get(ruta, t)
            filas = datos.get("archivos") or datos.get("resultados") or []
            self.assertFalse([f for f in filas if f["id"] >= BASE_ID], ruta)
        self.assertEqual(self.nivel(t), "normal")
        self.assertEqual(self.c.foto()["cebos"], [])

    def test_buscar_algo_sensible_es_interes_no_delito(self):
        self.nuevo()
        t = self.login(INGENIERA)[1]["token"]
        self.get("/api/buscar?q=planos", t)
        inf = self.c.argos.informe(self.c.sesiones[t].ref)
        self.assertEqual((inf["nivel"], inf["intereses"]), ("normal", ["planos"]))


class CebosAlSospechoso(Base):
    def sospechoso(self, **kw):
        self.nuevo(**kw)
        t = self.login(CONTRATISTA)[1]["token"]
        self.get("/api/archivos/6", t)            # idor
        self.get("/api/admin/usuarios", t)        # escalada → 4 puntos: sospechoso
        self.assertEqual(self.nivel(t), "sospechoso")
        return t

    def test_recibe_el_cebo_de_lo_que_busca(self):
        t = self.sospechoso()
        r = self.get("/api/buscar?q=planos represa", t)[1]["resultados"]
        self.assertEqual(len(r), 1)
        self.assertIn("Represa", r[0]["titulo"])
        self.assertGreaterEqual(r[0]["id"], BASE_ID)
        # el mismo cebo cada vez: determinista
        self.assertEqual(self.get("/api/buscar?q=planos", t)[1]["resultados"][0]["id"], r[0]["id"])

    def test_morder_detecta_contiene_y_no_filtra(self):
        t = self.sospechoso()
        cebo = self.get("/api/buscar?q=planos", t)[1]["resultados"][0]
        estado, datos = self.get(f"/api/archivos/{cebo['id']}", t)
        self.assertEqual(estado, 200)
        self.assertIn("svc-respaldo", datos["contenido"])            # parece valioso y lleva a la siguiente trampa
        self.assertNotIn(MARCADOR, json.dumps(datos))
        e = self.c.ariadna[-1]
        self.assertEqual((e["accion"], e["argos"]), ("icaro", "confirmado"))
        self.assertTrue(self.c.sesiones[t].revocada)
        self.assertEqual(self.c.fugas, 0)

    def test_el_cebo_es_de_una_sola_sesion(self):
        t = self.sospechoso()
        cebo = self.get("/api/buscar?q=planos", t)[1]["resultados"][0]
        otra = self.login(INGENIERA)[1]["token"]
        self.assertEqual(self.get(f"/api/archivos/{cebo['id']}", otra)[0], 404)   # igual que un archivo inexistente
        self.assertFalse(self.c.sesiones[otra].revocada)
        self.assertEqual(self.get(f"/api/archivos/{BASE_ID + 1}", t)[0], 404)   # adivinar otro número no sirve

    def test_cortar_responde_401_y_la_cuenta_puede_volver(self):
        t = self.sospechoso(tras_icaro="cortar")
        cebo = self.get("/api/buscar?q=planos", t)[1]["resultados"][0]
        self.get(f"/api/archivos/{cebo['id']}", t)
        self.assertEqual(self.get("/api/archivos", t)[0], 401)
        # el límite de «cortar»: la contraseña sigue sirviendo y vuelve al portal real
        nuevo = self.login(CONTRATISTA)[1]["token"]
        self.assertFalse(self.c.sesiones[nuevo].laberinto)

    def test_desviar_nada_de_esa_cuenta_vuelve_al_sistema_real(self):
        t = self.sospechoso(tras_icaro="desviar")
        cebo = self.get("/api/buscar?q=planos", t)[1]["resultados"][0]
        self.get(f"/api/archivos/{cebo['id']}", t)
        n_deteccion = self.c.ariadna[-1]["n"]
        estado, _ = self.get("/api/archivos", t)                     # la sesión vieja «sigue funcionando»
        self.assertEqual(estado, 200)
        self.assertTrue(self.c.ariadna[-1]["laberinto"])
        nuevo = self.login(CONTRATISTA)[1]["token"]                  # y su contraseña real abre el laberinto
        self.assertTrue(self.c.sesiones[nuevo].laberinto)
        self.get("/api/archivos/6", nuevo)
        self.get("/api/perfil", nuevo)
        reales = [e for e in self.c.ariadna if e["n"] > n_deteccion and not e["laberinto"]]
        self.assertEqual(reales, [], "ninguna solicitud de la cuenta delatada llegó al portal real")
        self.assertGreaterEqual(self.c.desvios, 2)
        self.assertEqual(self.c.fugas, 0)

    def test_queda_inteligencia_sobre_el_atacante(self):
        t = self.sospechoso()
        cebo = self.get("/api/buscar?q=planos represa", t)[1]["resultados"][0]
        self.get(f"/api/archivos/{cebo['id']}", t)
        inf = self.c.foto()["argos"][self.c.sesiones[t].ref]
        self.assertEqual(inf["nivel"], "confirmado")
        self.assertEqual(inf["intereses"], ["planos represa", "planos"][:len(inf["intereses"])])
        self.assertIn("T1213 Datos de repositorios de información", inf["tecnicas"])
        self.assertIn("TA0009 Recolección (mordió un cebo)", inf["tecnicas"])
        self.assertLess(inf["paso_sospecha"], inf["paso_confirmado"])
        niveles = [a["nivel"] for a in self.c.alertas]
        self.assertEqual(niveles, ["observado", "sospechoso", "confirmado"])


class Ritmo(Base):
    def rafaga(self, usuario, n=8, **kw):
        self.nuevo(**kw)
        t = self.login(usuario)[1]["token"]
        for _ in range(n):
            self.get("/api/perfil", t, avanzar=1.0)          # 8 solicitudes en 8 s: ritmo de máquina
        return t

    def test_marcar_el_ritmo_solo_no_encierra_al_honesto(self):
        t = self.rafaga(INGENIERA, ritmo="marcar")
        self.assertEqual(self.nivel(t), "observado")
        self.assertFalse(self.c.sesiones[t].revocada)
        self.assertEqual(self.get("/api/archivos", t)[0], 200)

    def test_laberinto_el_ritmo_encierra_y_eso_es_un_falso_positivo(self):
        t = self.rafaga(INGENIERA, ritmo="laberinto", tras_icaro="desviar")
        self.assertTrue(self.c.sesiones[t].revocada)               # la ingeniera honesta quedó encerrada
        self.get("/api/archivos", t)
        self.assertTrue(self.c.ariadna[-1]["laberinto"])


if __name__ == "__main__":
    unittest.main()
