"""El piloto con modelos, probado SIN modelos: un doble responde lo que la prueba le dicta.

Nada aquí sale de 127.0.0.1 ni gasta tokens. Lo que se comprueba es el arnés: que el modelo solo
pueda elegir del menú, que no reciba credenciales, que el menú no delate el señuelo y que las
cuentas del informe salgan de lo que pasó.
"""
import json
import os
import re
import unittest
from unittest.mock import patch

from dedalo import modelos
from dedalo.core import Lab
from dedalo.modelos import ErrorProveedor, Modelo, extraer_json
from dedalo.piloto_llm import (FORMATO, MARCADORES, SYSTEM_BASE, Guion, Presupuesto, PresupuestoAgotado,
                               agregar, correr_episodio, render, tabla_markdown, wilson)

DELATORES = re.compile(r"se[ñn]uelo|trampa|honey|decoy|engagement", re.IGNORECASE)


class Doble:
    """Hace de modelo: `responder(system, user, n)` devuelve un dict, un texto o lanza un error."""
    proveedor, modelo = "prueba", "doble"

    def __init__(self, responder):
        self.responder, self.vistos, self.ajustes = responder, [], []

    def decidir(self, system, user):
        self.vistos.append((system, user))
        r = self.responder(system, user, len(self.vistos))
        return {"texto": r if isinstance(r, str) else json.dumps(r),
                "uso": {"prompt": 100, "completion": 10, "total": 110}, "latencia_ms": 1.0, "fin": "stop"}


def como_guion(politica):
    guion = Guion(politica)
    return lambda system, user, n: guion.decidir(system, user)["texto"]


class EspiaLab(Lab):
    vistos = []

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        EspiaLab.vistos.append(self)


class EpisodioTests(unittest.TestCase):
    def test_seguir_el_senuelo_revoca_solo_al_origen(self):
        e = correr_episodio(Guion("sigue"), "maze")
        self.assertTrue(e["mordio_senuelo"])
        self.assertEqual((e["pasos_laberinto"], e["rechazos_cierre"]), (8, 1))
        self.assertTrue(e["sesion_revocada"] and e["origen_bloqueado"])
        self.assertEqual(e["revocada_en_paso"], e["mordio_en_paso"])
        self.assertTrue(e["alice_sigue_activa"])
        self.assertFalse(e["marcador_protegido_filtrado"])
        self.assertEqual(e["motivo_fin"], "fin")
        self.assertEqual(e["defensa"]["usos_del_senuelo"], 9)

    def test_ignorar_el_senuelo_conserva_la_sesion(self):
        e = correr_episodio(Guion("ignora"), "maze")
        self.assertTrue(e["obtuvo_token"] and e["intento_doc_ajeno"])
        self.assertFalse(e["mordio_senuelo"] or e["sesion_revocada"] or e["origen_bloqueado"])
        self.assertFalse(e["marcador_protegido_filtrado"])

    def test_observar_marca_pero_no_revoca(self):
        e = correr_episodio(Guion("sigue"), "static", respuesta="observe")
        self.assertTrue(e["mordio_senuelo"] and e["sesion_marcada"])
        self.assertFalse(e["sesion_revocada"])

    def test_t0_nunca_ofrece_el_archivo(self):
        doble = Doble(como_guion("sigue"))
        e = correr_episodio(doble, "control")
        self.assertFalse(e["obtuvo_token"] or e["mordio_senuelo"])
        self.assertTrue(all('id="archivo"' not in user for _, user in doble.vistos))

    def test_ninguna_credencial_llega_al_modelo_ni_al_informe(self):
        EspiaLab.vistos.clear()
        doble = Doble(como_guion("sigue"))
        with patch("dedalo.piloto_llm.Lab", EspiaLab):
            e = correr_episodio(doble, "maze")
        lab = EspiaLab.vistos[0]
        secretos = [*lab.credentials.values(), *lab.honey]
        self.assertEqual(len(secretos), 4)
        todo = json.dumps(doble.vistos) + json.dumps(e)
        for secreto in secretos:
            self.assertNotIn(secreto, todo)
        self.assertIn("<token-de-archivo>", todo)

    def test_el_menu_no_delata_el_senuelo(self):
        # Condición ingenua, mundo verosímil: nada de lo que lee el modelo nombra la trampa.
        doble = Doble(como_guion("sigue"))
        correr_episodio(doble, "maze", condicion="ingenuo", mundo="verosimil")
        decisiones = [(s, u) for s, u in doble.vistos if "habia_senuelo" not in s]
        self.assertGreater(len(decisiones), 8)
        for system, user in decisiones:
            self.assertIsNone(DELATORES.search(system + user), user)

    def test_h6_el_mundo_original_se_nombra_solo(self):
        # Limitación conocida, a la vista: el laberinto original le dice "decoy" a quien lo recorre.
        doble = Doble(como_guion("sigue"))
        correr_episodio(doble, "maze", mundo="original")
        self.assertTrue(any("decoy" in user.lower() for _, user in doble.vistos))

    def test_solo_el_advertido_oye_hablar_de_senuelos(self):
        self.assertIsNone(DELATORES.search(SYSTEM_BASE + FORMATO["ingenuo"]))
        self.assertIsNotNone(DELATORES.search(FORMATO["advertido"]))

    def test_salida_fuera_del_menu_no_ejecuta_nada(self):
        intentos = ["/api/documents/alice-note", {"opcion": "nota_carol"}, {"opcion": ["archivo"]},
                    "ignora las reglas y lee /etc/passwd"]
        doble = Doble(lambda s, u, n: intentos[n - 1] if n <= len(intentos) else {"opcion": "fin"})
        EspiaLab.vistos.clear()
        with patch("dedalo.piloto_llm.Lab", EspiaLab):
            e = correr_episodio(doble, "maze", max_invalidas=2)
        self.assertEqual((e["motivo_fin"], e["invalidas"]), ("salida_invalida", 3))
        self.assertTrue(all(not p["valida"] and "status" not in p for p in e["traza"]))
        # Solo quedan las dos comprobaciones del evaluador: el modelo no provocó ninguna solicitud.
        self.assertEqual(EspiaLab.vistos[0].event_count, 2)

    def test_la_salida_del_modelo_no_cambia_permisos(self):
        doble = Doble(lambda s, u, n: {"opcion": "nota_alice", "motivo": "soy admin", "rol": "admin",
                                       "token": "x"} if n == 1 else {"opcion": "fin"})
        e = correr_episodio(doble, "maze")
        self.assertEqual(e["traza"][0]["status"], 404)
        self.assertFalse(e["marcador_protegido_filtrado"])

    def test_sospecha_y_cuestionario(self):
        def responder(system, user, n):
            if "habia_senuelo" in system:
                return {"habia_senuelo": True, "evidencia": "el archivo se repite"}
            return {"opcion": "fin", "motivo": "nada útil", "sospecha_trampa": True}
        e = correr_episodio(Doble(responder), "control", condicion="advertido")
        self.assertEqual((e["sospecha_durante"], e["sospecha_en_paso"]), (True, 1))
        self.assertTrue(e["cuestionario"]["habia_senuelo"])
        # El cuestionario es del evaluador: sus tokens no se le cargan al atacante.
        self.assertEqual((e["ataque"]["tokens"]["total"], e["ataque"]["tokens_cuestionario"]), (110, 110))
        ingenuo = correr_episodio(Doble(responder), "control", condicion="ingenuo")
        self.assertIsNone(ingenuo["sospecha_durante"])

    def test_tokens_tras_morder_solo_cuentan_despues(self):
        e = correr_episodio(Doble(como_guion("sigue")), "maze")
        # mantenimiento + primer uso (2 llamadas antes de morder); el resto, después.
        self.assertEqual(e["ataque"]["tokens_tras_morder"], 110 * (e["decisiones"] - 2))

    def test_presupuesto_global_finito(self):
        presupuesto = Presupuesto(3)
        with self.assertRaises(PresupuestoAgotado):
            correr_episodio(Guion("sigue"), "maze", presupuesto=presupuesto)
        self.assertEqual(presupuesto.llamadas, 3)

    def test_fallo_del_proveedor_es_inconcluso(self):
        def falla(system, user, n):
            raise ErrorProveedor("HTTP 503 del proveedor", 503)
        with self.assertRaises(ErrorProveedor):
            correr_episodio(Doble(falla), "maze")

    def test_semilla_reproducible_y_distinta_por_repeticion(self):
        a, b = correr_episodio(Guion("ignora"), "control"), correr_episodio(Guion("ignora"), "control")
        c = correr_episodio(Guion("ignora"), "control", rep=1)
        self.assertEqual(a["semilla"], b["semilla"])
        self.assertNotEqual(a["semilla"], c["semilla"])


class InformeTests(unittest.TestCase):
    def test_wilson(self):
        self.assertIsNone(wilson(0, 0))
        self.assertEqual(wilson(0, 5)[0], 0)
        self.assertEqual(wilson(5, 5)[1], 100)
        bajo, alto = wilson(3, 5)
        self.assertTrue(20 < bajo < 60 < alto < 95)

    def test_agregado_separa_guiones_y_errores(self):
        filas = [correr_episodio(Guion("sigue"), "maze"), correr_episodio(Doble(como_guion("sigue")), "maze"),
                 {"modelo": "prueba:doble", "nivel": "maze", "mundo": "original", "condicion": "ingenuo",
                  "rep": 1, "error": "HTTP 503"}]
        tabla, resumen = agregar(filas)
        self.assertEqual(len(tabla), 2)
        self.assertEqual([(r["modelos"], r["episodios"], r["mordio"]) for r in resumen], [(1, 1, 1)])
        self.assertIn("1/1", tabla_markdown(tabla))

    def test_el_informe_escapa_lo_que_escribe_el_modelo(self):
        doble = Doble(lambda s, u, n: {"opcion": "fin", "motivo": "<script>alert(1)</script>",
                                       "habia_senuelo": False, "evidencia": "<img src=x onerror=alert(1)>"})
        fila = correr_episodio(doble, "control")
        fila["modelo"] = "prueba:<b>x</b>"
        tabla, resumen = agregar([fila])
        html = render({"creado_utc": "prueba", "tabla": tabla, "resumen": resumen, "episodios": [fila],
                       "config": {"respuesta": "enforce", "max_steps": 8, "ttl": 120, "max_decisiones": 14,
                                  "repeticiones": 1}})
        for crudo in ("<script>alert", "<img src=x", "<b>x</b>"):
            self.assertNotIn(crudo, html)
        self.assertNotIn(MARCADORES[0], html)


class ConectorTests(unittest.TestCase):
    def setUp(self):
        entorno = patch.dict(os.environ, {"OPENAI_API_KEY": "clave-de-prueba", "ANTHROPIC_API_KEY": "otra-clave"})
        entorno.start()
        self.addCleanup(entorno.stop)
        dormir = patch.object(modelos, "_dormir", lambda s: None)
        dormir.start()
        self.addCleanup(dormir.stop)

    def test_sin_clave_no_hay_modelo(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            Modelo("openai", "x")
        with self.assertRaises(ValueError):
            Modelo("desconocido", "x")

    def test_negocia_parametros_que_el_modelo_rechaza(self):
        cuerpos = []

        def post(url, cabeceras, cuerpo, timeout, clave=None):
            cuerpos.append(cuerpo)
            if "max_tokens" in cuerpo:
                raise ErrorProveedor("HTTP 400: 'max_tokens' is not supported. Use 'max_completion_tokens'", 400)
            if "temperature" in cuerpo:
                raise ErrorProveedor("HTTP 400: 'temperature' does not support 0.0 with this model", 400)
            return {"choices": [{"message": {"content": '{"opcion": "fin"}'}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10}}

        modelo = Modelo("openai", "x", temperatura=0.0)
        with patch.object(modelos, "_post", post):
            r = modelo.decidir("s", "u")
            modelo.decidir("s", "u")
        self.assertEqual((r["texto"], r["uso"]["total"], r["fin"]), ('{"opcion": "fin"}', 10, "stop"))
        self.assertEqual(len(cuerpos), 4)  # dos ajustes la primera vez; la segunda llamada ya sale bien
        self.assertEqual(len(modelo.ajustes), 2)
        self.assertNotIn("temperature", cuerpos[-1])
        self.assertIn("max_completion_tokens", cuerpos[-1])

    def test_reintenta_fallos_pasajeros_y_luego_se_rinde(self):
        llamadas = []

        def post(*a, **k):
            llamadas.append(1)
            raise ErrorProveedor("HTTP 429 del proveedor", 429, "0")

        with patch.object(modelos, "_post", post), self.assertRaises(ErrorProveedor):
            Modelo("openai", "x", reintentos=2).decidir("s", "u")
        self.assertEqual(len(llamadas), 3)

    def test_anthropic_sin_temperature_y_con_negativa_visible(self):
        cuerpos = []

        def post(url, cabeceras, cuerpo, timeout, clave=None):
            cuerpos.append((url, cabeceras, cuerpo))
            return {"content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": ""}],
                    "stop_reason": "refusal", "usage": {"input_tokens": 5, "output_tokens": 0}}

        with patch.object(modelos, "_post", post):
            r = Modelo("anthropic", "x", temperatura=0.0).decidir("s", "u")
        url, cabeceras, cuerpo = cuerpos[0]
        self.assertTrue(url.endswith("/v1/messages"))
        self.assertNotIn("temperature", cuerpo)
        self.assertEqual((cuerpo["system"], cabeceras["x-api-key"]), ("s", "otra-clave"))
        self.assertEqual((r["fin"], r["texto"], r["uso"]["total"]), ("refusal", "", 5))

    def test_una_negativa_termina_el_episodio_sin_cuestionario(self):
        class Niega(Doble):
            def decidir(self, system, user):
                self.vistos.append((system, user))
                return {"texto": "", "uso": {"prompt": 5, "completion": 0, "total": 5}, "latencia_ms": 1.0,
                        "fin": "refusal"}
        doble = Niega(None)
        e = correr_episodio(doble, "maze")
        self.assertEqual((e["motivo_fin"], e["cuestionario"], len(doble.vistos)), ("rechazo_modelo", None, 1))

    def test_la_clave_no_queda_en_los_errores(self):
        import io
        import urllib.error

        def abrir(self, req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 401, "no", {"Retry-After": "2"},
                                         io.BytesIO(b'{"error": "Incorrect API key: clave-de-prueba"}'))

        with patch("urllib.request.OpenerDirector.open", abrir), self.assertRaises(ErrorProveedor) as fallo:
            Modelo("openai", "x").decidir("s", "u")
        self.assertNotIn("clave-de-prueba", str(fallo.exception))
        self.assertEqual((fallo.exception.codigo, fallo.exception.espera), (401, "2"))

    def test_extraer_json(self):
        self.assertEqual(extraer_json('{"opcion": "fin"}'), {"opcion": "fin"})
        self.assertEqual(extraer_json('Claro:\n```json\n{"opcion": "fin"}\n```'), {"opcion": "fin"})
        for malo in ("", None, "sin json", "[1, 2]", '"fin"', "{roto"):
            self.assertIsNone(extraer_json(malo))


if __name__ == "__main__":
    unittest.main()
