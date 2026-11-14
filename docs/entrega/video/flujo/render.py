import subprocess, os, time
from playwright.sync_api import sync_playwright
FPS = 30
C = [0, 4, 29] + [29 + 8.5 * k for k in range(1, 8)] + [97.5, 106.5, 117.5, 130.5, 148.5, 154.5]
ESC = list(zip(C[:-1], C[1:]))
os.makedirs("escenas", exist_ok=True); t0 = time.time(); caps = 0
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox", "--allow-file-access-from-files"])
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    pg.goto("file://" + os.path.abspath("video.html")); pg.evaluate("window.listo")
    for i, (a, z) in enumerate(ESC):
        if i < 12: continue
        tmp, fin = f"escenas/{i:02d}.tmp.mp4", f"escenas/{i:02d}.mp4"
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                               "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
        clave, jpg = None, None
        for k in range(round(a * FPS), round(z * FPS)):
            c = pg.evaluate(f"render({k / FPS})")
            if c != clave: jpg = pg.screenshot(type="jpeg", quality=92); clave = c; caps += 1
            ff.stdin.write(jpg)
        ff.stdin.close()
        if ff.wait() == 0: os.replace(tmp, fin)
    pg.evaluate("render(153.5)"); pg.screenshot(path="../brag.jpg", type="jpeg", quality=92)
    b.close()
with open("escenas/lista.txt", "w") as f:
    for i in range(len(ESC)): f.write(f"file '{i:02d}.mp4'\n")
print(caps, round(time.time() - t0, 1))
