# DÉDALO — laboratorio funcional v0.1

Estado al 13 de noviembre de 2026: prototipo Python con HTTP local, reglas deterministas, señuelo, laberinto y revocación. Doce pruebas automatizadas pasan; hay demo de integración de tres variantes. No hay agente LLM integrado ni evidencia de desgaste de tokens. El usuario cree haber sido aceptado; no se ha revisado confirmación.

## Ejecutar ahora

Requiere Python 3.12 o posterior. No instala paquetes, usa claves de proveedores ni llama a Internet. Desde esta carpeta:

```powershell
python -m unittest discover -s tests -v
python -m dedalo.demo
```

La demo inicia servicios temporales en `127.0.0.1`, hace solicitudes HTTP y los cierra. Genera `results/demo.md` y `results/demo.json`, sin credenciales. Requiere conexiones locales permitidas. WinError 10013 significa que la comunicación no se pudo verificar, no que la defensa haya funcionado.

Exploración manual: `python -m dedalo.server --mode maze --port 8765`. El servidor imprime credenciales efímeras para el laboratorio. Usar `Authorization: Bearer TOKEN` con un cliente HTTP. Rutas: `GET /api/documents`, `GET /api/documents/alice-note`, `GET /api/maintenance`. La última devuelve una credencial señuelo y su entrada. Usarla revoca su sesión de origen. `Ctrl+C` detiene el servidor. No exponer a Internet ni usar datos reales.

## Implementado y pendiente

- Autorización por propietario, token señuelo por sesión, recorrido con estado y revocación vinculada por el servidor.
- Máximo de 8 solicitudes al señuelo y 120 segundos desde emisión. Eventos acotados sin claves.
- Variantes: `control`, `static`, `maze`; mantienen la misma autorización básica.
- Aislamiento lógico dentro de un proceso, NO servicios físicamente aislados ni defensa de producción. Falso positivo conocido: auditor legítimo que usa el token.
- Pendientes: adaptador de modelo, selección adaptativa, tokens reales, aislamiento entre servicios y segunda aplicación.
- Repositorio Git local creado. Publicación remota pendiente. Ver COLABORACION.md.

## Propuesta en 30 segundos

DÉDALO estudia si una aplicación puede detectar el uso de credenciales señuelo, conducir esa interacción a un entorno falso coherente y contener los accesos reales asociados, manteniendo el servicio para usuarios legítimos. Combina Espejos (señuelos), Laberinto (estado ficticio por sesión) y Arqueros (contención).

La primera entrega implementa una aplicación HTTP pequeña, un señuelo y un recorrido falso de tres pasos con continuación acotada. La adaptación con IA sigue siendo una ampliación que debe demostrar su utilidad frente a reglas simples.

## Viabilidad

| Alcance | Evaluación de planificación |
|---|---|
| API de documentos sintéticos, señuelo, sesión falsa y revocación con reglas | Viable como objetivo de jornada para 2–4 personas con entorno listo; no es una garantía de tiempo. |
| Atacante LLM limitado a herramientas del laboratorio | Ampliación prioritaria si la base funciona y existe presupuesto de API. |
| Laberinto que adapta ramas mediante un LLM | Condicionado a integrar y evaluar antes el núcleo; recortable. |
| Defensa para aplicaciones arbitrarias, múltiples protocolos y sistemas operativos | Fuera de la hackathon. |
| HTER completo como dependencia | Fuera del camino crítico. |

## Leer en este orden

1. [Arquitectura](ARQUITECTURA.md): flujo, límites, contratos y criterio de integración.
2. [Experimento](EXPERIMENTO.md): comparación justa y señales de fracaso.
3. [Preparación y equipo](HACKATHON.md): qué llevar, trabajo previo y reparto del día.
4. [Escenarios](scenarios.json): casos definidos para implementar, todavía no ejecutados.
5. [Continuidad](CONTINUIDAD.md): estado, decisiones y próximos pasos.

## Primer hito ejecutable verificado

Un usuario autorizado puede leer su documento. Otro usuario no puede leerlo. Una credencial señuelo solo accede a datos ficticios. Una sesión revocada pierde acceso y otra sesión legítima sigue funcionando. La demo comprueba respuestas y marcadores, no declaraciones de éxito de agentes.

Resultados del guion: control 5 solicitudes, estático 6, laberinto 14; 0, 1 y 9 solicitudes al señuelo respectivamente, incluida la denegación por presupuesto. El guion sigue los enlaces automáticamente; estas cifras no prueban persuasión de un LLM. Ninguna variante entrega el marcador protegido al visitante. Los permisos básicos ya lo bloquean.

No hacen falta aún interfaz de castillo, orquestación multiagente ni HTER. Las metáforas organizan el diseño; las pruebas establecen qué protege.

## Fuentes y límites

- [Convocatoria](https://www.aisafetycolombia.org/defacchackathon), consultada el 11/11/2026: jornada del 14 de noviembre, equipos de 2–4 y ocho horas de construcción/evaluación. No se verificó una cláusula sobre código previo. La página ahora menciona seis frentes; DÉDALO sigue encajando en ciberdefensa.
- [MITRE Engage](https://engage.mitre.org/wp-content/uploads/2022/04/EngageHandbook-v1.0.pdf): referencia sobre entornos de engaño aislados.
- [Cowrie](https://docs.cowrie.org/en/stable/PROXY.html): antecedente de honeypots interactivos.

La combinación propuesta es una hipótesis de ingeniería; no se afirma novedad científica ni resistencia general a ataques.
