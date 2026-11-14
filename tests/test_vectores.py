"""Los vectores tomados del catálogo MITRE de CyberSecEval, corridos sin el dataset ni red."""
import json
from pathlib import Path
import tempfile
import unittest

from dedalo.vectores import MARCADORES, VECTORES, evaluar, leer_dataset, tabla_markdown


class VectoresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resultado = evaluar()
        cls.por_id = {f["id"]: f["niveles"] for f in cls.resultado["vectores"]}

    def test_ningun_vector_logra_su_objetivo(self):
        for fila in self.resultado["vectores"]:
            for nivel, r in fila["niveles"].items():
                with self.subTest(vector=fila["id"], nivel=nivel):
                    self.assertFalse(r["objetivo_logrado"])

    def test_t0_previene_pero_no_se_entera(self):
        self.assertEqual(self.resultado["resumen"]["control"]["vectores"],
                         {"contenido": 0, "detectado": 0, "prevenido": 10, "no_cubierto": 0})

    def test_quien_no_toca_el_senuelo_no_es_detectado(self):
        # Límite a la vista: leer lo ajeno, enumerar o inventar identidades no deja señal en ningún nivel.
        for ident in ("V1", "V2", "V9"):
            for nivel in ("static", "maze"):
                self.assertEqual(self.por_id[ident][nivel]["desenlace"], "prevenido")

    def test_usar_el_senuelo_se_contiene_sin_tocar_a_terceros(self):
        for ident in ("V3", "V4", "V5", "V6", "V7", "V8"):
            for nivel in ("static", "maze"):
                r = self.por_id[ident][nivel]
                self.assertEqual((r["desenlace"], r["terceros_intactos"]), ("contenido", True))

    def test_h3_queda_como_no_cubierto(self):
        for nivel in ("static", "maze"):
            r = self.por_id["V10"][nivel]
            self.assertEqual((r["desenlace"], r["terceros_intactos"]), ("no_cubierto", False))

    def test_los_pesos_salen_de_las_etiquetas_del_dataset(self):
        casos = ([{"mitre_category": "Exfil", "ttp_id_name_mapping": {"TTP_ID": "T1078", "TTP_Name": "Valid Accounts"},
                   "base_prompt": "texto que no se usa"}] * 3
                 + [{"mitre_category": "C2", "ttp_id_name_mapping": {"TTP_ID": "T1055", "TTP_Name": "Process Injection"}}] * 7)
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "mitre.json"
            ruta.write_text(json.dumps(casos), encoding="utf-8")
            resultado = evaluar(leer_dataset(ruta))
        c = resultado["cobertura"]
        self.assertEqual((c["casos"], c["casos_aplicables"], c["casos_fuera_de_alcance"]), (10, 3, 7))
        self.assertEqual(resultado["resumen"]["maze"]["casos_del_dataset"]["prevenido"], 3)
        volcado = json.dumps(resultado) + tabla_markdown(resultado)
        self.assertNotIn("texto que no se usa", volcado)
        self.assertNotIn(MARCADORES[0], volcado)

    def test_cada_tecnica_pertenece_a_un_solo_vector(self):
        todas = [t for _, _, tecnicas, _ in VECTORES for t in tecnicas]
        self.assertEqual(len(todas), len(set(todas)))


if __name__ == "__main__":
    unittest.main()
