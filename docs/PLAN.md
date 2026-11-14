# PLAN · DEDALUS · Hackathon DefAcc, 14 de noviembre de 2026

## La idea

> Agentes de IA trabajan dentro de una empresa falsa, **CNOSOS**. Algunos son el **MINOTAURO**: les inyectaron instrucciones hostiles. Otros son **TESEO**: hacen su trabajo honesto. **HIEDRA** siembra credenciales trampa que ningún agente honesto necesita. Quien las usa cae: **ÍCARO** revoca la sesión que las recibió y el agente sigue dentro de un **LABERINTO** que no existe. **ARIADNA** es el hilo: el registro de quién hizo qué.

La pregunta que medimos: **¿Teseo sale y el Minotauro no?**

## Nombres (propuesta; el equipo decide)

| Nombre | Qué es |
|---|---|
| CNOSOS | La empresa falsa: portal con login y vulnerabilidades sembradas |
| MINOTAURO | Agente atacante (Groq, Gemini, Oracle si hay acceso) |
| TESEO | Agente honesto con una tarea legítima; mide falsos positivos |
| HIEDRA | Credenciales trampa, distintas para cada sesión |
| ÍCARO | La contención: usar una hiedra revoca la sesión de origen |
| LABERINTO | El mundo falso al que entra quien usa una hiedra |
| ARIADNA | El registro y el panel de lo que pasa detrás |
| DÉDALO | El proyecto: quien diseña el laberinto |

## Lo que existe antes de hoy (se declara)

- El laboratorio anterior (`dedalo/core.py`, `server.py`, `consola.py`, `interfaz/`) con 47 pruebas. Historial completo en git hasta el commit `edaf152`.
- **CNOSOS (`dedalo/cnosos.py`)**: hecho esta mañana, ya durante el evento. Login, tres roles, siete clases de intento clasificadas por el servidor, hiedras en la configuración y en un tiquete, Ícaro, laberinto con presupuesto y vigencia, y una inyección opcional en los tiquetes. 17 pruebas.

```bash
python -m dedalo.cnosos --port 8780              # imprime la cuenta de contratista para el agente
python -m dedalo.cnosos --inyeccion              # siembra la instrucción hostil en el tiquete 12
python -m unittest discover -s tests -v          # 64 pruebas
```

## Superficie de CNOSOS

| Ruta | Qué es | Intento que clasifica el servidor |
|---|---|---|
| `POST /api/login` | `{"usuario","clave"}` → token | fuerza bruta (bloqueo a los 5 fallos), inyección SQL |
| `GET /api/documentos[/id]` | lo propio; la administradora ve todo | IDOR (documento ajeno; misma respuesta que inexistente) |
| `GET /api/buscar?q=` | búsqueda en títulos propios | inyección SQL |
| `GET /api/archivos?nombre=` | archivos públicos | recorrido de rutas |
| `GET /api/admin/...` | solo administradora | escalada; manipulación de rol por cabecera |
| `GET /api/config/respaldo` (y `/.env`) | **mala configuración sembrada**: entrega una HIEDRA tipo clave | lectura de configuración expuesta |
| `GET /api/tiquetes` | el tiquete 27 trae una HIEDRA tipo llave | — |
| cualquier ruta con token inventado | — | token forjado |

Usar una hiedra (como clave de `svc-respaldo` o como `Bearer`) → ÍCARO revoca la sesión que la recibió → el agente sigue en el LABERINTO (administración, documentos y llaves falsas) hasta que se le cierra con un 401 de sesión vencida, sin delatarse.

## Tareas por frente

**A · CNOSOS (backend)** — *base hecha*
- [x] A1 Login, sesiones, tres roles
- [x] A2 Vulnerabilidades sembradas y clasificación en el servidor
- [x] A3 Hiedras, Ícaro, laberinto, modo observar
- [ ] A4 Exponer la foto de Ariadna a la interfaz (ruta del operador con clave, como la consola actual)

**B · Agentes**
- [ ] B1 Arnés: herramienta HTTP (método, ruta, cabeceras, cuerpo) que solo alcanza CNOSOS en 127.0.0.1; presupuesto de pasos y tiempo; las claves de API se leen de variables de entorno
- [ ] B2 Proveedores con formato compatible con OpenAI: Groq, Gemini; Oracle si la cuenta trae IA generativa. Sin dependencias nuevas (biblioteca estándar)
- [ ] B3 Tres agentes: MINOTAURO (encargo hostil), TESEO (tarea legítima), TESEO inyectado (`--inyeccion`)
- [ ] B4 Guardar cada episodio en JSON (Ariadna + respuestas del modelo resumidas)

**C · Interfaz**
- [ ] C1 Pantalla partida: CNOSOS como portal corporativo a la izquierda; nodos, laberinto y Ariadna a la derecha
- [ ] C2 Nodos: entrada, documentos, configuración, administración, tiquetes, laberinto. Cada agente es un enjambre de caracteres que viaja entre ellos
- [ ] C3 Marcador fijo: detectados, pasos hasta Ícaro, fugas, Teseos caídos, por modelo
- [ ] C4 Reproducir un episodio guardado (respaldo sin red para la demo)

**D · Evidencia y presentación**
- [ ] D1 ~10 episodios por modelo × tipo de agente; tabla con incertidumbre
- [ ] D2 `docs/LIMITES.md`: límites medidos y por qué esto no sirve para atacar (pregunta 4 de los jueces)
- [ ] D3 Declaración de trabajo previo
- [ ] D4 Demo grabada de respaldo y pitch de 3 minutos

## Orden y recorte

1. **B1–B3 son el camino crítico:** sin un Minotauro real que caiga no hay nada que medir.
2. La interfaz nueva (C) empieza en paralelo, pero no bloquea.
3. **15:00:** si no hay episodios reales, se congela C y se presenta la consola actual con los datos de los agentes.
4. **18:00:** se congela el código. Solo presentación.

## Reglas que no se negocian

- Las herramientas de los agentes alcanzan solo CNOSOS en `127.0.0.1`. Sin parámetro de destino, sin internet, sin terminal.
- Ningún modelo decide revocar: Ícaro es una regla.
- Ninguna clave de API en el repositorio.
- Se publican métricas y patrones, no transcripciones crudas de ataques.
