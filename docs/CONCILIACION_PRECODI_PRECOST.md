# CONCILIACIÓN PRECODI ↔ PRECOST (MISIÓN III-B)

Fecha: 2026-10-14 · Evidencia completa y reproducible: `docs/datos/iiib_conciliacion.json`
(generada por `scripts/conciliar_iiib.py` sobre `bd/precodi.db` importada)
Precedente: `docs/INFORME_CONCILIACION.md` (fase III-D, análisis sobre ficheros).

---

## 1. Recuentos origen ↔ destino por base y tabla

**Resultado: 0 recuentos sin explicar.** Para cada tabla importada se cumple
`insertadas + explicadas_por_reglas = filas_fuente`, donde las reglas son exactamente
las documentadas (ninguna otra silently drop):

| Base (versión) | Tablas conciliadas | Insertadas | Reglas que explican diferencias |
|---|---:|---:|---|
| codigo_721 (2007-v7.21) | 18 | 99 196 | — (importación exacta al 100 %) |
| codigo_722 (2007-v7.22) | 18 | 102 327 | Equipos: 1 código nulo omitido (414+1=415) |
| codigo_raiz (2017-raiz) | 19 | 102 327 | Equipos: 1 código nulo omitido; Norma Juego Material1: duplicado exacto verificado (2 936 filas, 0 insertadas por diseño) |
| codigo_preambulos | 0 | 0 | duplicado byte a byte de 7.21 (SHA-256): referencia retirada sin filas propias |
| precost2025 (PRECONS_III) | — | 22 187 | catálogo embebido extraído sin modificar el HTML |
| sbd2008_815 (2011-sbd2008) | 40 | 389 871 | Norma MO 13 y Norma Eq 23 duplicadas omitidas; Norma Semis 10; Equipos 1 código nulo; Presupuesto Mat 7 recursos huérfanos preservados; Normas Descriptivas 1 duplicado exacto de contenido; grupos ya existentes contados |

## 2. Cruce PRECODI raíz 2017 ↔ catálogo embebido PRECOST 2025

| Métrica | Valor |
|---|---|
| Códigos de partida compartidos | **14 451** (90,1 % de los 15 351 de la raíz) |
| Solo en PRECODI 2017 | 900 |
| Solo en PRECOST 2025 | 1 461 |
| Descripciones idénticas (normalizadas) | **13 022 / 14 451** (90,1 %) |
| Unidades idénticas | 9 927 |
| Unidades distintas (equivalencias por abreviatura) | 4 524 — principales: tm↔t (2 471), ml↔m (1 662), cm↔m (142), c2↔m2 (69), ct↔u (60), c3↔m3 (33) |
| Ratio de precio total 2025/2017 | mediana **×10,81** · p10 ×5,83 · p90 ×28,95 (n=14 451) |
| Partidas con descomposición en PRECODI 2017 | **15 350** |
| …de ellas compartidas con PRECOST 2025 | **14 451 (100 % de los compartidos)** |

Nota metodológica: el ratio ×10,81 corrige el ×11,13 estimado en fase III-D — aquella
estimación usaba los precios 2017 truncados a 2 decimales por el parser original
(4.0683→'4.07'); la importación actual usa el Money exacto de 4 decimales.

**Lectura**: PRECOST 2025 aporta vigencia de precios y 1 461 partidas nuevas; PRECODI
aporta las descomposiciones de consumo que PRECOST no tiene — para el 100 % de los
códigos compartidos. La integración las combina: precio vigente 2025 + descomposición
2017 verificada.

## 3. Evolución interna de las versiones PRECODI importadas

| Transición | Agregadas | Eliminadas | Comunes |
|---|---:|---:|---:|
| 2007-v7.21 → 2007-v7.22 | +4 | 0 | 15 347 |
| 2007-v7.22 → 2017-raiz | 0 | 0 | 15 351 |
| 2017-raiz → 2011-sbd2008 | +10 | −2 | 15 349 |

El nomenclador de partidas es estable entre 2007 y 2017 (los mismos 15 351 códigos);
SBD añade 10 y carece de 2. Los conflictos de descripción/unidad entre versiones se
detectan y cuentan en cada importación (`importaciones.advertencias`) sin sobrescribir
ninguna versión (inmutabilidad).

## 4. Verificación del cálculo (casos verticales reproducibles)

- **012141** (raíz 2017, 9 componentes): CMMN 2.6290 vs 2.629000 (Δ 0.000000) ✓ ·
  CHMN 4.6074 vs 4.607424 (Δ 0.000024) ✓ · CEMN 1.6517 vs 1.651643 (Δ −0.000057) ✓ —
  tolerancia `max(0.0001·N, Σ|términos|·6e-8)`.
- Los excedentes de tolerancia en otras partidas corresponden a la deriva de precios
  documentada en fase III-C (costos almacenados calculados antes de actualizaciones de
  precios en la propia fuente): el importador no «corrige» la fuente, preserva y reporta.

## 5. Qué puede consultar PRECOST hoy (y qué no)

Puede (probado en navegador real, `docs/datos/iiib_overlay_navegador.png`): buscar por
código o descripción en cualquier versión importada; ver unidad, fuente, versión, SHA-256
y fecha de importación; ver la descomposición completa con coeficientes Float32
preservados y precios de 4 decimales; subtotales por tipo y verificación contra la
fuente; comparar la misma partida entre 2007/2011/2017/2025.

No declara (sin resultados de referencia verificables): equivalencia funcional con
SIECONS 11 — no ejecutado en este entorno (requiere Windows + Access 2013+).
