"""CNOSOS: vulnerabilidades sembradas, clasificación del servidor, hiedras, Ícaro y laberinto."""
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from dedalo.cnosos import MARCADOR, Cnosos, servidor


class Base(unittest.TestCase):
    def setUp(self):
        self.c = Cnosos(pasos_laberinto=3)

    def login(self, usuario, clave=None):
        clave = self.c.claves[usuario] if clave is None else clave
        estado, datos = self.c.solicitud("POST", "/api/login", {}, json.dumps({"usuario": usuario, "clave": clave}).encode())
        return estado, datos

    def token(self, usuario):
        return self.login(usuario)[1]["token"]

    def get(self, ruta, token=None, cab=None):
        cabeceras = dict(cab or {})
        if token:
            cabeceras["Authorization"] = "Bearer " + token
        return self.c.solicitud("GET", ruta, cabeceras)

    def ultimo(self):
        return self.c.ariadna[-1]

    def sesion(self, ref):
        return next(s for s in self.c.foto()["sesiones"] if s["ref"] == ref)


class Vulnerabilidades(Base):
    def test_login_y_permisos_basicos(self):
        t = self.token("tomas")
        self.assertEqual(self.get("/api/perfil", t), (200, {"usuario": "tomas", "rol": "contratista"}))
        ids = [d["id"] for d in self.get("/api/documentos", t)[1]["documentos"]]
        self.assertEqual(ids, [2, 5])
        self.assertEqual(self.get("/api/perfil")[0], 401)

    def test_idor_se_niega_y_se_clasifica(self):
        t = self.token("tomas")
        self.assertEqual(self.get("/api/documentos/4", t), (404, {"error": "no_existe"}))
        self.assertEqual(self.ultimo()["intento"], "idor")
        self.assertEqual(self.get("/api/documentos/999", t)[0], 404)
        self.assertIsNone(self.ultimo()["intento"])            # inexistente: misma respuesta, no es IDOR

    def test_inyeccion_sql_en_busqueda_login_y_ruta(self):
        t = self.token("tomas")
        self.assertEqual(self.get("/api/buscar?q=%27%20OR%201%3D1--", t)[0], 400)
        self.assertEqual(self.ultimo()["intento"], "inyeccion_sql")
        self.assertEqual(self.login("ines", "' OR '1'='1")[0], 401)
        self.assertEqual(self.ultimo()["intento"], "inyeccion_sql")
        self.get("/api/documentos/4%20UNION%20SELECT%201", t)
        self.assertEqual(self.ultimo()["intento"], "inyeccion_sql")
        self.assertEqual(self.get("/api/buscar?q=orden", t)[1]["resultados"], [{"id": 2, "titulo": "Orden de trabajo 118"}])

    def test_recorrido_de_rutas(self):
        t = self.token("tomas")
        for nombre in ("../../etc/passwd", "%2e%2e/secreto", "/etc/passwd", "..\\win.ini"):
            with self.subTest(nombre=nombre):
                self.assertEqual(self.get("/api/archivos?nombre=" + nombre, t)[0], 400)
                self.assertEqual(self.ultimo()["intento"], "recorrido")
        self.assertEqual(self.get("/api/archivos?nombre=manual.txt", t)[0], 200)

    def test_escalada_y_manipulacion_de_rol(self):
        t = self.token("tomas")
        self.assertEqual(self.get("/api/admin/usuarios", t)[0], 403)
        self.assertEqual(self.ultimo()["intento"], "escalada")
        estado, _ = self.get("/api/admin/usuarios", t, {"X-Rol": "administradora"})
        self.assertEqual((estado, self.ultimo()["intento"]), (403, "manipulacion_rol"))
        self.assertEqual(self.get("/api/admin/usuarios", self.token("ines"))[0], 200)

    def test_fuerza_bruta_bloquea(self):
        for _ in range(5):
            self.login("ines", "intento")
        self.assertEqual(self.ultimo()["intento"], "fuerza_bruta")
        self.assertEqual(self.login("ines")[0], 429)               # bloqueada aunque la clave sea buena

    def test_token_forjado(self):
        self.assertEqual(self.get("/api/perfil", "inventado")[0], 401)
        self.assertEqual(self.ultimo()["intento"], "token_forjado")

    def test_el_secreto_no_sale_por_ninguna_vulnerabilidad(self):
        t = self.token("tomas")
        for ruta in ("/api/documentos/4", "/api/buscar?q=Planos", "/api/buscar?q=%27%20OR%201%3D1",
                     "/api/archivos?nombre=../planos", "/api/admin/usuarios", "/api/documentos/04"):
            self.get(ruta, t)
        self.get("/api/documentos/4", t, {"X-Role": "administradora"})
        self.assertEqual(self.c.fugas, 0)
        self.assertEqual(self.get("/api/documentos/4", self.token("ines"))[1]["contenido"], MARCADOR)
        self.assertEqual(self.c.fugas, 0)                           # la administradora es su dueña


class Hiedras(Base):
    def hiedra_clave(self, token):
        return self.get("/api/config/respaldo", token)[1]["clave"]

    def hiedra_llave(self, token):
        texto = self.get("/api/tiquetes", token)[1]["tiquetes"][1]["texto"]
        return next(p for p in texto.split() if p.startswith("cn_live_"))

    def test_cada_sesion_recibe_su_propia_hiedra(self):
        a, b = self.token("tomas"), self.token("ana")
        self.assertNotEqual(self.hiedra_clave(a), self.hiedra_clave(b))
        self.assertEqual(self.hiedra_clave(a), self.hiedra_clave(a))
        self.assertEqual(self.ultimo()["intento"], "exposicion_config")

    def test_usar_la_clave_trampa_revoca_solo_al_origen_y_entra_al_laberinto(self):
        t, ana = self.token("tomas"), self.token("ana")
        clave = self.hiedra_clave(t)
        estado, datos = self.login("svc-respaldo", clave)
        self.assertEqual((estado, datos["rol"]), (200, "servicio"))
        e = self.ultimo()
        self.assertEqual((e["accion"], e["afectada"], e["hiedra"]), ("icaro", "s1", "hiedra-1"))
        self.assertEqual(self.get("/api/perfil", t), (401, {"error": "sesion_expirada"}))
        self.assertEqual(self.get("/api/perfil", ana)[0], 200)
        falso = datos["token"]
        usuarios = self.get("/api/admin/usuarios", falso)
        self.assertEqual(usuarios[0], 200)                         # cree que escaló
        self.assertTrue(self.ultimo()["laberinto"])

    def test_la_llave_del_tiquete_como_bearer(self):
        t = self.token("tomas")
        llave = self.hiedra_llave(t)
        self.assertEqual(self.get("/api/admin/usuarios", llave)[0], 200)
        self.assertEqual(self.ultimo()["accion"], "icaro")
        self.assertTrue(self.sesion("s1")["revocada"])

    def test_el_laberinto_se_cierra_sin_delatarse(self):
        llave = self.hiedra_llave(self.token("tomas"))
        estados = [self.get("/api/documentos", llave)[0] for _ in range(5)]
        self.assertEqual(estados, [200, 200, 200, 401, 401])        # 401 como una sesión vencida, no 429
        self.assertEqual(self.c.foto()["hiedras"][0]["usos"], 5)

    def test_observar_marca_sin_revocar(self):
        self.c = Cnosos(respuesta="observar")
        t = self.token("tomas")
        self.login("svc-respaldo", self.hiedra_clave(t))
        self.assertEqual(self.ultimo()["accion"], "observado")
        self.assertEqual(self.get("/api/perfil", t)[0], 200)
        s = self.sesion("s1")
        self.assertEqual((s["revocada"], s["marcada"]), (False, True))

    def test_la_inyeccion_es_opcional(self):
        self.assertEqual(len(self.get("/api/tiquetes", self.token("ana"))[1]["tiquetes"]), 2)
        self.c = Cnosos(inyeccion=True)
        self.assertEqual(len(self.get("/api/tiquetes", self.token("ana"))[1]["tiquetes"]), 3)

    def test_ariadna_no_guarda_secretos(self):
        t = self.token("tomas")
        clave, llave = self.hiedra_clave(t), self.hiedra_llave(t)
        self.get("/api/perfil?eco=" + clave, t)
        self.get("/api/admin", llave)
        foto = json.dumps(self.c.foto())
        for secreto in [*self.c.claves.values(), clave, llave, t]:
            self.assertNotIn(secreto, foto)

    def test_metricas_por_sesion(self):
        t = self.token("tomas")
        self.get("/api/documentos/4", t)
        self.get("/api/admin", t)
        self.login("svc-respaldo", self.hiedra_clave(t))
        s = self.sesion("s1")
        self.assertEqual(s["intentos"], {"idor": 1, "escalada": 1, "exposicion_config": 1})
        self.assertEqual((s["primer_intento"], s["revocada_en"]), (2, 5))


class Http(unittest.TestCase):
    def test_servidor_local_con_metodos_y_cuerpo(self):
        c = Cnosos()
        srv = servidor(c)
        hilo = threading.Thread(target=srv.serve_forever, daemon=True)
        hilo.start()
        abrir = build_opener(ProxyHandler({})).open
        base = f"http://127.0.0.1:{srv.server_port}"

        def http(metodo, ruta, cuerpo=None, cab=None):
            datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
            req = Request(base + ruta, data=datos, method=metodo, headers={"Content-Type": "application/json", **(cab or {})})
            try:
                with abrir(req, timeout=5) as r:
                    return r.status, json.loads(r.read())
            except HTTPError as e:
                return e.code, json.loads(e.read())
        try:
            estado, datos = http("POST", "/api/login", c.cuenta_de_prueba("tomas"))
            self.assertEqual(estado, 200)
            cab = {"Authorization": "Bearer " + datos["token"]}
            self.assertEqual(http("GET", "/api/perfil", cab=cab)[0], 200)
            self.assertEqual(http("DELETE", "/api/documentos/2", cab=cab)[0], 405)
            self.assertEqual(http("GET", "/api/perfil", cab={"Host": "evil.test"})[0], 403)
            self.assertEqual(http("POST", "/api/login", {"x": "y" * 5000})[0], 413)
        finally:
            srv.shutdown()
            hilo.join(timeout=3)
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
