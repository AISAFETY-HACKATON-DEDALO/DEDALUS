"""El informe del piloto: un archivo solo, sin código, con las letras dentro."""
import unittest

from dedalo.demo import run_mode
from dedalo.pilot import render


class InformeTests(unittest.TestCase):
    def test_informe_autonomo_y_sin_codigo(self):
        config = {"title": "prueba", "response": "enforce", "max_steps": 3, "ttl_seconds": 30}
        filas = [run_mode("maze", max_steps=3, ttl=30, strategy=s) for s in ("follow", "audit", "audit_granted")]
        html = render({"version": "0.3", "created_utc": "prueba", "config": config, "runs": filas})
        self.assertNotIn("<script", html)
        self.assertNotIn("http://", html.replace("http://scripts.sil.org", ""))   # nada que cargar de fuera
        self.assertNotIn("https://", html)
        self.assertIn("data:font/woff2;base64,", html)
        self.assertEqual(html.count("<tr><td>"), 3)
        self.assertEqual(html.count('<td class="si">REVOCADA</td>'), 2)   # sigue pistas y auditor sin ventana
        self.assertEqual(html.count('<i class="cierre"'), 3)               # cada recorrido termina en el cierre

    def test_la_foto_no_trae_secretos(self):
        fila = run_mode("maze", max_steps=3, ttl=30)
        html = render({"created_utc": "prueba", "runs": [fila],
                       "config": {"title": "t", "response": "enforce", "max_steps": 3, "ttl_seconds": 30}})
        self.assertNotIn("archive_token", html)
        self.assertNotIn("Bearer", html)


if __name__ == "__main__":
    unittest.main()
