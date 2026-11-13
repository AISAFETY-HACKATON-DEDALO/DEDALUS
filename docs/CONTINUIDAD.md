# Continuidad · 13 de noviembre de 2026

## Estado

- **v0.3.** Motor, servicio HTTP, demo, piloto configurable, consola jugable e informe sin conexión. 47 pruebas con la biblioteca estándar; corren en Linux y Windows en cada push.
- Repositorio privado: https://github.com/sfgamut/HDEF. HDEF es el repositorio; DÉDALO, la defensa.
- La revisión de política está integrada (`reviews/claude.md`): la contención ocurre antes del presupuesto, la evidencia no se pierde con el tráfico, existe la ventana de auditoría del operador.
- No hay agente de lenguaje integrado, ni aislamiento entre servicios, ni medición de tokens.
- Postulación a la hackathon enviada. La respuesta de la organización sobre código previo está pendiente (`docs/HACKATHON.md` tiene la consulta lista).

## Decisiones

- DÉDALO es independiente de HTER.
- El cliente no decide identidades ni permisos. El objetivo de una revocación sale solo de lo que el servidor emitió.
- La consola es banco de pruebas: guarda las credenciales y pide por los actores. No es parte de la defensa.
- Las métricas del guion no se presentan como evidencia sobre modelos.
- La estética es la de SATOR (`docs/DISENO.md`).

## Lo que queda abierto

1. Respuesta de la organización: aceptación y trabajo previo.
2. Un atacante que decide: agente con herramientas limitadas al laboratorio y presupuesto explícito. Proveedor por definir.
3. Protocolo de evaluación en `evaluation/PROTOCOL.md` (encargo de Grok, sin empezar).
4. Servicios separados antes de afirmar aislamiento.
5. Un cierre del laberinto que no delate la trampa (H5) y atar el señuelo al canal de su sesión (H3).
6. Licencia y crédito con el equipo antes de hacer público el repositorio.

## Retomar

Leer `README.md` y este archivo. Correr `python -m unittest discover -s tests -v`. Trabajar en una rama propia (`docs/COLABORACION.md`).
