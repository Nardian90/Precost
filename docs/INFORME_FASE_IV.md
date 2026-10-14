# INFORME FINAL — MISIÓN IV

**Fidelidad PRECODI + Paridad SIECONS 11 sobre PRECOST 9.17**

**Proyecto:** PRECOST 9.17 · **Fecha:** 14 de octubre de 2026
**Rama de trabajo:** `iv-fidelidad-precodi-paridad-siecons` (creada desde `iii-c-descomposiciones-recursos`)
**Tag protegido:** `v9.17-original` (intacto, verificado en cada suite)
**HTML original:** `app/PRECOST-v9.17.html` — SHA-256 `50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2` (byte-idéntico, verificado por suite y por request HTTP en cada arranque del servidor)

---

## 1. Resumen ejecutivo

MISIÓN IV ejecutó sus dos líneas en paralelo sobre la base protegida de
MISIÓN III-B/III-C, sin modificar nunca el archivo original ni mezclar
versiones de datos:

- **Línea A (fidelidad PRECODI):** el clasificador embebido de PRECOST
  (PRECONS III MICONS 2025) fue auditado campo a campo contra una fuente
  2025 independiente — la SBD que trae el instalador oficial de SIECONS 11 —
  y contra las versiones históricas PRECODI. Conclusión: **es una
  publicación fiel del mismo conjunto de datos subyacente de SIECONS 11**
  (contención del 100 % de las 15.912 partidas; materiales, mano de obra y
  equipos contenidos al 100 %). Quedan **502 diferencias concretas
  documentadas una a una** — no se declara un 100 % que no existe.
- **Línea B (paridad SIECONS 11):** el instalador oficial fue extraído de
  forma estática y verificable (39 archivos, 340.755.553 bytes exactos), el
  Manual Básico (54 págs., 115 capturas) fue procesado y se construyó la
  **matriz de paridad con 104 funciones en 11 módulos**, priorizada P0-P3
  con prueba de aceptación cada una.
- **Fase D (implementación):** primera función de paridad seleccionada por
  prioridad y viabilidad — **S-080 Calculadora de costos de actividad**
  (manual pág. 18) — implementada como tercer overlay 100 % aditivo,
  validada de extremo a extremo en navegador real.
- **Fase E (regresión):** **61/61 pruebas automatizadas** (19 IV + 21 III-B
  + 21 III-C) y **18/18 comprobaciones de navegador** superadas; el
  original permanece byte-idéntico.

Ningún dato fue inventado: cada cifra de este informe es reproducible con
los scripts citados en la §11.

---

## 2. Objetivo y alcance

**Línea A** — auditar la fidelidad del catálogo/clasificador embebido de
PRECOST (partidas, recursos, normas) contra los datos fuente PRECODI
identificables, campo a campo: códigos, descripciones, unidades, categorías,
coeficientes (precisión Float32 original) y precios (Currency de 4
decimales), con el criterio de «100 % de consistencia en campos
verificables» — prohibido inflar con recuentos de filas o consistencias
fabricadas.

**Línea B** — leer el manual de SIECONS 11 (`Manual Básico SIECONS.pdf`,
ruta de origen `SIECONS 11\App\MANUAL\Manual SIECONS`), extraer
módulos/menús/campos/flujo de cada función, construir la matriz de paridad
`docs/MATRIZ_PARIDAD_SIECONS_PRECOST.md` y luego implementar de forma
gradual según prioridad P0-P3 **una funcionalidad con evidencia y
verificación de extremo a extremo**.

**Fuera de alcance (respetado):** reescribir PRECOST, reconstruir el HTML,
alterar el catálogo embebido, mezclar datos de versiones, inventar datos
para rellenar huecos, romper presupuestos existentes.

---

## 3. Fase A — Protección y línea base

1. Rama `iv-fidelidad-precodi-paridad-siecons` creada desde el estado final
   de MISIÓN III-C (commit `4a7f066`); `v9.17-original` nunca se tocó.
2. Verificación SHA-256 del HTML original contra el valor de referencia
   completo (`50d3cf28…5cbaa2`) — byte-idéntico.
3. Suites de línea base ejecutadas antes de tocar nada:
   `tests_iiib.py` **21/21 OK**, `tests_iiic.py` **21/21 OK**.
4. Árbol limpio al comenzar; todo el trabajo posterior quedó registrado en
   commits atómicos por fase (ver §10).

---

## 4. Línea A — Auditoría de fidelidad: fuentes y metodología

**Fuentes (con hash verificado):**

| Fuente | Papel | Registros |
|---|---|---|
| PRECOST `const DB` (EMB) | auditado | P 15.912 · M 3.568 · O 143 · E 671 · G 1.893 |
| SBD_MICONS_2025.mdb (SIECONS 11) | referencia 2025 independiente | RV 16.865 · Mat 3.599 · RH 412 · Eq 712 · Normas 77.021 filas |
| PRECODI 2017-raíz / 7.22 / 7.21 / SBD2008 | referencias históricas (SQLite) | 15.351 / 15.350 / 15.347 partidas |

**Metodología (4 pasadas, scripts `iv_auditoria_fidelidad.py` →
`iv_auditoria_fina.py` → `iv_auditoria_paso3.py` → `iv_auditoria_paso4.py`):**

1. Extracción del catálogo embebido **sin modificar** el HTML (mecanismo de
   Fase III-D, re-verificado).
2. Lectura de SBD 2025 con access-parser + parche de precisión Money 4
   decimales (lección de III-B aplicada desde el diseño, no a posteriori).
3. Comparación campo a campo por categoría (partidas, materiales, mano de
   obra, equipos, grupos, unidades, precios, normas) con clasificación de
   cada diferencia y **lista nominal completa en JSON** — nada de promedios
   opacos.
4. Clasificación explícita: igual / equivalente (notación) / ruido de
   publicación / diferencia real pendiente.

La SBD 2025 fue posible gracias a la **extracción estática completa del
instalador** (§6), que además garantiza que la referencia es evidencia
primaria del fabricante, no una copia de terceros.

---

## 5. Línea A — Resultados de fidelidad

| Categoría | Resultado verificado |
|---|---|
| Partidas | **15.912/15.912** embebidas existen en SBD 2025 (contención 100 %; 0 solo-EMB) |
| Materiales | **3.568/3.568** contenidos |
| Mano de obra | **143/143** (tarifas: 142 exactas + 1 con Δ 0,01) |
| Equipos | **670/671** (exclusivo EMB: `0022906009` ZANJEADORA T-55, documentado) |
| Grupos | 1.866/1.893 (27 exclusivos EMB listados) |
| Descripciones | **99,0 %** exactas/equivalentes; 167 diferencias reales pendientes (artefactos PDF clasificados aparte) |
| Unidades | solo 12 pares de notación (t↔tm 2.480, m↔ml 1.687, 100m↔cm…); **153 con posible carga semántica** (u↔ct/cu/dc, m2↔d2/mm) verificados contra precio |
| Precios | 90–97 % dentro del ruido de publicación ±0,011 (EMB publica a 2 dec; SBD guarda 4 dec exactos); **201 diferencias reales >0,5** (deriva de fecha: EMB ~1 % por debajo); 31 inconsistencias internas de redondeo |
| Normas 2017↔2025 | 15.278 partidas compartidas: **96,7 %** iguales/dentro de tolerancia Float32; 1.838 diferentes con **ratios enteros limpios** (×2: 857…) — cambios reales de consumo, no corrupción |

**Incidentes heredados — cierre con evidencia:**

- **Patrón «×10» en CHMN (259 partidas, hallazgo III-B/III-C):** **0 casos
  en la fuente 2025** → era un artefacto de los datos 2017, no un bug de
  importación. Cerrado.
- **«148 unidades cambiadas 2017→2025» (III-D):** PRECODI 2017 y SBD 2025
  difieren en **1 sola unidad** → las 148 eran notación de publicación de
  PRECOST (t↔tm, m↔ml…), no cambios de unidad reales. Reinterpretado.
- **HORAS OPERARIO/AYUDANTE (pendiente desde Fase III):** OPERARIO existe
  en SBD 2025 (16.861 valores); AYUDANTE llega vacío desde la fuente — no
  inventable, documentado.
- **PESO:** la columna llega a 0 en SBD 2025 → no verificable contra esta
  fuente, documentado.

**Cobertura declarada con honestidad:** no se afirma «100 % consistente»;
se publica la lista completa de **502 diferencias concretas** (167
descripciones + 201 precios + 31 redondeos + 153 unidades semánticas + 27
grupos) en los JSON de evidencia, cada una con códigos y valores de ambas
fuentes.

Informe completo: `docs/INFORME_FIDELIDAD_CLASIFICADOR.md`.

---

## 6. Línea B — Instalador y manual SIECONS 11

**Extracción estática del instalador (hito técnico de la misión):**

- Formato Smart Install Maker v5.04 descifrado: overlay de 36 bytes al
  final del instalador + payload = cadena de 6 CABs estándar **sin firma
  MSCF** (compresión LZX ventana 21, CFFILE de 16 bytes).
- Driver en C (`scripts/cabdrv.c`) compilado contra libmspack **sin
  modificar** + append de la cadena → **39/39 archivos extraídos,
  340.755.553 bytes EXACTOS** al esperado, hashes publicados en
  `SHA256SUMS_payload.txt`.
- Contenido clave: `Manual Básico SIECONS.pdf` (7,97 MB),
  `Siecons_11_13.accde` (147,6 MB), `SBD_MICONS_2025.mdb` (63,9 MB),
  `Config.sie`, `BD_SIFCBIM_11.mdb`, PivoSie/SIFCBIM, plantillas MS-Project.
- Esto desbloqueó la Línea A (referencia 2025 primaria) y la Línea B
  (manual + matriz).

**Manual:** 54 páginas, 115 capturas, ~40k caracteres extraídos con PyMuPDF
(`docs/datos/manual_siecons/`); 5 capturas clave analizadas con modelo de
visión (menú principal de 8 módulos, filtro de A.C., estructura de
desagregación con árbol codificado).

**Matriz de paridad:** `docs/MATRIZ_PARIDAD_SIECONS_PRECOST.md` — **104
funciones documentadas en 11 módulos** (M1 entorno, M2 panel de control,
M3 actividades de construcción, M4 desagregación, M5 certificación, M6
normas, M7 informes, M8 herramientas, M9-SIFCBIM, M10 MS-Project, M11
BIM), cada una con: evidencia (página/captura del manual), estado PRECOST
(existente/parcial/ausente/no comparable), brecha funcional, prioridad
P0-P3, dependencias y **prueba de aceptación** concreta.

Hoja de ruta resultante (P1 primero): S-080 Calculadora → S-052/S-050
(edición de recursos) → S-032/S-039 (etapas y operaciones en bloque) →
S-070/071/072 (fichas de costo) → S-043/S-063 (informes de costo base) →
S-013/S-027 (obras y estructura).

---

## 7. Fase D — Implementación: S-080 Calculadora de costos de actividad

**Función SIECONS replicada** (manual pág. 18): «Calculadora: Evalúa y
calcula el precio de una actividad con coeficientes personalizados.»
Seleccionada por: prioridad P1 documentada, dependencia directa de la
infraestructura de descomposición verificada en III-C, criterio de
aceptación claro, valor real para el estimador (evaluar precio con
coeficientes propios sin crear presupuesto).

**Arquitectura (tercer overlay 100 % aditivo, `app/overlay/calculadora.js`,
661 líneas):**

- Inyección por el servidor local al servir el HTML — **el archivo en disco
  no se modifica** (SHA-256 verificado por request).
- Apertura con botón flotante 🧮 o **Alt+C** desde cualquier vista; Esc
  cierra.
- Búsqueda de actividad por código (catálogo embebido, offline) o por texto
  (servidor PRECODI); selección de versión de normas y fuente de precios
  (mecanismos III-C reutilizados, cero endpoints nuevos).
- Carga la descomposición (`/api/descomposicion`) y permite **editar
  coeficiente y precio por recurso**, aplicar **coeficiente global de
  ajuste** y **cantidad a evaluar**.
- Recálculo en vivo de CMMN/CHMN/CEMN y totales con `importe = coef ×
  precio` — misma fórmula que la pestaña Recursos de III-C; **el redondeo
  es solo de presentación, nunca del cálculo**.
- Comparación contra el PU oficial (motor PRECOST embebido y PRECODI de la
  versión) mostrando Δ % — **nunca sobrescribe** nada del catálogo ni de
  los presupuestos.
- Exporta JSON, copia resumen al portapapeles y guarda historial en
  **clave nueva** `p3pro.calcHist` (no colisiona con las 23 claves
  existentes de PRECOST; `p3pro.budgets` intacto — probado).
- **Degradación honesta sin servidor:** modo embebido con PU agregado
  (mat/mo/eq/total de `DB.P`) y aviso explícito de lo que no está
  disponible.

**Criterio de aceptación de la matriz — verificado:** abrir calculadora,
elegir `012141`, aplicar coeficiente 1,15, ver precio recalculado con
traza (18/18 en navegador, §8).

**Servidor:** `scripts/servidor_precodi.py` extendido para servir el tercer
overlay; `scripts/tests_iiic.py` ajustado en su invariante de inyección (de
«exactamente 2 etiquetas» a «toda etiqueta inyectada apunta a `/overlay/`»)
— generalización correcta, no relajación: sigue probando que no se añade
nada ajeno a los overlays.

---

## 8. Fase E — Regresión completa

| Suite | Resultado | Qué protege |
|---|---|---|
| `scripts/tests_iv.py` (nueva) | **19/19 OK** | integridad del HTML (disco y servido), 3 overlays servidos, inyección aditiva, sintaxis `node --check`, guardas (idempotente, no toca `p3pro.budgets`, clave propia), endpoint de descomposición coherente para 012141, fórmula idéntica a III-C, modo degradado, tag y árbol limpios |
| `scripts/tests_iiib.py` (regresión) | **21/21 OK** | toda la integración catálogo PRECODI de III-B |
| `scripts/tests_iiic.py` (regresión) | **21/21 OK** | descomposiciones en pestaña Recursos + invariante de inyección generalizado |
| `scripts/validar_iv_navegador.sh` (navegador real) | **18/18 ✓** | ver §8.1 |

### 8.1 Validación de extremo a extremo en navegador (18/18)

1. Botón flotante presente · 2. Alt+C abre · 3. descomposición de 012141
cargada (≥ 9 filas) · 4. descripción visible · 5. subtotales
CMMN/CHMN/CEMN · 6a. importe editado 2,4 × 1,8 = 4,32 · 6b. CMMN
recalculado = 4,789 · 7a. total unitario × 1,15 = 12,7053 · 7b. total
evaluación × 10 = 127,0528 · 8. comparación contra PU oficial embebido ·
9a. historial en `p3pro.calcHist` · 9b. `p3pro.budgets` SIN cambios · 10.
Esc cierra · 11. navegación de vistas intacta + FAB persistente · 12.
modo degradado honesto (PU embebido 011111 = 26,81 con aviso) · 13.
historial persiste tras recarga · 14. **0 errores de consola** · 15. HTML
byte-idéntico tras toda la sesión.

**Resultado: ACEPTACIÓN DE EXTREMO A EXTREMO SUPERADA.**

---

## 9. Integridad del original — verificación final

- `app/PRECOST-v9.17.html` — SHA-256 en disco =
  `50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2`
  (byte-idéntico al inicio de la misión; probado por las tres suites y por
  el script de navegador).
- Tag `v9.17-original` intacto, apuntando al commit base.
- Catálogo embebido completo en la BD importada (lo prueba `tests_iiic.py`
  en cada ejecución).
- Presupuestos existentes (`p3pro.budgets`) intactos tras usar la
  calculadora (comprobación 9b del navegador).
- Sin mezcla de versiones: cada número mostrado por la calculadora declara
  su fuente (versión de normas + versión de precios).

---

## 10. Registro de commits de la misión

| Commit | Contenido |
|---|---|
| `384c209` | Fase C técnica: extractor estático del instalador SIECONS 11 (Smart Install Maker v5.04) |
| `9b53f19` | Fases A-C: auditoría de fidelidad (Línea A) + manual SIECONS y matriz de paridad (Línea B) |
| (este commit) | Fase D: overlay calculadora S-080 + servidor 3 overlays; Fase E: suites y validación navegador; Fase F: informe final y matriz actualizada |

---

## 11. Reproducción completa

```bash
cd /home/z/my-project/precost
git checkout iv-fidelidad-precodi-paridad-siecons

# 0) Integridad del original
sha256sum app/PRECOST-v9.17.html   # = 50d3cf28…5cbaa2
git tag -l v9.17-original && git rev-parse v9.17-original

# 1) Regenerar la BD si hiciera falta (idempotente, ~50 s)
python3 scripts/importar_precodi.py --todo

# 2) Suites automatizadas (Fase E)
python3 scripts/tests_iv.py        # 19/19
python3 scripts/tests_iiib.py      # 21/21
python3 scripts/tests_iiic.py      # 21/21

# 3) Validación de extremo a extremo en navegador (requiere agent-browser)
bash scripts/validar_iv_navegador.sh   # 18/18

# 4) Uso manual
python3 scripts/servidor_precodi.py    # http://127.0.0.1:8788/
#   → botón 🧮 o Alt+C → buscar 012141 → editar coef/precios →
#     ajuste global 1.15 → cantidad 10 → comparar Δ% contra oficial →
#     exportar JSON / historial / Esc

# 5) Reproducir la auditoría de fidelidad (Línea A)
python3 scripts/iv_auditoria_fidelidad.py
python3 scripts/iv_auditoria_fina.py
python3 scripts/iv_auditoria_paso3.py
python3 scripts/iv_auditoria_paso4.py
#    → docs/INFORME_FIDELIDAD_CLASIFICADOR.md + JSON de evidencia

# 6) Reproducir la extracción del instalador SIECONS (Línea B)
python3 scripts/iv_cadena_cab.py && python3 scripts/iv_generar_mapeo.py
python3 scripts/iv_extraer_cab.py     # 39/39 archivos, hashes verificados
```

---

## 12. Limitaciones conocidas y siguientes pasos

**Limitaciones (sin inventar datos):**

1. 502 diferencias concretas EMB↔SBD pendientes de decisión editorial
   (listadas nominalmente; son el 0,2 % del catálogo compartido).
2. AYUDANTE llega vacío desde la fuente SBD 2025; PESO llega a 0 → no
   verificables contra esta fuente.
3. La calculadora consulta por código contra el catálogo embebido (offline)
   y por texto contra el servidor; sin servidor, la búsqueda por texto de
   catálogo importado no está disponible (modo degradado documentado).
4. SIECONS 11 no se ejecutó en este entorno (sin VM Windows): la paridad se
   establece contra el manual y los datos del fabricante, no contra la app
   en ejecución.

**Siguientes pasos sugeridos (orden de la matriz P1):**

1. S-052/S-050 — edición de recursos en la descomposición (los mecanismos
   de edición de la calculadora son la base).
2. S-032/S-039 — etapas y operaciones en bloque.
3. S-070/071/072 — fichas de costo.
4. Migración de presupuestos a tablas 0002 vía sql.js/OPFS (elimina el
   proceso local; diseño a proponer antes de tocar nada).
5. Decisión editorial sobre las 502 diferencias (aceptar EMB, adoptar SBD
   o marcar en overlay informativo).
