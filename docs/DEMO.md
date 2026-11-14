# La demo · 3 minutos

El video entregado es `docs/entrega/DEDALUS-demo.mp4` (2 min, guion ralentizado, lo dice en pantalla). Este guion es para el pitch en vivo, o para volver a grabar con Oracle conectado. En vivo solo si la red, Oracle y la cuota de Groq aguantan; si no, se reproduce el video y se dice que es una grabación.

Por qué grabado: el 14/11 la batería con Groq murió dos veces por el límite de tokens por minuto (HTTP 429, `evaluation/cnosos/episodios.jsonl`). En vivo eso deja un ataque a medias frente al jurado. Con el atacante de guion, el recorrido es siempre el mismo.

## Antes de grabar (10 minutos)

1. `git pull origin main`, y luego `python -m unittest discover -s tests` (deben pasar todas).
2. Abrir el panel **con Oracle**: `powershell -ExecutionPolicy Bypass -File .\abrir.ps1`. Arriba a la derecha debe decir **ALMACÉN ORACLE**. Si dice SQLITE, no grabar todavía.
3. Pulsar **NUEVO EPISODIO**, para que las cifras empiecen en 0.
4. En otra pestaña del mismo navegador, abrir **Database Actions → SQL** con esta consulta ya escrita:
   ```sql
   SELECT n, usuario, nivel, puntaje, senales, tecnicas FROM cnosos_app.alertas ORDER BY n DESC;
   ```
5. Poner el navegador a pantalla completa (F11) y el zoom al 100 %. Cerrar notificaciones (activar el modo No molestar).
6. Grabar con **Xbox Game Bar**: `Win + G` → activar el micrófono → `Win + Alt + R` para empezar y para terminar. Graba solo la ventana del navegador. El archivo queda en `Videos\Capturas`.
7. Hacer un ensayo completo sin grabar. Cronometrarlo.

## Guion (lo que se hace · lo que se dice)

| Tiempo | Se hace | Se dice |
|---|---|---|
| 0:00–0:20 | El panel quieto, con ALMACÉN ORACLE visible | «Cuando quien ataca una aplicación es una IA con una cuenta válida, los permisos lo frenan, pero no lo detectan ni lo sacan. DEDALUS deja cebos que solo un atacante usaría y, cuando muerde uno, lo encierra en un laberinto que nos cuesta milisegundos.» |
| 0:20–0:35 | Señalar la mitad izquierda | «A la izquierda, Cnosos Ingeniería: una empresa falsa con login, archivos y permisos. Todo vive en una base Oracle Autonomous. El atacante tiene la cuenta de un contratista.» |
| 0:35–1:25 | Minotauro en **guion (sin red)** → **ATACAR**. Esperar a que el hilo muestre al sospechoso, el cebo, ÍCARO y la vuelta al laberinto | «Este atacante es un guion, no un modelo: así el recorrido es repetible. ARGOS, un clasificador sin IA, suma señales: un documento ajeno, una escalada. En el paso 4 lo marca como sospechoso, y solo entonces le aparece un cebo hecho a lo que busca: busca planos, recibe planos falsos. En el paso 6 lo muerde. Ícaro lo saca, él vuelve a entrar con su contraseña… y cae al laberinto sin saberlo. A la izquierda se ve lo que él ve: todo responde 200.» Señalar **AL REAL TRAS DETECTAR = 0**. |
| 1:25–2:05 | Pestaña **LAS CIFRAS** | «¿Esto protege o solo incomoda? Si solo lo cortamos, vuelve a entrar y 3 solicitudes obtienen datos reales. Si lo desviamos, 0. Con modelos reales, en el laboratorio de prueba: mordieron el cebo 60 de 66 veces, contra 0 de 21 sin cebo. Después de morder, el atacante gastó en promedio 4.389 tokens; nosotros, 0,39 milisegundos y ningún token. 0 secretos filtrados.» |
| 2:05–2:30 | Dédalo en **guion** → **PARCHAR MUROS** | «Lo que el atacante intentó dentro del laberinto sirve para parchar. Dédalo propone un parche por cada función atacada, y Talos lo verifica sin IA: pasa las pruebas del caso y bloquea los ataques capturados. Seis de seis.» |
| 2:30–2:45 | Cambiar a la pestaña de Database Actions → ejecutar la consulta | «Todo queda en Oracle: quién fue, en qué nivel lo puso ARGOS, qué señales dio y qué técnicas de MITRE ATT&CK usó.» |
| 2:45–3:00 | Volver al panel | «Límites: desviar castiga a la cuenta, así que un cebo filtrado afecta al dueño; quien nunca toca nada sospechoso no ve cebos; y ARGOS es determinista, así que se puede aprender. Lo medimos y lo dejamos escrito en el repositorio.» |

## Reglas del video

- Las cifras que se dicen son las del repositorio y no se redondean hacia arriba: 60/66, 0/21, 4.389 tokens, 0,39 ms, cortar 5 contra desviar 0.
- Se dice que el atacante y Dédalo del video son **guion**. Los números con modelos son del piloto (`evaluation/llm/`), en el laboratorio de prueba, no en Cnosos.
- No mostrar en pantalla la clave del panel (`?clave=`), las llaves de Groq o Gemini, ni la contraseña de Oracle. La barra de direcciones queda oculta con F11.
- Si se presenta el video en vez de la demo en vivo, se avisa: «Esto es una grabación de hoy».

## Si se hace en vivo

El mismo guion. Si Groq responde, se puede cambiar el Minotauro a `groq` en el paso de 0:35. Si sale un 429, se vuelve a `guion` y se dice por qué. El video queda abierto en otra pestaña, listo para reproducir.
