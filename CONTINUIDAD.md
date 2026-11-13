# Continuidad del proyecto — 13 de noviembre de 2026

## Actualización HDEF v0.2

Repositorio compartido privado creado por el usuario: https://github.com/sfgamut/HDEF. Se subió la base v0.1 y se desarrolló `codex/pilot-v02`: configuración pilot.json, respuesta observe/enforce, tres perfiles y tres estrategias, informe HTML offline, pruebas y generación automática en Actions para Linux/Windows. HDEF es el repositorio y DÉDALO el concepto defensivo.

Consultar README y PILOTO antes de seguir. Las notas v0.1 que siguen son históricas; la publicación remota ya está realizada. No se ha llamado a proveedores de IA ni enviado mensajes a Claude/Grok. No hay aislamiento físico ni tokens medidos. El modo observe evita la revocación del auditor; no es un detector más inteligente.

## Estado real

- Nombre: DÉDALO.
- Objetivo: aprender y construir un proyecto público defendible de infraestructura de seguridad, con una entrega acotada para hackathon.
- Tres mecanismos: Espejos, Laberinto y Arqueros.
- Postulación enviada; el usuario cree haber sido aceptado. No se ha revisado confirmación.
- Este chat es local, alojado en el computador. Se renombró y fijó para facilitar encontrarlo.
- Existe carpeta de proyecto con repositorio Git local, no proyecto ChatGPT nuevo. Las herramientas permiten mover chats a proyectos existentes pero no crear el contenedor.
- Se implementó v0.1: Python estándar, HTTP local, permisos, señuelo, recorrido ficticio, revocación y trazas. Doce pruebas pasan; la demo HTTP de tres variantes pasa. Aislamiento lógico en un proceso, no físico. Los servicios temporales se cerraron al terminar.
- No se ha publicado en GitHub, conectado modelos ni gastado créditos. El conector no tiene acción de crear repositorio y gh no está instalado. No se ha contactado a Claude ni Grok; sus encargos están en COLABORACION.md.

## Decisiones

Mantener DÉDALO independiente de HTER. El núcleo determinista ya está verificado; falta evaluar IA. El cliente no decide identidades ni permisos. El enrutamiento señuelo no accede a documentos protegidos, pero comparte proceso y no demuestra aislamiento de sistemas. No usar una narrativa animada como sustituto de evidencia.

El guion sigue enlaces automáticamente: 0/1/9 solicitudes a señuelos no prueban persuasión ni desgaste de tokens. Se demuestra un falso positivo: un auditor legítimo que usa el token pierde su sesión. No se implementaron acertijos criptográficos ni bucles contra servicios externos. El desgaste cognitivo es una hipótesis pendiente de evaluar con presupuestos finitos y costo defensor/atacante.

## Próximos pasos

1. Incorporar respuesta de organización sobre aceptación y preparación previa.
2. Revisión de políticas/falso positivo por Claude/Fable y protocolo de evaluación por Grok, con ramas separadas.
3. Incorporar agente IA que pueda ignorar o abandonar los señuelos; presupuesto y proveedor por definir.
4. Separar servicios y redes antes de afirmar aislamiento físico.
5. Visualizar eventos reales, añadir segunda aplicación y correr escenarios reservados.
6. Publicar repositorio cuando se defina visibilidad, crédito y licencia.

## Retomar desde otro chat

Adjuntar el paquete e indicar: “Continúa DÉDALO v0.1. Lee README, CONTINUIDAD y COLABORACION. Ejecuta las pruebas. No atribuyas métricas deterministas a agentes IA ni confundas aislamiento lógico con físico. Trabaja en tu rama, sin depender de HTER”.

## Acceso móvil

La documentación oficial diferencia trabajo en nube y trabajo local. Para este chat local, revisar Remote en el móvil y conectar este computador. En escritorio: Settings → Connections → Control this Mac or PC → Set up/Add; emparejar con QR, usando la misma cuenta/espacio y manteniendo el computador encendido y conectado. No se configuró Remote en esta tarea.

Fuente: https://developers.openai.com/training/walkthroughs/working-on-your-phone
