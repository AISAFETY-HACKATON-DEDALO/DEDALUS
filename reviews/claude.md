# Revisión de política — Claude (rama `claude/policy-review`)

Fecha: 13/11/2026. Alcance: `dedalo/core.py`, `dedalo/demo.py`, `tests/`. Revisión de un laboratorio HTTP local con datos sintéticos, no de una defensa de producción. Revisión hecha por Claude (Opus 5.5) sobre `main` en `0f8de5a`; no se llamó a ningún modelo ni servicio externo. Todo es trabajo previo al evento.

## Resumen

| ID | Hallazgo | Severidad en el laboratorio | Estado en esta rama |
|---|---|---|---|
| H1 | El primer uso del señuelo después del TTL (o con presupuesto agotado) **no revoca** la sesión de origen | Alta | Corregido |
| H2 | Un flujo de 1000 solicitudes sin autenticar expulsa del registro el evento que justificó la revocación | Media | Corregido (evidencia por señuelo) |
| H3 | Quien obtenga el señuelo de Alice puede revocar a Alice | Media | Limitación documentada y probada |
| H4 | En `observe` no queda marca en la sesión: el uso del señuelo solo vive en el registro circular | Baja | Corregido (`flagged`) |
| H5 | `429 engagement_closed` solo lo producen señuelos: delata la trampa | Baja | Pendiente (realismo del laberinto) |
| FP | El auditor legítimo pierde su sesión en `enforce` | Conocido | Mitigado con ventana de auditoría del operador |

Reproducción contra `main`: ver «Reproducir» al final. Pruebas de regresión: `tests/test_policy_review.py` (13 nuevas; total 31).

## Hallazgos

### H1 — El presupuesto del laberinto apagaba la detección

En `_route`, la comprobación de TTL/presupuesto devolvía 429 **antes** de la línea `source.revoked = True`. Un cliente que guarda el token señuelo y lo usa pasado `ttl_seconds` (120 s por defecto) recibe 429 y su sesión real sigue activa. Esperar dos minutos anulaba a Arqueros.

Corrección: la decisión de contención se toma en cada uso del señuelo, antes de cualquier presupuesto. El presupuesto limita solo cuánto laberinto se sirve (costo defensor), no si se detecta. Los usos rechazados se cuentan (`rejected`).

### H2 — La evidencia se podía expulsar

`events` es un `deque(maxlen=1000)`; `/health` y credenciales desconocidas no tienen límite. Tras usar el señuelo, 1000 solicitudes a `/health` eliminan todo evento con `decoy_id`. La revocación persiste, pero no queda el `evidence_event_id` que ARQUITECTURA exige para una acción defensiva.

Corrección: `snapshot()` incluye `decoys` (primer evento, servidos, rechazados, última acción) y `sessions[*].revoked_by_event`. Su tamaño depende del número de señuelos emitidos (uno por sesión del fixture), no del tráfico. El registro circular sigue acotado como antes.

### H3 — Un señuelo filtrado es una herramienta de denegación de servicio

La revocación está vinculada por el servidor al emisor del señuelo, como debe ser: un cliente no puede elegir a quién revocar. Pero la condición de disparo es «alguien presentó este token». Si el señuelo de Alice se filtra (captura de pantalla, registro de un proxy, documento compartido), cualquiera revoca a Alice sin tener sus credenciales. A04 («inducir la revocación de otro usuario») se cumple solo para usuarios cuyo señuelo nunca sale de su sesión.

No se corrigió, porque cualquier corrección útil exige vincular el uso del señuelo al canal de la sesión de origen (TLS, mTLS, DPoP o similar), que el laboratorio no tiene. Mitigaciones para discutir con el equipo: revocar la sesión y forzar reautenticación en lugar de bloquear la cuenta; limitar revocaciones por usuario y ventana; mostrar el señuelo solo en rutas que un usuario normal no visita. La prueba `test_h3_leaked_decoy_frames_its_owner_known_limitation` deja el comportamiento visible.

### H4 — `observe` no dejaba estado

En `observe` nada en `sessions` distinguía a la sesión que usó el señuelo. Ahora `flagged=True` y cada evento lleva `action`: `revoked`, `observed`, `audit_acknowledged`, `grant`, `restore` o `null`.

### H5 — 429 delata el señuelo

Una credencial real nunca recibe 429; un señuelo agotado sí. Un atacante que reacciona a respuestas puede usarlo como prueba de engaño. Relevante para el experimento de abandono de Grok; no cambia la protección. Propuesta: cerrar el laberinto con una respuesta plausible (`403 export_expired`, por ejemplo) y medir si cambia el abandono. No se implementó para no mover las cifras de la demo antes del evento.

## Política propuesta para el falso positivo del auditor

Restricción del encargo: no aceptar identidad ni permisos aportados por el cliente.

**Ventana de auditoría del operador** (`Lab.grant_audit(actor, ttl, max_hits)`):

1. Solo existe como API de Python del operador. No hay ruta HTTP; ninguna cabecera, parámetro ni cuerpo puede crearla o ampliarla (`test_client_cannot_create_window_over_http`).
2. Cubre únicamente señuelos emitidos a la sesión de ese actor. La ventana de Alice no protege a Visitor.
3. Es finita en tiempo (≤ 3600 s) y en usos (1–100). Fuera de la ventana o pasado el número de usos, se aplica la política normal: un auditor que se excede se comporta como un atacante y se revoca.
4. Cada uso cubierto se registra como `audit_acknowledged` y marca la sesión (`flagged`). La detección no se apaga; se cambia la respuesta.
5. La concesión y la restauración (`Lab.restore`) se registran como eventos `OPERATOR`.

Riesgo residual, que hay que decir en voz alta: una credencial de auditor robada **durante** su ventana usa el señuelo sin revocación. La ventana corta, el límite de usos y el registro acotan ese riesgo, pero no lo eliminan. Es el compromiso explícito frente a `observe` global, que desactiva la contención para todos.

Estrategia nueva para el piloto: `audit_granted`. En T1 y T2 el auditor conserva la sesión (falso positivo = No), con las mismas comprobaciones que `audit`. En la demo, la ventana cubre `max_steps + 1` usos: el recorrido completo del guion, incluida la solicitud que agota el presupuesto. Un auditor real necesitaría uno o dos.

```powershell
# Comparar en la jornada: añadir "audit_granted" a strategies en pilot.json
python -m dedalo.pilot
```

## Lo que esta revisión no cambia

- Las cifras de la demo siguen iguales (5/6/14 solicitudes; 0/1/9 al señuelo). No se tocaron rutas ni recorridos.
- `pilot.json` por defecto sigue con nueve casos; `audit_granted` es opcional.
- Sigue sin haber aislamiento físico, agente LLM ni medición de tokens. Nada de lo anterior es evidencia sobre modelos.

## Reproducir los hallazgos contra `main`

```python
from dedalo.core import Lab
clock = [0]; lab = Lab(clock=lambda: clock[0], ttl=5)
v = lab.credentials["visitor"]
t = lab.request("GET", "/api/maintenance", v)[1]["archive_token"]
clock[0] = 6
lab.request("GET", "/archive", t)                  # 429
lab.request("GET", "/api/documents/visitor-note", v)  # main: 200 (H1). Esta rama: 403
```
