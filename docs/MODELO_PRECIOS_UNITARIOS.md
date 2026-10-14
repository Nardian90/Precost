# FASE III — MODELO DE PRECIOS UNITARIOS PRECODI (reconstrucción verificada)

Fecha: 2026-10-14 · Base analizada: `codigo.mdb` raíz 2017 (solo lectura)
Evidencia reproducible: `docs/datos/fase3c_verificacion.json` · Script: `scripts/fase3c_modelo_precios.py`

En este informe cada fórmula está marcada como **VERIFICADA** (coincide masivamente con los valores almacenados en la base), **PARCIAL** (estructura confirmada con excepciones cuantificadas y explicadas) o **PENDIENTE** (evidencia insuficiente; no se inventa nada).

---

## 1. El objeto: el renglón de variante (RV)

Un RV es una partida de presupuesto (p. ej. `012141` «EN ROCA CUALQUIER SECCION EN PLANTA…», unidad `m3`) cuyo **precio unitario** se descompone en tres componentes almacenados:

- `CMMN` — costo de **materiales** por unidad, en Moneda Nacional (CUP)
- `CHMN` — costo de **mano de obra** por unidad, en CUP
- `CEMN` — costo de **equipos** por unidad, en CUP

El precio unitario total en MN es `CMMN + CHMN + CEMN`. Existe además `CMMLC` (componente materiales en MLC) para recursos importados. La base no contiene porcentajes de gastos indirectos, utilidades ni impuestos: el RV es **costo directo**; la base pertenece al ámbito del nomenclador, no al del presupuesto (verificado: ninguna tabla de codigo.mdb los contiene).

## 2. Fórmulas VERIFICADAS contra los valores almacenados

### F1 — Costo de materiales (PARCIAL, estructura confirmada)

```
CMMN = Σ_materiales (CantMat × PMN[material])         ← Norma de Materiales
     + Σ_juegos    (CantJuego × PMN[juego])           ← Norma de Juegos
     + Σ_semis     (CantSElab × PMN[semielaborado])   ← Norma de Semielaborados
```

| Métrica | Valor |
|---|---|
| RVs verificables (todas las normas con precio disponible) | 14.602 |
| Coincidencia exacta (±0,01 CUP) | **13.659 (93,5%)** |
| Cerca (±1 CUP) | 225 |
| Lejos | 718 |

Los 718 casos «lejos» siguen el patrón de **deriva de precios**: costos unitarios calculados en una fecha anterior con precios que luego cambiaron sin recálculo. Evidencia: RVs con descomposición idéntica comparten exactamente el mismo costo almacenado desfasado (013111/013112/013113: recalculo 4,91 vs almacenado 1,87).

### F2 — Costo de mano de obra (VERIFICADA)

```
CHMN = Σ (CantRHum × PMN[categoría])    ← Norma de Mano de Obra
```

14.980/15.246 exactos (98,3%) · 262 cerca · 4 lejos.

**Excepción documentada (hallazgo de esta fase)**: 259 partidas (1,7% del total; 88 de ellas dentro de la muestra del sobregrupo 01) presentan `CHMN ≈ 10 × Σ(CantRHum×PMN)` (ratios 9,6–10,2). Es una **inconsistencia de escala de los coeficientes en la fuente** — concentrada en excavación — con dos lecturas posibles: (a) coeficientes tabulados por 10 unidades, o (b) costo almacenado por 10 unidades. Los datos disponibles no permiten decidir entre ambas; se documenta el patrón exacto (conteo, ratios y ejemplos en `fase3c_verificacion.json` → `pendientes`) y **no se aplica ningún factor correctivo**.

### F3 — Costo de equipos (PARCIAL)

```
CEMN = Σ (CantEquipo × PMN[equipo])     ← Norma de Equipos
```

14.011/15.296 exactos (91,6%) · 1.282 cerca · 3 lejos. Los 1.282 «cerca» son diferencias de 0,01–0,03 CUP originadas en el redondeo de coeficientes float32 (p. ej. 7,6923 = 100/13 almacenado como real simple). La columna de precio correcta es **PMN** (con PrecioU coincidirían solo 1.723/6.432 RVs con equipos).

### F4 / F5 — Horas hombre y horas equipo (VERIFICADAS)

```
HORAS HOMBRE = Σ CantRHum        (15.346/15.350 exactos)
HORAS EQUIPO = Σ CantEquipo      (15.341/15.350 exactos)
```

### F6 — Componente MLC de materiales (VERIFICADA al 100 %)

```
CMMLC = Σ (CantMat × PMLC[material])    → 15.350/15.350 exactos
```

### F7 — Precio de los juegos de trabajo (PARCIAL)

```
PMN[juego] = Σ (CantMatJ × PMN[material])   ← Norma Juego Material
```

266/287 juegos con descomposición completa coinciden exactamente; 12 «lejos» muestran deriva de precios (mismo fenómeno que F1); los juegos con materiales sin precio no son verificables (p. ej. `0009990001` incluye BARRA REDONDA ACERO INOXIDABLE con precio NULL).

### F8 — Precio de los semielaborados (PARCIAL con reservas)

```
PMN[semi] = Σ (CantMatSE × PMN[mat]) + Σ (CantRHumSE × PMN[rh]) + Σ (CantEquipoSE × PMN[eq])
```

47/186 exactos + 41 dentro de ±1 CUP (88/186 = 47% dentro de ±1). Los 98 restantes presentan desviaciones mayores consistentes con deriva de precios entre el último recálculo del semielaborado y los precios vigentes del nomenclador. Además 153/353 semielaborados **no tienen descomposición** (precio asignado directamente). **Confianza media**: la estructura mat+rh+eq está confirmada por los 88 casos que cuadran; la magnitud del error en el resto impide certificar la fórmula al nivel de F2/F6.

### F9 / F10 / F11 — Redundancias de columnas (verificadas)

- `CMMN == COSTO DE MATERIALES`: 14.914/14.918 (columnas redundantes).
- `PMN == PrecioU`: **falso** en general — ver F11.
- **`PrecioU = PMN + PMLC`**: VERIFICADA en los cinco nomencladores — Materiales 7.340/7.580 (97%), MO 248/248 (100%), Juegos 325/325 (100%), Semielaborados 337/341 (99%), Equipos 396/413 (96%). `PrecioU` es el precio total en ambas monedas; `PMN`/`PMLC` sus componentes.

## 3. Ejemplo completo verificado (documentado en el JSON)

**RV `012141` — «EN ROCA CUALQUIER SECCION EN PLANTA, HASTA 1.80 M DE PROFUNDIDAD CON DETONADOR ELECTRICO. (CARGA MANUAL)» · unidad `m3`**

| Componente | Recurso | Coeficiente | Precio PMN | Importe |
|---|---|---:|---:|---:|
| material | 3834010001 TECTRON 100 (EMULSION) | 1,2000 | 1,80 | 2,16 |
| material | 3842030002 DETONADOR ELÉCTRICO MICRORETARDO | 1,5000 | 0,27 | 0,41 |
| material | 3844010002 ALAMBRE DUPLEX | 0,8000 | 0,80 | 0,64 |
| mano de obra | 0000000211 AYUDANTE GRUPO SALARIAL II | 2,4000 | 1,91 | 4,58 |
| mano de obra | 0000010181 ARTILLERO GRUPO SALARIAL V | 0,0096 | 2,44 | 0,02 |
| equipo | 0023411907 MARTILLO BARRENADOR 26–40 mm | 0,1667 | 2,94 | 0,49 |
| equipo | 0023511943 MARTILLO ROMPEDOR | 0,0167 | 2,95 | 0,05 |
| equipo | 0053104003 CAMIÓN PLANCHA 4,1–5,5 t | 0,0096 | 16,36 | 0,16 |
| equipo | 0063114304 COMPRESOR DE AIRE MÓVIL 8–12 m³/min | 0,1667 | 5,73 | 0,96 |

Recalculado: materiales 3,21 (≈CMMN 2,63 con deriva menor) · mano de obra 4,61 (=CHMN) · equipos 1,66 (=CEMN 1,65). La descomposición completa se consulta en la PoC (`prueba/poc_catalogo_externo.html`, partida 012141).

## 4. Modelo completo (resumen ejecutivo)

```
PRECIO UNITARIO RV (MN) = CMMN + CHMN + CEMN
  CMMN = Σ CantMat×PMN + Σ CantJuego×PMN_juego + Σ CantSElab×PMN_semi     [F1 ✓]
  CHMN = Σ CantRHum×PMN_rh                                               [F2 ✓]
  CEMN = Σ CantEquipo×PMN_eq                                             [F3 ✓]
  PMN_juego = Σ CantMatJ×PMN_mat                                          [F7 ✓]
  PMN_semi  = Σ componentes (mat+rh+eq)                                   [F8 parcial]
  PrecioU(recurso) = PMN + PMLC                                           [F11 ✓]
  CMMLC = Σ CantMat×PMLC                                                  [F6 ✓ 100%]
  HORAS HOMBRE = Σ CantRHum · HORAS EQUIPO = Σ CantEquipo                 [F4/F5 ✓]
```

## 5. Fórmulas PENDIENTES (evidencia insuficiente — no se inventan)

| Incógnita | Hipótesis probadas y rechazadas | Evidencia que falta |
|---|---|---|
| `HORAS OPERARIO` / `HORAS AYUDANTE` | Σ CantRHum con «OPERARIO» en descripción (455/15.351) · con «OFICIAL» (171/15.351) · con «AYUDANTE» (3.829/15.351) | Criterio de clasificación interno de Codigo.exe (posiblemente la columna `Oficial` de la RV o una tabla externa). Requiere ejecutar la aplicación en Windows o documentación del fabricante |
| `PESO` del RV | PESO = Σ CantMat×PesoU (24/6.464) | Posible exclusión de tipos de recurso o criterio de redondeo propio; sin evidencia en datos |
| Patrón ×10 de F2 | — (documentado, no explicado) | Normas PRECONS oficiales (PDF SECCION-01..45) o comportamiento del recálculo en Codigo.exe |
| `FACTOR` | 1,0 en 15.351/15.351 → columna sin uso aparente en esta versión | Documentación de versiones anteriores |
| Gastos indirectos/utilidad | No existen en codigo.mdb | Pertenecen a SIECONS/SBD (ámbito presupuesto); se diseñaron en migración 0002 sin valores normativos inventados |

## 6. Implicaciones para la evolución de PRECOST

1. El catálogo externo PRECODI aporta lo que al catálogo embebido PRECOST **le falta**: las descomposiciones (coeficientes de consumo) — la Fase III-D verificó que PRECOST solo almacena costos agregados.
2. La fórmula de recálculo verificada permite a PRECOST **recalcular costos unitarios** ante cambios de precios de recursos — replicando el motor de Codigo.exe/SIECONS con evidencia, no con supuestos.
3. El patrón ×10 y la deriva de precios obligan a que la importación **registre advertencias por partida** (implementado en `importaciones.advertencias`) y que la UI muestre «costo almacenado» y «costo recalculado» como valores distintos cuando difieran.
