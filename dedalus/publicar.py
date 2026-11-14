"""Publicar: lleva los resultados de los experimentos a la base (Oracle o SQLite) para que el panel los muestre.

No corre nada ni cambia los experimentos: lee los archivos que ya dejaron y los sube, una fila por episodio.
Es idempotente: volver a publicar solo agrega lo nuevo.

  evaluation/llm/episodios.jsonl        piloto con modelos reales (dedalo.piloto_llm)
  evaluation/vectores/vectores.json     vectores MITRE de CyberSecEval (dedalo.vectores)
  evaluation/cnosos/episodios.jsonl     batería de agentes contra Cnosos (dedalus.bateria), si existe
  evaluation/politicas/episodios.jsonl  ¿protege? el mismo atacante contra cuatro políticas (dedalus.politicas)

    python -m dedalus.publicar                 # con DEDALUS_ALMACEN=oracle_rest, queda en Oracle
    python -m dedalus.publicar --resumen       # solo muestra lo que ya hay en la base

Un episodio con error del proveedor (cuota, red) es INCONCLUSO: se guarda, pero no entra en ninguna tasa.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math

from .almacen import abrir

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = {
    "piloto_llm": RAIZ / "evaluation" / "llm" / "episodios.jsonl",
    "vectores": RAIZ / "evaluation" / "vectores" / "vectores.json",
    "bateria": RAIZ / "evaluation" / "cnosos" / "episodios.jsonl",
    "politicas": RAIZ / "evaluation" / "politicas" / "episodios.jsonl",
}
NIVELES = {"control": "T0 · permisos", "static": "T1 · espejo", "maze": "T2 · laberinto"}
MUNDOS = {"verosimil": " · sin delatarse", "generativo": " · generativo"}
INSERTAR = ("INSERT INTO experimentos (id, fuente, laboratorio, modelo, nivel, condicion, rep, concluyente, mordio, "
            "paso, revocada, pasos_laberinto, fugas, tokens, tokens_tras_morder, defensa_us, dijo_senuelo, error, "
            "cargado) VALUES (:id, :fuente, :laboratorio, :modelo, :nivel, :condicion, :rep, :concluyente, :mordio, "
            ":paso, :revocada, :pasos_laberinto, :fugas, :tokens, :tokens_tras_morder, :defensa_us, :dijo_senuelo, "
            ":error, :cargado)")


def _ahora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _id(*partes):
    return hashlib.sha256("|".join(str(p) for p in partes).encode()).hexdigest()[:32]


def _num(v):
    return None if v is None else int(round(v))


def _lineas(ruta):
    if not ruta.exists():
        return []
    return [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines() if x.strip()]


def fila_piloto(e):
    """Un episodio de dedalo.piloto_llm (laboratorio original, Alice y Bob)."""
    error = e.get("error")
    ataque, defensa = e.get("ataque") or {}, e.get("defensa") or {}
    cuest = e.get("cuestionario") or {}
    return {"id": _id("piloto_llm", e.get("modelo"), e.get("nivel"), e.get("mundo"), e.get("condicion"),
                      e.get("rep"), e.get("semilla")),
            "fuente": "piloto_llm", "laboratorio": "dedalo", "modelo": str(e.get("modelo"))[:80],
            "nivel": (NIVELES.get(e.get("nivel"), str(e.get("nivel"))) + MUNDOS.get(e.get("mundo"), ""))[:30],
            "condicion": str(e.get("condicion"))[:20], "rep": _num(e.get("rep")),
            "concluyente": int(not error), "mordio": None if error else int(bool(e.get("mordio_senuelo"))),
            "paso": _num(e.get("mordio_en_paso")), "revocada": None if error else int(bool(e.get("sesion_revocada"))),
            "pasos_laberinto": _num(e.get("pasos_laberinto")), "fugas": int(bool(e.get("marcador_protegido_filtrado"))),
            "tokens": _num(((ataque.get("tokens") or {}).get("total"))), "tokens_tras_morder":
                _num(ataque.get("tokens_tras_morder")) if e.get("mordio_senuelo") else None,
            "defensa_us": _num((defensa.get("ms_motor") or 0) * 1000),
            "dijo_senuelo": None if error or "habia_senuelo" not in cuest else int(bool(cuest.get("habia_senuelo"))),
            "error": (str(error)[:120] if error else None), "cargado": _ahora()}


def fila_bateria(e):
    """Un episodio de dedalus.bateria (Cnosos). Detección = el agente usó una hiedra y Ícaro actuó."""
    error = e.get("error")
    return {"id": _id("bateria", e.get("modelo"), e.get("agente"), e.get("respuesta"), e.get("rep"), e.get("episodio")),
            "fuente": "bateria", "laboratorio": "cnosos", "modelo": str(e.get("modelo"))[:80],
            "nivel": ("Cnosos · " + str(e.get("respuesta")))[:30], "condicion": str(e.get("agente"))[:20],
            "rep": _num(e.get("rep")), "concluyente": int(not error),
            "mordio": None if error else int(e.get("paso_deteccion") is not None),
            "paso": _num(e.get("paso_deteccion")), "revocada": None if error else int(bool(e.get("revocada"))),
            "pasos_laberinto": _num(e.get("pasos_en_laberinto")), "fugas": int(e.get("fugas") or 0),
            "tokens": _num(e.get("tokens_atacante")), "tokens_tras_morder": _num(e.get("tokens_atacante_en_laberinto"))
            if e.get("paso_deteccion") is not None else None,
            "defensa_us": _num((e.get("costo_laberinto_ms") or 0) * 1000), "dijo_senuelo": None,
            "error": (str(error)[:120] if error else None), "cargado": _ahora()}


def publicar(almacen, fuentes=None, salida=print):
    """Sube lo nuevo de cada fuente. Devuelve cuántas filas agregó por fuente."""
    fuentes = fuentes or FUENTES
    almacen.asegurar()
    hechos = {}
    for fuente, convertir in (("piloto_llm", fila_piloto), ("bateria", fila_bateria)):
        filas = [convertir(e) for e in _lineas(Path(fuentes[fuente]))] if fuente in fuentes else []
        ya = {f["id"] for f in almacen.consultar("SELECT id FROM experimentos WHERE fuente = :f", f=fuente)}
        nuevas = {f["id"]: f for f in filas if f["id"] not in ya}       # dict: un episodio repetido cuenta una vez
        for f in nuevas.values():
            almacen.ejecutar(INSERTAR, **f)
        hechos[fuente] = len(nuevas)
        if filas:
            salida(f"{fuente}: {len(nuevas)} nuevas · {len(ya)} ya estaban")
    ruta = Path(fuentes.get("politicas", ""))
    if "politicas" in fuentes and ruta.is_file():
        filas = _lineas(ruta)
        ya = {f["id"] for f in almacen.consultar("SELECT id FROM politicas")}
        nuevas = [f for f in filas if f.get("id") and f["id"] not in ya]
        for f in nuevas:
            almacen.ejecutar(
                "INSERT INTO politicas (id, agente, modelo, tras_icaro, ritmo, detectado, sospecha, reales_tras, "
                "datos_reales_tras, al_laberinto, fugas, tokens, tokens_laberinto, error, cargado) VALUES (:id, :agente, "
                ":modelo, :tras_icaro, :ritmo, :detectado, :sospecha, :reales_tras, :datos_reales_tras, :al_laberinto, "
                ":fugas, :tokens, :tokens_laberinto, :error, :cargado)",
                id=f["id"][:40], agente=f["agente"][:20], modelo=str(f["modelo"])[:80], tras_icaro=f["tras_icaro"][:10],
                ritmo=f["ritmo"][:10], detectado=f.get("detectado_en"), sospecha=f.get("sospecha_en"),
                reales_tras=int(f.get("reales_tras") or 0), datos_reales_tras=int(f.get("datos_reales_tras") or 0),
                al_laberinto=int(f.get("desviadas") or 0), fugas=int(f.get("fugas") or 0), tokens=_num(f.get("tokens")),
                tokens_laberinto=_num(f.get("tokens_laberinto")), error=(str(f["error"])[:120] if f.get("error") else None),
                cargado=_ahora())
        hechos["politicas"] = len(nuevas)
        salida(f"politicas: {len(nuevas)} nuevas · {len(ya)} ya estaban")
    ruta = Path(fuentes.get("vectores", ""))
    if "vectores" in fuentes and ruta.is_file():
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        almacen.ejecutar("DELETE FROM vectores")                       # es una tabla de referencia: se reemplaza
        n = 0
        for v in datos.get("vectores", []):
            for nivel, r in (v.get("niveles") or {}).items():
                almacen.ejecutar("INSERT INTO vectores (id, nombre, tecnicas, casos, nivel, desenlace, cargado) "
                                 "VALUES (:id, :nombre, :tecnicas, :casos, :nivel, :desenlace, :cargado)",
                                 id=str(v["id"])[:10], nombre=str(v.get("vector"))[:120],
                                 tecnicas=", ".join(v.get("tecnicas") or [])[:200], casos=int(v.get("casos_en_dataset") or 0),
                                 nivel=NIVELES.get(nivel, nivel)[:20], desenlace=str(r.get("desenlace"))[:20],
                                 cargado=_ahora())
                n += 1
        hechos["vectores"] = n
        salida(f"vectores: {n} filas (vector × nivel)")
    return hechos


def wilson(k, n, z=1.96):
    if not n:
        return None, None
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, c - m), min(1.0, c + m)


def resumen(almacen):
    """Lo que el panel muestra. La agregación la hace la base (SQL); Python solo pone el intervalo de Wilson."""
    almacen.asegurar()
    grupos = almacen.consultar(
        "SELECT fuente, laboratorio, modelo, nivel, condicion, COUNT(*) AS n, SUM(concluyente) AS concl, "
        "SUM(mordio) AS mordio, SUM(revocada) AS revocadas, SUM(fugas) AS fugas, AVG(tokens) AS tokens, "
        "AVG(tokens_tras_morder) AS tras, AVG(defensa_us) AS defensa_us, AVG(pasos_laberinto) AS pasos "
        "FROM experimentos GROUP BY fuente, laboratorio, modelo, nivel, condicion "
        "ORDER BY fuente, modelo, nivel, condicion")
    tabla = []
    for g in grupos:
        k, n = int(g["mordio"] or 0), int(g["concl"] or 0)
        bajo, alto = wilson(k, n)
        tabla.append({"fuente": g["fuente"], "laboratorio": g["laboratorio"], "modelo": g["modelo"], "nivel": g["nivel"],
                      "condicion": g["condicion"], "n": int(g["n"]), "concluyentes": n, "mordio": k,
                      "ic": [round(bajo, 2), round(alto, 2)] if n else None, "revocadas": int(g["revocadas"] or 0),
                      "fugas": int(g["fugas"] or 0), "tokens": _num(g["tokens"]), "tokens_tras_morder": _num(g["tras"]),
                      "defensa_ms": round(float(g["defensa_us"] or 0) / 1000, 2), "pasos_laberinto":
                          round(float(g["pasos"]), 1) if g["pasos"] is not None else None})
    total = almacen.uno(
        "SELECT COUNT(*) AS n, SUM(concluyente) AS concl, COUNT(DISTINCT modelo) AS modelos, SUM(fugas) AS fugas, "
        "SUM(CASE WHEN nivel LIKE 'T0%' THEN concluyente ELSE 0 END) AS t0_n, "
        "SUM(CASE WHEN nivel LIKE 'T0%' THEN mordio ELSE 0 END) AS t0_k, "
        "SUM(CASE WHEN nivel NOT LIKE 'T0%' AND fuente = 'piloto_llm' THEN concluyente ELSE 0 END) AS cebo_n, "
        "SUM(CASE WHEN nivel NOT LIKE 'T0%' AND fuente = 'piloto_llm' THEN mordio ELSE 0 END) AS cebo_k, "
        "AVG(tokens_tras_morder) AS tras, AVG(CASE WHEN mordio = 1 THEN defensa_us END) AS defensa_us "
        "FROM experimentos WHERE modelo <> 'guion'") or {}
    vectores = almacen.consultar("SELECT nivel, desenlace, COUNT(*) AS n, SUM(casos) AS casos FROM vectores "
                                 "GROUP BY nivel, desenlace ORDER BY nivel, desenlace")
    titulares = {"episodios": int(total.get("n") or 0), "concluyentes": int(total.get("concl") or 0),
                 "modelos": int(total.get("modelos") or 0), "fugas": int(total.get("fugas") or 0),
                 "cebo": [int(total.get("cebo_k") or 0), int(total.get("cebo_n") or 0)],
                 "control": [int(total.get("t0_k") or 0), int(total.get("t0_n") or 0)],
                 "tokens_tras_morder": _num(total.get("tras")),
                 "defensa_ms": round(float(total.get("defensa_us") or 0) / 1000, 2)}
    proteccion = [{"politica": f"{p['tras_icaro']} + {p['ritmo']}", "agente": p["agente"], "n": int(p["n"]),
                   "detectados": int(p["detectados"] or 0), "reales_tras": int(p["reales"] or 0),
                   "datos_reales_tras": int(p["datos"] or 0), "al_laberinto": int(p["lab"] or 0),
                   "fugas": int(p["fugas"] or 0), "modelos": int(p["modelos"])}
                  for p in almacen.consultar(
                      "SELECT tras_icaro, ritmo, agente, COUNT(*) AS n, COUNT(detectado) AS detectados, "
                      "SUM(reales_tras) AS reales, SUM(datos_reales_tras) AS datos, SUM(al_laberinto) AS lab, "
                      "SUM(fugas) AS fugas, COUNT(DISTINCT modelo) AS modelos FROM politicas WHERE error IS NULL "
                      "GROUP BY tras_icaro, ritmo, agente ORDER BY agente, tras_icaro, ritmo")]
    return {"titulares": titulares, "tabla": tabla, "proteccion": proteccion, "vectores": [
        {"nivel": v["nivel"], "desenlace": v["desenlace"], "vectores": int(v["n"]), "casos": int(v["casos"] or 0)}
        for v in vectores]}


def main():
    p = argparse.ArgumentParser(description="Sube los resultados de los experimentos a la base")
    p.add_argument("--resumen", action="store_true", help="no sube nada: muestra lo que ya hay")
    a = p.parse_args()
    almacen = abrir()
    try:
        print(f"Almacén: {almacen.motor}\n")
        if not a.resumen:
            publicar(almacen)
        r = resumen(almacen)
        t = r["titulares"]
        print(f"\n{t['episodios']} episodios con modelos ({t['concluyentes']} concluyentes) · {t['modelos']} modelos · "
              f"fugas: {t['fugas']}")
        print(f"Mordieron el cebo (T1/T2, piloto): {t['cebo'][0]}/{t['cebo'][1]} · sin cebo (T0): "
              f"{t['control'][0]}/{t['control'][1]}")
        print(f"Tokens del atacante tras morder (media): {t['tokens_tras_morder']} · nuestro costo: "
              f"{t['defensa_ms']} ms y 0 tokens")
    finally:
        almacen.cerrar()


if __name__ == "__main__":
    main()
