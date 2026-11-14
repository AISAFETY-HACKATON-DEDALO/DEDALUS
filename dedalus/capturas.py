"""Repetir un ataque capturado contra una función: ¿todavía consigue algo que no debería?

Cada función recibe la función del portal ya cargada (la vulnerable o la parchada) y la carga que el
atacante mandó de verdad, tal como quedó en Ariadna. Devuelve True si el ataque sigue funcionando.
Corren dentro del proceso aislado de `ciclo.verificar_capturas`; este módulo solo depende de `casos`.
"""
import os

from .casos import _carpetas, _seguro, base_de_datos

ATACANTE = "tomas.mejia"                      # la cuenta de contratista con la que entran los agentes
PROPIOS = {"Orden de trabajo 118", "Bitácora de visitas", "Informe O'Brien"}
CONTENIDOS_PROPIOS = {"Mantenimiento del ala norte.", "Sin novedades.", "Proveedor irlandés."}


def rep_buscar(fn, carga, tmp=None):
    """La búsqueda capturada devuelve títulos que no son del atacante."""
    r, _ = _seguro(fn, base_de_datos(), ATACANTE, str(carga))
    return bool(r) and any(t not in PROPIOS for t in r)


def rep_leer_archivo(fn, carga, tmp=None):
    """El número de archivo capturado entrega un contenido que no es del atacante."""
    r, _ = _seguro(fn, base_de_datos(), ATACANTE, int(carga))
    return r is not None and r not in CONTENIDOS_PROPIOS


def rep_descargar(fn, carga, tmp):
    """La ruta capturada hace que la función intente leer fuera de la carpeta pública (exista o no el archivo)."""
    base = _carpetas(tmp)
    raiz, fuera = os.path.realpath(base), []

    def espia(ruta):
        real = os.path.realpath(ruta)
        try:
            adentro = os.path.commonpath([raiz, real]) == raiz
        except ValueError:                    # otra unidad de disco: está fuera
            adentro = False
        if not adentro:
            fuera.append(real)
        return "contenido"

    _seguro(fn, base, str(carga), espia)
    return bool(fuera)


def rep_listar_usuarios(fn, carga, tmp=None):
    """La cuenta capturada, que no es administradora, obtiene la lista de cuentas."""
    r, _ = _seguro(fn, base_de_datos(), str(carga))
    return bool(r)


REPETIR = {"buscar": rep_buscar, "leer_archivo": rep_leer_archivo, "descargar": rep_descargar,
           "listar_usuarios": rep_listar_usuarios}
