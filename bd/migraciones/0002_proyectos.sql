-- ============================================================================
-- Migración 0002 — Proyectos y presupuestos (FASE III-E, esquema preparado)
-- ============================================================================
-- Modela el ciclo presupuesto → capítulos → partidas presupuestadas con
-- cantidades, sobre la base de catálogos versionados de la migración 0001.
-- PRECOST ya gestiona presupuestos en localStorage (p3pro.budgets); este
-- esquema es el destino persistente equivalente para la evolución: los
-- presupuestos referencian partidas de catálogo POR VERSIÓN (inmutables)
-- y guardan copias snapshot de los valores usados (para que un cambio de
-- catálogo no altere retrospectivamente un presupuesto cerrado).

-- ----------------------------------------------------------------------------
-- Proyectos
-- ----------------------------------------------------------------------------
CREATE TABLE proyectos (
    id                  INTEGER PRIMARY KEY,
    nombre              TEXT    NOT NULL,
    cliente             TEXT,
    ubicacion           TEXT,
    moneda              TEXT    NOT NULL DEFAULT 'CUP',
    catalogo_version_id INTEGER REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    creado_en           TEXT    NOT NULL DEFAULT (datetime('now')),
    modificado_en       TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- Presupuestos (versiones de presupuesto dentro de un proyecto)
-- ----------------------------------------------------------------------------
CREATE TABLE presupuestos (
    id                  INTEGER PRIMARY KEY,
    proyecto_id         INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE RESTRICT,
    nombre              TEXT    NOT NULL,
    version             INTEGER NOT NULL DEFAULT 1,
    estado              TEXT    NOT NULL DEFAULT 'borrador'
                        CHECK (estado IN ('borrador','emitido','aprobado','cerrado')),
    base_version_id     INTEGER REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    creado_en           TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (proyecto_id, nombre, version)
);

-- ----------------------------------------------------------------------------
-- Capítulos del presupuesto (estructura del documento)
-- ----------------------------------------------------------------------------
CREATE TABLE capitulos_presupuesto (
    id                  INTEGER PRIMARY KEY,
    presupuesto_id      INTEGER NOT NULL REFERENCES presupuestos(id) ON DELETE RESTRICT,
    orden               INTEGER NOT NULL,
    codigo              TEXT,                           -- normalmente el capítulo del catálogo
    descripcion         TEXT    NOT NULL,
    UNIQUE (presupuesto_id, orden)
);

-- ----------------------------------------------------------------------------
-- Partidas presupuestadas (partida de catálogo + cantidad + snapshot)
-- ----------------------------------------------------------------------------
CREATE TABLE partidas_presupuesto (
    id                      INTEGER PRIMARY KEY,
    capitulo_id             INTEGER NOT NULL REFERENCES capitulos_presupuesto(id) ON DELETE RESTRICT,
    partida_catalogo_id     INTEGER REFERENCES partidas(id) ON DELETE RESTRICT,
    codigo                  TEXT    NOT NULL,
    descripcion             TEXT    NOT NULL,
    unidad                  TEXT    NOT NULL,
    cantidad                REAL    NOT NULL CHECK (cantidad >= 0),
    -- snapshot de costos unitarios en el momento de insertar (inmutabilidad)
    costo_unitario_json     TEXT    NOT NULL,
    -- coeficientes de descomposición usados (opcional; para trazabilidad)
    descomposicion_json     TEXT,
    creado_en               TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_pp_capitulo ON partidas_presupuesto(capitulo_id);
CREATE INDEX idx_pp_codigo   ON partidas_presupuesto(codigo);
