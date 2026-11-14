| atacante | defensor | esquema | contenido | fuga | ataques capturados (en el laberinto) | funcionaban contra el original | funciones cerradas | s hasta cerrar | s del atacante tras caer |
|---|---|---|---|---|---|---|---|---|---|
| ensayo | groq:openai/gpt-oss-120b | sí | sí | no | 4 (3) | 4 | 4/4 | 14.9 | 0 |
| ensayo | groq:openai/gpt-oss-120b | sí | sí | no | 4 (3) | 4 | 4/4 | 29.26 | 0 |
| ensayo | groq:openai/gpt-oss-120b | sí | sí | no | 4 (3) | 4 | 4/4 | 11.63 | 0 |

Cerrada: el parche pasa las pruebas del caso y además bloquea todos los ataques capturados a esa función.
`guion` y `ensayo` no son modelos. Los casos son funciones aisladas del portal; el parche se verifica, no se despliega.
