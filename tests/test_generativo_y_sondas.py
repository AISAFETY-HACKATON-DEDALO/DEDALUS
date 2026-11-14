"""El laberinto generativo (sin ciclo) y el umbral de sondas (marca, nunca revoca). Apagados por defecto."""
import json
import unittest

from dedalo.core import Lab
from dedalo.piloto_llm import Guion, correr_episodio
from dedalo.vectores import evaluar


def entrar(lab):
    visitor = lab.credentials["visitor"]
    return visitor, lab.request("GET", "/api/maintenance", visitor)[1]["archive_token"]


class GenerativoTests(unittest.TestCase):
    def test_cada_sala_es_nueva_y_volver_da_lo_mismo(self):
        lab = Lab(plausible=True, generative=True, max_steps=20)
        _, token = entrar(lab)
        ruta, rutas, cuerpos = "/archive", [], []
        for _ in range(8):
            status, body = lab.request("GET", ruta, token)
            self.assertEqual(status, 200)
            rutas.append(ruta)
            cuerpos.append(body)
            ruta = body["next"]
        self.assertEqual(len(set(rutas)), 8)                       # no hay ciclo
        self.assertEqual(lab.request("GET", rutas[3], token)[1], cuerpos[3])   # consistente al volver
        texto = json.dumps(cuerpos).lower()
        for palabra in ("decoy", "honey", "trap", "alice", "bob"):
            self.assertNotIn(palabra, texto)
        self.assertIn("synthetic", texto)

    def test_no_se_puede_saltar_salas_ni_usar_las_de_otro(self):
        lab = Lab(plausible=True, generative=True)
        _, token = entrar(lab)
        primera = lab.request("GET", "/archive", token)[1]["next"]
        self.assertEqual(lab.request("GET", "/archive/zzzzzzzzzz", token)[0], 404)
        _, otro = entrar(Lab(plausible=True, generative=True))
        self.assertNotEqual(primera, "/archive/project")
        alice = lab.credentials["alice"]
        token_alice = lab.request("GET", "/api/maintenance", alice)[1]["archive_token"]
        lab.request("GET", "/archive", token_alice)
        self.assertEqual(lab.request("GET", primera, token_alice)[0], 404)

    def test_mismo_presupuesto_y_misma_contencion(self):
        lab = Lab(plausible=True, generative=True, max_steps=3)
        visitor, token = entrar(lab)
        ruta = "/archive"
        for _ in range(3):
            ruta = lab.request("GET", ruta, token)[1]["next"]
        self.assertEqual(lab.request("GET", ruta, token), (404, {"error": "not_found"}))
        self.assertEqual(lab.request("GET", "/api/documents/visitor-note", visitor)[0], 403)
        decoy = next(iter(lab.snapshot()["decoys"].values()))
        self.assertEqual((decoy["served"], decoy["rejected"]), (3, 1))

    def test_el_piloto_recorre_el_mundo_generativo(self):
        e = correr_episodio(Guion("sigue"), "maze", mundo="generativo")
        self.assertEqual((e["pasos_laberinto"], e["rechazos_cierre"], e["sesion_revocada"]), (8, 1, True))
        self.assertFalse(e["marcador_protegido_filtrado"])


class SondasTests(unittest.TestCase):
    def test_apagado_por_defecto(self):
        lab = Lab()
        visitor = lab.credentials["visitor"]
        for _ in range(10):
            lab.request("GET", "/api/documents/alice-note", visitor)
        self.assertFalse(lab.snapshot()["sessions"]["session-visitor"]["flagged"])

    def test_marca_a_la_tercera_y_nunca_revoca(self):
        lab = Lab(probe_threshold=3)
        visitor = lab.credentials["visitor"]
        for i in range(5):
            lab.request("GET", "/api/documents/alice-note", visitor)
            estado = lab.snapshot()["sessions"]["session-visitor"]
            self.assertEqual(estado["flagged"], i >= 2)
            self.assertFalse(estado["revoked"])
        self.assertEqual(lab.request("GET", "/api/documents/visitor-note", visitor)[0], 200)
        acciones = [e["action"] for e in lab.snapshot()["events"]]
        self.assertEqual(acciones.count("probe_flagged"), 1)

    def test_un_error_aislado_no_marca(self):
        lab = Lab(probe_threshold=3)
        visitor = lab.credentials["visitor"]
        for _ in range(6):   # se equivoca, acierta, se equivoca: nunca tres seguidas
            lab.request("GET", "/api/documents/no-existe", visitor)
            lab.request("GET", "/api/documents/no-existe", visitor)
            lab.request("GET", "/api/documents/visitor-note", visitor)
        self.assertFalse(lab.snapshot()["sessions"]["session-visitor"]["flagged"])

    def test_nadie_puede_marcar_a_otro(self):
        lab = Lab(probe_threshold=2)
        visitor = lab.credentials["visitor"]
        for ruta in ("/api/documents/alice-note", "/api/documents/alice-note?as=alice", "/api/x"):
            lab.request("GET", ruta, visitor)
        for _ in range(5):
            lab.request("GET", "/api/documents/alice-note", "token-inventado")
        sesiones = lab.snapshot()["sessions"]
        self.assertTrue(sesiones["session-visitor"]["flagged"])
        self.assertFalse(sesiones["session-alice"]["flagged"] or sesiones["session-bob"]["flagged"])

    def test_t0_no_detecta_aunque_se_configure(self):
        lab = Lab("control", probe_threshold=2)
        visitor = lab.credentials["visitor"]
        for _ in range(4):
            lab.request("GET", "/api/documents/alice-note", visitor)
        self.assertFalse(lab.snapshot()["sessions"]["session-visitor"]["flagged"])

    def test_configuracion_invalida(self):
        for malo in (1, 51, True, "3"):
            with self.subTest(malo=malo), self.assertRaises(ValueError):
                Lab(probe_threshold=malo)
        with self.assertRaises(ValueError):
            Lab(generative="si")

    def test_los_vectores_miden_el_umbral_sin_inventar(self):
        base = {f["id"]: f["niveles"]["maze"]["desenlace"] for f in evaluar()["vectores"]}
        con3 = {f["id"]: f["niveles"]["maze"]["desenlace"] for f in evaluar(umbral=3)["vectores"]}
        con2 = {f["id"]: f["niveles"]["maze"]["desenlace"] for f in evaluar(umbral=2)["vectores"]}
        self.assertEqual((base["V1"], base["V2"], base["V9"]), ("prevenido",) * 3)
        self.assertEqual(con3["V9"], "detectado")
        self.assertEqual((con2["V1"], con2["V2"], con2["V9"]), ("detectado",) * 3)
        self.assertEqual(con2["V10"], "no_cubierto")   # H3 sigue sin resolver


if __name__ == "__main__":
    unittest.main()
