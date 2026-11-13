# Piloto editable para la jornada

Para presentar en vivo está la consola: `python -m dedalo.consola --abrir` y la tecla G corre este mismo guion en pantalla. El informe de abajo es el respaldo que se abre sin servidor.

## Preparación: dos comandos

```powershell
python -m unittest discover -s tests -v
python -m dedalo.pilot
```

Abrir `results/pilot/index.html`. Guardar también `results/pilot/pilot.json`: contiene resultados y trazas sin claves. La presentación es una reproducción de resultados HTTP locales, no una interfaz en vivo ni una prueba con modelos. Todo es trabajo previo al evento.

## Ajustes sin cambiar código

Editar `pilot.json` en la RAÍZ (no el archivo de resultados):

| Campo | Opciones | Efecto |
|---|---|---|
| response | enforce / observe | Revocar sesión vinculada o solo observar |
| max_steps | entero 1–100 | Solicitudes permitidas al señuelo; incluye rutas erróneas y repeticiones |
| ttl_seconds | número positivo hasta 3600 | Vigencia desde emisión del señuelo |
| profiles | control, static, maze | Variantes T0/T1/T2 a comparar |
| strategies | follow, ignore, audit, audit_granted | Cliente que sigue pistas, que las ignora, auditor legítimo, auditor con ventana del operador (ver reviews/claude.md) |
| title | texto hasta 120 caracteres | Título del informe |

No existe nivel T3 adaptativo todavía. No son SL1–SL5, certificaciones ni garantías generales. Mantener los mismos presupuestos cuando se comparen variantes.

## Guion de tres minutos

1. “Protegemos una aplicación de documentos; cada persona solo debe ver sus archivos”. Mostrar T0 y el control de otro usuario.
2. “Un señuelo detecta uso de una credencial ficticia”. Mostrar T1/follow y la revocación.
3. “El laberinto conserva el recorrido y cierra por presupuesto”. Abrir T2/follow y sus rutas.
4. “Si ignora las trampas, siguen aplicándose los permisos”. Mostrar T2/ignore.
5. “La respuesta agresiva puede perjudicar a un auditor legítimo”. Mostrar audit y falso positivo. Si interesa, cambiar response a observe y volver a ejecutar para mostrar el compromiso.
6. “El siguiente experimento es un agente que decida cuándo abandonar, con medición de tokens y costos”. No presentar las solicitudes del guion como persuasión de una IA.

## Qué responder según comentarios del equipo

- Falta IA: integrar primero el cliente LLM acotado, manteniendo el evaluador independiente. Elegir proveedor y presupuesto antes de usar claves.
- Falta aislamiento: separar protegido/señuelo en servicios sin conexión cruzada y añadir prueba de acceso directo. La versión actual no lo demuestra.
- La trampa es obvia: mejorar coherencia narrativa y datos ficticios, luego evaluar abandono frente al mismo atacante.
- Demasiado agresivo: usar observe como comparación, después diseñar confirmación o umbral que no dependa de identidad aportada por cliente.
- Piden algo instalable: primera integración HTTP explícita; no prometer compatibilidad universal.

## Automatización y respaldo

Cada push/PR ejecuta pruebas y piloto en Linux y Windows; genera artefactos de resultados descargables desde Actions. workflow_dispatch permite repetir manualmente sin un nuevo cambio. Retención: 7 días. No son tareas programadas ni llamadas a modelos.

Antes de presentar, ejecutar en la computadora de la demo. Ante WinError 10013, hay un bloqueo de conexión local; la ejecución es inconclusa, no un éxito defensivo. Usar como respaldo el informe anterior identificado como ejecución registrada.
