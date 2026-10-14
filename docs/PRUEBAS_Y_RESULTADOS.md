# FASE III — PRUEBAS AUTOMATIZADAS Y RESULTADOS

Fecha: 2026-10-14 · Suite: `scripts/fase3f_tests.py` · Resultados: `docs/datos/fase3f_resultados_tests.json`

## 1. Qué se probó (24 pruebas, todas REALES — recalculan desde las fuentes)

| Grupo | Pruebas | Método |
|---|---|---|
| Estructura | T1 (migraciones y 16 tablas) | consulta a `schema_migrations`/`sqlite_master` |
| Conteos | T2 (partidas PRECODI 510 == muestra recalculada del .mdb · partidas PRECONS 615 == fuente · normas 2.239 == .mdb) | recarga de las tablas .mdb con access-parser y comparación |
| Formatos | T3 (códigos 6/10 dígitos, GLOB) | SQL |
| Integridad | T4 (`PRAGMA foreign_key_check` vacío · 0 normas con recurso huérfano) | SQL |
| Semántica de fuente | T5 (discrepancias total≠mat+mo+eq == las que trae la propia fuente por redondeo del PDF) | comparación con `fase3d_precost_db.json` |
| Fórmulas III-C | T6 (F1 materiales 85,7% · F2 mano de obra 82,7%+17,3% patrón ×10 documentado, 0 sin explicar · F3 equipos 92,7%) | recálculo SQL solo con datos de la base |
| Procedencia | T7 (toda partida/recurso con fuente y SHA-256 · 2 importaciones registradas) | SQL |
| Inmutabilidad | T8 (**HTML original sin cambios** (SHA-256 `50d3cf28…`) · **codigo.mdb sin cambios** desde la importación) | SHA-256 |
| Dominios | T9 (unidades no vacías · sin costos negativos · factor de unidad > 0) | SQL |
| Funcional | T10 (partida 012141 con 9 recursos · búsqueda por texto · descomposición con precios y procedencia) | SQL JOIN |

## 2. Resultado

```
RESULTADO: 24/24 pruebas superadas · 0 fallidas
```

Detalle de las pruebas semánticas (T6), que validan la transferencia del conocimiento de la Fase III-C a la base de datos:

- **F2** (mano de obra): 422/510 exactos (±0,01) + **88 con el patrón ×10 documentado** (CHMN = 10×Σ en la fuente PRECODI, concentrado en excavaciones — hallazgo de la Fase III-C) + **0 sin explicar**.
- **F3** (equipos): 473/510 exactos (92,7%) — las diferencias son deriva de precios/float32 documentadas.
- **F1** (materiales, sin expandir juegos/semis): 437/510 (85,7%) — las partidas con juegos/semis requieren expansión de `componentes_recurso` (no implementada en el recálculo de la prueba por diseño: valida la tabla de normas pura).

## 3. Verificación funcional en navegador (PoC)

La página `prueba/poc_catalogo_externo.html` se probó con navegador headless real (agente de automatización) servida por HTTP local:

| Paso verificado | Resultado |
|---|---|
| Carga del catálogo externo (`fetch db/catalogo_export.json`) | ✓ «1.125 partidas · 525 recursos · 2.239 normas · 2 catálogos» |
| Búsqueda por código exacto `012141` | ✓ 2 resultados (2017+2025) |
| Detalle 2017: descomposición completa | ✓ 9 recursos con tipo, código, coeficiente, precio e importe |
| Detalle 2025: costos agregados + nota honesta de ausencia de descomposición | ✓ |
| Procedencia visible (catálogo, versión, archivo fuente, SHA-256, fecha) | ✓ ambas fuentes |
| Comparación 2017 vs 2025 de la misma partida | ✓ 8,89 → 123,02 CUP/m³ (×13,85) |
| Búsqueda por texto + filtro por fuente | ✓ «excavacion» en PRECONS_III → 18 resultados |
| Errores de consola del navegador | ✓ ninguno |
| Captura de evidencia | `docs/datos/fase3f_poc_navegador.png` |

## 4. Pruebas de no-regresión del original

- `app/PRECOST-v9.17.html`: SHA-256 idéntico al tag `v9.17-original` tras TODAS las operaciones de la fase (extracción, importación, pruebas, navegador).
- `AUXILIAR_PRECODI.rar` y copia de análisis `codigo.mdb`: SHA-256 sin cambios.
- La PoC es **totalmente reversible**: eliminar `prueba/db/` restaura el estado previo sin tocar nada más.
