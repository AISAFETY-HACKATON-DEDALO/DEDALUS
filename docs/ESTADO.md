# Estado de DEDALUS · 14 nov 2026, 14:15

Para quien retome el trabajo (persona o modelo). Léelo antes de tocar código.

## Qué es, en una frase

Una defensa para cuando quien ataca es una IA. Deja **cebos** que solo un atacante usaría y los acomoda a lo que el atacante busca. Cuando alguien muerde, su acceso real queda **desviado a un laberinto** determinista, infinito y barato para nosotros. Todo queda en **Oracle**: qué intentó, qué técnicas usó y cuándo se le detectó.

## Las cuatro preguntas del jurado y dónde está cada respuesta

| Pregunta | Respuesta | Evidencia | Estado |
|---|---|---|---|
| 1. Amenaza | Agente de IA con cuenta válida de bajo privilegio que escala en una aplicación web (MITRE: 157 casos aplicables de CyberSecEval) | `evaluation/vectores/` (Yefran) | ✅ |
| 2. Mecanismo | ARGOS (clasificador determinista) → cebos según lo que busca (D3FEND D3-DF/D3-DUC/D3-DST) → Ícaro → desviar al laberinto (HMAC, 0 tokens) | `dedalus/argos.py`, `cebos.py`, `cnosos.py`, `laberinto.py` | ✅ |
| 3. Validación | (a) Modelos reales muerden: 60 de 66, contra 0 de 21 sin cebo · (b) ¿Protege? Con desviar, 0 solicitudes al sistema real tras detectar; con cortar, 5 · (c) 0 fugas · (d) asimetría: unos 4.400 tokens del atacante contra 0,4 ms nuestros | `evaluation/llm/` · `evaluation/politicas/` · Oracle | (a)(c)(d) ✅ en el laboratorio original · (b) ✅ con guion, **falta con modelos** |
| 4. Límites | Desviar castiga a la cuenta (un cebo filtrado afecta al dueño); el ritmo solo da falsos positivos; quien no toca nada sospechoso no ve cebos; ARGOS se puede aprender | `docs/PROTECCION.md` | ✅ |

## A dónde va cada resultado

```
dedalo.piloto_llm (Yefran)  → evaluation/llm/episodios.jsonl       ┐
dedalo.vectores   (Yefran)  → evaluation/vectores/vectores.json    │  python -m dedalus.publicar
dedalus.bateria   (Yefran)  → evaluation/cnosos/episodios.jsonl    ├→ Oracle: experimentos · vectores · politicas
dedalus.politicas           → evaluation/politicas/episodios.jsonl ┘  (el panel publica solo al arrancar)
panel en vivo               → Oracle: eventos (cada solicitud) · corridas (cada ATACAR) · alertas (ARGOS)
```

Todo `evaluation/` se sube a git. `results/` no se sube: es para pruebas locales.

## Cómo se corre

```powershell
git pull origin main
powershell -ExecutionPolicy Bypass -File .\abrir.ps1        # pide la clave de Oracle; las llaves de Gemini y Groq las lee de Windows
python -m dedalus.politicas --modelos groq --agentes persistente minotauro teseo --repeticiones 3
python -m dedalus.bateria --modelos groq:openai/gpt-oss-120b groq:openai/gpt-oss-20b --repeticiones 5
python -m dedalus.publicar                                   # sube lo nuevo a Oracle y muestra los titulares
python -m unittest discover -s tests                         # 171 pruebas
```

## Lo que falta, en orden de valor

1. **Políticas con modelos reales (Groq).** Es la cifra 3(b) hecha con modelos, no con guion. Si un modelo, al ser desviado, nota el laberinto y se rinde, también es un resultado.
2. **Batería en Cnosos con Groq** (Yefran ya la tiene). Con eso, las cifras 3(a) y 3(d) quedan sobre el sistema que se ve en la demo, no sobre el laboratorio de Alice y Bob.
3. **Robustez de ARGOS:** variantes que lo evadan (una sola señal, señales espaciadas en el tiempo) y medir cuántas pasan. Lo honesto es mostrar también la cifra de evasión.
4. **TALOS** (Yefran): las 6 fallas CWE con Groq, más variantes de los exploits.
5. **Ensayo de la demo:** un guion de 3 minutos (ver abajo) y un respaldo grabado.

## Demo de 3 minutos

1. El panel abierto con ALMACÉN ORACLE. Contar en una frase qué es Cnosos.
2. **ATACAR** (guion persistente o Groq). En el hilo: ARGOS → observado → sospechoso → el cebo aparece en su búsqueda → muerde → Ícaro → vuelve a entrar y cae al laberinto. La cifra «al real tras detectar» se queda en **0**.
3. Pestaña **LAS CIFRAS**:
   - **¿Protege?**: cortar 5, desviar 0.
   - **Modelos reales**: 60 de 66 contra 0 de 21; 4.389 tokens contra 0,39 ms.
   - **Vectores MITRE**.
4. **PARCHAR MUROS**: DÉDALO propone y TALOS verifica sin IA.
5. Database Actions: `SELECT * FROM cnosos_app.alertas ORDER BY n DESC;` muestra la inteligencia guardada.
6. Límites: los de la tabla de arriba, dichos antes de que pregunten.

## Reparto

- **Yefran:** pruebas con modelos (piloto, batería, vectores) y TALOS. Trabaja en la rama `Modelos` y hace `pull` de `main` antes de cada commit.
- **Integración** (main, Oracle, panel, ARGOS, cebos): un solo responsable a la vez, para no pisarse.
- **Reglas:** `AGENTS.md`. Solo loopback, sin dependencias nuevas, y ninguna llave en el repositorio.
