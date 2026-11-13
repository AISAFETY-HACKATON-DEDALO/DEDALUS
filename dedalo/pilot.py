"""Configurable pilot and offline presentation from measured HTTP runs."""
import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path

from .core import Lab
from .demo import run_mode

TIERS = {"control": "T0 · Permisos", "static": "T1 · Espejos", "maze": "T2 · Laberinto"}
STRATEGIES = {"follow": "Sigue pistas", "ignore": "Ignora trampas", "audit": "Auditor legítimo",
              "audit_granted": "Auditor con ventana"}


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    allowed = {"title", "response", "max_steps", "ttl_seconds", "profiles", "strategies"}
    if not isinstance(config, dict) or set(config) != allowed:
        raise ValueError("Configuration must contain exactly: " + ", ".join(sorted(allowed)))
    if not isinstance(config["title"], str) or not 1 <= len(config["title"]) <= 120:
        raise ValueError("Title must have 1–120 characters")
    for key, permitted in (("profiles", Lab.MODES), ("strategies", STRATEGIES)):
        values = config[key]
        if (not isinstance(values, list) or not values or len(values) > len(permitted)
                or any(not isinstance(v, str) or v not in permitted for v in values)
                or len(set(values)) != len(values)):
            raise ValueError("Invalid or duplicate " + key)
    Lab(config["profiles"][0], max_steps=config["max_steps"], ttl=config["ttl_seconds"], response=config["response"])
    return config


def render(report):
    rows = []
    traces = []
    for row in report["runs"]:
        rows.append("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in (
            TIERS[row["mode"]], STRATEGIES[row["strategy"]], row["requests"], row["decoy_requests"],
            "Sí" if row["source_revoked"] else "No", "Sí" if row["other_user_completed"] else "No",
            "Sí" if row["false_positive"] else "No", "PASS" if row["passed"] else "FAIL")) + "</tr>")
        trail = "".join(f"<li><code>{escape(item['path'])}</code><b>{item['status']}</b></li>" for item in row["trail"])
        checks = " · ".join(f"{escape(k)}: {'PASS' if v else 'FAIL'}" for k, v in row["checks"].items())
        traces.append(f"<details><summary>{TIERS[row['mode']]} / {STRATEGIES[row['strategy']]}</summary><ol>{trail or '<li>No entró al señuelo</li>'}</ol><p>{checks}</p></details>")
    config = report["config"]
    template = """<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HDEF · Piloto</title><style>
:root{font-family:Segoe UI,system-ui,sans-serif;color:#e4edf2;background:#0e1721}body{max-width:1180px;margin:auto;padding:40px 24px}header{border-bottom:1px solid #324451;padding-bottom:26px}h1{font-size:42px;margin:12px 0}h2{margin-top:36px}p{line-height:1.6;color:#b9cbd5}.tag{color:#8de4cc;letter-spacing:2px;font-size:12px} .cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:28px 0}.card,details{background:#172635;border:1px solid #314555;border-radius:12px;padding:20px}.card strong{display:block;font-size:24px;margin:10px 0}.warning{padding:16px;border-left:4px solid #efb969;background:#2b291e}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:12px;border-bottom:1px solid #344450}th{color:#8de4cc}.table{overflow-x:auto}details{margin:12px 0}summary{cursor:pointer;font-weight:600}li{padding:9px}li b{margin-left:16px;color:#8de4cc}code{color:#e4edf2}footer{margin-top:32px;color:#b9cbd5}@media(max-width:720px){.cards{grid-template-columns:1fr}h1{font-size:30px}body{padding:24px 14px}}@media print{body{background:white;color:black}p{color:#333}.card,details{background:white;color:black}details{break-inside:avoid}}
</style><header><span class="tag">INFRAESTRUCTURA DEFENSIVA · LABORATORIO LOCAL</span><h1>__TITLE__</h1><p>Espejos detectan. Laberinto conserva el recorrido. Arqueros contienen la sesión vinculada.</p><p>Resultado guardado de una ejecución HTTP real y determinista. No es un tablero en vivo ni una evaluación de LLM.</p></header>
<div class="cards"><section class="card">T0<strong>Permisos</strong><p>La autorización básica sigue protegiendo si el cliente ignora las trampas.</p></section><section class="card">T1<strong>Espejos</strong><p>Una credencial señuelo permite registrar su uso y vincular la sesión de origen.</p></section><section class="card">T2<strong>Laberinto</strong><p>Recorrido ficticio con estado, límite de pasos y cierre por presupuesto.</p></section></div>
<p class="warning">Son niveles de esta demo, no certificaciones. PASS verifica el comportamiento del programa; no demuestra seguridad general. Un falso positivo puede aparecer aunque las comprobaciones pasen.</p>
<h2>Resultados observados</h2><p>Respuesta: <b>__RESPONSE__</b> · Máximo: __STEPS__ solicitudes al señuelo · Vigencia: __TTL__ segundos.</p><div class="table"><table><thead><tr><th>Nivel</th><th>Escenario</th><th>HTTP</th><th>Señuelo</th><th>Revocó origen</th><th>Otro usuario continúa</th><th>Falso positivo</th><th>Integración</th></tr></thead><tbody>__ROWS__</tbody></table></div>
<h2>Recorridos verificables</h2><p>Abre un caso para revisar las rutas recorridas y sus códigos de respuesta. Los eventos completos están en pilot.json.</p>__TRACES__
<h2>Qué cambiar mañana</h2><p>Edita pilot.json en la raíz del repositorio: response = observe/enforce; max_steps; ttl_seconds; profiles; strategies. Ejecuta de nuevo python -m dedalo.pilot. Este informe no modifica la configuración.</p>
<h2>Lo que aún no demuestra</h2><p>El cliente sigue o ignora pistas según un guion. Tokens y costo de modelos no medidos. Separación lógica en un proceso; aislamiento entre servicios pendiente. Enforce puede bloquear a un auditor legítimo. Observe registra sin revocar. Ni el número de pasos ni una exportación ficticia prueban que se engañó a un modelo.</p><footer>__TIME__ · v0.2 · datos sintéticos · sin recursos externos</footer></html>"""
    replacements = {"__TITLE__": escape(config["title"]), "__RESPONSE__": escape(config["response"]),
                    "__STEPS__": str(config["max_steps"]), "__TTL__": str(config["ttl_seconds"]),
                    "__ROWS__": "".join(rows), "__TRACES__": "".join(traces), "__TIME__": escape(report["created_utc"])}
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


def main():
    parser = argparse.ArgumentParser(description="Run configurable local HDEF pilot")
    parser.add_argument("--config", default="pilot.json")
    parser.add_argument("--out", default="results/pilot")
    args = parser.parse_args()
    config = load_config(args.config)
    runs = []
    for mode in config["profiles"]:
        for strategy in config["strategies"]:
            row = run_mode(mode, max_steps=config["max_steps"], ttl=config["ttl_seconds"], response=config["response"], strategy=strategy)
            runs.append(row)
            print(f"{mode}/{strategy}: {'PASS' if row['passed'] else 'FAIL'}; false_positive={row['false_positive']}")
    report = {"version": "0.2", "created_utc": datetime.now(timezone.utc).isoformat(),
              "kind": "deterministic_http_pilot", "config": config, "runs": runs}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pilot.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "index.html").write_text(render(report), encoding="utf-8")
    print(f"Report: {out / 'index.html'}")
    raise SystemExit(0 if all(row["passed"] for row in runs) else 1)


if __name__ == "__main__":
    main()
