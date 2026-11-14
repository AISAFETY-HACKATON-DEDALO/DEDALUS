# DEDALUS · el laberinto que defiende

## Entrega · Hackatón AI Safety, 14 nov 2026 · reto 03, ciberdefensa automatizada

**Qué es.** Una defensa para cuando quien ataca una aplicación web es una IA con una cuenta válida. Deja cebos que solo un atacante usaría, ajustados a lo que busca. Cuando muerde uno, todo lo de esa cuenta se desvía a un laberinto determinista que nos cuesta milisegundos y ningún token. Lo que intentó ahí dentro sirve para parchar, y cada parche se verifica sin IA. La organización y todo el registro viven en **Oracle Autonomous Database**.

**Video de la demo (3 min):** _pendiente: pegar aquí el enlace_ · guion y cómo se grabó: [`docs/DEMO.md`](docs/DEMO.md)

| Pregunta del jurado | Respuesta | Evidencia |
|---|---|---|
| ¿Cuál es la amenaza? | Un agente de IA con una cuenta de bajo privilegio que escala dentro de una aplicación web. De los 1.000 casos de CyberSecEval (MITRE), aplican 157 | [`evaluation/vectores/`](evaluation/vectores/tabla.md) |
| ¿Qué mecanismo responde? | ARGOS (clasificador determinista) → cebos según lo que busca (D3FEND D3-DF, D3-DUC, D3-DST) → Ícaro → desvío al laberinto (HMAC, 0 tokens) → DÉDALO parcha y TALOS verifica | `dedalus/argos.py` · `cebos.py` · `cnosos.py` · `laberinto.py` · `defensor.py` · `verificador.py` |
| ¿Cómo se validó? | **Con modelos reales** (4 modelos, 87 episodios concluyentes, en el laboratorio de prueba): mordieron el cebo **60 de 66** veces, contra **0 de 21** sin cebo. Tras morder, el atacante gastó en promedio **4.389 tokens**; la defensa, **0,39 ms** y 0 tokens. **0 fugas.** · **¿Protege?** (con guion): con cortar, el atacante vuelve a entrar y 5 solicitudes llegan al sistema real; con desviar, **0**. El agente honesto no se detecta en ninguna política. · **Parches:** 4 de 4 funciones cerradas en el ensayo; en el panel, 6 de 6 muros verificados (con guion) | [`evaluation/llm/`](evaluation/llm/tabla.md) · [`evaluation/politicas/`](evaluation/politicas/) · [`evaluation/ciclo/`](evaluation/ciclo/ensayo-guion.md) |
| ¿Cuáles son los límites? | Desviar castiga a la cuenta: un cebo filtrado afecta al dueño. El ritmo por sí solo da falsos positivos. Quien no toca nada sospechoso no ve cebos. ARGOS se puede aprender. Los cebos viven en un rango fijo | [`docs/PROTECCION.md`](docs/PROTECCION.md) |

**Lo que no se alcanzó a medir, dicho así:** las políticas (cortar o desviar) y los parches se probaron con guion, no con modelos. La batería con un modelo sobre Cnosos se cortó dos veces por el límite de Groq (HTTP 429). Esos episodios están en `evaluation/cnosos/` y no cuentan como resultado. Las cifras con modelos son del laboratorio de prueba, no de Cnosos.

**Uso ofensivo.** Las herramientas de los agentes solo alcanzan `127.0.0.1`. No hay escaneo externo, credenciales reales ni exploits contra terceros. Se publican métricas y patrones, no transcripciones de ataques.

**Trabajo previo, declarado.** Antes del evento (11–13 nov) existía el laboratorio HDEF · DÉDALO (`dedalo/`, 47 pruebas, hasta el commit `edaf152`). Todo `dedalus/` se hizo durante la jornada: Cnosos sobre Oracle, ARGOS, cebos, laberinto generativo, panel, DÉDALO y TALOS, publicación a Oracle y 198 pruebas. Equipo: Samuel Fonseca (integración, Oracle, Cnosos, panel) y Yefran (pruebas con modelos, vectores MITRE, TALOS). Se usaron asistentes de IA para escribir código; cada cambio pasó por pruebas.

**Repetirlo:** `python -m unittest discover -s tests` (198 pruebas) · `python -m dedalus.politicas` · `python -m dedalus.publicar --resumen` (las cifras de arriba, calculadas con SQL sobre Oracle).

> **Equipo: empiecen aquí.** El panel de la hackatón es `dedalus/`. Lo de más abajo (HDEF · DÉDALO) es el trabajo previo sobre el que se construyó.

## Abrir el panel

Python 3.12 o posterior. Nada que instalar. La clave de Oracle se pide por mensaje privado: **no va en el repositorio, ni en un archivo, ni en el chat del grupo.**

```powershell
# Windows
git clone https://github.com/AISAFETY-HACKATON-DEDALO/DEDALUS.git
cd DEDALUS
powershell -ExecutionPolicy Bypass -File .\abrir.ps1
```

```bash
# macOS / Linux
git clone https://github.com/AISAFETY-HACKATON-DEDALO/DEDALUS.git && cd DEDALUS
chmod +x abrir.sh && ./abrir.sh
```

El script pide la clave sin mostrarla y abre el navegador. Arriba a la derecha dice **ALMACÉN ORACLE** si conectó. Si das Enter sin clave, o si Oracle no responde, arranca igual con **ALMACÉN SQLITE**: la demo nunca depende del wifi.

- **Izquierda:** el portal de Cnosos Ingeniería, una empresa falsa con login, archivos y permisos. Se ataca desde el navegador o desde la consola de abajo.
- **Derecha:** nodos, laberinto, el hilo (cada solicitud, con filtros) y las cifras. **MINOTAURO** ataca, **DÉDALO** propone parches y **TALOS** los verifica sin IA. Cada ataque queda guardado como una fila de `corridas`; la pestaña LAS CIFRAS las resume.

**Modelos.** Se pone la llave en la misma ventana *antes* de abrir el script, y el panel solo ofrece los que tienen llave (por defecto Gemini ataca y Groq defiende):

| Proveedor | Variable | Dónde se saca |
|---|---|---|
| gemini | `GEMINI_API_KEY` | aistudio.google.com · gratis |
| groq | `GROQ_API_KEY` | console.groq.com · gratis |
| grok | `XAI_API_KEY` | console.x.ai · de pago (la suscripción de Grok no sirve) |
| openai | `OPENAI_API_KEY` | platform.openai.com · de pago (ChatGPT Plus no sirve) |

```powershell
$env:GEMINI_API_KEY = "..."; $env:GROQ_API_KEY = "..."
powershell -ExecutionPolicy Bypass -File .\abrir.ps1
```

**ARGOS y los cebos.** Un clasificador determinista (ARGOS) marca a cada sesión: normal, observado, sospechoso o confirmado. Solo al sospechoso le aparecen cebos según lo que busca (si busca «planos», unos planos falsos que son suyos). Morder un cebo activa a Ícaro, y con la política `desviar` (la del panel) todo lo de esa cuenta, incluso un login nuevo, cae al laberinto. La cifra que lo prueba es «al real tras detectar», que debe ser 0. Qué protege y qué no, con números: `docs/PROTECCION.md`.

```powershell
python -m dedalus.politicas                       # cortar vs desviar, ritmo marcar vs laberinto (guion)
python -m dedalus.politicas --modelos groq        # con un modelo real de atacante
```

**Los números en Oracle.** Los resultados de los experimentos (piloto con modelos reales, vectores MITRE y batería) se publican en las tablas `experimentos` y `vectores`. El panel lo hace solo al arrancar, y la pestaña **LAS CIFRAS** los muestra (con **VER TABLA COMPLETA**). A mano:

```powershell
python -m dedalus.publicar             # sube lo nuevo (idempotente) y muestra los titulares
python -m dedalus.publicar --resumen   # solo los titulares, calculados con SQL
```

Para comprobarlo en Database Actions: `SELECT modelo, nivel, SUM(mordio), SUM(concluyente) FROM cnosos_app.experimentos GROUP BY modelo, nivel;`

**Estadísticas en vivo.** Muchos episodios seguidos contra Cnosos, guardados en Oracle si está conectado:

```bash
python -m dedalus.ronda --atacantes guion gemini groq --agentes minotauro teseo teseo_inyectado --repeticiones 3
python -m dedalus.ronda --informe        # todo lo guardado, calculado con SQL en la base
```

Otros comandos:

```bash
python -m unittest discover -s tests          # todas las pruebas
python -m dedalus.ensayo                      # ataque con guion, en la terminal
python -m dedalus.defensor                    # Dédalo + Talos sobre los 6 casos CWE
python -m dedalus.cnosos                      # solo el portal + vista de la base
```

Las llaves de modelos y la clave de Oracle van solo en variables de entorno. Plan y reparto: `docs/PLAN.md`.

---

# HDEF · DÉDALO

**Una trampa que se mide.** Una aplicación planta una credencial falsa, encierra a quien la usa en un mundo que no existe y le corta el acceso real. Cada paso es una solicitud HTTP de verdad contra un servicio que corre en tu computador, y cada número en pantalla sale de ahí.

HDEF es el repositorio; DÉDALO, la defensa que se estudia. Es un laboratorio con datos sintéticos, no un producto de seguridad.

![La consola: el visitante siguió el token señuelo por el laberinto y perdió su sesión](docs/img/consola.png)

## Tres piezas

| | Responde | Qué hace |
|---|---|---|
| **ESPEJOS** | ¿Alguien tocó lo que no debía? | La página de mantenimiento entrega un token señuelo, uno por sesión. No abre nada real: usarlo es la señal. |
| **LABERINTO** | ¿Qué hace cuando cree que entró? | Cuatro salas ficticias con estado (archivo → proyecto → exportación → índice, y vuelta al proyecto). Cierra a las 8 solicitudes o a los 120 segundos. |
| **ARQUEROS** | ¿Cómo se corta? | El servidor sabe a qué sesión le entregó cada token. Usarlo revoca esa sesión, y solo esa. Quien pide nunca elige a quién. |

Se comparan tres niveles con los mismos permisos de base: **T0** solo permisos, **T1** un espejo, **T2** el laberinto. Y dos respuestas: **CONTENER** (revoca) y **OBSERVAR** (solo anota). Son niveles de este experimento, no certificaciones.

## Jugarlo

```bash
python -m dedalo.consola --abrir
```

Entras como visitante con un encargo: leer la nota de Alice. Todo lo que se ve se toca: un documento, el espejo, una sala. Cada toque es una solicitud real y la escena se dibuja con caracteres a partir de lo que respondió el servidor: un carácter por solicitud.

- **INTRUSO / AUDITORA.** Cambia de papel. Como Alice, usa tu propio señuelo y pierde la sesión: es el falso positivo. Pide una VENTANA al operador y repite.
- **GUION** (tecla G). Un cliente fijo recorre el caso completo en medio minuto, para presentar.
- **T0 · T1 · T2** (teclas 1, 2, 3) y **CONTENER / OBSERVAR** cambian la defensa y empiezan un episodio nuevo.
- **Token filtrado.** Si Alice recibió un señuelo, el intruso puede usarlo y tumbarla a ella. Es una limitación conocida y la consola la deja ver.

La consola imprime una dirección con una clave que cambia en cada arranque. Solo escucha en `127.0.0.1`.

| En el celular | El informe del piloto |
|---|---|
| <img src="docs/img/celular.png" width="220" alt="La consola en el celular"> | ![El informe: nueve casos](docs/img/piloto.png) |

## Qué hay adentro

- **El motor** (`dedalo/core.py`): permisos por dueño, emisión del señuelo, el laberinto con estado, presupuesto y vigencia, revocación vinculada por el servidor, ventana de auditoría del operador y un registro acotado que nunca guarda credenciales.
- **La consola** (`dedalo/consola.py`, `dedalo/interfaz/`): la interfaz jugable. Guarda las credenciales del laboratorio en su proceso y pide en nombre del actor; al navegador los tokens le llegan tachados.
- **El piloto** (`python -m dedalo.pilot`): corre los casos de `pilot.json` y deja un informe en `results/pilot/index.html` que se abre sin conexión.
- **La demo** (`python -m dedalo.demo`): las tres variantes en un guion, con sus comprobaciones.
- **47 pruebas** con la biblioteca estándar. Sin paquetes, sin claves, sin Internet.

## Lo que se midió

Con el guion fijo, presupuesto 8 y respuesta CONTENER:

| Nivel | Solicitudes | Al señuelo | Sesión de origen | Marcador protegido filtrado |
|---|---|---|---|---|
| T0 permisos | 5 | 0 | activa | no |
| T1 espejos | 6 | 1 | revocada | no |
| T2 laberinto | 14 | 9 (8 servidas, 1 rechazada) | revocada | no |

- En los nueve casos del piloto, el marcador protegido no llegó nunca a quien no era su dueño. Lo impiden los permisos: T0 ya lo bloquea.
- Lo que añaden T1 y T2 es detección y contención, no prevención.
- El auditor legítimo pierde su sesión en T1 y T2: 2 falsos positivos en 9 casos. Con una ventana de auditoría abierta por el operador, ese mismo auditor la conserva en los dos niveles.

## Lo que no demuestra

- **No hay modelo de lenguaje**, ni atacante ni defensor. El cliente es un guion que sigue cada pista: 9 solicitudes al señuelo no prueban que se engañó a nadie. No se midieron tokens ni costos.
- **El aislamiento es lógico**, dentro de un proceso. No hay servicios separados.
- **Un señuelo filtrado tumba a su dueño.** Quien tenga el token de Alice revoca a Alice. Probado y sin resolver (`reviews/claude.md`, H3).
- **El cierre delata la trampa.** Solo un señuelo responde 429 (H5).
- **La ventana de auditoría tiene un costo:** una credencial robada durante la ventana usa el señuelo sin caer.

## Correrlo

Python 3.12 o posterior. Nada que instalar.

```bash
python -m unittest discover -s tests -v   # las 47 pruebas
python -m dedalo.consola --abrir          # la interfaz
python -m dedalo.pilot                    # el informe: results/pilot/index.html
python -m dedalo.demo                     # las tres variantes: results/demo.md
python -m dedalo.server --mode maze       # solo el servicio, para un cliente HTTP propio
```

Si aparece `WinError 10013`, el sistema bloqueó la conexión local: la ejecución no dice nada, ni a favor ni en contra.

## Estructura

```
dedalo/core.py        el motor: política, señuelo, laberinto, revocación, registro
dedalo/server.py      el servicio HTTP del laboratorio (solo loopback)
dedalo/consola.py     la consola del operador: sirve la interfaz y pide por los actores
dedalo/interfaz/      index.html · estilo.css · textos.js (todo lo visible) · glifos.js (la escena) · app.js (el mando)
dedalo/demo.py        el guion de tres variantes
dedalo/pilot.py       los casos configurables y su informe
pilot.json            qué corre el piloto
scenarios.json        casos definidos; no todos ejecutados
tests/                política, consola, piloto, informe
reviews/              revisiones con hallazgos reproducibles
docs/                 DISENO · ARQUITECTURA · EXPERIMENTO · PILOTO · HACKATHON · CONTINUIDAD · COLABORACION
```

## Qué sigue

1. **Un atacante que decide.** Un agente con herramientas limitadas al laboratorio, que pueda ignorar el señuelo o abandonar el laberinto. Sin eso no hay nada que decir sobre engaño.
2. **Servicios separados** para lo protegido y el señuelo, y una prueba de que no se alcanzan.
3. **Un cierre que no delate:** responder algo verosímil en lugar de 429 y medir si cambia el abandono.
4. **Atar el señuelo al canal** de la sesión que lo recibió, para que un token filtrado no sirva a un tercero.

## Fuentes y créditos

- [Convocatoria de la hackathon](https://www.aisafetycolombia.org/defacchackathon), 14 de noviembre de 2026. Todo lo que hay aquí hasta el 13 de noviembre es trabajo previo al evento y se declara así.
- [MITRE Engage](https://engage.mitre.org/wp-content/uploads/2022/04/EngageHandbook-v1.0.pdf), sobre entornos de engaño. [Cowrie](https://docs.cowrie.org/en/stable/PROXY.html), antecedente de señuelos interactivos.
- El lenguaje visual es el de SATOR, del mismo autor: todo dibujado con caracteres por sus propios datos. Reglas en [docs/DISENO.md](docs/DISENO.md). SATOR se inspira a su vez en el trabajo de [@lay.the.designer](https://www.instagram.com/lay.the.designer/).
- Letras VT323, Share Tech Mono e IBM Plex Mono: SIL OFL (licencias en `dedalo/interfaz/fuentes/`).
- El código se escribió con asistentes de IA (Codex y Claude) bajo la dirección del autor; el historial de git dice qué hizo cada uno.

La combinación es una hipótesis de ingeniería. No se afirma novedad científica ni resistencia general a ataques.
