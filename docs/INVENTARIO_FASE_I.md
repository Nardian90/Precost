# FASE I — INVENTARIO Y PRESERVACIÓN DE ACTIVOS PRECOST

Fecha: 2026-10-14 · Repositorio: `/home/z/my-project/precost` · Rama: `evolucion` · Tag baseline: `v9.17-original`

## 1. Localización del proyecto y estado real

**No existe repositorio previo.** El proyecto llegó como un único archivo autónomo subido al chat. Estado verificado:

| Activo | Ruta | Tamaño | SHA-256 (primeros 16) |
|---|---|---|---|
| ORIGINAL (intacto, no tocar) | `/home/z/my-project/upload/PRECOST-v9.17.html` | 7.244.878 B | `50d3cf28e405201f` |
| Copia de trabajo (byte-idéntica) | `precost/app/PRECOST-v9.17.html` | 7.244.878 B | `50d3cf28e405201f` (verificado) |
| Instalador SIECONS 11 | `precost/activos/SIECONS_11_64Bit_MSA_13.exe` | 43.222.451 B | `e51befffe1205eff` |
| ZIP original Drive 1 | `precost/activos/APLICACION_SIECONS11.zip` | 42.783.005 B | `43594db25a0ebde9` |
| RAR original Drive 2 | `precost/activos/AUXILIAR_PRECODI.rar` | 25.310.728 B | `a34e944d5eac58d6` |

Punto de restauración: `git tag v9.17-original` (commit `1db420e` en `main`). Los binarios grandes quedan fuera de git (`.gitignore`) y se gestionan por `activos/SHA256SUMS.txt`. Regla adoptada: **`main` siempre contiene el original; todo cambio va en `evolucion` con justificación técnica por commit; no se reemplazan archivos completos sin justificar.**

## 2. Arquitectura real (verificada estáticamente, sin ejecutar)

- **Un solo archivo HTML autónomo**: 7.244.878 B totales → 1 bloque `<script>` con **7.020.901 B de JavaScript**, 127.172 B de CSS. **0 scripts externos, 0 librerías externas** (JSZip/SheetJS/jsPDF/pdfmake: 0 coincidencias).
- JS plano sin framework ni build: **269 funciones** definidas, **1.467 constantes**.
- Las 25 URLs «externas» son espacios de nombres XML de OOXML (no llamadas de red).
- **Red**: solo 3 `fetch()`, todas del copiloto IA y solo si el usuario configura endpoint+clave (`aiSettings`, `copilotConfig`, `copilotKey`). Sin configurar: **100 % offline**.
- **Almacenamiento**: `localStorage` con prefijo `p3pro.` — 23 claves: `budgets`, `currentId`, `userTemplates`, `importedCases`, `docsImported`, `importSeq`, `labResults`, `testResults`, `aiSettings`, `aiTemplates`, `copilotConfig`, `copilotKey`, `copilotState`, `anPick`, `catChapClosed`, `catFanClosed`, `catFilters`, `lastView`, `onboarded`, `t142`, `theme`, `uiMode`.
- **Router de vistas**: 13 vistas — `view-inicio`, `view-asistente`, `view-plantillas`, `view-mios`, `view-editor`, `view-ia`, `view-catalogo`, `view-anatomia`, `view-ayuda`, `view-config`, `view-laboratorio`, `view-normativa`, `view-reportes`.
- **Editor** con 6 pestañas: `tab-datos`, `tab-partidas`, `tab-recursos`, `tab-costos`, `tab-resumen`, `tab-exportar`.
- Doble interfaz heredada v8/v9 (`uiMode`, `v8Inicio`/`v9Inicio`).

## 3. Catálogo normativo embebido

Manifiesto con hashes SHA-256 por conjunto y conteos oficiales (autoritativos):

| Conjunto | Registros |
|---|---|
| Partidas | 15.912 |
| Grupos | 1.893 |
| Materiales | 3.568 |
| Equipos | 671 |
| Mano de obra | 143 |
| **Total** | **22.187** |

Formato de entrada: `"CÓDIGO": [descripción, unidad, precio MN, ..., precio, ..., "capítulo"]` (sondeo regex: 17.303 códigos con patrón de partida/grupo; el manifiesto es la cifra autoritativa).

## 4. Generadores de documentos (propios, sin dependencias)

- **XLSX**: generador OPC propio (58 refs. spreadsheetml), libro de 12 hojas (PRESUPUESTO, AUDITORIA, TRAZABILIDAD…), **fórmulas SUMPRODUCT reales** (24 refs.) → funciones `buildXLSX`, `exportXLSX`, `exportXLSXFixture`, `xlsxTitle`.
- **DOCX**: generador WordprocessingML propio (30 refs.) → `docxName`.
- **PDF**: 7 refs. `application/pdf` → `exportPDF`, `exportResumenEjecutivo`.
- Descargas vía `createObjectURL`; importación vía `FileReader` (7 refs.).

## 5. IA

- Contrato **PRECOST-AI-JSON**: 26 referencias, `contractVersion` (17 refs.).
- Funciones: `aiExportAIJSON`, `aiCompareModels`, `importJSONValidated`, `runImportPipeline`, panel copiloto (`fabCopiloto`, `cpDrawer`, `cpStatus`, indicador `netChip`).
- Multi-proveedor: endpoint OpenAI-compatible y Gemini (modelsURL, Bearer), credenciales aportadas por el usuario.

## 6. Pruebas disponibles (real)

- **Marco de validación integrado**: vista `view-laboratorio`, funciones `runFixtureValidation`, `validateFixture`, `validateFixture`, `exportConformanceMatrix`, `printInformeValidacion`; persistencia `labResults` y `testResults` → existen fixtures embebidos (profundidad a auditar en Fase IV).
- No existe suite de tests externa (archivo único sin empaquetado).

## 7. Sondeo funcional preliminar (la matriz formal es la Fase IV)

| Funcionalidad | Estado preliminar | Evidencia estática |
|---|---|---|
| Crear/editar presupuestos | Probable A | `nuevoPresupuesto`, `budgets`, `currentId`, `verPresupuestoCompleto` |
| Persistencia y recuperación | Probable A | claves `budgets`, `miosHist`, `lastView` |
| Catálogo embebido + búsqueda | Probable A | 22.187 registros + manifiesto, `catFilters`, `abrirBuscadorPartidas` |
| Exportar XLSX/PDF/Word | Probable A (verificar en vivo) | generadores OPC propios + SUMPRODUCT |
| Importación JSON / plantillas | Probable A | `importJSONValidated`, `runImportPipeline`, `userTemplates` |
| Versiones (comparar/restaurar/duplicar) | B — verificar profundidad | strings «VERSIONES (comparar · restaurar · duplicar)», `miosHist` |
| Descomposición de precios unitarios | B — verificar | `renderTabRecursos`, `recursosTable`, `equiposRecursoHTML` |
| Normativa PRECONS/MICONS | B | `view-normativa`, 500 refs. PRECONS, 152 MICONS |
| Copiloto IA | B — requiere endpoint externo configurado | 3 `fetch()` condicionales |
| BIM / IFC / Revit / Navisworks | **D — ausente** | 0 referencias |
| MS Project (.mpp) | **D — ausente** | 0 referencias |
| Gestión de bases .mdb externas | **D — ausente** | 0 refs. PRECODI/mdb |

## 8. Reglas de preservación

1. `upload/PRECOST-v9.17.html` nunca se modifica.
2. `main` = original etiquetado; desarrollo solo en `evolucion`.
3. Ninguna eliminación de funcionalidades, estilos, datos ni contratos (PRECOST-AI-JSON incluido).
4. Cambios de código justificados commit a commit.
