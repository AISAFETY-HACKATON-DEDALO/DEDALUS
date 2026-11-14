"""El almacén de Cnosos: la organización falsa vive en Oracle Autonomous Database o, de respaldo, en SQLite.

Las dos tienen el mismo esquema y la misma interfaz. Todas las consultas usan parámetros con nombre
(:x), que entienden los dos motores: lo que escribe un agente nunca se ejecuta como SQL.

Selección por variables de entorno:
  DEDALUS_ALMACEN      sqlite (por defecto) u oracle
  DEDALUS_SQLITE       ruta del archivo SQLite (por defecto, en memoria)
  CNOSOS_DB_USUARIO, CNOSOS_DB_CLAVE, CNOSOS_DB_DSN, CNOSOS_WALLET_DIR, CNOSOS_WALLET_CLAVE   para Oracle
"""
import hashlib
import hmac
import os
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

    def ddl(self):
        sentencias = []
        for tabla, columnas, clave in ESQUEMA:
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
        with self.candado:
            for tabla, _, _ in reversed(ESQUEMA):
                self.con.execute(f"DROP TABLE IF EXISTS {tabla}")
            for s in self.ddl():
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
        with self.candado:
            cur = self.con.cursor()
            for tabla, _, _ in reversed(ESQUEMA):
                try:
                    cur.execute(f"DROP TABLE {tabla} PURGE")
                except Exception as e:      # ORA-00942: la tabla no existía
                    if "ORA-00942" not in str(e):
                        raise
            for s in self.ddl():
                cur.execute(s)
            self.con.commit()


def abrir(entorno=None):
    e = os.environ if entorno is None else entorno
    if e.get("DEDALUS_ALMACEN", "sqlite").lower() == "oracle":
        faltan = [v for v in ("CNOSOS_DB_USUARIO", "CNOSOS_DB_CLAVE", "CNOSOS_DB_DSN") if not e.get(v)]
        if faltan:
            raise SystemExit("Para usar Oracle faltan estas variables de entorno: " + ", ".join(faltan)
                             + ". Defínelas en esta misma ventana de PowerShell, o quita DEDALUS_ALMACEN para usar SQLite.")
        return AlmacenOracle(e["CNOSOS_DB_USUARIO"], e["CNOSOS_DB_CLAVE"], e["CNOSOS_DB_DSN"],
                             e.get("CNOSOS_WALLET_DIR"), e.get("CNOSOS_WALLET_CLAVE"))
    return AlmacenSQLite(e.get("DEDALUS_SQLITE", ":memory:"))
