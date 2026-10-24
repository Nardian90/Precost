# PRECOST — Presupuestación y precios unitarios de construcción

**Versión original:** v9.17 · **Estado actual:** versión de desarrollo (núcleo original plenamente operativo; integraciones PRECODI con limitaciones de datos documentadas más abajo) · **SHA-256 del original protegido:** `50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2`

| Recurso | Enlace |
|---|---|
| Demo web estática (GitHub Pages) | <https://nardian90.github.io/Precost/> |
| Repositorio | <https://github.com/Nardian90/Precost> |
| Matriz de paridad SIECONS 11 → PRECOST | [`docs/MATRIZ_PARIDAD_SIECONS_PRECOST.md`](docs/MATRIZ_PARIDAD_SIECONS_PRECOST.md) |
| Informes por misión | [`docs/`](docs/) · [Fase IV](docs/INFORME_FASE_IV.md) · [Fase V](docs/INFORME_FASE_V.md) · [Fase VI](docs/INFORME_FASE_VI.md) |
| Punto de restauración del original | tag [`v9.17-original`](https://github.com/Nardian90/Precost/tree/v9.17-original) |

---

## A. Presentación

**PRECOST** es una aplicación de presupuestación de obra y cálculo de precios unitarios para el sector de la construcción. El producto original v9.17 es un único archivo HTML autónomo (`app/PRECOST-v9.17.html`, 7,2 MB) que funciona completamente **sin instalación, sin dependencias y sin conexión**: todo el motor de cálculo, los estilos y un catálogo normativo embebido de **22.187 registros** viajan dentro del propio archivo. Los presupuestos del usuario se guardan en el `localStorage` del navegador (prefijo `p3pro.`).

Este repositorio preserva ese original **byte a byte** (verificado por SHA-256 en cada build y en las suites de pruebas) y lo extiende mediante **overlays aditivos** que incorporan los catálogos PRECODI, la descomposición de partidas en recursos y una calculadora de costos de actividad, además de un servidor local de solo lectura para consultar las bases PRECODI.

**Objetivo del proyecto:** alcanzar la compatibilidad funcional con **PRECODI** (bases de precios de la construcción) y con **SIECONS 11** (software de referencia), siguiendo una [matriz de paridad](docs/MATRIZ_PARIDAD_SIECONS_PRECOST.md) de 57+ requisitos con evidencia por ítem. **No se afirma equivalencia total**: la matriz distingue `existente`, `parcial`, `ausente` y `pendiente` con las brechas documentadas.

**Estado honesto del proyecto:** el núcleo original y las funciones cliente de las Misiones III–V están operativos y probados (28/28 pruebas de Misión V, 23 verificaciones de navegador sin fallos). Las funciones que dependen de las bases PRECODI históricas (normas de composición 2007/2011/2017) están **pendientes de re-importación de datos**: tras una pérdida del entorno de desarrollo solo quedó regenerada la base PRECOST 2025. Ver §G y [INFORME_FASE_V.md](docs/INFORME_FASE_V.md).

## B. Funcionalidades

### Operativas (núcleo original v9.17, sin servidor)

- Gestión completa de presupuestos: crear, duplicar, editar, autoguardado en `localStorage`.
- Editor con 6 pestañas: Datos, Partidas, Recursos, Costos, Resumen, Exportar; 13 vistas de aplicación.
- Catálogo normativo embebido: **15.912 partidas**, 1.893 grupos, 3.568 materiales, 671 equipos, 143 manos de obra.
- Cálculo de precios unitarios con descomposición por capítulos/subcapítulos.
- Exportaciones: **Excel (XLSX)**, **PDF**, **Word (resumen ejecutivo, OOXML)** y **JSON**.
- Importación de presupuestos **JSON con validación** (`importJSONValidated`).
- **S-005 — Respaldo y restauración completa** (botón «Respaldo» abajo-izquierda o Alt+B): exporta TODOS los datos del usuario (presupuestos, plantillas, casos importados, historial, configuración y tema) a un archivo JSON portable, y lo restaura con validación estricta y confirmación. Funciona igual en la web estática y en local.
- Funciona 100 % offline abriendo el archivo directamente en el navegador.

### Operativas con servidor local (`scripts/servidor_precodi.py`) — y en la web con datos embebidos (MISIÓN VIII)

- Consulta del catálogo PRECODI importado por código o descripción (`precodi.js`, overlay del botón flotante).
- Descomposición de partidas en recursos en la pestaña Recursos, con **selección de versión** del catálogo y **snapshot persistente** por partida del presupuesto (`recursos.js`).
- Trazabilidad de fuentes: cada respuesta de la API etiqueta catálogo y versión usados; precios de recursos consultables en versión distinta a la de las normas.
- **S-050** — indicadores **M / H / E** por partida (materiales, mano de obra, equipos) con especificación manual de recursos propios; reponer la palomita descarta lo especificado y vuelve a la norma.
- **S-052** — edición persistente de **coeficiente y precio** de cada recurso **solo dentro del presupuesto**, con reversión al original; nunca altera el catálogo maestro ni otros presupuestos.
- **S-080** — calculadora de costos de actividad (Alt+C) con modo embebido sin servidor.
- Nomenclador de recursos con búsqueda por código/descripción y filtro por tipo (`/api/recursos`, Misión V).

### Operativas con los datos completos (MISIÓN VIII: bases PRECODI re-importadas)

- Las **6 versiones** están en la BD local (PRECONS_III 2025 + PRECODI 2007-v7.21, 2007-v7.22, 2017-raíz, 2007-v7.21-Preambulos≡7.21 y 2011-sbd2008): 84.681 recursos y ~74.000 normas de composición por versión PRECODI (regenerables con `scripts/importar_precodi.py --todas` + `--base sbd --priorizadas` desde las fuentes `.mdb` del propietario).
- La **web pública** incluye los datos embebidos de las 5 versiones con filas propias (`dist/data`, 59 MB): catálogo, normas, nomenclador y comparación entre versiones funcionan sin servidor (paridad probada: `tests_viii` 11/11).

### Experimentales

- Copiloto IA del original: requiere que el usuario configure endpoint y clave propios; sin configurar, la aplicación es 100 % offline. No se incluye ninguna clave en este repositorio.

### Pendientes (desarrollo)

- Las listadas como `pendiente` en la [matriz de paridad](docs/MATRIZ_PARIDAD_SIECONS_PRECOST.md) (p. ej. S-004 control de usuarios multiusuario, S-012 colecciones, S-032 etapas, S-070 fichas de costo).

## C. Requisitos

| Componente | Requisito verificado |
|---|---|
| Núcleo PRECOST (sin servidor) | Navegador moderno con `localStorage` (probado en Chromium). Basta abrir `app/PRECOST-v9.17.html`. |
| Capa PRECODI (servidor local) | **Python 3.8+** (probado con 3.12). **Sin dependencias externas**: solo biblioteca estándar (`http.server`, `sqlite3`, `json`, …). |
| Base de datos | `bd/precodi.db` (no se publica; ver §I). Regenerable: ver §D paso 4. |
| Sistema operativo probado | Linux (desarrollo y pruebas). El servidor usa solo stdlib multiplataforma; el núcleo es solo navegador. |
| Puerto del servidor | `127.0.0.1:8765` por defecto (configurable con `--puerto`). Solo escucha en local. |
| Pruebas de navegador | `agent-browser` + `node` (solo para desarrollo). |

## D. Instalación y ejecución local

```bash
# 1. Clonar
git clone https://github.com/Nardian90/Precost.git
cd Precost

# 2. Núcleo SIN servidor (no requiere nada más):
#    abrir app/PRECOST-v9.17.html con doble clic en el navegador.
#    (En Linux también: xdg-open app/PRECOST-v9.17.html)

# 3. Capa PRECODI CON servidor local:
#    3a. Regenerar la base de datos (una sola vez) desde el extracto
#        JSON versionado (15.912 partidas + 4.382 recursos, PRECOST 2025):
python3 scripts/importar_precodi.py --base precost2025

#    3b. Iniciar el servidor de solo lectura (127.0.0.1:8765):
python3 scripts/servidor_precodi.py

#    3c. Abrir en el navegador:
#        http://127.0.0.1:8765/
```

Comprobación rápida de la API (opcional):

```bash
curl http://127.0.0.1:8765/api/versiones    # versiones importadas
curl "http://127.0.0.1:8765/api/recursos?q=cemento&limit=5"
```

Ejecutar las pruebas (ver tabla real de resultados en §G):

```bash
python3 scripts/tests_v.py          # Misión V (no requiere servidor aparte)
python3 scripts/tests_iv.py         # Misión IV (requiere bd/precodi.db)
bash   scripts/validar_v_navegador.sh   # validación E2E en navegador real
```

> Las bases PRECODI históricas (2007/2011/2017) solo pueden importarse desde sus fuentes `.mdb` originales (`AUXILIAR_PRECODI.rar`), que **no se publican** en este repositorio. El comando, cuando el propietario disponga las fuentes en `activos/`, es `python3 scripts/importar_precodi.py --todas`.

## E. Arquitectura

```
app/PRECOST-v9.17.html     ← ORIGINAL PROTEGIDO (7,2 MB, autónomo, no se modifica nunca;
                             verificado por SHA-256 en cada build y suite)
app/overlay/precodi.js     ← overlay III-B: botón flotante de búsqueda del catálogo PRECODI (API)
app/overlay/recursos.js    ← overlay III-C + Misión V: pestaña Recursos (descomposiciones,
                             snapshots, S-050 M/H/E, S-052 edición por presupuesto)
app/overlay/calculadora.js ← overlay IV: calculadora S-080 (Alt+C, modo embebido sin servidor)
app/overlay/respaldo.js    ← overlay VII: respaldo/restauración completa S-005 (Alt+B,
                             100 % cliente — funciona igual en Pages y en local)
scripts/servidor_precodi.py← servidor local 127.0.0.1:8765, SOLO LECTURA: sirve el HTML
                             original inyectando las 4 etiquetas <script> EN MEMORIA
                             (el archivo en disco nunca cambia) + API /api/*
bd/precodi.db              ← SQLite (gitignore). Solo el importador escribe; el servidor
                             abre en modo=ro. Regenerable (§D).
scripts/importar_precodi.py← importador .mdb/.json → SQLite (versiones PRECODI + PRECOST 2025)
scripts/tests_*.py         ← suites automatizadas por misión (III-B/III-C/IV/V)
scripts/validar_*_navegador.sh ← validación E2E en navegador real (agent-browser)
scripts/construir_web.py   ← MISIÓN VI: genera dist/ (versión estática para GitHub Pages)
.github/workflows/pages.yml← MISIÓN VI: build + despliegue de la versión estática
docs/                      ← informes por misión, matriz de paridad, diccionarios, evidencias
```

Puntos clave del diseño:

1. **El original nunca se modifica.** Toda la evolución es aditiva: overlays independientes (IIFE con guardas idempotentes) que se inyectan al vuelo (5 en la web: catálogo, recursos, calculadora, respaldo y datos embebidos `estatico.js`; 4 con servidor local, donde la API ya sirve los datos). El punto de restauración es el tag `v9.17-original`.
2. **El servidor es de solo lectura** (`sqlite3 mode=ro`): ninguna función de la aplicación escribe en la BD; las ediciones de recursos viajan únicamente dentro del propio presupuesto en `localStorage` (`it.edicionRecursos`), con aislamiento verificado entre presupuestos.
3. **La versión estática de Pages** se genera desde el código fuente con `scripts/construir_web.py` (mismo mecanismo de inyección que el servidor, con rutas relativas); el HTML original en disco permanece intacto y el build falla si su hash cambia.

## F. Datos y precisión

- **Procedencia y versiones:** cada base importada se registra con catálogo, versión y etiqueta de fuente (`docs/datos/iiib_importaciones.json`). Las respuestas de descomposición etiquetan la versión usada; nunca se mezclan precios de versiones distintas en silencio.
- **Conservación de valores:** los precios y coeficientes de la norma se conservan tal cual; las ediciones del usuario se guardan como capa diferencial (original → editado, reversible) sin destruir el original.
- **Precisión decimal:** doble precisión en tránsito (JSON); presentación con **4 decimales fijos** en importes de descomposición. Verificado con coef fraccionarios (0,375 × 4,5678) y totales de obra (× cantidad) exactos.
- **Separación catálogo/presupuesto:** el catálogo maestro (BD y catálogo embebido) es inmutable desde la aplicación; la modificación de un recurso en un presupuesto no afecta ni a la BD ni a otros presupuestos con el mismo código (probado con presupuesto testigo en la validación E2E).
- **Bases completas (MISIÓN VIII):** las 6 versiones están importadas en la BD local (verificado con conteos e integridad SHA-256 de cada fuente); los datos de la web se regeneran con `scripts/generar_datos_web.py` y se verifican contra un manifest SHA-256 en el build. Hallazgo documentado: los datos útiles de 2017-raíz ≡ 2007-v7.22 bit a bit.

## G. Pruebas y calidad

Resultados reales de la ejecución más reciente (**2026-10-24**, MISIÓN VIII: bases PRECODI re-importadas + paridad web; **139/139 pruebas + 3 validaciones E2E de navegador**):

| Prueba / suite | Comando real | Resultado | Observaciones |
|---|---|---|---|
| Misión III-B — suite importación | `python3 scripts/tests_iiib.py` | **21/21 OK** | 6 versiones re-importadas y verificadas (antes 3/21 por fuentes perdidas) |
| Misión III-C — suite descomposiciones | `python3 scripts/tests_iiic.py` | **21/21 OK** | Con las bases completas (antes 0/21); ids por versión, no literales |
| Misión IV — suite regresión | `python3 scripts/tests_iv.py` | **19/19 OK** | Antes 15/19 (4 fallos de datos) |
| Misión V — suite S-050/S-052 y API | `python3 scripts/tests_v.py` | **28/28 OK** | Nomenclador, edición, precisión, aislamiento, persistencia, BD intacta |
| Misión V — validación navegador E2E | `bash scripts/validar_v_navegador.sh` | **25 ✓ · 0 ✗ · 0 ⏸** | Pasos de norma 17/18/18b EJECUTADOS por primera vez (recalibrados para BD completa) |
| Misión VII — suite respaldo S-005 | `python3 scripts/tests_vii.py` | **15/15 OK** | Contrato actualizado a 5 overlays (estatico.js web-only en dist) |
| Misión VII — validación navegador E2E | `bash scripts/validar_vii_navegador.sh` | **21/21 ✓ × 3 modalidades** | Servidor local, `dist/` y URL pública |
| **Misión VIII — suite paridad web↔local** | `python3 scripts/tests_viii.py` | **11/11 OK** | Equivalencia overlay real (Node) vs servidor real: E1–E5, C1–C3, D1 |
| MISIÓN VI/VIII — pre-validación estática | `bash scripts/prevalidar_web_estatica.sh [URL]` | **18/18 ✓** (dist y URL pública) | Modo web con datos embebidos, norma renderizada y vinculada, catálogo, 0 errores consola |
| Fase III-F — PoC catálogo | `python3 scripts/fase3f_tests.py` | **24/24 OK** | Migraciones 0001..0003 |
| Integridad del original | `sha256sum app/PRECOST-v9.17.html` | **OK** | `50d3cf28…5cbaa2` idéntico antes y después de todos los builds |

> Los fallos históricos de IIIB/IIIC/IV (documentados en [INFORME_FASE_V.md](docs/INFORME_FASE_V.md)) eran **de datos, no de código**: se cerraron al re-importar las bases PRECODI en MISIÓN VIII, sin cambios de lógica de servidor.

## H. Publicación y enlaces (GitHub Pages)

La **demo web estática** se genera automáticamente desde el código fuente en cada push a `main` mediante el workflow [`.github/workflows/pages.yml`](.github/workflows/pages.yml) (ver [ejecuciones](https://github.com/Nardian90/Precost/actions/workflows/pages.yml)):

> **<https://nardian90.github.io/Precost/>**

**MISIÓN VIII — paridad «literal» web ↔ local:** la web incluye los datos PRECODI/PRECOST embebidos (`dist/data`, 5 bases: 2025, 7.21, 7.22, 2017-raíz, SBD2008 — 59 MB generados desde la BD con [scripts/generar_datos_web.py](scripts/generar_datos_web.py)) y el overlay `estatico.js` replica los 5 endpoints del servidor local con formas de respuesta idénticas. La equivalencia está probada automáticamente (tests_viii 11/11: mismas búsquedas, mismas normas, mismas advertencias, misma verificación CMMN/CHMN/CEMN).

| Función | Pages (estático) | Local (con servidor) |
|---|---|---|
| Núcleo PRECOST completo (presupuestos, catálogo embebido, exportaciones XLSX/PDF/Word/JSON) | ✅ | ✅ |
| **Respaldo/restauración completa S-005** (botón «Respaldo» / Alt+B) | ✅ | ✅ |
| Pestaña Recursos: indicadores M/H/E, especificación, edición S-052, «Cargar normas», vínculo de la norma al presupuesto | ✅ | ✅ |
| Calculadora S-080 (modo embebido/manual) | ✅ | ✅ |
| Búsqueda del catálogo PRECODI (botón flotante) en las 5 bases | ✅ (datos embebidos) | ✅ |
| Descomposiciones/normas de composición con verificación contra la fuente | ✅ (datos embebidos) | ✅ |
| Nomenclador `/api/recursos` (añadir recurso propio) y comparación entre versiones | ✅ (datos embebidos) | ✅ |
| Escritura/edición del catálogo y las normas (la BD real) | — | BD solo lectura (por diseño) |

En la web, las consultas del catálogo se sirven desde los datos publicados (aviso «Modo web — datos PRECODI embebidos»); las ediciones del usuario viven SOLO en su presupuesto (`localStorage`). Sin datos publicados, los overlays degradan con aviso explícito («Capa local PRECODI no disponible…»). Detalle en [INFORME_FASE_VIII.md](docs/INFORME_FASE_VIII.md).

Para generar y pre-validar el artefacto localmente:

```bash
python3 scripts/generar_datos_web.py        # exporta la BD → app/web-datos/ (requiere bases importadas)
python3 scripts/construir_web.py            # genera dist/ (verifica SHA-256 del original + manifest de datos)
python3 -m http.server 8877 --bind 127.0.0.1 &   # raíz del repo
bash scripts/prevalidar_web_estatica.sh     # 18 comprobaciones bajo /dist/ (o con URL como argumento)
```

> **Cambio de dispositivo o de navegador:** use el botón «Respaldo» (Alt+B) para exportar todos sus datos a un archivo JSON y restaúrelo en el otro navegador. Es la vía segura para no perder presupuestos al cambiar de equipo, porque los datos viven en el `localStorage` de cada navegador.

## I. Seguridad y limitaciones

- **No se publican** (gitignore + verificación en el build): bases de datos (`bd/*.db`), fuentes `.mdb`/`.rar`/`.exe` de `activos/`, tokens, `.env` ni credenciales. El historial completo ha sido auditado: 0 secretos.
- El servidor local **solo escucha en 127.0.0.1** y abre la BD en **modo solo lectura**.
- Ninguna función del repositorio incluye claves del copiloto IA; esa configuración es del usuario final en su navegador.
- Los presupuestos en la demo estática viven en el `localStorage` del navegador del visitante (origen `nardian90.github.io`): no se envían a ningún servidor.
- El artefacto de Pages se audita en cada build: falla si contiene `.db/.sqlite/.mdb/.env/.rar/.zip/.exe`.
- Limitación estructural de Pages: no ejecuta backends; las funciones de la tabla §H requieren ejecución local.

## J. Licencia y contribución

**Licencia: pendiente de decisión del propietario.** Este repositorio no incorpora aún un archivo `LICENSE`; los derechos sobre el código original v9.17 y sus integraciones corresponden a su propietario hasta que este autorice una licencia concreta. No se ha inventado ni asumido ninguna.

Flujo de contribución del proyecto (ramas + PR, el mismo usado en las Misiones II–V):

1. Crear rama descriptiva desde `main` (p. ej. `v-edicion-recursos-presupuesto`).
2. Commits atómicos con justificación técnica; **nunca modificar** `app/PRECOST-v9.17.html` (el CI lo protege por SHA-256).
3. Ejecutar las suites afectadas y añadir pruebas nuevas para lo que se aporte.
4. Abrir Pull Request hacia `main` con resumen, pruebas ejecutadas, limitaciones y riesgos.
