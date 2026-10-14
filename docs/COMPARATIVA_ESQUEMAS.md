# FASE III — COMPARATIVA DE ESQUEMAS ENTRE VERSIONES DE LAS BASES PRECODI

Fecha: 2026-10-14 · Datos reproducibles: `docs/datos/fase3b_comparativa.json` · Script: `scripts/fase3b_diccionario.py`

## 1. Panorama general

| Base | Formato | Tablas usuario | Núcleo PRECODI | Extensión |
|---|---|---:|---|---|
| `7.21/codigo.mdb` | Jet 3 (Access 97) | 22 | 22 tablas | — |
| `Preambulos/codigo.mdb` | Jet 3 (Access 97) | 22 | idéntica a 7.21 (mismo SHA-256) | — |
| `7.22/codigo.mdb` | Jet 4 (Access 2000) | 23 | 22 + `Actividades de Estimación` | — |
| `codigo.mdb` raíz | Jet 4 (Access 2000) | 24 | 23 + `Norma Juego Material1` | copia de trabajo con 2 filas más en `HojaCalculo` |
| `8.15/SBD2008_815.mdb` | Jet 4 (Access 2000) | 284 | 12 tablas del núcleo (mismos nombres/esquema) | +272 tablas del módulo empresarial SBD v8.15 |

## 2. Evolución del núcleo entre versiones de codigo.mdb

Estructura de columnas **estable** en las 22 tablas comunes: ninguna columna fue añadida ni eliminada entre v7.21 (2007) y la raíz (2017). Las diferencias son:

| Cambio | v7.21 → v7.22 | v7.22 → raíz | Naturaleza |
|---|---|---|---|
| `Actividades de Estimación` (671 filas) | **+ añadida** | = | Nueva funcionalidad: estimaciones rápidas con precios y tiempos |
| `Norma Juego Material1` (2.936 filas) | — | **+ añadida** | Duplicado exacto de `Norma Juego Material` (copia de seguridad) |
| Migración de formato Jet 3 → Jet 4 | sí | — | Access 97 → Access 2000 (página 0x800→0x1000; texto UCS-2) |
| Volumen de datos | materiales 3.228→7.769 (+141%) | = | La v7.22 casi duplica el nomenclador de materiales |

Conteos clave por versión (fuente: `fase3a_resumen.md`):

| Tabla | v7.21 | v7.22 | raíz 2017 |
|---|---:|---:|---:|
| Nomenclador de RV | 15.347 | 15.351 | 15.351 |
| Materiales | 3.228 | 7.769 | 7.769 |
| Mano de Obra | 243 | 248 | 248 |
| Equipos | 411 | 415 | 415 |
| Juegos | 315 | 328 | 328 |
| Semielaborados | 138 | 353 | 353 |
| Norma de Materiales | 18.058 | 18.060 | 18.060 |
| Norma de Mano de Obra | 41.651 | 41.662 | 41.662 |
| Norma de Equipos | 12.908 | 12.909 | 12.909 |
| Normas de Juegos / Semielab. | 341 / 1.004 | 341 / 1.006 | 341 / 1.006 |

**Lectura**: el esquema PRECODI estuvo congelado entre 2007 y 2017 (solo adiciones puntuales de tablas); el crecimiento fue de datos (materiales y semielaborados), no de estructura. Para la integración con PRECOST esto significa que **un único mapeo de esquema cubre las cuatro variantes de codigo.mdb**.

## 3. Núcleo compartido con SBD2008_815.mdb

Las 12 tablas del núcleo existen con el mismo nombre y esquema en SBD2008_815: los 6 nomencladores (Materiales, MO, Equipos, Juegos, Semielaborados, RV) + jerarquía (SobreGrupos/Grupos/SubGrupos) + 5 normas (Materiales, MO, Equipos, Juegos, Semielaborados) + `Norma Juego Material`. Diferencias de volumen notables: Materiales 56.158 filas (vs 7.769) y RV 15.359 (vs 15.351) — la SBD 8.15 incorporó una lista de materiales mucho más amplia, aunque con precios de 2008/2011.

SBD añade además tablas que **extienden el núcleo** con semántica relacionada:
- `Normas RH` (9.699), `Normas RH Extendida` (57.838), `Normas Eq` — desgloses alternativos de normas por tarifa/escala salarial.
- `Normas Descriptivas` (2.361) — textos normativos.
- `tc Duración y Costo con Norma Precons MO` (15.236) y `tc Costo con Norma Precons Equipo` (6.485) — **tablas de cálculo** que asocian duraciones y costos con las normas PRECONS.
- `ColecRV` / `Colecciones` + composiciones (92.054 filas) — agrupaciones reutilizables de renglones.
- `Presupuesto Composición *` — descomposiciones ya presupuestadas por obra.

Estas tablas confirman la dirección del modelo (proyectos → presupuesto → composición → recursos) que la migración 0002 de PRECOST formaliza.

## 4. Tipos de datos Jet presentes (mapa usado por los importadores)

| Tipo Jet | Nombre | Uso en PRECODI |
|---:|---|---|
| 1 | Booleano | `Oficial` (RV) |
| 3 | Entero 16 bits | — (no observado en columnas de usuario) |
| 4 | Entero largo 32 | `IdEstab`, ids autonuméricos |
| 5 | Moneda (escala 4 dec) | **todos los precios y costos** (PMN, PMLC, PrecioU, CMMN…) |
| 6 | Real simple 32 (float32) | **todos los coeficientes de consumo** (Cant*) |
| 7 | Real doble 64 | HORAS HOMBRE/EQUIPO, indicadores |
| 8 | Fecha/Hora | `Fecha_Aprov` |
| 10 | Texto | códigos y descripciones |

Implicación para la integración: los coeficientes float32 arrastran errores de representación (p. ej. 0.009600000455975533); el esquema PRECOST los guarda como REAL (doble) sin redondear, y las verificaciones usan tolerancia 0.01.

## 5. Conclusiones para la evolución de PRECOST

1. **Un solo conector .mdb→SQLite basta** para las 4 variantes de codigo.mdb (esquema común estable 2007–2017).
2. SBD2008_815 demuestra la necesidad de las entidades proyecto/presupuesto/certificación (migración 0002) y aporta un vocabulario de datos ya probado en producción cubana.
3. La ausencia de cambios de esquema en 10 años indica un **formato de datos estable** apto como fuente de importación recurrente.
