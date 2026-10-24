# INFORME FINAL — MISIÓN VIII: Bases PRECODI re-importadas y paridad «literal» en la web

**Fecha:** 24 de octubre de 2026 · **Repositorio:** `Nardian90/Precost` · **Rama base:** `main` (`43e6e64`, MISIÓN VII)

**Motivo:** el propietario re-entregó las fuentes históricas perdidas en el reinicio del servidor (`AUXILIAR_PRECODI`, archivo 2) junto al instalador oficial SIECONS 11 de 2025 (archivo 1), y pidió lograr la paridad «literal» total. La web pública (MISIÓN VI/VII) funcionaba hasta ahora sin las bases PRECODI: sin normas de composición, sin nomencladores históricos y con el buscador del catálogo excluido del artefacto estático. Esta misión cierra esa brecha en dos fases: **(A)** re-importar TODAS las bases a la BD local y **(B)** embeber esos mismos datos en la web pública para que las funciones de servidor funcionen idénticamente sin servidor.

---

## 1. Auditoría previa (archivos entregados por el propietario)

| Archivo | Contenido verificado | Tratamiento |
|---|---|---|
| Archivo 1 (ZIP, 42,8 MB) | `SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe` (43,2 MB, SHA-256 `e51befff…2368`) — instalador oficial SIECONS 11 de julio de 2025 | Solo custodia: NO se ejecuta ni se publica (material con copyright de terceros; el repositorio es público). Sirve como referencia del artefacto comercial con el que se compara la paridad. |
| Archivo 2 (RAR5, 25,3 MB) | `AUXILIAR_PRECODI`: `Codigo (PRECODI)/` con 7.21, 7.22, 8.15/SBD2008_815.mdb, código.mdb raíz 2017, Preambulos, `Codigo.exe`, 35 preámbulos `.doc`, ayuda DeurisPreambulos | **Fuentes de datos re-importadas** (es lo que faltaba desde el reinicio del servidor, documentado en INFORME_FASE_V §limitaciones). Extraído con unrar 7.12 (RAR5). Los `.mdb` y `.exe` originales NO se publican: solo sus datos ya transformados. |

## 2. Fase A — Re-importación completa de las bases PRECODI

Ejecutada con el importador verificado de MISIÓN III-B (`scripts/importar_precodi.py`), transaccional e idempotente, verificando el SHA-256 de cada `.mdb` antes y después de importarlo (modo solo lectura):

| Versión | Estado | Partidas | Recursos | Normas | Componentes |
|---|---|---|---|---|---|
| PRECONS_III 2025-06-06 (embebida) | ya estaba (idempotente) | 15.912 | 4.382 | 0 | 0 |
| PRECODI 2007-v7.21 | **importada** | 15.347 | 4.335 | 73.962 | 3.674 |
| PRECODI 2007-v7.22 | **importada** | 15.351 | 9.112 | 73.978 | 3.886 |
| PRECODI 2017-raíz (canónico) | **importada** | 15.351 | 9.112 | 73.978 | 3.886 |
| PRECODI 2007-v7.21-Preambulos | referencia duplicada de 7.21 (verificado por hash: sin filas propias) | — | — | — | — |
| PRECODI 2011-sbd2008 (+ priorizadas) | **importada** | 15.359 | 57.740 | 74.047 | 3.929 |

Con las priorizadas de SBD: normas descriptivas (2.360), RH extendida (57.838), tarifas de transporte (22.510), obras (28) y colecciones (27).

**Hallazgo verificado:** los datos útiles de `2017-raíz` y `2007-v7.22` son **idénticos bit a bit** (los JSON exportados coinciden en SHA-256; los `.mdb` difieren solo en metadatos Jet). La raíz 2017 es la canónica de la serie 7.22.

### Tests degradados reparados (la batería completa pasa por primera vez desde el reinicio)

Los fallos de las suites no eran de código: eran expectativas escritas contra la BD degradada (ids literales de la numeración pre-reinicio y estado «sin normas»). Se repararon resolviendo versiones **por nombre**, nunca por id literal:

- `tests_iiic`: 3 literales `version_id=3` → vid dinámico de `2017-raíz`. Ahora **21/21** (antes 0/21).
- `tests_v`: 6 fallos eran expectativas del estado degradado (defecto del servidor documentado: con BD completa es `2017-raíz`; las pruebas de recursos pasan a `version_id` de 2025 explícito). Ahora **28/28**.
- `tests_iv`: 4 fallos de datos desaparecen solos con las bases. Ahora **19/19** (antes 15/19).
- `fase3f_tests`: migraciones 0001..0003 en orden (0003 se añadió legítimamente en III-C). Ahora **24/24**.

## 3. Fase B — Paridad «literal» en la web estática

### 3.1 Arquitectura

```
bd/precodi.db ──(generar_datos_web.py, solo lectura)──▶ app/web-datos/*.json
                                                              │ (commit: el build de
                                                              │  Actions NO necesita BD)
                              construir_web.py ──────────────┤
                              (verifica manifest sha256)      ▼
                                         dist/index.html + overlay/×5 + data/×15
                                                               │ GitHub Pages
                                                               ▼
                                        https://nardian90.github.io/Precost/
```

- **`scripts/generar_datos_web.py`** exporta la BD a JSON compactos deterministas: `i.json` (índice con los ids de la BD, conteos, slugs), `p-<versión>.json` (partidas), `n-<versión>.json` (normas por partida + descomposición de juegos/semielaborados), `r-<versión>.json` (nomenclador) y `manifest.json` (SHA-256 de cada archivo). Verificación doble: conteos BD↔JSON al generar **y** al releer. Resultado: 15 archivos, 59,3 MB, 5 versiones.
- **`app/overlay/estatico.js`** (quinto overlay, **web-only**, no lo inyecta el servidor local): expone `window.__pcodEstatico` con réplicas **exactas** de los 5 endpoints del servidor — `/api/versiones`, `/api/partidas`, `/api/partida`, `/api/recursos` y `/api/descomposicion` — incluyendo los mismos textos de advertencia, el precio de respaldo propio cuando la versión de precios no trae el recurso, los duplicados, `fuentes_precio` y la verificación CMMN/CHMN/CEMN con la MISMA tolerancia `|Δ| ≤ max(0.0001·N, Σ|coef·precio|·6e-8)`. Usa los ids de la BD reales (sin re-mapeos) y búsqueda LIKE ASCII-insensitive como SQLite.
- **`precodi.js`** (buscador del catálogo): todos sus `fetch` ahora tienen `.catch` y caen a la capa embebida — **eliminada la razón histórica de su exclusión de la web** (búsquedas colgadas sin servidor, documentada en MISIÓN VI).
- **`recursos.js`**: sin servidor, si existe `__pcodEstatico` el modo pasa a «web con datos embebidos» (no degradación): las descomposiciones, la búsqueda del nomenclador y la búsqueda de catálogo usan la capa estática con el MISMO post-proceso (incluido el vínculo automático al presupuesto). Los selectores de versión de normas y fuente de precios también se ofrecen en modo web.
- **`construir_web.py`**: `OVERLAYS_WEB` = 5 (estatico.js primero) y copia `app/web-datos → dist/data` verificando el SHA-256 de cada archivo en origen y destino.

### 3.2 Prueba de equivalencia automatizada (tests_viii)

`scripts/tests_viii.py` + `tests_viii_runner.js` ejecutan el overlay **real** (`estatico.js` en Node con shim de `fetch` al disco) contra el **servidor real** (BD completa) y comparan respuesta por respuesta:

| Prueba | Qué verifica | Resultado |
|---|---|---|
| E1 | `/api/versiones`: mismas versiones, conteos y orden | ✓ |
| E2 | búsquedas por versión (5 versiones × 4 consultas): mismos códigos, orden, costos | ✓ |
| E3 | partidas con normas: mismos recursos y MISMO veredicto de verificación | ✓ |
| E4 | descomposiciones completas: componentes, precios, **advertencias textuales**, duplicados, fuentes_precio, precios cruzados 7.21→2017 | ✓ |
| E5 | nomenclador: mismos resultados, `sin_precio`, ambigüedades | ✓ |
| C1 | servidor inyecta SOLO sus 4 overlays (estatico.js es web-only); dist lleva 5 en orden | ✓ |
| C2 | HTML original intacto + `dist/data` íntegro contra manifest | ✓ |
| C3 | sintaxis `node --check` ×5 | ✓ |
| D1 | índice embebido = BD (conteos por versión) | ✓ |

**11/11 OK** (tolerancias documentadas: subtotales ≤ 1e-6 por double-vs-Decimal; el resto exacto).

### 3.3 Validación V recalibrada (los pasos de norma se activan)

Con las bases presentes, los pasos 17/18/18b de `validar_v_navegador.sh` —pendientes desde MISIÓN V— se ejecutan por primera vez. La recalibración necesaria (documentada en el propio script): precios dinámicos (el nomenclador por defecto ahora es 2017-raíz), BASE de las filas H/E de la norma activas, `parseFloat` de totales (el display añade el paréntesis de referencia), secuencia del paso 17 (el botón «Cargar normas» requiere la palomita quitada, manual pág. 34) y contrato del paso 13 (la norma de B es su snapshot propio del vínculo automático, III-C). **Resultado: 25 verificados · 0 fallos · 0 pendientes** (antes 23✓/0✗/3⏸ con los pasos de norma inalcanzables).

## 4. Pruebas ejecutadas (2026-10-24, todas reales)

| Suite | Resultado |
|---|---|
| `tests_iiib` | **21/21 OK** |
| `tests_iiic` | **21/21 OK** |
| `tests_iv` | **19/19 OK** |
| `tests_v` | **28/28 OK** |
| `tests_vii` | **15/15 OK** |
| `tests_viii` (nueva) | **11/11 OK** |
| `fase3f_tests` | **24/24 OK** |
| `validar_v_navegador` | **25✓/0✗/0⏸** (pasos de norma ejecutados) |
| `validar_vii_navegador` | **21/21** × 3 modalidades (servidor, dist, URL pública) |
| `prevalidar_web_estatica` (12 bloques) | **18/18 ✓** en dist local **y** 18/18 ✓ contra la URL pública |

Integridad verificada en todo momento: HTML original `50d3cf28…5cbaa2` byte-idéntico; BD en modo solo lectura; `dist/` sin bases de datos ni ejecutables (auditoría de prohibidos ampliada en tests_viii C2).

## 5. Publicación y despliegue

Rama `viii-paridad-web` con commits atómicos (a14bd6e → 4c902c4) + integración fast-forward a `main` (autorizada por el propietario; el token no tiene `Pull requests:write`). Runs de Actions: `40058508776` (4c902c4) **completed/success**; el workflow vuelve a construir `dist/` desde el código fuente y a verificar el hash del original antes de desplegar. La web sirve ahora el índice y los datos (`/data/i.json`, `/data/n-2017-raiz.json` 10,7 MB, `/data/r-2011-sbd2008.json` 5,4 MB — todos HTTP 200 verificados).

## 6. Validación final de la URL pública (navegador real)

`prevalidar_web_estatica.sh https://nardian90.github.io/Precost` — **18/18 ✓**: título, 5 overlays relativos, capa `__pcodEstatico` ejecutada, índice con las 4 versiones con normas, núcleo operativo, localStorage, catálogo embebido >10k, aviso «Modo web — datos PRECODI embebidos», **norma de 012141 renderizada desde los datos embebidos con inputs de edición (18)**, descomposición **vinculada y persistida** en el presupuesto, panel PRECODI en modo web con búsqueda «roca» (60 resultados), detalle con verificación CMMN/CHMN/CEMN contra la fuente, selector con las 5 bases y 0 errores de consola. Evidencias: `docs/datos/viii_publico_01_catalogo.png` y `viii_publico_02_descomposicion.png`.

## 7. Qué funciona hoy igual en la web y en local (paridad «literal»)

- Consulta del catálogo PRECODI por código o descripción en **las 5 bases** (2025, 7.21, 7.22, 2017-raíz, SBD2008) con costo MN de la versión elegida.
- Descomposición por partida (normas) con recursos, coeficientes, precios, descomposición anidada de juegos/semielaborados, subtotales por tipo y **verificación contra la fuente** (CMMN/CHMN/CEMN con la tolerancia documentada).
- Comparación de la misma partida **entre versiones** y fuente de precios cruzada (p. ej. normas 7.21 con precios 2017).
- Nomenclador de recursos para «añadir recurso propio» (S-050) con aviso de unidad distinta y ambigüedades.
- Edición S-050/S-052 (indicadores M/H/E, especificación, cantidad/precio) **persistente solo en el presupuesto**; S-080 calculadora; S-005 respaldo/restauración completo; exportaciones XLSX/PDF/Word/JSON.
- Diferencia única (por diseño): la web no tiene backend — todo lo anterior funciona desde los datos publicados; la BD editable con los 6 catálogos vive solo en la ejecución local.

## 8. Pendientes del propietario

1. **Rotar el token** pegado en el chat (tiene permisos de escritura en el repositorio).
2. Decidir la **licencia** del repositorio (sigue pendiente desde MISIÓN VI).
3. Los preámbulos `.doc` (35) y la ayuda DeurisPreambulos de `AUXILIAR_PRECODI` quedan custodiados fuera del repositorio público (contenido con copyright); si se quieren consultar desde PRECOST habría que extraerlos a texto y decidir su licencia.
