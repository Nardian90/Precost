#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MISIÓN III-B · Fases 2-3 — Importador común PRECODI → SQLite.

Importa las variantes de codigo.mdb (7.21, 7.22, raíz 2017, Preambulos), el
catálogo embebido de PRECOST 2025 (extracto verificado fase III-D) y —con
--base sbd --priorizadas— el núcleo y las tablas priorizadas de SBD2008_815.

Garantías de la misión:
  * Inspecciona el esquema ANTES de importar y se adapta a las diferencias
    (tablas y columnas opcionales; SBD sin CodSobreG/CodG en RV → capítulo
    derivado del prefijo del código, verificado contra grupos).
  * Mapa explícito tablas → entidades (NUCLEO / NORMAS / COMPONENTES).
  * Orden: grupos → nomencladores (recursos) → partidas → normas →
    componentes (los nomencladores ANTES que las normas que los referencian).
  * Preserva códigos, descripciones, unidades (con factor), identificadores
    de origen y relaciones; precisión Money 4 decimales EXACTA y Float32
    preservado (scripts/precision_precodi.py).
  * Detecta códigos duplicados, claves huérfanas, unidades vacías y
    conflictos de coeficiente; archivos duplicados por SHA-256 (Preambulos ≡
    7.21 → versión de referencia con 0 filas propias).
  * Idempotente: reimportar no duplica registros (versión + hash idénticos →
    salta; intento previo fallido → lo purga y reintenta limpio).
  * Transacción única por versión: error → ROLLBACK completo (reversible),
    registrado como importación con resultado 'error'.
  * Registra versión, hash de origen, fecha, filas por tabla, advertencias y
    resultado en las tablas 0001 (versiones_catalogo / importaciones).

Uso:
  python3 scripts/importar_precodi.py --base 721   [--bd bd/precodi.db]
  python3 scripts/importar_precodi.py --todas          # 721,722,raiz,preambulos,precost2025
  python3 scripts/importar_precodi.py --base sbd --priorizadas
  python3 scripts/importar_precodi.py --informe        # docs/datos/iiib_importaciones.json
"""
import argparse
import hashlib
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from precision_precodi import (a_real, cargar_tipos_inventario, decimal_a_real,  # noqa: E402
                               money_a_decimal, parchear_jet3_textos, parchear_money_exacto)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE_BASE = "/home/z/my-project/work/recuperacion/analisis/PRECODI"
HTML = os.path.join(REPO, "app", "PRECOST-v9.17.html")
EXTRACTO_PRECOST = os.path.join(REPO, "docs", "datos", "fase3d_precost_db.json")
BD_DEFECTO = os.path.join(REPO, "bd", "precodi.db")
SHA_HTML = "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"

BASES = {
    "721": {"archivo": "Codigo (PRECODI)/7.21/codigo.mdb", "catalogo": "PRECODI",
            "version": "2007-v7.21", "etiqueta": "codigo.mdb v7.21 (Jet 3, carpeta 7.21)",
            "inventario_id": "codigo_721"},
    "722": {"archivo": "Codigo (PRECODI)/7.22/codigo.mdb", "catalogo": "PRECODI",
            "version": "2007-v7.22", "etiqueta": "codigo.mdb v7.22 (Jet 4, carpeta 7.22)",
            "inventario_id": "codigo_722"},
    "raiz": {"archivo": "Codigo (PRECODI)/codigo.mdb", "catalogo": "PRECODI",
             "version": "2017-raiz", "etiqueta": "codigo.mdb raíz 2017 (canónico, junto a Codigo.exe)",
             "inventario_id": "codigo_raiz"},
    "preambulos": {"archivo": "Codigo (PRECODI)/Preambulos/codigo.mdb", "catalogo": "PRECODI",
                   "version": "2007-v7.21-Preambulos", "etiqueta": "codigo.mdb carpeta Preambulos",
                   "inventario_id": "codigo_preambulos", "secundaria": True},
    "sbd": {"archivo": "Codigo (PRECODI)/8.15/SBD2008_815.mdb", "catalogo": "PRECODI",
            "version": "2011-sbd2008", "etiqueta": "SBD2008_815.mdb (base empresarial, núcleo PRECODI ampliado)",
            "inventario_id": "sbd2008_815"},
    "precost2025": {"archivo": None, "json": EXTRACTO_PRECOST, "catalogo": "PRECONS_III",
                    "version": "2025-06-06", "etiqueta": "PRECONS III MICONS 2025 (const DB de PRECOST v9.17)",
                    "inventario_id": None},
}

# --- Mapa explícito del núcleo (columnas opcionales resueltas dinámicamente) ---
GRUPOS_MAP = [
    ("Nomenclador de SobreGrupos RV", 1, "CodSobreG", None, "SubreGrupo"),
    ("Nomenclador de Grupos RV", 2, "CodG", "CodSobreG", "Grupo"),
    ("Nomenclador de SubGrupos RV", 3, "CodSubG", "CodG", "SubGrupo"),
]
NOMENCLADORES = {  # tipo → (tabla, col_codigo, col_desc)
    "material": ("Nomenclador de Materiales", "CodMat", "Material"),
    "mano_obra": ("Nomenclador de Mano de Obra", "CodRHum", "RHum"),
    "equipo": ("Nomenclador de Equipos", "CodEquipo", "Equipo"),
    "juego": ("Nomenclador de Juegos", "CodJuego", "Juego"),
    "semielaborado": ("Nomenclador de Semielaborados", "CodSElab", "SElab"),
}
NORMAS = [  # (tipo, tabla, col_recurso, col_coef, col_cod_norma)
    ("material", "Norma de Materiales", "CodMat", "CantMat", None),
    ("mano_obra", "Norma de Mano de Obra", "CodRHum", "CantRHum", "CodNorma"),
    ("equipo", "Norma de Equipos", "CodEquipo", "CantEquipo", "CodNorma"),
    ("juego", "Norma de Juegos", "CodJuego", "CantJuego", None),
    ("semielaborado", "Norma de Semielaborados", "CodSElab", "CantSElab", None),
]
COMPONENTES = [  # (tipo_recurso, tabla, col_recurso, tipo_componente, col_componente, col_coef, col_cod_norma)
    ("juego", "Norma Juego Material", "CodJuego", "material", "CodMat", "CantMatJ", None),
    ("semielaborado", "Norma Semi Material", "CodSemi", "material", "CodMat", "CantMatSE", None),
    ("semielaborado", "Norma Semi RHumanos", "CodSemi", "mano_obra", "CodRHum", "CantRHumSE", "CodNorma"),
    ("semielaborado", "Norma Semi Equipos", "CodSemi", "equipo", "CodEquipo", "CantEquipoSE", None),
]


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def norm_um(s):
    """unidad → (unidad_normalizada, factor) para '100 m2' etc."""
    if s is None:
        return "", 1.0
    s = str(s).strip()
    m = re.match(r"^([\d.,]+)\s+(.+)$", s)
    if m:
        try:
            return m.group(2).strip().lower(), float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    return s.lower(), 1.0


class FuenteMdb:
    """Acceso solo-lectura a un .mdb con conversión por tipo Jet verificado."""

    def __init__(self, ruta, inventario_id):
        parchear_money_exacto()
        parchear_jet3_textos()
        logging.getLogger("access_parser").setLevel(logging.CRITICAL)
        from access_parser import AccessParser
        self.ruta = ruta
        self.db = AccessParser(ruta)
        ruta_inv = os.path.join(REPO, "docs", "datos", "fase3a_inventario.json")
        self.tipos = cargar_tipos_inventario(ruta_inv, inventario_id)
        self._cache = {}

    def tablas(self):
        return [n for n in self.db.catalog if not n.startswith("MSys")]

    def parse(self, tabla):
        if tabla not in self._cache:
            self._cache[tabla] = self.db.parse_table(tabla)
        return self._cache[tabla]

    def tiene(self, tabla, columna):
        return columna in self.parse(tabla)

    def col(self, tabla, columna):
        datos = self.parse(tabla)
        if columna not in datos or datos[columna] is None:
            return []
        crudo = datos[columna]
        kind = self.tipos.get((tabla, columna))
        if kind == "money":
            return [money_a_decimal(v) for v in crudo]
        if kind in ("real32", "real64"):
            return [a_real(v) for v in crudo]
        if kind == "entero":
            return [v if (v is None or isinstance(v, int)) else a_real(v) for v in crudo]
        return list(crudo)

    def filas(self, tabla, columnas):
        datos = self.parse(tabla)
        cols = {c: self.col(tabla, c) for c in columnas if c in datos}
        if not cols:
            return []
        n = min(len(v) for v in cols.values())
        return [{c: cols[c][i] for c in cols} for i in range(n)]


# ----------------------------------------------------------------------------
# Núcleo PRECODI
# ----------------------------------------------------------------------------

def importar_grupos(cur, f, cat_id, stats, adv):
    for tabla, nivel, col_cod, col_padre, col_desc in GRUPOS_MAP:
        if tabla not in f.tablas():
            adv.append(f"{tabla}: ausente en esta base (nivel {nivel} no importado)")
            continue
        vistos = {}
        duplicados = 0
        for r in f.filas(tabla, [c for c in (col_cod, col_padre, col_desc) if c]):
            cod = str(r.get(col_cod) or "").strip()
            desc = str(r.get(col_desc) or "").strip()
            padre = str(r.get(col_padre) or "").strip() if col_padre else None
            if not cod:
                stats.inc(tabla, "omitidas_invalidas")
                continue
            if cod in vistos:
                duplicados += 1
                if vistos[cod] != (desc, padre):
                    adv.append(f"{tabla}: código duplicado {cod!r} con contenido distinto "
                               f"(se conserva la primera aparición)")
                stats.inc(tabla, "duplicadas_omitidas")
                continue
            vistos[cod] = (desc, padre)
            existe = cur.execute("SELECT descripcion FROM grupos WHERE catalogo_id=? AND nivel=? AND codigo=?",
                                 (cat_id, nivel, cod)).fetchone()
            if existe:
                # el grupo ya existe (otra versión del mismo catálogo ya importada)
                stats.inc(tabla, "ya_existentes")
                if (existe[0] or "") != desc:
                    stats.inc(tabla, "conflictos_descripcion_entre_versiones")
                    adv_ejemplo(stats, adv, tabla,
                                f"grupo {cod!r} con descripción distinta a la de otra versión "
                                f"(se conserva la primera: {existe[0]!r} ≠ {desc!r})")
                continue
            cur.execute("INSERT INTO grupos (catalogo_id, nivel, codigo, padre_codigo, descripcion)"
                        " VALUES (?,?,?,?,?)", (cat_id, nivel, cod, padre or None, desc))
            stats.inc(tabla, "insertadas")
        if duplicados:
            stats.inc(tabla, "duplicados_detectados", duplicados)


def importar_recursos(cur, f, ver_id, stats, adv):
    ids = {}
    for tipo, (tabla, col_cod, col_desc) in NOMENCLADORES.items():
        if tabla not in f.tablas():
            adv.append(f"{tabla}: ausente en esta base (recursos {tipo} no importados)")
            continue
        tipo_id = cur.execute("SELECT id FROM tipos_recurso WHERE codigo=?", (tipo,)).fetchone()[0]
        cols = [col_cod, col_desc, "UmRec", "PMN", "PMLC", "PrecioU", "PesoU"]
        if tipo == "mano_obra":
            cols += ["Grupo", "Especialidad"]
        if tipo == "equipo":
            cols += ["IdTipoEquipo", "NormaHoraria"]
        vistos = {}
        for r in f.filas(tabla, cols):
            cod = str(r.get(col_cod) or "").strip()
            if not cod:
                stats.inc(tabla, "omitidas_invalidas")
                adv_ejemplo(stats, adv, tabla, "fila con código nulo/vacío (omitida)")
                continue
            desc = str(r.get(col_desc) or "").strip()
            um = str(r.get("UmRec") or "").strip().lower()
            if cod in vistos:
                stats.inc(tabla, "duplicadas_omitidas")
                if vistos[cod] != desc:
                    adv.append(f"{tabla}: código {cod!r} duplicado con descripción distinta "
                               f"(se conserva la primera)")
                continue
            vistos[cod] = desc
            cur.execute("""INSERT INTO recursos (version_id, tipo_id, codigo, descripcion, unidad,
                precio_mn, precio_mlc, precio_total, peso_unidad, grupo_salarial, especialidad,
                tipo_equipo_id, norma_horaria)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (ver_id, tipo_id, cod, desc, um or None,
                         decimal_a_real(r.get("PMN")), decimal_a_real(r.get("PMLC")),
                         decimal_a_real(r.get("PrecioU")), decimal_a_real(r.get("PesoU")),
                         str(r.get("Grupo") or "").strip() or None if tipo == "mano_obra" else None,
                         str(r.get("Especialidad") or "").strip() or None if tipo == "mano_obra" else None,
                         int(r["IdTipoEquipo"]) if tipo == "equipo" and r.get("IdTipoEquipo") is not None else None,
                         int(r["NormaHoraria"]) if tipo == "equipo" and r.get("NormaHoraria") is not None else None))
            ids[(tipo, cod)] = cur.lastrowid
            stats.inc(tabla, "insertadas")
    return ids


def importar_partidas(cur, f, ver_id, stats, adv, codigos_grupo1):
    ids, vistos = {}, {}
    tabla = "Nomenclador de RV"
    cols = ["CODIGO RV", "Desc Rv", "UNIDAD DE MEDIDA", "CodSobreG", "CMMN", "CHMN", "CEMN",
            "CMMLC", "CHMLC", "CEMLC", "HORAS HOMBRE", "HORAS EQUIPO", "HORAS OPERARIO",
            "HORAS AYUDANTE", "PESO", "Oficial", "Res_Aprov", "Fecha_Aprov", "TIPO", "DescCorta"]
    deriva_capitulo = not f.tiene(tabla, "CodSobreG")
    if deriva_capitulo:
        adv.append("Nomenclador de RV sin columna CodSobreG (SBD): capítulo derivado del prefijo "
                   "del código de partida, verificado contra grupos de nivel 1")
    for r in f.filas(tabla, cols):
        cod = str(r.get("CODIGO RV") or "").strip()
        desc = str(r.get("Desc Rv") or "").strip()
        if not cod or not desc:
            stats.inc(tabla, "omitidas_invalidas")
            continue
        if cod in vistos:
            stats.inc(tabla, "duplicadas_omitidas")
            if vistos[cod] != desc:
                adv.append(f"{tabla}: código {cod!r} duplicado con descripción distinta "
                           f"(se conserva la primera)")
            continue
        vistos[cod] = desc
        um, factor = norm_um(r.get("UNIDAD DE MEDIDA"))
        if not um:
            adv_ejemplo(stats, adv, tabla, f"partida {cod} sin unidad de medida")
        if deriva_capitulo:
            cap = cod[:2]
            if codigos_grupo1 is not None and cap not in codigos_grupo1:
                adv_ejemplo(stats, adv, tabla, f"capítulo derivado {cap!r} de {cod} ausente en grupos nivel 1")
        else:
            cap = str(r.get("CodSobreG") or "").strip() or None
        cmmn, chmn, cemn = r.get("CMMN"), r.get("CHMN"), r.get("CEMN")
        total = (cmmn or 0) + (chmn or 0) + (cemn or 0) if (cmmn or chmn or cemn) is not None else None
        fecha = r.get("Fecha_Aprov")
        cur.execute("""INSERT INTO partidas (version_id, codigo, descripcion, unidad, factor_unidad,
            capitulo, costo_mat_mn, costo_mo_mn, costo_eq_mn, costo_total_mn, costo_mat_mlc,
            horas_hombre, horas_equipo, peso_kg, es_oficial, resolucion_aprob, fecha_aprobacion,
            chmlc, cemlc, horas_operario, horas_ayudante, tipo_rv, desc_corta)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (ver_id, cod, desc, um, factor, cap, decimal_a_real(cmmn), decimal_a_real(chmn),
                     decimal_a_real(cemn), decimal_a_real(total), decimal_a_real(r.get("CMMLC")),
                     a_real(r.get("HORAS HOMBRE")), a_real(r.get("HORAS EQUIPO")), a_real(r.get("PESO")),
                     1 if r.get("Oficial") else 0,
                     str(r.get("Res_Aprov")).strip() or None if r.get("Res_Aprov") else None,
                     str(fecha)[:10] if fecha else None,
                     decimal_a_real(r.get("CHMLC")), decimal_a_real(r.get("CEMLC")),
                     a_real(r.get("HORAS OPERARIO")), a_real(r.get("HORAS AYUDANTE")),
                     str(r.get("TIPO") or "").strip() or None,
                     str(r.get("DescCorta") or "").strip() or None))
        ids[cod] = cur.lastrowid
        stats.inc(tabla, "insertadas")
    return ids


def importar_normas(cur, f, ver_id, tipos_ids, ids_partidas, ids_recursos, stats, adv):
    for tipo, tabla, col_rec, col_coef, col_norma in NORMAS:
        if tabla not in f.tablas():
            adv.append(f"{tabla}: ausente en esta base (normas {tipo} no importadas)")
            continue
        tipo_id = tipos_ids[tipo]
        cols = ["CodigoRV", col_rec, col_coef] + ([col_norma] if col_norma else []) \
            + (["UMNorma"] if f.tiene(tabla, "UMNorma") else [])
        coef_previos = {}
        for r in f.filas(tabla, cols):
            cod_rv = str(r.get("CodigoRV") or "").strip()
            cod_rec = str(r.get(col_rec) or "").strip()
            coef = r.get(col_coef)
            cn = str(r.get(col_norma) or "").strip() if col_norma else ""
            if cod_rv not in ids_partidas:
                stats.inc(tabla, "huérfanas_partida")
                adv_ejemplo(stats, adv, tabla, f"norma con CodigoRV {cod_rv!r} ausente en partidas (omitida)")
                continue
            if coef is None:
                stats.inc(tabla, "omitidas_invalidas")
                continue
            if not cod_rec:
                stats.inc(tabla, "omitidas_invalidas")
                continue
            if (cod_rv, tipo, cod_rec, cn) in coef_previos:
                if coef_previos[(cod_rv, tipo, cod_rec, cn)] != coef:
                    adv.append(f"{tabla}: coeficiente conflictivo para {cod_rv}/{cod_rec}"
                               f" (se conserva el primero)")
                stats.inc(tabla, "duplicadas_omitidas")
                continue
            coef_previos[(cod_rv, tipo, cod_rec, cn)] = coef
            if (tipo, cod_rec) not in ids_recursos:
                stats.inc(tabla, "huérfanas_recurso")
                adv_ejemplo(stats, adv, tabla, f"recurso {cod_rec!r} ausente en nomenclador (norma insertada)")
            um_norma = str(r.get("UMNorma") or "").strip() or None if "UMNorma" in r else None
            cur.execute("""INSERT INTO normas_partida (partida_id, version_id, tipo_recurso_id,
                codigo_recurso, coeficiente, cod_norma, um_norma) VALUES (?,?,?,?,?,?,?)""",
                        (ids_partidas[cod_rv], ver_id, tipo_id, cod_rec, float(coef), cn or "S/C", um_norma))
            stats.inc(tabla, "insertadas")


def importar_componentes(cur, f, ver_id, tipos_ids, ids_recursos, stats, adv):
    for tipo_rec, tabla, col_rec, tipo_comp, col_comp, col_coef, col_norma in COMPONENTES:
        if tabla not in f.tablas():
            adv.append(f"{tabla}: ausente en esta base (componentes no importados)")
            continue
        _importar_componentes_tabla(cur, f, ver_id, tipos_ids, ids_recursos, stats, adv,
                                    tabla, tipo_rec, col_rec, tipo_comp, col_comp, col_coef, col_norma)
    # Norma Juego Material1: duplicado exacto verificado en la raíz 2017
    t1, t2 = "Norma Juego Material", "Norma Juego Material1"
    if t1 in f.tablas() and t2 in f.tablas():
        a = {(str(r["CodJuego"]), str(r["CodMat"]), r.get("CantMatJ"))
             for r in f.filas(t1, ["CodJuego", "CodMat", "CantMatJ"])}
        b = {(str(r["CodJuego"]), str(r["CodMat"]), r.get("CantMatJ"))
             for r in f.filas(t2, ["CodJuego", "CodMat", "CantMatJ"])}
        if a == b:
            adv.append(f"{t2}: copia EXACTA de {t1} ({len(b)} filas idénticas) → no se reimporta "
                       f"(verificado con datos)")
            stats.fijar(t2, {"fuente": len(b), "insertadas": 0, "nota": "duplicado exacto de Norma Juego Material"})
        else:
            adv.append(f"{t2}: DIFFIERE de {t1} (solo en Material1: {len(b - a)}, solo en Material: "
                       f"{len(a - b)}): filas propias importadas con cod_norma='NJM1'")
            for jg, mat, cant in sorted(b - a):
                rid = ids_recursos.get(("juego", jg))
                if rid is None or cant is None:
                    continue
                cur.execute("""INSERT OR IGNORE INTO componentes_recurso (recurso_id, version_id,
                    tipo_componente_id, codigo_componente, coeficiente, cod_norma)
                    VALUES (?,?,?,?,?, 'NJM1')""",
                            (rid, ver_id, tipos_ids["material"], mat, float(cant)))
                stats.inc(t2, "insertadas")


def _importar_componentes_tabla(cur, f, ver_id, tipos_ids, ids_recursos, stats, adv,
                                tabla, tipo_rec, col_rec, tipo_comp, col_comp, col_coef, col_norma):
    coef_previos = set()
    for r in f.filas(tabla, [col_rec, col_comp, col_coef] + ([col_norma] if col_norma else [])):
        cod_rec = str(r.get(col_rec) or "").strip()
        cod_comp = str(r.get(col_comp) or "").strip()
        coef = r.get(col_coef)
        cn = str(r.get(col_norma) or "").strip() if col_norma else ""
        if not cod_rec or not cod_comp or coef is None:
            stats.inc(tabla, "omitidas_invalidas")
            continue
        rid = ids_recursos.get((tipo_rec, cod_rec))
        if rid is None:
            stats.inc(tabla, "huérfanas_recurso")
            adv_ejemplo(stats, adv, tabla, f"{tipo_rec} {cod_rec!r} ausente en nomenclador (omitido)")
            continue
        if (rid, cod_comp, cn) in coef_previos:
            stats.inc(tabla, "duplicadas_omitidas")
            continue
        coef_previos.add((rid, cod_comp, cn))
        cur.execute("""INSERT INTO componentes_recurso (recurso_id, version_id, tipo_componente_id,
            codigo_componente, coeficiente, cod_norma) VALUES (?,?,?,?,?,?)""",
                    (rid, ver_id, tipos_ids[tipo_comp], cod_comp, float(coef), cn or "S/C"))
        stats.inc(tabla, "insertadas")


# ----------------------------------------------------------------------------
# PRECOST 2025 (catálogo embebido, extracto fase III-D)
# ----------------------------------------------------------------------------

def importar_precost2025(cur, ver_id, cat_id, stats, adv):
    data = json.load(open(EXTRACTO_PRECOST, encoding="utf-8"))
    G, P, M, O, E = data["G"], data["P"], data["M"], data["O"], data["E"]
    # grupos
    for cod, v in sorted(G.items()):
        nivel = {2: 1, 3: 2, 4: 3}.get(len(cod))
        if nivel is None:
            continue
        padre = cod[:-1] if nivel > 1 else None
        if padre is not None and padre not in G:
            adv_ejemplo(stats, adv, "G", f"grupo {cod!r} sin padre {padre!r} (importado sin padre)")
            padre = None
        cur.execute("INSERT OR IGNORE INTO grupos (catalogo_id, nivel, codigo, padre_codigo, descripcion)"
                    " VALUES (?,?,?,?,?)", (cat_id, nivel, cod, padre, str(v[0])))
        stats.inc("G", "insertadas")
    # partidas
    for cod, p in sorted(P.items()):
        um, factor = norm_um(p[1])
        total_fuente = a_real(p[2])
        suma = (a_real(p[3]) or 0) + (a_real(p[4]) or 0) + (a_real(p[5]) or 0)
        if total_fuente is not None and abs(total_fuente - suma) > 1e-6:
            stats.inc("P", "total_no_coincide_componentes")
        cur.execute("""INSERT INTO partidas (version_id, codigo, descripcion, unidad, factor_unidad,
            capitulo, costo_mat_mn, costo_mo_mn, costo_eq_mn, costo_total_mn, peso_kg)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (ver_id, cod, str(p[0]).strip(), um, factor, str(p[7]),
                     a_real(p[3]), a_real(p[4]), a_real(p[5]), total_fuente, a_real(p[6])))
        stats.inc("P", "insertadas")
    # recursos M/O/E + precios por fuente/fecha
    # Estructura real del extracto (fase3d): M = [desc, um, precio, peso];
    # O = [desc, tarifa horaria]; E = [desc, costo horario de uso].
    # CORRECCIÓN III-C: antes se leía v[2] para todos los tipos → las tarifas
    # de mano de obra y costos de equipo 2025 quedaban en NULL (los materiales
    # no se veían afectados). El dato de origen siempre estuvo en el extracto.
    for tipo, fuente, um_def, idx_precio in (
            ("material", M, None, 2), ("mano_obra", O, "hh", 1), ("equipo", E, "he", 1)):
        tipo_id = cur.execute("SELECT id FROM tipos_recurso WHERE codigo=?", (tipo,)).fetchone()[0]
        for cod, v in sorted(fuente.items()):
            desc = str(v[0]).strip()
            um = str(v[1]).lower() if (tipo == "material" and len(v) > 1) else um_def
            precio = a_real(v[idx_precio]) if len(v) > idx_precio else None
            peso = a_real(v[3]) if (tipo == "material" and len(v) > 3) else None
            cur.execute("""INSERT INTO recursos (version_id, tipo_id, codigo, descripcion, unidad,
                precio_mn, peso_unidad) VALUES (?,?,?,?,?,?,?)""",
                        (ver_id, tipo_id, cod, desc, um, precio, peso))
            stats.inc(f"{'M' if tipo == 'material' else 'O' if tipo == 'mano_obra' else 'E'}", "insertadas")
            cur.execute("""INSERT INTO precios_recurso (recurso_id, fuente, fecha, precio_mn, moneda)
                VALUES (?,?,?,?, 'CUP')""", (cur.lastrowid, "PRECONS_III_2025", "2025-06-06", precio))


# ----------------------------------------------------------------------------
# Gestión de versiones, idempotencia y transacción
# ----------------------------------------------------------------------------

class Stats:
    def __init__(self):
        self.d = defaultdict(lambda: defaultdict(int))

    def inc(self, tabla, clave, n=1):
        self.d[tabla][clave] += n

    def fijar(self, tabla, d):
        self.d[tabla] = defaultdict(int, d)

    def fijar_extra(self, tabla, d):
        """Fija contadores absolutos calculados localmente (semántica SET)."""
        for k, v in d.items():
            self.d[tabla][k] = v

    def json(self):
        return {t: dict(v) for t, v in self.d.items()}


def adv_ejemplo(stats, adv, tabla, mensaje, limite=3):
    """Advertencia con tope de EJEMPLOS por tipo de mensaje (cuenta completa en stats):
    la clave de control normaliza dígitos para agrupar mensajes del mismo tipo."""
    clave = f"_ej_{tabla}_" + re.sub(r"\d+", "#", mensaje)[:40]
    stats.d["_controles"][clave] += 1
    if stats.d["_controles"][clave] <= limite:
        adv.append(f"{tabla}: {mensaje}")


def resolver_version(con, cfg, sha, stats, adv):
    """Devuelve ('importar', None) | ('omitir', vid) | ('referencia', vid)."""
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO catalogos (codigo, nombre) VALUES (?,?)",
                (cfg["catalogo"], cfg["catalogo"]))
    con.commit()
    cat_id = cur.execute("SELECT id FROM catalogos WHERE codigo=?", (cfg["catalogo"],)).fetchone()[0]

    # ¿otra versión con el MISMO hash (archivo duplicado exacto)?
    dup = cur.execute("""SELECT id, version FROM versiones_catalogo
                         WHERE fuente_sha256=? AND catalogo_id=? AND version != ?""",
                      (sha, cat_id, cfg["version"])).fetchone()
    if dup and cfg.get("secundaria"):
        vid = cur.execute("""INSERT INTO versiones_catalogo (catalogo_id, version, fecha_publicacion,
            fuente_archivo, fuente_sha256, fuente_detalle, estado)
            VALUES (?,?,?,?,?,?,'retirada')""",
                          (cat_id, cfg["version"], None, cfg["archivo"], sha,
                           f"REFERENCIA: contenido byte-idéntico a la versión {dup[1]} "
                           f"(mismo SHA-256); 0 filas propias para no duplicar registros")).lastrowid
        adv.append(f"Archivo duplicado exacto de la versión {dup[1]} (SHA-256 idéntico): "
                   f"se registra como referencia retirada, sin filas propias")
        return "referencia", vid
    if dup and not cfg.get("secundaria"):
        raise SystemExit(
            f"ERROR: el contenido de {cfg['base_id']!r} ya está importado como versión "
            f"{dup[1]!r} (SHA-256 idéntico). Importar la misma base bajo otra etiqueta "
            f"duplicaría registros: si quiere esta etiqueta, purge primero esa versión.")

    fila = cur.execute("""SELECT id, fuente_sha256 FROM versiones_catalogo
                          WHERE catalogo_id=? AND version=?""", (cat_id, cfg["version"])).fetchone()
    if fila:
        vid, sha_existente = fila
        if sha_existente != sha:
            raise SystemExit(f"ERROR: la versión {cfg['version']!r} ya existe con OTRO hash "
                             f"({sha_existente[:16]}…): no se sobrescribe. Use una etiqueta nueva.")
        ultima = cur.execute("""SELECT resultado FROM importaciones WHERE version_id=?
                                ORDER BY id DESC LIMIT 1""", (vid,)).fetchone()
        if ultima and ultima[0] in ("ok", "ok_con_advertencias"):
            return "omitir", vid
        # intento previo fallido/interrumpido: purgar la cáscara y reintentar limpio
        cur.execute("DELETE FROM importaciones WHERE version_id=?", (vid,))
        cur.execute("DELETE FROM versiones_catalogo WHERE id=?", (vid,))
        con.commit()
        adv.append("Detectado intento de importación anterior incompleto para esta versión: "
                   "se purga la cáscara sin filas y se reintenta desde cero")
    return "importar", cat_id


def registrar_importacion(cur, vid, script, stats, adv, resultado, iniciada):
    cur.execute("""INSERT INTO importaciones (version_id, iniciada_en, finalizada_en, script,
        filas_por_tabla, advertencias, resultado) VALUES (?,?,?,?,?,?,?)""",
                (vid, iniciada, datetime.now(timezone.utc).isoformat(),
                 script, json.dumps(stats.json(), ensure_ascii=False),
                 json.dumps(adv, ensure_ascii=False), resultado))


def importar_base(cfg, ruta_bd, con_sbd=None, priorizadas=False, inyectar_fallo=None):
    """Importa una base completa en una transacción reversible."""
    iniciada = datetime.now(timezone.utc).isoformat()
    stats, adv = Stats(), []
    es_json = cfg["base_id"] == "precost2025"

    # --- integridad de originales ANTES ---
    if es_json:
        sha_html = sha256(HTML)
        assert sha_html == SHA_HTML, "¡El HTML original cambió! Abortando."
        sha_fuente, ruta_fuente = sha_html, "PRECOST-v9.17.html (const DB)"
    else:
        ruta_fuente = os.path.join(FUENTE_BASE, cfg["archivo"])
        sha_fuente = sha256(ruta_fuente)

    r = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "fase3e_migrar.py"), ruta_bd],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"migraciones: {r.stderr}")
    con = sqlite3.connect(ruta_bd, timeout=60)
    con.isolation_level = None
    con.execute("PRAGMA foreign_keys = ON")

    modo, vid = resolver_version(con, cfg, sha_fuente, stats, adv)
    if modo == "omitir":
        print(f"  = versión {cfg['version']} ya importada correctamente (idempotente): nada que hacer")
        con.close()
        return {"base": cfg["base_id"], "resultado": "omitida_idempotente", "version_id": vid}
    if modo == "referencia":
        registrar_importacion(con.cursor(), vid, os.path.basename(__file__), stats,
                              adv, "ok_con_advertencias", iniciada)
        con.commit()
        con.close()
        return {"base": cfg["base_id"], "resultado": "referencia_duplicado", "version_id": vid}

    cat_id = vid
    print(f"  … importando {cfg['etiqueta']} → versión {cfg['version']}")

    f = None
    if not es_json:
        f = FuenteMdb(ruta_fuente, cfg["inventario_id"])
        tablas = f.tablas()
        esperadas = ([t for t, *_ in GRUPOS_MAP] + [v[0] for v in NOMENCLADORES.values()]
                     + [t for _, t, *_ in NORMAS] + [t for _, t, *_ in COMPONENTES])
        faltan = [t for t in esperadas if t not in tablas]
        if faltan:
            raise SystemExit(f"ERROR: tablas del núcleo ausentes en {ruta_fuente}: {faltan}")
        extra = [t for t in ("Actividades de Estimación", "Norma Juego Material1") if t in tablas]
        for t in extra:
            adv.append(f"tabla opcional {t!r} presente en esta base "
                       f"({'se procesa en SBD' if t == 'Actividades de Estimación' else 'verificada como duplicada'})")

    try:
        con.execute("BEGIN IMMEDIATE")
        cur = con.cursor()
        cur.execute("""INSERT INTO versiones_catalogo (catalogo_id, version, fecha_publicacion,
            fuente_archivo, fuente_sha256, fuente_detalle, estado)
            VALUES (?,?,?,?,?,?, 'importada')""",
                    (cat_id, cfg["version"],
                     "2025-06-06" if es_json else None,
                     ruta_fuente, sha_fuente, cfg["etiqueta"]))
        vid = cur.lastrowid
        tipos_ids = {c: i for c, i in cur.execute("SELECT codigo, id FROM tipos_recurso").fetchall()}

        if es_json:
            importar_precost2025(cur, vid, cat_id, stats, adv)
        else:
            codigos_g1 = {c for (c,) in cur.execute(
                "SELECT codigo FROM grupos WHERE catalogo_id=? AND nivel=1", (cat_id,)).fetchall()}
            importar_grupos(cur, f, cat_id, stats, adv)
            importar_recursos(cur, f, vid, stats, adv)
            ids_recursos = {(t, c): i for t, c, i in cur.execute(
                """SELECT (SELECT codigo FROM tipos_recurso WHERE id=tipo_id), codigo, id
                   FROM recursos WHERE version_id=?""", (vid,)).fetchall()}
            ids_partidas = importar_partidas(cur, f, vid, stats, adv, codigos_g1)
            importar_normas(cur, f, vid, tipos_ids, ids_partidas, ids_recursos, stats, adv)
            importar_componentes(cur, f, vid, tipos_ids, ids_recursos, stats, adv)
            if cfg["base_id"] == "sbd" and priorizadas:
                from importar_sbd import importar_priorizadas
                importar_priorizadas(cur, f, vid, stats, adv)
        if inyectar_fallo:
            raise RuntimeError(f"FALLO INYECTADO (prueba de reversibilidad): {inyectar_fallo}")

        resultado = "ok" if not adv else "ok_con_advertencias"
        registrar_importacion(cur, vid, os.path.basename(__file__), stats, adv, resultado, iniciada)
        con.execute("COMMIT")
    except Exception as e:  # noqa: BLE001
        con.execute("ROLLBACK")
        # registrar el intento fallido (transacción aparte) para auditoría
        try:
            cur = con.cursor()
            cur.execute("""INSERT INTO versiones_catalogo (catalogo_id, version, fecha_publicacion,
                fuente_archivo, fuente_sha256, fuente_detalle, estado)
                VALUES (?,?,?,?,?,?, 'importada')""",
                        (cat_id, cfg["version"], None, ruta_fuente, sha_fuente,
                         f"INTENTO FALLIDO: {e}"))
            registrar_importacion(cur, cur.lastrowid, os.path.basename(__file__), stats,
                                  [f"ERROR: {e}"], "error", iniciada)
            con.execute("COMMIT")
        except Exception:  # noqa: BLE001
            pass
        con.close()
        raise

    # --- integridad de originales DESPUÉS ---
    if not es_json:
        assert sha256(ruta_fuente) == sha_fuente, f"¡{ruta_fuente} cambió durante la importación!"
    else:
        assert sha256(HTML) == SHA_HTML, "¡El HTML original cambió durante la importación!"
    con.close()

    resumen = {k: v.get("insertadas", 0) for k, v in stats.json().items() if isinstance(v, dict)}
    print(f"  ✓ versión {cfg['version']} (id {vid}): {sum(resumen.values()):,} filas insertadas, "
          f"{len(adv)} advertencias")
    return {"base": cfg["base_id"], "resultado": "ok", "version_id": vid,
            "filas": stats.json(), "advertencias": adv}


def purgar_version(ruta_bd, catalogo, version):
    """Borra una versión y sus filas (orden FK-seguro). Acción administrativa
    documentada: uso principal, reimportar tras corregir algo o probar."""
    con = sqlite3.connect(ruta_bd)
    con.execute("PRAGMA foreign_keys = ON")
    fila = con.execute("""SELECT vc.id FROM versiones_catalogo vc JOIN catalogos c ON c.id=vc.catalogo_id
                          WHERE c.codigo=? AND vc.version=?""", (catalogo, version)).fetchone()
    if not fila:
        print(f"No existe {catalogo}/{version}: nada que purgar")
        con.close()
        return
    vid = fila[0]
    # CORRECCIÓN III-C: precios_recurso NO tiene columna version_id (referencia
    # recursos(id)); el borrado genérico por version_id fallaba en silencio y
    # el DELETE posterior de recursos chocaba con la FK (IntegrityError).
    # Se borra primero por recurso_id, en el mismo orden FK-seguro.
    orden = ["normas_partida", "componentes_recurso", "recursos", "partidas",
             "sbd_colecciones_recursos", "sbd_colec_rv", "sbd_normas_recurso", "sbd_normas_rh_extendida",
             "sbd_normas_descriptivas", "sbd_tarifas_transporte", "sbd_tarifas_especiales",
             "sbd_duracion_costo_rv", "sbd_actividades_estimacion", "sbd_macros_rv",
             "sbd_presupuesto_recursos", "sbd_presupuesto_rv", "sbd_obras", "sbd_objetos_obra",
             "sbd_etapas", "sbd_colecciones"]
    borradas = {}
    try:
        n = con.execute("""DELETE FROM precios_recurso WHERE recurso_id IN
                           (SELECT id FROM recursos WHERE version_id=?)""", (vid,)).rowcount
        if n:
            borradas["precios_recurso"] = n
    except sqlite3.OperationalError:
        pass  # tabla aún no creada (migración no aplicada)
    for t in orden:
        try:
            n = con.execute(f"DELETE FROM {t} WHERE version_id=?", (vid,)).rowcount
            if n:
                borradas[t] = n
        except sqlite3.OperationalError:
            pass  # tabla aún no creada (migración no aplicada)
    con.execute("DELETE FROM importaciones WHERE version_id=?", (vid,))
    con.execute("DELETE FROM versiones_catalogo WHERE id=?", (vid,))
    con.commit()
    con.close()
    print(f"Purgada {catalogo}/{version} (id {vid}): {borradas}")


def informe(ruta_bd):
    con = sqlite3.connect(ruta_bd)
    con.row_factory = sqlite3.Row
    out = {"generado": datetime.now(timezone.utc).isoformat(), "versiones": [], "conteos": {}}
    for v in con.execute("""SELECT vc.*, c.codigo AS catalogo FROM versiones_catalogo vc
                            JOIN catalogos c ON c.id=vc.catalogo_id ORDER BY vc.id"""):
        entry = dict(v)
        entry["importaciones"] = [dict(i) for i in con.execute(
            "SELECT * FROM importaciones WHERE version_id=? ORDER BY id", (v["id"],))]
        out["versiones"].append(entry)
    for (cat, ver, vid) in con.execute(
            """SELECT c.codigo, vc.version, vc.id FROM versiones_catalogo vc
               JOIN catalogos c ON c.id=vc.catalogo_id ORDER BY vc.id"""):
        conteo = {}
        for tabla, col in (("partidas", "id"), ("recursos", "id"), ("normas_partida", "id"),
                           ("componentes_recurso", "id"), ("grupos", "id")):
            n = con.execute(f"SELECT COUNT(*) FROM {tabla} WHERE version_id=?", (vid,)).fetchone()[0] \
                if tabla != "grupos" else con.execute(
                    "SELECT COUNT(*) FROM grupos WHERE catalogo_id=(SELECT catalogo_id FROM versiones_catalogo WHERE id=?)", (vid,)).fetchone()[0]
            if n:
                conteo[tabla] = n
        out["conteos"][f"{cat}/{ver}"] = conteo
    salida = os.path.join(REPO, "docs", "datos", "iiib_importaciones.json")
    with open(salida, "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    print(f"Informe → {salida}")
    con.close()
    return salida


def main():
    ap = argparse.ArgumentParser(description="Importador común PRECODI/PRECOST → SQLite (Misión III-B)")
    ap.add_argument("--bd", default=BD_DEFECTO)
    ap.add_argument("--base", choices=list(BASES), help="base a importar")
    ap.add_argument("--todas", action="store_true", help="721, 722, raiz, preambulos y precost2025")
    ap.add_argument("--priorizadas", action="store_true", help="con --base sbd: además del núcleo, tablas priorizadas")
    ap.add_argument("--informe", action="store_true", help="vuelca docs/datos/iiib_importaciones.json")
    ap.add_argument("--purgar", metavar="CATALOGO/VERSION",
                    help="borra una versión y sus filas (acción administrativa, orden FK-seguro)")
    ap.add_argument("--inyectar-fallo", default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.purgar:
        catalogo, version = args.purgar.split("/", 1)
        purgar_version(args.bd, catalogo, version)
        return 0
    if args.informe:
        informe(args.bd)
        return 0
    if not (args.base or args.todas):
        ap.error("indique --base o --todas")

    orden = ["721", "722", "raiz", "preambulos", "precost2025"] if args.todas else [args.base]
    resultados = []
    for base_id in orden:
        cfg = dict(BASES[base_id])
        cfg["base_id"] = base_id
        print(f"\n=== {base_id}: {cfg['etiqueta']} ===")
        resultados.append(importar_base(cfg, args.bd, priorizadas=args.priorizadas,
                                        inyectar_fallo=args.inyectar_fallo))
    informe(args.bd)
    print("\n" + json.dumps([{k: v for k, v in r.items() if k != "filas"} for r in resultados],
                            ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
