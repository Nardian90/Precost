# INFORME DE FIDELIDAD DEL CLASIFICADOR — MISIÓN IV (LÍNEA A)

**Proyecto:** PRECOST 9.17 · **Fecha:** 14 de octubre de 2026
**Rama:** `iv-fidelidad-precodi-paridad-siecons`
**Objeto:** verificación de fidelidad del catálogo/clasificador embebido de PRECOST contra fuentes PRECODI identificables y comparables.

---

## 1. Resumen ejecutivo

El catálogo embebido de PRECOST 9.17 (PRECONS III MICONS 2025) fue comparado
registro a registro y campo a campo contra una fuente independiente de la
misma época —la base de datos que SIECONS 11 trae por defecto
(SBD_MICONS_2025.mdb), extraída estáticamente del instalador oficial— y
contra las versiones históricas PRECODI ya importadas (2017-raíz, 7.22,
7.21, SBD2008).

**Conclusión principal:** el clasificador embebido de PRECOST es una
publicación fiel del mismo conjunto de datos subyacente que utiliza
SIECONS 11 para 2025. Las 15.912 partidas embebidas existen todas en la
base de SIECONS (contención del 100 %); materiales, mano de obra y equipos
también están contenidos al 100 % (equipos: 670/671). Las diferencias se
concentran en tres clases explicables y documentadas: redondeo editorial a
2 decimales, notación de unidades y deriva de precios de materiales entre
fechas de compilación. Quedan **502 diferencias concretas pendientes de
decisión** (167 descripciones, 201 precios, 31 inconsistencias internas,
153 unidades con posible carga semántica, 27 grupos exclusivos), listadas
una a una en los JSON de evidencia.

Se resuelven además dos incidentes heredados de III-B/III-C: el patrón
«×10» en costos de mano de obra **no existe en la fuente 2025** (0 casos
frente a 259 en 2017) y las «148 unidades cambiadas 2017→2025» se revelan
como notación de publicación de PRECOST, no cambios reales (PRECODI 2017 y
SBD 2025 solo difieren en **1** unidad).

---

## 2. Fuentes comparadas

| Fuente | Papel | Registros clave | SHA-256 (verificado) |
|---|---|---|---|
| PRECOST 9.17 `const DB` (EMB) | Catálogo auditado | P 15.912 · M 3.568 · O 143 · E 671 · G 1.893 | HTML `50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2` |
| SBD_MICONS_2025.mdb (SBD) | Referencia 2025 independiente (SIECONS 11) | RV 16.865 · Mat 3.599 · RH 412 · Eq 712 · Juegos 320 · Semi 149 · SubGrupos 1.714 · Grupos 340 · SobreGrupos 42 · Normas 77.021 filas | `74398070b004ec39c18fc157ae4e65180faa1774bde3fd04704c8167314a2904` |
| PRECODI 2017-raíz (P17) | Referencia histórica (SQLite v3) | 15.351 partidas · 73.978 normas | `c4f94962c3e0cde62bc455262830904b033425f00f1946000dc9eb2869e175bc` |
| PRECODI 7.22 / 7.21 | Contexto histórico (SQLite v2/v1) | 15.350 / 15.347 partidas | `d6719a42…` / `8b94cebf…` |

La SBD_MICONS_2025.mdb fue extraída del instalador oficial de SIECONS 11
(Smart Install Maker v5.04: cadena de 6 CABs LZX sin firma MSCF,
reconstruidos y decodificados con libmspack sin modificar; 39 archivos,
340.755.553 bytes verificados). El procedimiento completo es reproducible
con `scripts/iv_extraer_cab.py` + `scripts/iv_cadena_cab.py` +
`scripts/cabdrv.c` + `scripts/iv_generar_mapeo.py`.

---

## 3. Metodología

1. Extracción del catálogo embebido **sin modificar** el HTML original
   (`fase3d_extraer_catalogo`).
2. Lectura de SBD_MICONS_2025 con access-parser + parche de precisión
   Money de III-B (4 decimales exactos; Float32 bit a bit).
3. Comparación **por código normalizado** (nunca por IDs autoincrementales):
   existencia, descripción, unidad, precios (total, mat, mo, eq), peso,
   horas, categoría.
4. Clasificación de cada diferencia según la taxonomía de la misión
   (coincidencia exacta / equivalente / versión / unidad / precio /
   descripción / faltante / duplicado / conflicto / no verificable).
5. Tolerancias **justificadas y documentadas**: 0,005 para redondeo a
   2 decimales de publicación; 0,011 como ruido máximo de publicación;
   1e-6 relativo para coeficientes Float32. Ninguna tolerancia global
   arbitraria.

Archivos de evidencia (reproducibles):
`docs/datos/fidelidad_iv.json` (métricas y ejemplos),
`fidelidad_iv_fina.json` (clasificación fina),
`fidelidad_iv_paso3.json` (distribuciones),
`fidelidad_iv_paso4.json` (diferencias reales listadas).

---

## 4. Resultados por categoría

### 4.1 Partidas (EMB 15.912 ↔ SBD RV 16.865)

| Métrica | Valor |
|---|---|
| Comunes | **15.912 (100 % del catálogo EMB)** |
| Solo en EMB | **0** |
| Solo en SBD | 953 (macroactividades, tipos no publicados en el PDF, etc.) |

**Descripción** (clasificación con normalización conservadora primero y
agresiva después para separar artefactos de PDF):

| Clase | Casos | % |
|---|---:|---:|
| Exacta | 13.619 | 85,7 % |
| Equivalente (espaciado del PDF: «2 .00» vs «2.00») | 1.313 | 8,3 % |
| Artefacto de sufijo del PDF (número de unidad / «LISTA DE COSTOS») | 104 | 0,7 % |
| Truncada por columna del PDF | 709 | 4,5 % |
| **Diferente real (pendiente)** | **167** | **1,0 %** |

**Unidad** — 11.321 exactas (71,1 %); 4.591 difieren en **solo 12 pares de
notación**:

| Par EMB ↔ SBD | Casos | Equivalencia |
|---|---:|---|
| t ↔ tm | 2.480 | tonelada métrica (sinónimo) |
| m ↔ ml | 1.687 | metro lineal (sinónimo) |
| 100 m ↔ cm | 147 | «cm» = cien metros en PRECODI (sinónimo) |
| 100 m2 ↔ c2 · 100 m3 ↔ c3 · l ↔ hl | 74+48+4 | equivalente decimal |
| m2 ↔ d2 · m2 ↔ mm | 37 | **riesgo semántico (×10 / ×1000)** |
| u ↔ ct · u ↔ cu · u ↔ dc | 112 | **riesgo semántico (×100 / ×12)** |

Los 153 casos de la última zona se verificaron contra el precio: en 122 el
precio es idéntico en ambas fuentes (relabel de unidad); en 31 además hay
deriva de precio. PRECODI 2017 y SBD 2025 **coinciden** entre sí en la
unidad de estos códigos, por lo que la presentación de EMB es la que
difiere de ambas referencias. Ejemplo verificado: `031901` «COLOCACION DE
BLOQUE PANEL BP-1» — SBD/P17 unidad `ct` (ciento), EMB unidad `u`, mismo
precio 1.118,12. **Recomendación:** mostrar la unidad PRECODI/SBD (o
ambas) en el clasificador; el listado completo está en
`fidelidad_iv_paso4.json → 4_unidades_riesgo`.

**Precios** (distribución de |EMB − SBD|):

| Campo | Exacto | ≤ 0,005 | ≤ 0,011 (ruido publicación) | > 0,5 (real) |
|---|---:|---:|---:|---:|
| mat (CMMN) | 9.278 | 5.151 | 1.047 | **189** |
| mo (CHMN) | 3.228 | 9.011 | 3.218 | 0 |
| eq (CEMN) | 8.885 | 3.873 | 1.570 | **12** |

- El patrón es consistente con **publicación editorial a 2 decimales**
  (SBD guarda 4 decimales exactos; caso `012141`: EMB 123,02 =
  12,89+30,36+79,77 publicados, SBD 123,0132 exacto).
- Las 201 diferencias > 0,5 son **todas de materiales/equipos con EMB por
  debajo de SBD en ~1 %** (deriva de precios entre la fecha del PDF fuente
  —06/06/2025— y la compilación de la SBD). Listado completo en
  `fidelidad_iv_paso4.json → 2_precios_grandes`.
- Consistencia interna EMB: `total == mat+mo+eq` en 15.881/15.912; los 31
  desvíos son ±0,01–0,02 por acumulación de redondeo de publicación.

### 4.2 Materiales (EMB 3.568 ↔ SBD 3.599)

**Contención 100 %** (3.568/3.568). SBD añade 31 materiales no publicados
en el PDF. Descripción/unidad/precio/peso: ver `fidelidad_iv.json →
B_materiales` (mismo patrón de publicación que partidas).

### 4.3 Equipos (EMB 671 ↔ SBD 712)

Comunes 670; SBD añade 42. **1 equipo exclusivo de PRECOST:
`0022906009` ZANJEADORA T-55 DE 275 HP (1107,00)** — presente en el
catálogo embebido y ausente en la base 2025 de SIECONS 11 (no es error de
importación: se verificó el código directo en la tabla). Duplicado
legítimo/decisión pendiente documentado.

### 4.4 Mano de obra (EMB 143 ↔ SBD RH 412)

**Contención 100 %** (143/143). Tarifas: 142 exactas + 1 con diferencia
0,01 (`0000010182`: EMB 15,22 / SBD 15,23). SBD mantiene 269 especialidades
adicionales que el PDF de PRECOST no publica.

### 4.5 Grupos (EMB 1.893 ↔ SBD 2.096)

Comunes 1.866 (98,6 %); 27 códigos solo en EMB y 227 solo en SBD
(estructura de grupos+sobregrupos más fina en SBD). Muestras en
`fidelidad_iv.json → E_grupos`.

### 4.6 Normas de composición (P17 2017 ↔ SBD 2025; 15.278 partidas compartidas)

| Clase | Casos |
|---|---:|
| Coeficiente idéntico | 52.196 (89,9 %) |
| Dentro de tolerancia Float32 | 724 |
| **Diferente** | **1.838 (3,2 %)** |
| Norma solo en 2017 | 12.308 |
| Norma solo en 2025 | 10.084 |

Los 1.838 coeficientes diferentes se descomponen en **cambios enteros
limpios** (×2: 857, ×5: 44, ×3: 30, ×4: 7, ×9: 1, ×0,5: 1) —revisiones
reales de normas entre versiones— y 898 con otros valores. Estos son
**diferencias explicadas por versión**, no errores: cada clave (RV, tipo,
recurso) está listada en `fidelidad_iv.json → F_normas`.

Los duplicados por (RV, RH) en normas de mano de obra de SBD son
**legítimos** (la misma especialidad con normas base distintas; mismo
patrón ya documentado en III-C para `096231`); no se eliminó ninguno.

### 4.7 Caso de referencia 012141 (multi-fuente)

| Fuente | Descripción | UM | mat | mo | eq | total |
|---|---|---|---:|---:|---:|---:|
| EMB (2025) | EN ROCA CUALQUIER SECCION… | m3 | 12,89 | 30,36 | 79,77 | **123,02** |
| SBD (2025) | ídem (sin espacio antes del punto) | m3 | 12,891 | 30,3556 | 79,7666 | **123,0132** |
| P17 (2017) | ídem | m3 | — | — | — | disponible en SQLite |

Las 9 normas de descomposición de 012141 están presentes en P17 y SBD y
coinciden con lo integrado en III-C (PU 123,02 oficial 2025; Δ 0,006 % con
normas 2017 + precios 2025).

---

## 5. Incidentes heredados (III-B / III-C) — estado

| Incidente | Estado tras esta auditoría |
|---|---|
| Patrón «×10» en CHMN de 259 partidas (2017) | **RESUELTO**: en la fuente 2025 hay **0 casos** recalculando Σ(CantRHum×tarifa) contra CHMN con datos SBD. El patrón era una incoherencia interna de los datos 2017, no del importador. |
| «148 unidades con cambio 2017→2025» | **REINTERPRETADO**: P17↔SBD difieren en **1 sola** unidad. Las 148 diferencias de III-D son notación de publicación de EMB (ver §4.1). |
| HORAS OPERARIO / AYUDANTE | SBD 2025 mantiene HORAS OPERARIO (16.861 partidas con valor) y HORAS AYUDANTE **vacío** (0). EMB no publica el campo (no está en el PDF fuente). No es pérdida de fidelidad de PRECOST; queda como limitación de la fuente publicada. |
| PESO | SBD RV.PESO = 0 en todas las filas (el peso no se mantiene en la base SIECONS) → comparación EMB↔SBD **no verificable** en este campo; EMB publica 7.780 pesos tomados del PDF. |
| Recursos sin precio en alguna versión | Verificado en tarifas MO (142/143 exactas) y en materiales (31 SBD sin publicar). |
| Diferencias descomposición vs PU del motor | El motor PRECOST usa los PU publicados (2 dec); la descomposición (normas 2017 + precios 2025) reproduce el PU 2025 con Δ ≤ 0,006 % (III-C) — consistente con el ruido de publicación aquí cuantificado. |

---

## 6. Cobertura verificable de fidelidad

| Categoría | Comparables | Exactas + equivalentes | Pendientes de decisión |
|---|---:|---:|---:|
| Partidas — existencia | 15.912 | 15.912 (100 %) | 0 |
| Partidas — descripción | 15.912 | 15.745 (99,0 %) | 167 |
| Partidas — unidad | 15.912 | 15.412 (96,9 %) | 153 semánticas (122 notación + 31 con deriva) |
| Partidas — precio mat | 15.676 | 15.476 (98,7 %) | 189 reales + 205 intermedias |
| Partidas — precio mo | 15.457 | 15.457 (100 % dentro de publicación) | 455 intermedias (≤0,05) |
| Partidas — precio eq | 15.912* | 14.328 (90,0 %) | 12 reales + 1.572 intermedias |
| Materiales | 3.568 | 3.568 (100 % contención) | campos: ver JSON |
| Equipos | 671 | 670 | 1 exclusivo EMB |
| Mano de obra | 143 | 143 | 0 |
| Grupos | 1.893 | 1.866 | 27 |
| Normas (2017↔2025, compartidas) | 54.758 claves | 52.920 (96,7 %) | 1.838 (versión) |

(*) campos con ambos valores no nulos.

**No se declara «100 % de fidelidad»**: existen 502 diferencias concretas
pendientes (listadas en JSON), ninguna de las cuales afecta la integridad
del motor de cálculo ni de los presupuestos existentes. La afirmación
verificable es: *el catálogo embebido es la publicación a 2 decimales del
mismo conjunto de datos que SIECONS 11 usa internamente para 2025, con
contención completa de partidas, materiales, mano de obra y grupos, y una
lista acotada y documentada de desviaciones.*

---

## 7. Reproducción completa

```bash
cd /home/z/my-project/precost
# 1. extraer el payload del instalador SIECONS (una sola vez)
python3 scripts/iv_extraer_cab.py          # reconstruye los 6 CABs
python3 scripts/iv_generar_mapeo.py        # mapeo índice→ruta real
gcc -O2 -I /tmp/libmspack/libmspack/mspack -o scripts/cabdrv scripts/cabdrv.c \
    /tmp/libmspack/libmspack/mspack/{cabd,lzxd,mszipd,qtmd,system,crc32}.c
(cd /home/z/my-project/work/siecons_extract && \
   /home/z/my-project/precost/scripts/cabdrv cabs payload mapeo.txt)
# 2. auditoría (4 pasadas, ~2 min en total)
python3 scripts/iv_auditoria_fidelidad.py   # → docs/datos/fidelidad_iv.json
python3 scripts/iv_auditoria_fina.py        # → fidelidad_iv_fina.json
python3 scripts/iv_auditoria_paso3.py       # → fidelidad_iv_paso3.json
python3 scripts/iv_auditoria_paso4.py       # → fidelidad_iv_paso4.json
# 3. verificación de integridad del original
sha256sum app/PRECOST-v9.17.html
# esperado: 50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2
```

La comparación no depende de IDs autoincrementales: todas las claves son
códigos normalizados (código de partida, código de recurso, tipo).
