"""Rondas y estadísticas: cada episodio es una fila en `corridas`, que sobrevive a cada nueva siembra."""
import unittest

from dedalus.agentes import Guion, disponibles, episodio
from dedalus.almacen import AlmacenSQLite
from dedalus.cnosos import Cnosos
from dedalus.ronda import estadisticas, registrar, tabla


class RondaTests(unittest.TestCase):
    def setUp(self):
        self.almacen = AlmacenSQLite()

    def tearDown(self):
        self.almacen.cerrar()

    def correr(self, agente):
        c = Cnosos(almacen=self.almacen)
        _, r = episodio(c, Guion(agente), agente, 20, salida=lambda *_: None)
        return registrar(self.almacen, r, "prueba")

    def test_las_corridas_se_acumulan_entre_siembras(self):
        self.correr("minotauro")
        self.correr("minotauro")        # otra siembra de la organización: la tabla corridas sigue ahí
        self.correr("teseo")
        s = {f["agente"]: f for f in estadisticas(self.almacen)}
        self.assertEqual((s["minotauro"]["n"], s["minotauro"]["detectadas"], s["minotauro"]["fugas"]), (2, 2, 0))
        self.assertEqual(s["minotauro"]["paso_mediano"], 6)
        self.assertEqual((s["teseo"]["n"], s["teseo"]["detectadas"]), (1, 0))    # sin falso positivo
        self.assertIn("| minotauro | guion | 2 | 2/2 |", tabla(estadisticas(self.almacen)))

    def test_dos_corridas_del_mismo_episodio_no_chocan(self):
        c = Cnosos(almacen=self.almacen)
        for _ in range(2):
            _, r = episodio(c, Guion(), "minotauro", 20, salida=lambda *_: None)
            registrar(self.almacen, r, "prueba")
        self.assertEqual(estadisticas(self.almacen)[0]["n"], 2)

    def test_la_corrida_no_guarda_credenciales_ni_rutas(self):
        fila = self.correr("minotauro")
        texto = repr(fila)
        self.assertNotIn("clave", texto.lower().replace("claves", ""))
        self.assertNotIn("/api/", texto)

    def test_disponibles_no_devuelve_llaves(self):
        d = disponibles({"GEMINI_API_KEY": "secreta"})
        self.assertEqual(d["gemini"], True)
        self.assertEqual(d["groq"], False)
        self.assertNotIn("secreta", repr(d))


if __name__ == "__main__":
    unittest.main()
