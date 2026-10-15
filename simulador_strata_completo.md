# Simulador visual Ollama vs Strata — documento completo

Dos piezas en un archivo:

- **Parte 1 — Especificación.** Es lo que se pega en un agente de código para que genere la web.
  Si el agente acepta adjuntos, adjuntar también la imagen `FONDO.png`: el bloque «Estilo visual»
  contiene su paleta exacta por si no se puede adjuntar.
- **Parte 2 — Checklist de validación.** Material de verificación. No forma parte del prompt: se usa
  cuando el agente entrega el `index.html`.

**Cómo usarlo**

1. Copiar desde `## Rol` hasta el final de la Parte 1 y pegarlo en el agente.
2. Cuando entregue el archivo, abrirlo con doble clic y pasar la Parte 2. Los ítems `[C]` se los dejas
   auditar a la IA con el prompt de auditoría del final; los `[N]` se comprueban en el navegador.

## Contenido

**Parte 1 — Especificación**
  - Rol
  - Qué debe simular
  - Panel de hardware
  - Inspector de cuello de botella
  - Modo comparativo directo (Ollama vs Strata)
  - Benchmarks de hardware (ModelDock) — el eje económico
  - Estilo visual (referencia: FONDO.png)
  - Restricciones técnicas
  - Criterios de aceptación

**Parte 2 — Checklist de validación**
  - Bloque A — Integridad técnica
  - Bloque B — Criterios de aceptación
  - Bloque C — Estilo visual (contra FONDO.png)
  - Bloque D — Honestidad numérica
  - Bloque E — Accesibilidad y responsive
  - Bloque F — Benchmarks de hardware (ModelDock)
  - Recuento
  - Criterios de corte
  - Prompt de auditoría

---

# PARTE 1 — Especificación

*Pegar desde aquí hasta el final de esta parte.*

## Rol

Eres un ingeniero de front-end y de sistemas de inferencia. Quiero una **web de una sola página
(un único `index.html`)** que sea un **simulador animado en tiempo real** de lo que ocurre por
dentro de un PC cuando se carga y se usa un modelo de lenguaje grande, comparando dos motores:

1. **Ollama** (carga clásica GGUF: el modelo debe quedar residente en VRAM o, si no cabe, en RAM
   vía mmap; lo que no cabe en GPU se ejecuta capa a capa desde CPU).
2. **Strata** (https://stratallm.org/docs/quickstart/ · https://github.com/Niko1221/Strata),
   que reparte el modelo entre **VRAM + RAM + SSD** y usa decodificación especulativa.

El objetivo no es un dashboard de métricas: es que alguien **vea con los ojos** por qué un PC de
jugador puede mover un modelo de 125 mil millones de parámetros y por qué el mismo PC con Ollama
se ahoga. La simulación debe **reaccionar en vivo a los cambios de hardware**: si muevo la RAM de
32 a 64 GB, la animación, los tiempos de carga y los tokens/s tienen que cambiar delante de mí.

---

## Qué debe simular

### Fase A — Carga del modelo

Línea de tiempo horizontal con scrubber, play/pausa y velocidad ×1 ×4 ×16. Flujo por etapas, con
barras de progreso y bytes moviéndose como partículas por el camino:

```
Disco (pesos GGUF) ──► RAM (pinned) ──► VRAM (expert cache / capas) ──► listo
```

- **Ollama:** descarga → volcado del archivo GGUF → carga de capas en VRAM hasta llenarla →
  las capas restantes se ejecutan desde CPU (mostrar el *spill* y avisar de la penalización). Si el
  fichero no cabe en RAM, hace page faults contra el disco. El KV cache se reserva en VRAM y crece
  con el contexto.
- **Strata:** descarga del shard 1 (los expertos → RAM, pinned) + shard 2 (tabla n-gram / PLE de
  ~28,8 GB que **se queda en el SSD**, no se copia: se lee bajo demanda) + capa draft MTP (~6 GB,
  +1 GB con imágenes) → al arrancar, Strata copia a VRAM **solo los expertos más usados** (el
  "expert cache") y el resto se queda en RAM. Mostrar el aviso real: *"mientras carga, el PC puede
  ir lento 1–3 minutos"*.
- Contador de segundos de carga y de GB movidos por etapa, y un veredicto explícito:
  **CABE / NO CABE / CABE EN MODO LOW-RAM / GPU NO SOPORTADA**.

### Fase B — Inferencia

Bucle continuo, token a token, con los tokens viajando por el pipeline:

1. **Prompt** → se procesa en **chunks de hasta 8.192 tokens** (32.768 opcional), con los expertos
   **streaming por PCIe** hacia la GPU. Barra de prefill con tokens/s.
2. **Enrutado MoE**: el modelo tiene **48 capas × 512 expertos = 24.576 expertos**; cada token
   activa **solo ~10**. Dibujar una rejilla de expertos donde se encienden los que tocan, y
   distinguir visualmente los que están **en VRAM (cacheados)** de los que se ejecutan **en RAM por
   la CPU en paralelo** y de los que se **streaman por PCIe**. Ese es el corazón de la visualización.
3. **KV cache** en VRAM; a partir de 64K de contexto solo la parte más leída vive en VRAM y el
   resto se streama desde RAM.
4. **Tabla PLE / n-gram en SSD**: peticiones de filas por segundo al disco. Umbral real: el motor
   avisa por debajo de **~15K filas/s**; un SATA topea en **10–14K** con lecturas directas.
5. **Decodificación especulativa**: la capa MTP del propio modelo **propone hasta 3 tokens**, una
   sola pasada por las 48 capas los **verifica en bloque**; media real de **2,4–3,2 tokens por
   pasada**. Animar propuesta → verificación → aceptados/rechazados, y mostrar el acierto.
   Ollama, en el mismo escenario, genera 1 token por pasada (o con un modelo draft aparte).
6. **Salida**: streaming de texto con tokens/s en vivo.

---

## Panel de hardware

Sliders y selects; **cada cambio re-evalúa el modelo de simulación al instante**, sin recargar:

| Parámetro | Valores |
| --- | --- |
| GPU | 1 o 2 tarjetas; VRAM 4–32 GB; modelo (afecta a soporte y a ancho de banda) |
| Multi-GPU | off / split por capas (Strata). Ollama también parte capas entre tarjetas, pero sin reparto VRAM+RAM+SSD ni cache de expertos por tarjeta: modelar la diferencia, no un «no soporta» |
| RAM | 16–128 GB |
| CPU | núcleos, AVX-512 sí/no |
| PCIe | Gen3/4/5 × x16/x8/x4 (afecta al streaming de expertos) |
| Disco | HDD / SATA SSD / NVMe (afecta a la tabla PLE y a la carga) |
| Modelo Strata | Coder (IQ1_M) · Q2_0 · IQ2_XS · IQ3_XXS · IQ3_S · UD-IQ4_XS · UD-Q4_K_XL |
| Contexto | 4K · 32K · 128K · 262K |
| Carga de trabajo | prompt de N tokens · tokens de salida · nivel de thinking · `parallel: 1 o 2` |

### Presets de hardware (cargables de un clic)

- `RTX 5070 12 GB + Ryzen 5 7600 + 64 GB DDR5 + NVMe` (el PC de referencia de los benchmarks)
- `RX 9070 XT 16 GB + Ryzen 9 3900X + 47 GB` (AMD; en Windows no puede leer imágenes, en Linux las
  lee por CPU; el MTP no se ve afectado)
- `RTX 3090 24 GB + 64 GB + NVMe` (más VRAM = más expertos cacheados = más rápido)
- `RTX 5080 16 GB + RTX 3090 24 GB` (doble GPU, split por capas)
- `32 GB de RAM + GPU de 24 GB` (dispara el modo low-RAM: expertos mapeados desde fichero)
- `GTX 1080 Ti 11 GB` (ver las dos rutas más abajo)
- `Sin GPU (solo CPU)` (solo Ollama, muy lento)

### Reglas de ajuste

- Strata cabe cuando **RAM ≥ expertos + ~10 GB**. Expertos por tamaño: Coder 23 GB, Q2_0 34 GB,
  IQ2_XS 35,5 GB, IQ3_XXS 43 GB, IQ3_S 50 GB, UD-IQ4_XS 59,5 GB, UD-Q4_K_XL 77 GB.
- **El modo low-RAM no está disponible para todos los tamaños.** Con una GPU de 12–16 GB solo
  admite el **Coder**; con una GPU de 24 GB admite Q2_0, IQ2_XS y Coder. Con GPU pequeña y un
  tamaño grande el veredicto es **NO CABE**, no low-RAM.
- Más VRAM **no** baja la RAM necesaria (salvo en modo low-RAM), pero **sí** sube la velocidad:
  más expertos cacheados en GPU, menos streaming por PCIe y menos trabajo de CPU.
- El KV cache crece con el contexto y compite con el expert cache por la VRAM.
- `parallel: 2` multiplica peticiones pero ralentiza cada respuesta en tarjetas de 12 GB.
- Requisitos de GPU: **12 GB de VRAM o más** y **compute capability ≥ 7.5** (RTX 20 en adelante).
  En multi-GPU, tarjetas de menos de 8 GB no se admiten en conjunto salvo que se nombren a mano.
- **GPU no soportada (GTX 1080 Ti, compute 6.1):** modelar **dos rutas**. Por defecto Strata la
  rechaza y nombra el motivo. Si el usuario la fuerza (`--gpus` + motor experimental CUDA 12), sí
  funciona, más lenta: los docs reportan 2× Tesla P40 pasando de 19,6 a 34,8 tok/s al usar las dos.
  Mostrar el aviso de experimental y la penalización.

### Datos de calibración

RTX 5070 12 GB / Ryzen 5 7600 / 64 GB DDR5-5200 / Windows. El decode se mide con **prompt corto** y
el prefill con **prompt de 32K**: son dos mediciones distintas, no el mismo escenario.

| Tamaño | Decode tok/s (prompt corto) | Prefill tok/s (prompt 32K) | RAM+VRAM |
| --- | ---: | ---: | ---: |
| Q2_0 | 94 | 2.650 | 37,6 GB |
| IQ2_XS | 79 | 2.090 | 39,2 GB |
| IQ3_XXS | 62 | 1.750 | 47,0 GB |
| IQ3_S | 53 | 1.620 | 54,8 GB |
| Coder | 55 | 2.180 | 29,6 GB |

Penalización por contexto largo en decode (128K frente a prompt corto), por tamaño:
Q2_0 −19%, IQ2_XS −20%, IQ3_XXS −21%, IQ3_S −13%, Coder −22%.

AMD RX 9070 XT 16 GB (Linux): Q2_0 60 / 1.160, IQ2_XS 52 / 1.110, Coder 44 / 1.420.
RTX 3090 24 GB: ~100–140 tok/s. Primera lectura de un prompt largo: ~1 min por cada 30.000 tokens.

Anclas para los dos modelos grandes:

- **UD-Q4_K_XL**: 111 GB de descarga, 77 GB de expertos que no caben en RAM; **7–8,5 tok/s** en un
  PC de 64 GB con GPU de 12 GB. Requiere ≥48 GB de RAM, NVMe y una sola GPU NVIDIA; sin imágenes.
- **UD-IQ4_XS**: 94 GB de descarga, 59,5 GB de expertos. Requiere ≥48 GB de RAM. Por debajo de
  ~80 GB de RAM parte de los expertos se leen del SSD mientras responde (más lento; un NVMe ayuda).

Estas cifras son **picos por tamaño de modelo**. La sección «Benchmarks de hardware» tiene
rendimiento **sostenido bajo carga mixta**, que da números más bajos para la misma tarjeta: no las
mezcles ni las promedies.

Usa estos números como anclas y **extrapola de forma visible y honesta**: si un número es una
estimación, márcalo con un asterisco y un tooltip que diga «estimación del modelo de simulación, no
medido». Igual con los valores de disco no documentados (un HDD mecánico y un NVMe moderno en
filas/s de la tabla PLE son estimaciones).

---

## Inspector de cuello de botella

Un panel que, para el estado actual, dice **qué recurso es el limitante** y lo resalta en la
animación (la pieza implicada late/brilla): VRAM llena → streaming PCIe saturado → CPU sin AVX-512
→ SSD lento para la tabla PLE → RAM insuficiente → contexto demasiado grande. Cada diagnóstico
lleva la acción concreta que lo arregla (bajar de IQ3_S a IQ2_XS, activar low-RAM, poner NVMe,
quitar la segunda GPU mal dimensionada, etc.).

---

## Modo comparativo directo (Ollama vs Strata)

Selector de vista en la cabecera: **`CARGA` · `INFERENCIA` · `VS` · `ECONOMÍA`**. El modo `VS` es
el modo por defecto al entrar. La vista `ECONOMÍA` se define en la sección «Benchmarks de hardware».

**Regla de oro del modo VS:** un solo hardware, un solo modelo, una sola carga de trabajo, **un
reloj compartido**. No dos simulaciones independientes: mismo `t=0`, misma secuencia de tokens de
entrada, mismo prompt. Todo lo que difiere es el motor.

### 1. Carrera sincronizada

Dos carriles apilados (Ollama arriba, Strata abajo) sobre la misma línea de tiempo:

- Barra de carga que avanza en paralelo; se ve cuándo Ollama se queda sin VRAM y empieza el *spill*
  a CPU, y cuándo Strata está soltando 35–50 GB a RAM y dejando los 28,8 GB de tabla en el SSD sin
  copiarlos.
- Barra de prefill y luego decode, con los tokens generados avanzando en el carril de cada motor.
  El más rápido se va adelantando en pantalla; contador de tokens generados y de adelantamiento
  (Δs y Δtokens).
- Cada carril tiene su mini-grafo de memoria (VRAM / RAM / PCIe / SSD) animando a la vez, para que
  el adelantamiento se entienda como causa-efecto y no como un número suelto.

### 2. Tabla de métricas de cuello de botella

Una fila por recurso, tres columnas **Ollama | Strata | Δ**, más una columna **limitante** que marca
con la rampa de calor el recurso que más penaliza a cada motor. Todas las métricas se recalculan al
mover cualquier slider.

| Métrica | Definición | Umbral de cuello de botella |
| --- | --- | --- |
| Ocupación de VRAM | GB usados / GB totales, incluyendo pesos + KV + buffers | > 92% |
| Headroom de VRAM | MiB libres tras reservar KV y buffers | < 512 MiB |
| Capas en CPU (Ollama) | nº de capas GGUF que no caben en VRAM / total | > 0 ya penaliza |
| Acierto del expert cache (Strata) | % de los ~10 expertos activos por token que ya estaban en VRAM | < 40% |
| Anchura PCIe usada | GB/s de streaming de expertos vs teórico del enlace (Gen×/x) | > 85% del enlace |
| Uso de CPU | % de núcleos ocupados × factor del set de instrucciones (AVX-512 > AVX2 > sin AVX2) | > 90% |
| Carga del SSD | filas/s de la tabla PLE vs capacidad del disco (SATA 10–14K medido; HDD y NVMe estimados) | < 15K filas/s disponibles |
| Presión de RAM | GB libres tras pesos pinned + KV en RAM + sistema | < 2 GB → swap |
| Tokens por pasada | Strata 2,4–3,2 con MTP; Ollama 1 | < 1,8 |
| TTFT | segundos hasta el primer token | — |
| Decode sostenido | tok/s tras el prefill | — |
| Tiempo de carga | segundos y GB movidos por etapa | — |

**Definición única de limitante, para ambos motores:**
`factor_recurso = tok_s_ideal_sin_ese_recurso / tok_s_real`. El recurso con el **factor más alto**
es el cuello de botella y es el que debe brillar en el grafo. Si dos factores quedan a menos de
1,15×, mostrar **cuello de botella doble** (p. ej. PCIe + CPU en una RTX 5070 con IQ3_S: los
expertos viajan y la vez los calcula la CPU).

### 3. Tarjeta de veredicto

Una tarjeta compacta sobre la tabla, en lenguaje llano:

- **Quién gana y cuánto** («Strata 3,1× más rápido aquí»), con el ganador en el tono más caliente de
  la rampa, nunca en verde.
- **La causa en una frase**: «Ollama no puede mantener 66–76 GB residentes: 32 GB de RAM no bastan
  y la GPU de 12 GB no los aloja; termina haciendo page faults contra el disco».
- **Qué cambiaría el resultado**: la palanca concreta y su efecto estimado («subir a 64 GB de RAM
  hace que Strata pase de low-RAM a todo-en-RAM: +X%»). Si el resultado no se puede arreglar con
  ese control, decirlo explícitamente («ninguna cantidad de VRAM hace que Ollama quepa en 32 GB de
  RAM»).
- **Dónde Strata no gana.** Ningún modelo de la lista cabe entero en 32 GB de VRAM (el más pequeño,
  el Coder, son ~58 GB de fichero), así que el caso «ya cabe todo en GPU» no es alcanzable y no
  debe fingirse. Los casos reales que sí hay que mostrar: **GPU no soportada** (Strata no arranca
  con esa tarjeta salvo forzándola, Ollama sí), **sin GPU** (solo Ollama) y **UD-Q4_K_XL con GPU de
  12 GB** (7–8,5 tok/s: Ollama con un modelo pequeño puede ir mejor).

### 4. Barrido de punto de cruce

Un control para **barrer un eje** (VRAM 4→32 GB, RAM 16→128 GB, tipo de disco o tamaño de modelo) y
dibujar en el mismo eje las dos curvas de tok/s. Marcar:

- el punto donde **Ollama deja de caber** (línea discontinua + motivo),
- el punto donde **Strata cambia de régimen** (todo-en-RAM → low-RAM → expertos desde SSD),
- el **cuello de botella dominante por tramo** (la curva se pinta con el color del recurso que
  manda en esa zona).

El eje Y debe poder cambiarse a **coste local vs API** usando los datos de la sección siguiente.

### 5. Lado Ollama

No inventar cifras de Ollama: modelar el mecanismo y declararlo estimado.

- Ollama/llama.cpp necesita el **modelo completo residente** (VRAM o RAM vía mmap); si no cabe en
  RAM, hace page faults contra el disco y se hunde. Con un GGUF de 66–76 GB, en 32 GB de RAM
  directamente no cabe: el veredicto es «no arranca usable», no un número lento.
- El *spill* a CPU penaliza según la fracción de capas fuera de GPU y el ancho de banda RAM↔GPU.
- Sin especulación MTP nativa: 1 token por pasada.
- Sí parte capas entre varias GPU, pero sin el reparto VRAM+RAM+SSD ni el cache de expertos.
- Todo lo que se derive de ahí lleva asterisco y tooltip. Los números de Strata salen de la tabla
  de calibración; los de Ollama, del mecanismo.

---

## Benchmarks de hardware (ModelDock) — el eje económico

La web debe responder también a **«¿me compensa hacerlo en local o pagando una API?»**. Para eso,
los 29 perfiles de hardware de los benchmarks de Strata (medianas del carril ordinario para
Qwen3.8 Flash Next).

**Qué mide esta tabla:** rendimiento **sostenido bajo una carga mixta** — un solo flujo, primero
lectura y luego escritura, con una mezcla por defecto de **90% lectura / 10% escritura, 24 h/día**.
Sus números son **más bajos** que los de la tabla por tamaño: los 94 tok/s de Q2_0 son un pico en
chat corto; los ~48 tok/s de escritura de una RTX 5070 es lo que rinde de forma continua cuando el
90% del tiempo está procesando prompts largos. La tabla por tamaño manda en `CARGA`, `INFERENCIA` y
`VS`; esta manda en `ECONOMÍA`. Si un hardware aparece en las dos, mostrar ambas cifras etiquetadas
como «pico por tamaño» y «sostenido mixto», nunca un promedio.

### Vista `ECONOMÍA`

Controles: **mezcla lectura/escritura** (por defecto 90/10), **uso diario** (h/día),
**electricidad ($/kWh)**, **vida útil (años)** y **precios de API** (por defecto $0,10/M lectura y
$0,64/M escritura). Botón «Restablecer».

El coste local y la recuperación se **recalculan** al cambiar cualquiera de esos controles. Estas
son las fórmulas que reproducen la tabla publicada:

```
t_por_millon   = mezcla_lectura·1e6 / lectura_tok_s + mezcla_escritura·1e6 / escritura_tok_s
M_tok_dia      = (uso_h_dia · 3600) / t_por_millon
energia_dia    = watios · uso_h_dia / 1000 · precio_kwh
valor_api_dia  = M_tok_dia · (mezcla_lectura · precio_api_lectura + mezcla_escritura · precio_api_escritura)
local_$por_M   = (energia_dia + equipo / (vida_anios · 365)) / M_tok_dia
recuperacion_d = equipo / (valor_api_dia - energia_dia)
```

Con los valores por defecto ($0,15/kWh y 5 años) esto reproduce exactamente las columnas
publicadas. Si `valor_api_dia <= energia_dia`, la recuperación es infinita: mostrar «no compensa
frente a la API», nunca `Infinity` ni `NaN`.

### Los 29 perfiles

| Hardware | Memoria | Lectura tok/s | Escritura tok/s | Ajuste | Potencia | Equipo | M tok/día | Local $/M | Energía/día | Valor API/día | Recuperación | Evidencia |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **RTX 4090** · single-card | 24 GB | 4000 | 109,3 | Holgado | 550 W | $4199 | 75,8 | $0,056 | $1,98 | $11,67 | 433 d | Mediana |
| **RTX 5080** 16GB GDDR7 · single-card | 16 GB | 3712,5 | 80,7 | Holgado | 510 W | $2800 | 58,3 | $0,058 | $1,84 | $8,98 | 392 d | Mediana |
| **RTX 5070 Ti** 16GB · solo Q3 o menor | 16 GB | 2498,5 | 71,1 | Holgado | 450 W | $2380 | 48,9 | $0,060 | $1,62 | $7,53 | 403 d | Mediana |
| **RTX 3090** · single-card | 24 GB | 2094 | 86,5 | Holgado | 500 W | $2700 | 54,5 | $0,060 | $1,80 | $8,39 | 410 d | Mediana |
| **RTX 4070 Ti SUPER** 16GB GDDR6X · single-card | 16 GB | 1700 | 72 | Holgado | 435 W | $2140 | 45,0 | $0,061 | $1,57 | $6,94 | 398 d | Mediana |
| **RTX 5090** · single-card | 32 GB | 5803 | 168,4 | Holgado | 700 W | $8500 | 115,4 | $0,062 | $2,52 | $17,77 | 558 d | Mediana |
| **RTX 3090 Ti** · single-card | 24 GB | ~2255,1 | ~93,1 | Holgado | ~600 W | $2774 | 58,6 | $0,063 | $2,16 | $9,03 | 404 d | Estimación |
| **AMD RX 7900 XTX** 24GB GDDR6 · single-card | 24 GB | 1459,3 | 75,5 | Holgado | 475 W | $2000 | 44,5 | $0,063 | $1,71 | $6,85 | 389 d | Mediana |
| **AMD RX 9070 XT** 16GB GDDR6 · single-card | 16 GB | 1652 | 53,8 | Holgado | 454 W | $2000 | 35,9 | $0,076 | $1,63 | $5,54 | 513 d | Mediana |
| **Ryzen AI Max+ 395** 128 GB unificada (Radeon 8060S) | 128 GB | 1320 | 51,4 | Holgado | 170 W | $3500 | 32,9 | $0,077 | $0,61 | $5,06 | 786 d | Mediana |
| **2× RTX 5060 Ti** 16 GB c/u · dual-card | 32 GB | 1602 | 67,6 | Holgado | 480 W | $2960 | 42,3 | $0,079 | $1,73 | $6,52 | 618 d | Mediana |
| **RTX 5070** 12GB GDDR7 · single-card | 12 GB | 1443,2 | 48,3 | Holgado | 400 W | $2070 | 32,1 | $0,080 | $1,44 | $4,94 | 592 d | Mediana |
| **2× RTX 3090** 24 GB c/u · dual-card layer split | 48 GB | 2137,6 | 111,3 | Justo | 850 W | $4200 | 65,5 | $0,082 | $3,06 | $10,08 | 598 d | Mediana |
| **Mac Studio M5 Ultra** 96 GB (30C CPU / 64C GPU) | 96 GB | ~2284,8 | ~64,8 | Holgado | ~360 W | $5499 | 44,6 | $0,097 | $1,30 | $6,87 | 987 d | Estimación |
| **DGX Spark** 128 GB unificada | 128 GB | 2228,5 | 48,7 | Holgado | 170 W | $5100 | 35,2 | $0,097 | $0,61 | $5,41 | 1062 d | Mediana |
| **RTX PRO 6000 Blackwell** 96GB GDDR7 ECC · single-card | 96 GB | 8987,9 | 171,1 | Holgado | 720 W | $18.317 | 126,2 | $0,100 | $2,59 | $19,44 | 1087 d | Mediana |
| **2× RTX 3060** 12 GB c/u · dual-card layer split | 24 GB | 1239,8 | 41,3 | Holgado | 490 W | $1814 | 27,5 | $0,100 | $1,76 | $4,23 | 736 d | Mediana |
| **MacBook Pro M5 Max** 128 GB | 128 GB | 1310 | 67,3 | Holgado | 120 W | $6699 | 39,8 | $0,103 | $0,43 | $6,12 | 1177 d | Mediana |
| **2× TITAN RTX** 24 GB c/u · dual-card layer split | 48 GB | 1698,2 | 60,6 | Holgado | 710 W | $2881 | 39,6 | $0,104 | $2,56 | $6,10 | 812 d | Mediana |
| **AMD RX 6900 XT** 16GB GDDR6 · single-card | 16 GB | 466 | 47,6 | Holgado | 450 W | $1669 | 21,4 | $0,118 | $1,62 | $3,30 | 994 d | Mediana |
| **2× AMD RX 6900 XT** 16 GB c/u · dual-card layer split | 32 GB | 772,3 | 63 | Holgado | 750 W | $2138 | 31,4 | $0,123 | $2,70 | $4,83 | 1002 d | Mediana |
| **Mac Studio M5 Ultra** 256 GB (36C CPU / 80C GPU) | 256 GB | 2856 | 81 | Holgado | 360 W | $10.799 | 55,8 | $0,129 | $1,30 | $8,59 | 1481 d | Mediana |
| **Mac Studio M5 Max** 64 GB (40C GPU) | 64 GB | ~517,9 | ~36 | Holgado | ~180 W | $3799 | 19,1 | $0,143 | $0,65 | $2,95 | 1653 d | Estimación |
| **MacBook Pro M5 Max** 64 GB (40C GPU, chasis no declarado) | 64 GB | 517,9 | 36 | Holgado | 120 W | $5099 | 19,1 | $0,169 | $0,43 | $2,95 | 2028 d | Mediana |
| **Mac Studio M5 Max** 128 GB (40C GPU) | 128 GB | ~517,9 | ~36 | Holgado | ~180 W | $5399 | 19,1 | $0,188 | $0,65 | $2,95 | 2349 d | Estimación |
| **Mac mini M5 Pro** 64 GB (18C CPU / 20C GPU) | 64 GB | ~259 | ~18 | Holgado | ~110 W | $2899 | 9,6 | $0,207 | $0,40 | $1,47 | 2691 d | Estimación |
| **Mac Studio M4 Max** 128 GB (perfil oMLX con fuente) | 128 GB | 446,8 | 32,5 | Holgado | 145 W | $6500 | 17,0 | $0,241 | $0,52 | $2,61 | 3108 d | Mediana |
| **Mac Studio M3 Ultra** 512 GB (80-core) | 512 GB | 479,6 | 18,1 | Holgado | 330 W | $9499 | 11,7 | $0,548 | $1,19 | $1,80 | 15.580 d | Mediana |
| **RTX 4070** 12GB (GDDR6/GDDR6X según placa) · single-card | 12 GB | 1376 | 36,9 | Holgado | 350 W | — | 25,7 | — | $1,26 | $3,96 | — | Mediana |

### Reglas al usar esta tabla

- **No todos estos equipos los soporta Strata.** La matriz oficial es Windows/Linux con NVIDIA
  RTX 20+ o las AMD listadas, y 12 GB de VRAM o más. Los perfiles de **Apple Silicon y el DGX
  Spark** se midieron con otros motores (el del M4 Max es **oMLX**) y los **TITAN RTX** son Turing.
  Pueden aparecer en `ECONOMÍA` etiquetados con el motor con que se midieron, pero **no** deben ser
  seleccionables en `CARGA`/`INFERENCIA`/`VS`, y la web no debe afirmar que Strata funciona en un
  Mac.
- La columna **Ajuste** (Holgado / Justo) describe el perfil, no el hardware: «Justo» en 2× RTX 3090
  significa que el reparto va justo de espacio. Debe mostrarse como aviso.
- Las filas de **doble GPU** llevan un aviso de «requiere espacio en la caja, margen de potencia y
  planificación multi-GPU».
- La **RTX 4070 12 GB** no tiene precio de equipo: sin precio no hay $/M local ni recuperación.
  Mostrar «—» y explicar por qué, no inventar un precio.
- Las filas marcadas **Estimación** en la columna de evidencia usan el mismo asterisco y tooltip que
  el resto de estimaciones del proyecto.

---

## Estilo visual (referencia: `FONDO.png`)

La imagen de referencia es un **gradiente radial cálido tipo brasa**: centro brillante ámbar-amarillo
situado hacia el centro, cayendo a rojo y a vino casi negro en las cuatro esquinas, con viñeteado
suave y **grano de película muy fino**. El ~99% de los píxeles caen en tonos 0–45° y 330–15°: no
hay ni un verde ni un cian. Las transiciones son continuas (diferencia entre píxeles vecinos:
mediana 3, media 5 sobre la suma de canales), sin bordes duros ni bandas.

Paleta exacta, de oscuro a caliente, que es a la vez la **rampa de calor** de la simulación.
Declararla **una sola vez** como variables CSS en `:root` y referenciar siempre las variables:

```css
:root{
  --calor-900:#2b0308; --calor-800:#3d030d; --calor-700:#560d1b;
  --calor-600:#920c08; --calor-500:#ac191c; --calor-450:#ef2602;
  --calor-400:#f84402; --calor-300:#fd7c00; --calor-250:#fe9003;
  --calor-200:#feac04; --calor-150:#fcc205; --calor-100:#fdd813;
  --tinta:#f6e6d8; --tinta-suave:#c98a6a;
}
```

- **Fondo:** `radial-gradient` con el centro en ~52% x / 52% y, de `--calor-100` → `--calor-300` →
  `--calor-600` → `--calor-800`, más una capa de **grano** generada en canvas o con un
  `feTurbulence` de SVG a opacidad ~4%. Nada de degradados planos de dos colores.
- **Semántica de la rampa:** frío/oscuro = recurso en reposo, caliente = recurso trabajando. Un
  cuello de botella se representa con la zona **sobre-expuesta** (casi blanca-amarilla) y pulsante,
  no con rojo de error.
- **Modo VS:** los dos carriles comparten la misma rampa. Se distinguen por **textura y elevación**
  —el carril activo más brillante y con más glow, el inactivo en baja emisividad—, no por paletas
  distintas. La columna Δ usa la rampa para la magnitud y una flecha para el signo.
- **Paneles:** superficies oscuras translúcidas (`rgba(43,3,8,.72)`) con `backdrop-filter: blur()`,
  bordes de 1px en `rgba(253,200,5,.18)`, esquinas de 10–14px, sombras cálidas difusas.
- **Texto:** cuerpo en `--tinta`, títulos y datos en `--calor-100` / `--calor-200`, secundario en
  `--tinta-suave`. Tipografía: `font-family: Outfit, Inter, ui-sans-serif, system-ui, sans-serif`
  (Outfit es la que usa la app de Strata) y monoespaciada para números con
  `font-variant-numeric: tabular-nums`. Sin `@font-face` ni CDN: si la fuente no está instalada, se
  degrada a la del sistema.
- **Prohibido:** modo oscuro gris/azulado, neón cian/magenta, glassmorphism blanco, emojis como
  iconos y cualquier verde o azul en la visualización.
- **Movimiento:** 60 fps, `requestAnimationFrame`, easing suave, partículas de bytes y tokens, glow
  aditivo. Respetar `prefers-reduced-motion`.

---

## Restricciones técnicas

- **Un solo `index.html`** autocontenido: HTML + CSS + JS vanilla, sin build, sin Node, sin
  dependencias de red (ni CDN, ni fuentes externas).
- El grafo de memoria y el flujo de tokens en **`<canvas>`** (o SVG si sale más limpio); el resto de
  la UI en HTML/CSS.
- El modelo de simulación separado del render: una función pura
  `simularMotor(motor, hardware, carga) -> {cabe, motivoFallo, modoCarga, tiempoCarga, gbMovidos,
  tokS, ttft, usoVRAM, headroomVRAM, usoRAM, presionRAM, gbpsPCIe, filasSSD, capasEnCPU,
  aciertoCache, tokensPorPasada, factorPorRecurso, limitante}`, con `motor ∈ {"ollama","strata"}`.
  Esa función **no puede tocar `document` ni `canvas`**. El modo VS la llama dos veces con el mismo
  `hardware` y `carga` y deriva la tabla de Δ y el veredicto de esas dos salidas.
- **Un solo reloj y una sola ruta de actualización.** Una única función de refresco para toda la
  página; prohibido un `setInterval` o un bucle de animación por carril.
- **El grafo no decide el cuello de botella por su cuenta:** debe leer el campo `limitante` que
  devuelve `simularMotor()`. Prohibido que el render calcule su propio umbral.
- **El veredicto CABE / NO CABE / LOW-RAM sale de la fórmula** (`RAM ≥ expertos + ~10 GB` y la
  restricción de qué tamaños admite el low-RAM según la VRAM), no de una tabla de casos a mano.
- **Las fórmulas económicas van implementadas como código**, no como valores precalculados.
- El barrido de crossover reutiliza `simularMotor` muestreando el eje (mínimo 24 puntos, con
  interpolación), sin duplicar lógica, y emite los marcadores de «Ollama deja de caber» y «Strata
  cambia de régimen» como datos, no como texto pintado a mano.
- Responsive: de móvil (una columna, vista simplificada) a monitor grande (comparación lado a lado).
  Accesible: contraste AA, controles con `label`, navegación por teclado, `aria-live` en los
  veredictos, y la tabla de métricas con `<table>` real y `<caption>`.
- Sin backend, sin llamadas externas. Persistencia solo en `localStorage` para guardar el preset.
- Comentar en el código de dónde sale cada constante de rendimiento y enlazar la fuente (docs de
  Strata / benchmarks).

---

## Criterios de aceptación

1. Al cambiar la RAM de 32 → 64 GB con **IQ3_S**, la simulación pasa de **NO CABE** a **CABE**, y
   el tiempo de carga y los tokens/s cambian en pantalla sin recargar.
2. Con **32 GB de RAM + GPU de 24 GB + Q2_0** aparece el modo **LOW-RAM** y se explica por qué. Con
   **32 GB + GPU de 12 GB + IQ3_S** el veredicto es **NO CABE**: el low-RAM con GPU de 12–16 GB solo
   admite el Coder.
3. Al cambiar el disco de NVMe → HDD, la lectura de la tabla PLE se hunde y el cuello de botella se
   marca en el disco.
4. Con la **GTX 1080 Ti**: por defecto Strata la rechaza nombrando el motivo (compute 6.1 < 7.5), y
   existe la ruta forzada (`--gpus` + motor experimental CUDA 12) que sí la usa, más lenta y con
   aviso de experimental. Ollama funciona en ambos casos.
5. Al pasar de 32K a 262K de contexto, se ve el KV cache comiéndose la VRAM y el expert cache
   encogiéndose, y el decode cae en la banda medida (−13% a −22% según tamaño).
6. Con dos GPUs se anima el split por capas (tarjetas en serie, cada una con su propio cache de
   expertos) y se entiende que es paralelismo de capas, no de tensores.
7. Se reproduce el escenario de los benchmarks oficiales con los mismos tokens/s (±5%), midiendo
   **decode con prompt corto y prefill con prompt 32K por separado**.
8. En el modo `VS`, al mover cualquier slider, las dos columnas y la de Δ se actualizan en el mismo
   frame, con el mismo reloj y la misma carga de trabajo.
9. La columna **limitante** coincide con el recurso que está brillando en el grafo, porque ambos leen
   el mismo campo. Si dos factores quedan a menos de 1,15× se muestra cuello de botella doble.
10. El barrido de VRAM muestra el punto exacto donde Ollama deja de caber y el punto donde Strata
    cambia de régimen, con el motivo escrito en el gráfico.
11. Con `32 GB de RAM + RTX 5070 12 GB + IQ3_S`, el veredicto de Ollama es **«no cabe»** y el de
    Strata también es **«no cabe»** (50 GB de expertos + ~10 GB > 32 GB, y el low-RAM no está
    disponible con GPU de 12 GB). Ninguno muestra un tok/s inventado.
12. Hay al menos un escenario alcanzable donde **Strata no gana** y el veredicto lo dice: GPU no
    soportada, sin GPU, o UD-Q4_K_XL con GPU de 12 GB.
13. `parallel: 2` es seleccionable y ralentiza cada respuesta en una tarjeta de 12 GB.
14. El preset elegido se guarda en `localStorage` y se recupera al recargar.
15. La vista `ECONOMÍA` reproduce la tabla de ModelDock. Con los valores por defecto (90/10,
    24 h/día, $0,15/kWh, 5 años, API $0,10/$0,64 por millón), la fila **RTX 5070 12 GB** debe dar
    32,1 M tok/día, $1,44 de energía, $4,94 de valor API, $0,080/M local y 592 días de recuperación.
    Verificar además **RTX 4090** (75,8 / $1,98 / $11,67 / $0,056 / 433 d) y **2× RTX 3090**
    (65,5 / $3,06 / $10,08 / $0,082 / 598 d).
16. Al cambiar la mezcla a 50/50, el precio de la API o el coste del kWh, todas las columnas
    económicas se recalculan en vivo, y la recuperación pasa a «no compensa frente a la API» cuando
    el valor API es menor que la energía.
17. Los perfiles de Apple Silicon y DGX Spark aparecen **solo** en `ECONOMÍA`, etiquetados con el
    motor con que se midieron, y la web no afirma que Strata funcione en un Mac. En
    `CARGA`/`INFERENCIA`/`VS` no son seleccionables.
18. Las filas marcadas «Estimación» llevan el mismo asterisco y tooltip que el resto de
    estimaciones; la RTX 4070 sin precio muestra «—» en $/M y recuperación en vez de inventarse un
    precio.
19. Todo funciona abriendo el archivo directamente en el navegador, sin servidor.

Empieza por el modelo de simulación y su calibración, luego el modo VS y su tabla de métricas,
después la vista `ECONOMÍA`, después la animación y por último el escalado al estilo visual. Entrega
el `index.html` completo y, aparte, una lista de qué números son medidos y cuáles son extrapolaciones.

---

**Fin de la parte para pegar.** Todo lo que sigue es material de verificación y no debe incluirse
en el prompt.

---

# PARTE 2 — Checklist de validación

*Material de verificación. No se envía al agente al pedir la web; se usa al recibir el resultado.*

Se aplica sobre el `index.html` que resulte de la Parte 1. Cada ítem indica **qué hacer** y
**qué debe salir**.

Marcar solo lo comprobado por ti, no lo que la IA afirme haber hecho.

**Regla general:** cuando un ítem dice «abrir el archivo», es doble clic sobre el `.html`
(protocolo `file://`), sin servidor y sin errores en consola. Si algo solo funciona con
`npm run dev` o con un servidor local, ese ítem es un fallo.

### Etiquetas

- **`[C]` Comprobable en el código.** Lo audita la IA o tú abriendo el archivo en un editor.
  No requiere ejecutar nada.
- **`[N]` Solo en navegador.** Requiere ejecutar la página y mirar. La IA no puede comprobarlo.

---

## Bloque A — Integridad técnica

- [ ] **A1** `[C]` Un solo archivo `.html`, sin `node_modules`, sin `package.json`, sin `.js` ni
      `.css` aparte.
- [ ] **A2** `[N]` Abre con doble clic y funciona. Sin pantalla en blanco ni aviso de «ábreme con
      un servidor».
- [ ] **A3** `[C]` En el código no hay `http://` ni `https://` en `<link>`, `<script src>`,
      `@import`, `fetch()` ni `@font-face`. Buscar los cinco patrones: cero coincidencias.
- [ ] **A3b** `[N]` DevTools → Network: cero peticiones externas.
- [ ] **A4** `[N]` DevTools → Console: cero errores al cargar y tras 60 s de simulación.
- [ ] **A5** `[C]` JS vanilla: sin `import` de librerías, sin React/Vue/Three/Chart.js.
- [ ] **A6** `[C]` Existe una función pura `simularMotor(motor, hardware, carga)` separada del
      render. Dentro de esa función no aparecen `document`, `canvas`, `window`, `ctx` ni `innerHTML`.
- [ ] **A7** `[C]` Las constantes de rendimiento tienen comentario con su fuente. Buscar por
      nombre, no por valor (pueden estar escritas como `48 * 512`): `EXPERTOS`, `CAPAS`, `CHUNK`,
      `PREFILL`, `MTP`, `PLE`, `EXPERTS_PER_TOKEN`. Cada una cita docs de Strata o los benchmarks.
- [ ] **A8** `[C]` Sin `eval()` sobre texto ni `innerHTML` con datos del usuario.

---

## Bloque B — Criterios de aceptación

### B1. RAM 32 → 64 GB con IQ3_S
- [ ] **B1a** `[C]` El veredicto sale de la fórmula `RAM >= expertos + 10`. No debe haber una tabla
      de casos tipo `if (ram === 32)`.
- [ ] **B1b** `[N]` Preset `RTX 5070 12 GB + 64 GB`, modelo **IQ3_S**, contexto 32K. Con RAM en
      **32 GB** debe salir **NO CABE** (IQ3_S = 50 GB de expertos; con GPU de 12 GB el low-RAM no
      está disponible).
- [ ] **B1c** `[N]` Subir el slider de RAM a **64 GB**: el veredicto pasa a **CABE**, y el tiempo de
      carga y los tok/s cambian sin recargar la página.
- [ ] **B1d** `[N]` El cambio se ve en la animación (más expertos a RAM pinned), no solo en el
      número.

### B2. Modo low-RAM
- [ ] **B2a** `[N]` Con `32 GB de RAM + GPU de 24 GB + Q2_0` aparece **LOW-RAM** (expertos mapeados
      desde fichero) y se explica por qué.
- [ ] **B2b** `[N]` Con `32 GB + GPU de 12 GB + IQ3_S` el veredicto es **NO CABE**, no low-RAM.
      Con GPU de 12–16 GB el low-RAM solo admite el Coder.
- [ ] **B2c** `[C]` Existe en el código la restricción de qué tamaños admite el low-RAM según la VRAM.

### B3. NVMe → HDD
- [ ] **B3a** `[N]` Con cualquier preset que funcione, cambiar el disco a **HDD**: la lectura de la
      tabla PLE cae y el disco pasa a ser el limitante (brilla en el grafo y aparece en la columna
      limitante).
- [ ] **B3b** `[N]` Con **SATA SSD** sale un valor en la banda **10–14K filas/s** y el aviso del
      umbral (~15K/s).
- [ ] **B3c** `[C]` Los valores de HDD y NVMe en filas/s están marcados como estimación (solo el de
      SATA está documentado).

### B4. GTX 1080 Ti (dos rutas)
- [ ] **B4a** `[N]` Por defecto Strata la rechaza nombrando el motivo (compute 6.1 < 7.5 y/o
      11 GB < 12 GB), no un error genérico.
- [ ] **B4b** `[N]` Existe la ruta forzada (`--gpus` + motor experimental CUDA 12) que sí la usa,
      más lenta y con aviso de experimental.
- [ ] **B4c** `[N]` Ollama sigue funcionando en ambos casos. La página no se rompe.
- [ ] **B4d** `[N]` En el modo VS, el carril de Strata muestra el estado «no disponible» con el
      motivo.

### B5. Contexto 32K → 262K
- [ ] **B5a** `[N]` El KV cache crece en VRAM y el expert cache se encoge en la animación.
- [ ] **B5b** `[N]` El decode cae en la banda medida: −13% a −22% según tamaño (Q2_0 −19, IQ2_XS
      −20, IQ3_XXS −21, IQ3_S −13, Coder −22).
- [ ] **B5c** `[N]` A partir de 64K se representa el KV streamando desde RAM (solo la parte más
      leída en VRAM).

### B6. Dos GPUs
- [ ] **B6a** `[N]` Preset `RTX 5080 16 GB + RTX 3090 24 GB`: se anima el split por capas, tarjetas
      en serie, cada una con su propio cache de expertos.
- [ ] **B6b** `[N]` Se entiende que es paralelismo de capas, no de tensores.
- [ ] **B6c** `[C]` Ollama no está marcado como «no soporta multi-GPU»: parte capas, pero sin
      reparto VRAM+RAM+SSD ni cache de expertos por tarjeta.

### B7. Benchmarks oficiales (±5%)
El decode se mide con **prompt corto** y el prefill con **prompt de 32K**: son dos mediciones
distintas. Si la IA da los dos números del mismo escenario, B7 falla.

- [ ] **B7a** `[N]` Preset `RTX 5070 12 GB + Ryzen 5 7600 + 64 GB DDR5 + NVMe`, **prompt corto**:

| Modelo | Decode esperado | Obtenido | ✓ |
| --- | ---: | --- | --- |
| Q2_0 | 94 | ______ | [ ] |
| IQ2_XS | 79 | ______ | [ ] |
| IQ3_XXS | 62 | ______ | [ ] |
| IQ3_S | 53 | ______ | [ ] |
| Coder | 55 | ______ | [ ] |

- [ ] **B7b** `[N]` Mismo preset, **prompt de 32K**:

| Modelo | Prefill esperado | Obtenido | ✓ |
| --- | ---: | --- | --- |
| Q2_0 | 2.650 | ______ | [ ] |
| IQ2_XS | 2.090 | ______ | [ ] |
| IQ3_XXS | 1.750 | ______ | [ ] |
| IQ3_S | 1.620 | ______ | [ ] |
| Coder | 2.180 | ______ | [ ] |

- [ ] **B7c** `[N]` Preset AMD `RX 9070 XT 16 GB`: Q2_0 ≈ 60 / 1.160, IQ2_XS ≈ 52 / 1.110,
      Coder ≈ 44 / 1.420.
- [ ] **B7d** `[N]` Preset `RTX 3090 24 GB`: más rápido que la 5070 (~100–140 tok/s) y el porqué
      (más expertos cacheados) está explicado en pantalla.
- [ ] **B7e** `[C]` Los dos modelos grandes tienen anclas en el código: **UD-Q4_K_XL 7–8,5 tok/s**
      (64 GB + GPU 12 GB, exige NVMe y una sola NVIDIA) y **UD-IQ4_XS** lento por debajo de ~80 GB
      de RAM.

### B8. Modo VS coherente
- [ ] **B8a** `[C]` Una sola función de refresco para toda la página y ningún
      `setInterval`/`requestAnimationFrame` por carril. `requestAnimationFrame` debe aparecer como
      máximo un bucle de animación.
- [ ] **B8b** `[C]` El modo VS llama a `simularMotor` dos veces con el mismo objeto `hardware` y
      `carga` (misma referencia o copia idéntica).
- [ ] **B8c** `[N]` Al mover cualquier slider, las dos columnas y la de Δ se actualizan en el mismo
      frame, con un único reloj y la misma secuencia de tokens.

### B9. Tabla ↔ animación
- [ ] **B9a** `[C]` El grafo lee el campo `limitante` que devuelve `simularMotor()`. No debe haber
      comparaciones de umbral duplicadas en el render.
- [ ] **B9b** `[C]` Existe la rama de cuello de botella doble (dos factores a menos de 1,15×).
- [ ] **B9c** `[C]` La tabla es una `<table>` real con `<caption>`, no divs disfrazados.
- [ ] **B9d** `[N]` Fuerzo un SSD lento: la tabla no señala la CPU, y lo que brilla en el grafo es
      el disco.

### B10. Barrido de crossover
- [ ] **B10a** `[C]` La función de barrido emite los marcadores como datos (punto donde Ollama deja
      de caber, punto donde Strata cambia de régimen), no como texto pintado a mano.
- [ ] **B10b** `[C]` Reutiliza `simularMotor` y muestrea ≥ 24 puntos, sin duplicar lógica.
- [ ] **B10c** `[N]` Barrido de VRAM 4→32 GB: aparecen los dos puntos con el motivo escrito, y la
      curva se colorea según el cuello de botella dominante de cada tramo.

### B11. Caso crítico 32 GB + 5070 12 GB + IQ3_S
- [ ] **B11a** `[N]` Veredicto de Ollama: **no cabe** (66–76 GB no residen en 32 GB de RAM).
- [ ] **B11b** `[N]` Veredicto de Strata: **también no cabe** — 50 GB de expertos + ~10 GB > 32 GB,
      y el low-RAM no está disponible con GPU de 12 GB. Si la IA dice que Strata cabe ahí, ha roto
      su propia regla.
- [ ] **B11c** `[N]` Ninguno de los dos muestra un tok/s inventado para el caso que no cabe.

### B12. Strata puede perder o empatar
- [ ] **B12a** `[C]` El código contempla los tres casos reales donde Strata no gana: GPU no
      soportada, sin GPU, UD-Q4_K_XL con GPU de 12 GB.
- [ ] **B12b** `[N]` Pruebo uno de esos tres y el veredicto lo dice explícitamente.
- [ ] **B12c** `[C]` No se finge un caso «el modelo cabe entero en VRAM»: ninguno de la lista cabe
      en 32 GB (el menor, Coder, son ~58 GB de fichero).

### B13. `parallel: 2`
- [ ] **B13a** `[C]` Existe la opción `parallel` (1 o 2) en el modelo de simulación.
- [ ] **B13b** `[N]` Con `parallel: 2` en una tarjeta de 12 GB, cada respuesta se ralentiza.

### B14. Persistencia
- [ ] **B14a** `[C]` Hay escritura y lectura de `localStorage` para el preset.
- [ ] **B14b** `[N]` Recargo la página y el preset vuelve.

### B15. Sin servidor
- [ ] Cubierto por A2. Si hubo que levantar un servidor, B15 es fallo.

---

## Bloque C — Estilo visual (contra `FONDO.png`)

- [ ] **C1** `[C]` El fondo es un `radial-gradient`, no lineal.
- [ ] **C2** `[C]` La paleta está declarada una sola vez en `:root` como variables (`--calor-900` …
      `--calor-100`) con los 12 hex de la rampa, y el resto del CSS referencia las variables.
      Buscar hex sueltos fuera de `:root`: no debe haber ninguno. No buscar los hex uno a uno: si
      se usaron `oklch()` o `hsl()` la búsqueda falla y el trabajo puede estar bien. Lo que importa
      es que la rampa esté completa y centralizada.
- [ ] **C3** `[C]` Cero verdes y cero cianes. Auditar las variables de `:root` y cualquier color
      literal fuera de la rampa: los tonos válidos están en 0–45° y 330–360°. No usar la búsqueda
      `hsl(1` / `hsl(2`: `hsl(15,…)` es un tono válido de la rampa y daría falso positivo.
- [ ] **C4** `[C]` Hay capa de grano (canvas o `feTurbulence`) a opacidad ~4% y viñeteado en las
      esquinas.
- [ ] **C5** `[N]` Semántica de la rampa en movimiento: reposo = oscuro, trabajando = caliente,
      cuello de botella = sobre-expuesto y pulsante, nunca rojo de error plano.
- [ ] **C6** `[N]` En el modo VS los dos carriles comparten la misma rampa y se distinguen por
      brillo/elevación, no por paletas distintas.
- [ ] **C7** `[C]` Paneles oscuros translúcidos con `backdrop-filter: blur()`, bordes de 1px en tono
      ámbar a baja opacidad, esquinas 10–14px.
- [ ] **C8** `[C]` Pila de fuentes con degradación al sistema (`Outfit, Inter, ui-sans-serif,
      system-ui`) y sin `@font-face` ni CDN. Números con `font-variant-numeric: tabular-nums`.
- [ ] **C9** `[C]` Sin emojis como iconos, sin glassmorphism blanco, sin neón cian/magenta, sin modo
      oscuro gris/azulado.
- [ ] **C10** `[C]` Existe la rama `@media (prefers-reduced-motion: reduce)` que atenúa o detiene la
      animación.
- [ ] **C10b** `[N]` Con `prefers-reduced-motion` activo en el sistema, la animación se atenúa.

**Prueba de contraste:** poner el `FONDO.png` al lado de la web. Si la web parece un dashboard
oscuro con acentos naranjas en vez de la foto, C1–C5 han fallado aunque los hex estén.

---

## Bloque D — Honestidad numérica

- [ ] **D1** `[C]` Todo número que no venga de la tabla de calibración lleva asterisco y tooltip
      («estimación del modelo de simulación, no medido»).
- [ ] **D2** `[C]` Los números de Ollama están marcados como derivados del mecanismo, no medidos.
- [ ] **D3** `[N]` No hay cifras de Ollama para un modelo que no cabe: el veredicto es «no cabe».
- [ ] **D4** La IA entregó, aparte del código, la lista de qué es medido y qué es extrapolado. Si no
      la entregó, pedírsela.
- [ ] **D5** `[C]` Los umbrales reales están bien en el código: 12 GB de VRAM mínimos, compute
      ≥ 7.5, `RAM ≥ expertos + ~10 GB`, umbral PLE ~15K filas/s, chunks de 8.192 tokens, 2,4–3,2
      tokens por pasada, 24.576 expertos, ~10 por token.

---

## Bloque E — Accesibilidad y responsive

- [ ] **E1** `[N]` 375 px de ancho: una columna, vista simplificada, nada cortado ni desbordado.
- [ ] **E2** `[N]` 1440 px: comparación lado a lado legible.
- [ ] **E3** `[C]` Todos los controles tienen `<label>` asociado y el panel de hardware es operable
      solo con teclado. Los sliders son `<input type="range">` reales.
- [ ] **E4** `[C]` Los veredictos cambian en una región con `aria-live`.
- [ ] **E5** `[N]` Contraste AA en texto sobre los paneles. El blanco roto `#f6e6d8` sobre
      `rgba(43,3,8,.72)` pasa; el ámbar sobre ámbar, no.

---

## Bloque F — Benchmarks de hardware (ModelDock)

- [ ] **F1** `[C]` Las fórmulas de coste están en el código, no los valores precalculados. Buscar
      `t_por_millon`, `M_tok_dia`, `energia_dia`, `valor_api_dia`, el cálculo de `local` por millón y
      el de recuperación. Los números de la tabla no deben estar como constantes literales de salida.
- [ ] **F2** `[C]` Los 29 perfiles están en los datos, con la columna evidencia (Mediana /
      Estimación) conservada.
- [ ] **F3** `[N]` Con los valores por defecto (90/10, 24 h/día, $0,15/kWh, 5 años, API
      $0,10/$0,64), la fila **RTX 5070 12 GB** debe dar: 32,1 M tok/día · $1,44 energía · $4,94
      valor API · $0,080/M local · **592 d** de recuperación.
- [ ] **F4** `[N]` **RTX 4090**: 75,8 · $1,98 · $11,67 · $0,056 · **433 d**. **2× RTX 3090**:
      65,5 · $3,06 · $10,08 · $0,082 · **598 d**.
- [ ] **F5** `[N]` Cambiar la mezcla a 50/50, o el kWh, o los precios de API: todas las columnas se
      recalculan en vivo.
- [ ] **F6** `[N]` Cuando el valor API cae por debajo de la energía, la recuperación se muestra como
      «no compensa frente a la API», no como un número ni como `Infinity` ni `NaN`.
- [ ] **F7** `[C]` Los perfiles de Apple Silicon y DGX Spark no son seleccionables en
      `CARGA`/`INFERENCIA`/`VS`; solo aparecen en `ECONOMÍA`, etiquetados con el motor con que se
      midieron (p. ej. oMLX en el M4 Max).
- [ ] **F8** `[C]` Las filas marcadas Estimación usan el mismo mecanismo de asterisco/tooltip que el
      resto de estimaciones del proyecto.
- [ ] **F9** `[N]` La **RTX 4070 12 GB** (sin precio de equipo) muestra «—» en $/M local y en
      recuperación. No se inventa un precio.
- [ ] **F10** `[C]` No se promedian las dos tablas. Existe separación explícita entre «pico por
      tamaño» y «sostenido mixto». Ninguna vista debe mezclar los 94 tok/s de Q2_0 con los 48,3
      tok/s de la RTX 5070.
- [ ] **F11** `[C]` Las filas de doble GPU llevan el aviso de caja / margen de potencia /
      planificación multi-GPU, y la columna Ajuste (Holgado/Justo) se muestra.
- [ ] **F12** `[N]` El barrido de crossover puede usar coste local vs API como eje Y alternativo a
      tok/s.

---

## Recuento

| Bloque | Ítems | `[C]` en código | `[N]` en navegador |
| --- | ---: | ---: | ---: |
| A Integridad | 9 | 6 | 3 |
| B Criterios | 45 | 16 | 29 |
| C Estilo | 11 | 8 | 3 |
| D Honestidad | 4 | 3 | 1 |
| E Accesibilidad | 5 | 2 | 3 |
| F Benchmarks ModelDock | 12 | 6 | 6 |
| **Total** | **86** | **41** | **45** |

D4 no lleva etiqueta: no es una comprobación de código ni de navegador, es una entrega (la lista de
qué es medido y qué es extrapolado). Pedirla aparte.

**Reparto:** la IA se autoaudita solo los 41 `[C]` con la tabla de evidencia del prompt de auditoría.
Los 45 `[N]` son una sesión de 20–25 minutos en el navegador. Prioridad entre ellos: B1b–B1c, B2b,
B3a, B7a–B7b, B9d, B11b, B12b, C5–C6 y F3–F6.

---

## Criterios de corte

Con uno solo que falle, se rechaza el entregable.

| # | Corte |
| --- | --- |
| 1 | Necesita servidor o build para funcionar (A2, B15). |
| 2 | Peticiones externas o errores en consola (A3b, A4). |
| 3 | Al mover un slider no cambia nada en la simulación (B1c). |
| 4 | Los números de los benchmarks oficiales no salen, o salen midiendo decode y prefill en el mismo escenario (B7a–B7b). |
| 5 | La tabla de cuello de botella y la animación se contradicen (B9a, B9d). |
| 6 | Inventa tok/s de Ollama para un caso que no cabe (D3, B11c). |
| 7 | Dice que IQ3_S cabe en 32 GB de RAM, o que el low-RAM aplica a cualquier tamaño con GPU de 12 GB (B2b, B11b). |
| 8 | La paleta tiene verdes/cianes o el fondo es un degradado plano (C1–C3). |
| 9 | La vista ECONOMÍA tiene los resultados hardcodeados en vez de calcularlos (F1), o se inventa el precio de la RTX 4070 (F9), o promedia las dos tablas de rendimiento (F10). |

---

## Prompt de auditoría

> Aquí está el `index.html` que generaste y el checklist de validación (la Parte 2 de este
> documento). No lo reescribas entero.
>
> Autoaudita únicamente los ítems marcados `[C]`. Para cada uno, en una tabla: **ítem · estado
> (cumple / no cumple / no lo puedo comprobar) · dónde en el código (línea o función) · evidencia
> textual** (el fragmento concreto que lo demuestra).
>
> Los ítems `[N]` no los audites: requieren navegador y los compruebo yo. Si crees que uno de esos
> no puede fallar, dilo en una línea, pero no lo marques como cumplido.
>
> Arregla solo los `[C]` que no cumplan, en parches concretos con el fragmento de código afectado.
> No toques los que ya cumplen.
>
> Verifica en particular estos cinco, que son los que más se rompen:
>
> 1. `simularMotor()` no toca `document` ni `canvas` (A6).
> 2. El render lee el campo `limitante` que devuelve `simularMotor()` y no calcula su propio umbral
>    (B9a).
> 3. El veredicto IQ3_S + 32 GB de RAM + GPU de 12 GB es NO CABE, no low-RAM (B2b, B11b).
> 4. Decode y prefill se calculan en escenarios de prompt distintos (B7a, B7b).
> 5. Las fórmulas económicas están en el código y no los resultados precalculados, y ninguna vista
>    mezcla los picos por tamaño con los valores sostenidos de ModelDock (F1, F10).
