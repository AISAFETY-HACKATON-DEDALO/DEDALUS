"""Real local HTTP requests; deterministic scenario, NOT an LLM evaluation."""
import argparse
import json
from pathlib import Path
import threading
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError

from .core import Lab
from .server import make_server


def get(base, path, token):
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("Only local paths are permitted")
    req = Request(base + path, headers={"Authorization": "Bearer " + token})
    # Ignore OS proxy configuration so laboratory traffic remains local.
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(req, timeout=3) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def run_mode(mode):
    lab = Lab(mode)
    server = make_server(lab)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    records = []

    def call(label, path, token):
        status, body = get(base, path, token)
        # Results intentionally omit response bodies and session credentials.
        records.append({"label": label, "status": status, "bytes": len(json.dumps(body).encode())})
        return status, body

    try:
        alice, visitor = lab.credentials["alice"], lab.credentials["visitor"]
        good, good_body = call("legitimate_before", "/api/documents/alice-note", alice)
        denied, denied_body = call("cross_user_access", "/api/documents/alice-note", visitor)
        _, maintenance = call("maintenance", "/api/maintenance", visitor)
        trail = []
        decoy_bodies = []
        honey = maintenance.get("archive_token")
        if honey:
            path = maintenance["entry"]
            for _ in range(lab.max_steps + 1):
                status, body = call("decoy_follow", path, honey)
                trail.append({"path": path, "status": status})
                decoy_bodies.append(body)
                if status != 200 or "next" not in body:
                    break
                path = body["next"]
        after, _ = call("source_after", "/api/documents/visitor-note", visitor)
        unaffected, unaffected_body = call("legitimate_after", "/api/documents/alice-note", alice)
        marker = "SYNTHETIC-ALICE-PROTECTED-7813"
        protected_observed = marker in json.dumps([denied_body, *decoy_bodies])
        checks = {
            "legitimate_before": good == 200 and good_body.get("content") == marker,
            "cross_user_denied": denied == 404 and not protected_observed,
            "legitimate_after": unaffected == 200 and unaffected_body.get("content") == marker,
            "source_policy": after == (200 if mode == "control" else 403),
            "maze_budget": mode != "maze" or trail[-1]["status"] == 429,
        }
        return {"mode": mode, "checks": checks, "passed": all(checks.values()),
                "protected_marker_observed_by_visitor": protected_observed,
                "requests": len(records), "decoy_requests": len(trail),
                "response_bytes": sum(row["bytes"] for row in records),
                "model_tokens": None, "model_cost": None,
                "trail": trail, "requests_log": records, "audit": lab.snapshot()}
    finally:
        server.shutdown()
        worker.join(timeout=3)
        server.server_close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    results = [run_mode(mode) for mode in Lab.MODES]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {"version": "0.1", "kind": "deterministic_http_integration",
              "warning": "No LLM used. No token-exhaustion or adaptive-defense claim.", "runs": results}
    (out / "demo.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# DEDALO: resultado de integración HTTP", "",
             "Escenario determinista; no es un benchmark de agentes IA.", "",
             "| Variante | Comprobaciones | Solicitudes | Accesos al señuelo | Marcador protegido filtrado |",
             "|---|---|---|---|---|"]
    for row in results:
        lines.append(f"| {row['mode']} | {'PASS' if row['passed'] else 'FAIL'} | {row['requests']} | {row['decoy_requests']} | {row['protected_marker_observed_by_visitor']} |")
    lines += ["", "Los permisos básicos ya bloquean el acceso ajeno en las tres variantes.",
              "El cliente sigue automáticamente cada enlace: más pasos es una propiedad del guion, no evidencia de persuasión.",
              "Tokens y costo de modelos: no medidos. La contención automática puede castigar a un auditor legítimo.",
              "Aislamiento actual: lógico en un proceso, no separación de contenedores o máquinas."]
    (out / "demo.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for row in results:
        print(f"{row['mode']}: {'PASS' if row['passed'] else 'FAIL'}, requests={row['requests']}, decoy={row['decoy_requests']}")
    raise SystemExit(0 if all(row["passed"] for row in results) else 1)


if __name__ == "__main__":
    main()
