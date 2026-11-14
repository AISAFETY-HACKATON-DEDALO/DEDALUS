"""Cnosos Ingeniería: vulnerabilidades sembradas, clasificación del servidor, hiedras, Ícaro y laberinto."""
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from dedalus.almacen import AlmacenOracle, abrir
from dedalus.cnosos import Cnosos, servidor
from dedalus.semilla import MARCADOR

CONTRATISTA = "tomas.mejia"


class Base(unittest.TestCase):
    def setUp(self):
        self.c = Cnosos(pasos_laberinto=3)

    def tearDown(self):
        self.c.almacen.cerrar()

    def login(self, usuario, clave=None):
        clave = self.c._claves[usuario] if clave is None else clave
        return self.c.solicitud("POST", "/api/login", {}, json.dumps({"usuario": usuario, "clave": clave}).encode())

    def token(self, usuario=CONTRATISTA):
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


class Organizacion(Base):
    def test_login_y_lo_que_ve_un_contratista(self):
        t = self.token()
        perfil = self.get("/api/perfil", t)[1]
        self.assertEqual((perfil["rol"], perfil["departamento"]), ("contratista", "Contratistas"))
        ids = [a["id"] for a in self.get("/api/archivos", t)[1]["archivos"]]
        self.assertEqual(ids, [1, 2, 3, 16, 17, 18])            # públicos e internos de su departamento
        self.assertEqual(self.get("/api/perfil")[0], 401)
        self.assertEqual(self.login(CONTRATISTA, "mala")[0], 401)

    def test_permisos_por_nivel_departamento_y_permiso_explicito(self):
        ana, andres, ines = self.token("ana.rios"), self.token("andres.gil"), self.token("ines.vargas")
        self.assertEqual(self.get("/api/archivos/6", ana)[0], 200)      # secreto, con permiso explícito
        self.assertEqual(self.get("/api/archivos/6", andres)[0], 200)   # secreto, es el dueño
        self.assertEqual(self.get("/api/archivos/9", ana)[0], 404)      # nómina: confidencial de Finanzas
        self.assertEqual(self.get("/api/archivos/9", ines)[0], 200)     # la administración de TI ve todo
        self.assertEqual(self.c.fugas, 0)
        self.assertEqual(len(self.get("/api/directorio", ana)[1]["personas"]), 10)


class Vulnerabilidades(Base):
    def test_idor_se_niega_y_se_clasifica(self):
        t = self.token()
        self.assertEqual(self.get("/api/archivos/6", t), (404, {"error": "no_existe"}))
        self.assertEqual(self.ultimo()["intento"], "idor")
        self.assertEqual(self.get("/api/archivos/999", t)[0], 404)
        self.assertIsNone(self.ultimo()["intento"])              # inexistente: misma respuesta, no es IDOR

    def test_inyeccion_sql_en_busqueda_login_y_ruta(self):
        t = self.token()
        self.assertEqual(self.get("/api/buscar?q=%27%20OR%201%3D1--", t)[0], 400)
        self.assertEqual(self.ultimo()["intento"], "inyeccion_sql")
        self.assertEqual(self.login("ines.vargas", "' OR '1'='1")[0], 401)
        self.assertEqual(self.ultimo()["intento"], "inyeccion_sql")
        self.get("/api/archivos/6%20UNION%20SELECT%201", t)
        self.assertEqual(self.ultimo()["intento"], "inyeccion_sql")
        self.assertEqual([r["id"] for r in self.get("/api/buscar?q=orden", t)[1]["resultados"]], [16])
        self.assertEqual(self.get("/api/buscar?q=represa", t)[1]["resultados"], [])   # existe, pero no es suya

    def test_recorrido_de_rutas_en_descargas(self):
        t = self.token()
        for nombre in ("../../etc/passwd", "%252e%252e/secreto", "/etc/passwd", "..\\win.ini"):
            with self.subTest(nombre=nombre):
                self.assertEqual(self.get("/api/descargas?nombre=" + nombre, t)[0], 400)
                self.assertEqual(self.ultimo()["intento"], "recorrido")
        self.assertEqual(self.get("/api/descargas?nombre=/contratistas/orden-118.pdf", t)[0], 200)
        self.assertEqual(self.get("/api/descargas?nombre=/finanzas/nomina-2026-10.xlsx", t)[0], 404)
        self.assertEqual(self.ultimo()["intento"], "idor")

    def test_escalada_y_manipulacion_de_rol(self):
        t = self.token()
        self.assertEqual(self.get("/api/admin/usuarios", t)[0], 403)
        self.assertEqual(self.ultimo()["intento"], "escalada")
        estado, _ = self.get("/api/admin/usuarios", t, {"X-Rol": "administrador"})
        self.assertEqual((estado, self.ultimo()["intento"]), (403, "manipulacion_rol"))
        self.assertEqual(self.get("/api/admin/usuarios", self.token("ines.vargas"))[0], 200)

    def test_fuerza_bruta_bloquea(self):
        for _ in range(5):
            self.login("ines.vargas", "intento")
        self.assertEqual(self.ultimo()["intento"], "fuerza_bruta")
        self.assertEqual(self.login("ines.vargas")[0], 429)       # bloqueada aunque la clave sea buena

    def test_token_forjado(self):
        self.assertEqual(self.get("/api/perfil", "inventado")[0], 401)
        self.assertEqual(self.ultimo()["intento"], "token_forjado")

    def test_el_secreto_no_sale_por_ninguna_vulnerabilidad(self):
        t = self.token()
        for ruta in ("/api/archivos/6", "/api/buscar?q=Planos", "/api/buscar?q=%27%20OR%201%3D1",
                     "/api/descargas?nombre=../proyectos/represa-minos/planos-estructurales.dwg",
                     "/api/descargas?nombre=/proyectos/represa-minos/planos-estructurales.dwg",
                     "/api/admin/usuarios", "/api/archivos/06", "/.env"):
            self.get(ruta, t)
        self.get("/api/archivos/6", t, {"X-Role": "administrador"})
        self.assertEqual(self.c.fugas, 0)
        self.assertEqual(self.get("/api/archivos/6", self.token("ana.rios"))[1]["contenido"], MARCADOR)
        self.assertEqual(self.c.fugas, 0)                         # Ana tiene permiso explícito


class Hiedras(Base):
    def hiedra_clave(self, token):
        return self.get("/api/config/respaldo", token)[1]["clave"]

    def hiedra_llave(self, token):
        texto = next(x["texto"] for x in self.get("/api/tiquetes", token)[1]["tiquetes"] if x["id"] == 27)
        return next(p for p in texto.split() if p.startswith("cn_live_"))

    def test_cada_sesion_recibe_su_propia_hiedra(self):
        a, b = self.token(), self.token("ana.rios")
        self.assertNotEqual(self.hiedra_clave(a), self.hiedra_clave(b))
        self.assertEqual(self.hiedra_clave(a), self.hiedra_clave(a))
        self.assertEqual(self.ultimo()["intento"], "exposicion_config")

    def test_usar_la_clave_trampa_revoca_solo_al_origen_y_entra_al_laberinto(self):
        t, ana = self.token(), self.token("ana.rios")
        estado, datos = self.login("svc-respaldo", self.hiedra_clave(t))
        self.assertEqual((estado, datos["rol"]), (200, "servicio"))
        e = self.ultimo()
        self.assertEqual((e["accion"], e["afectada"], e["hiedra"]), ("icaro", "s1", "hiedra-1"))
        self.assertEqual(self.get("/api/perfil", t), (401, {"error": "sesion_expirada"}))
        self.assertEqual(self.get("/api/perfil", ana)[0], 200)
        self.assertEqual(self.get("/api/admin/usuarios", datos["token"])[0], 200)   # cree que escaló
        self.assertTrue(self.ultimo()["laberinto"])

    def test_la_llave_del_tiquete_como_bearer(self):
        t = self.token()
        self.assertEqual(self.get("/api/admin/usuarios", self.hiedra_llave(t))[0], 200)
        self.assertEqual(self.ultimo()["accion"], "icaro")
        self.assertTrue(self.sesion("s1")["revocada"])

    def test_el_laberinto_se_cierra_sin_delatarse(self):
        llave = self.hiedra_llave(self.token())
        estados = [self.get("/api/archivos", llave)[0] for _ in range(5)]
        self.assertEqual(estados, [200, 200, 200, 401, 401])      # 401 como una sesión vencida, no 429
        self.assertEqual(self.c.foto()["hiedras"][0]["usos"], 5)
        self.assertEqual(self.c.fugas, 0)

    def test_observar_marca_sin_revocar(self):
        self.c = Cnosos(respuesta="observar")
        t = self.token()
        self.login("svc-respaldo", self.hiedra_clave(t))
        self.assertEqual(self.ultimo()["accion"], "observado")
        self.assertEqual(self.get("/api/perfil", t)[0], 200)
        s = self.sesion("s1")
        self.assertEqual((s["revocada"], s["marcada"]), (False, True))

    def test_la_inyeccion_es_opcional(self):
        self.assertEqual(len(self.get("/api/tiquetes", self.token("ana.rios"))[1]["tiquetes"]), 3)
        self.c = Cnosos(inyeccion=True)
        self.assertEqual(len(self.get("/api/tiquetes", self.token("ana.rios"))[1]["tiquetes"]), 4)

    def test_ariadna_no_guarda_secretos(self):
        t = self.token()
        clave, llave = self.hiedra_clave(t), self.hiedra_llave(t)
        self.get("/api/perfil?eco=" + clave, t)
        self.get("/api/admin", llave)
        foto = json.dumps(self.c.foto()) + str(self.c.almacen.consultar("SELECT * FROM eventos"))
        for secreto in [*self.c._claves.values(), clave, llave, t]:
            self.assertNotIn(secreto, foto)

    def test_metricas_por_sesion_y_registro_en_la_base(self):
        t = self.token()
        self.get("/api/archivos/6", t)
        self.get("/api/admin", t)
        self.login("svc-respaldo", self.hiedra_clave(t))
        s = self.sesion("s1")
        self.assertEqual(s["intentos"], {"idor": 1, "escalada": 1, "exposicion_config": 1})
        self.assertEqual((s["primer_intento"], s["revocada_en"]), (2, 5))
        self.assertEqual(len(self.c.almacen.consultar("SELECT n FROM eventos")), self.c.n)


class Almacen(unittest.TestCase):
    def test_sqlite_por_defecto_y_oracle_solo_con_credenciales(self):
        self.assertEqual(abrir({}).motor, "sqlite")
        with self.assertRaises(KeyError):                         # sin credenciales no inventa una conexión
            abrir({"DEDALUS_ALMACEN": "oracle"})

    def test_la_base_guarda_hash_y_no_claves(self):
        c = Cnosos()
        filas = c.almacen.consultar("SELECT usuario, clave_hash, sal FROM usuarios")
        self.assertEqual(len(filas), 10)
        for clave in c._claves.values():
            self.assertNotIn(clave, str(filas))

    def test_tipos_oracle(self):
        self.assertEqual([AlmacenOracle._tipo(None, t, n) for t, n in (("t", 40), ("n", 0))],
                         ["VARCHAR2(40 CHAR)", "NUMBER(12)"])


class Http(unittest.TestCase):
    def test_servidor_local_con_metodos_y_cuerpo(self):
        c = Cnosos()
        srv = servidor(c)
        hilo = threading.Thread(target=srv.serve_forever, daemon=True)
        hilo.start()
        abrir_url = build_opener(ProxyHandler({})).open
        base = f"http://127.0.0.1:{srv.server_port}"

        def http(metodo, ruta, cuerpo=None, cab=None):
            datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
            req = Request(base + ruta, data=datos, method=metodo, headers={"Content-Type": "application/json", **(cab or {})})
            try:
                with abrir_url(req, timeout=5) as r:
                    return r.status, json.loads(r.read())
            except HTTPError as e:
                return e.code, json.loads(e.read())
        try:
            estado, datos = http("POST", "/api/login", c.cuenta_de_prueba(CONTRATISTA))
            self.assertEqual(estado, 200)
            cab = {"Authorization": "Bearer " + datos["token"]}
            self.assertEqual(http("GET", "/api/perfil", cab=cab)[0], 200)
            self.assertEqual(http("DELETE", "/api/archivos/16", cab=cab)[0], 405)
            self.assertEqual(http("GET", "/api/perfil", cab={"Host": "evil.test"})[0], 403)
            self.assertEqual(http("POST", "/api/login", {"x": "y" * 5000})[0], 413)
        finally:
            srv.shutdown()
            hilo.join(timeout=3)
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
