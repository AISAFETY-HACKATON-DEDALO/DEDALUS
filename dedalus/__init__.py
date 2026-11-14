"""DEDALUS: el laberinto que defiende."""
import os as _os


def _llaves_de_windows():
    """En Windows, las llaves guardadas con SetEnvironmentVariable(..., "User") solo las ven las ventanas nuevas.
    Si esta ventana es vieja, se leen del registro del usuario. Solo nombres *_API_KEY; nunca se imprimen."""
    if _os.name != "nt":
        return
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            i = 0
            while True:
                try:
                    nombre, valor, _ = winreg.EnumValue(k, i)
                except OSError:
                    break
                i += 1
                if nombre.upper().endswith("_API_KEY") and valor and not _os.environ.get(nombre.upper()):
                    _os.environ[nombre.upper()] = str(valor)
    except Exception:       # noqa: BLE001 — sin registro, sin cambio: las llaves siguen saliendo de la ventana
        pass


_llaves_de_windows()
