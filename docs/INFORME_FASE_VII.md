# INFORME FINAL — MISIÓN VII: Respaldo/restauración completa (S-005) y experiencia web mejorada

**Fecha:** 24 de octubre de 2026 · **Repositorio:** `Nardian90/Precost` · **Rama base:** `main` (`3f4edb1`, MISIÓN VI)

**Motivo:** el propietario solicitó que PRECOST «funcione literal como SIECONS pero mejor» y que se pueda «usar desde internet desde GitHub». La versión web ya estaba desplegada (MISIÓN VI); esta misión cierra el hueco de paridad P2 más visible para un uso real desde la web: la copia de seguridad de los datos del usuario.

---

## 1. Auditoría previa

| Verificación | Resultado |
|---|---|
| `main` local vs remoto | `3f4edb1` en ambos — sin cambios del propietario desde MISIÓN VI (9 días) |
| Árbol de trabajo | Limpio |
| SHA-256 del HTML protegido | `50d3cf28…5cbaa2` — idéntico a la referencia de Misiones I–VI |
| GitHub Pages | `https://nardian90.github.io/Precost/` respondiendo 200 (7.244.982 bytes) |
| Ítem de matriz seleccionado | **S-005** (P2): «Copia de seguridad/duplicado» — estado anterior: `parcial` / `pendiente` |
| Análisis de hueco | El núcleo solo exportaba/importaba presupuestos individuales; no existía salva del conjunto (plantillas, casos, historial, configuración). SIECONS lo ofrece en pág. 14 de su manual. |

## 2. Implementación — overlay `app/overlay/respaldo.js` (S-005, cuarto overlay aditivo)

Diseño 100 % cliente (sin servidor, sin red — verificado estáticamente en tests_vii V2):

- **Exportación:** botón «Respaldo» (abajo-izquierda) o **Alt+B** → panel con estado real (N claves, N presupuestos, N plantillas; aviso si hay clave de API del copiloto incluida) → descarga `precost-respaldo-AAAA-MM-DD-HHMM.json` con **todas** las claves `p3pro.*` (formato `{app, formato:1, fecha, claves, datos}`).
- **Restauración:** selección de archivo → validación **estricta** (app PRECOST, formato 1, sección datos objeto, todas las claves con prefijo `p3pro.`, valores de texto, tamaño por clave < 8 MB) → confirmación explícita con resumen → **modo reemplazo** (el navegador queda exactamente como estaba al generar el respaldo) → recarga. **Nada se escribe si la validación completa no pasa** (sin escrituras parciales).
- **Mejora sobre SIECONS:** el respaldo es un archivo JSON portable — sirve para migrar entre navegadores y dispositivos, algo que la salva de SIECONS (ligada al equipo/Access) no ofrece.
- **Privacidad:** el archivo puede contener la clave de API del copiloto si el usuario la configuró — se advierte en el panel. No hay ninguna comunicación de red.

Corrección de calidad incluida (MISIÓN IV heredada): `calculadora.js` ahora **apila** su botón flotante encima del del catálogo cuando ambos coexisten en modo servidor local (antes se solapaban). Verificado en navegador: catálogo y=524, calculadora y=486, respaldo abajo-izquierda — los tres visibles y accesibles.

## 3. Cambios de contrato documentados (3 → 4 overlays)

La arquitectura creció de 3 a 4 overlays aditivos. Los contratos exactos se actualizaron con justificación en el propio código de prueba (no se «pintó de verde» nada: el conteo exacto sigue siendo estricto, ahora espera 4):

- `scripts/tests_iv.py` T3 → `test_t3_inyeccion_cuatro_etiquetas`
- `scripts/tests_v.py` N14 → `test_n14_inyeccion_exactamente_cuatro_overlays` (+ marca idempotente `__pcodRespaldo`)
- `scripts/servidor_precodi.py`: inyección + ruta `/overlay/respaldo.js`
- `scripts/construir_web.py`: `respaldo.js` en `OVERLAYS_WEB` y en la plantilla de inyección relativa del artefacto estático.

## 4. Pruebas ejecutadas (2026-10-24, todas reales)

| Suite / validación | Resultado | Detalle |
|---|---|---|
| `python3 scripts/tests_vii.py` (nueva) | **15/15 OK** | Integridad SHA-256; sintaxis node; guardas (idempotente, solo `p3pro.*`, sin red, confirmación, validación antes de escribir, gancho de pruebas); servidor sirve el archivo byte a byte; inyección; artefacto `dist/` con overlay íntegro y sin archivos privados; guardia del fix de coexistencia |
| `bash scripts/validar_vii_navegador.sh` (nueva, servidor local) | **21/21 ✓** | UI (FAB, panel, estado, Alt+B, Esc); setup presupuesto+plantilla+tema; exportación correcta; **catástrofe simulada** (borrar todo + recargar → pérdida); restauración → recuperación **bit a bit** de `budgets`/`userTemplates`/`theme`; la app carga el estado interno restaurado; 4 archivos inválidos rechazados (clave sin prefijo, archivo ajeno, valor no-texto, formato desconocido) sin escrituras ni alteración de datos legítimos; 0 errores de consola |
| `bash scripts/validar_vii_navegador.sh http://127.0.0.1:8877/dist` | **21/21 ✓** | La misma batería contra el artefacto estático (modalidad Pages) |
| `python3 scripts/tests_v.py` (regresión) | **28/28 OK** | Tras actualizar N14 al contrato de 4 overlays |
| `bash scripts/validar_v_navegador.sh` (regresión) | **23 ✓ · 0 ✗ · 3 ⏸** | Idéntico al baseline de MISIÓN V (⏸ = datos PRECODI) |
| `python3 scripts/tests_iv.py` (regresión) | **15/19** | Los mismos 4 fallos del baseline (BD sin normas — pendiente de datos; sin regresión) |
| `bash scripts/prevalidar_web_estatica.sh` (regresión) | **10/10 ✓** | Artefacto con el 4º overlay bajo subdirectorio |
| `sha256sum app/PRECOST-v9.17.html` | **OK** | `50d3cf28…5cbaa2` antes y después de todo |

## 5. Publicación y despliegue

- Rama de trabajo: `vii-respaldo-usuario` desde `main` (`3f4edb1`), commits atómicos.
- Integración a `main` según la autorización permanente del propietario («haces el pr o commit al main»). El PR por API sigue bloqueado por el ámbito del token (sin `Pull requests:write`).
- El workflow de Pages reconstruye el artefacto y redespliega automáticamente en cada push a `main`.
- Verificación final contra la URL pública: ver §7 tras el despliegue.

## 6. Documentación actualizada

- `README.md`: S-005 en funciones operativas sin servidor; arquitectura con 4º overlay; fila nueva en la matriz Pages/local; tabla de pruebas con resultados del 2026-10-24; nota de migración entre dispositivos.
- `docs/MATRIZ_PARIDAD_SIECONS_PRECOST.md`: **S-005 → existente (mejorado), probado**.
- Este informe. Evidencias: `docs/datos/vii_respaldo_01_panel.png`, `vii_respaldo_02_estado.png`.

## 7. Validación final de la URL pública (tras el despliegue)

Ejecutada contra `https://nardian90.github.io/Precost/` el 2026-10-24, tras el workflow **#40054929557** (`completed / success`, commit `e73ebf5`):

- URL pública: **HTTP 200, 7.245.032 bytes** (original + inyección de 3 etiquetas relativas); `overlay/respaldo.js` servido con 200.
- `bash scripts/validar_vii_navegador.sh https://nardian90.github.io/Precost` → **21/21 ✓**: botón y panel operativos, Alt+B/Esc, exportación correcta, catástrofe simulada y recuperación **bit a bit**, 4 rechazos sin escrituras parciales, 0 errores de consola.
- SHA-256 del original en el repositorio remoto (`main`): `50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2` — **idéntico** (además verificado por el CI en el build).
- Evidencias: `docs/datos/vii_pages_respaldo_publico.png`, `vii_pages_panel_publico.png`.

## 8. Qué funciona hoy en la web (estado honesto)

**En `https://nardian90.github.io/Precost/` (estático):** núcleo completo de presupuestación (13 vistas, 6 pestañas, catálogo embebido de 22.187 registros), exportaciones XLSX/PDF/Word/JSON, importación JSON validada, pestaña Recursos con snapshots + S-050 (indicadores M/H/E y especificación manual) + S-052 (edición por presupuesto), calculadora S-080 embebida y **respaldo/restauración completa S-005**.

**Solo con servidor local:** búsqueda del catálogo PRECODI, descomposiciones del catálogo no guardadas, «Cargar normas», nomenclador `/api/recursos`, versiones históricas.

**Pendiente de datos (bloquea el resto de la paridad «literal» con SIECONS):** re-importar las bases PRECODI históricas (2007/2011/2017). Requiere que el propietario vuelva a subir `AUXILIAR_PRECODI.rar` (o las carpetas `.mdb`); con ellas, una futura misión puede incluso **embeber las normas de composición en el artefacto estático** para que la web tenga descomposiciones completas sin servidor.

## 9. Pasos manuales del propietario

1. (Opcional pero recomendado) Re-subir `AUXILIAR_PRECODI.rar` para desbloquear las bases históricas y completar la paridad de descomposiciones.
2. Decidir la licencia (`LICENSE` sigue pendiente de autorización).
3. Rotar el token de GitHub si no se ha hecho (higiene de credenciales).
