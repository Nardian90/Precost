#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MISIÓN III-B · Fase 4 — Importación de tablas SBD2008_815 priorizadas.

Lo invoca scripts/importar_precodi.py (con --base sbd --priorizadas) DENTRO de
la misma transacción reversible. Solo tablas clasificadas en categoría 2 por
scripts/clasificar_sbd.py (docs/datos/sbd_clasificacion.json); las categorías
3 (documental) y 4 (pendiente) NO se importan.

Cada familia verifica sus relaciones CON DATOS REALES contra el núcleo ya
importado (partidas/recursos/colecciones/padres) y registra coincidencias y
huérfanos en stats/advertencias: nada se asume, todo se cuenta.
"""
import json


def _int(v):
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _s(v):
    return str(v).strip() if v is not None else None


def importar_priorizadas(cur, f, ver_id, stats, adv):
    # conjuntos de verificación del núcleo ya importado
    codigos_partida = {c for (c,) in cur.execute(
        "SELECT codigo FROM partidas WHERE version_id=?", (ver_id,))}
    recursos_por_tipo = {}
    for tipo, cod in cur.execute(
            """SELECT (SELECT codigo FROM tipos_recurso WHERE id=r.tipo_id), r.codigo
               FROM recursos r WHERE r.version_id=?""", (ver_id,)):
        recursos_por_tipo.setdefault(tipo, set()).add(cod)
    todos_recursos = set().union(*recursos_por_tipo.values()) if recursos_por_tipo else set()

    _colecciones(cur, f, ver_id, stats, adv)
    _colecciones_composicion(cur, f, ver_id, stats, adv, todos_recursos)
    _colec_rv(cur, f, ver_id, stats, adv, codigos_partida)
    _normas_recurso(cur, f, ver_id, stats, adv)
    _normas_rh_extendida(cur, f, ver_id, stats, adv, codigos_partida, recursos_por_tipo)
    _normas_descriptivas(cur, f, ver_id, stats, adv)
    _tarifas(cur, f, ver_id, stats, adv)
    _duracion_costo(cur, f, ver_id, stats, adv, codigos_partida)
    _actividades(cur, f, ver_id, stats, adv)
    _macros(cur, f, ver_id, stats, adv)
    padres = _padres(cur, f, ver_id, stats, adv)
    _presupuesto_rv(cur, f, ver_id, stats, adv, padres, codigos_partida)
    _presupuesto_recursos(cur, f, ver_id, stats, adv, recursos_por_tipo)


def _contar(cur, stats, t):
    """Cuenta insertadas/duplicadas según el rowcount real del INSERT OR IGNORE."""
    if cur.rowcount and cur.rowcount > 0:
        stats.inc(t, "insertadas")
    else:
        stats.inc(t, "duplicadas_omitidas")


def _colecciones(cur, f, ver_id, stats, adv):
    t = "Colecciones"
    for r in f.filas(t, ["IdColec", "Colec", "Tipo", "Suministrador", "IdColecVieja"]):
        idc = _int(r.get("IdColec"))
        if idc is None or not _s(r.get("Colec")):
            stats.inc(t, "omitidas_invalidas")
            continue
        cur.execute("""INSERT OR IGNORE INTO sbd_colecciones (version_id, id_colec_origen, nombre,
            tipo, suministrador, id_colec_vieja) VALUES (?,?,?,?,?,?)""",
                    (ver_id, idc, _s(r.get("Colec")), _s(r.get("Tipo")),
                     _s(r.get("Suministrador")), _int(r.get("IdColecVieja"))))
        stats.inc(t, "insertadas")


def _colecciones_composicion(cur, f, ver_id, stats, adv, todos_recursos):
    t = "Colecciones Composición"
    ids_colec = {i for (i,) in cur.execute(
        "SELECT id_colec_origen FROM sbd_colecciones WHERE version_id=?", (ver_id,))}
    for r in f.filas(t, ["IdColec", "CodigoRec", "PcMN", "PcMLC", "Activa", "CPO_e", "CPE_e", "CET_e"]):
        idc, cod = _int(r.get("IdColec")), _s(r.get("CodigoRec"))
        if idc is None or not cod:
            stats.inc(t, "omitidas_invalidas")
            continue
        if idc not in ids_colec:
            stats.inc(t, "huérfanas_coleccion")
        if cod not in todos_recursos:
            stats.inc(t, "huérfanas_recurso")
        cur.execute("""INSERT OR IGNORE INTO sbd_colecciones_recursos (version_id, id_colec_origen,
            codigo_recurso, activa, precio_mn, precio_mlc, cpo_e, cpe_e, cet_e)
            VALUES (?,?,?,?,?,?,?,?,?)""",
                    (ver_id, idc, cod, 1 if r.get("Activa") else 0,
                     _r(r.get("PcMN")), _r(r.get("PcMLC")),
                     _r(r.get("CPO_e")), _r(r.get("CPE_e")), _r(r.get("CET_e"))))
        stats.inc(t, "insertadas")


def _r(v):
    """Money (Decimal) → REAL; el resto pasa por a_real."""
    from precision_precodi import a_real, decimal_a_real
    if v is None:
        return None
    if hasattr(v, "as_tuple"):  # Decimal
        return decimal_a_real(v)
    return a_real(v)


def _colec_rv(cur, f, ver_id, stats, adv, codigos_partida):
    t = "ColecRV Composición"
    for r in f.filas(t, ["IdColecRV", "CodigoRV", "Activa_Col", "LopCS_Col", "LopSS_Col",
                         "Salario_MN_SP_Col", "Salario_MLC_SP_Col", "Salario_MN_CP_Col",
                         "Salario_MLC_CP_Col"]):
        idc, cod = _int(r.get("IdColecRV")), _s(r.get("CodigoRV"))
        if idc is None or not cod:
            stats.inc(t, "omitidas_invalidas")
            continue
        if cod not in codigos_partida:
            stats.inc(t, "huérfanas_partida")
        cur.execute("""INSERT OR IGNORE INTO sbd_colec_rv (version_id, id_colec_rv_orig, codigo_rv,
            activa, lop_cs, lop_ss, salario_mn_sp, salario_mlc_sp, salario_mn_cp, salario_mlc_cp)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (ver_id, idc, cod, 1 if r.get("Activa_Col") else 0,
                     _r(r.get("LopCS_Col")), _r(r.get("LopSS_Col")), _r(r.get("Salario_MN_SP_Col")),
                     _r(r.get("Salario_MLC_SP_Col")), _r(r.get("Salario_MN_CP_Col")),
                     _r(r.get("Salario_MLC_CP_Col"))))
        stats.inc(t, "insertadas")


def _normas_recurso(cur, f, ver_id, stats, adv):
    for clase, t in (("RH", "Normas RH"), ("EQ", "Normas Eq")):
        if t not in f.tablas():
            continue
        for r in f.filas(t, ["CodigoNRH" if clase == "RH" else "CodigoNEq", "CodPNorma",
                             "Norma_Descrip", "UM_Normada", "NormaProd", "Norma_Especif",
                             "Norma_Titulo", "UM_RV", "Fact_UM_RV"]):
            cod = _s(r.get("CodigoNRH" if clase == "RH" else "CodigoNEq"))
            if not cod:
                stats.inc(t, "omitidas_invalidas")
                continue
            cur.execute("""INSERT OR IGNORE INTO sbd_normas_recurso (version_id, clase, codigo,
                cod_pnorma, descrip, um_normada, norma_prod, especificacion, titulo, um_rv, fact_um_rv)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (ver_id, clase, cod, _s(r.get("CodPNorma")), _s(r.get("Norma_Descrip")),
                         _s(r.get("UM_Normada")), _r(r.get("NormaProd")), _s(r.get("Norma_Especif")),
                         _s(r.get("Norma_Titulo")), _s(r.get("UM_RV")), _r(r.get("Fact_UM_RV"))))
            stats.inc(t, "insertadas")


def _normas_rh_extendida(cur, f, ver_id, stats, adv, codigos_partida, recursos_por_tipo):
    t = "Normas RH Extendida"
    rh = recursos_por_tipo.get("mano_obra", set())
    for r in f.filas(t, ["TipoEn", "CodigoRV_Ex", "CodSE_Ex", "CodEq_Ex", "CodNS", "CodRHum",
                         "SubRH", "ImpS"]):
        cod_rhum = _s(r.get("CodRHum"))
        if not cod_rhum:
            stats.inc(t, "omitidas_invalidas")
            continue
        cod_rv = _s(r.get("CodigoRV_Ex"))
        if cod_rv and cod_rv not in codigos_partida:
            stats.inc(t, "huérfanas_partida")
        if cod_rhum not in rh:
            stats.inc(t, "huérfanas_recurso")
        cur.execute("""INSERT OR IGNORE INTO sbd_normas_rh_extendida (version_id, tipo_en, codigo_rv,
            cod_se, cod_eq, cod_ns, cod_rhum, sub_rh, imp_s) VALUES (?,?,?,?,?,?,?,?,?)""",
                    (ver_id, _int(r.get("TipoEn")), cod_rv, _s(r.get("CodSE_Ex")),
                     _s(r.get("CodEq_Ex")), _s(r.get("CodNS")), cod_rhum,
                     _s(r.get("SubRH")), _f32(r.get("ImpS"))))
        stats.inc(t, "insertadas")


def _f32(v):
    """Float32: preservar el valor recuperado tal cual (sin redondear)."""
    from precision_precodi import a_real
    return a_real(v)


def _normas_descriptivas(cur, f, ver_id, stats, adv):
    t = "Normas Descriptivas"
    base_cols = ["GrupoN", "CODIGO", "DESCRIPC", "ESPECIFIC", "UMEDIDA", "NORMA_Tiempo", "NORMA_PROD"]
    cuad_cols = [f"{p}_{i}" for i in range(1, 7) for p in ("FT_DESC", "CANTIDAD", "GRUPO")]
    for r in f.filas(t, base_cols + cuad_cols):
        cod = _s(r.get("CODIGO"))
        if not cod:
            stats.inc(t, "omitidas_invalidas")
            continue
        cuadrilla = []
        for i in range(1, 7):
            slot = {"funcion": _s(r.get(f"FT_DESC_{i}")), "cantidad": _s(r.get(f"CANTIDAD_{i}")),
                    "grupo": _s(r.get(f"GRUPO_{i}"))}
            if any(slot.values()):
                cuadrilla.append(slot)
        cur.execute("""INSERT OR IGNORE INTO sbd_normas_descriptivas (version_id, grupo, codigo,
            descripcion, especificacion, umedida, norma_tiempo, norma_prod, cuadrilla_json)
            VALUES (?,?,?,?,?,?,?,?,?)""",
                    (ver_id, _s(r.get("GrupoN")), cod, _s(r.get("DESCRIPC")),
                     _s(r.get("ESPECIFIC")), _s(r.get("UMEDIDA")), _f32(r.get("NORMA_Tiempo")),
                     _f32(r.get("NORMA_PROD")), json.dumps(cuadrilla, ensure_ascii=False)))
        _contar(cur, stats, t)


def _tarifas(cur, f, ver_id, stats, adv):
    t = "Tarifas de T"
    for r in f.filas(t, ["IdOrigDest", "IdServTransp", "Distancia", "Tarifa", "TarifaMLC"]):
        iod, ist, dist = _int(r.get("IdOrigDest")), _int(r.get("IdServTransp")), _int(r.get("Distancia"))
        if iod is None or ist is None or dist is None:
            stats.inc(t, "omitidas_invalidas")
            continue
        cur.execute("""INSERT OR IGNORE INTO sbd_tarifas_transporte (version_id, id_origen_destino,
            id_servicio_transp, distancia, tarifa_mn, tarifa_mlc) VALUES (?,?,?,?,?,?)""",
                    (ver_id, iod, ist, dist, _r(r.get("Tarifa")), _r(r.get("TarifaMLC"))))
        stats.inc(t, "insertadas")

    t = "Tarifas_AD_TD"
    for r in f.filas(t, ["IdTipo_AD_TD", "IdSubServ_AD_TD", "Tarifa_AD_TD_MN", "Tarifa_AD_TD_MLC"]):
        cur.execute("""INSERT OR IGNORE INTO sbd_tarifas_especiales (version_id, clase, id_tipo,
            id_subserv, tarifa_mn, tarifa_mlc) VALUES (?, 'AD_TD', ?,?,?,?)""",
                    (ver_id, _int(r.get("IdTipo_AD_TD")), _int(r.get("IdSubServ_AD_TD")),
                     _r(r.get("Tarifa_AD_TD_MN")), _r(r.get("Tarifa_AD_TD_MLC"))))
        stats.inc(t, "insertadas")

    t = "Tarifas de Demora"
    for r in f.filas(t, ["IdT_Demora", "DescTarifaDemora", "T_Demora_MN", "T_Demora_MLC"]):
        cur.execute("""INSERT OR IGNORE INTO sbd_tarifas_especiales (version_id, clase, id_tipo,
            descripcion, tarifa_mn, tarifa_mlc) VALUES (?, 'demora', ?,?,?,?)""",
                    (ver_id, _int(r.get("IdT_Demora")), _s(r.get("DescTarifaDemora")),
                     _r(r.get("T_Demora_MN")), _r(r.get("T_Demora_MLC"))))
        stats.inc(t, "insertadas")

    t = "Tarifas de Recorrido Vacio"
    for r in f.filas(t, ["DD", "AA", "TarfRecVac", "TarfRecVacMLC"]):
        cur.execute("""INSERT OR IGNORE INTO sbd_tarifas_especiales (version_id, clase, id_tipo,
            id_subserv, tarifa_mn, tarifa_mlc) VALUES (?, 'recorrido_vacio', ?,?,?,?)""",
                    (ver_id, _int(r.get("DD")), _int(r.get("AA")),
                     _r(r.get("TarfRecVac")), _r(r.get("TarfRecVacMLC"))))
        stats.inc(t, "insertadas")


def _duracion_costo(cur, f, ver_id, stats, adv, codigos_partida):
    t = "tc Duración y Costo con Norma Precons MO"
    exactos = prefijo = 0
    for r in f.filas(t, ["CodigoRV", "HorasHombreP", "DuraciónP", "CostoTyNP", "CostoTyNPMN",
                         "CostoTyNPMLC", "CostoTPrecons", "CostoTPreconsMN", "CostoTPreconsMLC"]):
        cod = _s(r.get("CodigoRV"))
        if not cod:
            stats.inc(t, "omitidas_invalidas")
            continue
        if cod in codigos_partida:
            exactos += 1
        elif cod[:6] in codigos_partida:
            prefijo += 1
        else:
            stats.inc(t, "sin_relacion_partida")
        cur.execute("""INSERT OR IGNORE INTO sbd_duracion_costo_rv (version_id, codigo_rv,
            horas_hombre_p, duracion_p, costo_tynp, costo_tynp_mn, costo_tynp_mlc,
            costo_tprecons, costo_tprecons_mn, costo_tprecons_mlc) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (ver_id, cod, _r(r.get("HorasHombreP")), _r(r.get("DuraciónP")),
                     _r(r.get("CostoTyNP")), _r(r.get("CostoTyNPMN")), _r(r.get("CostoTyNPMLC")),
                     _r(r.get("CostoTPrecons")), _r(r.get("CostoTPreconsMN")),
                     _r(r.get("CostoTPreconsMLC"))))
        stats.inc(t, "insertadas")
    stats.fijar_extra(t, {"codigo_partida_exacto": exactos, "codigo_prefijo6_partida": prefijo})
    if exactos + prefijo == 0:
        adv.append(f"{t}: ningún código coincide con partidas (sistema de códigos propio, "
                   f"pendiente de interpretación — datos preservados)")


def _actividades(cur, f, ver_id, stats, adv):
    t = "Actividades de Estimación"
    for r in f.filas(t, ["CodGActEst", "ActEst", "UMEst", "PrecEst", "PrecEstMLC",
                         "TPesimista", "TEsperado", "TOptimista"]):
        cod = _s(r.get("CodGActEst"))
        if not cod:
            stats.inc(t, "omitidas_invalidas")
            continue
        cur.execute("""INSERT OR IGNORE INTO sbd_actividades_estimacion (version_id, cod_g_actest,
            descripcion, um, precio_est, precio_est_mlc, t_pesimista, t_esperado, t_optimista)
            VALUES (?,?,?,?,?,?,?,?,?)""",
                    (ver_id, cod, _s(r.get("ActEst")), _s(r.get("UMEst")),
                     _f32(r.get("PrecEst")), _f32(r.get("PrecEstMLC")),
                     _r(r.get("TPesimista")), _r(r.get("TEsperado")), _r(r.get("TOptimista"))))
        _contar(cur, stats, t)


def _macros(cur, f, ver_id, stats, adv):
    t = "Macros Composicion RV"
    for r in f.filas(t, ["CodMacro", "CODIGO RV", "CantRV", "ConSum", "ConRH", "ConEqu",
                         "Coef_Complegidad_RVM", "RVPrincipal", "EtiquetaMacro"]):
        cm, crv = _s(r.get("CodMacro")), _s(r.get("CODIGO RV"))
        if not cm or not crv:
            stats.inc(t, "omitidas_invalidas")
            continue
        cur.execute("""INSERT OR IGNORE INTO sbd_macros_rv (version_id, cod_macro, codigo_rv,
            cantidad, con_sum, con_rh, con_equipo, coef_complejidad, rv_principal, etiqueta)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (ver_id, cm, crv, _r(r.get("CantRV")), 1 if r.get("ConSum") else 0,
                     1 if r.get("ConRH") else 0, 1 if r.get("ConEqu") else 0,
                     _r(r.get("Coef_Complegidad_RVM")), 1 if r.get("RVPrincipal") else 0,
                     _s(r.get("EtiquetaMacro"))))
        stats.inc(t, "insertadas")


def _padres(cur, f, ver_id, stats, adv):
    """Obras, Objetos de Obra y Etapas (importación mínima documental)."""
    t = "Obras"
    for r in f.filas(t, ["IdObra", "CodObra", "Obra"]):
        cur.execute("""INSERT OR IGNORE INTO sbd_obras (version_id, id_origen, cod_obra, obra)
            VALUES (?,?,?,?)""", (ver_id, _int(r.get("IdObra")), _s(r.get("CodObra")), _s(r.get("Obra"))))
        stats.inc(t, "insertadas")

    t = "Objetos de Obra"
    ids_obj = set()
    for r in f.filas(t, ["IdObjObra", "IdObra", "CodObj", "ObjObra", "Nivel"]):
        idobj = _int(r.get("IdObjObra"))
        if idobj is None:
            stats.inc(t, "omitidas_invalidas")
            continue
        ids_obj.add(idobj)
        cur.execute("""INSERT OR IGNORE INTO sbd_objetos_obra (version_id, id_origen, id_obra,
            cod_obj, obj_obra, nivel) VALUES (?,?,?,?,?,?)""",
                    (ver_id, idobj, _int(r.get("IdObra")), _s(r.get("CodObj")),
                     _s(r.get("ObjObra")), _int(r.get("Nivel"))))
        stats.inc(t, "insertadas")
    # clave verificada con datos: Presupuesto Composición RV.IdObjObra → Objetos de
    # Obra.IdObjObra coincide 16816/16816 (la PK declarada (IdObra, CodObj) es compuesta,
    # pero el JOIN real de los presupuestos usa la columna autonumérica IdObjObra)

    t = "Etapas"
    ids_etapa = set()
    for r in f.filas(t, ["IdEtapa", "CodEtapa", "Etapa"]):
        ide = _int(r.get("IdEtapa"))
        if ide is None:
            stats.inc(t, "omitidas_invalidas")
            continue
        ids_etapa.add(ide)
        cur.execute("""INSERT OR IGNORE INTO sbd_etapas (version_id, id_origen, cod_etapa, etapa)
            VALUES (?,?,?,?)""", (ver_id, ide, _s(r.get("CodEtapa")), _s(r.get("Etapa"))))
        stats.inc(t, "insertadas")
    return {"ids_obj_obra": ids_obj, "ids_etapa": ids_etapa}


def _presupuesto_rv(cur, f, ver_id, stats, adv, padres, codigos_partida):
    t = "Presupuesto Composición RV"
    ids_prv = set()
    match_obj = match_eta = match_rv = 0
    for r in f.filas(t, ["IdPRV", "IdObjObra", "IdEtapa", "CODIGO RV", "TipoPres", "TipoA", "CantRV",
                         "ConSum", "ConRH", "ConEq", "FechaInicio", "FechaFinal", "PLCSMN", "PLCSMLC",
                         "PLSSMN", "PLSSMLC", "HHombre", "HEquipo", "Dura", "CodBloque",
                         "DescBloque", "ObcervaRV"]):
        idprv = _int(r.get("IdPRV"))
        if idprv is None:
            stats.inc(t, "omitidas_invalidas")
            continue
        idobj, ideta = _int(r.get("IdObjObra")), _int(r.get("IdEtapa"))
        crv = _s(r.get("CODIGO RV"))
        if idobj in padres["ids_obj_obra"]:
            match_obj += 1
        if ideta in padres["ids_etapa"]:
            match_eta += 1
        if crv in codigos_partida:
            match_rv += 1
        ids_prv.add(idprv)
        cur.execute("""INSERT OR IGNORE INTO sbd_presupuesto_rv (version_id, id_prv_origen,
            id_obj_obra, id_etapa, codigo_rv, tipo_pres, tipo_a, cantidad, con_sum, con_rh,
            con_equipo, fecha_inicio, fecha_final, plcsmn, plcsmlc, plssmn, plssmlc, h_hombre,
            h_equipo, duracion, cod_bloque, desc_bloque, observacion)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (ver_id, idprv, idobj, ideta, crv, _s(r.get("TipoPres")), _s(r.get("TipoA")),
                     _r(r.get("CantRV")), 1 if r.get("ConSum") else 0, 1 if r.get("ConRH") else 0,
                     1 if r.get("ConEq") else 0, _fecha(r.get("FechaInicio")), _fecha(r.get("FechaFinal")),
                     _r(r.get("PLCSMN")), _r(r.get("PLCSMLC")), _r(r.get("PLSSMN")), _r(r.get("PLSSMLC")),
                     _r(r.get("HHombre")), _r(r.get("HEquipo")), _r(r.get("Dura")),
                     _s(r.get("CodBloque")), _s(r.get("DescBloque")), _s(r.get("ObcervaRV"))))
        stats.inc(t, "insertadas")
    stats.fijar_extra(t, {"id_obj_obra_en_objetos": match_obj, "id_etapa_en_etapas": match_eta,
                          "codigo_rv_en_partidas": match_rv})
    return ids_prv


def _fecha(v):
    s = _s(v)
    return s[:10] if s else None


def _presupuesto_recursos(cur, f, ver_id, stats, adv, recursos_por_tipo):
    fam = [("material", "Presupuesto Composición Mat", "CodRc", "CantRc",
            ["IdPRV", "CodRc", "CantRc", "PsMN", "PsMLC", "Usos", "Modificado", "Cod_SE_J"]),
           ("mano_obra", "Presupuesto Composición RH", "CodRHum", "CantRHum",
            ["IdPRV", "CodRHum", "CantRHum", "PsMN", "PsMLC", "Usos", "Elab", "Modificado",
             "CodNorma", "HCPO_s", "Cod_SE_J"]),
           ("equipo", "Presupuesto Composición Equipo", "CodEquipo", "CantEquipo",
            ["IdPRV", "CodEquipo", "CantEquipo", "PsMN", "PsMLC", "Usos", "Elab", "Modificado",
             "CodNorma", "CPO_s", "CPE_s", "CET_s", "Cod_SE_J"]),
           ("semielaborado", "Presupuesto Composición SE", "CodSemi", "CantSE",
            ["IdPRV", "CodSemi", "CantSE", "PsMN", "PsMLC", "Usos", "Modificado"])]
    ids_prv = {i for (i,) in cur.execute(
        "SELECT id_prv_origen FROM sbd_presupuesto_rv WHERE version_id=?", (ver_id,))}
    for tipo_defecto, t, col_cod, col_cant, cols in fam:
        insertadas = huerf_prv = huerf_rec = reclasificadas = 0
        for r in f.filas(t, cols):
            idprv, cod = _int(r.get("IdPRV")), _s(r.get(col_cod))
            if idprv is None or not cod:
                stats.inc(t, "omitidas_invalidas")
                continue
            if idprv not in ids_prv:
                huerf_prv += 1
            tipo = tipo_defecto
            if cod not in recursos_por_tipo.get(tipo, set()):
                # reclasificación dirigida por DATOS: ¿el código pertenece a otro nomenclador?
                for otro in ("material", "semielaborado", "juego", "mano_obra", "equipo"):
                    if cod in recursos_por_tipo.get(otro, set()):
                        tipo = otro
                        reclasificadas += 1
                        break
                else:
                    huerf_rec += 1
            cur.execute("""INSERT OR IGNORE INTO sbd_presupuesto_recursos (version_id, id_prv_origen,
                tipo_recurso, codigo_recurso, cantidad, precio_mn, precio_mlc, usos, elaborada,
                modificado, cod_se_j, cod_norma, hcpo_s, cpo_s, cpe_s, cet_s)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (ver_id, idprv, tipo, cod, _r(r.get(col_cant)), _r(r.get("PsMN")),
                         _r(r.get("PsMLC")), _r(r.get("Usos")),
                         1 if r.get("Elab") else 0, 1 if r.get("Modificado") else 0,
                         _s(r.get("Cod_SE_J")), _s(r.get("CodNorma")), _r(r.get("HCPO_s")),
                         _r(r.get("CPO_s")), _r(r.get("CPE_s")), _r(r.get("CET_s"))))
            insertadas += 1
        stats.fijar_extra(t, {"insertadas": insertadas, "huérfanas_idprv": huerf_prv,
                              "huérfanas_recurso": huerf_rec, "reclasificadas_por_datos": reclasificadas})
        if huerf_rec:
            adv.append(f"{t}: {huerf_rec} recursos con código ausente en los nomencladores "
                       f"importados (filas preservadas con su código; ver docs/DICCIONARIO_PRECODI.md)")
