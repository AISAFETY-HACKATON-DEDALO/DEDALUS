"""El almacén de Cnosos: la organización falsa vive en Oracle Autonomous Database o, de respaldo, en SQLite.

Las dos tienen el mismo esquema y la misma interfaz. Todas las consultas usan parámetros con nombre
(:x), que entienden los dos motores: lo que escribe un agente nunca se ejecuta como SQL.

Selección por variables de entorno:
  DEDALUS_ALMACEN      sqlite (por defecto), oracle (wallet, puerto 1522) u oracle_rest (HTTPS, sin wallet)
  CNOSOS_ORDS_URL      para oracle_rest: https://<base>.adb.<región>.oraclecloudapps.com/ords/cnosos_app/_/sql
  DEDALUS_SQLITE       ruta del archivo SQLite (por defecto, en memoria)
  CNOSOS_DB_USUARIO, CNOSOS_DB_CLAVE, CNOSOS_DB_DSN, CNOSOS_WALLET_DIR, CNOSOS_WALLET_CLAVE   para Oracle
"""
from queue import Queue
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading

# (tabla, [(columna, tipo, largo)], clave primaria). Tipos: t = texto, n = número.
ESQUEMA = (
    ("departamentos", [("id", "n", 0), ("nombre", "t", 80)], "id"),
    ("usuarios", [("id", "n", 0), ("usuario", "t", 40), ("nombre", "t", 80), ("rol", "t", 30),
                  ("departamento_id", "n", 0), ("cargo", "t", 80), ("sal", "t", 64), ("clave_hash", "t", 128),
                  ("activo", "n", 0)], "id"),
    ("archivos", [("id", "n", 0), ("ruta", "t", 200), ("titulo", "t", 200), ("departamento_id", "n", 0),
                  ("propietario_id", "n", 0), ("nivel", "t", 20), ("contenido", "t", 2000)], "id"),
    ("permisos", [("archivo_id", "n", 0), ("usuario_id", "n", 0)], "archivo_id, usuario_id"),
    ("tiquetes", [("id", "n", 0), ("autor_id", "n", 0), ("asunto", "t", 200), ("texto", "t", 2000),
                  ("solo_inyeccion", "n", 0)], "id"),
    ("eventos", [("episodio", "t", 20), ("n", "n", 0), ("ms", "n", 0), ("sesion", "t", 20), ("usuario", "t", 40),
                 ("rol", "t", 30), ("metodo", "t", 10), ("ruta", "t", 200), ("estado", "n", 0), ("intento", "t", 40),
                 ("hiedra", "t", 20), ("accion", "t", 20), ("afectada", "t", 20), ("laberinto", "n", 0),
                 ("fuga", "n", 0)], "episodio, n"),
)
ORGANIZACION_TABLAS = tuple(t for t, _, _ in ESQUEMA if t != "eventos")
ITERACIONES = 60_000


def cifrar(clave, sal=None):
    sal = sal or secrets.token_hex(16)
    return sal, hashlib.pbkdf2_hmac("sha256", clave.encode(), sal.encode(), ITERACIONES).hex()


def coincide(clave, sal, esperado):
    return hmac.compare_digest(cifrar(clave, sal)[1], esperado)


class Almacen:
    motor = "?"

    def __init__(self):
        self.candado = threading.RLock()

    def _tipo(self, tipo, largo):
        raise NotImplementedError

    def ddl(self, tablas=None):
        sentencias = []
        for tabla, columnas, clave in ESQUEMA:
            if tablas is None or tabla in tablas:
                cols = ", ".join(f"{c} {self._tipo(t, l)}" for c, t, l in columnas)
                sentencias.append(f"CREATE TABLE {tabla} ({cols}, PRIMARY KEY ({clave}))")
        return sentencias

    def consultar(self, sql, **binds):
        with self.candado:
            cur = self.con.cursor()
            cur.execute(sql, binds)
            nombres = [d[0].lower() for d in cur.description]
            return [dict(zip(nombres, fila)) for fila in cur.fetchall()]

    def uno(self, sql, **binds):
        filas = self.consultar(sql, **binds)
        return filas[0] if filas else None

    def ejecutar(self, sql, **binds):
        with self.candado:
            self.con.cursor().execute(sql, binds)
            self.con.commit()

    def ejecutar_fondo(self, sql, **binds):
        """Escritura que no debe frenar al portal (el registro). Por defecto, inmediata."""
        self.ejecutar(sql, **binds)

    def muchos(self, sql, filas):
        with self.candado:
            if filas:
                self.con.cursor().executemany(sql, filas)
            self.con.commit()

    def cerrar(self):
        with self.candado:
            self.con.close()


class AlmacenSQLite(Almacen):
    motor = "sqlite"

    def __init__(self, ruta=":memory:"):
        super().__init__()
        self.con = sqlite3.connect(ruta, check_same_thread=False)

    def _tipo(self, tipo, largo):
        return "TEXT" if tipo == "t" else "INTEGER"

    def reiniciar(self):
        """Recrea la organización. La tabla eventos (Ariadna) se conserva: acumula todos los episodios."""
        with self.candado:
            for tabla in ORGANIZACION_TABLAS[::-1]:
                self.con.execute(f"DROP TABLE IF EXISTS {tabla}")
            existe = self.con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'eventos'").fetchone()
            for s in self.ddl(ORGANIZACION_TABLAS + (() if existe else ("eventos",))):
                self.con.execute(s)
            self.con.commit()


class AlmacenOracle(Almacen):
    motor = "oracle"

    def __init__(self, usuario, clave, dsn, wallet_dir=None, wallet_clave=None):
        super().__init__()
        import oracledb     # dependencia opcional: solo hace falta para usar Oracle
        extra = {}
        if wallet_dir:
            extra = {"config_dir": wallet_dir, "wallet_location": wallet_dir, "wallet_password": wallet_clave}
        self.con = oracledb.connect(user=usuario, password=clave, dsn=dsn, tcp_connect_timeout=10, **extra)
        self.con.call_timeout = 15_000

    def _tipo(self, tipo, largo):
        return f"VARCHAR2({largo} CHAR)" if tipo == "t" else "NUMBER(12)"

    def reiniciar(self):
        """Recrea la organización. La tabla eventos (Ariadna) se conserva: acumula todos los episodios."""
        with self.candado:
            cur = self.con.cursor()
            for tabla in ORGANIZACION_TABLAS[::-1]:
                try:
                    cur.execute(f"DROP TABLE {tabla} PURGE")
                except Exception as e:      # ORA-00942: la tabla no existía
                    if "ORA-00942" not in str(e):
                        raise
            cur.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = 'EVENTOS'")
            existe = cur.fetchone()[0] > 0
            for s in self.ddl(ORGANIZACION_TABLAS + (() if existe else ("eventos",))):
                cur.execute(s)
            self.con.commit()


class AlmacenOracleREST(Almacen):
    """Oracle Autonomous Database por HTTPS (REST-Enabled SQL de ORDS). Sin wallet ni puerto 1522: va por el
    mismo camino que Database Actions en el navegador. Requiere ORDS_ADMIN.ENABLE_SCHEMA sobre el esquema."""
    motor = "oracle"

    def __init__(self, url, usuario, clave, timeout=20, abrir_url=None):
        super().__init__()
        if not url.startswith("https://") or not url.rstrip("/").endswith("/_/sql"):
            raise SystemExit("CNOSOS_ORDS_URL debe ser https://…/ords/cnosos_app/_/sql")
        self.url, self.timeout = url, timeout
        self._auth = "Basic " + base64.b64encode(f"{usuario}:{clave}".encode()).decode()
        self._abrir = abrir_url or urlopen
        self.con = None
        self._cola = Queue()
        threading.Thread(target=self._escritor, daemon=True).start()

    def _tipo(self, tipo, largo):
        return f"VARCHAR2({largo} CHAR)" if tipo == "t" else "NUMBER(12)"

    @staticmethod
    def _binds(sql, binds):
        nombres = dict.fromkeys(re.findall(r"(?<!:):([a-z_]\w*)", sql))
        salida = []
        for n in nombres:
            v = binds.get(n)
            salida.append({"name": n, "data_type": "NUMBER" if isinstance(v, (int, float)) and not isinstance(v, bool)
                           else "VARCHAR2", "value": v})
        return salida

    def _sql(self, sql, binds=None):
        cuerpo = {"statementText": sql}
        if binds:
            cuerpo["binds"] = self._binds(sql, binds)
        req = Request(self.url, data=json.dumps(cuerpo).encode(), method="POST",
                      headers={"Content-Type": "application/json", "Authorization": self._auth})
        try:
            with self._abrir(req, timeout=self.timeout) as r:
                datos = json.loads(r.read())
        except HTTPError as e:
            raise RuntimeError(f"Oracle REST respondió {e.code}: {e.read()[:200].decode(errors='replace')}") from None
        except (URLError, TimeoutError, OSError) as e:
            raise RuntimeError(f"Sin conexión con Oracle REST: {e}") from None
        item = (datos.get("items") or [{}])[0]
        if item.get("errorCode"):
            raise RuntimeError(f"ORA-{int(item['errorCode']):05d}: {item.get('errorMessage', '')[:200]}")
        return item

    def consultar(self, sql, **binds):
        with self.candado:
            item = self._sql(sql, binds)
        filas = (item.get("resultSet") or {}).get("items") or []
        return [{k.lower(): v for k, v in f.items()} for f in filas]

    def ejecutar(self, sql, **binds):
        with self.candado:
            self._sql(sql, binds)

    def ejecutar_fondo(self, sql, **binds):
        self._cola.put((sql, binds))

    def _escritor(self):
        while True:
            sql, binds = self._cola.get()
            try:
                self.ejecutar(sql, **binds)
            except Exception:       # el registro es secundario: si falla, el portal sigue
                pass
            finally:
                self._cola.task_done()

    def muchos(self, sql, filas):
        for f in filas:
            self.ejecutar(sql, **f)

    def reiniciar(self):
        """Recrea la organización. La tabla eventos se conserva: acumula todos los episodios."""
        for tabla in ORGANIZACION_TABLAS[::-1]:
            try:
                self.ejecutar(f"DROP TABLE {tabla} PURGE")
            except RuntimeError as e:
                if "ORA-00942" not in str(e):
                    raise
        existe = self.consultar("SELECT COUNT(*) AS n FROM user_tables WHERE table_name = 'EVENTOS'")[0]["n"] > 0
        for s in self.ddl(ORGANIZACION_TABLAS + (() if existe else ("eventos",))):
            self.ejecutar(s)

    def cerrar(self):
        self._cola.join()


def abrir(entorno=None):
    e = os.environ if entorno is None else entorno
    if e.get("DEDALUS_ALMACEN", "sqlite").lower() == "oracle_rest":
        faltan = [v for v in ("CNOSOS_ORDS_URL", "CNOSOS_DB_USUARIO", "CNOSOS_DB_CLAVE") if not e.get(v)]
        if faltan:
            raise SystemExit("Para usar Oracle por HTTPS faltan estas variables de entorno: " + ", ".join(faltan))
        return AlmacenOracleREST(e["CNOSOS_ORDS_URL"], e["CNOSOS_DB_USUARIO"], e["CNOSOS_DB_CLAVE"])
    if e.get("DEDALUS_ALMACEN", "sqlite").lower() == "oracle":
        faltan = [v for v in ("CNOSOS_DB_USUARIO", "CNOSOS_DB_CLAVE", "CNOSOS_DB_DSN") if not e.get(v)]
        if faltan:
            raise SystemExit("Para usar Oracle faltan estas variables de entorno: " + ", ".join(faltan)
                             + ". Defínelas en esta misma ventana de PowerShell, o quita DEDALUS_ALMACEN para usar SQLite.")
        return AlmacenOracle(e["CNOSOS_DB_USUARIO"], e["CNOSOS_DB_CLAVE"], e["CNOSOS_DB_DSN"],
                             e.get("CNOSOS_WALLET_DIR"), e.get("CNOSOS_WALLET_CLAVE"))
    return AlmacenSQLite(e.get("DEDALUS_SQLITE", ":memory:"))
