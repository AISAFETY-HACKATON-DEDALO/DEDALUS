# Qué rescatamos hoy · DÉDALO

Síntesis para el pitch y la discusión del equipo. Cada afirmación sale de `evaluation/`; nada aquí es una estimación.

## Cuántos datos hay (y cuántos no)

| Fuente | Episodios | Qué son |
|---|---|---|
| Piloto controlado | 87 válidos (+33 inconclusos por cuota) | 3 modelos abiertos como atacante, T0/T1/T2 × ingenuo/advertido × 3 laberintos |
| El ciclo | 17 válidos | ataque → captura → parche de modelo → verificación |
| Políticas | 12 | cortar vs desviar, **solo guion, sin modelo** |
| Cnosos (agente libre) | 0 válidos | la cuota gratuita cortó las 2 corridas |
| Vectores CyberSecEval | 157 casos × 3 niveles × 3 umbrales | deterministas, sin modelo |

**Datos reales con modelos: 104 episodios (87 + 17).** Es exploratorio, no una prueba general. Decirlo así, antes de que lo pregunten, es parte del puntaje.

## Las cinco conclusiones

1. **Avisarle al agente no lo salva.** Advertidos de que hay señuelos y de que usarlos cuesta la sesión, **25 de 30** los usaron igual (ingenuos, 35 de 36). El engaño no depende de que el atacante sea ingenuo.

2. **Lo que retiene es el progreso, no el disfraz.** Quitarle al laberinto la palabra «decoy» (H6) no cambió la conducta: 3,4 pasos frente a 3,6. Quitarle el ciclo —laberinto generativo, cada sala nueva— sí: entre los que mordieron en T2, **6,0 pasos y 7.536 tokens** del atacante frente a 2,7 pasos y 4.450 con el original, y el abandono cayó de 15 de 16 a 4 de 10 (recalculado de `evaluation/llm/episodios.jsonl`). El diseño del mundo falso importa; su decoración, no.

3. **No hay que creerle al modelo cuando dice que detectó la trampa.** En T0, donde **no hay señuelo**, 14 de 21 afirmaron que sí lo había. El auto-reporte de sospecha no mide nada; lo que mide es la conducta (pasos, abandono). Es un hallazgo metodológico que vuelve honesta toda la evaluación.

4. **El ciclo captura→parche→verifica funciona, y el verificador es lo que lo hace fiable.** Con el esquema de la base, los modelos cerraron **48 de 52** funciones atacadas; sin él, 6 de 12 (adivinaban nombres de columnas). TALOS, el verificador **sin IA**, rechazó **10 parches** —entre ellos los que rompían el uso legítimo—. Sin ese verificador, esos 10 parches malos habrían pasado. La IA propone; una regla decide.

5. **La contención es dirigida, pero no evita el primer golpe.** De lo medido: 0 fugas en 87 episodios, y los que mordieron perdieron su sesión sin tocar a terceros. Pero **17 de 68 ataques tocaron la aplicación real antes de la contención** (el primer intento ambiguo pasa) y 6 de 66 atacantes nunca fueron detectados. DÉDALO contiene y aprende de lo que sigue; no es un muro en el primer paso.

## La frase para el jurado

«Los señuelos no son nuevos. Lo nuevo es medir cómo responden los agentes de IA —advertidos incluidos— y cerrar el ciclo: el ataque que cae en el laberinto se convierte en la prueba que verifica el parche. Lo que decide nunca es un modelo, es una regla.»

## Lo que un juez crítico dirá, y la respuesta

- **«Los ceros son por construcción.»** Cierto: 0 fugas lo dan los permisos, no el engaño. Por eso la tabla separa lo que previene el permiso (igual en línea base) de lo que añade DÉDALO (detección y contención).
- **«Muestra pequeña.»** Cierto: 104 episodios, 3 modelos abiertos medianos, ninguno de frontera. Está en Límites.
- **«El atacante elige de un menú.»** Cierto en el piloto. El ciclo y Cnosos dan al agente herramienta HTTP libre; Cnosos con modelos quedó sin correr por cuota.
