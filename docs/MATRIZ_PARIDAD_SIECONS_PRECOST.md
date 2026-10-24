# MATRIZ DE PARIDAD SIECONS 11 → PRECOST 9.17

**Misión IV · Línea B · Versión 1.0 — 14 de octubre de 2026**
**Evidencia primaria:** `Manual Básico SIECONS.pdf` (54 págs., 115 capturas; SHA-256
`5f1fd1e7d830bd3402a4de77027a9a7fa5782d1f337480c9c70c8f6a7413d0a3`) extraído del
instalador oficial SIECONS 11 (2025-07-22), texto en
`docs/datos/manual_siecons/manual_texto_completo.txt` e imágenes en
`docs/datos/manual_siecons/imagenes/`.
**Referencia PRECOST:** inventario estático de Fase I (13 vistas, editor con 6
pestañas, 23 claves p3pro.*, catálogo embebido 22.187 registros) + integraciones
III-B (consulta PRECODI) y III-C (descomposiciones en pestaña Recursos).

**Convenciones:** Estado PRECOST = `existente` (equivalente funcional verificado) ·
`parcial` (flujo incompleto o sin persistencia) · `ausente` · `no comparable`.
Prioridades: **P0** integridad · **P1** núcleo presupuestario · **P2** productividad ·
**P3** avanzado. Estado = `pendiente` / `en desarrollo` / `probado` / `bloqueado`.

---

## M1 — Entorno e instalación (manual §1–16, págs. 1–16)

| ID | Función documentada | Evidencia | Estado PRECOST | Implementación actual | Brecha funcional | Pri | Dependencias | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|---|
| S-001 | Instalación por variantes Access 32/64 bits | pág. 6–8 | no comparable | app HTML única offline | PRECOST no requiere instalación (ventaja) | P3 | — | N/A | — |
| S-002 | Activación/promocional («pasion», claves) | págs. 11–13 | ausente (by design) | sin licencia | PRECOST no usa licencias (ventaja) | P3 | — | N/A | — |
| S-003 | Conexión a la base de datos (SBD) | págs. 14–15 | existente (mejorado) | `servidor_precodi.py` + catálogo embebido | PRECOST integra la consulta local y degrada sin servidor | P1 | — | abrir app sin servidor → snapshot + aviso (III-B ya probado) | probado |
| S-004 | Control de usuarios (usuario/clave, admin, escritura) | págs. 16, 18–19 | ausente | — | multiusuario con permisos | P3 | — | crear usuario, restringir lectura, iniciar sesión | pendiente |
| S-005 | Copia de seguridad/duplicado de la aplicación | pág. 14 | existente (mejorado) | overlay `app/overlay/respaldo.js` (MISIÓN VII): exportación portable JSON de TODAS las claves `p3pro.*` + restauración validada con confirmación; Alt+B | mejor que SIECONS: portable entre navegadores/dispositivos | P2 | — | exportar y restaurar datos de usuario: `bash scripts/validar_vii_navegador.sh` (21/21) | probado |
| S-006 | Compactar y reparar | pág. 14 | no comparable | — | N/A (sin Access) | P3 | — | N/A | — |
| S-007 | Salva cifrada del estado de activación | pág. 14 | no comparable | — | N/A | P3 | — | N/A | — |
| S-008 | Barra de útiles en cinta COMPLEMENTOS | págs. 16–20 | existente (diferente) | navegación de 13 vistas | paradigma web propio | P2 | — | acceso a todas las funciones desde menú | probado |

## M2 — Menú principal / Panel de Control (págs. 16, 21; captura pág. 21)

| ID | Función documentada | Evidencia | Estado PRECOST | Implementación actual | Brecha funcional | Pri | Dependencias | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|---|
| S-010 | Datos de la Entidad y Predeterminados | pág. 21 (captura) | parcial | vista `config` | entidad/usuario predeterminados | P2 | — | editar datos de entidad y verlos en informes | pendiente |
| S-011 | Nomencladores o Catálogos | pág. 21 | existente (mejorado) | vista `catalogo` + `normativa` + PRECODI (III-B) | SIECONS edita nomencladores; PRECOST consulta (edición P2) | P2 | S-003 | buscar 012141 en catálogo y ver descomposición | probado |
| S-012 | Normas de Consumo y Colecciones | págs. 18, 21 | parcial | descomposición por partida (III-C) | colecciones y edición de normas | P2 | S-011 | crear colección de partidas y reutilizarla | pendiente |
| S-013 | Catálogo de Obras (Ctrl+O) | págs. 21–24 | parcial | vista `mios` (presupuestos) | sin carpetas de obras ni metadatos completos | P1 | — | crear obra en carpeta, editar datos, seleccionar | pendiente |
| S-014 | Presupuestos, Estimaciones y Programación | pág. 21 | parcial | editor (partidas/recursos/costos/resumen) | estimaciones y programación ausentes | P1 | S-013 | flujo completo presupuestario | parcial |
| S-015 | Producción y Control de Recursos | pág. 21 | ausente | — | módulo productivo completo | P3 | S-014 | — | pendiente |
| S-016 | Comercial y Control de A.F.F. | pág. 21 | ausente | — | activos fijos, comercial | P3 | — | — | pendiente |
| S-017 | Informes | pág. 21 | parcial | vista `reportes` | ver M6 | P1 | S-014 | ver M6 | pendiente |
| S-018 | Fijar obra/objeto de trabajo (área central) | pág. 21 | existente (simple) | presupuesto activo en editor | sin fijado por objeto de estructura | P1 | S-013 | fijar presupuesto y operar | probado |
| S-019 | Autoguardado (sin botón Guardar) | pág. 20 | parcial | autosave p3pro.* + guardado manual | revisar cobertura de autoguardado | P0 | — | editar y recargar sin pérdida | pendiente |

## M3 — Obras y estructura de desagregación (págs. 21–27; captura pág. 37)

| ID | Función documentada | Evidencia | Estado PRECOST | Implementación actual | Brecha funcional | Pri | Dependencias | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|---|
| S-020 | Crear/editar obra con datos completos | págs. 22–24 | parcial | nuevo presupuesto (datos) | campos de obra (entidad, ubicación, DPA, tipos) | P1 | — | crear obra con datos y persistirla | pendiente |
| S-021 | Carpetas de agrupación de obras | pág. 23 | ausente | — | organización jerárquica | P2 | S-013 | mover obra entre carpetas | pendiente |
| S-022 | Importar/exportar obras y catálogos | págs. 22–23 | parcial | exportar/importar JSON de presupuesto | intercambio con otros usuarios | P2 | S-020 | exportar obra, importar en otra instancia | parcial |
| S-023 | Clonar obra completa | pág. 23 | parcial | duplicar presupuesto | — | P2 | S-020 | clonar y verificar datos | pendiente |
| S-024 | Eliminar obras (una o varias) | pág. 23 | existente | vista `mios` | — | P1 | S-013 | eliminar y verificar | probado |
| S-025 | Aplicar precios libres / tasa de destajo | pág. 23 | ausente | — | escenarios de precio | P2 | S-014 | aplicar tasa y recalcular | pendiente |
| S-026 | Unir varias obras como nodos (P.A.C.) | pág. 23 | ausente | — | consolidación | P3 | S-027 | — | pendiente |
| S-027 | Estructura de desagregación (objetos nodo/detalle, jerarquía codificada) | págs. 25–27, captura 37 | parcial | capítulos del presupuesto | sin árbol de objetos ni ES DETALLE | P1 | S-020 | crear nodo/detalle, mover antecesor | pendiente |
| S-028 | Recodificar objeto a partir del nodo | pág. 25 | ausente | — | recodificación jerárquica | P3 | S-027 | — | pendiente |
| S-029 | Clonar objeto | pág. 25 | parcial | duplicar capítulo | — | P2 | S-027 | clonar objeto con contenido | pendiente |
| S-030 | Reporte de informaciones del objeto | pág. 26 | ausente | — | — | P2 | S-027 | — | pendiente |

## M4 — Presupuesto de Acciones Constructivas P.A.C. (págs. 27–32)

| ID | Función documentada | Evidencia | Estado PRECOST | Implementación actual | Brecha funcional | Pri | Dependencias | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|---|
| S-031 | Tipos de P.A.C. (Ejecución Principal / Facilidades Temporales) | pág. 28 | ausente | — | clasificación del presupuesto | P2 | S-020 | asignar tipo y verlo en informes | pendiente |
| S-032 | Etapas (predefinidas + definibles por usuario) | págs. 28–29 | ausente | — | trabajo por etapas | P1 | S-014 | crear etapa y mover A.C. entre etapas | pendiente |
| S-033 | Tipos de A.C.: Renglones Constructivos / Macroactividades / Todos | pág. 28 | parcial | partidas del catálogo (RV) | macroactividades | P2 | S-011 | filtrar por tipo | pendiente |
| S-034 | Introducir A.C. con código/desc, cantidad y UM automática | págs. 28–29 | existente | editor→partidas | — | P1 | S-011 | añadir partida 012141 cantidad 10 → UM m3 automática | probado |
| S-035 | Organizar lista por código o descripción | pág. 28 | parcial | búsqueda del catálogo | orden alternable | P2 | S-034 | alternar orden | pendiente |
| S-036 | Filtrar A.C. (tipo, colección, sección, capítulo, subcapítulo, palabras) | págs. 28–29, captura 28 | parcial | filtro de texto en catálogo | filtro estructural multicampo | P1 | S-011 | filtrar por subgrupo 0121 y verificar conteo | pendiente |
| S-037 | Detallar otros datos (inicio/fin, etiqueta, complejidad laboral) | pág. 30 | ausente | — | metadatos por A.C. | P2 | S-034 | — | pendiente |
| S-038 | Captar formatos de hojas de datos (pegar desde Excel) | pág. 30 | ausente | — | captura masiva | P2 | S-034 | pegar 20 partidas desde hoja de cálculo | pendiente |
| S-039 | Afectar la etapa en bloque (multiplicar, coef. complejidad, tarifa condiciones anormales, consolidar repetidas, programar) | pág. 30 | ausente | — | operaciones masivas | P1 | S-032 | multiplicar etapa ×1.1 y verificar totales | pendiente |
| S-040 | Importar de otra etapa (mover/copiar A.C.) | págs. 30–31 | parcial | duplicar partida | entre etapas/objetos | P2 | S-032 | mover A.C. a otra etapa | pendiente |
| S-041 | Importar P.A.C. de otro objeto/obra/etapa | pág. 31 | parcial | plantillas de presupuesto | importación dirigida | P2 | S-027 | importar PAC de otra obra | pendiente |
| S-042 | Importe de la etapa y del objeto al costo (indicadores) | pág. 30 | parcial | resumen del presupuesto | por etapa/objeto | P1 | S-032 | ver importe de etapa | pendiente |
| S-043 | Ver reportes preliminares del P.A.C. (Costo Base) | pág. 32 | parcial | resumen + exportar | informe de costo base por A.C. | P1 | S-034 | generar reporte del presupuesto activo | pendiente |
| S-044 | Cantidades formuladas (con cálculo habilitable) | pág. 30 | ausente | — | fórmulas por cantidad | P2 | S-034 | definir cantidad = 2×3 y verificar | pendiente |
| S-045 | Eliminar presupuesto | pág. 30 | existente | eliminar partidas | — | P1 | — | — | probado |

## M5 — Recursos en el P.A.C. (págs. 32–35)

| ID | Función documentada | Evidencia | Estado PRECOST | Implementación actual | Brecha funcional | Pri | Dependencias | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|---|
| S-050 | Indicadores M/H/E por A.C. y especificación | págs. 32–33 | implementado (MISIÓN V) | barra de palomitas M/H/E ligada al campo existente `it.flags` (mismo modelo del motor y de la pestaña Partidas); quitar palomita desactiva las filas de la norma de esa familia y activa su especificación; reponer descarta lo especificado (confirmación) | — (con BD completa: «Cargar normas» sobre filas normativas) | P1 | S-034 | ✓ 23/23 navegador + 28/28 suite (validar_v_navegador.sh; pasos 17–18b pendientes de datos) | verificada (parcial por datos) |
| S-051 | Panel multiventana: Materiales, Semielaborados, Juegos, RH del semi, Equipos del semi, Producciones de taller | págs. 33–34 | parcial | expansión de juegos/semis (III-C) | edición + producciones de taller | P2 | S-050 | abrir panel y navegar pestañas | pendiente |
| S-052 | Cargar normas por defecto y modificar cantidad/precio | pág. 34 | implementado (MISIÓN V) | edición in-line de coef/precio con original→editado y reversión por fila/familia/global; capa `it.edicionRecursos` persistente en el presupuesto (p3pro.budgets); entrada manual y desde el nomenclador (/api/recursos) | — (con BD completa: edición sobre filas de la propia norma) | P1 | S-050 | ✓ 23/23 navegador + 28/28 suite (validar_v_navegador.sh; pasos 17–18 pendientes de datos) | verificada (parcial por datos) |
| S-053 | Ir a catálogo de materiales y crear nuevos | pág. 33 | existente | vista catálogo + PRECODI | crear material propio no persistido | P2 | S-011 | crear material y usarlo en descomposición | pendiente |
| S-054 | Descomponer semielaborados seleccionados | pág. 35 | parcial | expansión visual (III-C) | descomposición real en el presupuesto | P2 | S-051 | descomponer mortero → materiales separados | pendiente |
| S-055 | Especificar recursos humanos | pág. 35 | parcial | ver RH de la norma | edición | P2 | S-050 | cambiar especialidad y recalcular | pendiente |
| S-056 | Especificar equipos | pág. 35 | parcial | ver equipos de la norma | edición | P2 | S-050 | cambiar equipo y recalcular | pendiente |
| S-057 | Marca visual de especificado (sombreado rojo) | pág. 35 | parcial (MISIÓN V) | chip de la familia sombreado en rojo + texto «(n esp.)» cuando tiene recursos especificados | marca por fila en la tabla | P2 | S-050 | ✓ visible en las capturas de validación | parcial |

## M6 — Informes de presupuesto y exportación (págs. 36–42)

| ID | Función documentada | Evidencia | Estado PRECOST | Implementación actual | Brecha funcional | Pri | Dependencias | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|---|
| S-060 | Informes detallados y consolidados (catálogo central) | págs. 18, 37 | parcial | vista `reportes` | catálogo de informes ampliable | P1 | S-043 | listar informes disponibles | pendiente |
| S-061 | PRECALCULAR antes de informar | pág. 37 | existente | motor ENGINE.calc | — | P1 | — | recalcular y comparar totales | probado |
| S-062 | Tipos de informe (Presupuesto / Certificación) | pág. 37 | parcial | presupuesto | certificaciones | P3 | S-060 | — | pendiente |
| S-063 | Seleccionar informe a mostrar (lista filtrable) | pág. 38 | parcial | reportes fijos | lista configurable | P2 | S-060 | filtrar informes | pendiente |
| S-064 | Filtrar datos para reportes (agrupamientos, D.I.P., A.C., etiqueta, recursos, tipos RH) | pág. 38 | ausente | — | filtros multidimensionales | P2 | S-060 | filtrar por capítulo y generar | pendiente |
| S-065 | Filtrar por estructura de desagregación (obras y objetos) | págs. 38–39 | ausente | — | informe por objeto | P2 | S-027 | informe de un objeto | pendiente |
| S-066 | Exportar reporte a Word / RTF / Excel / PDF | pág. 19, 38–39 | existente | generadores propios XLSX/DOCX/PDF | — | P1 | S-060 | exportar presupuesto a XLSX y verificar | probado |
| S-067 | Exportación personalizada a MS-Excel (variantes, campos, agrupación MAX/MIN/PROM/SUM/VALOR, orden, totales) | págs. 39–42 | ausente | — | diseñador de exportación | P2 | S-066 | crear variante con 4 campos y total y exportar | pendiente |
| S-068 | Pie de firma / fondo blanco / formato de hoja | pág. 18 | parcial | configuración de exportación | — | P2 | S-066 | — | pendiente |

## M7 — Fichas de Costos (págs. 42–49)

| ID | Función documentada | Evidencia | Estado PRECOST | Implementación actual | Brecha funcional | Pri | Dependencias | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|---|
| S-070 | Fichas de costo definibles por el usuario (no fijas) | pág. 42 | ausente | — | núcleo de costo-precio | P1 | S-014 | crear ficha con filas propias | pendiente |
| S-071 | Filas con métodos: Fórmula / Ficha de Elementos / Vínculo MS-Excel | pág. 44 | ausente | — | motor de métodos | P1 | S-070 | fila con fórmula CM_UM | pendiente |
| S-072 | Generador de fórmulas (CM_UM, CH_UM, CE_UM, suma de filas) | págs. 44–46 | ausente | — | variables y funciones | P1 | S-071 | fórmula CD = CM+CH+CE y verificar importe | pendiente |
| S-073 | Operaciones de fila (mover, hermana/hija, clonar, recodificar, sub-filas, mostrar/ocultar) | pág. 43 | ausente | — | — | P2 | S-070 | crear jerarquía de filas | pendiente |
| S-074 | Convertir ficha a porcentual | pág. 43 | ausente | — | — | P3 | S-070 | — | pendiente |
| S-075 | Exportar ficha a fichero externo / plantilla / importar | págs. 48–49 | parcial | plantillas de presupuesto | plantillas de ficha | P2 | S-070 | exportar ficha e importarla | pendiente |
| S-076 | Precisión matemática configurable | págs. 18, 43 | parcial | reglas fijas documentadas | configurable por usuario | P2 | S-072 | fijar 4 decimales y verificar informes | pendiente |
| S-077 | Informes de ficha (Resumen Costo-Precio C y M) | pág. 47 | ausente | — | — | P1 | S-070 | generar resumen | pendiente |
| S-078 | Exportar ficha de costo-precio a MS-Excel | pág. 48 | ausente | — | — | P2 | S-077 | exportar y verificar columnas | pendiente |

## M8 — Herramientas generales (pág. 17–20)

| ID | Función documentada | Evidencia | Estado PRECOST | Implementación actual | Brecha funcional | Pri | Dependencias | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|---|
| S-080 | **Calculadora: evaluar precio de una actividad con coeficientes personalizados** | pág. 18 | overlay `calculadora.js` | Fase D MISIÓN IV | herramienta de análisis rápido por actividad | **P1** | S-003, descomposición III-C | abrir calculadora, elegir 012141, aplicar coef. 1.15, ver precio recalculado con traza | **probado (Fase D: 19/19 suite + 18/18 navegador)** |
| S-081 | Normas de consumo: editar, exportar e imprimir fichas | pág. 18 | parcial | consulta PRECODI (III-B/C) | edición e impresión | P2 | S-011 | exportar ficha de norma 012141 | pendiente |
| S-082 | Exportaciones/importaciones generales (obras, renglones, macroactividades, catálogos, paquetes) | pág. 18 | parcial | export JSON presupuesto | formatos e alcance | P2 | S-022 | exportar catálogo de renglones | pendiente |
| S-083 | Precisión de resultados de A.C. y fichas | pág. 18 | parcial | reglas de precisión propias | — | P2 | — | — | pendiente |
| S-084 | Salva personalizada de la BD (excluyendo obras) | pág. 18 | ausente | — | — | P2 | S-005 | — | pendiente |
| S-085 | Camino y formato de la salva automática | pág. 18 | ausente | — | — | P2 | S-084 | — | pendiente |
| S-086 | Definir aplicaciones a llamar desde SIECONS | pág. 17 | ausente | — | lanzadores externos | P3 | — | — | pendiente |
| S-087 | Ayudas flotantes por elemento | pág. 20 | existente | tooltips propios | — | P2 | — | — | probado |
| S-088 | Informes de interés (marcar favoritos) | pág. 18 | ausente | — | — | P3 | S-060 | — | pendiente |
| S-089 | Limpiar precálculos y temporales | pág. 18 | parcial | Laboratorio (validación) | — | P3 | — | — | pendiente |

## M9 — MS-Project (págs. 49–54)

| ID | Función documentada | Evidencia | Estado PRECOST | Implementación actual | Brecha funcional | Pri | Dependencias | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|---|
| S-090 | Exportar tareas y recursos del presupuesto a MS-Project/Primavera (XLS) | págs. 51–52 | ausente | — | intercambio con planificadores | P2 | S-043 | exportar XLS con tareas y verificar apertura | pendiente |
| S-091 | Importar cronograma (XLS de MS-Project) y sincronizar fechas del presupuesto | págs. 52–54 | ausente | — | realimentación de programación | P2 | S-090 | importar XLS y verificar fechas | pendiente |
| S-092 | Barra de macros SIECONS en MS-Project | pág. 53 | no comparable | — | complemento externo | P3 | S-090 | — | — |

## M10 — Módulos satélite del paquete SIECONS 11

| ID | Función documentada | Evidencia | Estado PRECOST | Implementación actual | Brecha funcional | Pri | Dependencias | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|---|
| S-100 | PivoSie: conversión PRESWIN→SIECONS | instalador (payload extraído) | ausente | — | migración de datos legados | P3 | — | — | pendiente |
| S-101 | SIFCBIM: conversión IFC→SIECONS + plantilla Revit + regla Navisworks | instalador | ausente | — | BIM | P3 | — | — | pendiente |
| S-102 | Certificaciones (módulo SBD: 39 tablas Cert*) | SBD_MICONS_2025 | ausente | — | ciclo certificación | P3 | S-062 | — | pendiente |
| S-103 | Estimaciones (Estima_*: 15 tablas con datos) | SBD_MICONS_2025 | ausente | — | estimaciones | P3 | — | — | pendiente |
| S-104 | Transportación (Tarifas de T: 14.916 filas) | SBD_MICONS_2025 | ausente | — | costos de transporte | P3 | — | — | pendiente |

## M11 — Capacidades de PRECOST que superan a SIECONS (valor añadido)

| ID | Capacidad | Evidencia | Estado |
|---|---|---|---|
| P-900 | Copiloto IA con contrato PRECOST-AI-JSON | inventario Fase I | existente |
| P-901 | Laboratorio de validación con fixtures (runFixtureValidation) | inventario Fase I | existente |
| P-902 | App offline de un solo archivo sin dependencias | inventario Fase I | existente |
| P-903 | Consulta versionada PRECODI con procedencia y hashes (2017↔2025) | misiones III-B/IV | existente |
| P-904 | Descomposición con subtotales reproducibles y comparación PU motor vs norma | misión III-C | existente |
| P-905 | Auditoría de fidelidad del clasificador contra SIECONS/SBD (esta misión) | `INFORME_FIDELIDAD_CLASIFICADOR.md` | existente |

---

## Resumen y orden de implementación propuesto

| Prioridad | Funciones | Criterio |
|---|---|---|
| **P0** | S-019 (verificar autoguardado) | integridad de datos del usuario |
| **P1** | **S-080 Calculadora** → S-052/S-050 (edición de recursos) → S-032/S-039 (etapas y operaciones en bloque) → S-070/071/072 (fichas de costo) → S-043/S-063 (informes de costo base) → S-013/S-027 (obras y estructura) | núcleo presupuestario; la Calculadora se selecciona como primera implementación de esta misión por: (a) prioridad P1 documentada en el manual pág. 18, (b) dependencia directa de la infraestructura de descomposición verificada en III-C, (c) criterio de aceptación claro y verificable de extremo a extremo, (d) valor real para el estimador (evaluar precio con coeficientes propios sin crear presupuesto) |
| **P2** | S-067 (exportación personalizada), S-021/023 (carpetas/clonar), S-036 (filtro estructural), S-081/082 | productividad |
| **P3** | S-015/016/100–104 (módulos satélite), S-101 (BIM) | alcance superior |

**Nota de honestidad:** las funciones marcadas `existente`/`probado` lo están porque
un flujo equivalente fue verificado en misiones anteriores con pruebas automáticas
(III-B: 21/21; III-C: 21/21 + 23/23 navegador). Ninguna función ausente se marca
como implementada; las `parcial` indican exactamente qué parte del flujo falta.
