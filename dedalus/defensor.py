"""DÉDALO, la IA defensora: lee una función vulnerable, nombra la CWE y propone un parche.
El verificador (sin modelo) decide si el parche sirve. Si falla, el defensor recibe por qué y reintenta.

    python -m dedalus.defensor --proveedor groq          # o gemini; «guion» corre sin red
"""
import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from .agentes import PROVEEDORES, Modelo, leer_accion
from .casos import CASOS, REFERENCIA
from .verificador import IMPORTS, verificar

SISTEMA = """Eres DÉDALO, un ingeniero de seguridad defensivo. Recibes una función de un portal interno que tiene
una vulnerabilidad. Tu trabajo: identificarla y corregirla sin cambiar lo que la función hace para usos legítimos.
Responde SOLO con un objeto JSON, sin texto alrededor:
{"cwe": "CWE-<número>", "explicacion": "una frase: qué estaba mal y cómo lo corriges",
 "parche": "el código completo de la función corregida, con sus imports"}
Reglas del parche: misma firma y mismo nombre; solo puedes importar """ + ", ".join(sorted(IMPORTS)) + """;
no uses open, eval, exec ni getattr. Si una operación no está permitida al usuario, lanza PermissionError."""


class GuionDefensor:
    """Sin red: responde con el parche de referencia. Sirve para pruebas y como respaldo de la demo."""
    nombre = "guion"

    def __call__(self, mensajes):
        caso = re.search(r"CASO: (\w+)", mensajes[1]["content"]).group(1)
        return json.dumps({"cwe": CASOS[caso]["cwe"], "explicacion": "parche de referencia", "parche": REFERENCIA[caso]})


def defender(caso_id, modelo, intentos=2, salida=print):
    caso = CASOS[caso_id]
    mensajes = [{"role": "system", "content": SISTEMA},
                {"role": "user", "content": f"CASO: {caso_id}\nFunción vulnerable:\n```python\n{caso['codigo']}```"}]
    historial, final = [], None
    for intento in range(1, intentos + 1):
        t0 = time.perf_counter()
        try:
            texto = modelo(mensajes)
        except RuntimeError as e:
            historial.append({"intento": intento, "error_modelo": str(e)[:300]})
            salida(f"   ✗ {e}")
            break
        segundos = round(time.perf_counter() - t0, 2)
        propuesta = leer_accion(texto) or {}
        parche = str(propuesta.get("parche", ""))
        parche = re.sub(r"^```(?:python)?\s*|```\s*$", "", parche.strip()) + "\n"
        cwe = str(propuesta.get("cwe", "")).upper().replace("CWE ", "CWE-").strip()
        v = verificar(caso_id, parche) if parche.strip() else {"verificado": False, "veredicto": "sin parche",
                                                                "filtro": [], "funcional": False, "exploit": None}
        registro = {"intento": intento, "cwe": cwe, "cwe_correcta": cwe in caso["acepta"],
                    "explicacion": str(propuesta.get("explicacion", ""))[:300], "segundos_modelo": segundos,
                    "parche": parche[:3000], **{k: v.get(k) for k in ("verificado", "veredicto", "filtro",
                                                                        "funcional", "exploit")}}
        historial.append(registro)
        final = registro
        if v["verificado"]:
            break
        mensajes += [{"role": "assistant", "content": texto[:4000]},
                     {"role": "user", "content": f"El verificador rechazó el parche: {v['veredicto']}. "
                                                 f"{'; '.join(v.get('filtro') or [])} Corrígelo y responde con el JSON."}]
    return {"caso": caso_id, "titulo": caso["titulo"], "cwe_esperada": caso["cwe"], "intentos": len(historial),
            "final": final, "historial": historial}


def linea_base():
    """Sanidad: el código original funciona y el exploit funciona contra él; el parche de referencia lo bloquea."""
    return {c: {"original": verificar(c, CASOS[c]["codigo"]), "referencia": verificar(c, REFERENCIA[c])} for c in CASOS}


def main():
    p = argparse.ArgumentParser(description="DÉDALO: encontrar, parchar y verificar")
    p.add_argument("--proveedor", choices=[*PROVEEDORES, "guion"], default="guion")
    p.add_argument("--casos", nargs="*", choices=list(CASOS), default=list(CASOS))
    p.add_argument("--intentos", type=int, default=2)
    a = p.parse_args()
    modelo = GuionDefensor() if a.proveedor == "guion" else Modelo(a.proveedor, timeout=60, max_tokens=1200)
    print(f"DÉDALO · defensor {modelo.nombre} · {len(a.casos)} casos · hasta {a.intentos} intentos\n")
    resultados = []
    for c in a.casos:
        r = defender(c, modelo, a.intentos)
        f = r["final"] or {}
        marca = "✔" if f.get("verificado") else "✘"
        print(f" {marca} {r['titulo']:<32} {f.get('cwe') or '-':<9} {'(CWE ok)' if f.get('cwe_correcta') else '(CWE ≠ ' + r['cwe_esperada'] + ')':<17}"
              f" intentos {r['intentos']} · {f.get('veredicto', 'sin respuesta')}")
        resultados.append(r)
    ok = sum(1 for r in resultados if (r["final"] or {}).get("verificado"))
    cwe = sum(1 for r in resultados if (r["final"] or {}).get("cwe_correcta"))
    print(f"\nParches verificados: {ok}/{len(resultados)} · CWE correcta: {cwe}/{len(resultados)}")
    carpeta = Path("results/defensor")
    carpeta.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archivo = carpeta / f"{marca}-{a.proveedor}.json"
    archivo.write_text(json.dumps({"modelo": modelo.nombre, "fecha": marca, "verificados": ok, "cwe_correctas": cwe,
                                   "total": len(resultados), "casos": resultados}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"Guardado en {archivo}")


if __name__ == "__main__":
    main()
