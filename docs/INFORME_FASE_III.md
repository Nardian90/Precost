# INFORME DE FASE III — INGENIERÍA DE DATOS PRECODI Y PLAN DE INTEGRACIÓN EN PRECOST

Fecha: 2026-10-14 · Repositorio: `/home/z/my-project/precost` · Rama: `evolucion` · Baseline inmutable: tag `v9.17-original`
Precedentes: `docs/INVENTARIO_FASE_I.md`, `docs/INFORME_FASE_II.md`

**Cumplimiento de condiciones de aceptación**: archivos originales intactos (verificados por SHA-256 en cada script: HTML `50d3cf28…` y codigo.mdb `c4f94962…`); todos los informes reflejan datos realmente examinados; todos los recuentos son reproducibles por scripts; las fórmulas están respaldadas por evidencia masiva o marcadas PENDIENTES; la prueba de concepto funciona (24/24 pruebas + verificación en navegador real) sin tocar las funcionalidades existentes.

---

## Ejecución por subfases

### III-A · Inventario y metadatos — COMPLETA
5 bases `.mdb` localizadas, con hash SHA-256, procedencia dentro del RAR, formato Jet y 357 tablas de usuario inventariadas (nombre, columnas, tipos Jet, nulabilidad, autonuméricos, PK **leídas de la definición de tabla**, filas, muestras). Hallazgos: `Preambulos/codigo.mdb` es byte-idéntico a `7.21/`; la raíz 2017 es la canónica (24 tablas); SBD2008_815 = núcleo PRECODI + 272 tablas empresariales. → `docs/DICCIONARIO_DATOS.md` §1, `docs/datos/fase3a_*`

### III-B · Diccionario de datos — COMPLETA
Diccionario por tabla con finalidad, tipos, PK, **23/23 relaciones verificadas con datos reales (0 huérfanos)**, dominios de unidades, calidad (duplicados, nulos, mayúsculas inconsistentes) y nivel de confianza por tabla. CODIGO RV es único por sí solo (15.351/15.351) — la clave de integración. → `docs/DICCIONARIO_DATOS.md`, `docs/datos/fase3b_*`, `docs/DIAGRAMA_RELACIONAL.md`, `docs/COMPARATIVA_ESQUEMAS.md`

### III-C · Modelo de precios unitarios — COMPLETA (con 4 fórmulas PENDIENTES documentadas)
```
PRECIO UNITARIO RV = CMMN + CHMN + CEMN
CMMN = Σ CantMat×PMN + Σ CantJuego×PMN_juego + Σ CantSElab×PMN_semi   [93,5% exacto]
CHMN = Σ CantRHum×PMN                                                 [98,3% exacto]
CEMN = Σ CantEquipo×PMN                                               [91,6% exacto]
CMMLC = Σ CantMat×PMLC                                                [100% exacto]
HORAS HOMBRE/EQUIPO = Σ coeficientes                                  [99,99% exacto]
PrecioU = PMN + PMLC (5 nomencladores)                                [96–100% exacto]
```
Pendientes sin inventar: HORAS OPERARIO/AYUDANTE (3 hipótesis rechazadas), PESO (1 rechazada), explicación del patrón ×10 en 259 partidas, FACTOR (constante 1,0). → `docs/MODELO_PRECIOS_UNITARIOS.md`, `docs/datos/fase3c_verificacion.json`

### III-D · Conciliación con el catálogo embebido — COMPLETA
Catálogo PRECOST extraído íntegro sin modificar el HTML (const `DB`, 22.187 registros, PRECONS III MICONS 2025, publicada 06/06/25). Conciliación: **14.451 códigos de partida compartidos** (94% de PRECODI), 13.462 descripciones idénticas, 4.377 unidades equivalentes por abreviatura, ratio de precios 2025/2017 mediana ×11,13. **Hallazgo central: PRECOST 2025 no contiene descomposiciones; PRECODI las tiene para el 100% de los códigos compartidos.** → `docs/INFORME_CONCILIACION.md`, `docs/datos/fase3d_*`

### III-E · Diseño de base de datos — COMPLETA
SQLite (justificado por arquitectura offline de un solo archivo), 16 tablas en 2 migraciones versionadas e idempotentes, claves estables de negocio, versionado por catálogo (nunca se sobrescribe), procedencia con hash, auditoría append-only, precios por fuente/fecha, y módulo proyectos/presupuestos con snapshots. → `docs/ESQUEMA_BD_PRECOST.md`, `bd/migraciones/0001_catalogo.sql`, `bd/migraciones/0002_proyectos.sql`, `scripts/fase3e_migrar.py`

### III-F · Prueba de concepto — COMPLETA Y VERIFICADA
Base nueva aislada (`prueba/db/precost_catalogo.db`), muestra representativa importada (510 partidas PRECODI del sobregrupo 01 + 20 con juegos + 20 con semis, 2.239 normas, 276 recursos; 615 partidas PRECONS 2025 del capítulo 01, 245 recursos comparables), **24/24 pruebas automatizadas superadas** (recuentos recalculados desde las fuentes, integridad FK, fórmulas, procedencia, inmutabilidad de originales), y página de consulta de catálogo externo verificada en navegador real con búsqueda por código/texto, descomposición con coeficientes y precios, comparación 2017 vs 2025 y procedencia visible. Reversible: basta eliminar `prueba/db/`. → `docs/PRUEBAS_Y_RESULTADOS.md`, `prueba/`, `scripts/fase3f_*`

---

## Los 10 entregables de la fase

| # | Entregable | Ubicación |
|---|---|---|
| 1 | Diccionarios de datos por base | `docs/DICCIONARIO_DATOS.md` (+ JSON en `docs/datos/`) |
| 2 | Diagramas relacionales | `docs/DIAGRAMA_RELACIONAL.md` (ER Mermaid + grafo de cálculo + correspondencia) |
| 3 | Comparativa de esquemas entre versiones | `docs/COMPARATIVA_ESQUEMAS.md` (+ `fase3b_comparativa.json`) |
| 4 | Informe del modelo de precios unitarios | `docs/MODELO_PRECIOS_UNITARIOS.md` (+ `fase3c_verificacion.json`) |
| 5 | Informe de conciliación PRECODI–PRECOST | `docs/INFORME_CONCILIACION.md` (+ `fase3d_conciliacion.json`) |
| 6 | Esquema propuesto de base de datos | `docs/ESQUEMA_BD_PRECOST.md` |
| 7 | Migraciones y scripts de importación | `bd/migraciones/` + `scripts/fase3e_migrar.py`, `scripts/fase3f_importar_poc.py` |
| 8 | Prueba de concepto ejecutable | `prueba/` (base SQLite + export JSON + `poc_catalogo_externo.html`) |
| 9 | Pruebas automatizadas y resultados | `docs/PRUEBAS_Y_RESULTADOS.md` (+ `fase3f_resultados_tests.json`, `fase3f_poc_navegador.png`) |
| 10 | Limitaciones y siguientes pasos | `docs/LIMITACIONES_Y_SIGUIENTES_PASOS.md` |

Scripts reproducibles (todos solo-lectura sobre los originales): `fase3a_inventario_mdb.py`, `fase3b_diccionario.py`, `fase3c_modelo_precios.py` (+ `fase3c_debug_semi.py`), `fase3d_extraer_catalogo.py`, `fase3d_conciliar.py`, `fase3e_migrar.py`, `fase3f_importar_poc.py`, `fase3f_exportar_json.py`, `fase3f_tests.py`.

## Cifras clave de la fase (todas reproducibles)

| Cifra | Valor |
|---|---:|
| Bases .mdb analizadas (hashes) | 5 (2 idénticas entre sí) |
| Tablas inventariadas | 357 |
| Relaciones FK verificadas con datos | 23/23, 0 huérfanos |
| RVs con fórmula de mano de obra verificada | 14.980/15.246 |
| RVs con componente MLC verificado | 15.350/15.350 |
| Registros del catálogo PRECOST extraído | 22.187 (HTML intacto) |
| Códigos compartidos PRECODI↔PRECOST | 14.451 (94,1% de PRECODI) |
| Descomposiciones disponibles solo en PRECODI | 15.350 normas → 100% de compartidos |
| Pruebas automatizadas superadas | 24/24 |
| Modificaciones al HTML original | **0** (SHA-256 constante en todas las verificaciones) |

## Conclusión

Las dos fuentes —PRECODI 2017 y el catálogo embebido PRECOST 2025— son **el mismo nomenclador normativo cubano en dos momentos**, con claves de código estables y compatibles. PRECOST 2025 aporta vigencia de precios; PRECODI aporta las descomposiciones de consumo que PRECOST no tiene. El esquema SQLite versionado diseñado e implementado en la PoC permite a PRECOST consumir ambas fuentes con procedencia sin sobrescribir nada, sentando la base técnica de los módulos A–G de la Fase VI.
