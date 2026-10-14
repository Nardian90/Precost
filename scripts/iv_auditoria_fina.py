#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MISIÓN IV — Línea A (paso 2): clasificación fina de las diferencias.

Partiendo de fidelidad_iv.json y de las fuentes, reclasifica:

  1. Diferencias de precio EMB↔SBD:
     - ¿EMB.mat == redondeo(SBD.cmmn, 2)?  → dif_redondeo_presentacion
     - ¿EMB.total == EMB.mat+EMB.mo+EMB.eq (componentes redondeados)?
  2. Diferencias de unidad EMB↔SBD:
     - tabulación de pares (um_emb, um_sbd) con conteos
     - verificación de equivalencia semántica con las parejas conocidas
  3. Diferencias de descripción: artefactos PDF conocidos (sufijos) vs reales
  4. PESO: EMB vs SBD vs PRECODI 2017 (¿dónde vive el peso?)
  5. El código de equipo presente solo en EMB
  6. Normas: solo para partidas compartidas 2017↔2025
"""
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import precision_precodi  # noqa: E402
precision_precodi.parchear_money_exacto()
from access_parser import AccessParser  # noqa: E402

SBD_RUTA = ("/home/z/my-project/work/siecons_extract/payload/"
            "BD/SBD_11/SBD_11_MICONS_2025/SBD_MICONS_2025.mdb")
BD = os.path.join(REPO, "bd", "precodi.db")
ENTRADA = os.path.join(REPO, "docs", "datos", "fidelidad_iv.json")
SALIDA = os.path.join(REPO, "docs", "datos", "fidelidad_iv_fina.json")


def a_numero(v):
    from decimal import Decimal
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
    return re.sub(r"\s+", " ", str(s).upper()).strip()


def main():
    res = json.load(open(ENTRADA, encoding="utf-8"))
    fina = {"base": "fidelidad_iv.json", "origen_sha_html":
            "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"}

    # recargar EMB + SBD (solo lo necesario)
    import fase3d_extraer_catalogo as f3d
    html = open(os.path.join(REPO, "app", "PRECOST-v9.17.html"),
                encoding="utf-8").read()
    m = re.search(r"const\s+DB\s*=\s*", html)
    ini = html.index("{", m.end())
    emb = json.loads(f3d.extraer_objeto_js(html, ini))

    db = AccessParser(SBD_RUTA)
    rv = db.get_table("Nomenclador de RV").parse()
    sbd_rv = {}
    for i, cod in enumerate(rv["CODIGO RV"]):
        sbd_rv[str(cod)] = dict(
            desc=rv["Desc Rv"][i], um=rv["UNIDAD DE MEDIDA"][i],
            cmmn=a_numero(rv["CMMN"][i]), chmn=a_numero(rv["CHMN"][i]),
            cemn=a_numero(rv["CEMN"][i]),
            peso=a_numero(rv["PESO"][i]),
            hh=a_numero(rv["HORAS HOMBRE"][i]),
            hrop=a_numero(rv["HORAS OPERARIO"][i]),
            hayu=a_numero(rv["HORAS AYUDANTE"][i]))

    con = sqlite3.connect(f"file:{BD}?mode=ro", uri=True)
    cur = con.cursor()
    p17 = {}
    for fila in cur.execute(
            "SELECT codigo, descripcion, unidad, costo_mat_mn, costo_mo_mn, "
            "costo_eq_mn, costo_total_mn, peso_kg FROM partidas "
            "WHERE version_id=3"):
        p17[fila[0]] = dict(desc=fila[1], um=fila[2], mat=fila[3],
                            mo=fila[4], eq=fila[5], total=fila[6],
                            peso=fila[7])

    # ---------------------------------------------- 1. precios: redondeo
    print("[1] Clasificación fina de diferencias de precio EMB↔SBD")
    clasificacion = Counter()
    ej = defaultdict(list)
    for cod, e in emb["P"].items():
        s = sbd_rv.get(cod)
        if not s:
            continue
        e_desc, e_um, e_total, e_mat, e_mo, e_eq, e_peso = e[0], e[1], \
            a_numero(e[2]), a_numero(e[3]), a_numero(e[4]), \
            a_numero(e[5]), a_numero(e[6])
        for campo, ve, vs in (("mat", e_mat, s["cmmn"]),
                              ("mo", e_mo, s["chmn"]),
                              ("eq", e_eq, s["cemn"])):
            if vs is None or ve is None:
                clasificacion[f"{campo}:no_verificable"] += 1
                continue
            if ve == vs:
                clasificacion[f"{campo}:exacto"] += 1
            elif abs(ve - round(vs, 2)) < 1e-9:
                clasificacion[f"{campo}:redondeo_2dec"] += 1
            else:
                clasificacion[f"{campo}:dif_real"] += 1
                if len(ej[f"{campo}:dif_real"]) < 8:
                    ej[f"{campo}:dif_real"].append(
                        {"codigo": cod, "emb": ve, "sbd": vs})
        # total: ¿suma de componentes redondeados?
        s_total = (s["cmmn"] or 0) + (s["chmn"] or 0) + (s["cemn"] or 0)
        comp_sum = (round(s["cmmn"] or 0, 2) + round(s["chmn"] or 0, 2)
                    + round(s["cemn"] or 0, 2))
        if e_total is None:
            clasificacion["total:no_verificable"] += 1
        elif abs(e_total - comp_sum) < 1e-9:
            clasificacion["total:suma_componentes_redondeados"] += 1
        elif abs(e_total - round(s_total, 2)) < 1e-9:
            clasificacion["total:redondeo_directo"] += 1
        else:
            clasificacion["total:dif_real"] += 1
            if len(ej["total:dif_real"]) < 8:
                ej["total:dif_real"].append(
                    {"codigo": cod, "emb": e_total, "sbd": s_total,
                     "suma_comp_red": round(comp_sum, 2)})
    fina["1_precios"] = dict(clasificacion)
    fina["1_ejemplos_dif_real"] = {k: v for k, v in ej.items()}
    for k, v in sorted(clasificacion.items()):
        print(f"  {k}: {v:,}")

    # ---------------------------------------------- 2. unidades
    print("\n[2] Pares de unidades EMB↔SBD (top 40)")
    pares = Counter()
    detalles_pares = defaultdict(list)
    for cod, e in emb["P"].items():
        s = sbd_rv.get(cod)
        if not s:
            continue
        if normalizar_texto(e[1]) != normalizar_texto(s["um"]):
            pares[(str(e[1]).strip(), str(s["um"]).strip())] += 1
            if len(detalles_pares[(str(e[1]).strip(), str(s["um"]).strip())]) < 3:
                detalles_pares[(str(e[1]).strip(), str(s["um"]).strip())].append(cod)
    pares_orden = sorted(pares.items(), key=lambda kv: -kv[1])
    for (a, b), n in pares_orden[:40]:
        print(f"  EMB {a!r:<12} ↔ SBD {b!r:<10} : {n:,}")
    fina["2_pares_unidades"] = [
        {"emb": a, "sbd": b, "conteo": n,
         "ejemplos": detalles_pares[(a, b)][:3]}
        for (a, b), n in pares_orden]
    print(f"  total pares distintos: {len(pares_orden)}")

    # ---------------------------------------------- 3. descripciones
    print("\n[3] Descripciones EMB↔SBD diferentes (clasificación)")
    desc_clases = Counter()
    ej_desc = defaultdict(list)
    artefactos = Counter()
    for cod, e in emb["P"].items():
        s = sbd_rv.get(cod)
        if not s:
            continue
        de, ds = str(e[0]).strip(), str(s["desc"]).strip()
        if de == ds:
            desc_clases["exacta"] += 1
            continue
        if normalizar_texto(de) == normalizar_texto(ds):
            # espacios/puntuación
            desc_clases["equivalente_espacios"] += 1
            continue
        # artefactos conocidos del PDF (III-D)
        d_clean = re.sub(r"\s*LISTA DE COSTOS\s*$", "", de, flags=re.I)
        if normalizar_texto(d_clean) == normalizar_texto(ds):
            artefactos["sufijo_lista_de_costos"] += 1
            continue
        # sufijo numérico final (cambio de unidad documentado en III-D)
        d_clean2 = re.sub(r"\s+\d+(\.\d+)?\s*$", "", de)
        if normalizar_texto(d_clean2) == normalizar_texto(ds):
            artefactos["sufijo_numerico_unidad"] += 1
            continue
        # prefijo de sección en descripción SBD
        s_clean = re.sub(r"^\s*\d+\s*[-.]\s*", "", ds)
        if normalizar_texto(de) == normalizar_texto(s_clean):
            artefactos["prefijo_seccion_sbd"] += 1
            continue
        if normalizar_texto(de) in normalizar_texto(ds) or \
                normalizar_texto(ds) in normalizar_texto(de):
            desc_clases["contenida_parcial"] += 1
            if len(ej_desc["contenida_parcial"]) < 8:
                ej_desc["contenida_parcial"].append(
                    {"codigo": cod, "emb": de[:70], "sbd": ds[:70]})
            continue
        desc_clases["diferente"] += 1
        if len(ej_desc["diferente"]) < 12:
            ej_desc["diferente"].append(
                {"codigo": cod, "emb": de[:70], "sbd": ds[:70]})
    fina["3_descripciones"] = {"clases": dict(desc_clases),
                               "artefactos_pdf": dict(artefactos),
                               "ejemplos": {k: v for k, v in ej_desc.items()}}
    print(f"  {dict(desc_clases)}")
    print(f"  artefactos PDF: {dict(artefactos)}")

    # ---------------------------------------------- 4. peso
    print("\n[4] PESO: EMB vs SBD vs PRECODI 2017")
    peso_stats = Counter()
    ej_peso = []
    for cod, e in emb["P"].items():
        s = sbd_rv.get(cod)
        p = p17.get(cod)
        e_peso = a_numero(e[6])
        s_peso = s["peso"] if s else None
        p_peso = p["peso"] if p else None
        if s and p:
            if e_peso and s_peso:
                peso_stats["emb_y_sbd_con_peso"] += 1
                if abs(e_peso - s_peso) <= 0.005:
                    peso_stats["peso_igual_emb_sbd"] += 1
                else:
                    peso_stats["peso_dif_emb_sbd"] += 1
            elif e_peso and not s_peso:
                if p_peso and abs(e_peso - p_peso) <= 0.005:
                    peso_stats["emb=2017_sbd_vacio"] += 1
                else:
                    peso_stats["emb_con_peso_sbd_sin_peso"] += 1
                    if len(ej_peso) < 8:
                        ej_peso.append({"codigo": cod, "emb": e_peso,
                                        "sbd": s_peso, "p17": p_peso})
            elif not e_peso and s_peso:
                peso_stats["sbd_con_peso_emb_sin"] += 1
            else:
                peso_stats["ambos_sin_peso"] += 1
    fina["4_peso"] = {"clases": dict(peso_stats), "ejemplos": ej_peso}
    print(f"  {dict(peso_stats)}")

    # ---------------------------------------------- 5. equipo solo EMB
    print("\n[5] Código de equipo solo en EMB")
    eq_sbd = {str(c) for c in db.get_table("Nomenclador de Equipos")
              .parse()["CodEquipo"]}
    solo = [c for c in emb["E"] if c not in eq_sbd]
    fina["5_equipo_solo_emb"] = [
        {"codigo": c, "registro": emb["E"][c]} for c in solo]
    print(f"  {solo}: {[(c, emb['E'][c]) for c in solo]}")

    # ---------------------------------------------- 6. normas compartidas
    print("\n[6] Normas P17↔SBD solo en partidas compartidas")
    rv17 = set(p17)
    rv_sbd = set(sbd_rv)
    compartidas = rv17 & rv_sbd
    tipo_map = {"Material": ("norma_mat", "CodigoRV", "CodMat", "CantMat"),
                "Mano de obra": ("norma_mo", "CodigoRV", "CodRHum", "CantRHum"),
                "Equipo": ("norma_eq", "CodigoRV", "CodEquipo", "CantEquipo"),
                "Juego de trabajo": ("norma_juegos", "CodigoRV", "CodJuego",
                                     "CantJuego"),
                "Semielaborado": ("norma_semi", "CodigoRV", "CodSElab",
                                  "CantSElab")}
    normas_sbd = defaultdict(dict)
    for tipo, (tabla, c_rv, c_rec, c_cant) in tipo_map.items():
        t = db.get_table({
            "norma_mat": "Norma de Materiales",
            "norma_mo": "Norma de Mano de Obra",
            "norma_eq": "Norma de Equipos",
            "norma_juegos": "Norma de Juegos",
            "norma_semi": "Norma de Semielaborados"}[tabla]).parse()
        for i in range(len(t[c_rv])):
            rv_c = str(t[c_rv][i])
            if rv_c in compartidas:
                normas_sbd[(rv_c, tipo, str(t[c_rec][i]))] = \
                    a_numero(t[c_cant][i])
    normas_17 = {}
    for fila in cur.execute("""
            SELECT p.codigo, tr.nombre, n.codigo_recurso, n.coeficiente
            FROM normas_partida n
            JOIN partidas p ON n.partida_id = p.id
            JOIN tipos_recurso tr ON n.tipo_recurso_id = tr.id
            WHERE p.version_id = 3"""):
        if fila[0] in compartidas:
            normas_17[(fila[0], fila[1], str(fila[2]))] = fila[3]
    n_stats = Counter()
    ej_n = []
    for k in set(normas_17) & set(normas_sbd):
        a, b = normas_17[k], normas_sbd[k]
        if a is None or b is None:
            continue
        if a == b:
            n_stats["igual"] += 1
        elif abs(a - b) <= max(abs(a), abs(b)) * 1e-6:
            n_stats["tol_float32"] += 1
        else:
            n_stats["diferente"] += 1
            if len(ej_n) < 10:
                ratio = b / a if a else None
                ej_n.append({"clave": list(k), "p17": a, "sbd": b,
                             "ratio": round(ratio, 4) if ratio else None})
    fina["6_normas_compartidas"] = {
        "partidas_compartidas": len(compartidas),
        "normas_17": len(normas_17), "normas_sbd": len(normas_sbd),
        "interseccion": len(set(normas_17) & set(normas_sbd)),
        "clases": dict(n_stats), "ejemplos_diferentes": ej_n,
        "solo_en_2017": len(set(normas_17) - set(normas_sbd)),
        "solo_en_2025": len(set(normas_sbd) - set(normas_17))}
    print(f"  partidas compartidas: {len(compartidas):,}")
    print(f"  {dict(n_stats)}")
    print(f"  solo 2017: {fina['6_normas_compartidas']['solo_en_2017']:,}; "
          f"solo 2025: {fina['6_normas_compartidas']['solo_en_2025']:,}")

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(fina, f, ensure_ascii=False, indent=1, default=str)
    print(f"\nResultado: {SALIDA}")
    con.close()


if __name__ == "__main__":
    main()
