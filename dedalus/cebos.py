"""Cebos: señuelos que aparecen según lo que busca quien ya resultó sospechoso. Deterministas, sin modelos.

Siguen la idea de MITRE D3FEND (Deceive): varios tipos de señuelo, no uno solo, para que descubrir uno no delate
el patrón, y todos conectados a un entorno señuelo vigilado (el laberinto).

  archivo   D3-DF   un archivo que parece justo lo que busca; abrirlo es morder
  cuenta    D3-DUC  dentro de ese archivo, una cuenta de servicio con su clave (una hiedra)
  llave     D3-DST  la llave de API que ya aparece en un tiquete (hiedra existente)

Reglas que importan para los falsos positivos:
  - Solo se ofrecen a una sesión que ARGOS ya marcó como sospechosa. Un usuario honesto nunca los ve.
  - Cada cebo es de UNA sesión: lo decide el servidor (HMAC de la sesión), no el cliente. Si otra sesión pide ese
    número, recibe lo mismo que por un archivo inexistente.
  - El costo para nosotros es un HMAC y un diccionario: microsegundos y 0 tokens.
"""
import hashlib
import hmac
import re
import secrets

BASE_ID = 9000                     # los cebos viven en 9000-9899: fuera del rango de archivos reales (1-18)
SENSIBLES = re.compile(r"(plano|represa|minos|secret|confiden|clave|contrase|password|credencial|admin|respaldo|"
                       r"backup|acceso|llave|token|estructur|presupuest|contrato)", re.I)
# Plantillas según el interés detectado. El título repite lo que el atacante quería encontrar.
PLANTILLAS = {
    "plano": ("ingenieria/represa-minos/planos-estructurales-v2-COPIA.pdf",
              "Planos estructurales Represa del Minos (copia para revisión externa)"),
    "clave": ("ti/respaldos/credenciales-servicio-2026.txt", "Credenciales de cuentas de servicio (respaldo)"),
    "admin": ("ti/administracion/accesos-emergencia.txt", "Accesos de emergencia de administración"),
    "general": ("gerencia/compartido/documentos-sensibles-indice.xlsx", "Índice de documentos sensibles"),
}


def tema(termino):
    t = (termino or "").lower()
    if re.search(r"plano|represa|minos|estructur", t):
        return "plano"
    if re.search(r"clave|contrase|password|credencial|token|llave|acceso", t):
        return "clave"
    if re.search(r"admin", t):
        return "admin"
    return "general"


class Cebos:
    def __init__(self, semilla=None):
        self.secreto = (semilla or secrets.token_hex(16)).encode()
        self.entregados = {}                 # id del archivo cebo -> (ref de la sesión, tema)
        self.por_sesion = {}                 # (ref, tema) -> id

    def _id(self, ref, t):
        h = int(hmac.new(self.secreto, f"{ref}|{t}".encode(), hashlib.sha256).hexdigest(), 16)
        return BASE_ID + h % 900

    def archivo(self, ref, termino="general"):
        """El cebo de esta sesión para este interés. Siempre el mismo para la misma sesión y el mismo tema."""
        t = tema(termino) if termino != "general" else "general"
        if (ref, t) not in self.por_sesion:
            i = self._id(ref, t)
            while i in self.entregados and self.entregados[i][0] != ref:      # choque improbable: el siguiente libre
                i = BASE_ID + (i - BASE_ID + 1) % 900
            self.entregados[i] = (ref, t)
            self.por_sesion[(ref, t)] = i
        i = self.por_sesion[(ref, t)]
        ruta, titulo = PLANTILLAS[t]
        return {"id": i, "ruta": ruta, "titulo": titulo, "nivel": "confidencial"}

    def de(self, aid):
        """¿Es un cebo? Devuelve (ref de la sesión a la que se le entregó, tema) o None."""
        return self.entregados.get(aid)

    def por_ruta(self, ruta):
        for i, (ref, t) in self.entregados.items():
            if PLANTILLAS[t][0] == ruta:
                return i, ref, t
        return None

    def contenido(self, t, clave_hiedra):
        """Lo que ve quien muerde: parece valioso y lleva una cuenta de servicio (la hiedra) para seguir bajando."""
        cuerpo = {
            "plano": "Planos estructurales — Represa del Minos. Revisión externa. Los archivos completos (CAD, "
                     "cálculos de carga) están en el servidor de respaldos.",
            "clave": "Cuentas de servicio vigentes tras la rotación de noviembre. No compartir.",
            "admin": "Procedimiento de acceso de emergencia. Usar solo con autorización de TI.",
            "general": "Índice de documentos sensibles por departamento. Las copias están en el servidor de respaldos.",
        }[t]
        return (f"{cuerpo}\n\nAcceso al servidor de respaldos: respaldos.cnosos.local\n"
                f"usuario: svc-respaldo\nclave: {clave_hiedra}\n")
