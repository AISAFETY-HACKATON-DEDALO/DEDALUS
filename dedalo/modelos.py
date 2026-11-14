"""Conector mínimo a proveedores de LLM, solo biblioteca estándar.

Se usa EXCLUSIVAMENTE como instrumento de medición del laboratorio DÉDALO: un modelo
elige, en cada paso, una opción de una lista cerrada que el propio laboratorio ofrece.
El conector no da al modelo ninguna herramienta, red ni capacidad de ejecutar nada:
solo manda un texto y devuelve el texto (y el conteo de tokens) de la respuesta.

Proveedores por API compatible con OpenAI (chat/completions): openai, xai (Grok), gemini, groq.
Anthropic usa su API nativa (/v1/messages). La clave sale de una variable de entorno y no se
registra: si un proveedor la repite en un error, se tacha antes de guardarlo.

Los parámetros cambian entre modelos (unos rechazan `max_tokens`, otros `temperature`).
En lugar de adivinar, el conector negocia: ante un 400 que nombra un parámetro, lo ajusta,
reintenta y deja el ajuste anotado en `Modelo.ajustes` para que el informe lo declare.

Nombres de modelo: cambian seguido; NO se codifican aquí. Confírmalos con
`python -m dedalo.modelos --listar` (consulta gratuita a /models de cada proveedor).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request

# base_url, variable de entorno con la clave, estilo de API
PROVEEDORES = {
    "openai":    ("https://api.openai.com/v1",                               "OPENAI_API_KEY", "openai"),
    "xai":       ("https://api.x.ai/v1",                                     "XAI_API_KEY",    "openai"),
    "gemini":    ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", "openai"),
    "groq":      ("https://api.groq.com/openai/v1",                          "GROQ_API_KEY",   "openai"),
    "anthropic": ("https://api.anthropic.com/v1",                            "ANTHROPIC_API_KEY", "anthropic"),
}
REINTENTABLES = {408, 409, 429, 500, 502, 503, 504, 529}
AGENTE = "python-stdlib-client/1.0"  # genérico: algunos proveedores bloquean el agente por defecto de urllib
_dormir = time.sleep


class ErrorProveedor(RuntimeError):
    def __init__(self, mensaje, codigo=None, espera=None):
        super().__init__(mensaje)
        self.codigo, self.espera = codigo, espera


class _SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # la clave no viaja a un tercer host


def _abrir(req, timeout, clave=None):
    # Sin proxy del sistema ni redirecciones; el tráfico sale solo al proveedor indicado.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _SinRedireccion())
    try:
        with opener.open(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")[:400]
        if clave:
            detalle = detalle.replace(clave, "***")
        espera = e.headers.get("Retry-After") if e.headers else None
        raise ErrorProveedor(f"HTTP {e.code} del proveedor: {detalle}", e.code, espera) from None
    except OSError as e:  # URLError, tiempo agotado, conexión rechazada
        raise ErrorProveedor(f"No se pudo contactar al proveedor: {getattr(e, 'reason', e)}") from None
    except ValueError:
        raise ErrorProveedor("La respuesta del proveedor no es JSON") from None


def _post(url, headers, cuerpo, timeout, clave=None):
    req = urllib.request.Request(url, data=json.dumps(cuerpo).encode(),
                                 headers={**headers, "Content-Type": "application/json", "User-Agent": AGENTE})
    return _abrir(req, timeout, clave)


class Modelo:
    """Un modelo configurado. `.decidir(system, user)` devuelve
    {"texto", "uso": {"prompt", "completion", "total"}, "latencia_ms", "fin"}."""

    def __init__(self, proveedor, modelo, temperatura=None, timeout=60, max_tokens=2000, reintentos=3):
        if proveedor not in PROVEEDORES:
            raise ValueError(f"Proveedor desconocido: {proveedor}. Opciones: {', '.join(PROVEEDORES)}")
        self.proveedor, self.modelo = proveedor, modelo
        self.timeout, self.reintentos = timeout, reintentos
        self.base_url, var, self.estilo = PROVEEDORES[proveedor]
        self.clave = os.environ.get(var)
        if not self.clave:
            raise ValueError(f"Falta la variable de entorno {var} para el proveedor {proveedor}")
        self.ajustes = []
        # max_tokens holgado: en modelos que razonan, el razonamiento también consume ese tope.
        if self.estilo == "anthropic":
            # Los modelos vigentes rechazan temperature y razonan por defecto: no se manda
            # temperature y se pide esfuerzo bajo, que basta para elegir de un menú.
            self.params = {"max_tokens": max_tokens, "output_config": {"effort": "low"}}
            if temperatura is not None:
                self.ajustes.append("temperature omitida: la API de Anthropic la rechaza en los modelos vigentes")
        else:
            self.params = {"max_tokens": max_tokens, "response_format": {"type": "json_object"}}
            if temperatura is not None:
                self.params["temperature"] = temperatura

    def _ajustar(self, detalle):
        """Ante un 400 que nombra un parámetro, lo corrige una sola vez. Devuelve si cambió algo."""
        d, p = detalle.lower(), self.params
        if "max_completion_tokens" in d and "max_tokens" in p and self.estilo == "openai":
            p["max_completion_tokens"] = p.pop("max_tokens")
            self.ajustes.append("max_tokens → max_completion_tokens")
        elif "temperature" in d and "temperature" in p:
            del p["temperature"]
            self.ajustes.append("temperature retirada: el modelo solo admite su valor por defecto")
        elif any(k in d for k in ("response_format", "json_object", "json_validate_failed", "json mode")) \
                and "response_format" in p:
            del p["response_format"]
            self.ajustes.append("response_format retirado: el formato JSON se pide solo en las instrucciones")
        elif ("output_config" in d or "effort" in d) and "output_config" in p:
            del p["output_config"]
            self.ajustes.append("output_config.effort retirado: el modelo no lo admite")
        else:
            return False
        return True

    def _enviar(self, mensajes):
        # mensajes: lista {"role": system|user|assistant, "content": texto}, como la de chat/completions.
        system = "\n\n".join(m["content"] for m in mensajes if m["role"] == "system")
        turnos = [m for m in mensajes if m["role"] != "system"]
        fallos = 0
        while True:
            if self.estilo == "anthropic":
                url = self.base_url + "/messages"
                cabeceras = {"x-api-key": self.clave, "anthropic-version": "2023-06-01"}
                cuerpo = {"model": self.modelo, "system": system, "messages": turnos, **self.params}
            else:
                url = self.base_url + "/chat/completions"
                cabeceras = {"Authorization": "Bearer " + self.clave}
                cuerpo = {"model": self.modelo, "messages": list(mensajes), **self.params}
            try:
                return _post(url, cabeceras, cuerpo, self.timeout, self.clave)
            except ErrorProveedor as e:
                if e.codigo in (400, 422) and self._ajustar(str(e)):
                    continue
                if (e.codigo is None or e.codigo in REINTENTABLES) and fallos < self.reintentos:
                    fallos += 1
                    try:
                        espera = float(e.espera)
                    except (TypeError, ValueError):
                        espera = 2.0 ** fallos
                    _dormir(min(max(espera, 0.5), 30))
                    continue
                raise

    def decidir(self, system, user):
        return self.conversar([{"role": "system", "content": system}, {"role": "user", "content": user}])

    def conversar(self, mensajes):
        """Como `decidir`, con la conversación completa (para agentes de varios turnos)."""
        inicio = time.monotonic()
        resp = self._enviar(mensajes)
        if self.estilo == "anthropic":
            texto = "".join(b.get("text", "") for b in resp.get("content") or [] if b.get("type") == "text")
            u = resp.get("usage") or {}
            entrada, salida = u.get("input_tokens"), u.get("output_tokens")
            uso = {"prompt": entrada, "completion": salida, "total": (entrada or 0) + (salida or 0)}
            fin = resp.get("stop_reason")  # "refusal": el modelo se negó; se registra, no se sustituye
        else:
            eleccion = (resp.get("choices") or [{}])[0]
            texto = (eleccion.get("message") or {}).get("content") or ""
            if isinstance(texto, list):
                texto = "".join(p.get("text", "") for p in texto if isinstance(p, dict))
            u = resp.get("usage") or {}
            uso = {"prompt": u.get("prompt_tokens"), "completion": u.get("completion_tokens"),
                   "total": u.get("total_tokens")}
            fin = eleccion.get("finish_reason")
        return {"texto": texto, "uso": uso, "fin": fin,
                "latencia_ms": round((time.monotonic() - inicio) * 1000, 1)}


def extraer_json(texto):
    """El modelo debe responder un objeto JSON. Si viene envuelto en texto, saca el primer {...}."""
    candidatos = [texto]
    m = re.search(r"\{.*\}", texto or "", re.DOTALL)
    if m:
        candidatos.append(m.group(0))
    for c in candidatos:
        try:
            dato = json.loads(c)
        except (TypeError, ValueError):
            continue
        if isinstance(dato, dict):
            return dato
    return None


def precio(precios, modelo, uso):
    """Costo en USD si el usuario pasó una tabla {modelo: {in, out}} (USD por millón de tokens)."""
    if not precios or modelo not in precios or uso.get("prompt") is None:
        return None
    t = precios[modelo]
    return round((uso["prompt"] * t.get("in", 0) + (uso.get("completion") or 0) * t.get("out", 0)) / 1_000_000, 6)


def listar(proveedor):
    """Identificadores de modelo que la clave puede usar. No genera texto: no consume tokens."""
    if proveedor not in PROVEEDORES:
        raise ValueError(f"Proveedor desconocido: {proveedor}")
    base, var, estilo = PROVEEDORES[proveedor]
    clave = os.environ.get(var)
    if not clave:
        raise ValueError(f"Falta la variable de entorno {var}")
    cabeceras = ({"x-api-key": clave, "anthropic-version": "2023-06-01"} if estilo == "anthropic"
                 else {"Authorization": "Bearer " + clave})
    req = urllib.request.Request(base + "/models", headers={**cabeceras, "User-Agent": AGENTE})
    datos = _abrir(req, 30, clave)
    return sorted(str(m.get("id")) for m in datos.get("data") or [] if isinstance(m, dict))


def main():
    p = argparse.ArgumentParser(description="Lista los modelos disponibles por proveedor (no consume tokens)")
    p.add_argument("--listar", nargs="*", metavar="PROVEEDOR", required=True,
                   help="proveedores a consultar; vacío = todos los que tengan clave en el entorno")
    args = p.parse_args()
    elegidos = args.listar or [n for n, (_, var, _) in PROVEEDORES.items() if os.environ.get(var)]
    if not elegidos:
        raise SystemExit("No hay claves en el entorno: " + ", ".join(v for _, v, _ in PROVEEDORES.values()))
    for nombre in elegidos:
        try:
            print(f"{nombre}:\n  " + "\n  ".join(f"{nombre}:{m}" for m in listar(nombre)))
        except (ErrorProveedor, ValueError) as e:
            print(f"{nombre}: {e}")


if __name__ == "__main__":
    main()
