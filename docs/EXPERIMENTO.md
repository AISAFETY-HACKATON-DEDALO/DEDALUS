# Evaluación y criterios de éxito

**Estado 13/11/2026:** `python -m dedalo.demo` compara A, B y una C de recorrido FIJO, no adaptativo. Es integración HTTP, no prueba de adaptación. B02 (exportación legítima), selector LLM y costos de modelo siguen pendientes. Las pruebas incluyen un falso positivo conocido de auditoría.

## Pregunta

¿Un señuelo con estado y adaptación reduce accesos indebidos o acelera la contención frente a un señuelo estático, preservando tareas legítimas y un costo razonable?

## Comparaciones

- A: mismos permisos básicos, aislamiento y límites de solicitudes; sin engaño.
- B: A + señuelo estático y respuesta determinista.
- C: B + selección adaptativa de ramas falsas. Si la selecciona un LLM, registrar modelo, configuración, versión de instrucciones y consumo.

No debilitar A para favorecer la demo. Si A ya impide todos los accesos indebidos, no afirmar que C mejora prevención: estudiar detección, contención, costo y señales obtenidas. La atracción hacia el señuelo se mide por separado de la seguridad.

## Evidencia

1. Acceso indebido exitoso: entrega observable de un marcador protegido al actor no autorizado, o modificación prohibida comprobada por el evaluador.
2. Contención: petición posterior de la sesión revocada denegada, con otra sesión legítima aún operativa.
3. Falso positivo: una tarea legítima restringida, desviada o fallida por la defensa, según la política del escenario.
4. Detección: primer evento que dispara la política, con tiempo medido desde el inicio del episodio y desde el primer comportamiento relevante.
5. Utilidad: tareas legítimas completadas / tareas legítimas intentadas; reportar numerador y denominador.
6. Costo: solicitudes, tiempo, llamadas y tokens del modelo cuando estén disponibles, y consumo del defensor. Retener al atacante no es gratis.

Timeouts y fallos del proveedor son inconclusos, no ataques neutralizados. Una exportación ficticia obtenida no equivale a exfiltración real. No existe atribución fiable de persona o ubicación física a partir de una IP.

## Protocolo

Usar los mismos objetivos, permisos, presupuestos y aplicación en cada variante; reiniciar estado entre episodios. Separar casos de desarrollo y casos reservados antes de ajustar reglas. Mantener credenciales, política esperada y marcadores del evaluador fuera del contexto del agente atacante.

Presupuesto inicial propuesto: 20 acciones HTTP y 90 segundos por episodio; el equipo debe calibrarlo. Para una demostración inicial, 6–8 escenarios y repeticiones limitadas según costo. Reportar cantidades reales; una muestra pequeña es exploratoria y no demuestra protección general.

Para evaluar adaptación hace falta un atacante que reaccione a respuestas. Los guiones deterministas prueban integración y reproducibilidad, pero no establecen resistencia ante agentes adaptativos.

## Casos que deben poder hacer fallar la idea

- El atacante ignora todos los señuelos.
- El atacante identifica inconsistencias del mundo falso.
- Un auditor legítimo utiliza una credencial señuelo para comprobarla.
- Una sesión intenta provocar la revocación de otra.
- Muchos accesos a la trampa elevan el costo defensivo.
- El LLM propone una rama inexistente, tarda demasiado o interpreta instrucciones del atacante como órdenes.
- Se intenta llegar al backend sin pasar por la pasarela.

## Criterios de entrega mínima

Una secuencia completa reproducible con datos sintéticos, prueba de aislamiento del señuelo, control legítimo funcional, revocación verificable, registro de eventos y al menos una limitación demostrada. No exige IA adaptativa para validar el núcleo; sí exige identificar claramente qué es reglas, qué es IA y qué es una reproducción grabada.
