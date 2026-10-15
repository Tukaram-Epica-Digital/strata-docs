# Simulador visual Ollama vs Strata — especificación

*Uso: pegar este documento completo en un agente de código. Si es posible, adjuntar también la
imagen `FONDO.png`; el bloque «Estilo visual» contiene su paleta exacta por si no se puede adjuntar.*

---

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
