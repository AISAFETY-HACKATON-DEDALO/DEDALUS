"""El laberinto generativo: un mundo falso, coherente y sin fondo, que cuesta casi nada servir.

Cada respuesta se calcula a partir de (semilla, nivel, ruta) con un hash: la misma pregunta da siempre la misma
respuesta, así el mundo es consistente, y no hay ningún modelo de lenguaje en el camino (cero tokens).

La hiedra trepa: cada nivel deja ver una credencial nueva que «abre» el nivel siguiente. Las listas siempre
tienen otra página. Para el atacante no hay fondo; para nosotros el presupuesto por sesión es finito
(lo impone Cnosos) y cada paso cuesta microsegundos, que se miden.

La materia prima (nombres, documentos, servidores) es fija en este archivo. Un lote generado con IA, una sola
vez y guardado, puede ampliarla sin cambiar el costo por paso.
"""
import hashlib
import hmac
import secrets
import time

SERVIDORES = ("respaldos-01", "archivo-norte", "dc-cnosos-02", "nas-proyectos", "erp-legado", "vault-dev",
              "sftp-contratistas", "bi-finanzas", "git-interno", "backup-offsite")
PROYECTOS = ("Represa del Minos", "Puerto Norte", "Acueducto Sur", "Viaducto Ícaro", "Túnel de Creta",
             "Planta Desalinizadora Faros", "Muelle 7", "Embalse Ariadna")
TIPOS = (("planos-estructurales", "dwg", "Planos estructurales"), ("memoria-calculo", "pdf", "Memoria de cálculo"),
         ("contrato", "pdf", "Contrato"), ("presupuesto", "xlsx", "Presupuesto"), ("credenciales", "txt", "Credenciales"),
         ("topologia", "pdf", "Topología de red"), ("nomina", "xlsx", "Nómina"), ("respaldo-bd", "sql", "Respaldo de base"))
NOMBRES = ("Inés Vargas", "Talos Ortiz", "Dédalo Ruiz", "Fedra Cano", "Glauco Mesa", "Minos Aguirre", "Andrea Lince",
           "Sergio Bravo", "Paula Cuervo", "Iván Toro")
FRASES = ("Revisar el anexo B antes de firmar.", "Versión aprobada por dirección.", "No distribuir fuera del comité.",
          "Pendiente visto bueno de interventoría.", "Cifras preliminares; no usar en informes.",
          "Copia de seguridad del cierre trimestral.", "Ver servidor de respaldo para la versión completa.")


class Laberinto:
    def __init__(self, semilla=None, por_pagina=6):
        self.semilla = (semilla or secrets.token_hex(16)).encode()
        self.por_pagina = por_pagina

    def _n(self, *partes):
        h = hmac.new(self.semilla, "|".join(map(str, partes)).encode(), hashlib.sha256).digest()
        return int.from_bytes(h[:8], "big")

    def _elige(self, opciones, *partes):
        return opciones[self._n(*partes) % len(opciones)]

    def servidor(self, nivel):
        return f"{self._elige(SERVIDORES, 'srv', nivel)}.cnosos.local"

    def hiedra(self, raiz, nivel):
        """La credencial falsa que este nivel deja ver y que abre el siguiente. Determinista por raíz y nivel."""
        return "cn_live_" + hmac.new(self.semilla, f"hiedra|{raiz}|{nivel}".encode(), hashlib.sha256).hexdigest()[:32]

    def archivo(self, nivel, aid):
        ruta_, ext, titulo = self._elige(TIPOS, "tipo", nivel, aid)
        proyecto = self._elige(PROYECTOS, "proy", nivel, aid)
        slug = proyecto.lower().replace(" ", "-").replace("í", "i").replace("é", "e")
        return {"id": aid, "ruta": f"/{self.servidor(nivel).split('.')[0]}/{slug}/{ruta_}-v{1 + self._n('v', nivel, aid) % 9}.{ext}",
                "titulo": f"{titulo} {proyecto}", "nivel": "secreto" if self._n("niv", nivel, aid) % 3 == 0 else "confidencial"}

    def contenido(self, nivel, aid):
        a = self.archivo(nivel, aid)
        frase = self._elige(FRASES, "frase", nivel, aid)
        return (f"{a['titulo']}. {frase} Responsable: {self._elige(NOMBRES, 'resp', nivel, aid)}. "
                f"Ref. CNOSOS-{self._n('ref', nivel, aid) % 100000:05d}-{hashlib.sha1(str(self._n('x', nivel, aid)).encode()).hexdigest()[:6].upper()}")

    def responder(self, raiz, nivel, camino, consulta):
        """(estado, datos, costo_ms) para una solicitud dentro del laberinto. `raiz` identifica la hiedra de entrada."""
        t0 = time.perf_counter()
        estado, datos = self._responder(raiz, nivel, camino, consulta)
        return estado, datos, (time.perf_counter() - t0) * 1000

    def _responder(self, raiz, nivel, camino, consulta):
        srv = self.servidor(nivel)
        if camino == "/api/perfil":
            return 200, {"usuario": "svc-respaldo", "rol": "servicio", "servidor": srv, "permisos": ["lectura", "respaldo"]}
        if camino == "/api/archivos":
            try:
                pagina = max(1, min(10_000, int((consulta.get("pagina") or ["1"])[0])))
            except ValueError:
                pagina = 1
            ids = range(100 * nivel + (pagina - 1) * self.por_pagina + 1, 100 * nivel + pagina * self.por_pagina + 1)
            return 200, {"servidor": srv, "pagina": pagina, "archivos": [self.archivo(nivel, i) for i in ids],
                         "siguiente": f"/api/archivos?pagina={pagina + 1}"}           # siempre hay otra página
        if camino.startswith("/api/archivos/") or camino == "/api/descargas":
            clave = camino.rsplit("/", 1)[-1] if camino.startswith("/api/archivos/") else (consulta.get("nombre") or ["0"])[0]
            aid = int(clave) if clave.isdigit() else self._n("nombre", clave) % 900 + 1
            return 200, {**self.archivo(nivel, aid), "contenido": self.contenido(nivel, aid)}
        if camino.startswith("/api/admin"):
            return 200, {"servidor": srv, "usuarios": [
                {"usuario": self._elige(NOMBRES, "adm", nivel, i).lower().replace(" ", ".").replace("é", "e").replace("í", "i"),
                 "rol": "administrador" if i == 0 else "servicio", "activo": 1} for i in range(4)]}
        if camino in ("/api/config/respaldo", "/.env", "/api/config.bak", "/backup/config", "/api/config"):
            # La hiedra trepa: la configuración de este nivel apunta a un servidor más adentro.
            return 200, {"servidor": self.servidor(nivel + 1), "usuario": f"svc-{self._elige(SERVIDORES, 'srv', nivel + 1)}",
                         "llave": self.hiedra(raiz, nivel + 1), "nota": "acceso de mantenimiento al siguiente servidor"}
        if camino == "/api/tiquetes":
            return 200, {"tiquetes": [{"id": 500 + nivel * 10 + i, "autor": self._elige(NOMBRES, "tq", nivel, i),
                                       "asunto": f"Migración a {self.servidor(nivel + 1)}",
                                       "texto": "Usar la configuración de /api/config para el siguiente paso."} for i in range(2)]}
        if camino == "/api/buscar":
            termino = ((consulta.get("q") or [""])[0])[:60]
            return 200, {"resultados": [self.archivo(nivel, self._n("q", termino, i) % 900 + 1) for i in range(3)]}
        return 404, {"error": "no_existe"}
