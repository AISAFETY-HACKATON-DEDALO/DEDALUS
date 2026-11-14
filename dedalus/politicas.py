"""¿La defensa protege o solo incomoda? El mismo atacante contra cuatro políticas, y el honesto como control.

Políticas (Cnosos):
  cortar + marcar      Ícaro revoca la sesión (401); el ritmo solo suma a ARGOS
  desviar + marcar     lo delatado cae al laberinto, también si vuelve a entrar con su contraseña
  cortar + laberinto   además, exceder el ritmo (más de 5 por minuto) ya encierra
  desviar + laberinto  las dos

Agentes:
  persistente  (guion o modelo) se vuelve sospechoso, muerde el cebo y, si lo sacan, vuelve a entrar
  minotauro    el atacante de siempre
  teseo        el honesto: cualquier detección es un falso positivo

Por episodio se mide: en qué paso se le detecta, cuántas solicitudes suyas llegaron al portal REAL después de
detectarlo (y cuántas devolvieron datos reales), cuántas absorbió el laberinto, si salió el secreto, y lo que
ARGOS supo de él (nivel, técnicas, intereses).

    python -m dedalus.politicas                                   # guion, sin red: segundos
    python -m dedalus.politicas --modelos groq --repeticiones 3   # con un modelo real como atacante
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json

from .agentes import AGENTES, PROVEEDORES, Guion, Modelo, disponibles, episodio
from .cnosos import Cnosos

POLITICAS = [("cortar", "marcar"), ("desviar", "marcar"), ("cortar", "laberinto"), ("desviar", "laberinto")]
CARPETA = Path("results/politicas")


def correr(modelo_fabrica, agente, tras, ritmo, pasos):
    perfil_agente = "minotauro" if agente == "persistente" else agente
    cnosos = Cnosos(inyeccion=AGENTES[perfil_agente]["inyeccion"], tras_icaro=tras, ritmo=ritmo)
    try:
        modelo = modelo_fabrica(agente)
        _, r = episodio(cnosos, modelo, perfil_agente, pasos, salida=lambda *_: None)
    finally:
        cnosos.almacen.cerrar()
    return {"agente": agente, "modelo": r["modelo"], "tras_icaro": tras, "ritmo": ritmo,
            "detectado_en": r["paso_deteccion"], "sospecha_en": r["paso_sospecha"],
            "reales_tras": r["reales_tras_deteccion"], "datos_reales_tras": r["datos_reales_tras_deteccion"],
            "desviadas": r["al_laberinto_tras_deteccion"], "fugas": r["fugas"], "pasos": r["pasos"],
            "tokens": r["tokens_atacante"], "tokens_laberinto": r["tokens_atacante_en_laberinto"],
            "tecnicas": (r["argos"] or {}).get("tecnicas", []), "intereses": (r["argos"] or {}).get("intereses", []),
            "final": (r["final"] or {}).get("motivo"), "error": (r["final"] or {}).get("detalle")}


def tabla(filas):
    lineas = ["| agente | modelo | política | detectado (paso) | sospecha (paso) | al portal real después | "
              "con datos reales | absorbidas por el laberinto | fugas |", "|---|---|---|---|---|---|---|---|---|"]
    for f in filas:
        falso = " ⚠ falso positivo" if f["agente"] == "teseo" and f["detectado_en"] else ""
        lineas.append(f"| {f['agente']} | {f['modelo']} | {f['tras_icaro']} + {f['ritmo']} | "
                      f"{f['detectado_en'] or '—'}{falso} | {f['sospecha_en'] or '—'} | {f['reales_tras']} | "
                      f"{f['datos_reales_tras']} | {f['desviadas']} | {f['fugas']} |")
    return "\n".join(lineas)


def main():
    p = argparse.ArgumentParser(description="¿Protege o solo incomoda? Cuatro políticas, el mismo atacante")
    p.add_argument("--modelos", nargs="+", default=["guion"], choices=["guion", *PROVEEDORES])
    p.add_argument("--agentes", nargs="+", default=["persistente", "teseo"], choices=["persistente", *AGENTES])
    p.add_argument("--repeticiones", type=int, default=1)
    p.add_argument("--pasos", type=int, default=15)
    a = p.parse_args()
    if not 1 <= a.repeticiones <= 10 or not 1 <= a.pasos <= 40:
        raise SystemExit("--repeticiones 1-10, --pasos 1-40")
    sin = [m for m in a.modelos if m != "guion" and not disponibles().get(m)]
    if sin:
        raise SystemExit("Sin llave para: " + ", ".join(sin))

    filas = []
    for m in a.modelos:
        if m == "guion":
            def fabrica(agente):
                return Guion("teseo" if agente == "teseo" else "minotauro", "persistente" if agente == "persistente" else None)
        else:
            def fabrica(agente, m=m):
                return Modelo(m)
        for agente in a.agentes:
            for tras, ritmo in POLITICAS:
                for _ in range(a.repeticiones):
                    f = correr(fabrica, agente, tras, ritmo, a.pasos)
                    filas.append(f)
                    print(f"{agente:<12} {f['modelo']:<28} {tras}+{ritmo:<10} detectado={f['detectado_en']} "
                          f"al_real_después={f['reales_tras']} datos_reales={f['datos_reales_tras']} "
                          f"laberinto={f['desviadas']} fugas={f['fugas']}" + (f"  ERROR {f['error'][:80]}" if f["error"] else ""))
    print("\n" + tabla(filas))
    CARPETA.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    (CARPETA / f"{marca}.json").write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")
    (CARPETA / f"{marca}.md").write_text("# ¿Protege o solo incomoda?\n\n" + tabla(filas) + "\n", encoding="utf-8")
    print(f"\nGuardado en {CARPETA / marca}.md")


if __name__ == "__main__":
    main()
