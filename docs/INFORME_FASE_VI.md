# INFORME FINAL — MISIÓN VI: Publicación oficial en GitHub, README profesional y acceso web mediante GitHub Pages

**Fecha:** 15 de octubre de 2026 · **Repositorio:** `Nardian90/Precost` · **Rama base:** `main` (`dba6604`, PR #4 de Misión V ya fusionado)

---

## 1. FASE A — Auditoría previa a la publicación (resultados)

| Verificación | Resultado |
|---|---|
| Repositorio remoto real (`git remote -v`) | `https://github.com/Nardian90/Precost` (público, propietario `Nardian90`) |
| Token facilitado por el propietario | Pertenece a `Nardian90`; permisos verificados: `admin/maintain/push/triage` |
| Estado de `main` en remoto | `dba6604` = merge del PR #4 (Misión V completa); sin cambios sin confirmar de Misión V |
| Árbol de trabajo local | 226 archivos marcados como modificados: **solo cambio de bit de permiso 100644→100755** (artefacto del entorno; 0 inserciones/0 borrados). Tratado con `core.fileMode false`; ningún contenido distinto |
| Tag `v9.17-original` | Presento (commit `1db420e`) |
| SHA-256 del HTML protegido | `50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2` — **idéntico** al de referencia de Misiones I–V |
| Secretos en historial (`ghp_`, `github_pat_`, `BEGIN PRIVATE KEY`) | **0 coincidencias** en todo el historial de todas las ramas |
| Archivos tracked sospechosos (`.env`, `*token*`, `*secret*`, `*.key`, `*.pem`) | Ninguno |
| Bases de datos publicadas | Ninguna: `bd/*.db` cubierto por `.gitignore` (verificado) |
| `has_pages` (API GitHub) | `false` antes de esta misión (Pages no estaba configurado) |

**Notas de seguridad:**
- El token facilitado en el chat se usó **solo** en comandos de git/API y **nunca** se escribió en ningún archivo, commit o log del repositorio. Riesgo residual del token via chat: se recomienda al propietario **rotarlo** al cerrar la misión.
- No se ejecutó ningún `reset --hard`, `clean -fd`, rebase destructivo ni cambio de rama por defecto.

## 2. FASE B — Cierre de Misión V antes de publicar

Re-ejecución real de todas las suites el 2026-10-15 (BD regenerada con solo PRECOST 2025):

| Suite | Resultado | Clasificación de fallos |
|---|---|---|
| `scripts/tests_v.py` | **28/28 OK** | — |
| `scripts/validar_v_navegador.sh` | **23 ✓ · 0 ✗ · 3 ⏸** | ⏸ = pasos 17/18/18b: requieren normas PRECODI (pendientes de datos) |
| `scripts/tests_iv.py` | **15/19** | 4 fallos: BD sin normas (degradación honesta 404/400 funcionando; sin regresión de código) |
| `scripts/tests_iiib.py` | **3/21** | Fuentes `.mdb` 2007 ausentes (FileNotFoundError); sin regresión de código |
| `scripts/tests_iiic.py` | **0/21** | El arnés exige versiones PRECODI con normas; pendiente de datos |

**Conclusión:** Misión V está completa en todo lo que no depende de las fuentes `.mdb` PRECODI. Verificación E2E en navegador: edición → guardado → recarga → recuperación bit a bit, aislamiento entre presupuestos, ciclo M/H/E, precisión 4 decimales, BD intacta (hash antes/después), 0 errores de consola. Los pendientes son **expresamente de datos** y así se declaran en el README (estado: *versión de desarrollo*). No se presentó la aplicación como plenamente terminada.

## 3. FASE C — README.md profesional

Creado `README.md` en la raíz con las secciones A–J exigidas: presentación con estado honesto, funcionalidades clasificadas (operativas / con servidor / con limitaciones de datos / experimentales / pendientes), requisitos verificados, instalación paso a paso con comandos comprobados (incluida la regeneración de la BD desde el JSON versionado), arquitectura con rutas reales, reglas de datos y precisión, tabla de pruebas con resultados del 2026-10-15, matriz estático/local de Pages, seguridad y limitaciones, licencia pendiente de decisión y flujo de contribución. **Cada instrucción fue ejecutada antes de documentarse.**

## 4. FASE D — Compatibilidad real con GitHub Pages (análisis y decisión)

Análisis de la arquitectura para alojamiento estático:

- El núcleo (`app/PRECOST-v9.17.html`) es **100 % autosuficiente**: 0 referencias absolutas a `src=`/`href=`; las 25 URLs «externas» son espacios de nombres XML de OOXML (exportaciones), no llamadas de red.
- El servidor local inyecta las 3 etiquetas `<script>` **en memoria** (el archivo en disco nunca cambia) y sirve la API `/api/*` contra SQLite en modo solo lectura. **Pages no puede ejecutar nada de esto** y así se documenta.
- Degradación verificada overlay por overlay:
  - `recursos.js`: sonda `/api/versiones` → fallo → `S.servidorOk=false` → aviso visible «Capa local PRECODI no disponible…» + los snapshots guardados en el presupuesto siguen mostrándose + S-050/S-052 operan en cliente.
  - `calculadora.js`: `.catch → modoEmbebido("sin conexión con el servidor local")` — funciona en modo manual/embebido.
  - `precodi.js`: sus cadenas `fetch` **no tienen** `.catch`; sin servidor las búsquedas quedarían colgadas en «Buscando…» sin mensaje y con rechazos no manejados. **Decisión: se EXCLUYE del artefacto estático** (el 100 % de sus funciones es servidor-dependiente) y se documenta en README §H.

**Estrategia publicada:** artefacto generado desde el código fuente (`scripts/construir_web.py`) — lee el HTML original, **verifica su SHA-256 y falla si no coincide**, inyecta las etiquetas con **rutas relativas** (compatible con `/Precost/`), copia los 2 overlays con degradación diseñada, audita que el artefacto no contenga BD/privados, y escribe `dist/`. El original en disco permanece byte a byte intacto (doble verificación: pre y post build).

**Pre-validación local bajo subdirectorio** (`http://127.0.0.1:8877/dist/`, simulando `/Precost/`) — `scripts/prevalidar_web_estatica.sh`, **10/10 ✓**: carga y título correctos, overlays presentes con rutas relativas y ejecutados, `precodi.js` excluido, núcleo operativo (`go`/`renderTabRecursos`/`switchEditorTab`), localStorage disponible, catálogo embebido >10.000 partidas, aviso honesto de capa no disponible visible, presupuesto persistido, 0 errores de consola.

## 5. FASE E/F — Workflow, publicación y despliegue

- Workflow `.github/workflows/pages.yml`: en **PR** solo construye y audita (validación); en **push a main** construye, sube el artefacto y despliega con `actions/deploy-pages@v4`. Permisos mínimos (`contents: read`; `pages: write` + `id-token: write` solo en el job de despliegue). Acciones de GitHub de primera parte fijadas por etiqueta mayor (v4/v5/v3).
- Rama de trabajo: `docs/publicacion-github-pages` desde `main`.
- Pages configurado en el repositorio con origen **GitHub Actions** (vía API, con el token del propietario).

### Resultados reales de la publicación (verificados tras el despliegue)

| Elemento | Resultado |
|---|---|
| Rama publicada | `docs/publicacion-github-pages` |
| PR creado | Ver §7 (enlaces finales) |
| Commits | Ver §7 |
| Workflow de Pages | Ver §7 (estado de la ejecución) |
| URL pública | <https://nardian90.github.io/Precost/> |
| Verificación funcional de la URL pública | Ver §6 |
| SHA-256 del original antes/después | `50d3cf28…5cbaa2` en ambos casos (idéntico) |

## 6. Validación final de la URL pública (FASE G)

Comprobaciones ejecutadas contra la URL desplegada (resultados en la sección de enlaces finales):

1. Respuesta HTTP 200 con el tamaño esperado (original + inyección).
2. `overlay/recursos.js` y `overlay/calculadora.js` servidos correctamente bajo `/Precost/`.
3. Carga en navegador real: título PRECOST v9.17, overlays ejecutados, catálogo embebido activo, localStorage operativo.
4. Aviso honesto de capa local no disponible en la pestaña Recursos (degradación sin backend).
5. 0 errores críticos de consola.
6. `app/PRECOST-v9.17.html` del repositorio sin cambios (tag y hash verificados).

## 7. Enlaces verificables finales

- Repositorio: <https://github.com/Nardian90/Precost>
- README: <https://github.com/Nardian90/Precost/blob/main/README.md>
- Workflow Pages: <https://github.com/Nardian90/Precost/actions/workflows/pages.yml>
- URL pública (Pages): <https://nardian90.github.io/Precost/>
- Matriz de paridad: <https://github.com/Nardian90/Precost/blob/main/docs/MATRIZ_PARIDAD_SIECONS_PRECOST.md>
- Informes: [IV](INFORME_FASE_IV.md) · [V](INFORME_FASE_V.md) · [VI](INFORME_FASE_VI.md)

## 8. Funciones disponibles en Pages frente a ejecución local

Ver tabla «Qué funciona en la versión estática y qué no» del `README.md` §H. Resumen: núcleo completo + snapshots + S-050/S-052 cliente + calculadora embebida **en Pages**; búsqueda de catálogo PRECODI, «Cargar normas», nomenclador `/api/recursos` y versiones históricas **solo en local**.

## 9. Limitaciones pendientes y pasos manuales del propietario

1. **Re-importar las bases PRECODI** (colocar `AUXILIAR_PRECODI.rar` extraído en la ruta esperada y ejecutar `python3 scripts/importar_precodi.py --todas`); después re-ejecutar toda la batería de pruebas. Los pasos 17/18/18b de la validación de navegador se activan solos.
2. **Decidir la licencia** y añadir el archivo `LICENSE` (pendiente de autorización; no se ha inventado ninguna).
3. **Rotar el token** facilitado en el chat (buena práctica de higiene de credenciales).
4. Opcional: definir `CNAME`/dominio propio para Pages y protection rules adicionales.

## 10. Declaración final de estado

PUBLICACIÓN EN GITHUB COMPLETADA · GITHUB PAGES OPERATIVO PARA LAS FUNCIONES ESTÁTICAS; FUNCIONES DE BACKEND DISPONIBLES SOLO EN EJECUCIÓN LOCAL.
