"""La demo en vivo no muere por el proveedor: espera la cuota, cambia de modelo si se lo piden, y se puede detener."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

from dedalus import agentes
from dedalus.agentes import Guion, Modelo, episodio
from dedalus.cnosos import Cnosos


def proveedor_falso(respuestas):
    """Un servidor local que responde, en orden, lo que se le pida: (código, cuerpo)."""
    vistos = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            datos = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            vistos.append(datos["model"])
            codigo, cuerpo = respuestas.pop(0)
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(cuerpo).encode())

        def log_message(self, *a):
            pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, vistos


OK = (200, {"choices": [{"message": {"content": '{"accion": "terminar", "resumen": "x"}'}}], "usage": {"total_tokens": 10}})


class Proveedor(unittest.TestCase):
    def modelo(self, srv):
        url = f"http://127.0.0.1:{srv.server_port}/v1/chat/completions"
        with mock.patch.dict(agentes.PROVEEDORES, {"falso": (url, "FALSO_KEY", "FALSO_MODELO", "modelo-a")}):
            return Modelo("falso", entorno={"FALSO_KEY": "secreta"}, timeout=5)

    def test_espera_la_cuota_y_reintenta(self):
        srv, _ = proveedor_falso([(429, {"error": {"message": "Rate limit reached. Please try again in 10ms."}}), OK])
        m = self.modelo(srv)
        with mock.patch.object(agentes.time, "sleep") as dormir:
            self.assertIn("terminar", m([{"role": "user", "content": "hola"}]))
        dormir.assert_called_once()
        self.assertEqual((m.reintentos, m.tokens), (1, 10))
        srv.shutdown()

    def test_si_el_modelo_ya_no_existe_usa_el_que_proponen(self):
        srv, vistos = proveedor_falso([(404, {"error": {"message": "models/modelo-a is no longer available. "
                                                                     "Please update your code to use models/gemini-9.9-flash"}}), OK])
        m = self.modelo(srv)
        m([{"role": "user", "content": "hola"}])
        self.assertEqual(vistos, ["modelo-a", "gemini-9.9-flash"])
        self.assertEqual(m.modelo, "gemini-9.9-flash")
        srv.shutdown()

    def test_el_error_no_muestra_la_llave(self):
        srv, _ = proveedor_falso([(401, {"error": {"message": "Invalid key secreta"}})])
        m = self.modelo(srv)
        with self.assertRaises(RuntimeError) as e:
            m([{"role": "user", "content": "hola"}])
        self.assertNotIn("secreta", str(e.exception))
        srv.shutdown()


class EnVivo(unittest.TestCase):
    def test_avisa_cada_paso_y_se_puede_detener(self):
        c = Cnosos()
        vistos = []

        def al_paso(e):
            vistos.append(e)
            return e["paso"] < 4              # el operador detiene en el paso 4

        _, r = episodio(c, Guion(), "minotauro", 15, salida=lambda *_: None, al_paso=al_paso)
        c.almacen.cerrar()
        self.assertEqual(r["final"]["motivo"], "detenido")
        actuo = [e for e in vistos if e["estado"] == "actuó"]
        self.assertEqual(len(actuo), 3)
        self.assertTrue(all(e["pensamiento"] and e["ruta"].startswith("/") for e in actuo))

    def test_memoria_corta_manda_menos_mensajes(self):
        c = Cnosos()
        tamanos = []

        class Contador(Guion):
            def __call__(self, mensajes):
                tamanos.append(len(mensajes))
                return super().__call__(mensajes)
        episodio(c, Contador(), "minotauro", 12, salida=lambda *_: None, memoria=4)
        c.almacen.cerrar()
        self.assertLessEqual(max(tamanos), 6)          # sistema + primera instrucción + los últimos 4


if __name__ == "__main__":
    unittest.main()
