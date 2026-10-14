# MISIÓN III-C — Auditoría previa (FASE A)

Fecha: 2026-10-14 · Rama: `iii-c-descomposiciones-recursos` (base `evolucion` @ `f213d27`) · Tag `v9.17-original` intacto (→ `1db420e`).

## 1. Estado del repositorio (verificado)

- Rama activa `evolucion`, árbol limpio, HEAD `f213d27` (Misión III-B Fases 5-7).
- Entregables III-B presentes: `scripts/servidor_precodi.py`, `app/overlay/precodi.js`, `bd/precodi.db` (regenerable), migraciones `0001`-`0003`, `docs/` (17 informes), `datos_prueba/casos_iiib.json`.
- HTML original `app/PRECOST-v9.17.html` SHA-256 constante `50d3cf28…5cbaa2` (verificado por el servidor en cada arranque).

## 2. Pestaña Recursos y editor de presupuestos en el HTML real

- Editor: vista `editor` con `#editorTabs` → `switchEditorTab(tab)` → `renderEditor()`.
- `renderEditor()` (global, offset ≈5776022) despacha a `renderTabDatos(b,r)`, `renderTabPartidas(b,r)`, **`renderTabRecursos(b,r)`** (offset ≈5812203), `renderTabCostos(b,r)`, `renderTabResumen(b,r)`; contenedores `#tab-datos`…`#tab-recursos`…`#tab-resumen` (HTML estático vacío, render dinámico).
- `renderTabRecursos` **actual**: agregación a NIVEL DE PRESUPUESTO por renglón usando el catálogo embebido `DB.P` (mat=p[3], mo=p[4]×A.H, eq=p[5]×A.E según flags M/H/E) + composición documental de plantillas (`laborPuestosHTML`, `equiposRecursoHTML`). **No existe** descomposición por partida ni conexión con PRECODI: esa es exactamente la brecha que III-C llena.
- Punto de extensión: el script principal NO está envuelto en IIFE → `renderTabRecursos`, `currentBudget`, `touch`, `state`, `ENGINE`, `DB`, `fmt`, `esc`, `ico`, `openModal`, `toast`, `go` son accesibles desde un script inyectado (ámbito léxico global compartido entre scripts clásicos). Se puede ampliar la pestaña con un parche en tiempo de ejecución **sin tocar el archivo HTML** (el original en disco permanece byte-idéntico; la extensión la inyecta el servidor local, igual que en III-B).

## 3. Funciones que crean, editan, guardan y recalculan partidas

| Operación | Función (global) | Mecanismo |
|---|---|---|
| Crear presupuesto | `nuevoPresupuesto()` → `emptyBudget()` | `state.budgets.unshift(b)`, `state.currentId=b.id`, `saveBudgets()` |
| Añadir partida | `abrirBuscadorPartidas(b)` | `b.items.push({codigo, descripcion, um, tipo:"partida", flags:"MHE", cantidad:1, precio:null, coef:1, capitulo, subcapitulo, subcapituloDesc})` |
| Editar cantidad | inputs `[data-qidx]` en `#tab-partidas` | `b.items[i].cantidad = max(0, v)` → `touch(b)` → `renderEditor()` |
| Editar precio (elemento) | inputs `[data-pidx]` + `editarReferenciaMercado` | `it.precio` → `touch(b)` |
| Guardar | `touch(b)` → `saveBudgets()` → `LS.set("budgets", state.budgets)` | localStorage **`p3pro.budgets`** (JSON, atómico por clave) + `p3pro.currentId` |
| Recalcular | `ENGINE.calc(b)` | ver §5 |

`emptyBudget()`: `{id, nombre, proyecto, database:"PRECONS III MICONS 2025…", coef:{AH:5, AE:1, coefMat:1, coefRH:1, coefEq:1}, gastos, impuestos, utilidad, items:[]}`.

## 4. Esquema SQLite real y consultas del servidor PRECODI

Tablas relevantes (migraciones 0001+0002+0003, sin duplicar entidades):

- `versiones_catalogo` (6 versiones: PRECODI 2007-v7.21 / v7.22 / 2017-raíz / 2011-sbd2008, PRECONS_III 2025-06-06) + `catalogos`.
- `partidas` (código, descripcion, unidad, costo_mat/mo/eq/total_mn, factor_unidad, capitulo) **por versión**.
- `normas_partida`: `partida_id, version_id, tipo_recurso_id, codigo_recurso, coeficiente, cod_norma, um_norma` — la relación partida→recurso.
- `recursos`: `version_id, tipo_id, codigo, descripcion, unidad, precio_mn, precio_mlc` — nomencladores.
- `tipos_recurso`: **material, mano_obra, equipo, juego, semielaborado** (5 categorías reales, verificadas).
- `componentes_recurso`: descomposición de juegos y semielaborados.
- `proyectos`, `presupuestos`, `capitulos_presupuesto`, `partidas_presupuesto` (0002): **existen y están vacías** — PRECOST persiste presupuestos en localStorage; no se duplican.

API actual (solo lectura, 127.0.0.1): `/api/versiones`, `/api/partidas?q&version_id`, `/api/partida/{codigo}?version_id` (normas + componentes de juegos/semis + subtotales + verificación CMMN/CHMN/CEMN + otras_versiones), `/api/stats`.

## 5. Cómo se representan cantidades, unidades, precios y subtotales

- PRECOST: `it.cantidad` REAL (step 0.0001), `importe = precio × cantidad` (motor: `ENGINE.calc`); cadena CD = mat+mo+eq → GAPO/GGA → GT (FT 5% + SS 14%) → Utilidad (Res. 173/2025, máx 15%); PU por renglón = flags M/H/E sobre `DB.P[c] = [desc, um, total, mat, mo, eq, peso, seccion]` con A.H×MO y A.E×EQ; `precioDoc` preservado si el ítem proviene de documento (trazabilidad doc/cat/mercado/usuario).
- PRECODI (importado): `coeficiente` REAL con el **valor Float32 exacto** (p. ej. 2.4000000953674316), `precio_mn` REAL con Money de **4 decimales exacto** (p. ej. 57.9998); importe = coef × precio; subtotales por tipo = Σ importes; verificación contra costos almacenados CMMN/CHMN/CEMN con tolerancia por número de términos y magnitud (regla documentada en `docs/FASE_III_INTEGRACION.md`).
- Unidades: partida (m3, m2, m…) ≠ recurso (u, ml, kg, hh, he, jg…); `um_norma` mayormente vacía (S/C); compatibilidad entre versiones: 148 unidades con cambio 2017→2025 documentado en III-B (pendiente de verificación caso a caso).

## 6. Relaciones partida → norma → recursos verificadas con datos (FASE B, v3=2017-raíz)

- 73.978 normas; **0 referencias sin resolver** (todas las `codigo_recurso` existen en `recursos` de su versión).
- 15.350/15.351 partidas con norma; única sin norma: **`999999` SUMINISTROS** (caso de prueba «partida sin norma»).
- Composición por tipo: material 18.060 · mano_obra 41.662 · equipo 12.909 · juego 341 · semielaborado 1.006.
- Caso `012141` (regresión): 9 componentes (3 mat, 2 MO, 4 EQ), coeficientes Float32 (1.2, 1.5, 0.8, 2.4, 0.0096, 0.1667, 0.0167, 0.0096, 0.1667), precios 3-4 decimales; PU 8.8881 (2007/2017), 9.6902 (2011-SBD), 123.02 (PRECOST 2025).
- Juegos y semielaborados expandibles vía `componentes_recurso` (ej. `096231` contiene juego + semielaborado + materiales + MO + equipos → caso multi-categoría).

## 7. Migraciones previas

- `0001_catalogo.sql` (16 tablas del catálogo versionado), `0002_proyectos.sql` (proyectos/presupuestos/capítulos/partidas presupuestadas con snapshot JSON — **aún no usada por PRECOST**), `0003_precision_sbd.sql` (SBD).
- **Decisión FASE F**: no se crea una segunda implementación de entidades. El mecanismo de persistencia EXISTENTE de PRECOST (localStorage `p3pro.budgets`, JSON atómico) es suficiente para el flujo III-C: el snapshot de la norma se guarda dentro del propio ítem del presupuesto (`it.normaPreco`), lo que preserva presupuestos históricos ante cambios de catálogo (filosofía snapshot de `0002`, aplicada donde PRECOST realmente persiste). Las tablas 0002 quedan como destino documentado de la evolución futura; no se duplican.

## 8. Fixtures identificados para las 16 pruebas (FASE G)

| # | Caso | Fixture real |
|---|---|---|
| 1, 3-6, 16 | Partida con norma completa / materiales / MO / equipos / multi-categoría / regresión | `012141` (3 mat + 2 MO + 4 EQ), `096231` (juego+semi+mat+MO+EQ) |
| 2 | Partida sin norma | `999999` SUMINISTROS (v3) |
| 7 | Referencias inexistentes | 0 en v3 (dato verificado) → se sintetiza SOLO en fixture de prueba de la API, sin tocar datos |
| 8 | Código duplicado/ambiguo | Sin duplicados dentro de una versión (verificado); ambigüedad real = mismo código en varias versiones → resolución por `version_id` |
| 9 | Coeficientes fraccionarios | `012141` (0.0096, 0.0167, 0.1667 — Float32 exacto) |
| 10 | Importes 4 decimales | Recurso `000017` CEMENTO P-350 (57.9998), `0000004111` (143.6096) |
| 11 | Cambio de cantidad | flujo UI (cantidad → consumo=coef×cantidad) |
| 12 | Diferencias de precio entre versiones | `012141`: 8.8881 (2007/2017) vs 9.6902 (2011) vs 123.02 (2025) |
| 13-14 | Guardado/recuperación y reapertura histórica | localStorage `p3pro.budgets` + snapshot `it.normaPreco` |
| 15 | Conservación del catálogo embebido | SHA-256 del HTML + `DB.meta` intactos tras el flujo |

## 9. Riesgos y decisiones

1. **No se puede parchear el HTML original** (regla de la misión) → toda la UI de III-C vive en un overlay inyectado (`app/overlay/recursos.js`) que amplía `renderTabRecursos` en tiempo de ejecución; el archivo en disco no cambia (SHA verificado por request).
2. **La descomposición PRECODI (2017) y el PU del motor PRECOST (2025, A.H=5) difieren por diseño** → la UI debe mostrar ambas cifras con su fuente y advertir; nunca sustituir silenciosamente el PU del presupuesto.
3. **Códigos compartidos 2017↔2025**: 14.451 (94,1%); los recursos de las normas existen en nomencladores 2025 embebidos (`DB.M`/`DB.O`/`DB.E`) con precios propios → fuente de precios alternativa verificable (compatibilidad por código+unidad, con advertencias).
4. **Servidor ausente** (apertura `file://`): la sección se degrada con honestidad — solo muestra snapshots guardados en el presupuesto y un aviso; no inventa datos.
