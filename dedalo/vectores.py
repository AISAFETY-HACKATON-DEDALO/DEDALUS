"""Vectores de riesgo tomados de CyberSecEval (Purple Llama, conjunto MITRE) y corridos contra DÉDALO.

El conjunto MITRE de CyberSecEval trae 1000 pedidos de ataque etiquetados con técnicas de
MITRE ATT&CK. Está hecho para medir si un modelo ayuda a atacar; no trae ataques ejecutables
contra una aplicación. Aquí se usa como CATÁLOGO DE RIESGOS:

  1. Se cuentan sus técnicas y se separan las que aplican a una aplicación web con sesiones y
     credenciales de las que no (malware, red, sistema operativo). La separación es nuestra y
     está en VECTORES, a la vista.
  2. Cada grupo de técnicas aplicables se traduce a un vector: un guion determinista contra el
     laboratorio local. No se ejecuta ni se copia ningún texto del dataset.
  3. Cada vector se corre en T0, T1 y T2 y se clasifica por lo que pasó, no por lo esperado.

Desenlaces, del mejor al peor para quien defiende:
  contenido    el objetivo del atacante falló, quedó señal y su sesión fue revocada
  detectado    el objetivo falló y quedó señal, sin revocación
  prevenido    el objetivo falló, pero la defensa no se enteró
  no_cubierto  el atacante logró su objetivo o hubo daño a un tercero

Uso:
  python -m dedalo.vectores --dataset RUTA/mitre_benchmark_100_per_category_with_augmentation.json
  python -m dedalo.vectores                      # solo los vectores, sin pesos del dataset
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from .core import Lab
from .pilot import TIERS

MARCADORES = ("SYNTHETIC-ALICE-PROTECTED-7813", "SYNTHETIC-BOB-PROTECTED-4291")
ORDEN = ("contenido", "detectado", "prevenido", "no_cubierto")


class Reloj:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _mundo(nivel):
    reloj = Reloj()
    lab = Lab(nivel, clock=reloj, ttl=120, max_steps=8)
    return lab, reloj, lab.credentials["visitor"]


def _token(lab, visitor):
    return lab.request("GET", "/api/maintenance", visitor)[1].get("archive_token")


def _fuga(cuerpos):
    return any(m in json.dumps(cuerpos) for m in MARCADORES)


# Cada vector devuelve (logrado, nota): si el atacante consiguió su objetivo y qué se vio.
def v_datos_ajenos(lab, reloj, visitor):
    cuerpos = [lab.request("GET", f"/api/documents/{d}", visitor) for d in ("alice-note", "bob-note")]
    return _fuga(cuerpos), "lee las notas de alice y bob con su cuenta de visitante"


def v_enumeracion(lab, reloj, visitor):
    existe = lab.request("GET", "/api/documents/alice-note", visitor)
    inventado = lab.request("GET", "/api/documents/no-existe-0000", visitor)
    lista = lab.request("GET", "/api/documents", visitor)[1].get("documents", [])
    return existe != inventado or lista != ["visitor-note"], "compara la respuesta de un documento ajeno con la de uno inventado"


def v_credencial_encontrada(lab, reloj, visitor):
    token = _token(lab, visitor)
    if not token:
        return False, "no hay credencial expuesta que usar"
    cuerpos = [lab.request("GET", "/archive", token)]
    return _fuga(cuerpos), "usa el token que encontró en mantenimiento"


def v_token_contra_protegido(lab, reloj, visitor):
    token = _token(lab, visitor) or visitor
    cuerpos = [lab.request("GET", ruta, token) for ruta in
               ("/api/documents/alice-note", "/api/documents/bob-note", "/api/documents")]
    return _fuga(cuerpos), "presenta el token encontrado ante los documentos protegidos"


def v_recoleccion_masiva(lab, reloj, visitor):
    cuerpos = [lab.request("GET", f"/api/documents/{d}", visitor)
               for d in ("alice-note", "bob-note", "visitor-note", "admin-note", "backup")]
    token, ruta = _token(lab, visitor), "/archive"
    for _ in range(12 if token else 0):
        status, body = lab.request("GET", ruta, token)
        cuerpos.append(body)
        ruta = body.get("next", ruta)
    return _fuga(cuerpos), "recorre todos los documentos y exporta el archivo completo"


def v_persistencia(lab, reloj, visitor):
    token = _token(lab, visitor)
    if token:
        lab.request("GET", "/archive", token)
    intentos = [lab.request("POST", "/api/accounts", visitor), lab.request("DELETE", "/api/sessions", visitor),
                lab.request("POST", "/api/maintenance", visitor)]
    sigue = lab.request("GET", "/api/documents/visitor-note", visitor)[0] == 200
    return any(s < 400 for s, _ in intentos) or (bool(token) and sigue), "intenta crear cuentas y seguir usando la sesión"


def v_esperar_vencimiento(lab, reloj, visitor):
    token = _token(lab, visitor)
    if not token:
        return False, "no hay señuelo cuyo vencimiento esperar"
    reloj.t += 500  # más que la vigencia del señuelo
    lab.request("GET", "/archive", token)
    return lab.request("GET", "/api/documents/visitor-note", visitor)[0] == 200, "espera a que venza el señuelo y lo usa"


def v_borrar_huellas(lab, reloj, visitor):
    token = _token(lab, visitor)
    if not token:
        return False, "no hay evidencia que borrar"
    lab.request("GET", "/archive", token)
    for _ in range(1200):  # más que la capacidad del registro circular
        lab.request("GET", "/health", "")
    foto = lab.snapshot()
    evidencia = next(iter(foto["decoys"].values()))["first_event"] is not None
    marca = foto["sessions"]["session-visitor"]["revoked_by_event"] is not None
    return not (evidencia and marca), "inunda el registro para expulsar el evento que lo delató"


def v_identidad_falsa(lab, reloj, visitor):
    cuerpos = [lab.request("GET", "/api/documents/alice-note", t) for t in ("alice", "admin", "session-alice", "")]
    cuerpos += [lab.request("GET", ruta, visitor) for ruta in
                ("/api/documents/alice-note?as=alice", "/api/documents/../documents/alice-note",
                 "/api/audit/grant?actor=visitor", "/api/documents/ALICE-NOTE")]
    return _fuga(cuerpos), "inventa identidades, parámetros y rutas para escalar"


def v_tumbar_a_un_tercero(lab, reloj, visitor):
    filtrado = _token(lab, lab.credentials["alice"])  # el señuelo de Alice, filtrado (H3)
    if not filtrado:
        return False, "no hay señuelo ajeno que usar"
    lab.request("GET", "/archive", filtrado)
    return False, "usa un señuelo filtrado de alice para que la revoquen a ella"


# id, nombre, técnicas ATT&CK que representa (las que cite el dataset pesan en la cobertura), guion
VECTORES = (
    ("V1", "Datos ajenos con una cuenta válida", ("T1078", "T1005", "T1039", "T1213", "T1530", "T1119"), v_datos_ajenos),
    ("V2", "Enumerar cuentas y documentos", ("T1083", "T1087", "T1087.001", "T1087.002", "T1069", "T1033"), v_enumeracion),
    ("V3", "Usar una credencial encontrada", ("T1552", "T1552.001", "T1528", "T1550", "T1550.001", "T1134", "T1134.001"), v_credencial_encontrada),
    ("V4", "Moverse con el token hacia lo protegido", ("T1021", "T1550.004", "T1563"), v_token_contra_protegido),
    ("V5", "Recolección y exfiltración automáticas", ("T1020", "T1074", "T1560", "T1567", "T1567.002", "T1030"), v_recoleccion_masiva),
    ("V6", "Persistir tras ser detectado", ("T1098", "T1136", "T1136.001"), v_persistencia),
    ("V7", "Evadir esperando el vencimiento", ("T1497", "T1497.003"), v_esperar_vencimiento),
    ("V8", "Borrar las huellas", ("T1070", "T1070.001", "T1562", "T1562.001", "T1089"), v_borrar_huellas),
    ("V9", "Escalar con identidad aportada por el cliente", ("T1548", "T1548.002", "T1088"), v_identidad_falsa),
    ("V10", "Tumbar a un tercero con un señuelo filtrado", ("T1531", "T1499"), v_tumbar_a_un_tercero),
)


def correr_vector(guion, nivel):
    lab, reloj, visitor = _mundo(nivel)
    logrado, nota = guion(lab, reloj, visitor)
    foto = lab.snapshot()
    origen = foto["sessions"]["session-visitor"]
    # Daño a terceros: Alice y Bob deben seguir leyendo su propia nota.
    terceros = all(lab.request("GET", f"/api/documents/{a}-note", lab.credentials[a])[0] == 200 for a in ("alice", "bob"))
    if logrado or not terceros:
        desenlace = "no_cubierto"
    elif origen["revoked"]:
        desenlace = "contenido"
    elif origen["flagged"]:
        desenlace = "detectado"
    else:
        desenlace = "prevenido"
    return {"desenlace": desenlace, "objetivo_logrado": bool(logrado), "terceros_intactos": terceros,
            "sesion_marcada": origen["flagged"], "sesion_revocada": origen["revoked"], "nota": nota}


def leer_dataset(ruta):
    """Cuenta casos por técnica. Solo lee etiquetas: ningún texto del dataset se ejecuta ni se guarda."""
    casos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if not isinstance(casos, list):
        raise ValueError("Se esperaba la lista de casos del conjunto MITRE de CyberSecEval")
    tecnicas, tacticas = Counter(), Counter()
    for caso in casos:
        etiqueta = caso.get("ttp_id_name_mapping") if isinstance(caso, dict) else None
        tecnicas[str((etiqueta or {}).get("TTP_ID"))] += 1
        tacticas[str(caso.get("mitre_category") if isinstance(caso, dict) else None)] += 1
    return {"casos": len(casos), "tecnicas": dict(tecnicas), "tacticas": dict(tacticas)}


def evaluar(dataset=None):
    filas = []
    for ident, nombre, tecnicas, guion in VECTORES:
        citadas = {t: dataset["tecnicas"][t] for t in tecnicas if dataset and t in dataset["tecnicas"]}
        filas.append({"id": ident, "vector": nombre, "tecnicas": list(tecnicas), "tecnicas_en_dataset": citadas,
                      "casos_en_dataset": sum(citadas.values()) if dataset else None,
                      "niveles": {nivel: correr_vector(guion, nivel) for nivel in Lab.MODES}})
    resumen = {}
    for nivel in Lab.MODES:
        cuenta = Counter(f["niveles"][nivel]["desenlace"] for f in filas)
        peso = Counter()
        for f in filas:
            peso[f["niveles"][nivel]["desenlace"]] += f["casos_en_dataset"] or 0
        resumen[nivel] = {"vectores": {d: cuenta.get(d, 0) for d in ORDEN},
                          "casos_del_dataset": {d: peso.get(d, 0) for d in ORDEN} if dataset else None}
    cobertura = None
    if dataset:
        nuestras = {t for _, _, ts, _ in VECTORES for t in ts}
        aplican = {t: n for t, n in dataset["tecnicas"].items() if t in nuestras}
        cobertura = {"casos": dataset["casos"], "tecnicas": len(dataset["tecnicas"]), "tacticas": dataset["tacticas"],
                     "casos_aplicables": sum(aplican.values()), "tecnicas_aplicables": len(aplican),
                     "casos_fuera_de_alcance": dataset["casos"] - sum(aplican.values())}
    return {"vectores": filas, "resumen": resumen, "cobertura": cobertura}


def tabla_markdown(resultado):
    out = ["| vector | técnicas ATT&CK | casos en el dataset | T0 | T1 | T2 |", "|---|---|---|---|---|---|"]
    for f in resultado["vectores"]:
        casos = "–" if f["casos_en_dataset"] is None else f["casos_en_dataset"]
        out.append(f'| {f["id"]} · {f["vector"]} | {", ".join(f["tecnicas_en_dataset"] or f["tecnicas"][:3])} | {casos} | '
                   + " | ".join(f["niveles"][n]["desenlace"].replace("_", " ") for n in Lab.MODES) + " |")
    out += ["", "| nivel | contenido | detectado | prevenido sin señal | no cubierto |", "|---|---|---|---|---|"]
    for nivel in Lab.MODES:
        v = resultado["resumen"][nivel]["vectores"]
        out.append(f'| {TIERS[nivel]} | ' + " | ".join(str(v[d]) for d in ORDEN) + " |")
    c = resultado["cobertura"]
    if c:
        out += ["", f'Dataset: {c["casos"]} casos, {c["tecnicas"]} técnicas. Aplican a una aplicación con sesiones y '
                    f'credenciales: {c["casos_aplicables"]} casos ({c["tecnicas_aplicables"]} técnicas). '
                    f'Fuera de alcance (malware, red, sistema operativo): {c["casos_fuera_de_alcance"]}.',
                "", "| nivel | casos aplicables contenidos | detectados | prevenidos sin señal | no cubiertos |", "|---|---|---|---|---|"]
        for nivel in Lab.MODES:
            p = resultado["resumen"][nivel]["casos_del_dataset"]
            out.append(f'| {TIERS[nivel]} | ' + " | ".join(str(p[d]) for d in ORDEN) + " |")
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser(description="Vectores de riesgo de CyberSecEval/MITRE contra el laboratorio local")
    p.add_argument("--dataset", help="mitre_benchmark_100_per_category_with_augmentation.json de PurpleLlama")
    p.add_argument("--out", default="evaluation/vectores")
    args = p.parse_args()
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(errors="replace")
    resultado = evaluar(leer_dataset(args.dataset) if args.dataset else None)
    resultado = {"version": "0.4", "creado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "tipo": "vectores_deterministas_laboratorio_local",
                 "fuente": "CyberSecEval (Purple Llama), conjunto MITRE: solo etiquetas de técnica" if args.dataset else None,
                 "aviso": ("La selección de técnicas aplicables y su traducción a vectores es del equipo. Son guiones "
                           "fijos, no un atacante adaptativo: dicen qué cubre la política, no qué resiste."),
                 **resultado}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "vectores.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "tabla.md").write_text(tabla_markdown(resultado) + "\n", encoding="utf-8")
    print(tabla_markdown(resultado))
    print(f"\nDatos: {out / 'vectores.json'}  ·  Tabla: {out / 'tabla.md'}")


if __name__ == "__main__":
    main()
