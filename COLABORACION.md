# Trabajo con Claude/Fable, Grok y Codex

No se ha contactado a otros proveedores ni gastado créditos. Estos encargos se pueden transferir a sus herramientas. Tres chats abiertos no coordinan por sí mismos los archivos.

## Flujo compartido

Cada colaborador trabaja en su rama y preferiblemente checkout distinto. No editar los mismos archivos simultáneamente. Integrar una propuesta a la vez después de pruebas. No publicar claves, documentos personales ni código de HTER. Definir licencia con el equipo antes de publicación pública.

Ramas: `codex/core`, `claude/policy-review`, `grok/evaluation`. Una persona integra a `main`. Cada entrega explica cambio, comprobaciones y límites. No atribuir revisiones a modelos que no las hicieron.

## Encargo para Claude / Fable 5.2

Lee README.md, ARQUITECTURA.md, dedalo/core.py y tests/test_lab.py. Revisa v0.1 como laboratorio HTTP, no como defensa de producción. Busca errores en correlación de identidad, revocación, límites y separación de datos. Un auditor legítimo que usa el token se bloquea: propone una política que reduzca ese falso positivo sin aceptar identidad ni permisos aportados por el cliente. Entrega hallazgos reproducibles y propuesta en `reviews/claude.md`. Si implementas, usa `claude/policy-review` y pruebas. No integres modelos, interfaz ni cambios generales de estructura.

## Encargo para Grok

Lee README.md, EXPERIMENTO.md, scenarios.json y dedalo/demo.py. Diseña en `evaluation/PROTOCOL.md` una comparación que no obligue al atacante a seguir señuelos. Incluye ignorar la trampa, detectar contradicciones y abandonar. Distingue protección, detección, retención, tokens, costo y falsos positivos. Fija presupuestos iguales, casos reservados y éxito observable. No afirmes dificultad específica para Fable sin datos. Trabaja en `grok/evaluation`; no cambies dedalo/core.py ni pruebas existentes sin acordar el contrato. Llamadas pagadas y objetivos externos fuera del encargo.

## Encargo de Codex

Mantener integración, pruebas y reproducción. Conectar después un agente real con herramientas limitadas al laboratorio y presupuestos explícitos. Separar redes/procesos antes de afirmar aislamiento físico. No declarar finalizado el proyecto por pasar pruebas deterministas.

## Repositorio remoto

Nombre sugerido: `dedalo-lab`. Creación remota pendiente; este paquete contiene un repositorio local y workflow de pruebas. La visibilidad pública debe quedar explícita al crearlo. No incluir proyectos privados enteros.
