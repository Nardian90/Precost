# AUDITORÍA PREVIA — MISIÓN III-B: INTEGRACIÓN REAL DE PRECODI CON PRECOST 9.17

Fecha: 2026-10-14 · Rama: `evolucion` · Repositorio: `/home/z/my-project/precost`
Evidencia machine-readable y reproducible: `docs/datos/auditoria_iiib.json` (generada por `scripts/auditar_iiib.py`)
Precedente: `docs/INFORME_FASE_III.md` (fase III-A…F de ingeniería de datos y plan)

Esta auditoría **no da por ciertos los resultados de los informes anteriores**: recalculó
hashes, releyó las migraciones, reparseó las bases y revisó el código ejecutado. Todo lo
que sigue está verificado con datos reales en esta sesión.

---

## 1. Estado Git verificado

| Elemento | Estado real |
|---|---|
| Rama activa | `evolucion` |
| Commits | `1db420e` baseline → `67a8af3` Fases I-II → `ce43a5b` Fase III |
| Tag `v9.17-original` | existe, apunta al commit baseline `1db420e` (== `main`) |
| Árbol de trabajo | limpio antes de esta auditoría; los archivos de la auditoría son adiciones nuevas |
| Remoto | se configuró en esta sesión: push a `github.com/Nardian90/PRESUPUESTOCV` refs `precost/evolucion`, `precost/main` y tag `v9.17-original` (no destructivo: el `main` existente del repo remoto no se tocó) |

## 2. Migración `0002` — qué implementa realmente

Parseo del SQL (no del informe): crea exactamente **4 tablas** —
`proyectos`, `presupuestos`, `capitulos_presupuesto`, `partidas_presupuesto` — con FK a
`versiones_catalogo` y `partidas` (migración 0001) y snapshot de costos en
`costo_unitario_json`/`descomposicion_json`. **No hay entidades duplicadas ni que
sobrecriban** con la 0001 (16 tablas del núcleo de catálogos). Conclusión: el importador
nuevo **reutiliza 0001/0002 sin crear tablas redundantes** para el núcleo PRECODI.

## 3. Scripts existentes localizados

| Script | Papel | Reutilización en III-B |
|---|---|---|
| `fase3e_migrar.py` | ejecutor de migraciones versionadas idempotente | **Sí, tal cual** (aplica 0001/0002/0003) |
| `fase3f_importar_poc.py` | importador de MUESTRA (510 partidas) a base aislada | Parcial (ver §4) |
| `fase3f_exportar_json.py` | export JSON + PoC HTML externo | Referencia para la capa de consulta |
| `fase3f_tests.py` | 24 pruebas de la PoC | Referencia de estilo de pruebas |
| `fase3a/b/c/d_*.py` | análisis de fuentes (inventario, diccionario, modelo, conciliación) | Solo lectura de sus JSON de salida |

## 4. Importador `.mdb`→SQLite existente — verificación del código ejecutado

`fase3f_importar_poc.py` importó **solo una muestra** (510 partidas, 2.239 normas, 276
recursos) de la **raíz 2017**. La auditoría estática y empírica confirma:

**Defectos reales (por qué no sirve tal cual para las 4 variantes):**

1. **Money escalado sin dividir.** En 7.21/7.22 (Jet 3/sin Format) `access_parser`
   devuelve el entero escalado ×10 000 (`CHMN=40683` para el valor real 4.0683). El
   `f()` del PoC hace `float(v)` sin dividir: con esas bases almacenaría precios
   ×10 000 erróneos. Solo funcionó porque la raíz 2017 tiene propiedad `Format` y
   `access_parser` devuelve otra representación (ver §6).
2. **Pérdida silenciosa ≥1000 en la raíz.** Con Format, los Money llegan como string
   `'1,234.57'` (coma de miles): `float()` lanza excepción y `f()` devuelve `None` →
   el valor se pierde sin advertencia.
3. **Truncamiento a 2 decimales en la raíz.** El string formateado `'4.07'` pierde los
   decimales 3-4 del valor Jet real `4.0683` (Money internamente tiene 4 decimales).

**Componentes correctos que se reutilizan:** mapa tablas→entidades del esquema 0001,
patrón idempotente por (catálogo, versión), registro en `importaciones`, verificación
SHA-256 de originales antes/después, `norm_um()` (factor de unidad), recursión de
componentes de juegos/semielaborados.

## 5. Bases de datos originales — existencia y hashes recalculados

| Base | Tamaño | SHA-256 recalculado == inventario | Tablas usuario |
|---|---:|---|---:|
| `7.21/codigo.mdb` | 30 MB | ✓ `8b94cebf…` | 22 (Jet 3) |
| `7.22/codigo.mdb` | 42 MB | ✓ `d6719a42…` | 23 (Jet 4) |
| `codigo.mdb` raíz | 42 MB | ✓ `c4f94962…` | 24 (Jet 4) |
| `Preambulos/codigo.mdb` | 30 MB | ✓ **idéntico byte a byte a 7.21** | 22 |
| `8.15/SBD2008_815.mdb` | 106,5 MB | ✓ `3a9a50a2…` | 284 |

El HTML original `app/PRECOST-v9.17.html` permanece intacto
(SHA-256 `50d3cf28…cbaa2` verificado en esta sesión).

**Deducción obligada para el importador:** "cuatro variantes de `codigo.mdb`" son en
contenido **tres conjuntos de datos distintos + un duplicado exacto** (Preambulos).
El importador debe procesar las cuatro y **detectar el duplicado por hash** sin duplicar
registros.

## 6. Evidencia empírica de tipos (base del diseño de precisión, Fase 3)

Parseo directo en esta sesión (misma fila 011112 en ambas bases, valor real almacenado 4.0683):

| Base | `CHMN` devuelto | Tipo Python | Problema |
|---|---|---|---|
| 7.21 (Jet 3, sin Format) | `40683` | `int` | escala ×10 000 no aplicada |
| raíz 2017 (Jet 4, con Format) | `'4.07'` | `str` | pérdida de decimales 3-4; coma de miles ≥1000 |

`CantMat` (Float32): `1.2000000476837158` (float64 exacto del binario float32) — el
valor recuperado se conserva íntegro; la precisión ORIGINAL es float32 (~7 dígitos
significativos).

Además, con Format y valor cero, `access_parser` devuelve una **lista vacía** o el string
por defecto del formato (p. ej. `'0.00'`): el convertidor debe tratarlo como 0, distinto
de `None` (nulo real).

**Decisión de diseño (implementada en `scripts/precision_precodi.py`):** parchear
`access_parser.utils.parse_money_type` para devolver siempre el `Decimal` exacto
`entero/10 000` (o `/100` si el formato es porcentaje), eliminando las tres
representaciones inconsistentes; conversión dirigida por el TIPO Jet de columna
registrado en `fase3a_inventario.json`, no por el valor.

## 7. Tolerancias numéricas definidas (nada de tolerancia universal 0,01)

| Comparación | Tolerancia | Justificación |
|---|---|---|
| Round-trip Money almacenado (REAL) vs Decimal exacto | `max(1e-9, |v|·1e-13)` | float64 conserva 15-16 dígitos; 4 decimales ≤ 1e6 caben con holgura |
| Coeficientes Float32 recuperados vs almacenados | exacto (bit a bit) | float32→float64 es amplificación sin pérdida |
| Verificación de fórmulas F1/F2/F3 (Σ coef×precio vs costo almacenado) | `max(0.0001·N, Σ|coef·precio|·6e-8)` y clasificación de excedentes como deriva de precios documentada | error rel float32 6e-8 por término; fase III-C demostró deriva de precios en la fuente |
| Presentación (UI) | redondeo a 2 decimales SOLO en capa visual | la fidelidad de importación queda separada del redondeo de presentación |

## 8. Decisiones que se derivan de esta auditoría

1. **Importador nuevo** (`scripts/importar_precodi.py`): común para las 4 variantes,
   inspección de esquema antes de importar, mapa explícito tablas→entidades, orden
   nomencladores→normas, idempotencia por (catálogo, versión, hash), transacción
   reversible por versión, registro completo en `importaciones`.
2. **Detección de duplicado exacto** Preambulos≡7.21 por SHA-256: se registra la
   referencia y NO se reimportan filas (verificable: 0 filas nuevas).
3. **Tablas opcionales por variante**: `Actividades de Estimación` (7.22+), `Norma Juego
   Material1` (raíz; verificada en esta sesión como copia EXACTA de `Norma Juego
   Material`, 2936/2936 filas idénticas → se importa una y se documenta la otra).
4. **SBD2008_815**: el núcleo es el mismo esquema PRECODI (verificado: mismas 24 tablas
   + `Normas RH`/`Normas RH Extendida`/`Normas Eq` y nomencladores más amplios), pero
   las 284 tablas NO se importan indiscriminadamente: se clasifican en 4 categorías
   (integrable directo / con transformación / documental / pendiente) y solo entran las
   priorizadas con relaciones verificadas.
5. **Capa de acceso para PRECOST**: la app es un HTML autónomo que no puede abrir
   SQLite desde `file://`; se justifica e implementa una **capa de acceso local**
   (servidor localhost solo-lectura + overlay aditivo inyectado al servir, sin tocar el
   archivo original en disco). Detalle y justificación en `docs/FASE_III_INTEGRACION.md` §5.
