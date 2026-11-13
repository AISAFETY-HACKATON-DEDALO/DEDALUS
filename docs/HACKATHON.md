# Preparación y colaboración

## Qué está confirmado y qué falta

La convocatoria consultada el 11/11/2026 anuncia equipos de 2–4 personas, formación de equipos para quienes se postulen solos a las 8:30 y ocho horas de construcción/evaluación. La jornada completa es de 8:00 a 20:00 del sábado 14. No se encontró una norma explícita sobre trabajo previo en el contenido accesible. Postulación enviada; respuesta pendiente.

No es necesario asumir que debes llevar un producto terminado. Recomendación: llegar con una propuesta explicable, arquitectura, escenarios y un entorno que sepas usar. Si permiten código previo, declarar qué existía antes y qué construyó el equipo durante la jornada.

## Consulta a organización, lista para copiar y NO enviada

Hola. Ya envié mi postulación. Estoy preparando una propuesta de ciberdefensa con credenciales señuelo y un entorno aislado. ¿Podemos llevar arquitectura, escenarios y código base preparado antes de la jornada? ¿Qué parte del desarrollo debe hacerse durante el evento y cómo debemos declarar componentes previos? También quisiera confirmar cómo se acuerdan los proyectos al formar equipos de participantes individuales. Gracias.

## Antes del evento

- Aprender y poder explicar autenticación, autorización, sesiones, señuelos y aislamiento.
- Acordar el alcance permitido de preparación con organización cuando respondan.
- Instalar y comprobar herramientas de trabajo; evitar depender de instalaciones largas el sábado.
- Preparar tareas benignas, objetivos adversarios y política esperada.
- Si se autoriza una base previa, llevar un hito pequeño ejecutable con fecha y estado claramente documentados.
- Preparar un respaldo sin API; identificarlo como prueba de integración y no como agente IA.

## Entrada al equipo

Presentar DÉDALO en dos minutos: problema, demostración mínima, experimento y piezas abiertas. Proponerlo, no dar por hecho que el equipo lo adoptará. Los compañeros deberían poder influir en arquitectura, evaluación y diseño, no solo terminar tareas ya decididas.

Las decisiones que quedan abiertas: escenario de aplicación, proveedor/modelo, selección de trampas, visualización, prioridad de adaptación y reparto de tareas.

## Jornada de ocho horas — estimación, no agenda oficial

| Tramo | Entregable y decisión |
|---|---|
| 0:00–0:30 | Acordar proyecto y permisos; repartir responsabilidades; fijar criterio de éxito. |
| 0:30–2:00 | Aplicación y autorización; usuario legítimo y acceso prohibido comprobados. |
| 2:00–3:30 | Un token señuelo, estado ficticio y eventos; primer recorrido completo. |
| 3:30–5:00 | Contención y control benigno; primer resultado independiente. |
| 5:00–6:15 | Comparaciones; integrar un atacante LLM si la base ya funciona. |
| 6:15–7:00 | Selección adaptativa solo si hay tiempo y evidencia previa. Congelar alcance. |
| 7:00–8:00 | Resultados, límites, demo y README de ejecución. |

Con dos personas: infraestructura/contención y escenarios/evaluación; ambos revisan integración y presentación. Con tres: separar señuelos y panel. Con cuatro: separar integración del agente y análisis. Estas son tareas para personas del equipo, no agentes automáticos.

Regla de recorte: si no hay flujo completo a mitad de jornada, retirar adaptación IA y priorizar aislamiento, contención y evaluación. Si el evento exige un componente IA, priorizar un atacante LLM acotado para evaluar la defensa y explicitar el papel real de la IA.

## Demo de tres minutos propuesta

1. Usuario legítimo lee su documento.
2. Agente adversario usa una credencial señuelo y entra al entorno falso.
3. Se muestra el evento, una respuesta defensiva y su efecto verificable.
4. El usuario legítimo continúa trabajando.
5. Tabla de resultados y un caso de fallo. Si se muestra una grabación, identificarla.

## Trabajo previo y publicación

La preparación conceptual comenzó el 11/11/2026. El 13/11/2026 se añadió v0.1 ejecutable con pruebas y demo determinista HTTP. Todo es trabajo PREVIO al evento y debe declararse. No hay evaluación LLM. Llevar un registro de componentes y autoría. Antes de publicar, acordar crédito y licencia con el equipo y revisar secretos/datos. No publicar código privado de HTER como aporte nuevo del evento.
