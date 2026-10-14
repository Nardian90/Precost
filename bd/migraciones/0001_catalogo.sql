-- ============================================================================
-- Migración 0001 — Núcleo de catálogos PRECOST (FASE III-E)
-- ============================================================================
-- Esquema persistente para gestionar catálogos normativos externos (PRECODI,
-- PRECONS III MICONS 2025 y futuros) consultables desde PRECOST.
--
-- Decisiones de diseño (justificadas en docs/ESQUEMA_BD_PRECOST.md):
--   * SQLite: archivo único, sin servidor, embebible en la app HTML vía sql.js
--     (WASM) u OPFS; el PRECOST actual es 100 % local y offline.
--   * Versionado por catálogo: los registros NUNCA se sobrescriben; cada
--     importación crea una versión nueva (inmutabilidad + trazabilidad).
--   * Claves estables de negocio: codigo (+ version) — no IdEstab/autonuméricos
--     de Access, que son locales a cada .mdb.
--   * Procedencia explícita en importaciones y versiones.
--   * ON DELETE RESTRICT en todas las FK: no se permite borrar datos
--     referenciados; el flujo normal es insertar nuevas versiones.

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- Catálogos y versiones
-- ----------------------------------------------------------------------------
CREATE TABLE catalogos (
    id              INTEGER PRIMARY KEY,
    codigo          TEXT    NOT NULL UNIQUE,          -- 'PRECODI', 'PRECONS_III_2025'
    nombre          TEXT    NOT NULL,                 -- 'PRECODI codigo.mdb', 'PRECONS III MICONS 2025'
    pais            TEXT    NOT NULL DEFAULT 'CU',
    base_monetaria  TEXT    NOT NULL DEFAULT 'CUP',   -- moneda en que están expresados los precios MN
    descripcion     TEXT,
    creado_en       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE versiones_catalogo (
    id                  INTEGER PRIMARY KEY,
    catalogo_id         INTEGER NOT NULL REFERENCES catalogos(id) ON DELETE RESTRICT,
    version             TEXT    NOT NULL,              -- '2017-raiz', '2025-06-06'
    fecha_publicacion   TEXT,                          -- fecha oficial de la lista de precios
    fecha_importacion   TEXT    NOT NULL DEFAULT (datetime('now')),
    fuente_archivo      TEXT    NOT NULL,              -- ruta/origen del archivo importado
    fuente_sha256       TEXT,                          -- hash del archivo original
    fuente_detalle      TEXT,                          -- p.ej. 'const DB en PRECOST-v9.17.html'
    estado              TEXT    NOT NULL DEFAULT 'importada'
                        CHECK (estado IN ('importada','validada','activa','retirada')),
    UNIQUE (catalogo_id, version)
);

CREATE TABLE importaciones (
    id                  INTEGER PRIMARY KEY,
    version_id          INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    iniciada_en         TEXT    NOT NULL DEFAULT (datetime('now')),
    finalizada_en       TEXT,
    script              TEXT    NOT NULL,              -- script que la ejecutó
    filas_por_tabla     TEXT    NOT NULL DEFAULT '{}', -- JSON {tabla: n}
    advertencias        TEXT    NOT NULL DEFAULT '[]', -- JSON [strings]
    resultado           TEXT    CHECK (resultado IN ('ok','ok_con_advertencias','error'))
);

-- ----------------------------------------------------------------------------
-- Jerarquía de grupos (capítulo → grupo → subgrupo)
-- PRECODI: SobreGrupos RV (2 dígitos) / Grupos RV (3) / SubGrupos RV (4)
-- PRECOST: G con longitudes 2/3/4
-- ----------------------------------------------------------------------------
CREATE TABLE grupos (
    id              INTEGER PRIMARY KEY,
    catalogo_id     INTEGER NOT NULL REFERENCES catalogos(id) ON DELETE RESTRICT,
    nivel           INTEGER NOT NULL CHECK (nivel IN (1,2,3)),
    codigo          TEXT    NOT NULL,                  -- '01', '011', '0111'
    padre_codigo    TEXT,
    descripcion     TEXT    NOT NULL,
    UNIQUE (catalogo_id, nivel, codigo),
    UNIQUE (catalogo_id, codigo),
    -- FK compuesta: los códigos se repiten entre catálogos, la unicidad del
    -- padre es (catalogo_id, codigo). NULL en padre_codigo = nivel 1.
    FOREIGN KEY (catalogo_id, padre_codigo)
        REFERENCES grupos(catalogo_id, codigo) ON DELETE RESTRICT
);
CREATE INDEX idx_grupos_padre ON grupos(catalogo_id, padre_codigo);

-- ----------------------------------------------------------------------------
-- Partidas (renglones de variante / partidas de presupuesto)
-- PRECODI: Nomenclador de RV · PRECOST: DB.P
-- ----------------------------------------------------------------------------
CREATE TABLE partidas (
    id                  INTEGER PRIMARY KEY,
    version_id          INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    codigo              TEXT    NOT NULL,               -- 6 dígitos, p.ej. '012141'
    descripcion         TEXT    NOT NULL,
    unidad              TEXT    NOT NULL,               -- 'm2', 'tm', '100 m2'…
    factor_unidad       REAL    NOT NULL DEFAULT 1.0,   -- 100.0 si unidad='100 m2'
    capitulo            TEXT,                           -- código de capítulo ('01'..'45')
    -- costos unitarios (componentes VERIFICADOS en FASE III-C)
    costo_mat_mn        REAL,                           -- CMMN  / p[3]
    costo_mo_mn         REAL,                           -- CHMN  / p[4]
    costo_eq_mn         REAL,                           -- CEMN  / p[5]
    costo_total_mn      REAL,                           -- suma / p[2]
    costo_mat_mlc       REAL,                           -- CMMLC
    horas_hombre        REAL,                           -- HORAS HOMBRE
    horas_equipo        REAL,                           -- HORAS EQUIPO
    peso_kg             REAL,                           -- PESO / p[6]
    -- metadatos de la fuente PRECODI (NULL en PRECOST 2025)
    es_oficial          INTEGER CHECK (es_oficial IN (0,1)),
    resolucion_aprob    TEXT,
    fecha_aprobacion    TEXT,
    UNIQUE (version_id, codigo)
);
CREATE INDEX idx_partidas_codigo ON partidas(codigo);
CREATE INDEX idx_partidas_desc   ON partidas(descripcion COLLATE NOCASE);

-- ----------------------------------------------------------------------------
-- Recursos (nomencladores unificados)
-- tipos: material · mano_obra · equipo · juego · semielaborado
-- ----------------------------------------------------------------------------
CREATE TABLE tipos_recurso (
    id      INTEGER PRIMARY KEY,
    codigo  TEXT NOT NULL UNIQUE,          -- 'material', 'mano_obra', …
    nombre  TEXT NOT NULL
);

CREATE TABLE recursos (
    id                  INTEGER PRIMARY KEY,
    version_id          INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    tipo_id             INTEGER NOT NULL REFERENCES tipos_recurso(id) ON DELETE RESTRICT,
    codigo              TEXT    NOT NULL,               -- 10 dígitos en PRECODI
    descripcion         TEXT    NOT NULL,
    unidad              TEXT,
    precio_mn           REAL,                           -- PMN
    precio_mlc          REAL,                           -- PMLC
    precio_total        REAL,                           -- PrecioU = PMN + PMLC (F11)
    peso_unidad         REAL,                           -- PesoU / m[3]
    -- específicos de mano de obra (NULL en otros tipos)
    grupo_salarial      TEXT,                           -- 'II'..'XII'
    especialidad        TEXT,
    -- específicos de equipos (NULL en otros tipos)
    tipo_equipo_id      INTEGER,
    norma_horaria       REAL,
    UNIQUE (version_id, tipo_id, codigo)
);
CREATE INDEX idx_recursos_codigo ON recursos(tipo_id, codigo);
CREATE INDEX idx_recursos_desc   ON recursos(descripcion COLLATE NOCASE);

-- ----------------------------------------------------------------------------
-- Normas de consumo: descomposición de partidas en recursos
-- PRECODI: Norma de Materiales / Mano de Obra / Equipos / Juegos / Semielaborados
-- coeficiente = CantMat | CantRHum | CantEquipo | CantJuego | CantSElab
-- cod_norma  = norma compleja ('S/C' = sin norma / simple)
-- ----------------------------------------------------------------------------
CREATE TABLE normas_partida (
    id                  INTEGER PRIMARY KEY,
    partida_id          INTEGER NOT NULL REFERENCES partidas(id) ON DELETE RESTRICT,
    version_id          INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    tipo_recurso_id     INTEGER NOT NULL REFERENCES tipos_recurso(id) ON DELETE RESTRICT,
    codigo_recurso      TEXT    NOT NULL,
    coeficiente         REAL    NOT NULL,
    cod_norma           TEXT    NOT NULL DEFAULT 'S/C',
    um_norma            TEXT,
    UNIQUE (partida_id, tipo_recurso_id, codigo_recurso, cod_norma)
);
CREATE INDEX idx_normas_partida_rv ON normas_partida(version_id, partida_id);
CREATE INDEX idx_normas_recurso    ON normas_partida(tipo_recurso_id, codigo_recurso);

-- ----------------------------------------------------------------------------
-- Componentes de recursos compuestos:
--   juego        → materiales  (Norma Juego Material)
--   semielaborado → materiales, mano de obra, equipos (Norma Semi *)
-- ----------------------------------------------------------------------------
CREATE TABLE componentes_recurso (
    id                      INTEGER PRIMARY KEY,
    recurso_id              INTEGER NOT NULL REFERENCES recursos(id) ON DELETE RESTRICT,
    version_id              INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    tipo_componente_id      INTEGER NOT NULL REFERENCES tipos_recurso(id) ON DELETE RESTRICT,
    codigo_componente       TEXT    NOT NULL,
    coeficiente             REAL    NOT NULL,
    cod_norma               TEXT    NOT NULL DEFAULT 'S/C',
    UNIQUE (recurso_id, tipo_componente_id, codigo_componente, cod_norma)
);
CREATE INDEX idx_componentes_recurso ON componentes_recurso(version_id, recurso_id);

-- ----------------------------------------------------------------------------
-- Precios de recursos por fuente y fecha (evolución temporal)
-- ----------------------------------------------------------------------------
CREATE TABLE precios_recurso (
    id              INTEGER PRIMARY KEY,
    recurso_id      INTEGER NOT NULL REFERENCES recursos(id) ON DELETE RESTRICT,
    fuente          TEXT    NOT NULL,                   -- 'PRECODI-2017', 'mercado', 'usuario'
    fecha           TEXT    NOT NULL,                   -- ISO
    precio_mn       REAL,
    precio_mlc      REAL,
    moneda          TEXT    NOT NULL DEFAULT 'CUP',
    UNIQUE (recurso_id, fuente, fecha)
);

-- ----------------------------------------------------------------------------
-- Auditoría de modificaciones (append-only)
-- ----------------------------------------------------------------------------
CREATE TABLE auditoria (
    id                  INTEGER PRIMARY KEY,
    tabla               TEXT    NOT NULL,
    registro_id         INTEGER NOT NULL,
    accion              TEXT    NOT NULL CHECK (accion IN ('insert','update','delete','validar')),
    datos_antes_json    TEXT,
    datos_despues_json  TEXT,
    usuario             TEXT    NOT NULL DEFAULT 'sistema',
    fecha               TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_auditoria_tabla ON auditoria(tabla, registro_id);

-- Catálogos de tipos de recurso (semilla)
INSERT INTO tipos_recurso (codigo, nombre) VALUES
    ('material',      'Material'),
    ('mano_obra',     'Mano de obra'),
    ('equipo',        'Equipo'),
    ('juego',         'Juego de trabajo'),
    ('semielaborado', 'Semielaborado');
