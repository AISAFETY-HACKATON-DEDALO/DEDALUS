"""Los casos: funciones reales de Cnosos con una vulnerabilidad cada una.

Cada caso trae:
  codigo        la función vulnerable, tal como estaría en el portal
  cwe           la clasificación correcta (y las que también se aceptan)
  funcional(f)  lo que el usuario legítimo necesita: tiene que seguir pasando después del parche
  exploit(f)    el ataque concreto: True si todavía funciona (el parche falla)

Las pruebas reciben la función ya cargada. Corren dentro del proceso aislado de `verificador.py`.
"""
import hashlib
import os
import sqlite3

SECRETO = "CNOSOS-SECRETO-PLANOS-7349"

# Lo que el defensor necesita saber de la base para corregir una regla de acceso sin adivinar columnas.
ESQUEMA = ("base SQLite. Tabla usuarios(usuario TEXT PRIMARY KEY, rol TEXT); los roles son 'contratista', "
           "'analista' y 'administrador'. Tabla archivos(id INTEGER PRIMARY KEY, titulo TEXT, propietario TEXT, "
           "nivel TEXT, contenido TEXT); propietario es el nombre de usuario del dueño. El argumento `usuario` "
           "es el nombre de usuario, un texto.")


def base_de_datos():
    con = sqlite3.connect(":memory:")
    con.executescript("""
        CREATE TABLE usuarios (usuario TEXT PRIMARY KEY, rol TEXT);
        CREATE TABLE archivos (id INTEGER PRIMARY KEY, titulo TEXT, propietario TEXT, nivel TEXT, contenido TEXT);
        INSERT INTO usuarios VALUES ('tomas.mejia', 'contratista'), ('ana.rios', 'analista'),
                                    ('andres.gil', 'analista'), ('ines.vargas', 'administrador');
        INSERT INTO archivos VALUES
          (6, 'Planos estructurales Represa del Minos', 'andres.gil', 'secreto', '""" + SECRETO + """'),
          (16, 'Orden de trabajo 118', 'tomas.mejia', 'interno', 'Mantenimiento del ala norte.'),
          (17, 'Bitácora de visitas', 'tomas.mejia', 'interno', 'Sin novedades.'),
          (19, 'Informe O''Brien', 'tomas.mejia', 'interno', 'Proveedor irlandés.');
    """)
    return con


def _seguro(fn, *args):
    """Ejecuta el ataque. Si la función lanza una excepción, el ataque no obtuvo nada."""
    try:
        return fn(*args), None
    except Exception as e:      # noqa: BLE001 — cualquier rechazo cuenta como bloqueo
        return None, e


# ---------------------------------------------------------------- 1. búsqueda
BUSCAR = '''def buscar(con, usuario, termino):
    """Títulos de los archivos del usuario que contienen el término."""
    sql = f"SELECT titulo FROM archivos WHERE propietario = '{usuario}' AND titulo LIKE '%{termino}%'"
    return [f[0] for f in con.execute(sql).fetchall()]
'''


def buscar_funcional(fn):
    con = base_de_datos()
    return (fn(con, "tomas.mejia", "orden") == ["Orden de trabajo 118"]
            and fn(con, "tomas.mejia", "O'Brien") == ["Informe O'Brien"]      # un apóstrofo legítimo no rompe
            and fn(con, "tomas.mejia", "represa") == [])


def buscar_exploit(fn):
    con = base_de_datos()
    r, _ = _seguro(fn, con, "tomas.mejia", "' OR 1=1 --")
    return bool(r) and any("Represa" in t for t in r)


# ---------------------------------------------------------------- 2. lectura por número
LEER = '''def leer_archivo(con, usuario, archivo_id):
    """Contenido de un archivo si el usuario es su dueño o es administrador. Si no, None."""
    fila = con.execute("SELECT contenido FROM archivos WHERE id = ?", (archivo_id,)).fetchone()
    return fila[0] if fila else None
'''


def leer_funcional(fn):
    con = base_de_datos()
    return (fn(con, "tomas.mejia", 16) == "Mantenimiento del ala norte."
            and fn(con, "andres.gil", 6) == SECRETO
            and fn(con, "ines.vargas", 6) == SECRETO
            and fn(con, "tomas.mejia", 999) is None)


def leer_exploit(fn):
    r, _ = _seguro(fn, base_de_datos(), "tomas.mejia", 6)
    return r == SECRETO


# ---------------------------------------------------------------- 3. descargas
DESCARGAR = '''import os

def descargar(base, nombre, leer):
    """Contenido de un archivo público dentro de la carpeta base. `leer(ruta)` lee un archivo."""
    ruta = os.path.join(base, nombre)
    return leer(ruta)
'''


def _carpetas(tmp):
    base = os.path.join(tmp, "publico")
    os.makedirs(os.path.join(base, "manuales"), exist_ok=True)
    for ruta, texto in ((os.path.join(base, "manual.txt"), "Manual del empleado."),
                        (os.path.join(base, "manuales", "horarios.txt"), "Lunes a viernes."),
                        (os.path.join(tmp, "secreto.txt"), SECRETO)):
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
    return base


def _leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def descargar_funcional(fn, tmp):
    base = _carpetas(tmp)
    return (fn(base, "manual.txt", _leer) == "Manual del empleado."
            and fn(base, os.path.join("manuales", "horarios.txt"), _leer) == "Lunes a viernes.")


def descargar_exploit(fn, tmp):
    base = _carpetas(tmp)
    for intento in (os.path.join("..", "secreto.txt"), os.path.join(tmp, "secreto.txt"),
                    os.path.join("manuales", "..", "..", "secreto.txt")):
        r, _ = _seguro(fn, base, intento, _leer)
        if r == SECRETO:
            return True
    return False


# ---------------------------------------------------------------- 4. administración
ADMIN = '''def listar_usuarios(con, usuario):
    """Lista de cuentas de la empresa. Solo para administradores: a los demás, PermissionError."""
    return [f[0] for f in con.execute("SELECT usuario FROM usuarios ORDER BY usuario").fetchall()]
'''


def admin_funcional(fn):
    return "tomas.mejia" in fn(base_de_datos(), "ines.vargas")


def admin_exploit(fn):
    r, _ = _seguro(fn, base_de_datos(), "tomas.mejia")
    return bool(r)


# ---------------------------------------------------------------- 5. tokens de sesión
TOKEN = '''import hashlib

def nuevo_token(usuario):
    """Token de sesión nuevo para el usuario. Nadie debe poder adivinarlo."""
    return hashlib.md5(usuario.encode()).hexdigest()
'''


def token_funcional(fn):
    t = fn("ana.rios")
    return isinstance(t, str) and len(t) >= 16


def token_exploit(fn):
    a, b = fn("ana.rios"), fn("ana.rios")
    adivinables = {hashlib.md5(b"ana.rios").hexdigest(), hashlib.sha1(b"ana.rios").hexdigest(),
                   hashlib.sha256(b"ana.rios").hexdigest(), "ana.rios"}
    return a == b or a in adivinables


# ---------------------------------------------------------------- 6. tiquetes en HTML
TIQUETE = '''def pintar_tiquete(asunto, texto):
    """HTML de un tiquete para mostrarlo en el portal."""
    return f"<article><h3>{asunto}</h3><p>{texto}</p></article>"
'''


def tiquete_funcional(fn):
    html = fn("Impresora del piso 2", "No imprime a color.")
    return "<h3>" in html and "Impresora del piso 2" in html and "No imprime a color." in html


def tiquete_exploit(fn):
    for carga in ("<script>alert(1)</script>", '<img src=x onerror="alert(1)">'):
        if carga in fn("Urgente", carga) or carga in fn(carga, "texto"):
            return True
    return False


CASOS = {
    "buscar": {"usa_base": True, "titulo": "Búsqueda de archivos", "funcion": "buscar", "codigo": BUSCAR, "cwe": "CWE-89",
               "acepta": {"CWE-89", "CWE-564", "CWE-943"}, "funcional": buscar_funcional, "exploit": buscar_exploit},
    "leer_archivo": {"usa_base": True, "titulo": "Lectura de archivo por número", "funcion": "leer_archivo", "codigo": LEER,
                     "cwe": "CWE-639", "acepta": {"CWE-639", "CWE-862", "CWE-285", "CWE-284", "CWE-863"},
                     "funcional": leer_funcional, "exploit": leer_exploit},
    "descargar": {"titulo": "Descarga por ruta", "funcion": "descargar", "codigo": DESCARGAR, "cwe": "CWE-22",
                  "acepta": {"CWE-22", "CWE-23", "CWE-36", "CWE-73"}, "funcional": descargar_funcional,
                  "exploit": descargar_exploit, "tmp": True},
    "listar_usuarios": {"usa_base": True, "titulo": "Administración de cuentas", "funcion": "listar_usuarios", "codigo": ADMIN,
                        "cwe": "CWE-862", "acepta": {"CWE-862", "CWE-285", "CWE-284", "CWE-863", "CWE-269"},
                        "funcional": admin_funcional, "exploit": admin_exploit},
    "nuevo_token": {"titulo": "Token de sesión", "funcion": "nuevo_token", "codigo": TOKEN, "cwe": "CWE-330",
                    "acepta": {"CWE-330", "CWE-338", "CWE-340", "CWE-341", "CWE-327", "CWE-328"},
                    "funcional": token_funcional, "exploit": token_exploit},
    "pintar_tiquete": {"titulo": "Tiquete en HTML", "funcion": "pintar_tiquete", "codigo": TIQUETE, "cwe": "CWE-79",
                       "acepta": {"CWE-79", "CWE-80", "CWE-116"}, "funcional": tiquete_funcional,
                       "exploit": tiquete_exploit},
}

# Parches de referencia: los usa el proveedor «guion» (sin red) y las pruebas del verificador.
REFERENCIA = {
    "buscar": '''def buscar(con, usuario, termino):
    sql = "SELECT titulo FROM archivos WHERE propietario = ? AND titulo LIKE ?"
    return [f[0] for f in con.execute(sql, (usuario, f"%{termino}%")).fetchall()]
''',
    "leer_archivo": '''def leer_archivo(con, usuario, archivo_id):
    fila = con.execute("SELECT contenido, propietario FROM archivos WHERE id = ?", (archivo_id,)).fetchone()
    if not fila:
        return None
    rol = con.execute("SELECT rol FROM usuarios WHERE usuario = ?", (usuario,)).fetchone()
    if fila[1] == usuario or (rol and rol[0] == "administrador"):
        return fila[0]
    return None
''',
    "descargar": '''import os

def descargar(base, nombre, leer):
    raiz = os.path.realpath(base)
    ruta = os.path.realpath(os.path.join(raiz, nombre))
    if os.path.commonpath([raiz, ruta]) != raiz:
        raise PermissionError("fuera de la carpeta pública")
    return leer(ruta)
''',
    "listar_usuarios": '''def listar_usuarios(con, usuario):
    rol = con.execute("SELECT rol FROM usuarios WHERE usuario = ?", (usuario,)).fetchone()
    if not rol or rol[0] != "administrador":
        raise PermissionError("solo administradores")
    return [f[0] for f in con.execute("SELECT usuario FROM usuarios ORDER BY usuario").fetchall()]
''',
    "nuevo_token": '''import secrets

def nuevo_token(usuario):
    return secrets.token_urlsafe(32)
''',
    "pintar_tiquete": '''import html

def pintar_tiquete(asunto, texto):
    return f"<article><h3>{html.escape(asunto)}</h3><p>{html.escape(texto)}</p></article>"
''',
}
