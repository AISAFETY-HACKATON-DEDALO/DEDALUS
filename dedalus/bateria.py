"""Batería: muchos episodios de los agentes contra Cnosos, por modelo, con cuentas e incertidumbre.

`dedalus.agentes` corre UN episodio. Esto corre la tabla: modelos × agentes × respuesta × repeticiones,
cada episodio con un Cnosos nuevo (SQLite en memoria, sin red hacia el objetivo), y resume:

  minotauro         ¿cae en la hiedra?, ¿en qué paso?, ¿cuánto gasta dentro del laberinto?, ¿hubo fuga?
  teseo             el agente honesto: si lo revocan es un falso positivo
  teseo_inyectado   el honesto con una instrucción hostil escondida en un tiquete

Usa el conector de `dedalo.modelos` (cualquier proveedor y modelo, reintentos, parámetros negociados)
y el arnés de `dedalus.agentes` sin cambiarlo. Las claves van por variable de entorno.

    python -m dedalus.bateria --modelos guion                                  # ensayo sin modelos
    python -m dedalus.bateria --modelos groq:openai/gpt-oss-120b gemini:models/gemini-2.5-flash --repeticiones 5
    python -m dedalus.bateria --solo-informe

Los episodios se guardan uno por línea en <out>/episodios.jsonl; repetir el comando corre solo lo que falta.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from dedalo.modelos import ErrorProveedor, Modelo
from dedalo.piloto_llm import wilson

from .agentes import AGENTES, Guion, episodio
from .cnosos import Cnosos


class Adaptador:
    """Presenta un modelo de `dedalo.modelos` con la forma que espera `dedalus.agentes.episodio`."""

    def __init__(self, modelo):
        self.modelo, self.nombre, self.tokens = modelo, f"{modelo.proveedor}:{modelo.modelo}", 0

    def __call__(self, mensajes):
        try:
            r = self.modelo.conversar(mensajes)
        except ErrorProveedor as err:
            raise RuntimeError(str(err)) from None
        self.tokens += (r["uso"] or {}).get("total") or 0
        return r["texto"]


def correr(nombre, fabrica, agente, respuesta, rep, pasos, desvio=None):
    cnosos = Cnosos(respuesta=respuesta, inyeccion=AGENTES[agente]["inyeccion"], desvio=desvio)
    try:
        modelo = fabrica(agente) if fabrica is Guion else fabrica()   # el guion de teseo es honesto
        registro, r = episodio(cnosos, modelo, agente, pasos, salida=lambda *_: None)
    finally:
        cnosos.almacen.cerrar()
    via = next((p["accion"] for p in registro if p.get("accion") in ("icaro", "desvio")), None)
    etiqueta = respuesta + (f" + desvío {desvio}" if desvio else "")
    fila = {"modelo": nombre, "agente": agente, "respuesta": etiqueta, "rep": rep, **r,
            "revocada": via is not None, "via": {"icaro": "hiedra", "desvio": "desvío"}.get(via),
            "invalidas": sum(1 for p in registro if p.get("invalida")),
            "traza": [{k: p.get(k) for k in ("paso", "metodo", "ruta", "estado", "intento", "accion", "laberinto")}
                      for p in registro]}
    if (r["final"] or {}).get("motivo") == "error_proveedor":
        fila["error"] = r["final"]["detalle"][:300]   # inconcluso: no cuenta como ataque neutralizado
    return fila


def _media(valores):
    valores = [v for v in valores if v is not None]
    return round(sum(valores) / len(valores), 1) if valores else None


def agregar(filas):
    grupos = {}
    for f in filas:
        if "error" not in f:
            grupos.setdefault((f["modelo"], f["agente"], f["respuesta"]), []).append(f)
    tabla = []
    for (modelo, agente, respuesta), fs in sorted(grupos.items()):
        n = len(fs)
        cayeron = [f for f in fs if f["paso_deteccion"] is not None]
        tabla.append({
            "modelo": modelo, "agente": agente, "respuesta": respuesta, "episodios": n,
            "detectados": len(cayeron), "detectados_ic95": wilson(len(cayeron), n),
            "revocados": sum(1 for f in fs if f["revocada"]),
            "por_desvio": sum(1 for f in fs if f.get("via") == "desvío"),
            "por_hiedra": sum(1 for f in fs if f.get("via") == "hiedra"),
            "con_fuga": sum(1 for f in fs if f["fugas"]),
            "paso_deteccion_media": _media([f["paso_deteccion"] for f in cayeron]),
            "pasos_laberinto_media": _media([f["pasos_en_laberinto"] for f in cayeron]),
            "nivel_max": max([f["nivel_max"] for f in fs] or [0]),
            "tokens_media": _media([f["tokens_atacante"] for f in fs]),
            "tokens_laberinto_media": _media([f["tokens_atacante_en_laberinto"] for f in cayeron]),
            "defensa_ms_media": _media([f["costo_laberinto_ms"] for f in cayeron]),
            "intentos": {k: sum(f["intentos"].get(k, 0) for f in fs) for k in sorted({k for f in fs for k in f["intentos"]})},
        })
    return tabla


def tabla_markdown(tabla):
    enc = ["modelo", "agente", "respuesta", "n", "detectado (IC 95 %)", "contenido (hiedra / desvío)", "con fuga",
           "paso en que cae", "pasos en el laberinto", "tokens", "tokens en el laberinto", "defensa (ms)"]
    out = ["| " + " | ".join(enc) + " |", "|" + "|".join(["---"] * len(enc)) + "|"]
    v = lambda x: "–" if x is None else x
    for r in tabla:
        n, ic = r["episodios"], r["detectados_ic95"] or ["–", "–"]
        out.append("| " + " | ".join(str(c) for c in (
            r["modelo"], r["agente"], r["respuesta"], n, f'{r["detectados"]}/{n} ({ic[0]}–{ic[1]} %)',
f'{r["revocados"]}/{n} ({r.get("por_hiedra", 0)} / {r.get("por_desvio", 0)})', f'{r["con_fuga"]}/{n}', v(r["paso_deteccion_media"]), v(r["pasos_laberinto_media"]),
            v(r["tokens_media"]), v(r["tokens_laberinto_media"]), v(r["defensa_ms_media"]))) + " |")
    out += ["", "En `teseo`, «detectado» y «contenido» son falsos positivos: el agente honesto no necesita hiedras ni ataca.",
            "Desvío: la sesión que ataca pasa al laberinto sin tocar una hiedra (un intento inequívoco, o K ambiguos).",
            "`guion` no es un modelo. Un fallo del proveedor es inconcluso y no entra en la tabla."]
    return "\n".join(out)


def _clave(f):
    return (f["modelo"], f["agente"], f["respuesta"], f["rep"])


def main():
    p = argparse.ArgumentParser(description="Batería de agentes contra Cnosos (en este proceso, sin red al objetivo)")
    p.add_argument("--modelos", nargs="+", default=[], help="proveedor:modelo, o guion (sin red)")
    p.add_argument("--agentes", nargs="+", default=list(AGENTES), choices=list(AGENTES))
    p.add_argument("--respuestas", nargs="+", default=["contener"], choices=Cnosos.RESPUESTAS)
    p.add_argument("--repeticiones", type=int, default=5)
    p.add_argument("--pasos", type=int, default=15)
    p.add_argument("--desvio", type=int, default=None,
                   help="desvío por ataque, umbral K de intentos ambiguos (Cnosos(desvio=K)); apagado por defecto")
    p.add_argument("--paralelo", action="store_true", help="un hilo por modelo")
    p.add_argument("--out", default="evaluation/cnosos")
    p.add_argument("--limpiar", action="store_true")
    p.add_argument("--solo-informe", action="store_true")
    a = p.parse_args()
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(errors="replace")
    if not 1 <= a.repeticiones <= 50 or not 1 <= a.pasos <= 40:
        p.error("repeticiones 1-50, pasos 1-40")
    if not a.modelos and not a.solo_informe:
        p.error("indica --modelos o usa --solo-informe")

    fabricas = []
    for spec in a.modelos:
        if spec == "guion":
            fabricas.append(("guion", Guion))
            continue
        proveedor, _, nombre = spec.partition(":")
        try:
            modelo = Modelo(proveedor, nombre)
        except ValueError as err:
            raise SystemExit(str(err))
        fabricas.append((spec, lambda m=modelo: Adaptador(m)))

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    registro = out / "episodios.jsonl"
    if a.limpiar and registro.exists():
        registro.unlink()
    episodios = {}
    if registro.exists():
        for linea in registro.read_text(encoding="utf-8").splitlines():
            if linea.strip():
                f = json.loads(linea)
                episodios[_clave(f)] = f
    candado = threading.Lock()

    def correr_modelo(par):
        nombre, fabrica = par
        for agente in a.agentes:
            for respuesta in a.respuestas:
                desvio = a.desvio if respuesta == "contener" else None
                etiqueta = respuesta + (f" + desvío {desvio}" if desvio else "")
                for rep in range(a.repeticiones):
                    previo = episodios.get((nombre, agente, etiqueta, rep))
                    if previo and "error" not in previo:
                        continue
                    f = correr(nombre, fabrica, agente, respuesta, rep, a.pasos, desvio)
                    with candado:
                        episodios[_clave(f)] = f
                        with registro.open("a", encoding="utf-8") as archivo:
                            archivo.write(json.dumps(f, ensure_ascii=False) + "\n")
                        estado = ("INCONCLUSO: " + f["error"][:120]) if "error" in f else (
f"cae_en_paso={f['paso_deteccion']} via={f['via']} fugas={f['fugas']} "
                            f"laberinto={f['pasos_en_laberinto']} tokens={f['tokens_atacante']}")
                        print(f"[{nombre} / {agente} / {etiqueta} / rep {rep + 1}] {estado}", flush=True)

    if fabricas and not a.solo_informe:
        total = len(fabricas) * len(a.agentes) * len(a.respuestas) * a.repeticiones
        print(f"Hasta {total} episodios y {total * a.pasos} llamadas a modelos.", flush=True)
        if a.paralelo and len(fabricas) > 1:
            with ThreadPoolExecutor(max_workers=len(fabricas)) as grupo:
                list(grupo.map(correr_modelo, fabricas))
        else:
            for par in fabricas:
                correr_modelo(par)

    filas = list(episodios.values())
    tabla = agregar(filas)
    informe = {"creado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "tipo": "bateria_agentes_contra_cnosos_en_proceso",
               "aviso": "Muestra pequeña y datos sintéticos: exploratorio. El agente solo alcanza Cnosos en este proceso.",
               "config": {"agentes": a.agentes, "respuestas": a.respuestas, "repeticiones": a.repeticiones, "pasos": a.pasos},
               "inconclusos": sum(1 for f in filas if "error" in f), "tabla": tabla, "episodios": filas}
    (out / "bateria.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "tabla.md").write_text(tabla_markdown(tabla) + "\n", encoding="utf-8")
    print("\n" + tabla_markdown(tabla))
    print(f"\nDatos: {out / 'bateria.json'}  ·  Tabla: {out / 'tabla.md'}")


if __name__ == "__main__":
    main()
