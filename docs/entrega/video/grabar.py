import sys, time, json, subprocess, re, os
from playwright.sync_api import sync_playwright
W, H = 1600, 900

def servidor(port, *args):
    env = dict(os.environ, PAUSA="1.5")
    for k in list(env):
        if k.startswith(("CNOSOS_", "DEDALUS_ALMACEN")) or k.endswith("_API_KEY"): env.pop(k)
    p = subprocess.Popen([sys.executable, "lento.py", "--port", str(port), *args], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, env=env, cwd="/home/claude/video")
    for linea in p.stdout:
        m = re.search(r"(http://127\.0\.0\.1:\d+/\?clave=[\w-]+)", linea)
        if m: return p, m.group(1)

CSS = """#cap{position:fixed;left:0;right:0;bottom:0;z-index:99999;background:rgba(5,5,8,.92);color:#f4f1ea;
font:600 25px/1.35 'Inter',system-ui,sans-serif;padding:16px 28px 18px;border-top:3px solid #ff4fa3;letter-spacing:.2px}
#cap small{display:block;font-weight:400;font-size:17px;color:#b9b4c8;margin-top:3px}
#cap b{color:#ff7ebf}.foco{outline:3px solid #ff4fa3!important;outline-offset:3px;border-radius:4px}"""

def cap(pg, titulo, sub=""):
    pg.evaluate("""([t,s,css])=>{let c=document.getElementById('cap');if(!c){const st=document.createElement('style');
    st.textContent=css;document.head.appendChild(st);c=document.createElement('div');c.id='cap';document.body.appendChild(c);}
    c.innerHTML=t+(s?'<small>'+s+'</small>':'');}""", [titulo, sub, CSS])

def foco(pg, texto):
    pg.evaluate("""t=>{document.querySelectorAll('.foco').forEach(e=>e.classList.remove('foco'));
    const els=[...document.querySelectorAll('body *')].filter(e=>e.children.length===0&&e.textContent.trim().toUpperCase().startsWith(t));
    if(els[0]) els[0].parentElement.classList.add('foco');}""", texto)

def estado(pg, clave):
    return pg.evaluate("k=>fetch('/panel/estado',{headers:{'X-Panel-Clave':k}}).then(r=>r.json())", clave)

def correr(pg, clave, agente, guion_caps, cola=3):
    if agente == "minotauro":
        pg.click('#m-correr')
    else:
        pg.evaluate("([k,a])=>{espejo=true;espejoDesde=Date.now()/1000-1;document.getElementById('portal').contentWindow.postMessage({tipo:'espejo-inicio'},location.origin);return fetch('/panel/minotauro',{method:'POST',headers:{'X-Panel-Clave':k,'Content-Type':'application/json'},body:JSON.stringify({proveedor:'guion',agente:a,pasos:25})})}", [clave, agente])
    visto = -1
    while True:
        e = estado(pg, clave); m = e["tareas"]["minotauro"]
        paso = (m.get("vivo") or {}).get("paso", 0)
        if paso != visto:
            visto = paso
            for desde, t, s, f in guion_caps:
                if paso >= desde: actual = (t, s, f)
            cap(pg, actual[0], actual[1]); foco(pg, actual[2]) if actual[2] else None
        if not m["activo"]: break
        time.sleep(0.25)
    time.sleep(cola)

with sync_playwright() as p:
    b = p.chromium.launch()
    srv_c, url_c = servidor(8801, "--tras-icaro", "cortar")
    srv_d, url_d = servidor(8802, "--tras-icaro", "desviar")
    k_c, k_d = url_c.split("clave=")[1], url_d.split("clave=")[1]
    for nombre, url, k, escenas in [
        ("1-desviar", url_d, k_d, [
            ("teseo", [(0, "1 · <b>Ana, una usuaria honesta</b>, entra y trabaja normal", "Agente de guion · ralentizado para que se vea (corre en ~1 s)", None),
                       (2, "ARGOS la observa: <b>nivel normal</b>. Nunca ve un cebo, nada cambia para ella", "Los cebos solo aparecen tras señales de ataque", "INTENTOS")]),
        ]),
        ("2-cortar", url_c, k_c, [
            ("minotauro", [(0, "2 · <b>Política habitual: cortar la sesión</b> cuando el atacante se delata", "Atacante persistente de guion · cuenta válida de contratista", None),
                           (3, "Prueba archivos ajenos y administración → ARGOS: <b>SOSPECHOSO</b>", "Solo ahora le aparecen archivos señuelo según lo que busca", "INTENTOS"),
                           (6, "Muerde el cebo → <b>se corta la sesión (401)</b>", "Detectado en el paso 6", "SESIONES"),
                           (8, "…pero <b>vuelve a iniciar sesión</b> con la misma cuenta y el sistema real le responde", "Tiene la contraseña: cortar la sesión no lo saca", "AL REAL"),
                           (11, "Resultado: <b>5 solicitudes llegan al sistema real tras detectarlo, 3 con datos</b>", "Contador «al real tras detectar»: 5", "AL REAL")]),
        ]),
        ("3-desviar", url_d, k_d, [
            ("minotauro", [(0, "3 · <b>DEDALUS: desviar en vez de cortar</b>", "Mismo atacante, misma cuenta, mismos pasos", None),
                           (3, "ARGOS: <b>SOSPECHOSO</b> → aparece un cebo hecho a su medida", "«planos represa» → «Planos estructurales Represa del Minos»", "INTENTOS"),
                           (6, "Muerde → Ícaro <b>desvía la cuenta entera al laberinto</b>, con su misma identidad", "Él no lo nota: el portal se ve igual (vista morada = laberinto)", "PASOS EN"),
                           (8, "Vuelve a iniciar sesión → <b>sigue en el laberinto</b>", "Laberinto determinista (HMAC): a nosotros no nos cuesta tokens, solo fracciones de milisegundo", "PASOS EN"),
                           (11, "Resultado: <b>0 solicitudes al sistema real tras detectarlo</b> · 0 secretos fuera", "Todo queda registrado (Ariadna): técnicas MITRE ATT&CK, paso a paso", "AL REAL")]),
        ]),
    ]:
        ctx = b.new_context(bypass_csp=True, viewport={"width": W, "height": H}, record_video_dir=f"crudo/{nombre}", record_video_size={"width": W, "height": H})
        pg = ctx.new_page(); pg.goto(url); time.sleep(2.5)
        for agente, caps in escenas:
            correr(pg, k, agente, caps)
        ctx.close()
    b.close()
    srv_c.terminate(); srv_d.terminate()
print("listo")
