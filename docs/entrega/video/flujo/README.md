# Cómo se hizo el video del flujo y el demo en bucle

Todo sale del panel real corriendo en local con SQLite y el atacante de guion `persistente` (política `desviar`).

1. `python capturar.py` levanta el panel con `lento.py` (el guion ralentizado) y guarda capturas a doble resolución en `cap/`, una por solicitud.
2. Los recortes del portal y del registro van a `rec/` (ver las coordenadas en la conversación del equipo o repetir el recorte: portal `0,76–1920,1378`, registro `1940,1284–3064,2044` sobre capturas de 3840×2160).
3. `video.html` dibuja cada cuadro en función del tiempo (`render(t)`); `render.py` lo recorre con Chrome y ffmpeg, una escena por archivo; `audio.py` sintetiza la música.
4. `demo.html` dibuja los 12 cuadros del demo en bucle (`poner(k)`), que usan la presentación y `DEDALUS-demo-bucle.mp4`.

Necesita `playwright`, Chrome y `ffmpeg`. No forma parte del producto.
