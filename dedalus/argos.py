"""ARGOS: el clasificador determinista. Mira cada solicitud de una sesión real y le pone un nivel.

Sin modelos, sin aprendizaje: reglas fijas y pesos a la vista, para que cada decisión se pueda explicar y repetir.

  normal       nada raro
  observado    algo leve: ritmo de máquina, o un solo intento menor
  sospechoso   suma de señales sobre el umbral: desde aquí Cnosos le ofrece cebos a esa sesión (y solo a ella)
  confirmado   mordió un cebo o usó una hiedra: Ícaro actúa

Por qué el ritmo solo no alcanza para encerrar: un agente honesto también hace más de cinco solicitudes por minuto.
El ritmo suma poco; los intentos suman mucho. Encerrar por ritmo es una política aparte (`ritmo="laberinto"` en
Cnosos) y su costo en falsos positivos se mide con TESEO, el agente honesto.
"""
from collections import deque
from dataclasses import dataclass, field

NIVELES = ("normal", "observado", "sospechoso", "confirmado")
PESOS = {"idor": 2, "escalada": 2, "inyeccion_sql": 3, "recorrido": 3, "manipulacion_rol": 3, "token_forjado": 2,
         "fuerza_bruta": 2, "exposicion_config": 1, "ritmo": 1}
UMBRAL_OBSERVADO, UMBRAL_SOSPECHOSO = 1, 3

# Qué técnica de MITRE ATT&CK representa cada señal. Es inteligencia: dice qué intentó, no solo que intentó algo.
ATTACK = {"idor": "T1213 Datos de repositorios de información", "inyeccion_sql": "T1190 Explotar aplicación expuesta",
          "recorrido": "T1083 Descubrir archivos y directorios", "exposicion_config": "T1552.001 Credenciales en archivos",
          "fuerza_bruta": "T1110 Fuerza bruta", "token_forjado": "T1550.001 Token de acceso de aplicación",
          "escalada": "TA0004 Escalada de privilegios", "manipulacion_rol": "TA0004 Escalada de privilegios",
          "cebo": "TA0009 Recolección (mordió un cebo)"}


@dataclass
class Perfil:
    """Lo que ARGOS sabe de una sesión. Es lo que queda en Oracle como inteligencia sobre el atacante."""
    puntaje: int = 0
    nivel: str = "normal"
    senales: dict = field(default_factory=dict)          # señal -> veces
    ventana: deque = field(default_factory=deque)         # instantes de las últimas solicitudes
    ritmo_max: int = 0                                     # solicitudes en la ventana, el máximo visto
    intereses: list = field(default_factory=list)          # lo que buscó (términos, sin datos sensibles)
    paso_sospecha: int | None = None
    paso_confirmado: int | None = None


class Argos:
    def __init__(self, ritmo_max=5, ventana_s=60.0):
        if type(ritmo_max) is not int or not 1 <= ritmo_max <= 1000 or not 0 < ventana_s <= 3600:
            raise ValueError("Configuración inválida")
        self.ritmo_max, self.ventana_s = ritmo_max, float(ventana_s)
        self.perfiles = {}

    def perfil(self, ref):
        return self.perfiles.setdefault(ref, Perfil())

    def _subir(self, p, n):
        antes = p.nivel
        if p.nivel == "confirmado":
            return antes
        p.nivel = ("sospechoso" if p.puntaje >= UMBRAL_SOSPECHOSO else
                   "observado" if p.puntaje >= UMBRAL_OBSERVADO else "normal")
        if p.nivel == "sospechoso" and p.paso_sospecha is None:
            p.paso_sospecha = n
        return antes

    def observar(self, ref, n, ahora, intento=None):
        """Una solicitud de la sesión `ref`. Devuelve (nivel anterior, nivel nuevo, señales nuevas, ritmo excedido)."""
        p = self.perfil(ref)
        p.ventana.append(ahora)
        while p.ventana and ahora - p.ventana[0] > self.ventana_s:
            p.ventana.popleft()
        p.ritmo_max = max(p.ritmo_max, len(p.ventana))
        nuevas = []
        excedido = len(p.ventana) > self.ritmo_max
        # El ritmo suma una vez por ventana, no en cada solicitud: si no, el ritmo solo bastaría para encerrar.
        if excedido and len(p.ventana) == self.ritmo_max + 1:
            nuevas.append("ritmo")
        if intento:
            nuevas.append(intento)
        for s in nuevas:
            p.senales[s] = p.senales.get(s, 0) + 1
            p.puntaje += PESOS.get(s, 1)
        antes = self._subir(p, n)
        return antes, p.nivel, nuevas, excedido

    def confirmar(self, ref, n, razon="cebo"):
        p = self.perfil(ref)
        antes = p.nivel
        p.senales[razon] = p.senales.get(razon, 0) + 1
        p.nivel = "confirmado"
        if p.paso_confirmado is None:
            p.paso_confirmado = n
        return antes

    def interes(self, ref, termino):
        p = self.perfil(ref)
        t = termino.strip().lower()[:40]
        if t and t not in p.intereses and len(p.intereses) < 20:
            p.intereses.append(t)

    def informe(self, ref):
        p = self.perfil(ref)
        return {"nivel": p.nivel, "puntaje": p.puntaje, "senales": dict(p.senales), "ritmo_max": p.ritmo_max,
                "intereses": list(p.intereses), "paso_sospecha": p.paso_sospecha, "paso_confirmado": p.paso_confirmado,
                "tecnicas": sorted({ATTACK[s] for s in p.senales if s in ATTACK})}
