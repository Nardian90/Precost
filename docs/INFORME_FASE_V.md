# INFORME FINAL — MISIÓN V

**Edición de recursos en el presupuesto real: S-050 + S-052 (MATRIZ_PARIDAD §M5)**

**Proyecto:** PRECOST 9.17 · **Fecha:** 14 de octubre de 2026
**Rama de trabajo:** `v-edicion-recursos-presupuesto` (creada desde `main` = e711082, que ya contiene MISIÓN I–IV vía el PR #3 fusionado)
**Tag protegido:** `v9.17-original` (intacto, verificado en cada suite y por request HTTP)
**HTML original:** `app/PRECOST-v9.17.html` — SHA-256 `50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2` (byte-idéntico antes, durante y después de toda la misión; verificado por `tests_v.py` N15, por `validar_v_navegador.sh` paso 19 y por el campo `html_original_intacto` de cada respuesta del API)

---

## 0. Contexto de recuperación (hecho material que condiciona esta misión)

El servidor local se reinició y el sistema de archivos se perdió. El trabajo de
MISIÓN I–IV sobrevivió **únicamente** porque estaba protegido en GitHub (push +
PR #3 ya fusionado). Tras el reinicio:

- Repositorio clonado de `https://github.com/Nardian90/Precost` (público).
- `bd/precodi.db` estaba **gitignored** («regenerable») pero sus fuentes —
  `AUXILIAR_PRECODI.rar` → `Codigo (PRECODI)/…/codigo.mdb`, extraídas en
  `/home/z/my-project/work/recuperacion/analisis/PRECODI` — ya no existen en
  GitHub ni en disco (verificada también su ausencia en las demás cuentas y
  repositorios, y en el historial git: nunca se commitearon).
- Se regeneró la **única base recuperable con datos reales**: `precost2025`
  (`docs/datos/fase3d_precost_db.json`, verificado en Fase III-D) → 15 912
  partidas + 4 382 recursos (3568 materiales + 143 MO + 671 equipos, todos con
  precio) + 22187 filas totales. **Las normas de composición quedan a 0**
  (documentado: PRECOST embebido no trae descomposiciones).
- En consecuencia, los pasos que requieren normas PRECODI (2007-v7.21/7.22,
  2011-sbd2008, 2017-raíz) quedan **EXPRESAMENTE PENDIENTES** hasta que el
  usuario re-cargue las fuentes; nada se declara completo sin demostración.

La misión se ejecutó igualmente al 100 % de lo demostrable, con todos los
pasos dependientes de datos marcados ⏸ y el procedimiento exacto de
restauración documentado en §10.

---

## 1. S-052/S-050 — significado exacto (auditado, no deducido)

Fuente: `docs/MATRIZ_PARIDAD_SIECONS_PRECOST.md` (104 funciones, construida en
MISIÓN IV sobre el manual extraído del instalador oficial) + **manual SIECONS
págs. 32–35** (`docs/datos/manual_siecons/manual_texto_completo.txt`):

- **S-050 (P1, págs. 32–33):** «Indicadores M/H/E por A.C. y especificación».
  Cada A.C. muestra un cuarto campo con tres cuadros: **M** (Materiales),
  **H** (Recursos Humanos), **E** (Equipos). Palomita = la actividad es
  afectada por recursos primarios de esa familia. **Quitar la palomita
  desactiva los recursos de la norma de esa familia y activa la opción
  «ESPECIFICAR RECURSOS» de esa familia; reponerla descarta lo especificado
  y vuelve a la norma** (manual pág. 35, con confirmación si hay datos que
  perder). Prueba de aceptación: «quitar palomita M y ver recursos
  especificables».
- **S-052 (P1, pág. 34, depende de S-050):** «Cargar normas por defecto y
  modificar cantidad/precio». Prueba de aceptación: «modificar coeficiente y
  recalcular importe». El propio manual aclara (pág. 32): *«las
  modificaciones realizadas al P.A.C. importado no afectarán a la Obra u
  Objeto desde el cual se importó, solo afectarán al Objeto al cual se le está
  aplicando ese P.A.C.»* — el **aislamiento** es parte de la especificación.

Cubertura de familias (decisión documentada, coherente con el motor PRECOST y
la verificación III-C, que suma juegos+semis en CMMN): **M → material + juego
+ semielaborado; H → mano_obra; E → equipo.**

## 2. Auditoría previa ejecutada (sección 1 de la misión)

1. Repositorio y línea base: clonación verificada; `main` = e711082 (PR #3
   fusionado por el usuario; MISIÓN IV completa en `b8348f5`); rama nueva
   creada desde `main`. `git status` limpio antes de empezar.
2. SHA-256 del HTML verificado contra el valor de referencia completo (also
   `upload/PRECOST-v9.17.html`, idéntico).
3. Definiciones S-050/S-052 confirmadas desde matriz + manual (§1); **no se
   usó ninguna otra función por inferencia**: S-051/S-053/S-055/S-056/S-057
   quedan como estaban (S-057 avanza parcialmente como efecto del sombreado).
4. Modelo de recursos de PRECOST auditado: `it.flags` ("MHE" — el MISMO campo
   que el selector `data-flg` de la pestaña Partidas y el motor
   `ENGINE.partidaPrecio`/`partidaDescomposicion`), `it.cantidad`
   (`data-qidx`), `it.normaPreco` (snapshot III-C), `touch()` →
   `saveBudgets()` → `p3pro.budgets`, `renderTabRecursos(b,r)` (hook del
   overlay), `state.budgets`/`currentId`, `toast`/`toastAction`.
5. Overlays y suites auditados: `tests_iv.py` T3 exige exactamente 3
   etiquetas de overlay → MISIÓN V **extiende `recursos.js`** en el propio
   archivo (sin 4º overlay, sin modelo duplicado); `tests_iiic.py` caso 15 es
   aditivo.
6. Fuentes PRECODI verificadas no disponibles (§0) y BD regenerada parcial.
   Suites de línea base ejecutadas ANTES de tocar nada (resultados en §7).

## 3. Archivos modificados/creados

| Archivo | Cambio |
|---|---|
| `app/overlay/recursos.js` | +928/−94 (722 → 1556 líneas): S-050 (barra de palomitas ligada a `it.flags`, especificación, sombreado) + S-052 (tabla efectiva editable, `it.edicionRecursos`, panel del nomenclador). 100 % aditivo; el HTML en disco no se toca. Repara además un defecto latente de III-C: acumulación de secciones en renders directos (ahora exactamente una sección). |
| `scripts/servidor_precodi.py` | +108/−0: endpoint **`/api/recursos`** (búsqueda del nomenclador por código/descripción con filtro por tipo, SOLO LECTURA, aditivo) + degradación honesta 404/400 controlados cuando la BD no tiene normas (antes: 500 por `int(None)`). Con BD completa el comportamiento es idéntico al de III-C. |
| `app/overlay/calculadora.js` | +8/−3: reparación de la **carrera latente de MISIÓN IV** (`cargarVersiones` tras cerrar la calculadora → `Cannot set properties of null (outerHTML)`, rechazo de promesa no manejado). Guardas de DOM nulo. |
| `scripts/tests_v.py` | **nuevo** (407 lín.): suite de la misión — 28 pruebas, 15 escenarios obligatorios + infraestructura. |
| `scripts/validar_v_navegador.sh` | **nuevo** (348 lín.): validación reproducible en navegador real — 21 comprobaciones + setup, con pendientes por datos. |
| `docs/MATRIZ_PARIDAD_SIECONS_PRECOST.md` | S-050/S-052 → implementado (verificado parcialmente por datos); S-057 → parcial. |
| `docs/INFORME_FASE_V.md` | este informe. |
| `docs/datos/v_validacion_01..03.png` | capturas nuevas de la validación en navegador (las `iv_validacion_*.png` se regeneran al re-ejecutar la suite IV). |

`bd/precodi.db` regenerado (gitignored; solo base precost2025) — ver §0/§10.

## 4. Funcionalidad implementada

**S-050 — Indicadores M/H/E y especificación**
- Barra de palomitas **M/H/E** en la vista de descomposición de la partida del
  presupuesto, ligada al mecanismo EXISTENTE `it.flags` (sin duplicación:
  el mismo campo que la pestaña Partidas y el motor). Accesible por teclado
  (rol checkbox, Espacio/Enter).
- Quitar una palomita: las filas de la norma de esa familia quedan
  **desactivadas** (tenues, tachadas, excluidas del total, con etiqueta
  explícita `desactivada (M)`) y se activa la especificación de esa familia.
- Reponer la palomita: **descarta lo especificado** de esa familia y vuelve a
  la norma — con confirmación explícita si hay recursos que perder (manual
  pág. 35).
- Marca visual de especificado: chip **sombreado en rojo** + «(n esp.)»
  (avance parcial de S-057).

**S-052 — Cargar normas y modificar cantidad/precio**
- Tabla de la **descomposición efectiva** (solo partidas del presupuesto):
  edición in-line de coef y precio en cada fila, con el **original de la norma
  en el tooltip** y etiqueta «editada»; reversión por fila (↺), por familia y
  global («Quitar TODAS las ediciones», con confirmación).
- **Recursos propios** por familia sin palomita: «⤓ Cargar normas» (copia las
  filas de la norma de esa familia como punto de partida editable — pendiente
  de datos para ejecutarse con filas normativas reales), «+ Añadir recurso»
  con **búsqueda del nomenclador** (`/api/recursos`: código/descripción +
  filtro por tipo + um + precio + avisos) y **entrada manual** (del
  presupuesto, nunca del catálogo).
- Caja de **Modificaciones** con transparencia total: cada cambio listado
  como «original → editado», cada propio con origen (norma/catálogo/manual) y
  fecha; ediciones huérfanas avisadas.
- Entradas inválidas rechazadas (negativo, no numérico, vacío en coef; el
  precio admite vacío = «sin precio», excluido del total con aviso explícito,
  nunca se inventa).
- Precisión: cálculo en doble precisión sin redondeo interno; presentación a
  4 decimales (verificado con coef 0.375, precio 4.5678, cantidad 2.5 —
  exactos a 4 decimales en todos los niveles).

**Reglas de datos (fidelidad heredada):** nunca se mezclan versiones en
silencio (cada número lleva su fuente); la comparación con el PU del motor
PRECOST (base 2025, flags y A.H/A.E) es informativa y **nunca se sobrescribe**;
sin norma no se inventan componentes.

## 5. Distinción de capas de datos (regla central de la misión)

| Capa | Dónde vive | La edición la toca |
|---|---|---|
| Catálogo maestro / norma PRECODI (`bd/precodi.db`) | servidor SOLO LECTURA (mode=ro, query_only) | **NUNCA** — verificado: hash de la BD idéntico antes/después (paso 19) |
| Nomenclador (recursos + precios por versión) | BD (solo lectura) vía `/api/recursos` | **NUNCA** (paso 21: respuestas idénticas) |
| Descomposición de la norma (snapshot `it.normaPreco`) | dentro del presupuesto | **NUNCA** — el snapshot permanece inmutable (contrato III-C) |
| Coeficientes/precios originales de la norma | snapshot/vista | **NUNCA** — solo se referencian (original→editado) |
| Presupuesto (partida, cantidad, `it.flags`) | `p3pro.budgets` | con el mecanismo EXISTENTE `touch()` (mismo que usa PRECOST) |
| **Capa nueva: `it.edicionRecursos`** (cambios + propios) | **solo dentro del ítem del presupuesto** | reversible por fila/familia/global; aislada por diseño de otros presupuestos (paso 13) |
| PU del motor PRECOST | catálogo embebido 2025 | **NUNCA** (comparación informativa, etiquetada) |

El aislamiento del manual pág. 32 queda demostrado: presupuesto B con el
MISMO código 012141 no hereda nada de A, y A queda intacta mientras B se
abre (paso 13).

## 6. Capturas (validación en navegador real)

- `docs/datos/v_validacion_01_especificacion.png` — especificación sombreada,
  tabla efectiva editable, modificaciones.
- `docs/datos/v_validacion_02_recuperado.png` — tras recargar y reabrir.
- `docs/datos/v_validacion_03_final.png` — estado final.

## 7. Resultados de las pruebas (por separado, exigencia expresa)

| Suite | Resultado real | Causa de los fallos |
|---|---|---|
| **`tests_v.py` (nueva)** | **28/28 OK** | — |
| **`validar_v_navegador.sh` (nueva)** | **23 ✓ · 0 ✗ · 3 ⏸ pendientes (datos)** | pasos 17/18/18b requieren normas PRECODI |
| `tests_iv.py` | 15/19 (4 datos) | t5/t7 requieren la descomposición de 012141 (9 recursos de norma); t5_404 depende de la forma del 404 con BD completa |
| `validar_iv_navegador.sh` | 13 ✓ / 5 ✗ | pasos 3/6a/6b/7a/7b requieren normas de 012141 |
| `tests_iiib.py` | 3/21 (18 datos) | FileNotFoundError de las fuentes `.mdb`; «falta la versión 2007-v7.21»; 0 ≠ 15347 partidas |
| `tests_iiic.py` | 0/21 (2 errores de clase) | el arranque exige las 5 versiones (documentado en la suite) |

**Clasificación verificada caso por caso: ningún fallo apunta a una
regresión de código.** Las verificaciones que SÍ pueden ejecutarse con la BD
parcial (endpoints previos, inyección, solo-lectura, integridad) están
incluidas en `tests_v.py` y pasan (28/28). La consigna de la misión se cumple
estrictamente: **ninguna suite se reporta como superada sin demostración**, y
las dependientes de datos quedan como pendientes expresas, no como fallos
silenciosos ni éxitos inflados.

Detalles de los escenarios exigidos (todos verificados en navegador, pasos
1–21 del script): búsqueda con filtro por tipo y avisos de um ≠ um partida
(3/3b); edición in-line con recálculo exacto a 4 decimales (7/8); rechazo de
negativo/no-numérico/vacío con restauración (9); sin precio excluido con
aviso (10); recarga y recuperación bit a bit (11/12/12b); aislamiento entre
presupuestos con el mismo código (13); presupuesto antiguo pre-Misión V
funciona (13b); ciclo M/H/E completo con descarte al reponer (14); S-080
coexistente sin tocar el presupuesto (15); 0 errores de consola (16);
protección de BD/norma/API (19/20/21).

## 8. SHA-256 del HTML original

- Antes de la misión: `50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2`
- Después de la misión: `50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2`
- **Idénticos** (verificado por `tests_v.py` N15, `validar_v_navegador.sh` 19
  y `validar_iv_navegador.sh` 15; además `git status` del HTML limpio).

## 9. Git — commit y rama

- Rama: `v-edicion-recursos-presupuesto` desde `main` (e711082).
- Diff revisado antes de cada commit (archivos implicados, sin temporales:
  los `.db` siguen gitignored; el informe del importador
  `docs/datos/iiib_importaciones.json` se restauró a su versión git — es
  registro histórico de la importación completa, no de la regeneración).
- Commits atómicos por fase (implementación / pruebas / documentación).
- Push a `origin` y PR a `main` (el token facilitado por el usuario se usa
  solo en línea de comandos/URL, nunca se persiste; sin PR-write el PR se
  crea por la vía disponible y se documenta).

## 10. Limitaciones y pasos pendientes (expresos)

1. **Fuentes PRECODI perdidas por el reinicio del servidor** (hecho material,
   §0). Para restaurar: volver a cargar `AUXILIAR_PRECODI.rar` (o la carpeta
   `Codigo (PRECODI)` extraída) en la ruta documentada
   `/home/z/my-project/work/recuperacion/analisis/PRECODI` y ejecutar
   `python3 scripts/importar_precodi.py --todas`. Después re-ejecutar
   `tests_iiib.py`, `tests_iiic.py`, `tests_iv.py`, `validar_iv_navegador.sh`
   y `validar_v_navegador.sh` (los pasos 17/18/18b se activan solos al
   detectar normas > 0). Hasta entonces: S-050/S-052 están **verificados en
   todo lo que no depende de normas** y la edición de filas normativas
   («Cargar normas» con filas reales, `cambios` sobre la norma) está
   implementada pero **pendiente de demostración** — no se declara completa.
2. La búsqueda del nomenclador hereda la limitación de SQLite NOCASE (solo
   pliega ASCII): «ñ» no se pliega (documentado en `tests_v.py`); el contrato
   de búsqueda de III-B/III-C no se toca.
3. S-051/S-053/S-055/S-056/S-057 (completo) siguen pendientes en la matriz.
4. La especificación vive en el ítem del presupuesto: no hay (por diseño
   SIECONS) edición de recursos a nivel de plantilla/obra compartida.

## 11. Siguiente prioridad de la matriz

Según §prioridades (P1 restantes tras esta misión): **S-032/S-039** (etapas y
operaciones en bloque) y **S-070/071/072** (fichas de costo), después
S-043/S-063 (informes de costo base). Con datos restaurados, cerrar antes los
⏸ de esta misión (re-ejecutar la batería completa).
