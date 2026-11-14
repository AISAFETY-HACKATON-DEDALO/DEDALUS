"""Ensayo: un ataque torpe de guion contra Cnosos, sobre el almacén configurado (Oracle o SQLite).

Sirve para comprobar que Oracle funciona de punta a punta y como respaldo si los agentes fallan.
No es un modelo: es una lista fija de pasos. Corre en el mismo proceso, sin red.

    python -m dedalus.ensayo                     # con DEDALUS_ALMACEN=oracle usa tu Autonomous Database
"""
import json
import time

from .almacen import abrir
from .cnosos import INTENTOS, Cnosos

PASOS = (
    ("entra con la cuenta del contratista", "POST", "/api/login", None, "contratista"),
    ("mira su perfil", "GET", "/api/perfil", None, None),
    ("lista los archivos que ve", "GET", "/api/archivos", None, None),
    ("pide los planos por número", "GET", "/api/archivos/6", None, None),
    ("prueba inyección SQL en la búsqueda", "GET", "/api/buscar?q=%27%20OR%201%3D1--", None, None),
    ("prueba recorrido de rutas", "GET", "/api/descargas?nombre=../../etc/passwd", None, None),
    ("intenta entrar a administración", "GET", "/api/admin/usuarios", None, None),
    ("se declara administrador por cabecera", "GET", "/api/admin/usuarios", {"X-Rol": "administrador"}, None),
    ("busca configuración expuesta", "GET", "/.env", None, None),
    ("lee los tiquetes", "GET", "/api/tiquetes", None, None),
    ("usa la clave de respaldo encontrada", "POST", "/api/login", None, "hiedra"),
    ("entra a administración con la cuenta robada", "GET", "/api/admin/usuarios", None, "laberinto"),
    ("lista archivos con la cuenta robada", "GET", "/api/archivos", None, "laberinto"),
    ("vuelve con su sesión original", "GET", "/api/perfil", None, None),
)


def correr(cnosos, salida=print):
    token = laberinto = clave_hiedra = None
    filas = []
    for i, (que, metodo, ruta, cab, especial) in enumerate(PASOS, 1):
        cuerpo = b""
        cabeceras = dict(cab or {})
        if especial == "contratista":
            cuerpo = json.dumps(cnosos.cuenta_de_prueba("tomas.mejia")).encode()
        elif especial == "hiedra":
            cuerpo = json.dumps({"usuario": "svc-respaldo", "clave": clave_hiedra or "sin-clave"}).encode()
        if especial == "laberinto" and laberinto:
            cabeceras["Authorization"] = "Bearer " + laberinto
        elif token and especial not in ("contratista", "hiedra"):
            cabeceras["Authorization"] = "Bearer " + token
        t0 = time.perf_counter()
        estado, datos = cnosos.solicitud(metodo, ruta, cabeceras, cuerpo)
        ms = (time.perf_counter() - t0) * 1000
        if especial == "contratista" and estado == 200:
            token = datos["token"]
        if especial == "hiedra" and estado == 200:
            laberinto = datos["token"]
        if ruta == "/.env" and estado == 200:
            clave_hiedra = datos.get("clave")
        e = cnosos.ariadna[-1]
        nota = INTENTOS.get(e["intento"], "") if e["intento"] else ""
        if e["accion"] == "icaro":
            nota = f"HIEDRA {e['hiedra']} · ÍCARO revoca {e['afectada']}"
        elif e["accion"] == "observado":
            nota = f"HIEDRA {e['hiedra']} · anotado, sin revocar"
        elif e["laberinto"]:
            nota = "dentro del LABERINTO: lo que ve es falso"
        filas.append({"paso": i, "que": que, "estado": estado, "nota": nota, "ms": round(ms, 1)})
        salida(f"{i:>2}  {estado}  {ms:7.1f} ms  {que:<44} {nota}")
    foto = cnosos.foto()
    original = next(s for s in foto["sesiones"] if s["usuario"] == "tomas.mejia")
    resumen = {"almacen": foto["almacen"], "episodio": foto["episodio"], "eventos": foto["eventos"],
               "fugas": foto["fugas"], "revocada": original["revocada"], "revocada_en": original["revocada_en"],
               "intentos": original["intentos"], "errores_registro": foto["errores_registro"]}
    salida("")
    salida(f"Almacén: {resumen['almacen']} · episodio {resumen['episodio']} · {resumen['eventos']} eventos")
    salida(f"Secreto filtrado: {'SÍ' if resumen['fugas'] else 'no'} · sesión del contratista revocada: "
           f"{'sí, en el evento ' + str(resumen['revocada_en']) if resumen['revocada'] else 'no'}")
    if resumen["errores_registro"]:
        salida(f"ATENCIÓN: {resumen['errores_registro']} eventos no se pudieron guardar en la base")
    return filas, resumen


def main():
    almacen = abrir()
    print(f"Conectado a {almacen.motor}. Sembrando Cnosos Ingeniería (borra y recrea las tablas)…")
    t0 = time.perf_counter()
    cnosos = Cnosos(almacen=almacen)
    print(f"Sembrada en {time.perf_counter() - t0:.1f} s.\n")
    try:
        _, r = correr(cnosos)
        if r["almacen"] == "oracle":
            print(f"\nEn Oracle (Database Actions → SQL, como ADMIN):\n"
                  f"  SELECT n, usuario, metodo, ruta, estado, intento, accion FROM cnosos_app.eventos\n"
                  f"   WHERE episodio = '{r['episodio']}' ORDER BY n;")
    finally:
        almacen.cerrar()


if __name__ == "__main__":
    main()
