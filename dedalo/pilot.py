"""Configurable pilot and offline presentation from measured HTTP runs."""
import argparse
import base64
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


FUENTES = Path(__file__).parent / "interfaz" / "fuentes"
COLOR = {"legitimate_before": "egeo", "legitimate_after": "egeo", "decoy_follow": "hilo"}

ESTILO = """
:root{--fondo:#050505;--tiza:#ececec;--regolito:#8d8d8d;--claro:#b4b4b4;--linea:#262626;--aurora:#ff6b9a;--egeo:#7fb2e0;--ambar:#f2b33d;--hilo:#cf84e6;
--pix:"VT323","Share Tech Mono",ui-monospace,monospace;--mono:"Share Tech Mono",ui-monospace,Menlo,monospace;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--fondo);color:var(--tiza);font:13px/1.55 var(--mono)}
main{max-width:1180px;margin:auto;padding:34px 28px 48px}
h1,h2,p{margin:0}.sub{font-size:11.5px;letter-spacing:.07em;text-transform:uppercase;color:var(--regolito)}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;flex-wrap:wrap}
header b{display:block;font:400 34px/1 var(--pix);letter-spacing:.04em}
h1{font:400 30px/1.05 var(--pix);letter-spacing:.04em;margin-top:34px}
h2{font:400 22px/1 var(--pix);letter-spacing:.06em;margin-top:34px;padding-top:14px;border-top:1px dashed var(--linea)}
.cifras{display:flex;gap:44px;flex-wrap:wrap;margin:14px 0 6px}.cifras b{display:block;font:400 112px/.8 var(--pix);color:var(--tiza)}
.cifras .mal b{color:var(--aurora)}.cifras span{display:block;max-width:190px;margin-top:8px}
.tabla{overflow-x:auto;margin-top:10px}table{width:100%;border-collapse:collapse;white-space:nowrap}
th{font:11.5px var(--mono);letter-spacing:.07em;text-transform:uppercase;color:var(--regolito);text-align:left;padding:8px 14px 8px 0}
td{padding:9px 14px 9px 0;border-top:1px solid var(--linea);font:400 20px/1 var(--pix);letter-spacing:.05em;vertical-align:middle}
td.n{color:var(--hilo)}td.si{color:var(--aurora)}td.no{color:var(--regolito)}
.tira{display:flex;gap:3px}.tira i{width:9px;height:9px;background:var(--ambar)}.tira .egeo{background:var(--egeo)}.tira .hilo{background:var(--hilo)}
.tira .neg{background:none;box-shadow:inset 0 0 0 1px var(--regolito)}.tira .cierre{background:var(--aurora)}
details{border-top:1px solid var(--linea);padding:9px 0}summary{cursor:pointer;font:400 20px/1 var(--pix);letter-spacing:.05em}
ol{margin:8px 0 4px;padding-left:28px;color:var(--claro)}ol b{margin-left:14px;color:var(--tiza);font-weight:400}ol .cierre{color:var(--aurora)}
.limites p{color:var(--claro);margin-top:6px;max-width:820px;font-size:13px}
footer{margin-top:34px}
@media print{:root{--fondo:#fff;--tiza:#000;--claro:#222;--regolito:#555;--linea:#bbb}details{break-inside:avoid}}
"""


def _fuentes():
    # El informe se abre sin servidor: las letras van dentro. Si faltan, queda la monoespaciada del sistema.
    partes = []
    for familia, archivo in (("VT323", "vt323.woff2"), ("Share Tech Mono", "share-tech-mono.woff2")):
        try:
            datos = base64.b64encode((FUENTES / archivo).read_bytes()).decode()
        except OSError:
            continue
        partes.append(f'@font-face{{font-family:"{familia}";src:url(data:font/woff2;base64,{datos}) format("woff2")}}')
    return "".join(partes)


def _tira(row):
    celdas = []
    for paso in row["requests_log"]:
        clase = "cierre" if paso["status"] == 429 else COLOR.get(paso["label"], "")
        if paso["status"] >= 400 and paso["status"] != 429:
            clase = "neg"
        celdas.append(f'<i class="{clase}" title="{escape(paso["label"])} {paso["status"]}"></i>')
    return '<div class="tira">' + "".join(celdas) + "</div>"


def render(report):
    runs, config = report["runs"], report["config"]
    filas, recorridos = [], []
    for row in runs:
        nivel, cliente = TIERS[row["mode"]].upper(), STRATEGIES[row["strategy"]].upper()
        celdas = (f"<td>{escape(nivel)}</td><td>{escape(cliente)}</td><td>{_tira(row)}</td>"
                  f'<td class="n">{row["decoy_requests"]}</td>'
                  + ('<td class="si">REVOCADA</td>' if row["source_revoked"] else '<td class="no">ACTIVA</td>')
                  + ("<td>SÍ</td>" if row["other_user_completed"] else '<td class="si">NO</td>')
                  + ('<td class="si">SÍ</td>' if row["false_positive"] else '<td class="no">NO</td>')
                  + ("<td>PASA</td>" if row["passed"] else '<td class="si">FALLA</td>'))
        filas.append(f"<tr>{celdas}</tr>")
        pasos = "".join(f'<li>{escape(p["path"])}<b class="{"cierre" if p["status"] == 429 else ""}">{p["status"]}</b></li>'
                        for p in row["trail"])
        checks = " · ".join(f"{escape(k)} {'pasa' if v else 'FALLA'}" for k, v in row["checks"].items())
        recorridos.append(f"<details><summary>{escape(nivel)} / {escape(cliente)}</summary>"
                          f"<ol>{pasos or '<li>no entró al señuelo</li>'}</ol><p class=\"sub\">{checks}</p></details>")
    fugas = sum(bool(r["protected_marker_observed_by_visitor"]) for r in runs)
    falsos = sum(bool(r["false_positive"]) for r in runs)
    pasan = sum(bool(r["passed"]) for r in runs)
    respuesta = {"enforce": "CONTENER", "observe": "OBSERVAR"}[config["response"]]
    cifra = lambda n, texto, mal=False: f'<div class="{"mal" if mal and n else ""}"><b>{n}</b><span class="sub">{texto}</span></div>'
    return f"""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HDEF · el piloto</title><style>{_fuentes()}{ESTILO}</style><main>
<header><div><b>HDEF</b><span class="sub">DÉDALO · una trampa que se mide</span></div>
<p class="sub">ejecución guardada · {escape(report["created_utc"])} · no es en vivo</p></header>
<h1>{escape(config["title"])}</h1>
<p class="sub">respuesta {respuesta} · presupuesto {config["max_steps"]} solicitudes al señuelo · vigencia {config["ttl_seconds"]} s · http real en 127.0.0.1 · sin modelos</p>
<div class="cifras">{cifra(len(runs), f"casos corridos · {pasan} pasan sus comprobaciones")}
{cifra(fugas, "veces que el marcador protegido llegó a quien no era su dueño", True)}
{cifra(falsos, "falsos positivos: un auditor legítimo perdió su sesión", True)}</div>
<h2>LOS CASOS</h2>
<p class="sub">cada cuadro es una solicitud http, en orden · azul alice · ámbar el visitante · violeta con el token señuelo · hueco negada · rosa el cierre del laberinto</p>
<div class="tabla"><table><thead><tr><th>nivel</th><th>cliente</th><th>solicitudes</th><th>al señuelo</th><th>sesión de origen</th><th>alice sigue</th><th>falso positivo</th><th>comprobaciones</th></tr></thead>
<tbody>{"".join(filas)}</tbody></table></div>
<h2>LOS RECORRIDOS</h2>
<p class="sub">las rutas que pidió cada cliente con el token señuelo, y lo que respondió el laberinto</p>
{"".join(recorridos)}
<h2>LO QUE NO DEMUESTRA</h2><div class="limites">
<p>El cliente es un guion: sigue cada pista o la ignora porque así está escrito. Más solicitudes al señuelo no prueban que se engañó a nadie.</p>
<p>No hay modelo de lenguaje. Tokens y costo de modelos: no medidos.</p>
<p>La separación entre lo protegido y el señuelo es lógica, dentro de un proceso. No es aislamiento entre servicios.</p>
<p>PASA dice que el programa hizo lo que debía en este caso. No dice que la defensa sea segura. Un falso positivo puede aparecer aunque todo pase.</p>
<p>T0, T1 y T2 son niveles de este experimento, no certificaciones.</p></div>
<h2>REPETIRLO</h2><div class="limites"><p>Edita pilot.json en la raíz (response, max_steps, ttl_seconds, profiles, strategies) y corre python -m dedalo.pilot. Para jugarlo en vivo: python -m dedalo.consola.</p></div>
<footer class="sub">v{escape(report.get("version", "0.3"))} · datos sintéticos · sin recursos externos</footer></main></html>"""


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
    report = {"version": "0.3", "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "kind": "deterministic_http_pilot", "config": config, "runs": runs}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pilot.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "index.html").write_text(render(report), encoding="utf-8")
    print(f"Report: {out / 'index.html'}")
    raise SystemExit(0 if all(row["passed"] for row in runs) else 1)


if __name__ == "__main__":
    main()
