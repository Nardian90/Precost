# MISIÓN III-C — Descomposiciones PRECODI integradas en el editor de presupuestos de PRECOST

Fecha: 2026-10-14 · Rama: `iii-c-descomposiciones-recursos` (base `evolucion` @ `f213d27`) · Tag `v9.17-original` intacto.

## 1. Resumen ejecutivo

La pestaña **Recursos** del editor de presupuestos de PRECOST 9.17 incorpora ahora la descomposición **por partida** a partir de las normas PRECODI importadas: el usuario selecciona una partida (del presupuesto o del catálogo), consulta su norma de composición (materiales, mano de obra, equipos, juegos y semielaborados) con coeficientes, precios, unidades y procedencia, ajusta la cantidad presupuestada y obtiene consumos e importes reproducibles que **se guardan y recuperan con el presupuesto** mediante el mecanismo existente de PRECOST (localStorage `p3pro.budgets`).

Todo lo anterior se logró **sin modificar el HTML original** (SHA-256 constante `50d3cf28…5cbaa2`, verificado por el servidor en cada request y por las pruebas): la interfaz vive en un overlay aditivo (`app/overlay/recursos.js`) que amplía `renderTabRecursos` en tiempo de ejecución, igual que el catálogo de III-B.

**Resultado de las verificaciones**: 21/21 pruebas automatizadas de datos/API (los 16 escenarios de la misión + regresión III-B + solo-lectura), 21/21 regresión de la suite III-B, 23/23 comprobaciones del flujo de aceptación en navegador real (`scripts/validar_iiic_navegador.sh`), 0 errores de consola.

## 2. Qué se construyó (reutilizando lo existente, sin duplicar)

### 2.1 Capa de datos (servidor local, solo lectura, 127.0.0.1)

- **`GET /api/descomposicion/{codigo}?version_id=&precio_version_id=`** — payload de la descomposición para el editor: partida con procedencia (catálogo, versión, SHA-256 de la fuente, fecha de importación), componentes de primer nivel con tipo/código/descripción/unidad/coeficiente/precio/importe/resolución, descomposición anidada de juegos y semielaborados, subtotales por tipo (Σ coef×precio, modelo F1/F7/F8 verificado en III-B), verificación contra los costos almacenados en la fuente (solo con precios de la misma versión, tolerancia por nº de términos y magnitud), informe de compatibilidad al combinar versiones, duplicados y advertencias explícitas, y la misma partida en otras versiones.
- **`GET /api/normas_disponibles?codigos=a,b,c&version_id=`** — consulta por lotes (≤500) para marcar qué partidas del presupuesto tienen norma.
- Los endpoints de III-B (`/api/partida`, `/api/partidas`, `/api/versiones`, `/api/stats`) permanecen **intactos** (regresión verificada).

### 2.2 Interfaz (overlay aditivo `app/overlay/recursos.js`)

Amplía la pestaña Recursos anteponiendo una sección «Descomposición por partida» al contenido original (que se conserva íntegro):

- **Selección de partida**: lista de partidas del presupuesto actual (con marca ✓ si ya tiene norma vinculada) o consulta del catálogo PRECODI por código/descripción. Diferenciación explícita «EN EL PRESUPUESTO» vs «CONSULTA DE CATÁLOGO».
- **Descomposición**: tabla con Tipo · Código · Descripción · Um · Coef · Precio MN · Importe/um (+ Consumo e Importe total si la partida es del presupuesto) · Fuente. Filtros por tipo con conteos, expansión/contraer todo, detalle por fila (valor Float32 exacto, código de norma, advertencias, coeficiente compuesto de componentes de juegos/semis, cálculo del consumo), filas indentadas para los componentes de juegos/semielaborados (informativas: los subtotales usan el precio del compuesto, sin doble conteo).
- **Cantidades presupuestadas**: edición con el **mecanismo existente** (mismo patrón que los inputs `data-qidx` de la pestaña Partidas: `b.items[i].cantidad` → `touch(b)` → `renderEditor()`). Consumo = coeficiente × cantidad; los coeficientes de la norma nunca se modifican.
- **Precios y versiones** (FASE D): selector de versión de normas (por defecto PRECODI 2017-raíz, orden documentado) y de fuente de precios (misma versión, otra versión PRECODI, o PRECOST 2025). Al combinar versiones se muestra el informe de compatibilidad (resueltos/total, porcentaje, códigos sin precio —con respaldo explícito de la versión de la norma—, unidades distintas) y **no** se verifica contra los costos almacenados (no comparables). El PU del presupuesto (motor PRECOST, catálogo 2025 con A.H/A.E) se muestra junto al PU de la descomposición con su diferencia y explicación: **nunca se sobrescribe**.
- **Persistencia** (FASE F): al consultar una partida del presupuesto, su descomposición se **vincula automáticamente** como snapshot inmutable (`it.normaPreco`) dentro del ítem del presupuesto → se guarda y recupera con `p3pro.budgets` (mecanismo existente, transaccional por clave única de localStorage). «Actualizar snapshot» y «Quitar vínculo» son operaciones explícitas. Un cambio de catálogo **no** altera retrospectivamente los presupuestos históricos.
- **Degradación honesta**: sin servidor local, la sección avisa y muestra únicamente los snapshots ya vinculados; no consulta ni inventa nada.

### 2.3 Corrección del importador (hallazgo y fix en la cadena de datos)

Durante las pruebas se detectó que las **tarifas de mano de obra y costos horarios de equipo de la versión PRECOST 2025** quedaban en NULL en la BD: el importador leía el precio en `v[2]` para todos los tipos, pero el extracto del catálogo embebido tiene `M=[desc,um,precio,peso]`, `O=[desc,tarifa]`, `E=[desc,costoHorario]` (precio en `v[1]` para MO/EQ). Corregido en `scripts/importar_precodi.py` (mapeo por tipo), junto con un bug de `--purgar` (`precios_recurso` no tiene columna `version_id`: el borrado genérico fallaba en silencio y el DELETE de `recursos` chocaba con la FK). Tras purgar y reimportar PRECONS_III/2025-06-06: **4.382/4.382 recursos con precio** (antes 3.568: solo materiales).

Consecuencia verificada: normas 2017 + precios 2025 de `012141` → 9/9 recursos con precio directo, PU descomposición **123.0125 MN/m³** vs PU oficial del catálogo 2025 **123.02** (Δ 0.0075 ≈ 0.006%, deriva de precios de la misma clase que la documentada como F8 en III-B). Las normas 2017 reproducen el catálogo 2025 con precisión — el flujo permite estimar descomposiciones 2025 sobre normas PRECODI con advertencias explícitas de unidades.

> Nota: la reimportación cambia los **ids** de versión (autoincrement). Pruebas y fixtures resuelven los ids **dinámicamente por etiqueta de versión** (catalogo+versión), nunca por id numérico.

## 3. Precisión y fidelidad de los cálculos (FASE E)

- **Coeficientes**: se conservan con el valor Float32 exacto de la fuente (p. ej. `2.4000000953674316`, `0.009600000455975533`) en la BD, en el API, en el snapshot y en el cálculo. La presentación usa 7 dígitos significativos (precisión float32) con el valor exacto visible en el detalle de cada fila. Sin redondeo en importación ni en cálculos intermedios.
- **Precios**: Money de 4 decimales exacto en tránsito (p. ej. `5191.9199`); `importe = coef × precio` a precisión completa (ej. `0.013100000098347664 × 5191.9199 = 68.0141512…`, mostrado `68.0142`).
- **Redondeo separado**: el cálculo nunca redondea; la presentación usa 4 decimales (importes/consumos) y el formato propio de PRECOST (`fmt`) para los totales del presupuesto. 
- **Sin tolerancia global 0.01**: la verificación contra la fuente usa la regla documentada `|Δ| ≤ max(0.0001·N, Σ|coef·precio|·6e-8)` (por número de términos y magnitud).
- **Traza de cálculo** visible: PU descomposición = Σ(coef×precio); consumo = coef × cantidad presupuestada; importe = consumo × precio; subtotal por tipo = Σ importes; total de obra = cantidad × PU. Fuentes (norma y precios, con versión y SHA) en cabecera.
- **Regresión `012141`** (caso 16): subtotales CMMN 2.6290 / CHMN 4.6074 / CEMN 1.6516 (vs almacenados 2.629/4.6074/1.6517 con Δ ≤ tolerancia), coeficientes y precios bit a bit contra el fixture extraído del `.mdb` original (III-B), verificación 3/3.

## 4. Persistencia (FASE F) — decisión de arquitectura

PRECOST persiste presupuestos en localStorage `p3pro.budgets` (JSON, escritura atómica por clave). Ese mecanismo **es suficiente** para el flujo III-C y es el existente: el snapshot de la norma viaja dentro del ítem (`it.normaPreco`, ~2 KB por partida). No se creó una segunda implementación de entidades: las tablas `proyectos`/`presupuestos`/`partidas_presupuesto` de la migración 0002 siguen como destino documentado de la evolución (p. ej. vía sql.js/OPFS), sin duplicarlas ni activarlas a medias. Se respetan los requisitos: cantidades por mecanismo existente, normas y catálogos inalterados (BD en modo solo-lectura), procedencia conservada (versión+SHA+fecha en el snapshot), presupuestos que se cierran y abren sin pérdida (verificado tras recarga), y ninguna actualización retroactiva sin operación explícita.

## 5. Pruebas (FASE G)

- **`scripts/tests_iiic.py` — 21/21 ✓** (requiere `bd/precodi.db`): los 16 escenarios de la misión con fixtures identificables y valores esperados de origen (`datos_prueba/casos_iiic.json`, regenerable con `scripts/extraer_casos_iiic.py`): norma completa, sin norma (`999999`), materiales/mano de obra/equipos, multi-categoría con juego y semielaborado (`096231`), referencias inexistentes (copia efímera de la BD: advertencia + código y coeficiente de origen conservados; el original permanece intacto), duplicado real (`mano_obra 0000000211` ×2 en `096231`, ambas filas conservadas y advertidas) y ambigüedad entre versiones resuelta por `version_id`, coeficientes Float32 bit a bit, importes con 4 decimales (`063611` → recurso `4641011001` a `5191.9199`), cambios de cantidad (1/120/250/0.0001) sin alterar la norma, precios por versión (012141: 8.8881 en 2007/2017, 9.6902 en 2011, 123.02 en 2025; cruces con informe de compatibilidad), snapshot con round-trip JSON exacto e inmutabilidad histórica, conservación del catálogo embebido (SHA-256 del HTML + inyección de solo 2 etiquetas + 15.912 partidas y 4.382 recursos en la importación 2025), regresión 012141 contra el fixture III-B. Además: lotes de normas disponibles (con límites), regresión de endpoints III-B, API solo-lectura (POST → 501) y BD no modificada por las pruebas.
- **`python3 scripts/tests_iiib.py` — 21/21 ✓** (regresión completa de la misión anterior tras la corrección del importador y la reimportación).
- **`bash scripts/validar_iiic_navegador.sh` — 23/23 ✓**: flujo de aceptación reproducible en navegador real (crear presupuesto → partida 012141 → descomposición → verificación 3/3 → cantidad 100→333.5 con recálculo → guardado → recarga → persistencia de presupuesto/cantidad/descomposición → las 6 vistas/pestañas intactas → 0 errores de consola).

## 6. Instrucciones reproducibles

```bash
cd /path/a/precost
python3 scripts/importar_precodi.py --todas        # (regenerable) BD completa ~50 s
python3 scripts/tests_iiib.py                      # 21/21 (regresión III-B)
python3 scripts/tests_iiic.py                      # 21/21 (FASE G)
bash scripts/validar_iiic_navegador.sh             # 23/23 (FASE H, requiere agent-browser)
python3 scripts/servidor_precodi.py                # http://127.0.0.1:8765/
# → Editor → abrir/crear presupuesto → pestaña Recursos → seleccionar partida
#   (o buscar en el catálogo PRECODI) → consultar descomposición, cambiar cantidad,
#   guardar (automático) y recargar.
```

## 7. Limitaciones conocidas (honestidad documentada)

1. **Servidor local requerido** para consultar el catálogo: la sección se degrada a snapshots guardados si no hay `servidor_precodi.py` activo (aviso visible; sin datos inventados). La vía sin proceso local (sql.js/OPFS) sigue siendo evolución futura.
2. **Descomposición ≠ PU del presupuesto**: el PU del motor PRECOST usa el catálogo 2025 con flags M/H/E y ajustes A.H/A.E; la descomposición PRECODI usa la versión seleccionada. Ambos se muestran con su fuente y diferencia; no se sustituyen entre sí.
3. **Cruce de versiones**: ~20% de los recursos de normas 2017 no tienen precio 2025 a nivel global (en `012141` hoy 0/9 tras el fix); los recursos sin precio usan el precio de la versión de la norma con distintivo «respaldo», y hay 1.077 recursos compartidos con unidad distinta entre 2017 y 2025 (variantes notacionales como `sc`/`saco`, `lt`/`litro` y cambios reales): se advierten por fila y en el informe; la validación semántica caso a caso queda como trabajo pendiente.
4. **Capacidad de localStorage** (~5 MB): presupuestos con cientos de partidas vinculadas (~2 KB/partida) pueden acercarse al límite; PRECOST ya avisa «almacenamiento lleno». Para volúmenes mayores, migrar a las tablas 0002 (futuro).
5. **Juegos/semielaborados anidados**: sus componentes se muestran como información; los subtotales usan el precio del compuesto (modelo F1/F7/F8). No hay recursión más profunda (los datos de origen tampoco la tienen).
6. Pendientes heredados de III-B sin inventar: HORAS OPERARIO/AYUDANTE, PESO, patrón ×10 (259 partidas), 148 unidades con cambio 2017→2025.

## 8. Entregables de esta misión

| Entregable | Ruta |
|---|---|
| Código de la pestaña Recursos (overlay aditivo) | `app/overlay/recursos.js` |
| Endpoints de descomposición y lotes | `scripts/servidor_precodi.py` |
| Corrección del importador (precios MO/EQ 2025 + purga FK) | `scripts/importar_precodi.py` |
| Suite automatizada 16 escenarios + complementos | `scripts/tests_iiic.py` |
| Fixtures regenerables con valores de origen | `scripts/extraer_casos_iiic.py` → `datos_prueba/casos_iiic.json` |
| Validación reproducible en navegador | `scripts/validar_iiic_navegador.sh` |
| Auditoría previa (FASE A) | `docs/AUDITORIA_IIIC.md` |
| Capturas del flujo funcional | `docs/datos/iiic_validacion_01..05*.png` |
| Este informe | `docs/FASE_IIIC_INTEGRACION.md` |

El archivo `app/PRECOST-v9.17.html` permanece **byte-idéntico** (verificado en cada prueba) y el tag `v9.17-original` no se ha tocado.
