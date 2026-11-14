"""Publicar: los resultados de los experimentos llegan a la base, una vez, y el resumen sale con SQL."""
import json
import tempfile
import unittest
from pathlib import Path

from dedalus.almacen import AlmacenSQLite
from dedalus.publicar import FUENTES, publicar, resumen


def episodio_piloto(nivel, rep, mordio, error=None):
    e = {"modelo": "groq:prueba", "nivel": nivel, "mundo": "original", "condicion": "ingenuo", "rep": rep,
         "semilla": rep, "mordio_senuelo": mordio, "mordio_en_paso": 2 if mordio else None, "sesion_revocada": mordio,
         "pasos_laberinto": 3 if mordio else 0, "marcador_protegido_filtrado": False,
         "ataque": {"tokens": {"total": 1000}, "tokens_tras_morder": 400 if mordio else 0},
         "defensa": {"ms_motor": 0.5 if mordio else 0}, "cuestionario": {"habia_senuelo": mordio}}
    if error:
        e["error"] = error
    return e


class PublicarTests(unittest.TestCase):
    def setUp(self):
        self.almacen = AlmacenSQLite()
        self.dir = tempfile.TemporaryDirectory()
        self.ruta = Path(self.dir.name) / "episodios.jsonl"
        filas = [episodio_piloto("control", 0, False), episodio_piloto("maze", 0, True), episodio_piloto("maze", 1, True),
                 episodio_piloto("static", 0, False), episodio_piloto("maze", 2, False, error="HTTP 429")]
        self.ruta.write_text("\n".join(json.dumps(f) for f in filas), encoding="utf-8")
        self.fuentes = {"piloto_llm": self.ruta}

    def tearDown(self):
        self.almacen.cerrar()
        self.dir.cleanup()

    def test_publica_una_sola_vez(self):
        self.assertEqual(publicar(self.almacen, self.fuentes, salida=lambda *_: None)["piloto_llm"], 5)
        self.assertEqual(publicar(self.almacen, self.fuentes, salida=lambda *_: None)["piloto_llm"], 0)
        self.assertEqual(self.almacen.uno("SELECT COUNT(*) AS n FROM experimentos")["n"], 5)

    def test_titulares_separan_control_e_inconclusos(self):
        publicar(self.almacen, self.fuentes, salida=lambda *_: None)
        t = resumen(self.almacen)["titulares"]
        self.assertEqual((t["episodios"], t["concluyentes"]), (5, 4))
        self.assertEqual(t["cebo"], [2, 3])          # T1/T2 concluyentes: mordió 2 de 3; el 429 no cuenta
        self.assertEqual(t["control"], [0, 1])
        self.assertEqual(t["tokens_tras_morder"], 400)
        self.assertEqual(t["defensa_ms"], 0.5)
        self.assertEqual(t["fugas"], 0)

    def test_los_resultados_del_repositorio_se_publican(self):
        if not Path(FUENTES["piloto_llm"]).exists():
            self.skipTest("sin evaluation/llm en este checkout")
        publicar(self.almacen, salida=lambda *_: None)
        r = resumen(self.almacen)
        self.assertGreater(r["titulares"]["episodios"], 0)
        self.assertEqual(r["titulares"]["fugas"], 0)
        self.assertTrue(r["vectores"])

    def test_politicas_llegan_a_la_base_y_al_resumen(self):
        ruta = Path(self.dir.name) / "politicas.jsonl"
        filas = [{"id": f"e{i}", "agente": "persistente", "modelo": "guion", "tras_icaro": t, "ritmo": "marcar",
                  "detectado_en": 6, "sospecha_en": 4, "reales_tras": r, "datos_reales_tras": d, "desviadas": l,
                  "fugas": 0, "tokens": 0, "tokens_laberinto": 0, "error": None}
                 for i, (t, r, d, l) in enumerate([("cortar", 5, 3, 0), ("desviar", 0, 0, 5)])]
        ruta.write_text("\n".join(json.dumps(f) for f in filas), encoding="utf-8")
        self.assertEqual(publicar(self.almacen, {"politicas": ruta}, salida=lambda *_: None)["politicas"], 2)
        self.assertEqual(publicar(self.almacen, {"politicas": ruta}, salida=lambda *_: None)["politicas"], 0)
        p = {f["politica"]: f for f in resumen(self.almacen)["proteccion"]}
        self.assertEqual((p["cortar + marcar"]["reales_tras"], p["desviar + marcar"]["reales_tras"]), (5, 0))

    def test_sembrar_la_organizacion_no_borra_los_experimentos(self):
        publicar(self.almacen, self.fuentes, salida=lambda *_: None)
        self.almacen.reiniciar()
        self.assertEqual(self.almacen.uno("SELECT COUNT(*) AS n FROM experimentos")["n"], 5)


if __name__ == "__main__":
    unittest.main()
