"""El verificador: decide si un parche sirve. No usa ningún modelo.

Un parche pasa si:
  1. supera el filtro estático (solo imports y llamadas permitidos; nada de archivos, red, procesos ni exec),
  2. el usuario legítimo sigue funcionando (las pruebas funcionales del caso),
  3. el exploit del caso deja de funcionar.

El código del modelo se ejecuta en un proceso aparte de Python (-I), con tiempo máximo y una carpeta temporal
propia. El filtro y el proceso aparte reducen el riesgo; no son una caja de arena del sistema operativo.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile

IMPORTS = {"os", "os.path", "html", "hashlib", "hmac", "secrets", "re", "string", "urllib.parse", "unicodedata"}
NOMBRES_PROHIBIDOS = {"exec", "eval", "compile", "open", "__import__", "globals", "locals", "vars", "getattr",
                      "setattr", "delattr", "input", "breakpoint", "exit", "quit", "memoryview", "__builtins__"}
OS_PERMITIDO = {"path", "sep", "altsep", "curdir", "pardir"}
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIEMPO_MAX = 10


def revisar(codigo, funcion):
    """Devuelve una lista de problemas. Vacía = el parche puede ejecutarse."""
    try:
        arbol = ast.parse(codigo)
    except SyntaxError as e:
        return [f"sintaxis: {e.msg} (línea {e.lineno})"]
    problemas = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            problemas += [f"import no permitido: {a.name}" for a in nodo.names if a.name not in IMPORTS]
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.module not in IMPORTS:
                problemas.append(f"import no permitido: {nodo.module}")
            elif nodo.module == "os":
                problemas += [f"os.{a.name} no permitido" for a in nodo.names if a.name not in OS_PERMITIDO]
        elif isinstance(nodo, ast.Name) and nodo.id in NOMBRES_PROHIBIDOS:
            problemas.append(f"nombre no permitido: {nodo.id}")
        elif isinstance(nodo, ast.Attribute):
            if nodo.attr.startswith("__"):
                problemas.append(f"atributo no permitido: {nodo.attr}")
            if isinstance(nodo.value, ast.Name) and nodo.value.id == "os" and nodo.attr not in OS_PERMITIDO:
                problemas.append(f"os.{nodo.attr} no permitido")
    if not any(isinstance(n, ast.FunctionDef) and n.name == funcion for n in arbol.body):
        problemas.append(f"falta la función {funcion}")
    return problemas


# Lo que corre dentro del proceso aparte. Recibe la raíz del repositorio, el caso y el archivo con el código.
_EJECUTOR = r"""
import json, sys, tempfile, traceback
sys.path.insert(0, sys.argv[1])
from dedalus.casos import CASOS
from dedalus.verificador import revisar
caso = CASOS[sys.argv[2]]
codigo = open(sys.argv[3], encoding="utf-8").read()
salida = {"filtro": revisar(codigo, caso["funcion"])}
if not salida["filtro"]:
    espacio = {"__name__": "parche"}
    try:
        exec(compile(codigo, "parche.py", "exec"), espacio)
        fn = espacio[caso["funcion"]]
        extra = (tempfile.mkdtemp(),) if caso.get("tmp") else ()
        try:
            salida["funcional"] = bool(caso["funcional"](fn, *extra))
        except Exception as e:
            salida["funcional"], salida["error_funcional"] = False, f"{type(e).__name__}: {e}"[:200]
        extra = (tempfile.mkdtemp(),) if caso.get("tmp") else ()
        salida["exploit"] = bool(caso["exploit"](fn, *extra))
    except Exception as e:
        salida["error"] = f"{type(e).__name__}: {e}"[:200]
print(json.dumps(salida))
"""


def verificar(caso_id, codigo):
    """Corre el parche contra las pruebas del caso en otro proceso. Devuelve un dict con el veredicto."""
    from .casos import CASOS
    problemas = revisar(codigo, CASOS[caso_id]["funcion"])
    resultado = {"filtro": problemas, "funcional": False, "exploit": None, "error": None}
    if problemas:
        resultado["veredicto"] = "rechazado por el filtro"
        resultado["verificado"] = False
        return resultado
    with tempfile.TemporaryDirectory() as tmp:
        archivo = os.path.join(tmp, "parche.py")
        with open(archivo, "w", encoding="utf-8") as f:
            f.write(codigo)
        try:
            p = subprocess.run([sys.executable, "-I", "-c", _EJECUTOR, RAIZ, caso_id, archivo], cwd=tmp,
                               capture_output=True, text=True, timeout=TIEMPO_MAX)
            datos = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {"error": p.stderr[-300:]}
        except subprocess.TimeoutExpired:
            datos = {"error": f"superó {TIEMPO_MAX} s"}
        except (ValueError, IndexError):
            datos = {"error": "salida ilegible del proceso"}
    resultado.update({k: datos.get(k, resultado.get(k)) for k in ("funcional", "exploit", "error", "error_funcional")})
    resultado["verificado"] = bool(resultado["funcional"]) and resultado["exploit"] is False and not resultado["error"]
    if resultado["error"]:
        resultado["veredicto"] = "no corre: " + resultado["error"]
    elif not resultado["funcional"]:
        resultado["veredicto"] = "rompe el uso legítimo"
    elif resultado["exploit"]:
        resultado["veredicto"] = "el exploit sigue funcionando"
    else:
        resultado["veredicto"] = "verificado: exploit bloqueado, uso legítimo intacto"
    return resultado
