# HDEF · reglas de diseño

El lenguaje visual es el de SATOR: todo se dibuja con caracteres por sus propios datos. Este documento fija lo que toda pantalla de HDEF respeta. Si algo nuevo no cabe, se discute la regla antes de romperla.

## La tesis

La interfaz es un instrumento, no una ilustración. La forma no se decide de antemano: la decide lo que respondió el servidor.

- **Un carácter, una solicitud.** El cuerpo de cada sesión son las solicitudes que hizo, con el primer dígito de su respuesta. Una sesión que no ha pedido nada es un anillo vacío.
- **Nada se dibuja sin dato.** Una sala del laberinto aparece cuando el motor la abrió. El hilo existe cuando alguien recorrió ese pasillo. La flecha de los arqueros sale cuando un evento revocó una sesión, no antes.
- **La voz dice lo que anotó el motor.** Cada frase corresponde a un motivo o una acción del registro. Si no hay dato, calla.
- **Toda simplificación se declara en pantalla:** «nada está a escala», «sin modelos», «ejecución guardada, no es en vivo».

## Composición

| Zona | Qué va |
|---|---|
| Arriba | La marca y el lema · los tres niveles (T0, T1, T2), que son la única navegación · el reloj del episodio, la respuesta, el sonido y la ayuda |
| Forma (izquierda) | La voz, la última respuesta tal como llegó, y la escena: sesiones, pasarela, documentos, espejo, laberinto |
| Información (derecha) | El parte: la cifra grande, el marcador, las sesiones con lo que puede hacer el operador, el registro |
| Abajo | El mando: quién eres, la línea para escribir una ruta, y un solo dock con las acciones |

En el computador, forma e información van lado a lado con una costura fina. En el celular se apilan: forma, mando, información. Lo que se puede tocar en la escena tiene su botón equivalente en el dock.

## Letra

- Números, nombres y botones: **VT323**, 16 px o más. La cifra del parte, más de 100.
- Rótulos y telemetría: **Share Tech Mono**, en mayúsculas, con espaciado, separados por `·`. Nunca por debajo de 11 px.
- Párrafos (solo en la ayuda): **IBM Plex Mono**.
- Una sola frase por pantalla va en letra sin remates y en blanco: el titular del parte.

## Color

El color es dato o es voz, nunca adorno. Cada cosa tiene el suyo y lo lleva en todas partes: su nombre, su cuerpo, su fila, su botón.

| Nombre | Para | Tono |
|---|---|---|
| Negro Olbers | Fondo | `#050505` |
| Tiza | Estructura y texto | `#ececec` |
| Regolito | Lo secundario; una respuesta negada | `#8d8d8d` |
| Aurora | Solo cuando algo pasa: una revocación, un cierre, un fallo | `#ff6b9a` |
| Egeo | Alice | `#7fb2e0` |
| Olivo | Bob | `#a9d18e` |
| Ámbar | Tú, el visitante | `#f2b33d` |
| Azogue | El espejo y su token | `#9fdcd9` |
| Hilo de Ariadna | El laberinto y lo que se recorre en él | `#cf84e6` |

Negro, tiza, regolito y aurora son los de SATOR. Dos cosas vecinas no llevan tonos parecidos. El rosa no se usa para decorar: si aparece, algo ocurrió.

## Movimiento y sonido

- Entre episodios y niveles no hay transición: corte seco.
- Lo que cambia, se mueve: la solicitud viaja a su destino y vuelve con su código; la escena cambia cuando la respuesta llega, no antes.
- La portada dura menos de dos segundos y cualquier tecla la termina. Con «reducir movimiento» no existe, y las solicitudes no viajan.
- Lo que cambia, suena, poco: una nota al pedir, otra al volver, dos graves cuando cae una sesión. `M` lo calla.
- Una sesión revocada deja de girar.

## Honestidad

- Ninguna credencial llega al navegador. Los tokens se muestran tachados y con su nombre (`token decoy-1`).
- El marcador protegido lo cuenta la consola mirando las respuestas, no lo declara quien ataca ni quien defiende.
- El guion se presenta como lo que es: un cliente fijo. Nunca como un modelo.
- Si la consola no responde, se dice SIN SEÑAL. Eso no es un resultado.

## Lista de revisión

- [ ] ¿Cada cosa dibujada corresponde a un dato del estado?
- [ ] ¿Todo texto visible está en `dedalo/interfaz/textos.js`?
- [ ] ¿Nada llega al documento como HTML? (solo `textContent`)
- [ ] ¿Ningún rótulo por debajo de 11 px? ¿Se lee en un proyector?
- [ ] ¿Cada cosa en su color, distinto del de su vecina, y el rosa solo en eventos?
- [ ] ¿Cabe sin desplazarse en 1366 × 768 y se apila bien en 390 de ancho?
- [ ] ¿Pasan `tests/test_consola.py` y el resto?
