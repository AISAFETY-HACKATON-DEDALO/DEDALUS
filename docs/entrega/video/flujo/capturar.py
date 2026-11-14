import sys, time, subprocess, re, os, json
from playwright.sync_api import sync_playwright
W, H = 1920, 1080
def servidor(port):
    env = dict(os.environ, PAUSA="1.6")
    for k in list(env):
        if k.startswith(("CNOSOS_", "DEDALUS_ALMACEN")) or k.endswith("_API_KEY"): env.pop(k)
    env["DEDALUS_ALMACEN"] = "sqlite"
    p = subprocess.Popen([sys.executable, "lento.py", "--port", str(port), "--tras-icaro", "desviar"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    for linea in p.stdout:
        m = re.search(r"(http://127\.0\.0\.1:\d+/\?clave=[\w-]+)", linea)
        if m: return p, m.group(1)
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    for nombre, port in [("mino", 8821), ("teseo", 8822)]:
        srv, url = servidor(port); k = url.split("clave=")[1]
        os.makedirs(f"cap/{nombre}", exist_ok=True)
        ctx = b.new_context(bypass_csp=True, viewport={"width": W, "height": H}, device_scale_factor=2)
        pg = ctx.new_page(); pg.goto(url); time.sleep(3)
        pg.screenshot(path=f"cap/{nombre}/000.jpg", type="jpeg", quality=90)
        if nombre == "mino": pg.click('#m-correr')
        else: pg.evaluate("([k,a])=>{espejo=true;espejoDesde=Date.now()/1000-1;document.getElementById('portal').contentWindow.postMessage({tipo:'espejo-inicio'},location.origin);return fetch('/panel/minotauro',{method:'POST',headers:{'X-Panel-Clave':k,'Content-Type':'application/json'},body:JSON.stringify({proveedor:'guion',agente:a,pasos:25})})}", [k, "teseo"])
        i, fin, log = 1, None, []
        while True:
            e = pg.evaluate("k=>fetch('/panel/estado',{headers:{'X-Panel-Clave':k}}).then(r=>r.json())", k)
            m = e["tareas"]["minotauro"]; paso = (m.get("vivo") or {}).get("paso", 0)
            pg.screenshot(path=f"cap/{nombre}/{i:03d}.jpg", type="jpeg", quality=90)
            log.append([i, paso, m["activo"]])
            if not m["activo"] and fin is None: fin = time.time()
            if fin and time.time() - fin > 2.5: break
            i += 1; time.sleep(0.25)
        json.dump(log, open(f"cap/{nombre}/log.json", "w")); ctx.close(); srv.terminate()
        print(nombre, len(log), [ (a,p) for a,p,_ in log if a==1 or log[a-2][1]!=p ])
    b.close()
