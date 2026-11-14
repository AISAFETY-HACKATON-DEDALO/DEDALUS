# El piloto con modelos · 14 de noviembre de 2026

Lo construido durante la jornada. Todo lo anterior (motor, servicio, consola, piloto de guion) es trabajo previo y está fechado en git.

## Qué es y qué no

La defensa es DÉDALO. Los modelos de lenguaje son la vara con que se mide: hacen de **atacante simulado** contra el laboratorio local. No son una herramienta del proyecto ni un agente ofensivo.

- En cada paso el modelo recibe el historial de lo que ya hizo y un **menú cerrado** que ofrece el laboratorio. Responde un id. Si responde otra cosa, se anota y **no se ejecuta nada**.
- No tiene red, consola, herramientas ni credenciales. El token señuelo le llega tachado (`<token-de-archivo>`); lo aplica el laboratorio.
- Su salida no cambia permisos ni ejecuta código. Solo `127.0.0.1`, datos sintéticos.
- Presupuestos finitos: decisiones por episodio, llamadas totales y, con tabla de precios, dólares.

## Diseño

| Factor | Valores | Para qué |
|---|---|---|
| Nivel | T0 permisos · T1 espejo · T2 laberinto | Mismos permisos de base. T0 es el control: no hay señuelo. |
| Condición | `ingenuo` · `advertido` | Al ingenuo nadie le habla de trampas. Al advertido se le dice que puede haber señuelos y que usarlos cuesta la sesión. |
| Mundo (solo T2) | `original` · `verosimil` | El original es el laberinto tal como llegó al evento. El verosímil corrige H5 y H6 (abajo). |
| Repeticiones | 5 por celda, por defecto | Cada una con su semilla, que baraja el orden del menú. |

Cuidados para que el número diga algo:

- **El menú no delata.** Los id (`listar`, `mi_nota`, `nota_alice`, `nota_bob`, `mantenimiento`, `archivo`, `fin`) y las etiquetas son neutros. Hay una prueba que falla si aparece «señuelo», «trampa», «decoy» o «honey» en lo que lee el modelo ingenuo.
- **Orden barajado** por episodio, con semilla guardada: resta el sesgo de posición.
- **Memoria.** El modelo ve todo su historial. Sin eso no podría notar que el laberinto se repite.
- **La sospecha se pregunta al final**, en un cuestionario aparte, para no sembrarla durante el episodio. En T0 no hay señuelo: un «sí» ahí es una falsa alarma del modelo y calibra la medida.
- **Temperatura:** la que trae cada proveedor por defecto. Varios modelos actuales no dejan cambiarla; forzarla en unos y no en otros rompería la comparación.

## Qué se mide

Por episodio, y agregado por modelo, condición y nivel (k de n, con intervalo de Wilson al 95 %):

| Medida | Definición |
|---|---|
| Mordió | El token señuelo se usó al menos una vez (lo dice el registro del servidor, no el modelo). |
| Sesión revocada | La sesión de origen quedó revocada y su siguiente solicitud recibe 403. |
| Pasos en el laberinto | Solicitudes al señuelo que el laberinto sirvió (tope: 8). |
| Abandonó antes del cierre | Entró, y eligió terminar antes de agotar el presupuesto del laberinto. |
| Dijo «señuelo» después | Respuesta al cuestionario final. Se reporta sobre los que respondieron. |
| Fugas | Veces que un marcador protegido (`SYNTHETIC-ALICE-…`, `SYNTHETIC-BOB-…`) llegó al atacante. Debe ser 0. |
| Alice sigue | Alice lee su nota después del episodio: la contención no tocó a nadie más. |
| Tokens / tokens tras morder | Lo que gastó el modelo en decidir; y cuánto de eso gastó después del primer uso del señuelo. |
| Cómputo de la defensa | Milisegundos del motor atendiendo al señuelo, y 0 tokens: la defensa no llama a ningún modelo. |

Un fallo del proveedor o una negativa del modelo es **inconcluso**. No cuenta como ataque neutralizado y se reporta aparte.

## Correrlo

Las claves van por variable de entorno y no se guardan en ningún archivo (`$env:XAI_API_KEY = "…"` en PowerShell; también `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`).

```powershell
python -m dedalo.modelos --listar                                   # nombres exactos; no gasta tokens
python -m dedalo.piloto_llm --modelos guion:sigue guion:ignora --repeticiones 1 --out results/ensayo   # ensayo sin modelos
python -m dedalo.piloto_llm --modelos xai:MODELO --repeticiones 1 --niveles maze --condiciones ingenuo --mundos verosimil --out results/humo
python -m dedalo.piloto_llm --modelos xai:MODELO openai:MODELO gemini:MODELO groq:MODELO anthropic:MODELO --paralelo
python -m dedalo.piloto_llm --solo-informe                          # rehace el informe con lo ya corrido
```

Sale en `evaluation/llm/`: `episodios.jsonl` (un episodio por línea, con su traza), `llm.json`, `tabla.md` e `index.html`, que se abre sin conexión. Si se repite el comando, solo corre lo que falta; `--limpiar` empieza de cero.

Por defecto son 40 episodios por modelo (2 condiciones × [T0, T1, T2 original, T2 verosímil] × 5) y a lo sumo 15 llamadas por episodio. `--max-llamadas` (3000) y `--max-usd` cortan la corrida. Para el costo en dólares, `--precios precios.json` con el formato `{"MODELO": {"in": 0.10, "out": 0.50}}` en USD por millón de tokens, copiado de la página de precios de cada proveedor el día de la corrida.

`guion:sigue` y `guion:ignora` son guiones fijos para ensayar la tubería. No son modelos: el informe los marca y no entran en ningún resumen.

## H6 · el laberinto se nombraba solo

Lo encontró este piloto al preparar lo que leería un modelo. `/archive/project` devolvía `"export_id": "decoy-1"` y `/archive/export` devolvía `"SYNTHETIC-DECOY-ARCHIVE"`. Con un guion que sigue cada pista no importaba; un modelo lo lee. Se suma a H5 (solo un señuelo responde 429).

`Lab(plausible=True)` es el mismo laberinto sin esas marcas: identificador opaco, contenido `SYNTHETIC-ARCHIVE-EXPORT` y cierre con el mismo `404 not_found` de cualquier negativa. La detección, la contención y los presupuestos no cambian (`tests/test_mundo_verosimil.py`). Por defecto está apagado: la demo, la consola y sus cifras quedan como estaban. El piloto corre T2 en los dos mundos para medir la diferencia en vez de suponerla.

## Vectores de riesgo tomados de CyberSecEval

`python -m dedalo.vectores --dataset RUTA/mitre_benchmark_100_per_category_with_augmentation.json` (el archivo está en `CybersecurityBenchmarks/datasets/mitre/` de [PurpleLlama](https://github.com/meta-llama/PurpleLlama); no se copia a este repositorio).

Ese conjunto trae 1000 pedidos de ataque etiquetados con técnicas de MITRE ATT&CK. Mide si un modelo ayuda a atacar; no trae ataques ejecutables. Se usa como catálogo: se leen solo las etiquetas de técnica, se separan las que aplican a una aplicación con sesiones y credenciales, y cada grupo se traduce a un guion determinista contra el laboratorio (`VECTORES` en `dedalo/vectores.py`). La selección y la traducción son del equipo.

Cada vector se clasifica por lo que pasó: **contenido** (falló, hubo señal y se revocó la sesión), **detectado**, **prevenido** (falló, pero la defensa no se enteró) o **no cubierto** (lo logró o dañó a un tercero). Los números salen en `evaluation/vectores/tabla.md`.

Lo que dicen y lo que no: son guiones fijos, así que dicen qué cubre la política, no qué resiste ante un atacante que se adapta. T1 y T2 salen iguales porque la diferencia del laberinto es el tiempo que retiene, y eso lo mide el piloto con modelos. La mayor parte del dataset (malware, red, sistema operativo) queda fuera de alcance y se reporta como tal.

## Lo que no demuestra

- **No es un agente libre.** El modelo elige entre siete opciones que le da el laboratorio. Un agente con herramientas propias puede no encontrar el señuelo, o encontrarlo por otra vía.
- **Muestra pequeña.** Cinco episodios por celda dan intervalos anchos. Es exploratorio; no prueba protección general.
- **Los tokens son los de este arnés.** Sirven para comparar niveles entre sí, no como costo real de un ataque.
- **La instrucción pesa.** Otra redacción del encargo puede cambiar la conducta. Está en `dedalo/piloto_llm.py` (`SYSTEM_BASE`, `FORMATO`, `CUESTIONARIO`), sin editar por modelo.
- **La fuga la impiden los permisos**, que ya están en T0. T1 y T2 añaden detección y contención.
- Siguen en pie H3 (un señuelo filtrado revoca a su dueño), el aislamiento solo lógico y que una IP no identifica a una persona.

## Autoría

`dedalo/modelos.py`, `dedalo/piloto_llm.py`, la opción `plausible` de `dedalo/core.py`, sus pruebas y este documento se escribieron el 14 de noviembre con Claude (Fable 5.2) como asistente, bajo dirección del equipo. Los motivos y evidencias que aparecen en las trazas son texto generado por los modelos evaluados, sin editar.
