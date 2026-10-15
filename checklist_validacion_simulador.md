# Checklist de validación — Simulador Ollama vs Strata

Complemento de `prompt_simulador_strata.md`. Se usa al recibir el `index.html`. Cada ítem indica
**qué hacer** y **qué debe salir**.

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

> Aquí está el `index.html` que generaste y el checklist de validación. No lo reescribas entero.
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
