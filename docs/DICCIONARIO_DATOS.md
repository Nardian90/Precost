# FASE III — DICCIONARIO DE DATOS PRECODI

Fecha: 2026-10-14 · Rama: `evolucion` · Scripts reproducibles: `scripts/fase3a_inventario_mdb.py`, `scripts/fase3b_diccionario.py`
Datos de soporte: `docs/datos/fase3a_inventario.json`, `docs/datos/fase3b_diccionario.json`, `docs/datos/fase3b_relaciones.json`

Lectura **solo lectura** con `access-parser` (Python puro). Ningún original fue modificado (verificado por SHA-256 antes y después).

---

## 1. Bases analizadas

| # | Base | Procedencia (ruta en RAR) | Tamaño | SHA-256 (16) | Formato | Tablas usuario |
|---|---|---|---:|---|---|---:|
| 1 | `codigo.mdb` v7.21 | `Codigo (PRECODI)/7.21/codigo.mdb` | 30.242.816 B | `8b94cebfa131751e` | Jet 3 (Access 97) | 22 |
| 2 | `codigo.mdb` v7.22 | `Codigo (PRECODI)/7.22/codigo.mdb` | 42.119.168 B | `d6719a4250f94d1d` | Jet 4 (Access 2000) | 23 |
| 3 | `codigo.mdb` raíz | `Codigo (PRECODI)/codigo.mdb` | 42.119.168 B | `c4f94962c3e0cde6` | Jet 4 (Access 2000) | 24 |
| 4 | `codigo.mdb` Preamb. | `Codigo (PRECODI)/Preambulos/codigo.mdb` | 30.242.816 B | `8b94cebfa131751e` | Jet 3 (Access 97) | 22 |
| 5 | `SBD2008_815.mdb` | `Codigo (PRECODI)/8.15/SBD2008_815.mdb` | 106.500.096 B | `3a9a50a2ef8fea84` | Jet 4 (Access 2000) | 284 |

**Hallazgos de identidad:**
- Las bases 1 y 4 son **byte-idénticas** (mismo SHA-256): la copia de `Preambulos/` es un duplicado de `7.21/`.
- Las bases 2 y 3 tienen el mismo tamaño pero **distinto hash**: la raíz añade la tabla `Norma Juego Material1` (copia exacta de `Norma Juego Material`, 2.936 filas) y 2 filas más en `HojaCalculo`. La raíz es la copia **más reciente y completa** (mtime 2017) y es la usada como canónica en esta fase.
- **No todas las bases tienen el mismo esquema** (ver `COMPARATIVA_ESQUEMAS.md`): v7.21/Preambulos = 22 tablas; v7.22 = 23 (añade `Actividades de Estimación`); raíz = 24 (añade además `Norma Juego Material1`); SBD2008_815 = 284 (núcleo PRECODI + módulo empresarial completo).

La fecha de archivo de las .mdb extraídas es la fecha de extracción del RAR; la datación real proviene de contenido (nomencladores 2017 en la raíz; SBD 2008 v8.15) y de los metadatos del formato.

---

## 2. Diccionario por tabla — `codigo.mdb` raíz (base canónica)

Convención de confianza: **Alta** = PK verificada en definición de tabla + relaciones verificadas con datos (0 huérfanos) + muestras coherentes. **Media** = interpretación por nombres/valores sin verificación cruzada posible. **Baja** = sin interpretación clara.

### 2.1 Nomencladores maestros

#### `Nomenclador de Materiales` — 7.769 filas · PK: `CodMat` · Confianza: **Alta**
Finalidad: catálogo maestro de materiales con precios oficiales MN/MLC.

| Campo | Tipo | Observaciones (verificadas con datos) |
|---|---|---|
| CodMat | Texto(10) | Código de 10 dígitos; único (PK). Un valor `S/CÓD. 1` para materiales sin código |
| Material | Texto(255) | Descripción en mayúsculas |
| UmRec | Texto(15) | Unidad: u×3778, U×1298, ml×471, kg×241, tm×238, m2×204, m×186, m3×165, cu×131, lt×116… |
| CodFamilia | Texto(3) | Familia de materiales (casi siempre '0' en esta copia — sin tabla padre local) |
| PrecioU | Moneda(4 dec) | Precio unitario **total** = PMN + PMLC (F11 verificada 7.340/7.580) |
| PesoU | Moneda(4 dec) | Peso unitario (kg) |
| PMN | Moneda(4 dec) | Precio en Moneda Nacional (CUP) |
| PMLC | Moneda(4 dec) | Precio en Moneda Libremente Convertible; >0 en 2.855/7.769 |
| IdEstab | Entero largo | Establecimiento (local de la .mdb; no usable como clave externa global) |
| Suministrador | Texto(100) | 'Desconocido' por defecto |
| IdM | Entero largo, autonumérico | Id interno |

Calidad: sin duplicados de PK; 4.763 materiales con PMN==PrecioU (los MLC=0); los restantes difieren exactamente por el componente MLC.

#### `Nomenclador de Mano de Obra` — 248 filas · PK: `CodRHum` · Confianza: **Alta**

| Campo | Tipo | Observaciones |
|---|---|---|
| CodRHum | Texto(10) | Código único; ej. `0000000211` |
| RHum | Texto | Descripción del oficio/categoría salarial |
| UmRec | Texto | `hh` (243) y `h/hombre` (5) — horas hombre |
| PrecioU / PMN / PMLC | Moneda(4) | Salario por hh; PrecioU = PMN+PMLC verificado 248/248 |
| Grupo | Texto | Grupo salarial: IV×52, V×52, VI×41, VII×36, III×33, IX×18, II×9, XII/XI/X… |
| Especialidad, AO | Texto | Mayormante NULL |
| PPMN, PPMLC | Moneda(4) | 0.00 en todos (columna sin uso en esta copia) |
| HCPO_N | Moneda(4) | 1.00 constante observada |
| IdH | Entero, autonum | Id interno |

#### `Nomenclador de Equipos` — 415 filas · PK: `CodEquipo` · Confianza: **Alta**
Campos análogos + `IdTipoEquipo`, `CPO_N`/`CPE_N`/`CET_N` (costos por operador/equipo/estación, 1.00 en la muestra), `NormaHoraria` (NULL), `PPMN` (difiere de PMN en algunos). UmRec: `he`×412, `HE`×1, `HH`×1, vacío×1.
Calidad: **1 fila con componente de PK nulo** (el registro `0000000000 NO DEFINIDO` es un placeholder del sistema).

#### `Nomenclador de Juegos` — 328 filas · PK: `CodJuego` · Confianza: **Alta**
Juegos de trabajo (paquetes de materiales instalados conjuntamente). UmRec `jg`×317. `UtilJ` (utilización) = 0.00 en la muestra. PrecioU=PMN+PMLC verificado 325/325.

#### `Nomenclador de Semielaborados` — 353 filas · PK: `CodSElab` · Confianza: **Alta**
Productos semielaborados (repellos, mezclas). Unidades: m3×171, M3×87, u×35, U×19, m2×8, hl×7, ml×6, M2×4, KG×2, tn×2 (inconsistencia de mayúsculas documentada). 153/353 **sin descomposición** en `Norma Semi *` (precio directo).

### 2.2 Jerarquía de partidas (RV = renglón de variante)

| Tabla | Filas | PK | Confianza | Finalidad |
|---|---:|---|---|---|
| `Nomenclador de SobreGrupos RV` | 40 | CodSobreG | Alta | Nivel 1 (capítulos, 2 dígitos): `01` MOVIMIENTO DE TIERRA… |
| `Nomenclador de Grupos RV` | 320 | (CodSobreG, CodG) | Alta | Nivel 2 (3 dígitos) |
| `Nomenclador de SubGrupos RV` | 1.518 | (CodSobreG, CodG, CodSubG) | Alta | Nivel 3 (4 dígitos) |

#### `Nomenclador de RV` — 15.351 filas · PK compuesta: (CodSobreG, CodG, CodSubG, CODIGO RV) · Confianza: **Alta**

Es la tabla central: cada RV es una partida de presupuesto con su **precio unitario descompuesto**.

| Campo | Tipo | Significado (verificado) |
|---|---|---|
| CODIGO RV | Texto(6) | **Único por sí solo** (15.351/15.351); prefijo = sobregrupo en 15.351/15.351 |
| Desc Rv | Texto(255) | Descripción normativa |
| UNIDAD DE MEDIDA | Texto | u×7036, m2×2757, tm×2473, ml×1667, m3×385, m×361, cm×148, U×78, ct×75, c2×73… |
| FACTOR | Doble | 1.0 en 15.351/15.351 (sin uso en esta copia) |
| COSTO DE MATERIALES / MANO DE OBRA / EQUIPOS | Moneda(4) | Componentes MN (redundantes con CMMN/CHMN/CEMN: F9 verificada 14.914/14.918) |
| CMMN, CHMN, CEMN | Moneda(4) | Costo materiales/mano de obra/equipos en MN por unidad de RV |
| CMMLC | Moneda(4) | Componente materiales en MLC |
| HORAS HOMBRE / HORAS EQUIPO | Doble | Totales de consumo por unidad (F4/F5 verificadas 15.346 y 15.341/15.350) |
| HORAS OPERARIO / HORAS AYUDANTE | Doble | **Criterio de reparto NO derivable de los datos** (hipótesis probadas y rechazadas — ver modelo de precios) |
| CEMENTO, ARIDOS, ASFALTO, CARGA, PREFABRICADO | Doble | Indicadores de consumo de insumos clave |
| PESO | Doble | Peso (fórmula no verificada: Σ CantMat×PesoU falla en 6.440/6.464) |
| TIPO | Texto | Vacío en todas las filas |
| IdActividad1 | Entero, autonum | Id interno |
| Oficial | Booleano | Marca (0 en la muestra) |
| LopCS, LopSS, DescCorta | — | Columnas auxiliares sin datos |
| Res_Aprov, Fecha_Aprov | Texto/Fecha | Resolución y fecha de aprobación normativa |
| CMMN…_Propia / CHMN_Propia… | Moneda(4) | Costos con normas propias (0.00) |

### 2.3 Normas de consumo (descomposiciones)

| Tabla | Filas | PK | Confianza | Relación (todas VERIFICADAS, 0 huérfanos) |
|---|---:|---|---|---|
| `Norma de Materiales` | 18.060 | (CodigoRV, CodMat) | Alta | RV → Materiales; coef. `CantMat` |
| `Norma de Mano de Obra` | 41.662 | (CodigoRV, CodRHum, CodNorma) | Alta | RV → MO; coef. `CantRHum` |
| `Norma de Equipos` | 12.909 | (CodigoRV, CodEquipo, CodNorma) | Alta | RV → Equipos; coef. `CantEquipo` |
| `Norma de Juegos` | 341 | (CodigoRV, CodJuego) | Alta | RV → Juegos; coef. `CantJuego` |
| `Norma de Semielaborados` | 1.006 | (CodigoRV, CodSElab) | Alta | RV → Semis; coef. `CantSElab` |
| `Norma Juego Material` | 2.936 | (CodJuego, CodMat) | Alta | Juego → Materiales; coef. `CantMatJ` |
| `Norma Semi Material` | 681 | (CodSemi, CodMat) | Alta | Semi → Materiales; `CantMatSE` |
| `Norma Semi RHumanos` | 149 | (CodSemi, CodNorma, CodRHum) | Alta | Semi → MO; `CantRHumSE` |
| `Norma Semi Equipos` | 120 | (CodSemi, CodNorma, CodEquipo) | Alta | Semi → Equipos; `CantEquipoSE` |
| `Norma Propia de Equipos` / `…Mano de Obra` | 0 | — | — | Vacías (reservadas a normas del usuario) |

Campo `CodNorma`: distingue variantes de norma del mismo recurso en la misma RV ('S/C' = simple en 11.071/41.662 filas de MO; los demás valores son códigos de 10 dígitos). Los coeficientes son `Real simple (float32)` — origen de pequeñas desviaciones por redondeo.
`NormaUsos` (Moneda): contador de usos mantenido por la aplicación (1.00 mayoritario; 10.000 observado en equipos).

### 2.4 Otras tablas

| Tabla | Filas | PK | Confianza | Finalidad / observaciones |
|---|---:|---|---|---|
| `AGIT_Indicadores Hijos` | 122 | IE1 | Media | Indicadores económicos AGIT por grupos de salario. Sin tabla padre en esta base (huérfana estructural por diseño) |
| `Actividades de Estimación` | 671 | (CodGActEst, ActEst) | Media | Actividades con precio y tiempos (TPesimista/TEsperado/TOptimista) para estimaciones rápidas |
| `HojaCalculo` | 4 | — | **Baja** | Borrador de trabajo de Codigo.exe (mezcla de columnas de recursos); no es nomenclador; contenido residual de uso interactivo |
| `Norma Juego Material1` | 2.936 | (CodJuego, CodMat) | Media | **Duplicado exacto de `Norma Juego Material`** (misma PK y conteo); probable copia de seguridad creada por el usuario |

---

## 3. Diccionario resumido — `SBD2008_815.mdb` (284 tablas)

Contiene el **mismo núcleo PRECODI** (12 tablas compartidas con `codigo.mdb`, verificados por nombre/esquema) con más datos (Materiales 56.158 filas vs 7.769; RV 15.359 vs 15.351) **más un módulo empresarial**. Inventario completo en `docs/datos/fase3a_inventario.json`. Agrupación funcional verificada:

| Módulo | Tablas (n) | Ejemplos con datos | Estado |
|---|---:|---|---|
| Núcleo PRECODI (nomencladores+normas) | 12 | Nomenclador de Materiales 56.158 · RV 15.359 · Norma MO 41.712 | Con datos |
| Presupuestos de obra | 17 | Presupuesto Composición RV 16.816 · Mat 15.893 · RH 2.718 | Con datos (plantilla) |
| Certificaciones | 23 | Certif_Cab 664 · Certificaciones M 8.463 · RV 7.779 | Con datos de ejemplo |
| AGIT (análisis económico) | 13 | AGIT_Indicadores Hijos 244 | Con datos |
| Transporte | ~12 | Tarifas de T 22.510 · Paquete de Transporte 1.946 | Con datos |
| Contratos/bancos/pagos | ~15 | Contratos, Bancos 3, Cheques… | Mayormente vacías |
| Programación (mensual/trimestral) | ~25 | Prog* — vacías | Vacías |
| Organización (obras, empresas, UEB) | ~20 | UEB_Constructoras 562 · Empresas… | Con datos |
| Compras/inventario | ~20 | Entrada de Materiales, Facturas… | Vacías o mínimas |
| Utilidades/depuración | ~10 | `ddddd` 325 · `SQLXLS` · `Errores de pegado` | Tablas de trabajo del desarrollador |

**Interpretación** (confianza Media): SBD2008_815.mdb es una **base de trabajo del sistema SBD v8.15 (2008)** que incorpora el nomenclador PRECODI como núcleo de datos más el ciclo económico completo (presupuesto→certificación→pago). 112/284 tablas están vacías: es una base plantilla con datos semilla. No se usó como fuente canónica de esta fase (su lista de precios es de 2008/2011, anterior a la de codigo.mdb raíz 2017), pero su esquema documenta hacia dónde evoluciona el modelo de datos (proyectos, certificaciones) — insumo directo para el diseño de la FASE III-E.

**Tablas no interpretadas** (confianza Baja, documentadas sin especular): `CONSTVAR` (1 fila, 12 columnas de constantes), `Candado` (2 filas, 18 columnas — posiblemente bloqueo/control de la aplicación), `VerBD`, `Todos`, `ddddd`, `Errores de pegado`. Los nombres y contenidos no permiten inferir finalidad normativa.

---

## 4. Relaciones verificadas (23/23 sin huérfanos)

Verificación por cruce real de datos (`fase3b_relaciones.json`): para cada FK declarada se calcularon los valores presentes en la tabla hija que no existen en la padre.

```
Nomenclador de RV ─┬─ CodSobreG → SobreGrupos RV          (40/40 cubiertos)   VERIFICADA
                   ├─ (CodSobreG,CodG) → Grupos RV        (320 grupos usados) VERIFICADA
                   └─ (CodSobreG,CodG,CodSubG) → SubGrupos                  VERIFICADA
Norma de Materiales ── CodigoRV → RV · CodMat → Materiales                   VERIFICADA
Norma de Mano de Obra ─ CodigoRV → RV · CodRHum → MO                         VERIFICADA
Norma de Equipos ───── CodigoRV → RV · CodEquipo → Equipos                   VERIFICADA
Norma de Juegos ────── CodigoRV → RV · CodJuego → Juegos                     VERIFICADA
Norma de Semielab. ─── CodigoRV → RV · CodSElab → Semielaborados             VERIFICADA
Norma Juego Material ─ CodJuego → Juegos · CodMat → Materiales               VERIFICADA
Norma Semi Material ── CodSemi → Semielab. · CodMat → Materiales             VERIFICADA
Norma Semi Equipos ─── CodSemi → Semielab. · CodEquipo → Equipos             VERIFICADA
Norma Semi RHumanos ── CodSemi → Semielab. · CodRHum → MO                    VERIFICADA
```

Jerarquía de grupos también verificada (SobreGrupos ← Grupos ← SubGrupos, 0 huérfanos).

**Relaciones NO existentes** (verificado por análisis): no hay tabla de proveedores/familias como entidad (solo columnas texto); `AGIT_Indicadores Hijos` no tiene padre local; `CodFamilia` de materiales no resuelve a ninguna tabla de esta base.

---

## 5. Problemas de calidad detectados (resumen)

| Hallazgo | Evidencia | Impacto |
|---|---|---|
| 259 partidas con CHMN = 10×Σ(CantRHum×PMN) | ratios 9,6–10,2 (147+48+37+13+10+3+1); concentradas en excavación (SG 01) | Inconsistencia de escala de coeficientes en la fuente; documentada, no corregida |
| Deriva de precios en costos almacenados | F1: 718/14.602 RVs con CMMN desactualizado vs precios vigentes del nomenclador | Los costos unitarios almacenados son «fotografías» de un recálculo anterior |
| 1 PK nula en Equipos | fila `NO DEFINIDO` | Fila placeholder del sistema |
| 153/353 semielaborados sin descomposición | Norma Semi * sin filas para ellos | Precio directo, sin trazabilidad de componentes |
| Mayúsculas/minúsculas inconsistentes en unidades | m3×171 vs M3×87; u vs U | Normalización necesaria al integrar |
| `Norma Juego Material1` duplicada | idéntica a `Norma Juego Material` | Copia de seguridad dentro de la base |
| Tablas de sistema ilegibles | MSysObjects con chunks corruptos (esperable en Jet) | Sin impacto en datos de usuario |

---

## 6. Limitaciones del análisis estático

1. **Consultas/relaciones/vistas guardadas de Access**: si existieran, no son extraíbles con access-parser (solo se leen tablas). Ninguna relación declarada a nivel de motor fue necesaria: las 23 relaciones se verificaron con datos.
2. **Lógica de negocio de Codigo.exe**: el ejecutable Delphi no fue analizado dinámicamente (requiere Windows); el comportamiento exacto de recálculo se infirió de los datos almacenados, no de la ejecución.
3. **HORAS OPERARIO/AYUDANTE y PESO**: fórmulas no demostrables con los datos disponibles (hipótesis probadas y rechazadas — ver `MODELO_PRECIOS_UNITARIOS.md` §5). No se inventaron reglas.
4. **MSysObjects**: metadatos de sistema parcialmente ilegibles (errores de chunk); no afecta a las tablas de usuario.
5. **SBD2008_815**: 284 tablas inventariadas; el diccionario detallado se documenta para el núcleo PRECODI y por módulos funcionales; tablas de módulos empresariales se documentan a nivel inventario (nombre, PK, filas, columnas) sin interpretación de negocio completa.
