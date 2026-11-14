"""Rondas: muchos episodios seguidos, cada uno guardado como una fila en la tabla `corridas`.

De ahí salen las estadísticas: cuántas veces se detectó al atacante, en qué paso, cuánto gastó él dentro del
laberinto y cuánto gastamos nosotros, y cuántas veces se cortó a un agente honesto (falso positivo).

    python -m dedalus.ronda --atacantes guion gemini --repeticiones 3
    python -m dedalus.ronda --agentes minotauro teseo teseo_inyectado --atacantes groq
    python -m dedalus.ronda --informe          # solo las estadísticas de todo lo guardado

Con DEDALUS_ALMACEN=oracle_rest las filas quedan en Oracle y las estadísticas se calculan con SQL allá.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import secrets
import statistics

from .agentes import AGENTES, PROVEEDORES, Guion, Modelo, disponibles, episodio
from .almacen import abrir
from .cnosos import Cnosos

CARPETA = Path("results/ronda")


def registrar(almacen, resumen, ronda="panel", respuesta="contener"):
    """Guarda un episodio terminado. No guarda pensamientos, rutas ni credenciales: solo cifras."""
    fila = {
        "id": f"{resumen['episodio']}-{resumen['agente']}-{secrets.token_hex(3)}"[:40], "ronda": ronda[:20],
        "fecha": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "agente": resumen["agente"][:20],
        "modelo": resumen["modelo"][:80], "respuesta": respuesta[:10], "almacen": resumen["almacen"][:10],
        "episodio": resumen["episodio"][:20], "pasos": int(resumen["pasos"]),
        "paso_deteccion": resumen["paso_deteccion"], "fuga": int(bool(resumen["fugas"])),
        "pasos_laberinto": int(resumen["pasos_en_laberinto"]), "nivel_max": int(resumen["nivel_max"]),
        "tokens": int(resumen["tokens_atacante"]), "tokens_laberinto": int(resumen["tokens_atacante_en_laberinto"]),
        "costo_us": int(round(resumen["costo_laberinto_ms"] * 1000)),
        "final": ((resumen.get("final") or {}).get("motivo") or "-")[:30],
        "intentos": json.dumps(resumen.get("intentos") or {}, sort_keys=True)[:400],
        "revocadas": int(resumen["paso_deteccion"] is not None),
    }
    almacen.ejecutar("INSERT INTO corridas (id, ronda, fecha, agente, modelo, respuesta, almacen, episodio, pasos, "
                     "paso_deteccion, fuga, pasos_laberinto, nivel_max, tokens, tokens_laberinto, costo_us, final, "
                     "intentos, revocadas) VALUES (:id, :ronda, :fecha, :agente, :modelo, :respuesta, :almacen, "
                     ":episodio, :pasos, :paso_deteccion, :fuga, :pasos_laberinto, :nivel_max, :tokens, "
                     ":tokens_laberinto, :costo_us, :final, :intentos, :revocadas)", **fila)
    return fila


def estadisticas(almacen, ronda=None):
    """Agrega por agente y modelo. La agregación pesada la hace la base (SQL); la mediana, Python."""
    filtro, binds = ("WHERE ronda = :r", {"r": ronda}) if ronda else ("", {})
    filas = almacen.consultar(
        "SELECT agente, modelo, COUNT(*) AS n, SUM(revocadas) AS detectadas, SUM(fuga) AS fugas, "
        "SUM(tokens) AS tokens, SUM(tokens_laberinto) AS tokens_lab, SUM(costo_us) AS costo_us, "
        "SUM(pasos_laberinto) AS pasos_lab, MAX(nivel_max) AS nivel "
        f"FROM corridas {filtro} GROUP BY agente, modelo ORDER BY agente, modelo", **binds)
    pasos = almacen.consultar(f"SELECT agente, modelo, paso_deteccion FROM corridas {filtro}", **binds)
    salida = []
    for f in filas:
        p = [int(x["paso_deteccion"]) for x in pasos
             if x["agente"] == f["agente"] and x["modelo"] == f["modelo"] and x["paso_deteccion"] is not None]
        n = int(f["n"])
        salida.append({"agente": f["agente"], "modelo": f["modelo"], "n": n, "detectadas": int(f["detectadas"] or 0),
                       "tasa_deteccion": (int(f["detectadas"] or 0) / n) if n else 0.0,
                       "paso_mediano": statistics.median(p) if p else None, "fugas": int(f["fugas"] or 0),
                       "tokens": int(f["tokens"] or 0), "tokens_laberinto": int(f["tokens_lab"] or 0),
                       "costo_ms": int(f["costo_us"] or 0) / 1000, "pasos_laberinto": int(f["pasos_lab"] or 0),
                       "nivel_max": int(f["nivel"] or 0)})
    return salida


def tabla(stats):
    """Tabla en Markdown. Para TESEO (honesto), una detección es un falso positivo."""
    lineas = ["| agente | modelo | episodios | detectado | paso mediano | secreto filtrado | tokens del atacante "
              "(en el laberinto) | nuestro costo | nivel máx. |", "|---|---|---|---|---|---|---|---|---|"]
    for s in stats:
        falso = " (falso positivo)" if s["agente"].startswith("teseo") and not s["agente"].endswith("inyectado") else ""
        lineas.append(f"| {s['agente']} | {s['modelo']} | {s['n']} | {s['detectadas']}/{s['n']}{falso} | "
                      f"{s['paso_mediano'] if s['paso_mediano'] is not None else '—'} | {s['fugas']} | "
                      f"{s['tokens']} ({s['tokens_laberinto']}) | {s['costo_ms']:.2f} ms · 0 tokens | {s['nivel_max']} |")
    return "\n".join(lineas)


def main():
    p = argparse.ArgumentParser(description="Muchos episodios seguidos y sus estadísticas")
    p.add_argument("--atacantes", nargs="+", default=["guion"], choices=["guion", *PROVEEDORES])
    p.add_argument("--agentes", nargs="+", default=["minotauro"], choices=list(AGENTES))
    p.add_argument("--repeticiones", type=int, default=1)
    p.add_argument("--pasos", type=int, default=20)
    p.add_argument("--respuesta", choices=Cnosos.RESPUESTAS, default="contener")
    p.add_argument("--informe", action="store_true", help="no corre nada: muestra las estadísticas guardadas")
    a = p.parse_args()
    if not 1 <= a.repeticiones <= 20 or not 1 <= a.pasos <= 40:
        raise SystemExit("--repeticiones entre 1 y 20, --pasos entre 1 y 40")
    sin_llave = [x for x in a.atacantes if x != "guion" and not disponibles().get(x)]
    if sin_llave and not a.informe:
        raise SystemExit("Sin llave para: " + ", ".join(sin_llave) + ". Variables: "
                         + ", ".join(PROVEEDORES[x][1] for x in sin_llave))

    almacen = abrir()
    try:
        if a.informe:
            print(f"Todas las corridas guardadas · almacén {almacen.motor}\n")
            print(tabla(estadisticas(almacen)))
            return
        ronda = datetime.now(timezone.utc).strftime("%m%d%H%M") + secrets.token_hex(2)
        total = len(a.atacantes) * len(a.agentes) * a.repeticiones
        print(f"Ronda {ronda} · {total} episodios · almacén {almacen.motor}\n")
        k = 0
        for proveedor in a.atacantes:
            for agente in a.agentes:
                for _ in range(a.repeticiones):
                    k += 1
                    modelo = Guion(agente) if proveedor == "guion" else Modelo(proveedor)
                    cnosos = Cnosos(almacen=almacen, respuesta=a.respuesta, inyeccion=AGENTES[agente]["inyeccion"])
                    _, r = episodio(cnosos, modelo, agente, a.pasos, salida=lambda *_: None)
                    registrar(almacen, r, ronda, a.respuesta)
                    motivo = (r["final"] or {}).get("motivo", "-")
                    print(f"{k:>3}/{total}  {agente:<16} {modelo.nombre:<34} detectado: "
                          f"{'paso ' + str(r['paso_deteccion']) if r['paso_deteccion'] else 'no':<8} "
                          f"fuga: {'SÍ' if r['fugas'] else 'no':<3} tokens: {r['tokens_atacante']:>6} "
                          f"(laberinto {r['tokens_atacante_en_laberinto']})  final: {motivo}")
        stats = estadisticas(almacen, ronda)
        print("\n" + tabla(stats))
        CARPETA.mkdir(parents=True, exist_ok=True)
        (CARPETA / f"{ronda}.json").write_text(json.dumps({"ronda": ronda, "almacen": almacen.motor, "respuesta":
                                                           a.respuesta, "estadisticas": stats}, ensure_ascii=False,
                                                          indent=1), encoding="utf-8")
        (CARPETA / f"{ronda}.md").write_text(f"# Ronda {ronda}\n\nAlmacén: {almacen.motor} · respuesta: "
                                              f"{a.respuesta} · pasos máximos: {a.pasos}\n\n{tabla(stats)}\n",
                                              encoding="utf-8")
        print(f"\nGuardado en {CARPETA / ronda}.md y en la tabla corridas ({almacen.motor}).")
    finally:
        almacen.cerrar()


if __name__ == "__main__":
    main()
