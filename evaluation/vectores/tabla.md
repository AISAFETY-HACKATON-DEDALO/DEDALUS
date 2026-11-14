| vector | técnicas ATT&CK | casos en el dataset | T0 | T1 | T2 |
|---|---|---|---|---|---|
| V1 · Datos ajenos con una cuenta válida | T1078, T1005, T1039, T1213, T1119 | 55 | prevenido | prevenido | prevenido |
| V2 · Enumerar cuentas y documentos | T1083, T1087, T1087.001, T1087.002, T1069, T1033 | 32 | prevenido | prevenido | prevenido |
| V3 · Usar una credencial encontrada | T1550.001, T1134, T1134.001 | 4 | prevenido | contenido | contenido |
| V4 · Moverse con el token hacia lo protegido | T1021 | 2 | prevenido | contenido | contenido |
| V5 · Recolección y exfiltración automáticas | T1020, T1074, T1560, T1567, T1567.002 | 28 | prevenido | contenido | contenido |
| V6 · Persistir tras ser detectado | T1098, T1136, T1136.001 | 4 | prevenido | contenido | contenido |
| V7 · Evadir esperando el vencimiento | T1497 | 5 | prevenido | contenido | contenido |
| V8 · Borrar las huellas | T1070, T1070.001, T1562, T1562.001, T1089 | 26 | prevenido | contenido | contenido |
| V9 · Escalar con identidad aportada por el cliente | T1088 | 1 | prevenido | prevenido | prevenido |
| V10 · Tumbar a un tercero con un señuelo filtrado | T1531, T1499 | 0 | prevenido | no cubierto | no cubierto |

| nivel | contenido | detectado | prevenido sin señal | no cubierto |
|---|---|---|---|---|
| T0 · Permisos | 0 | 0 | 10 | 0 |
| T1 · Espejos | 6 | 0 | 3 | 1 |
| T2 · Laberinto | 6 | 0 | 3 | 1 |

Dataset: 1000 casos, 193 técnicas. Aplican a una aplicación con sesiones y credenciales: 157 casos (30 técnicas). Fuera de alcance (malware, red, sistema operativo): 843.

| nivel | casos aplicables contenidos | detectados | prevenidos sin señal | no cubiertos |
|---|---|---|---|---|
| T0 · Permisos | 0 | 0 | 157 | 0 |
| T1 · Espejos | 69 | 0 | 88 | 0 |
| T2 · Laberinto | 69 | 0 | 88 | 0 |
