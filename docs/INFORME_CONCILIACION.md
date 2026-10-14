# FASE III — INFORME DE CONCILIACIÓN PRECODI ↔ PRECOST

Fecha: 2026-10-14 · Scripts reproducibles: `scripts/fase3d_extraer_catalogo.py`, `scripts/fase3d_conciliar.py`
Evidencia: `docs/datos/fase3d_precost_db.json` (catálogo PRECOST extraído, HTML intacto), `docs/datos/fase3d_conciliacion.json`

## 1. Fuentes conciliadas (procedencia completa)

| | PRECODI | PRECOST |
|---|---|---|
| Contenido | Nomencladores + normas de consumo | Catálogo normativo embebido |
| Nombre | codigo.mdb (raíz, junto a Codigo.exe) | PRECONS III MICONS 2025 (const `DB`) |
| Fecha base de precios | 2017 (mtime del archivo Jet 4) | publicada 06/06/25 |
| Documentos fuente | — (base de datos binaria) | LISTA-DE-MATERIALES.pdf · LISTA-DE-TARIFAS-HORARIAS-DE-MANO-DE-OBRA.pdf · LISTA-DE-COSTOS-HORARIOS-DE-USO-DE-EQUIPOS.pdf · SECCION-01..45.pdf |
| Procedencia del archivo | AUXILIAR_PRECODI.rar (Google Drive 2) | embebido en `PRECOST-v9.17.html` (SHA-256 `50d3cf28…`), extraído sin modificar |
| Estructura de partida | tabla `Nomenclador de RV` (40 columnas) | `P[código] = [descripción, unidad, total, material, mo, equipo, peso, sección]` |
| Recursos | 5 nomencladores con PMN/PMLC | `M` materiales [desc, um, precio, peso] · `O` MO [desc, precio] · `E` equipos [desc, precio] |
| Grupos | SobreGrupos(40)/Grupos(320)/SubGrupos(1.518) | `G` con claves de 2(45)/3(331)/4(1.517) dígitos |

## 2. Partidas (P ↔ Nomenclador de RV)

| Métrica | Valor |
|---|---:|
| Partidas PRECOST (códigos de 6 dígitos) | 15.912 |
| RVs PRECODI | 15.351 |
| **Coincidencia exacta de código** | **14.451** |
| Cobertura de PRECODI cubierta por PRECOST | 94,1% |
| Cobertura de PRECOST procedente de PRECODI | 90,8% |
| Solo PRECOST (nuevas o renumeradas en 2025) | 1.461 |
| Solo PRECODI (retiradas en 2025) | 900 |

**Descripciones** (tras limpieza de artefactos de extracción PDF del lado PRECOST — sufijos «L ista de Costos…» y cantidades finales sueltas; los datos originales no se alteran):

| Resultado | Valor |
|---|---:|
| Idénticas (normalizadas) | 13.462 (93,2% de las compartidas) |
| Parecidas (Jaccard ≥ 0,6) | 870 |
| Distintas | 119 |

Muestra de diferencias reales: `019901` «CARGA DE ESCOMBROS MANUAL» (2017) → «…EN OBRAS VIALES» (2025); `047122` «TECNICA DE ALPINISMO» → «TECNICA DE ACCESO CON CUERDAS» — actualizaciones normativas del reglamento 2025, no errores.

**Unidades** (comparadas solo cuando son semánticamente equivalentes):

| Resultado | Valor | Detalle |
|---|---:|---|
| Idénticas | 9.926 | |
| Equivalentes por abreviatura | 4.377 | t↔tm (2.471) · m↔ml (1.662) · 100 m↔cm (142) · 100 m²↔c2 (69) · 100 m³↔c3 (33) |
| Distintas o cambio de unidad | 148 | u↔ct (60) · m²↔d2 (28) · u↔cu (26) · u↔dc (23) · m²↔mm (6) · l↔hl (4) |

Los 148 casos restantes corresponden a partidas cuya unidad cambió en PRECONS III 2025 (de cientos/decenas/docenas a unidades simples; p. ej. `031901` COLOCACIÓN DE BLOQUE PANEL BP-1: `ct`→`u`). Quedan como **verificación semántica pendiente**: no se declaran ni equivalentes ni en conflicto.

**Precios** — bases monetarias distintas (2017 vs 2025), documentadas como cambio de base, no como conflicto:

| Estadístico del ratio total 2025/2017 (14.407 pares con precio) | Valor |
|---|---:|
| Mediana | ×11,13 |
| Percentil 10 | ×5,81 |
| Percentil 90 | ×31,24 |

## 3. Recursos

| Conjunto | PRECOST | PRECODI | Coincidencia exacta de código | Solo PRECOST | Solo PRECODI |
|---|---:|---:|---:|---:|---:|
| Materiales (M ↔ Nomenclador de Materiales) | 3.568 | 7.769 | 3.241 | 327 | 4.528 |
| Mano de obra (O ↔ Nomenclador de MO) | 143 | 248 | 125 | 18 | 123 |
| Equipos (E ↔ Nomenclador de Equipos) | 671 | 415 | 376 | 295 | 39 |

Descripciones de materiales compartidos: 3.019 idénticas · 176 parecidas · 46 distintas. Entre las distintas hay **conflictos reales de dato** (mismo código, producto diferente): `3749991002` «PERFIL UNIÓN PVC 69/45» (2025) vs «HOJA DE PUERTA DE PVC BLANCO» (2017); `3748919171` «REDUCIDO PEAD DN 160×110» vs «Reducido 110×40mm pvc presión». Otros son enriquecimientos del 2025 («CEMENTO GRIS P-350 A GRANEL (J. MERCERON, STGO. DE CUBA)»).

## 4. Jerarquía de grupos (G ↔ SobreGrupos/Grupos/SubGrupos)

| Nivel | PRECOST | PRECODI | Códigos comunes | Descripción idéntica |
|---|---:|---:|---:|---:|
| Capítulo (2 d) | 45 | 40 | 39 | 19 |
| Grupo (3 d) | 331 | 320 | 316 | 287 |
| Subgrupo (4 d) | 1.517 | 1.518 | 1.513 | 1.436 |

- PRECONS III 2025 añade capítulos 41–45 (la fuente cita SECCION-01..45) y renombra 20 capítulos (p. ej. el 39 común cambia de denominación).
- **32 códigos G sin padre** (hallazgo de calidad documentado): subgrupos como `2810` («CABLE POR TUBERÍA EXPUESTA…») con 10–41 partidas reales debajo pero sin grupo `281` en G — niveles intermedios ausentes en los PDF fuente. Se importaron con padre NULL y advertencia registrada.

## 5. Descomposiciones — el hallazgo central de la integración

| Métrica | Valor |
|---|---:|
| RVs PRECODI con norma de consumo | 15.350 |
| Códigos compartidos PRECOST∩PRECODI | 14.451 |
| Compartidos con norma disponible en PRECODI | 14.451 (100%) |
| Descomposiciones en el catálogo PRECOST | **0** |

**El catálogo embebido de PRECOST solo contiene costos agregados por partida y precios unitarios de recursos; NO contiene coeficientes de consumo.** Las normas de consumo (qué materiales, cuántas horas, qué equipos consume cada partida) existen únicamente en PRECODI. Esta asimetría es exactamente la oportunidad de integración: PRECOST evolucionado puede ofrecer la descomposición normativa que hoy no tiene, consultando el catálogo externo.

## 6. Reglas de conciliación aplicadas (reproducibles)

1. Coincidencia por **código exacto** (6 dígitos partidas / 10 dígitos recursos) — clave estable verificada en ambas fuentes (CODIGO RV único en PRECODI; claves de P/M/O/E en PRECOST).
2. Descripciones normalizadas (mayúsculas, sin acentos, espacios colapsados) + limpieza **solo para comparar** de artefactos PDF de PRECOST (sufijo «L ista de Costos…», números de cantidad finales).
3. Unidades: normalización minúsculas + extracción de factor («100 m2»→m2×100); equivalencias por abreviatura solo para los 5 pares dominantes verificados por frecuencia; el resto queda pendiente de verificación semántica.
4. Precios comparados solo con idéntico código y unidad equivalente; las diferencias se reportan como **cambio de base monetaria** (2017→2025), no como conflicto.
5. **Ningún registro original fue sobrescrito**: la conciliación es de solo lectura sobre ambas fuentes; el resultado se materializa como versiones separadas en la base de prueba.

## 7. Conclusión

Las dos fuentes son **el mismo nomenclador en dos momentos normativos** (2017 y 2025): 94% de códigos compartidos, 93% de descripciones idénticas, jerarquía equivalente con 5 capítulos nuevos en 2025. PRECOST 2025 aporta vigencia (precios oficiales 2025, 45 secciones); PRECODI 2017 aporta profundidad (descomposiciones normativas completas + precios MLC + juegos y semielaborados ausentes en 2025). La evolución de PRECOST debe **conservar ambos como versiones de un mismo catálogo con procedencia** — exactamente lo que implementa la base de prueba de la Fase III-F.
