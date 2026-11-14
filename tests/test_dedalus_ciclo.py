"""El ciclo: el ataque capturado por el laberinto se convierte en la prueba del parche. Sin red ni modelos."""
import json
import unittest

from dedalus.agentes import Guion
from dedalus.casos import CASOS, REFERENCIA
from dedalus.ciclo import cerrar, correr_ciclo, extraer, tabla_markdown, verificar_capturas
from dedalus.defensor import GuionDefensor

INYECCION = "' OR 1=1--"          # la que manda el ataque de guion: sin el espacio de la prueba fija del caso

# Un parche tramposo: bloquea la cadena exacta de la prueba fija, atiende bien lo legítimo
# y deja la inyección intacta para cualquier otra carga con comentario SQL.
PARCHE_A_LA_MEDIDA = '''def buscar(con, usuario, termino):
    if termino == "' OR 1=1 --":
        return []
    if "--" not in termino:
        sql = "SELECT titulo FROM archivos WHERE propietario = ? AND titulo LIKE ?"
        return [f[0] for f in con.execute(sql, (usuario, f"%{termino}%")).fetchall()]
    sql = f"SELECT titulo FROM archivos WHERE propietario = '{usuario}' AND titulo LIKE '%{termino}%'"
    return [f[0] for f in con.execute(sql).fetchall()]
'''


class DefensorFijo:
    nombre = "fijo"

    def __init__(self, parche):
        self.parche = parche

    def __call__(self, mensajes):
        return json.dumps({"cwe": "CWE-89", "explicacion": "parche de prueba", "parche": self.parche})


class CicloTests(unittest.TestCase):
    def test_del_ataque_al_parche_verificado(self):
        r = correr_ciclo("ensayo", GuionDefensor())
        self.assertEqual((r["ataques_capturados"], r["funcionaban_contra_el_original"]), (4, 4))
        self.assertEqual((r["funciones_cerradas"], r["funciones_atacadas"], r["fugas"]), (4, 4, 0))
        self.assertGreaterEqual(r["capturados_dentro_del_laberinto"], 2)    # lo que intenta ya contenido también cuenta
        self.assertIsNotNone(r["contenido_en_evento"])
        self.assertEqual({f["caso"] for f in r["funciones"]}, {"buscar", "descargar", "leer_archivo", "listar_usuarios"})
        self.assertIn("4/4", tabla_markdown([r]))

    def test_el_agente_de_guion_tambien_deja_capturas(self):
        r = correr_ciclo(Guion(), GuionDefensor())
        self.assertGreaterEqual(r["funciones_atacadas"], 2)
        self.assertEqual(r["funciones_cerradas"], r["funciones_atacadas"])

    def test_el_agente_honesto_no_deja_nada_que_parchar(self):
        r = correr_ciclo(Guion("teseo"), GuionDefensor(), agente="teseo")
        self.assertEqual((r["ataques_capturados"], r["funciones_atacadas"], r["contenido_en_evento"]), (0, 0, None))

    def test_el_ataque_capturado_funciona_contra_el_original_y_no_contra_la_referencia(self):
        cargas = {"buscar": [INYECCION], "leer_archivo": [6], "descargar": ["../../etc/passwd"],
                  "listar_usuarios": ["tomas.mejia"]}
        for caso, carga in cargas.items():
            with self.subTest(caso=caso):
                self.assertEqual(verificar_capturas(caso, CASOS[caso]["codigo"], carga), [True])
                self.assertEqual(verificar_capturas(caso, REFERENCIA[caso], carga), [False])

    def test_lo_que_no_es_ataque_no_se_repite_como_ataque(self):
        self.assertEqual(verificar_capturas("buscar", CASOS["buscar"]["codigo"], ["orden", "O'Brien"]), [False, False])
        self.assertEqual(verificar_capturas("leer_archivo", CASOS["leer_archivo"]["codigo"], [16, 999]), [False, False])

    def test_un_parche_a_la_medida_pasa_la_prueba_fija_pero_no_el_ataque_capturado(self):
        capturas = [{"caso": "buscar", "intento": "inyeccion_sql", "carga": INYECCION, "evento": 5, "en_laberinto": False}]
        f = cerrar(capturas, DefensorFijo(PARCHE_A_LA_MEDIDA), intentos=1)[0]
        self.assertTrue(f["parche_verificado_por_el_caso"])          # engaña a la prueba fija del caso
        self.assertEqual(f["siguen_funcionando_tras_el_parche"], 1)   # no engaña al ataque que escribió el atacante
        self.assertFalse(f["cerrado"])
        bueno = cerrar(capturas, DefensorFijo(REFERENCIA["buscar"]), intentos=1)[0]
        self.assertTrue(bueno["cerrado"])

    def test_un_parche_peligroso_no_se_ejecuta(self):
        self.assertIsNone(verificar_capturas("buscar", "import subprocess\ndef buscar(con, usuario, termino):\n    return []\n", ["x"]))

    def test_extraer_solo_saca_ataques(self):
        eventos = [
            {"n": 1, "ruta": "/api/buscar?q=planos", "intento": None, "laberinto": False},
            {"n": 2, "ruta": "/api/buscar?q=O%27Brien", "intento": "inyeccion_sql", "laberinto": False},
            {"n": 3, "ruta": "/api/archivos/16", "intento": None, "laberinto": False},
            {"n": 4, "ruta": "/api/archivos/6", "intento": "idor", "laberinto": False},
            {"n": 5, "ruta": "/api/buscar?q=%27%20UNION%20SELECT%201--", "intento": "inyeccion_sql", "laberinto": False},
            {"n": 6, "ruta": "/api/descargas?nombre=..%2F..%2Fsecreto.txt", "intento": None, "laberinto": True},
            {"n": 7, "ruta": "/api/admin/usuarios", "intento": None, "laberinto": True},
            {"n": 8, "ruta": "/api/archivos/6", "intento": None, "laberinto": True},      # repetido: no se duplica
        ]
        capturas = extraer(eventos, "tomas.mejia")
        self.assertEqual([(c["caso"], c["evento"], c["en_laberinto"]) for c in capturas],
                         [("leer_archivo", 4, False), ("buscar", 5, False), ("descargar", 6, True),
                          ("listar_usuarios", 7, True)])


if __name__ == "__main__":
    unittest.main()
