-- ============================================================================
-- Migración 0003 — Fidelidad PRECODI + entidades SBD priorizadas (MISIÓN III-B)
-- ============================================================================
-- PARTE A: columnas de fidelidad de origen en `partidas` (migración 0001).
--   La fase III-C verificó el modelo de precios; estas columnas preservan
--   datos de origen que el esquema 0001 no recogía y que las fórmulas
--   PENDIENTES (HORAS OPERARIO/AYUDANTE) necesitarán. No se duplican tablas:
--   se AMPLÍAN las existentes.
--
-- PARTE B: tablas de SBD2008_815 clasificadas en categoría 2 (integrables
--   mediante transformación) por scripts/clasificar_sbd.py. Prefijo `sbd_`
--   para separarlas del núcleo común. Todas llevan version_id → procedencia
--   completa. Las transformaciones están documentadas en
--   docs/DICCIONARIO_PRECODI.md §SBD y docs/MODELO_RELACIONAL.md.

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- PARTE A · Fidelidad de `partidas`
-- ----------------------------------------------------------------------------
ALTER TABLE partidas ADD COLUMN chmlc REAL;            -- CHMLC (costo MO en MLC)
ALTER TABLE partidas ADD COLUMN cemlc REAL;            -- CEMLC (costo equipos en MLC)
ALTER TABLE partidas ADD COLUMN horas_operario REAL;   -- HORAS OPERARIO (fórmula PENDIENTE fase III-C)
ALTER TABLE partidas ADD COLUMN horas_ayudante REAL;   -- HORAS AYUDANTE (fórmula PENDIENTE fase III-C)
ALTER TABLE partidas ADD COLUMN tipo_rv TEXT;          -- TIPO
ALTER TABLE partidas ADD COLUMN desc_corta TEXT;       -- DescCorta

-- ----------------------------------------------------------------------------
-- PARTE B · SBD — colecciones de precios y composiciones
-- ----------------------------------------------------------------------------
-- Cabeceras de colecciones (transformación: IdColec→id_colec_origen)
CREATE TABLE sbd_colecciones (
    id              INTEGER PRIMARY KEY,
    version_id      INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    id_colec_origen INTEGER NOT NULL,
    nombre          TEXT    NOT NULL,                  -- Colec
    tipo            TEXT,                              -- Tipo
    suministrador   TEXT,                              -- Suministrador
    id_colec_vieja  INTEGER,
    UNIQUE (version_id, id_colec_origen)
);

-- Recursos con precio por colección (Colecciones Composición)
CREATE TABLE sbd_colecciones_recursos (
    id              INTEGER PRIMARY KEY,
    version_id      INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    id_colec_origen INTEGER NOT NULL,
    codigo_recurso  TEXT    NOT NULL,                  -- CodigoRec (10 dígitos)
    activa          INTEGER,                           -- Activa (Sí/No → 1/0)
    precio_mn       REAL,                              -- PcMN (Money 4 dec)
    precio_mlc      REAL,                              -- PcMLC
    cpo_e           REAL, cpe_e REAL, cet_e REAL,
    UNIQUE (version_id, id_colec_origen, codigo_recurso)
);
CREATE INDEX idx_sbd_colrec_cod ON sbd_colecciones_recursos(version_id, codigo_recurso);

-- Variantes salariales por partida y colección (ColecRV Composición, 92 054 filas)
CREATE TABLE sbd_colec_rv (
    id               INTEGER PRIMARY KEY,
    version_id       INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    id_colec_rv_orig INTEGER NOT NULL,                 -- IdColecRV
    codigo_rv        TEXT    NOT NULL,
    activa           INTEGER,
    lop_cs           REAL,                             -- LopCS_Col
    lop_ss           REAL,                             -- LopSS_Col
    salario_mn_sp    REAL, salario_mlc_sp REAL,        -- Salario_MN/MLC_SP_Col
    salario_mn_cp    REAL, salario_mlc_cp REAL,        -- Salario_MN/MLC_CP_Col
    UNIQUE (version_id, id_colec_rv_orig, codigo_rv)
);
CREATE INDEX idx_sbd_colecrv_rv ON sbd_colec_rv(version_id, codigo_rv);

-- ----------------------------------------------------------------------------
-- PARTE B · SBD — normas RH/EQ (variante) y su versión extendida
-- ----------------------------------------------------------------------------
-- Biblioteca de normas de recurso (Normas RH 9 699 + Normas Eq 194, misma estructura)
CREATE TABLE sbd_normas_recurso (
    id          INTEGER PRIMARY KEY,
    version_id  INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    clase       TEXT    NOT NULL CHECK (clase IN ('RH','EQ')),
    codigo      TEXT    NOT NULL,                      -- CodigoNRH / CodigoNEq
    cod_pnorma  TEXT,                                  -- CodPNorma
    descrip     TEXT,                                  -- Norma_Descrip
    um_normada  TEXT,                                  -- UM_Normada
    norma_prod  REAL,                                  -- NormaProd (Money 4 dec)
    especificacion TEXT,                               -- Norma_Especif (Memo)
    titulo      TEXT,                                  -- Norma_Titulo
    um_rv       TEXT,                                  -- UM_RV
    fact_um_rv  REAL,                                  -- Fact_UM_RV (Money 4 dec)
    UNIQUE (version_id, clase, codigo)
);

-- Normas RH Extendida (57 838): descomposición extendida RV→RH
--   ImpS es Float32: se preserva el valor recuperado (ver precisión §Fase 3)
CREATE TABLE sbd_normas_rh_extendida (
    id          INTEGER PRIMARY KEY,
    version_id  INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    tipo_en     INTEGER,                               -- TipoEn
    codigo_rv   TEXT,                                  -- CodigoRV_Ex
    cod_se      TEXT,                                  -- CodSE_Ex
    cod_eq      TEXT,                                  -- CodEq_Ex
    cod_ns      TEXT,                                  -- CodNS
    cod_rhum    TEXT,                                  -- CodRHum
    sub_rh      TEXT,                                  -- SubRH
    imp_s       REAL,                                  -- ImpS (Float32 preservado)
    UNIQUE (version_id, tipo_en, codigo_rv, cod_ns, cod_rhum, cod_se, cod_eq)
);
CREATE INDEX idx_sbd_nrhe_rv ON sbd_normas_rh_extendida(version_id, codigo_rv);

-- ----------------------------------------------------------------------------
-- PARTE B · SBD — normas descriptivas
-- ----------------------------------------------------------------------------
CREATE TABLE sbd_normas_descriptivas (
    id              INTEGER PRIMARY KEY,
    version_id      INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    grupo           TEXT,                              -- GrupoN
    codigo          TEXT    NOT NULL,                  -- CODIGO
    descripcion     TEXT,                              -- DESCRIPC
    especificacion  TEXT,                              -- ESPECIFIC (Memo)
    umedida         TEXT,                              -- UMEDIDA
    norma_tiempo    REAL,                              -- NORMA_Tiempo
    norma_prod      REAL,                              -- NORMA_PROD
    cuadrilla_json  TEXT,                              -- FT_DESC_1..6/CANTIDAD_1..6/GRUPO_1..6
    -- La tabla fuente NO tiene PK y contiene variantes con mismo (grupo, codigo)
    -- y distinto tiempo de norma (verificado: 4 variantes de 120027): la unicidad
    -- es por CONTENIDO para conservar todas las variantes
    UNIQUE (version_id, grupo, codigo, descripcion, norma_tiempo, norma_prod)
);

-- ----------------------------------------------------------------------------
-- PARTE B · SBD — tarifas (variantes de tarifas de transporte)
-- ----------------------------------------------------------------------------
CREATE TABLE sbd_tarifas_transporte (
    id                  INTEGER PRIMARY KEY,
    version_id          INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    id_origen_destino   INTEGER NOT NULL,              -- IdOrigDest
    id_servicio_transp  INTEGER NOT NULL,              -- IdServTransp
    distancia           INTEGER NOT NULL,              -- Distancia
    tarifa_mn           REAL,                          -- Tarifa (Money 4 dec)
    tarifa_mlc          REAL,                          -- TarifaMLC
    UNIQUE (version_id, id_origen_destino, id_servicio_transp, distancia)
);

-- Tarifas_AD_TD + Tarifas de Demora + Tarifas de Recorrido Vacío (unificadas por clase)
CREATE TABLE sbd_tarifas_especiales (
    id          INTEGER PRIMARY KEY,
    version_id  INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    clase       TEXT    NOT NULL CHECK (clase IN ('AD_TD','demora','recorrido_vacio')),
    id_tipo     INTEGER,                               -- IdTipo_AD_TD / IdT_Demora
    id_subserv  INTEGER,                               -- IdSubServ_AD_TD
    descripcion TEXT,                                  -- DescTarifaDemora
    tarifa_mn   REAL,
    tarifa_mlc  REAL,
    UNIQUE (version_id, clase, id_tipo, id_subserv, descripcion)
);

-- ----------------------------------------------------------------------------
-- PARTE B · SBD — duración y costo
-- ----------------------------------------------------------------------------
CREATE TABLE sbd_duracion_costo_rv (
    id                INTEGER PRIMARY KEY,
    version_id        INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    codigo_rv         TEXT    NOT NULL,                -- CodigoRV (8 dígitos en esta tabla)
    horas_hombre_p    REAL,                            -- HorasHombreP (Money 4 dec)
    duracion_p        REAL,                            -- DuraciónP
    costo_tynp        REAL, costo_tynp_mn REAL, costo_tynp_mlc REAL,
    costo_tprecons    REAL, costo_tprecons_mn REAL, costo_tprecons_mlc REAL,
    UNIQUE (version_id, codigo_rv)
);

CREATE TABLE sbd_actividades_estimacion (
    id              INTEGER PRIMARY KEY,
    version_id      INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    cod_g_actest    TEXT    NOT NULL,                  -- CodGActEst (código de GRUPO: 48 grupos)
    descripcion     TEXT,                              -- ActEst (PK fuente = (CodGActEst, ActEst))
    um              TEXT,                              -- UMEst
    precio_est      REAL,                              -- PrecEst
    precio_est_mlc  REAL,                              -- PrecEstMLC
    t_pesimista     REAL, t_esperado REAL, t_optimista REAL,   -- Money 4 dec
    UNIQUE (version_id, cod_g_actest, descripcion)
);

-- ----------------------------------------------------------------------------
-- PARTE B · SBD — macros de RV
-- ----------------------------------------------------------------------------
CREATE TABLE sbd_macros_rv (
    id               INTEGER PRIMARY KEY,
    version_id       INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    cod_macro        TEXT    NOT NULL,                 -- CodMacro
    codigo_rv        TEXT    NOT NULL,                 -- CODIGO RV
    cantidad         REAL,                             -- CantRV
    con_sum          INTEGER, con_rh INTEGER, con_equipo INTEGER,
    coef_complejidad REAL,                             -- Coef_Complegidad_RVM
    rv_principal     INTEGER,
    etiqueta         TEXT,                             -- EtiquetaMacro
    UNIQUE (version_id, cod_macro, codigo_rv)
);

-- ----------------------------------------------------------------------------
-- PARTE B · SBD — composiciones presupuestarias existentes + padres mínimos
-- ----------------------------------------------------------------------------
-- Padres mínimos (importación documental: el resto de columnas queda en la
-- base SBD original, documentado en sbd_clasificacion.json)
CREATE TABLE sbd_obras (
    id          INTEGER PRIMARY KEY,
    version_id  INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    id_origen   INTEGER NOT NULL,                      -- IdObra
    cod_obra    TEXT,                                  -- CodObra
    obra        TEXT,                                  -- Obra (nombre)
    UNIQUE (version_id, id_origen)
);

CREATE TABLE sbd_objetos_obra (
    id          INTEGER PRIMARY KEY,
    version_id  INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    id_origen   INTEGER NOT NULL,                      -- clave de Objetos de Obra referida por IdObjObra
    id_obra     INTEGER,                               -- IdObra (FK a Obras)
    cod_obj     TEXT,                                  -- CodObj
    obj_obra    TEXT,                                  -- ObjObra (nombre)
    nivel       INTEGER,                               -- Nivel
    UNIQUE (version_id, id_origen)
);

CREATE TABLE sbd_etapas (
    id          INTEGER PRIMARY KEY,
    version_id  INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    id_origen   INTEGER NOT NULL,                      -- IdEtapa
    cod_etapa   TEXT,                                  -- CodEtapa
    etapa       TEXT,                                  -- Etapa (nombre)
    UNIQUE (version_id, id_origen)
);

-- Partidas presupuestadas existentes (Presupuesto Composición RV, 48 columnas
-- originales → esenciales documentadas; el resto queda en la base SBD)
CREATE TABLE sbd_presupuesto_rv (
    id              INTEGER PRIMARY KEY,
    version_id      INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    id_prv_origen   INTEGER NOT NULL,                  -- IdPRV
    id_obj_obra     INTEGER,                           -- IdObjObra (→ sbd_objetos_obra)
    id_etapa        INTEGER,                           -- IdEtapa (→ sbd_etapas)
    codigo_rv       TEXT,                              -- CODIGO RV (→ partidas)
    tipo_pres       TEXT, tipo_a TEXT,                 -- TipoPres, TipoA
    cantidad        REAL,                              -- CantRV (Money 4 dec)
    con_sum         INTEGER, con_rh INTEGER, con_equipo INTEGER,
    fecha_inicio    TEXT, fecha_final TEXT,
    plcsmn REAL, plcsmlc REAL, plssmn REAL, plssmlc REAL,   -- salarios plan
    h_hombre REAL, h_equipo REAL, duracion REAL,
    cod_bloque TEXT, desc_bloque TEXT, observacion TEXT,
    UNIQUE (version_id, id_prv_origen)
);
CREATE INDEX idx_sbd_prv_obj ON sbd_presupuesto_rv(version_id, id_obj_obra);

-- Recursos de las partidas presupuestadas (Mat + RH + Equipo + SE unificadas)
CREATE TABLE sbd_presupuesto_recursos (
    id              INTEGER PRIMARY KEY,
    version_id      INTEGER NOT NULL REFERENCES versiones_catalogo(id) ON DELETE RESTRICT,
    id_prv_origen   INTEGER NOT NULL,                  -- IdPRV (→ sbd_presupuesto_rv)
    tipo_recurso    TEXT    NOT NULL CHECK (tipo_recurso IN ('material','mano_obra','equipo','semielaborado')),
    codigo_recurso  TEXT    NOT NULL,                  -- CodRc/CodRHum/CodEquipo/CodSemi
    cantidad        REAL,                              -- CantRc/... (Money 4 dec)
    precio_mn       REAL, precio_mlc REAL,             -- PsMN/PsMLC
    usos            REAL,
    elaborada       INTEGER, modificado INTEGER,
    cod_se_j        TEXT, cod_norma TEXT,
    hcpo_s REAL, cpo_s REAL, cpe_s REAL, cet_s REAL,   -- específicos RH/Equipo
    UNIQUE (version_id, id_prv_origen, tipo_recurso, codigo_recurso)
);
CREATE INDEX idx_sbd_prr_prv ON sbd_presupuesto_recursos(version_id, id_prv_origen);
