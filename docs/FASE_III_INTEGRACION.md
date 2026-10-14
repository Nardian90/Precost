# FASE III-B — INTEGRACIÓN REAL DE PRECODI CON PRECOST 9.17

Fecha: 2026-10-14 · Rama: `evolucion` · Base importada: `bd/precodi.db` (regenerable, fuera de git)
Precedentes: `docs/AUDITORIA_PREVIA_IIIB.md` (Fase 1 de esta misión), `docs/INFORME_FASE_III.md` (fase III-A…F)

**Cumplimiento de los criterios de aceptación**: el importador funciona con datos reales
(6 versiones, ~717 000 filas), las relaciones están validadas con datos (presupuestos SBD
16 816/16 816 en sus tres FK), las importaciones repetidas no generan duplicados (probado),
la precisión numérica está probada (Money 4 decimales exactos, Float32 bit a bit, 21/21
pruebas) y PRECOST consulta el catálogo importado sin perder funcionalidades existentes
(verificado en navegador real con el HTML original byte-idéntico).

---

## 1. Resumen ejecutivo

| Concepto | Resultado |
|---|---|
| Bases importadas | 4 variantes de `codigo.mdb` (7.21, 7.22, raíz 2017, Preambulos≡7.21) + catálogo embebido PRECOST 2025 + SBD2008_815 (núcleo + 24 tablas priorizadas) |
| Filas totales importadas | 99 196 + 102 327 + 102 327 + 0 (duplicado) + 22 187 + 389 871 = **715 908** |
| Tiempo total de importación | ≈ 50 s (regenerable con los comandos del §8) |
| Recuentos origen↔destino sin explicar | **0** (`docs/datos/iiib_conciliacion.json`) |
| Pruebas automatizadas | **21/21 OK** (`scripts/tests_iiib.py`) |
| Modificaciones al HTML original | **0** (SHA-256 constante; el overlay se inyecta solo al servir) |
| Hallazgos técnicos mayores | 2 bugs del parser `access_parser` 0.0.6 corregidos con evidencia: Money truncado a 2 decimales y textos Jet 3 vacíos tras el primer salto de 256 bytes |

## 2. Fase 1 — Auditoría previa (resumen)

Ejecutada y evidenciada en `docs/AUDITORIA_PREVIA_IIIB.md` + `docs/datos/auditoria_iiib.json`.
Hallazgos que condicionaron el diseño:

1. **El importador PoC anterior no dividía el Money escalado ×10 000**: solo funcionó con
   la raíz 2017 porque `access_parser` devuelve strings formateadas para columnas con
   propiedad `Format` (con pérdida a 2 decimales y coma de miles ≥1000 → `float()` fallaba
   → valores perdidos en silencio).
2. **`Preambulos/codigo.mdb` es byte-idéntico a `7.21/`** (mismo SHA-256): importarlo de
   nuevo duplicaría registros; se registra como referencia retirada con 0 filas propias.
3. **`Norma Juego Material1`** (solo raíz) es copia exacta de `Norma Juego Material`
   (2936/2936 filas idénticas, verificado con datos): se importa una y se documenta la otra.
4. La migración `0002` ya modela proyectos/presupuestos: se reutiliza; no se duplican
   entidades (la `0003` solo AMPLÍA `partidas` y añade las tablas `sbd_*` justificadas).

## 3. Fases 2-3 — Importador común y precisión numérica

**Scripts**: `scripts/importar_precodi.py` (núcleo común), `scripts/importar_sbd.py`
(priorizadas), `scripts/precision_precodi.py` (reglas de precisión).

**Garantías implementadas y probadas**:
- Inspección de esquema antes de importar; mapa explícito tablas→entidades; orden
  grupos → nomencladores → partidas → normas → componentes (nomencladores ANTES que las
  normas que los referencian).
- Adaptación a diferencias de versión: 7.21 (Jet 3, 22 tablas) → 7.22 (23) → raíz (24) →
  SBD (núcleo superconjunto: RV sin `CodSobreG`/`CodG` → capítulo derivado del prefijo
  del código, verificado contra grupos nivel 1).
- Idempotencia por (catálogo, versión, hash): reimportar no duplica; un intento previo
  fallido se purga y reintenta limpio; un contenido idéntico bajo otra etiqueta se aborta
  (bases primarias) o se registra como referencia (Preambulos).
- Transacción única por versión: cualquier fallo → ROLLBACK completo + registro
  `importaciones.resultado='error'` (probado con fallo inyectado).
- Detección registrada: códigos duplicados (SBD: 13+23 normas), claves huérfanas
  (presupuesto Mat: 7 recursos), código nulo (Equipos raíz: 1 fila omitida, 414+1=415),
  conflictos de descripción de grupos entre versiones (contados, no sobrescritos).

**Reglas de precisión (Fase 3)** — nada de tolerancia universal 0,01:

| Tipo | Regla | Prueba |
|---|---|---|
| Money Jet (Currency) | Decimal exacto `entero/10 000` desde el dato binario (parche de `parse_money_type`); round-trip REAL con tol `max(1e-9, |v|·1e-13)` | `test_precio_4_decimales_roundtrip`, `test_precio_mayor_1000_no_se_pierde` |
| Float32 (coeficientes) | valor recuperado preservado bit a bit (1.2000000476837158), precisión original documentada (~7 dígitos) | `test_coeficiente_float32_bit_a_bit` |
| Float64 | preservado tal cual | — |
| Sumas (Σ coef×precio vs almacenado) | tol `max(0.0001·N, Σ|términos|·6e-8)`; excedentes clasificados como deriva de precios (documentado en fase III-C) | `test_caso_012141_completo` |
| Presentación | redondeo a 2 decimales SOLO en la capa visual | overlay |

**Corrección del bug Jet 3 de `access_parser`** (evidencia completa en el docstring de
`parchear_jet3_textos`): en registros Jet 3 los offsets de columnas variables se almacenan
módulo 256 con una tabla de saltos; la librería aplicaba el salto según la columna leída y
calculaba el FIN del dato con el offset siguiente sin su salto → todos los textos posteriores
al primer salto decodificaban como `''`. Corregido por-offset: **7.21 pasa de 226 a
15 347/15 347 descripciones** (cotejo contra 7.22: 15 346 idénticas, 1 diferencia real de
datos entre versiones, reportada). Este bug nunca se había detectado porque todos los
análisis de valores previos usaban la raíz 2017 (Jet 4).

## 4. Fase 4 — SBD2008_815 sin perder semántica

**Clasificación** (`scripts/clasificar_sbd.py` → `docs/datos/sbd_clasificacion.json`):
284 tablas → **4 integrables directamente** (esquema igual al núcleo), **38 mediante
transformación** (las 24 priorizadas por la misión + núcleo con adaptación + padres),
**19 documentales** (AGIT, contratos, certificaciones…) y **223 pendientes** (112 vacías
sin semántica verificable + sin patrón reconocido). Nada se importa sin clasificar.

**Tablas priorizadas importadas** (con verificación de relaciones con datos):
colecciones y composiciones (27 + 1 570 + 92 054), normas RH/EQ y RH Extendida
(9 699 + 194 + 57 838), normas descriptivas (2 361 con cuadrillas JSON y variantes
reales conservadas), tarifas (22 510 + 43), duración y costo (15 236; códigos verificados
contra partidas 15 232/15 236), actividades de estimación (671, PK compuesta respetada),
macros (27), composiciones presupuestarias existentes (16 816 partidas presupuestadas +
18 816 recursos) y padres mínimos (obras 28, objetos 844, etapas 63).

**Relaciones verificadas con datos reales**: `Presupuesto RV.IdObjObra → Objetos de Obra.IdObjObra`
**16 816/16 816** (la PK declarada compuesta `(IdObra, CodObj)` NO es la clave de join real;
se descubrió con datos: primero 276/16 816, corregido a la columna autonumérica correcta),
`IdEtapa → Etapas` 16 816/16 816, `CODIGO RV → partidas` 16 816/16 816,
`IdPRV → presupuesto_rv` 18 816/18 816. Reclasificación dirigida por datos disponible
(códigos de recurso encontrados en otro nomenclador).

## 5. Fase 5 — Conexión del catálogo importado con PRECOST

**Arquitectura** (decisión justificada): PRECOST es un HTML autónomo; un navegador no
puede abrir SQLite directamente. Se implementó una **capa de acceso local**
(`scripts/servidor_precodi.py`, solo librería estándar, sin dependencias, 100 % offline):

- Sirve el HTML **original desde disco sin modificarlo**, inyectando al vuelo una única
  etiqueta `<script src="/overlay/precodi.js" defer>` antes del `</body>` real (el archivo
  en disco permanece byte-idéntico, verificado en cada request por SHA-256).
- Expone `/api/versiones`, `/api/partidas` (búsqueda por código/descripción),
  `/api/partida/<código>` (descomposición completa con coeficientes, precios, subtotales,
  verificación contra la fuente y comparación entre versiones) y `/api/stats`.
- Conexión SQLite **solo lectura** (`mode=ro`, `query_only`); escucha **únicamente en
  127.0.0.1** — no es un servicio público y no expone bases de datos a Internet.
- Alternativa considerada y descartada por ahora: sql.js (WASM) — requiere dependencia
  externa y seguiría necesitando un servidor para el fetch inicial; queda como evolución
  (OPFS) si se quiere eliminar el proceso local.

**Overlay** (`app/overlay/precodi.js`): 100 % aditivo (botón flotante + panel con estilos
prefijados `.pcod-`), no toca el catálogo embebido, las vistas existentes ni el contrato
PRECOST-AI-JSON. Permite: consultar partidas importadas, buscar por código o descripción,
ver unidad/fuente/versión (con SHA-256 y fecha de importación), consultar los recursos de
cada norma con coeficientes y precios, ver subtotales reproducibles y su verificación
contra los valores almacenados en la fuente, y comparar la misma partida entre versiones
(PRECODI 2007/2011/2017 y PRECOST 2025).

**Caso de prueba documentado** (`datos_prueba/casos_iiib.json`, extraído de la fuente):
partida **012141** «EN ROCA CUALQUIER SECCION EN PLANTA, HASTA 1.80 M…» — 9 componentes;
CMMN almacenado 2.6290 vs recalculado 2.629000 (Δ 0.000000 ≤ tol 0.0009) ✓, CHMN
4.6074 vs 4.607424 (Δ 0.000024) ✓, CEMN 1.6517 vs 1.651643 (Δ −0.000057) ✓.

**Verificación en navegador real** (agent-browser headless, `docs/datos/iiib_overlay_navegador.png`):
PRECOST carga con título correcto, overlay presente, catálogo embebido `DB` intacto,
vistas propias renderizando, caso 012141 con 3/3 verificaciones ✓, búsqueda por texto
«roca» → 60 resultados, 0 errores de consola.

## 6. Fase 6 — Conciliación y validación

- **Suite**: `scripts/tests_iiib.py` — **21/21 OK** en 15 s, cubriendo los 10 escenarios
  exigidos (4 variantes, esquemas opcionales, idempotencia, duplicados/huérfanos,
  nulos/desconocidos, Float32, 4 decimales + caso ≥1000, multicomponente, interrupción con
  rollback y reintento, conservación del original).
- **Conciliación de recuentos** (`scripts/conciliar_iiib.py` → `docs/datos/iiib_conciliacion.json`):
  por base y tabla, `insertadas + explicadas_por_reglas == filas_fuente` con **0 casos sin
  explicar**; cada regla (duplicadas, omitidas, huérfanas, ya existentes, duplicado exacto
  NJM1/Preambulos) está nombrada en el propio JSON.
- **Cruce PRECODI 2017 ↔ PRECOST 2025** (ahora con precios exactos de 4 decimales):
  14 451 códigos compartidos, 13 022 descripciones idénticas, ratio de precio total
  2025/2017 mediana ×10.81 (fase III-D estimaba ×11.13 con precios truncados a 2 decimales),
  y **15 350 partidas con descomposición** — de las cuales 14 451 son consultables por
  PRECOST 2025 que no trae normas.
- **No se declara equivalencia funcional con SIECONS**: no hay resultados de referencia
  verificables de SIECONS en este entorno (requeriría Windows/Access); lo que se declara
  y prueba es la consulta del catálogo PRECODI importado desde PRECOST.

## 7. Fase 7 — Entregables

| Entregable | Ubicación |
|---|---|
| Informe maestro de la integración | `docs/FASE_III_INTEGRACION.md` (este documento) |
| Diccionario PRECODI consolidado + clasificación SBD | `docs/DICCIONARIO_PRECODI.md` |
| Modelo relacional (ER + correspondencias) | `docs/MODELO_RELACIONAL.md` |
| Conciliación PRECODI–PRECOST | `docs/CONCILIACION_PRECODI_PRECOST.md` (+ JSON) |
| Scripts reproducibles | `scripts/auditar_iiib.py`, `importar_precodi.py`, `importar_sbd.py`, `precision_precodi.py`, `clasificar_sbd.py`, `extraer_caso_prueba.py`, `servidor_precodi.py`, `conciliar_iiib.py`, `tests_iiib.py` |
| Migraciones | `bd/migraciones/0001_catalogo.sql`, `0002_proyectos.sql`, `0003_precision_sbd.sql` (aplicadas por `scripts/fase3e_migrar.py`, idempotentes) |
| Pruebas automatizadas | `scripts/tests_iiib.py` (21/21) + resultados en este informe |
| Datos de prueba | `datos_prueba/casos_iiib.json` (casos con valores exactos de la fuente) |
| Overlay + servidor | `app/overlay/precodi.js`, `scripts/servidor_precodi.py` |

## 8. Cómo reproducir todo (desde cero)

```bash
cd /home/z/my-project/precost

# 0) auditoría previa (verifica hashes, git, migraciones, tipos Money/Float32)
python3 scripts/auditar_iiib.py

# 1) importación completa (≈50 s; regenera bd/precodi.db desde las .mdb originales)
rm -f bd/precodi.db
python3 scripts/importar_precodi.py --todas            # 7.21, 7.22, raíz, Preambulos, PRECOST 2025
python3 scripts/importar_precodi.py --base sbd --priorizadas

# 2) fixture de casos de prueba (valores exactos desde la fuente)
python3 scripts/extraer_caso_prueba.py

# 3) pruebas automatizadas (21/21)
python3 scripts/tests_iiib.py

# 4) conciliación de recuentos
python3 scripts/conciliar_iiib.py

# 5) consultar desde PRECOST (capa local, solo lectura, 127.0.0.1)
python3 scripts/servidor_precodi.py        # → abrir http://127.0.0.1:8765/
#    botón «▤ Catálogo PRECODI» → buscar 012141 → verificación contra la fuente

# 6) informe de importaciones (versiones, hashes, filas, advertencias)
python3 scripts/importar_precodi.py --informe
```

Los archivos `.mdb` originales y `app/PRECOST-v9.17.html` **nunca se modifican**
(verificado por SHA-256 antes y después de cada importación, y por las pruebas).

## 9. Limitaciones y siguientes pasos

- **No ejecutado en este entorno**: SIECONS 11 (requiere Windows + Access 2013+); no hay
  referencia de cálculo externa contra la que validar equivalencia funcional.
- **Fórmulas PENDIENTES heredadas** de fase III-C (HORAS OPERARIO/AYUDANTE, PESO, patrón
  ×10): los datos están preservados (columnas nuevas de 0003) pero las fórmulas siguen
  sin inventarse.
- 223 tablas SBD quedan clasificadas como pendientes/documentales: no se importan sin
  comprender su finalidad (la clasificación completa está en `sbd_clasificacion.json`).
- Siguientes pasos naturales: (1) usar las descomposiciones PRECODI dentro del editor de
  presupuestos de PRECOST (rellenar la pestaña Recursos al añadir una partida); (2) vía
  sql.js/OPFS para eliminar el proceso local; (3) actualizar precios 2025→PRECODI aplicando
  las normas 2017 a los precios vigentes (la combinación que ninguna de las dos fuentes
  ofrece hoy por separado).
