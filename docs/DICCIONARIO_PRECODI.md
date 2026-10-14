# DICCIONARIO PRECODI — CONSOLIDADO (MISIÓN III-B)

Fecha: 2026-10-14 · Fuentes: núcleo PRECODI (4 variantes de `codigo.mdb` + SBD2008_815) y
catálogo embebido PRECOST 2025. Diccionario por columna de las tablas del núcleo:
`docs/DICCIONARIO_DATOS.md` (fase III-B anterior, sigue vigente). Este documento consolida
el modelo **ya importado** en `bd/precodi.db` y la clasificación SBD.

---

## 1. Núcleo PRECODI → esquema común (migraciones 0001/0003)

| Tabla fuente .mdb | Entidad SQLite | Clave natural | Notas de transformación |
|---|---|---|---|
| Nomenclador de SobreGrupos/Grupos/SubGrupos RV | `grupos` (nivel 1/2/3) | (catálogo, nivel, código) | compartida por catálogo: la 1ª versión importa, las siguientes cuentan `ya_existentes` y detectan conflictos de descripción sin sobrescribir |
| Nomenclador de RV | `partidas` | (versión, código 6 dígitos) | unidad normalizada + `factor_unidad` («100 m2»→m2, ×100); costos Money→REAL exacto; `costo_total_mn` recalculado CMMN+CHMN+CEMN; columnas de fidelidad 0003: `chmlc`, `cemlc`, `horas_operario`, `horas_ayudante`, `tipo_rv`, `desc_corta` |
| Nomenclador de Materiales / Mano de Obra / Equipos / Juegos / Semielaborados | `recursos` (tipo_id) | (versión, tipo, código 10 dígitos) | PMN/PMLC/PrecioU Money exacto; mano de obra conserva grupo salarial y especialidad; equipos conservan tipo y norma horaria |
| Norma de Materiales / Mano de Obra / Equipos / Juegos / Semielaborados | `normas_partida` | (partida, tipo, recurso, cod_norma) | coeficiente Float32 preservado bit a bit; `cod_norma` ('S/C' si simple) y `um_norma` de las normas complejas de MO/equipos; huérfanas de partida omitidas y contadas |
| Norma Juego Material (+ **Material1**) | `componentes_recurso` | (recurso juego, material, norma) | Material1 verificada copia EXACTA (2936/2936) en la raíz: no se reimporta |
| Norma Semi Material / RHumanos / Equipos | `componentes_recurso` | (recurso semi, componente, norma) | descomposición de semielaborados en material/MO/equipo |

Convenciones de precisión: `scripts/precision_precodi.py` (Money→Decimal /10 000 exacto,
Float32 preservado, tolerancias por tipo y magnitud).

## 2. PRECOST 2025 (catálogo embebido) → mismo esquema común

`const DB` extraída sin modificar el HTML (fase III-D): grupos G→`grupos` (catálogo
PRECONS_III), partidas P→`partidas` (versión 2025-06-06), recursos M/O/E→`recursos` con
precio en `precios_recurso` (fuente+fecha). **Sin descomposiciones** (asimetría central
documentada en la conciliación).

## 3. SBD2008_815 — clasificación de las 284 tablas

`scripts/clasificar_sbd.py` → `docs/datos/sbd_clasificacion.json` (cada tabla con
categoría, filas, columnas y motivo).

| Categoría | Tablas | Filas | Tratamiento |
|---|---:|---:|---|
| 1 · Integrable directamente (esquema idéntico al núcleo) | 4 | 60 173 | importador común sin adaptación |
| 2 · Integrable mediante transformación | 38 | 331 862 | 24 priorizadas + núcleo adaptado + padres mínimos |
| 3 · Solo documental/referencia (AGIT, contratos, certificaciones, bancos…) | 19 | 20 370 | quedan en la base original, no se importan |
| 4 · Pendiente (112 vacías + sin semántica verificada) | 223 | 32 683 | no se importan sin comprender su finalidad |

### 3.1 Tablas sbd_* importadas (migración 0003) y su transformación

| Tabla sbd_* | Fuente | Filas | Transformación / verificación con datos |
|---|---|---:|---|
| `sbd_colecciones` | Colecciones | 27 | cabeceras (IdColec→id_colec_origen) |
| `sbd_colecciones_recursos` | Colecciones Composición | 1 570 | precio por colección; huérfanas contadas |
| `sbd_colec_rv` | ColecRV Composición | 92 054 | variantes salariales por partida y colección; CodigoRV verificado contra partidas |
| `sbd_normas_recurso` | Normas RH + Normas Eq | 9 893 | unificadas por clase RH/EQ (misma estructura de 9 columnas) |
| `sbd_normas_rh_extendida` | Normas RH Extendida | 57 838 | CodRHum verificado contra nomenclador; ImpS Float32 preservado |
| `sbd_normas_descriptivas` | Normas Descriptivas | 2 360 | cuadrilla (FT_DESC/CANTIDAD/GRUPO 1..6) como JSON; sin PK en fuente: unicidad por contenido, variantes reales conservadas (4 de la norma 120027) |
| `sbd_tarifas_transporte` | Tarifas de T | 22 510 | origen-destino × servicio × distancia |
| `sbd_tarifas_especiales` | Tarifas_AD_TD + Demora + Recorrido Vacío | 43 | unificadas por clase |
| `sbd_duracion_costo_rv` | tc Duración y Costo con Norma Precons MO | 15 236 | códigos verificados contra partidas: 15 232 exactos |
| `sbd_actividades_estimacion` | Actividades de Estimación | 671 | PK compuesta fuente (CodGActEst, ActEst) respetada: 48 grupos × actividades |
| `sbd_macros_rv` | Macros Composicion RV | 27 | agrupaciones macro |
| `sbd_obras` / `sbd_objetos_obra` / `sbd_etapas` | Obras / Objetos de Obra / Etapas | 28 / 844 / 63 | importación mínima documental (el resto de columnas queda en la base SBD, documentado) |
| `sbd_presupuesto_rv` | Presupuesto Composición RV | 16 816 | columnas esenciales de las 48 originales; **IdObjObra→Objetos de Obra.IdObjObra verificado 16 816/16 816** (la PK compuesta declarada NO es la clave de join), IdEtapa 16 816/16 816, CODIGO RV 16 816/16 816 |
| `sbd_presupuesto_recursos` | Presupuesto Composición Mat/RH/Equipo/SE | 18 816 | unificada por tipo; IdPRV verificado; reclasificación dirigida por datos cuando el código pertenece a otro nomenclador; 7 recursos huérfanos preservados y contados |

## 4. Calidad de datos detectada al importar (reglas, no errores del importador)

- `Preambulos/codigo.mdb` ≡ `7.21` byte a byte (SHA-256): referencia retirada, 0 filas propias.
- `Norma Juego Material1` ≡ `Norma Juego Material` (raíz): duplicado exacto verificado.
- 1 fila con código nulo en Nomenclador de Equipos (raíz, 7.22 y SBD): omitida y contada
  (414+1=415 filas fuente en la raíz).
- Duplicados intra-tabla en SBD: Norma de MO 13, Norma de Equipos 23, Norma de Semis 10
  (primera aparición conservada, conflicto registrado).
- SobreGrupos SBD con códigos duplicados y descripción distinta (16 códigos ×2 filas:
  primera conservada, conflicto contado).
- 7 recursos de presupuestos SBD con código ausente en nomencladores: filas preservadas.
- 1 descripción de partida difiere entre 7.21 y 7.22 (código común): diferencia real de
  datos, reportada sin sobrescribir.
- **Cero** partidas sin unidad de medida en las 4 variantes (el análisis previo que
  reportaba 43 era un artefacto del bug de textos Jet 3, corregido).
