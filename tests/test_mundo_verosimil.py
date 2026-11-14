"""H5 y H6: el laberinto verosímil no se nombra ni cierra distinto. La contención no cambia."""
import json
import unittest

from dedalo.core import Lab


def recorrer(lab):
    visitor = lab.credentials["visitor"]
    token = lab.request("GET", "/api/maintenance", visitor)[1]["archive_token"]
    cuerpos, ruta = [], "/archive"
    for _ in range(lab.max_steps):
        status, body = lab.request("GET", ruta, token)
        cuerpos.append((status, body))
        ruta = body.get("next", ruta)
    return visitor, token, cuerpos


class MundoVerosimilTests(unittest.TestCase):
    def test_por_defecto_nada_cambia(self):
        lab = Lab()
        self.assertFalse(lab.plausible)
        _, token, cuerpos = recorrer(lab)
        self.assertIn("decoy", json.dumps(cuerpos).lower())  # H6, tal como llegó al evento
        self.assertEqual(lab.request("GET", "/archive", token), (429, {"error": "engagement_closed"}))

    def test_el_mundo_verosimil_no_se_nombra(self):
        lab = Lab(plausible=True)
        _, _, cuerpos = recorrer(lab)
        texto = json.dumps(cuerpos).lower()
        self.assertTrue(all(status == 200 for status, _ in cuerpos))
        for palabra in ("decoy", "honey", "engagement", "trap"):
            self.assertNotIn(palabra, texto)
        self.assertIn("synthetic", texto)  # sigue siendo, a la vista, un dato sintético

    def test_el_cierre_es_una_negativa_comun_y_sigue_contando(self):
        lab = Lab(plausible=True, max_steps=2)
        visitor, token, _ = recorrer(lab)
        cierre = lab.request("GET", "/archive", token)
        # Igual que la negativa uniforme de un documento o una ruta que no existe.
        self.assertEqual(cierre, (404, {"error": "not_found"}))
        decoy = next(iter(lab.snapshot()["decoys"].values()))
        self.assertEqual((decoy["served"], decoy["rejected"]), (2, 1))

    def test_la_contencion_es_identica(self):
        for plausible in (False, True):
            with self.subTest(plausible=plausible):
                lab = Lab(plausible=plausible)
                visitor, _, _ = recorrer(lab)
                self.assertEqual(lab.request("GET", "/api/documents/visitor-note", visitor)[0], 403)
                alice = lab.request("GET", "/api/documents/alice-note", lab.credentials["alice"])
                self.assertEqual(alice[0], 200)

    def test_configuracion_invalida(self):
        with self.assertRaises(ValueError):
            Lab(plausible="si")


if __name__ == "__main__":
    unittest.main()
