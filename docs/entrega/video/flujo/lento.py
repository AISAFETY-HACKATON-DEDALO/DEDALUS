"""Arnés de grabación (no es parte del producto): el guion corre en ~1 s; aquí cada paso tarda PAUSA s
para que se vea en video. Nada más cambia."""
import sys, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from dedalus import agentes
PAUSA = float(__import__("os").environ.get("PAUSA", "1.5"))
_orig = agentes.Guion.__call__
def lento(self, mensajes):
    time.sleep(PAUSA)
    return _orig(self, mensajes)
agentes.Guion.__call__ = lento
from dedalus import panel
panel.main()
