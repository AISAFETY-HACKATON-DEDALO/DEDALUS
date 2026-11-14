# DEDALUS · resumen

**Track 3 · Ciberdefensa automatizada** · Repositorio: https://github.com/AISAFETY-HACKATON-DEDALO/DEDALUS

DEDALUS es una defensa automatizada para aplicaciones web cuando quien ataca es un agente de IA con una cuenta válida. Un clasificador de reglas observa cada sesión; si usa una credencial señuelo o lanza un ataque inequívoco, el servidor revoca su acceso real y la desvía a un laberinto falso generado por HMAC, que cuesta milisegundos y cero tokens.

El aporte central es cerrar el ciclo: cada ataque capturado, incluidos los que el agente hace ya dentro del laberinto, se repite contra la función vulnerable; un modelo propone el parche y un verificador sin IA lo acepta solo si el uso legítimo sigue intacto y el ataque capturado deja de funcionar.

Evaluamos con modelos reales como atacantes simulados, en un laboratorio local con datos sintéticos. En 87 episodios no hubo ninguna fuga; 60 de 66 usaron el señuelo, incluso advertidos, y los 60 perdieron su sesión; sin señuelo, 0 de 21. Con el laberinto generativo, los que mordieron siguieron 6,0 pasos frente a 2,7 del original, y abandonaron 4 de 10 frente a 15 de 16. De 157 casos aplicables de CyberSecEval, ninguno logró su objetivo y 69 quedaron contenidos. Los modelos defensores cerraron 48 de 52 funciones atacadas cuando conocían el esquema de la base (6 de 12 sin él), y el verificador sin IA rechazó los parches que rompían el uso legítimo.

Los resultados son exploratorios: muestras pequeñas, modelos abiertos medianos y un límite sin resolver, que un señuelo filtrado revoca a su dueño.
