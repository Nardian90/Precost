#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MISIÓN IV — Línea A: auditoría de fidelidad del clasificador embebido.

Compara, campo a campo y sin depender de IDs autoincrementales:

  EMB = catálogo embebido de PRECOST 9.17 (const DB — PRECONS III MICONS 2025)
  SBD = SBD_MICONS_2025.mdb (base por defecto de SIECONS 11 — misma época)
  P17 = PRECODI 2017-raíz (importada en bd/precodi.db, versión 3)
  P72 = PRECODI 7.21 (versión 1, histórica)

Comparaciones:
  A. Partidas EMB.P ↔ SBD.RV   (2025↔2025: la verificación de fidelidad clave)
  B. Materiales EMB.M ↔ SBD.Materiales
  C. Equipos EMB.E ↔ SBD.Equipos
  D. Mano de obra EMB.O ↔ SBD.RH
  E. Grupos EMB.G ↔ SBD.SubGrupos/Grupos/SobreGrupos
  F. Normas P17 ↔ SBD (existencia y coeficientes por (RV, tipo, recurso))
  G. Caso de referencia 012141 multi-fuente
  H. Pendientes heredados: patrón ×10 recalculado en SBD, unidades 2017→2025,
     HORAS OPERARIO/AYUDANTE

Salida: docs/datos/fidelidad_iv.json (métricas + muestras por clase de
diferencia). El informe narrativo se genera en
docs/INFORME_FIDELIDAD_CLASIFICADOR.md.
"""
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from decimal import Decimal

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import precision_precodi  # noqa: E402
precision_precodi.parchear_money_exacto()
from access_parser import AccessParser  # noqa: E402

SBD_RUTA = ("/home/z/my-project/work/siecons_extract/payload/"
            "BD/SBD_11/SBD_11_MICONS_2025/SBD_MICONS_2025.mdb")
HTML = os.path.join(REPO, "app", "PRECOST-v9.17.html")
BD = os.path.join(REPO, "bd", "precodi.db")
SALIDA = os.path.join(REPO, "docs", "datos", "fidelidad_iv.json")

# ---------------------------------------------------------------- utilidades


def a_numero(v):
    """Convierte valores heterogéneos (Decimal/float/str con comas/'[]') a float."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s in ("", "[]", "None"):
        return None
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def normalizar_texto(s):
    if not s:
        return ""
    s = str(s).upper().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def cargar_embebido():
    """Extrae const DB del HTML original (sin modificarlo)."""
    import fase3d_extraer_catalogo as f3d
    html = open(HTML, encoding="utf-8").read()
    m = re.search(r"const\s+DB\s*=\s*", html)
    ini = html.index("{", m.end())
    obj = f3d.extraer_objeto_js(html, ini)
    return json.loads(obj)


def cargar_sbd():
    db = AccessParser(SBD_RUTA)
    out = {}
    for clave, tabla in [
        ("rv", "Nomenclador de RV"),
        ("mat", "Nomenclador de Materiales"),
        ("eq", "Nomenclador de Equipos"),
        ("rh", "Nomenclador RH"),
        ("juegos", "Nomenclador de Juegos"),
        ("semi", "Nomenclador de Semielaborados"),
        ("subgrupos", "Nomenclador de SubGrupos RV"),
        ("grupos", "Nomenclador de Grupos RV"),
        ("sobregrupos", "Nomenclador de SobreGrupos RV"),
        ("norma_mat", "Norma de Materiales"),
        ("norma_mo", "Norma de Mano de Obra"),
        ("norma_eq", "Norma de Equipos"),
        ("norma_juegos", "Norma de Juegos"),
        ("norma_semi", "Norma de Semielaborados"),
    ]:
        t = db.get_table(tabla).parse()
        filas = len(next(iter(t.values()))) if t else 0
        print(f"  SBD {tabla}: {filas:,} filas")
        out[clave] = t
    return out


# ------------------------------------------------------------- comparaciones

TOL_PRECIO = 0.005      # EMB redondea a 2 decimales
TOL_COEF = 1e-6         # Float32 relativo


def cmp_precio(a, b):
    if a is None or b is None:
        return "no_verificable"
    if abs(a - b) <= TOL_PRECIO:
        return "coincidencia_exacta"
    return "dif_precio"


def cmp_texto(a, b):
    if a is None or b is None:
        return "no_verificable"
    if a == b:
        return "coincidencia_exacta"
    if normalizar_texto(a) == normalizar_texto(b):
        return "equivalente_formato"
    return "dif_descripcion"


def comparar_diccionarios(emb, sbd, campos, nombre, ejemplos, resumen):
    """Compara {codigo: [...]} embebido vs {codigo: {...}} SBD por campo."""
    emb_cod = set(emb)
    sbd_cod = set(sbd)
    comunes = emb_cod & sbd_cod
    solo_emb = emb_cod - sbd_cod
    solo_sbd = sbd_cod - emb_cod

    clases = Counter()
    ejemplos_por_clase = defaultdict(list)

    for cod in comunes:
        e, s = emb[cod], sbd[cod]
        for campo, idx_e, idx_s in campos:
            ve = e[idx_e] if idx_e is not None else None
            vs = s.get(idx_s) if isinstance(idx_s, str) else (
                s[idx_s] if idx_s is not None else None)
            if campo in ("descripcion",):
                r = cmp_texto(ve, vs)
            elif campo in ("unidad", "um"):
                r = cmp_texto(ve, vs)
                if r == "dif_descripcion":
                    r = "dif_unidad"
            else:
                ve2, vs2 = a_numero(ve), a_numero(vs)
                r = cmp_precio(ve2, vs2)
            clases[campo + ":" + r] += 1
            if r not in ("coincidencia_exacta", "equivalente_formato"):
                clave = f"{campo}:{r}"
                if len(ejemplos_por_clase[clave]) < 8:
                    ejemplos_por_clase[clave].append(
                        {"codigo": cod, "emb": str(ve)[:60],
                         "sbd": str(vs)[:60]})

    resumen[nombre] = {
        "emb_registros": len(emb_cod),
        "sbd_registros": len(sbd_cod),
        "comunes": len(comunes),
        "solo_emb": len(solo_emb),
        "solo_sbd": len(solo_sbd),
        "clases_por_campo": dict(clases),
        "ejemplos_solo_emb": sorted(solo_emb)[:40],
        "ejemplos_solo_sbd": sorted(solo_sbd)[:40],
        "ejemplos_diferencias": {k: v for k, v in ejemplos_por_clase.items()},
    }
    print(f"  {nombre}: EMB {len(emb_cod):,} / SBD {len(sbd_cod):,} / "
          f"comunes {len(comunes):,} / solo EMB {len(solo_emb):,} / "
          f"solo SBD {len(solo_sbd):,}")
    return resumen[nombre]


def main():
    print("=== MISIÓN IV — Auditoría de fidelidad del clasificador ===\n")
    resumen = {}

    print("[1] Cargando catálogo embebido de PRECOST…")
    emb = cargar_embebido()
    for k, n in (("P", "partidas"), ("M", "materiales"), ("O", "mano de obra"),
                 ("E", "equipos"), ("G", "grupos")):
        print(f"  EMB {k}: {len(emb[k]):,} {n}")

    print("\n[2] Cargando SBD_MICONS_2025 (SIECONS 11)…")
    sbd = cargar_sbd()

    print("\n[3] Cargando SQLite (PRECODI 2017 / versiones)…")
    con = sqlite3.connect(f"file:{BD}?mode=ro", uri=True)
    cur = con.cursor()

    # ---------------------------------------------------------------- A. P vs RV
    print("\n[A] Partidas EMB.P ↔ SBD.RV (2025↔2025)")
    # RV: CODIGO RV, Desc Rv, UNIDAD DE MEDIDA, CMMN, CHMN, CEMN, PESO,
    #     HORAS HOMBRE, HORAS EQUIPO, HORAS OPERARIO, HORAS AYUDANTE, CodSubG
    sbd_rv = {}
    for i, cod in enumerate(sbd["rv"]["CODIGO RV"]):
        sbd_rv[str(cod)] = {
            "desc": sbd["rv"]["Desc Rv"][i],
            "um": sbd["rv"]["UNIDAD DE MEDIDA"][i],
            "cmmn": a_numero(sbd["rv"]["CMMN"][i]),
            "chmn": a_numero(sbd["rv"]["CHMN"][i]),
            "cemn": a_numero(sbd["rv"]["CEMN"][i]),
            "peso": a_numero(sbd["rv"]["PESO"][i]),
            "hh": a_numero(sbd["rv"]["HORAS HOMBRE"][i]),
            "he": a_numero(sbd["rv"]["HORAS EQUIPO"][i]),
            "hrop": a_numero(sbd["rv"]["HORAS OPERARIO"][i]),
            "hayu": a_numero(sbd["rv"]["HORAS AYUDANTE"][i]),
            "codsubg": sbd["rv"]["CodSubG"][i],
            "tipoa": sbd["rv"]["TipoA"][i],
        }
    # EMB.P: codigo -> [desc, um, total, mat, mo, eq, peso, seccion]
    emb_p = {c: v for c, v in emb["P"].items()}
    # total SBD = CMMN+CHMN+CEMN (MLC = 0 en 2025)
    # se compara contra EMB.total; además componentes por separado
    emb_p_norm = {}
    for cod, v in emb_p.items():
        emb_p_norm[cod] = v

    sbd_p_plano = {}
    for cod, d in sbd_rv.items():
        sbd_p_plano[cod] = {
            "desc": d["desc"], "um": d["um"],
            "cmmn": d["cmmn"], "chmn": d["chmn"], "cemn": d["cemn"],
            "total": (d["cmmn"] or 0) + (d["chmn"] or 0) + (d["cemn"] or 0),
            "peso": d["peso"], "hh": d["hh"], "he": d["he"],
            "hrop": d["hrop"], "hayu": d["hayu"], "codsubg": d["codsubg"],
            "tipoa": d["tipoa"],
        }

    r_a = {"emb": len(emb_p_norm), "sbd": len(sbd_p_plano)}
    comunes = set(emb_p_norm) & set(sbd_p_plano)
    solo_emb = set(emb_p_norm) - set(sbd_p_plano)
    solo_sbd = set(sbd_p_plano) - set(emb_p_norm)
    r_a["comunes"] = len(comunes)
    r_a["solo_emb"] = len(solo_emb)
    r_a["solo_sbd"] = len(solo_sbd)

    clases = Counter()
    ejemplos = defaultdict(list)
    for cod in comunes:
        e = emb_p_norm[cod]           # [desc, um, total, mat, mo, eq, peso, sec]
        s = sbd_p_plano[cod]
        # descripcion
        r = cmp_texto(e[0], s["desc"])
        clases["descripcion:" + r] += 1
        if r not in ("coincidencia_exacta", "equivalente_formato") and \
                len(ejemplos["descripcion:" + r]) < 10:
            ejemplos["descripcion:" + r].append(
                {"codigo": cod, "emb": str(e[0])[:60],
                 "sbd": str(s["desc"])[:60]})
        # unidad
        r = cmp_texto(e[1], s["um"])
        if r == "dif_descripcion":
            r = "dif_unidad"
        clases["unidad:" + r] += 1
        if r == "dif_unidad" and len(ejemplos["unidad:dif_unidad"]) < 15:
            ejemplos["unidad:dif_unidad"].append(
                {"codigo": cod, "emb": str(e[1]), "sbd": str(s["um"])})
        # precios: total, mat, mo, eq
        for campo, idx_e, idx_s in (("total", 2, "total"), ("mat", 3, "cmmn"),
                                    ("mo", 4, "chmn"), ("eq", 5, "cemn"),
                                    ("peso", 6, "peso")):
            ve, vs = a_numero(e[idx_e]), s[idx_s]
            if ve is None or vs is None:
                r = "no_verificable"
            elif abs(ve - vs) <= TOL_PRECIO:
                r = "coincidencia_exacta"
            else:
                r = "dif_precio"
            clases[f"{campo}:{r}"] += 1
            if r == "dif_precio" and len(ejemplos[f"{campo}:{r}"]) < 10:
                ejemplos[f"{campo}:{r}"].append(
                    {"codigo": cod, "emb": ve, "sbd": vs,
                     "delta": round(ve - vs, 4)})
    r_a["clases_por_campo"] = dict(clases)
    r_a["ejemplos_diferencias"] = {k: v for k, v in ejemplos.items()}
    r_a["ejemplos_solo_emb"] = sorted(solo_emb)[:40]
    r_a["ejemplos_solo_sbd"] = sorted(solo_sbd)[:40]
    resumen["A_partidas"] = r_a
    print(f"  comunes {len(comunes):,}; solo EMB {len(solo_emb):,}; "
          f"solo SBD {len(solo_sbd):,}")
    for k, v in sorted(clases.items()):
        print(f"    {k}: {v:,}")

    # ---------------------------------------------------------------- B-E. recursos
    print("\n[B] Materiales EMB.M ↔ SBD.Materiales")
    # M: codigo -> [desc, um, precio, peso]; SBD: CodMat, Material, UmRec, PMN, PesoU
    sbd_mat = {}
    for i, cod in enumerate(sbd["mat"]["CodMat"]):
        c = str(cod)
        sbd_mat[c] = [sbd["mat"]["Material"][i], sbd["mat"]["UmRec"][i],
                      sbd["mat"]["PMN"][i], sbd["mat"]["PesoU"][i]]
    emb_m = {c: v for c, v in emb["M"].items()}
    comparar_diccionarios(
        emb_m, sbd_mat,
        [("descripcion", 0, 0), ("unidad", 1, 1), ("precio", 2, 2),
         ("peso", 3, 3)],
        "B_materiales", None, resumen)

    print("\n[C] Equipos EMB.E ↔ SBD.Equipos")
    sbd_eq = {}
    for i, cod in enumerate(sbd["eq"]["CodEquipo"]):
        c = str(cod)
        sbd_eq[c] = [sbd["eq"]["Equipo"][i], None, sbd["eq"]["PMN"][i]]
    emb_e = {c: [v[0], None, v[1]] for c, v in emb["E"].items()}
    comparar_diccionarios(
        emb_e, sbd_eq,
        [("descripcion", 0, 0), ("costo_horario", 2, 2)],
        "C_equipos", None, resumen)

    print("\n[D] Mano de obra EMB.O ↔ SBD.RH")
    sbd_rh = {}
    for i, cod in enumerate(sbd["rh"]["CodRHum"]):
        c = str(cod)
        sbd_rh[c] = [sbd["rh"]["RHum"][i], None,
                     sbd["rh"]["TRH_MN"][i], sbd["rh"]["Grupo"][i]]
    emb_o = {c: [v[0], None, v[1], None] for c, v in emb["O"].items()}
    comparar_diccionarios(
        emb_o, sbd_rh,
        [("descripcion", 0, 0), ("tarifa", 2, 2)],
        "D_mano_obra", None, resumen)

    print("\n[E] Grupos EMB.G ↔ SBD.SubGrupos(+Grupos+SobreGrupos)")
    sbd_g = {}
    for t, cols in (("subgrupos", ("CodSubG", "SubGrupo")),
                    ("grupos", ("CodG", "Grupo")),
                    ("sobregrupos", ("CodSobreG", "SubreGrupo"))):
        for i, cod in enumerate(sbd[t][cols[0]]):
            c = str(cod)
            sbd_g.setdefault(c, [sbd[t][cols[1]][i]])
    emb_g = {c: v for c, v in emb["G"].items()}
    r_e = comparar_diccionarios(
        emb_g, sbd_g, [("descripcion", 0, 0)], "E_grupos", None, resumen)

    # ------------------------------------------------------- F. Normas P17 vs SBD
    print("\n[F] Normas PRECODI 2017 ↔ SBD 2025 (por RV+tipo+recurso)")
    # SQLite v3 (2017): normas_partida joined partidas (codigo)
    p17 = {}
    for fila in cur.execute("""
            SELECT p.codigo, tr.nombre, n.codigo_recurso, n.coeficiente
            FROM normas_partida n
            JOIN partidas p ON n.partida_id = p.id
            JOIN tipos_recurso tr ON n.tipo_recurso_id = tr.id
            WHERE p.version_id = 3"""):
        p17[(fila[0], fila[1], str(fila[2]))] = fila[3]
    print(f"  P17 normas: {len(p17):,}")

    tipo_map = {"Material": "norma_mat", "Mano de obra": "norma_mo",
                "Equipo": "norma_eq", "Juego de trabajo": "norma_juegos",
                "Semielaborado": "norma_semi"}
    campo_map = {"norma_mat": ("CodigoRV", "CodMat", "CantMat"),
                 "norma_mo": ("CodigoRV", "CodRHum", "CantRHum"),
                 "norma_eq": ("CodigoRV", "CodEquipo", "CantEquipo"),
                 "norma_juegos": ("CodigoRV", "CodJuego", "CantJuego"),
                 "norma_semi": ("CodigoRV", "CodSElab", "CantSElab")}
    sbd_normas = {}
    for tipo, tabla in tipo_map.items():
        c_rv, c_rec, c_cant = campo_map[tabla]
        t = sbd[tabla]
        for i in range(len(t[c_rv])):
            clave = (str(t[c_rv][i]), tipo, str(t[c_rec][i]))
            # duplicados reales: quedarse con el primero y registrar
            if clave in sbd_normas:
                continue
            sbd_normas[clave] = a_numero(t[c_cant][i])
    print(f"  SBD normas: {len(sbd_normas):,}")

    cl_p17 = set(p17)
    cl_sbd = set(sbd_normas)
    comunes_n = cl_p17 & cl_sbd
    r_f = {"p17": len(p17), "sbd": len(sbd_normas),
           "comunes": len(comunes_n),
           "solo_p17": len(cl_p17 - cl_sbd),
           "solo_sbd": len(cl_sbd - cl_p17)}
    iguales = dentro_tol = fuera = 0
    ej_fuera = []
    for k in comunes_n:
        a, b = p17[k], sbd_normas[k]
        if a is None or b is None:
            continue
        if a == b:
            iguales += 1
        elif abs(a - b) <= max(abs(a), abs(b)) * TOL_COEF:
            dentro_tol += 1
        else:
            fuera += 1
            if len(ej_fuera) < 10:
                ej_fuera.append({"clave": list(k), "p17": a, "sbd": b})
    r_f.update({"coef_iguales": iguales, "coef_dentro_tol_float32": dentro_tol,
                "coef_diferentes": fuera, "ejemplos_diferentes": ej_fuera})
    # desglose por tipo
    por_tipo = defaultdict(lambda: [0, 0, 0, 0])  # comunes, solo17, solo25, dif
    for k in comunes_n:
        por_tipo[k[1]][0] += 1
        if p17[k] != sbd_normas[k] and not (
                abs(p17[k] - sbd_normas[k]) <=
                max(abs(p17[k]), abs(sbd_normas[k])) * TOL_COEF):
            por_tipo[k[1]][3] += 1
    for k in cl_p17 - cl_sbd:
        por_tipo[k[1]][1] += 1
    for k in cl_sbd - cl_p17:
        por_tipo[k[1]][2] += 1
    r_f["por_tipo"] = {t: dict(zip(
        ["comunes", "solo_2017", "solo_2025", "coef_diferentes"], v))
        for t, v in por_tipo.items()}
    resumen["F_normas"] = r_f
    print(f"  comunes {len(comunes_n):,}; solo P17 {r_f['solo_p17']:,}; "
          f"solo SBD {r_f['solo_sbd']:,}")
    print(f"  coef iguales {iguales:,} / tol {dentro_tol:,} / dif {fuera:,}")

    # ------------------------------------------------------------- G. caso 012141
    print("\n[G] Caso de referencia 012141 (multi-fuente)")
    caso = {"codigo": "012141"}
    if "012141" in emb_p_norm:
        caso["emb"] = emb_p_norm["012141"]
    if "012141" in sbd_p_plano:
        s = sbd_p_plano["012141"]
        caso["sbd"] = {k: s[k] for k in
                       ("desc", "um", "cmmn", "chmn", "cemn", "total",
                        "peso", "hh", "he", "codsubg")}
    fila17 = cur.execute(
        "SELECT codigo, descripcion, unidad, costo_mat_mn, costo_mo_mn, "
        "costo_eq_mn, costo_total_mn, peso_kg, horas_hombre, horas_equipo "
        "FROM partidas WHERE version_id=3 AND codigo='012141'").fetchone()
    if fila17:
        caso["precodi_2017"] = {
            "codigo": fila17[0], "descripcion": fila17[1], "unidad": fila17[2],
            "mat": fila17[3], "mo": fila17[4], "eq": fila17[5],
            "total": fila17[6], "peso": fila17[7], "hh": fila17[8],
            "he": fila17[9]}
    # normas 012141 en las tres fuentes
    caso["normas_p17"] = [
        {"tipo": t, "recurso": r, "coef": p17[("012141", t, r)]}
        for (c, t, r) in sorted(p17) if c == "012141"]
    caso["normas_sbd"] = [
        {"tipo": t, "recurso": r, "coef": sbd_normas[("012141", t, r)]}
        for (c, t, r) in sorted(sbd_normas) if c == "012141"]
    resumen["G_caso_012141"] = caso
    print(f"  EMB: {caso.get('emb')}")
    print(f"  SBD: {caso.get('sbd')}")

    # --------------------------------------------- H. pendientes heredados
    print("\n[H] Pendientes heredados")
    # H1. Patrón ×10 recalculado en SBD 2025:
    #     CHMN vs Suma(CantRHum × TRH_MN) con tarifas SBD
    tarifas_rh = {}
    for i, cod in enumerate(sbd["rh"]["CodRHum"]):
        tarifas_rh[str(cod)] = a_numero(sbd["rh"]["TRH_MN"][i])
    suma_mo = defaultdict(float)
    t = sbd["norma_mo"]
    for i in range(len(t["CodigoRV"])):
        cod = str(t["CodigoRV"][i])
        rec = str(t["CodRHum"][i])
        cant = a_numero(t["CantRHum"][i]) or 0.0
        tar = tarifas_rh.get(rec)
        if tar is not None:
            suma_mo[cod] += cant * tar
    patron10 = []
    sin_norma = []
    for cod, d in sbd_p_plano.items():
        if cod not in suma_mo or suma_mo[cod] == 0:
            sin_norma.append(cod)
            continue
        chmn = d["chmn"] or 0
        if chmn == 0:
            continue
        ratio = chmn / suma_mo[cod]
        if 9.0 <= ratio <= 11.0:
            patron10.append({"codigo": cod, "chmn": chmn,
                             "suma_normas": round(suma_mo[cod], 4),
                             "ratio": round(ratio, 3)})
    resumen["H_patron_x10_sbd2025"] = {
        "partidas_con_norma_mo": len(suma_mo),
        "casos_patron_10": len(patron10),
        "muestras": sorted(patron10, key=lambda x: x["codigo"])[:20]}
    print(f"  patrón ×10 en SBD 2025: {len(patron10)} partidas "
          f"(P17 documentado: 259)")

    # H2. Unidades 2017 → 2025 (P17 vs SBD)
    unidades17 = {}
    for cod, um in cur.execute(
            "SELECT codigo, unidad FROM partidas WHERE version_id=3"):
        unidades17[cod] = um
    cambios_um = []
    um_equiv = {"m2": ("100 m2",), "m3": ("100 m3",), "m": ("100 m", "ml"),
                "km": ("1000 m",), "t": ("tm", "kg")}
    for cod, um17 in unidades17.items():
        if cod in sbd_p_plano:
            um25 = sbd_p_plano[cod]["um"]
            if normalizar_texto(um17) != normalizar_texto(um25):
                equivalente = normalizar_texto(um25) in [
                    normalizar_texto(x) for x in um_equiv.get(
                        str(um17).lower().strip(), ())]
                cambios_um.append({"codigo": cod, "p17": um17, "sbd": um25,
                                   "equivalente": equivalente})
    resumen["H_unidades_2017_2025"] = {
        "comparadas": sum(1 for c in unidades17 if c in sbd_p_plano),
        "cambiadas": len(cambios_um),
        "equivalentes": sum(1 for c in cambios_um if c["equivalente"]),
        "detalle": sorted(cambios_um, key=lambda x: x["codigo"])[:80]}
    print(f"  unidades cambiadas 2017→2025: {len(cambios_um)}")

    # H3. HORAS OPERARIO/AYUDANTE (SBD tiene el campo; EMB no lo tiene)
    con_rop = sum(1 for d in sbd_p_plano.values()
                  if d["hrop"] not in (None, 0))
    con_ayu = sum(1 for d in sbd_p_plano.values()
                  if d["hayu"] not in (None, 0))
    resumen["H_horas_op_ayu"] = {
        "sbd_con_horas_operario": con_rop,
        "sbd_con_horas_ayudante": con_ayu,
        "emb_tiene_campo": False,
        "nota": "El campo existe en SBD 2025 (y PRECODI 2017) pero no en el "
                "catálogo embebido de PRECOST (no es un defecto de "
                "importación: la fuente PDF de PRECOST no lo publica)"}
    print(f"  SBD con HORAS OPERARIO ≠ 0: {con_rop:,}; AYUDANTE ≠ 0: {con_ayu:,}")

    # ------------------------------------------------------------- persistir
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=1, default=str)
    print(f"\nResultado completo: {SALIDA}")
    con.close()


if __name__ == "__main__":
    main()
