# AGENTS.md · HDEF / DÉDALO

Para cualquier agente de IA que lea o cambie este repositorio. Laboratorio local con datos sintéticos; no es un producto de seguridad.

Lee primero `README.md` y `docs/CONTINUIDAD.md`.

## Reglas

1. Después de tocar política, HTTP o la interfaz: `python -m unittest discover -s tests -v`, `python -m dedalo.demo` y `python -m dedalo.pilot`.
2. Solo loopback. Nada de escaneo externo, credenciales reales ni llamadas pagadas a modelos sin que el dueño lo pida.
3. Una métrica del guion nunca se convierte en una afirmación sobre tokens, persuasión o modelos.
4. Las credenciales no se registran ni llegan al navegador. La vinculación entre señuelo y sesión la asigna el servidor; el cliente no elige a quién se revoca.
5. Presupuestos finitos. La salida de un modelo no cambia permisos ni ejecuta código.
6. Sin dependencias nuevas: biblioteca estándar de Python, y HTML, CSS y JavaScript sin framework.
7. Interfaz: `docs/DISENO.md`. Todo texto visible va en `dedalo/interfaz/textos.js`; nada entra al documento como HTML; la política de contenido de la consola no admite código ni estilos en línea.
8. Ramas y reparto: `docs/COLABORACION.md`. `main` lo integra el dueño.
9. Los límites y el trabajo previo al evento se documentan tal como son.
