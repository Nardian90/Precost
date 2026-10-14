# FASE III — ESQUEMA DE BASE DE DATOS PROPUESTO PARA PRECOST

Fecha: 2026-10-14 · DDL: `bd/migraciones/0001_catalogo.sql` y `bd/migraciones/0002_proyectos.sql`
Ejecutor de migraciones: `scripts/fase3e_migrar.py` (idempotente, registra `schema_migrations`)

## 1. Decisión de motor: SQLite (justificada sobre el PRECOST existente)

| Criterio | Situación de PRECOST v9.17 | Consecuencia |
|---|---|---|
| Arquitectura real | HTML único 100 % offline, sin servidor, sin dependencias externas | Un motor **embebido** es el único que no rompe la arquitectura |
| Persistencia actual | `localStorage` (`p3pro.*`, 23 claves) — límite ~5–10 MB, sin consultas | El catálogo embebido ya pesa 2,1 MB; con normas PRECODI (~80 MB de .mdb → ~20 MB útiles) se supera localStorage |
| Consultas necesarias | buscar por código/descripción, descomposición, comparar versiones | SQL con índices, imposible en localStorage sin cargar todo en RAM |
| Portabilidad | El usuario guarda/copia un archivo | SQLite = **un archivo** (`precost.db`), portable y respaldable |
| Vía de integración en navegador | — | sql.js (SQLite WASM, archivo único sin red) u OPFS + `sqlite-wasm`; el patrón de consulta ya está demostrado en la PoC de la Fase III-F |

**Decisión**: SQLite como almacenamiento local inicial. Un servidor solo se justificaría si aparecieran requisitos ausentes hoy: multiusuario concurrente, catálogo central editado por varias personas o sincronización en tiempo real — nada de lo cual exige el PRECOST actual. El esquema SQL es estándar y portable a PostgreSQL si ese día llega (sin tipos propietarios; los JSON se usan solo en columnas de snapshot/auditoría).

## 2. Modelo (migración 0001 — núcleo de catálogos)

16 tablas: `catalogos`, `versiones_catalogo`, `importaciones`, `grupos`, `partidas`, `tipos_recurso`, `recursos`, `normas_partida`, `componentes_recurso`, `precios_recurso`, `auditoria` (+ `schema_migrations`).

### Decisiones clave

1. **Versionado e inmutabilidad**: cada importación crea una `versiones_catalogo` (PRECODI `2017-raiz`, PRECONS_III `2025-06-06`, …). Las partidas/recursos se insertan POR VERSIÓN; nunca se sobrescriben. Así PRECOST puede mostrar «costo 2017 vs 2025» con procedencia — imposible hoy.
2. **Claves estables de negocio**: `codigo` (6 d partidas, 10 d recursos) — verificado único en ambas fuentes (CODIGO RV 15.351/15.351; claves de P/M/O/E). Los autonuméricos de Access (`IdM`, `IdEstab`…) son locales a cada .mdb y **se excluyen** como claves.
3. **Recursos unificados con tipo discriminator** (`tipos_recurso`: material/mano_obra/equipo/juego/semielaborado): refleja que los 5 nomencladores PRECODI comparten estructura de precios (PMN/PMLC/PrecioU/PesoU) y simplifica la descomposición a una sola tabla `normas_partida`.
4. **`componentes_recurso`** separa la composición de recursos compuestos (juego→materiales; semielaborado→mat/mo/eq) de la norma de la partida — espejo exacto de las tablas `Norma Juego Material`/`Norma Semi *`.
5. **`cod_norma`** se conserva en `normas_partida` (PK compuesta) porque la fuente distingue variantes de norma del mismo recurso (verificado: 4.963 pares RV-recurso con >1 CodNorma).
6. **`precios_recurso`** guarda la evolución de precios por fuente y fecha ('PRECODI-2017', 'PRECONS_III_2025', 'mercado', 'usuario') — habilita actualizaciones de precios sin tocar el dato normativo.
7. **Restricciones**: `ON DELETE RESTRICT` en todas las FK (no se borra nada referenciado; el flujo es insertar versiones nuevas); `CHECK` en estados y niveles; `UNIQUE` por (versión, código) y en composiciones.
8. **`factor_unidad`**: la unidad se normaliza ('100 m2' → m2 + factor 100.0) preservando el dato original en texto.
9. **Procedencia obligatoria**: `versiones_catalogo.fuente_archivo + fuente_sha256 + fuente_detalle` y registro `importaciones` (script, filas por tabla, advertencias, resultado) — cada dato es rastreable al archivo exacto de origen.
10. **`auditoria`** append-only: toda modificación posterior (updates de precios de usuario, validaciones) se registra con datos antes/después JSON.

## 3. Modelo (migración 0002 — proyectos y presupuestos)

`proyectos` → `presupuestos` (versiones, estados borrador→emitido→aprobado→cerrado) → `capitulos_presupuesto` → `partidas_presupuesto` (cantidad + `costo_unitario_json` snapshot + `descomposicion_json` opcional). Diseño alineado con el modelo de `p3pro.budgets` actual de PRECOST y con el vocabulario verificado de SBD2008_815 (`Obras`, `Presupuesto Composición *`): la partida presupuestada referencia la partida de catálogo POR VERSIÓN y congela el costo unitario usado, para que futuras importaciones de catálogo no alteren presupuestos cerrados.

## 4. Índices (justificados por las consultas de la PoC)

| Índice | Consulta que habilita |
|---|---|
| `idx_partidas_codigo` | búsqueda por código (demostrada) |
| `idx_partidas_desc` (NOCASE) | búsqueda por texto (demostrada) |
| `idx_recursos_codigo/desc` | buscador de recursos |
| `idx_normas_partida_rv` | descomposición de una partida (demostrada) |
| `idx_normas_recurso` | inversa: dónde se consume un recurso |
| `idx_componentes_recurso` | expandir juegos/semis |
| `idx_grupos_padre` | árbol de capítulos/grupos/subgrupos |
| `idx_auditoria_tabla` | historial por registro |

## 5. Migraciones versionadas y respaldo

- Cada fichero `bd/migraciones/NNNN_*.sql` se aplica en orden una sola vez (tabla `schema_migrations`); el ejecutor es idempotente y puede crear la base desde cero.
- **Respaldo**: SQLite en modo WAL + `VACUUM INTO 'respaldo-AAAAMMDD.db'` (transaccional, en línea) y/o copia del archivo único con la app cerrada. El respaldo NO requiere exportar/importar (es copia de archivo) — ventaja documentada frente a localStorage (hoy: export JSON manual).
- **Ruta de evolución**: 0003 podría añadir `certificaciones`/`cronograma` siguiendo el vocabulario verificado de SBD2008_815 — sin tocar 0001/0002 (las migraciones son aditivas).

## 6. Correspondencia con las fuentes (mapeo implementado)

| Origen | Destino | Nota |
|---|---|---|
| PRECODI `Nomenclador de RV` | `partidas` (versión PRECODI) | CMMN/CHMN/CEMN/CMMLC → costo_*; HORAS/PESO/Res_Aprov incluidos |
| PRECODI 5 nomencladores | `recursos` | PMN/PMLC/PrecioU/PesoU; grupo salarial en MO |
| PRECODI 5 tablas `Norma de *` | `normas_partida` | coeficiente = Cant*; cod_norma conservado |
| PRECODI `Norma Juego Material` / `Norma Semi *` | `componentes_recurso` | |
| PRECODI jerarquía SG/G/SG | `grupos` (catálogo PRECODI) | |
| PRECOST `P` | `partidas` (versión PRECONS_III) | p[2..6] → total/mat/mo/eq/peso; p[7] → capítulo |
| PRECOST `M`/`O`/`E` | `recursos` + `precios_recurso` | precio unitario + registro con fecha 2025-06-06 |
| PRECOST `G` | `grupos` (catálogo PRECONS_III) | 32 huérfanos con padre NULL + advertencia |

La implementación de referencia está en `scripts/fase3f_importar_poc.py` (muestra verificable) — el importador completo del catálogo es el siguiente paso (ver `LIMITACIONES_Y_SIGUIENTES_PASOS.md`).
