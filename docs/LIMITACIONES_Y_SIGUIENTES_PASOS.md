# FASE III — LIMITACIONES Y SIGUIENTES PASOS

Fecha: 2026-10-14

## 1. Limitaciones honestas de esta fase

### Del entorno
| Limitación | Efecto | Mitigación aplicada |
|---|---|---|
| Sin Windows ni VM ni Wine (contenedor Linux, sin root) | SIECONS 11 y Codigo.exe **no ejecutados**; ninguna verificación dinámica de la lógica de recálculo | Modelo de precios reconstruido y verificado **estáticamente** contra 15.350 valores almacenados (masivo, no muestral) |
| `mdbtools` no disponible | Sin `mdb-schema`/`mdb-tables` nativos | `access-parser` (Python) — PK reales leídas de la definición de tabla; MSys* ilegible (sin impacto) |
| pip sin red en la sesión original | — | `access-parser` ya instalado en Fase II; sin nuevas dependencias en Fase III |

### De los datos
| Limitación | Evidencia | Estado |
|---|---|---|
| Fórmulas PENDIENTES (no demostrables): HORAS OPERARIO/AYUDANTE, PESO del RV, explicación del patrón ×10 | hipótesis probadas y rechazadas con conteos exactos (`MODELO_PRECIOS_UNITARIOS.md` §5) | Documentadas; **ninguna regla inventada** |
| Deriva de precios en PRECODI (costos almacenados desactualizados vs precios vigentes) | F1: 718/14.602 RVs | Documentada; la importación registra advertencias por partida |
| PRECOST 2025 sin descomposiciones | 0 normas en el catálogo embebido | Es el hallazgo que motiva la integración, no un defecto corregible aquí |
| 32 grupos huérfanos en G de PRECOST | subgrupos con partidas y sin padre en la fuente | Importados con padre NULL + advertencia |
| 148 unidades con cambio aparente 2017→2025 (ct/cu/dc/d2/mm/hl) | pares documentados con ejemplos | Verificación semántica pendiente (requiere norma PDF 2025) |
| `AGIT_Indicadores Hijos`, `HojaCalculo`, tablas de trabajo de SBD (`Candado`, `ddddd`…) | interpretación parcial o nula | Documentadas con confianza Media/Baja; sin especulación |

### Del alcance de la PoC
1. **No se migró el catálogo completo** (decisión metodológica exigida): la PoC importa 510 partidas PRECODI + 615 PRECONS + 2.239 normas. El importador completo es trabajo de la Fase VI (módulo D).
2. **La PoC de navegador es una página separada** (`prueba/poc_catalogo_externo.html`), no una modificación del PRECOST original: demuestra el patrón de consulta externa sin riesgo de regresión. La integración en el HTML real (sql.js/OPFS + vista Catálogo) es la Fase VI.
3. Los presupuestos (migración 0002) están **diseñados pero sin datos**: la migración de `p3pro.budgets` a SQLite requiere la Fase IV (auditoría del formato real de budgets en localStorage).
4. El export JSON de la PoC (1,35 MB) es un vehículo de demostración; el objetivo final es consultar SQLite directamente desde el navegador (sql.js) o vía el patrón archivo+índice.

## 2. Qué quedó verificado y listo (resumen ejecutable)

| Activo | Ruta | Verificación |
|---|---|---|
| Inventario 5 bases .mdb | `docs/datos/fase3a_inventario.json` + `fase3a_resumen.md` | hashes, 357 tablas, PK, tipos, conteos |
| Diccionario + relaciones | `docs/datos/fase3b_diccionario.json` + `fase3b_relaciones.json` | 23/23 relaciones VERIFICADAS (0 huérfanos) |
| Modelo de precios | `docs/datos/fase3c_verificacion.json` | F2/F4/F5/F6/F9/F11 VERIFICADAS; F1/F3/F7/F8 PARCIALES con excepciones cuantificadas |
| Catálogo PRECOST extraído | `docs/datos/fase3d_precost_db.json` | 22.187 registros; HTML intacto (SHA-256) |
| Conciliación | `docs/datos/fase3d_conciliacion.json` | 14.451 códigos compartidos; equivalencias y conflictos documentados |
| Esquema + migraciones | `bd/migraciones/0001_catalogo.sql`, `0002_proyectos.sql` | aplicadas por `scripts/fase3e_migrar.py` |
| Base de prueba | `prueba/db/precost_catalogo.db` (+ `catalogo_export.json`) | 24/24 pruebas automatizadas |
| PoC navegador | `prueba/poc_catalogo_externo.html` | verificada con navegador headless, sin errores |

## 3. Siguientes pasos recomendados (orden y dependencias)

**Fase IV — Auditoría funcional de PRECOST (próxima, ya habilitada por esta fase)**
1. Mapear el formato real de `p3pro.budgets` y el motor de cálculo del editor (tab-recursos/costos) → contrato de migración a `partidas_presupuesto`.
2. Auditar la vista Catálogo (`abrirBuscadorPartidas`, `catFilters`) → puntos de extensión para catálogo externo.
3. Matriz formal de funcionalidades (la Fase I dejó sondeo preliminar).

**Fase V/VI — Importación completa e integración**
4. Importador completo PRECODI (15.351 RVs + 74.978 normas + 8.923 recursos) con reanudación y advertencias por partida → SQLite.
5. Decidir vía SQLite en el HTML: sql.js embebido (archivo único, +~1,5 MB WASM gzip) vs. OPFS — ambos compatibles con «offline primero»; evaluar tamaño final.
6. Extender la vista Catálogo con selector de versión/fuente y descomposición (patrón ya demostrado en la PoC).
7. Recalculadora de costos unitarios con las fórmulas verificadas (mostrar almacenado vs recalculado).

**Verificaciones que requieren recursos externos**
8. Resolución de fórmulas PENDIENTES: ejecutar SIECONS/Codigo.exe en VM Windows propia (checklist en `INFORME_FASE_II.md` §7) o consultar las normas PDF PRECONS III 2025 (SECCION-01..45).
9. Unidades con cambio 2017→2025: cotejo con los PDF oficiales 2025.
10. Decisión sobre descarga del .7z oficial 2026 (`pasion`) para obtener SBD_MICONS_2025.mdb — opcional, con autorización del usuario.

## 4. Riesgos abiertos

| Riesgo | Probabilidad | Contención |
|---|---|---|
| Patrón ×10 en PRECODI confunda al recálculo | media (259 partidas) | La importación marca advertencias; la UI debe distinguir almacenado vs recalculado |
| sql.js aumente el peso del HTML único | alta (≈1,5 MB) | alternativa OPFS; o carga diferida del catálogo bajo demanda (fetch local) |
| Formato `p3pro.budgets` incompatible con el esquema 0002 | media | La Fase IV audita antes de migrar; 0002 admite ajustes por migración 0003 sin romper 0001 |
| Unidades ambiguas (ct/cu/dc/d2/mm) generen cantidades erróneas ×10/×100 | media | factor_unidad + validación cruzada con descripciones (el número suele quedar pegado a la descripción 2025) |
