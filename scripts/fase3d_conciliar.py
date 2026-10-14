#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE III-D (paso 2) — Conciliación catálogo PRECODI (codigo.mdb 2017) ↔
catálogo embebido PRECOST (PRECONS III MICONS 2025).

Compara códigos, descripciones, unidades y precios SIN sobrescribir nada:
el catálogo embebido y las .mdb originales permanecen intactos.

Produce:
  docs/datos/fase3d_conciliacion.json — evidencia completa reproducible
  stdout — resumen de coincidencias/ausencias/conflictos

Reglas:
  - coincidencia exacta de código (6 dígitos partidas; 10 dígitos recursos)
  - descripciones normalizadas (mayúsculas, sin acentos, espacios colapsados)
  - unidades comparadas solo cuando semánticamente equivalentes
    (normalización minúsculas + prefijo multiplicador "100 x" → "x")
  - precios comparados por componente (mat/mo/eq/total) y documentados
    como bases de precios distintas (2017 vs 2025), no como conflictos
    de validez.

Uso:  python3 scripts/fase3d_conciliar.py
"""
import json
import logging
import os
import re
import statistics
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone

logging.getLogger("access_parser").setLevel(logging.CRITICAL)
from access_parser import AccessParser  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE = "/home/z/my-project/work/recuperacion/analisis/PRECODI"
BASE = "Codigo (PRECODI)/codigo.mdb"


def norm_txt(s):
    """Normaliza descripciones: mayúsculas, sin acentos, espacios simples."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().upper()


def norm_um(s):
    """Normaliza unidades: minúsculas; '100 m2' → 'm2' (se registra el factor)."""
    if s is None:
        return "", 1.0
    s = str(s).strip().lower()
    m = re.match(r"^([\d.,]+)\s*(.*)$", s)
    factor = 1.0
    if m and m.group(2):
        try:
            factor = float(m.group(1).replace(",", "."))
            s = m.group(2).strip()
        except ValueError:
            pass
    s = re.sub(r"\s+", " ", s)
    return s, factor


# Equivalencias de abreviaturas verificadas contra los datos (pares dominantes):
#   t↔tm (2471), m↔ml (1662), 100 m↔cm (142), 100 m2↔c2 (69), 100 m3↔c3 (33)
# Se registran por separado; NO se asumen equivalentes: ct (cientos), cu, dc
# (docena), d2 (10 m2), mm (1000 m2), hl — cambio de unidad aparente en 2025,
# verificación semántica pendiente.
EQUIV_UM = {("t", 1.0): ("tm", 1.0), ("m", 1.0): ("ml", 1.0),
            ("m", 100.0): ("cm", 1.0), ("m2", 100.0): ("c2", 1.0),
            ("m3", 100.0): ("c3", 1.0)}
EQUIV_UM_INV = {v: k for k, v in EQUIV_UM.items()}


def um_equivalentes(um_p, um_r):
    """True si las unidades normalizadas son iguales o abreviaturas equivalentes."""
    if um_p == um_r:
        return True
    return EQUIV_UM.get(um_p) == um_r or EQUIV_UM_INV.get(um_p) == um_r


def limpiar_desc_precost(s):
    """Quita artefactos de extracción PDF del catálogo PRECOST:
    sufijo de fuente 'L ista de Costos…' y cantidades de unidad pegadas al final
    (evidencia: descripciones con ' 100', ' 10', ' 1000' finales cuando la unidad
    cambió de ct/d2/dc/mm a u/m2 en 2025). Solo para comparar, nunca se altera
    el dato original."""
    if not s:
        return ""
    s = re.sub(r"\s*[Ll]\s?ista de Costos.*$", "", str(s))
    s = re.sub(r"\s+[0-9]{1,4}\s*$", "", s)
    return s.strip()


def similitud(a, b):
    """Similitud Jaccard de tokens de palabras (0..1)."""
    ta, tb = set(norm_txt(a).split()), set(norm_txt(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def main():
    # ---------- PRECOST ----------
    precost = json.load(open(os.path.join(REPO, "docs", "datos", "fase3d_precost_db.json"), encoding="utf-8"))
    P, M, O, E, G = precost["P"], precost["M"], precost["O"], precost["E"], precost["G"]

    # ---------- PRECODI ----------
    print(f"Cargando {BASE} (solo lectura)...")
    db = AccessParser(os.path.join(FUENTE, BASE))

    def rows(nombre):
        t = db.parse_table(nombre)
        return [dict(zip(t, v)) for v in zip(*t.values())]

    rv = rows("Nomenclador de RV")
    rv_por_codigo = {}
    for r in rv:
        c = str(r.get("CODIGO RV", "")).strip()
        if c and c not in rv_por_codigo:
            rv_por_codigo[c] = r
    mat = {str(r["CodMat"]): r for r in rows("Nomenclador de Materiales")}
    rh = {str(r["CodRHum"]): r for r in rows("Nomenclador de Mano de Obra")}
    eq = {str(r["CodEquipo"]): r for r in rows("Nomenclador de Equipos")}
    sg = {str(r["CodSobreG"]): r for r in rows("Nomenclador de SobreGrupos RV")}
    gr = {(str(r["CodSobreG"]), str(r["CodG"])): r for r in rows("Nomenclador de Grupos RV")}
    sub = {(str(r["CodSobreG"]), str(r["CodG"]), str(r["CodSubG"])): r
           for r in rows("Nomenclador de SubGrupos RV")}

    def f(v):
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    resultado = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "fuentes": {
            "precost": {"nombre": precost["meta"]["nombre"],
                        "publicada": precost["meta"]["publicada"],
                        "fuente": precost["meta"]["fuente"],
                        "origen": "embebido en app/PRECOST-v9.17.html (const DB), extraído sin modificar"},
            "precodi": {"nombre": "codigo.mdb (raíz, junto a Codigo.exe)",
                        "formato": "Jet 4 (Access 2000), mtime 2017",
                        "origen": "AUXILIAR_PRECODI.rar (Google Drive 2), extraído a copia de análisis"},
        },
    }

    # ============ 1. PARTIDAS (P ↔ Nomenclador de RV) ============
    print("\n=== 1. PARTIDAS: P (PRECOST) ↔ Nomenclador de RV (PRECODI) ===")
    cods_p = set(P)
    cods_rv = set(rv_por_codigo)
    inter = cods_p & cods_rv
    solo_p = cods_p - cods_rv
    solo_rv = cods_rv - cods_p

    desc_iguales = desc_parecidas = desc_distintas = 0
    um_eq = um_equiv_abrev = um_dist = 0
    ej_conflicto_desc, ej_conflicto_um = [], []
    detalle_um_dist = Counter()
    ratios_total = []
    comp_mat_eq = comp_mo_eq = comp_eq_eq = comp_verif = 0

    for c in sorted(inter):
        p, r = P[c], rv_por_codigo[c]
        # descripción (con limpieza de artefactos de PRECOST, solo para comparar)
        dp, dr = norm_txt(limpiar_desc_precost(p[0])), norm_txt(r.get("Desc Rv"))
        if dp == dr:
            desc_iguales += 1
        else:
            s = similitud(limpiar_desc_precost(p[0]), r.get("Desc Rv"))
            if s >= 0.6:
                desc_parecidas += 1
            else:
                desc_distintas += 1
                if len(ej_conflicto_desc) < 8:
                    ej_conflicto_desc.append({"codigo": c, "precost": p[0][:70],
                                              "precodi": str(r.get("Desc Rv"))[:70],
                                              "similitud": round(s, 2)})
        # unidad
        up, fp_ = norm_um(p[1])
        ur, fr_ = norm_um(r.get("UNIDAD DE MEDIDA"))
        if up == ur and fp_ == fr_:
            um_eq += 1
        elif um_equivalentes((up, fp_), (ur, fr_)):
            um_equiv_abrev += 1
        else:
            um_dist += 1
            detalle_um_dist[(p[1].strip().lower(), str(r.get("UNIDAD DE MEDIDA")).strip().lower())] += 1
            if len(ej_conflicto_um) < 8:
                ej_conflicto_um.append({"codigo": c, "precost": p[1],
                                        "precodi": str(r.get("UNIDAD DE MEDIDA"))})
        # precio total (documentado como bases distintas)
        total_p = f(p[2])
        total_r = (f(r.get("CMMN")) or 0) + (f(r.get("CHMN")) or 0) + (f(r.get("CEMN")) or 0)
        if total_p and total_r:
            ratios_total.append(total_p / total_r)
        # componentes (solo cuando ambos difieren de cero — señal de misma estructura)
        if (f(p[3]) or 0) > 0 and (f(r.get("CMMN")) or 0) > 0:
            comp_verif += 1
            if (f(p[3]) or 0) < 0.01 * (f(r.get("CMMN")) or 1):
                pass
        if (f(p[4]) or 0) > 0 and (f(r.get("CHMN")) or 0) > 0:
            comp_mo_eq += 1
        if (f(p[5]) or 0) > 0 and (f(r.get("CEMN")) or 0) > 0:
            comp_eq_eq += 1

    # distribución de capítulos PRECOST vs sobregrupos PRECODI
    caps_p = Counter(p[7] for p in P.values() if len(p) > 7)
    caps_rv = Counter(str(r.get("CodSobreG")) for r in rv_por_codigo.values())

    resultado["partidas"] = {
        "precost_total": len(P), "precodi_total": len(rv_por_codigo),
        "coincidencia_exacta_codigo": len(inter),
        "solo_precost": len(solo_p), "solo_precodi": len(solo_rv),
        "cobertura_precost_sobre_precodi": round(len(inter) / len(cods_rv), 4),
        "cobertura_precodi_sobre_precost": round(len(inter) / len(cods_p), 4),
        "descripcion": {"iguales": desc_iguales, "parecidas(jaccard>=0.6)": desc_parecidas,
                        "distintas": desc_distintas, "ejemplos_conflicto": ej_conflicto_desc},
        "unidad": {"iguales": um_eq, "equivalentes_por_abreviatura": um_equiv_abrev,
                   "distintas_o_cambio_de_unidad": um_dist,
                   "detalle_pares_distintos": {f"{a!r}↔{b!r}": n for (a, b), n in detalle_um_dist.most_common(15)},
                   "nota": "Equivalencias aplicadas (verificadas por frecuencia dominante): "
                            "t↔tm, m↔ml, 100 m↔cm, 100 m2↔c2, 100 m3↔c3. Los pares restantes "
                            "(u↔ct, u↔cu, u↔dc, m2↔d2, m2↔mm, l↔hl) corresponden a partidas "
                            "cuya unidad cambió en PRECONS III 2025 (p.ej. de cientos o decenas "
                            "a unidades simples): quedan como verificación semántica pendiente.",
                   "ejemplos_conflicto": ej_conflicto_um},
        "precios": {
            "nota": "Bases de precios distintas (PRECODI 2017 MN vs PRECONS III MICONS 2025): "
                    "no son conflictos de validez; se documenta el cambio de base.",
            "ratio_total_2025_2017": {
                "n": len(ratios_total),
                "mediana": round(statistics.median(ratios_total), 2) if ratios_total else None,
                "p10": round(statistics.quantiles(ratios_total, n=10)[0], 2) if len(ratios_total) >= 10 else None,
                "p90": round(statistics.quantiles(ratios_total, n=10)[8], 2) if len(ratios_total) >= 10 else None,
            },
            "partidas_con_componente_mat_ambos": comp_verif,
            "partidas_con_componente_mo_ambos": comp_mo_eq,
            "partidas_con_componente_eq_ambos": comp_eq_eq,
        },
        "capitulos_precost": dict(caps_p.most_common()),
        "sobregrupos_precodi": dict(caps_rv.most_common()),
        "ejemplos_solo_precost": sorted(solo_p)[:15],
        "ejemplos_solo_precodi": sorted(solo_rv)[:15],
    }
    p_res = resultado["partidas"]
    print(f"  Códigos: PRECOST {len(P)} · PRECODI {len(rv_por_codigo)} · intersección {len(inter)}"
          f" · solo PRECOST {len(solo_p)} · solo PRECODI {len(solo_rv)}")
    print(f"  Descripción: {desc_iguales} iguales · {desc_parecidas} parecidas · {desc_distintas} distintas")
    print(f"  Unidad: {um_eq} iguales · {um_equiv_abrev} equivalentes (abreviatura) · {um_dist} distintas/cambio")
    print(f"  Ratio total 2025/2017: mediana {p_res['precios']['ratio_total_2025_2017']['mediana']}")

    # ============ 2. MATERIALES (M ↔ Nomenclador de Materiales) ============
    print("\n=== 2. MATERIALES ===")
    # materiales: comparación con limpieza de artefactos
    inter_m = set(M) & set(mat)
    desc_m_eq = desc_m_par = desc_m_dis = 0
    ej_m = []
    for c in inter_m:
        d_p = limpiar_desc_precost(M[c][0])
        if norm_txt(d_p) == norm_txt(mat[c]["Material"]):
            desc_m_eq += 1
        elif similitud(d_p, mat[c]["Material"]) >= 0.6:
            desc_m_par += 1
        else:
            desc_m_dis += 1
            if len(ej_m) < 5:
                ej_m.append({"codigo": c, "precost": M[c][0][:60], "precodi": str(mat[c]["Material"])[:60]})
    resultado["materiales"] = {
        "precost_total": len(M), "precodi_total": len(mat),
        "coincidencia_exacta": len(inter_m),
        "solo_precost": len(set(M) - set(mat)), "solo_precodi": len(set(mat) - set(M)),
        "descripcion": {"iguales": desc_m_eq, "parecidas": desc_m_par, "distintas": desc_m_dis,
                        "ejemplos_conflicto": ej_m},
    }
    print(f"  {len(M)} ↔ {len(mat)} · intersección {len(inter_m)} · "
          f"desc iguales {desc_m_eq} / parecidas {desc_m_par} / distintas {desc_m_dis}")

    # ============ 3. MANO DE OBRA (O ↔ Nomenclador de Mano de Obra) ============
    print("\n=== 3. MANO DE OBRA ===")
    inter_o = set(O) & set(rh)
    resultado["mano_obra"] = {
        "precost_total": len(O), "precodi_total": len(rh),
        "coincidencia_exacta": len(inter_o),
        "solo_precost": len(set(O) - set(rh)), "solo_precodi": len(set(rh) - set(O)),
    }
    print(f"  {len(O)} ↔ {len(rh)} · intersección {len(inter_o)}")

    # ============ 4. EQUIPOS (E ↔ Nomenclador de Equipos) ============
    print("\n=== 4. EQUIPOS ===")
    inter_e = set(E) & set(eq)
    resultado["equipos"] = {
        "precost_total": len(E), "precodi_total": len(eq),
        "coincidencia_exacta": len(inter_e),
        "solo_precost": len(set(E) - set(eq)), "solo_precodi": len(set(eq) - set(E)),
    }
    print(f"  {len(E)} ↔ {len(eq)} · intersección {len(inter_e)}")

    # ============ 5. GRUPOS (G ↔ jerarquía SobreG/Grupos/SubGrupos) ============
    print("\n=== 5. GRUPOS (jerarquía) ===")
    g_por_long = Counter(len(k) for k in G)
    # hipótesis: 2 dígitos=sobregrupo, 3=grupo, 4=subgrupo (verificar contra PRECODI)
    sg_prec = {k: v for k, v in G.items() if len(k) == 2}
    gr_prec = {k: v for k, v in G.items() if len(k) == 3}
    sub_prec = {k: v for k, v in G.items() if len(k) == 4}
    otros_g = {k: v for k, v in G.items() if len(k) not in (2, 3, 4)}

    sg_iguales = sum(1 for k in sg_prec if k in sg and
                     norm_txt(sg_prec[k][0]) == norm_txt(sg[k]["SubreGrupo"]))
    gr_iguales = 0
    for k, v in gr_prec.items():
        r = gr.get((k[:2], k))
        if r and norm_txt(v[0]) == norm_txt(r["Grupo"]):
            gr_iguales += 1
    sub_iguales = 0
    for k, v in sub_prec.items():
        r = sub.get((k[:2], k[:3], k))
        if r and norm_txt(v[0]) == norm_txt(r["SubGrupo"]):
            sub_iguales += 1

    resultado["grupos"] = {
        "precost_total": len(G), "distribucion_longitudes": dict(g_por_long),
        "hipotesis_estructura": "2 dígitos=SobreGrupo, 3=Grupo, 4=SubGrupo (verificada abajo)",
        "sobregrupos": {"precost": len(sg_prec), "precodi": len(sg),
                        "coincidencia_codigo": len(set(sg_prec) & set(sg)),
                        "descripcion_igual": sg_iguales},
        "grupos": {"precost": len(gr_prec), "precodi": len(gr),
                   "coincidencia_codigo": sum(1 for k in gr_prec if (k[:2], k) in gr),
                   "descripcion_igual": gr_iguales},
        "subgrupos": {"precost": len(sub_prec), "precodi": len(sub),
                      "coincidencia_codigo": sum(1 for k in sub_prec if (k[:2], k[:3], k) in sub),
                      "descripcion_igual": sub_iguales},
        "otros": {"cantidad": len(otros_g), "ejemplos": {k: v for k, v in list(otros_g.items())[:5]}},
    }
    print(f"  G: {len(G)} → 2d:{len(sg_prec)} 3d:{len(gr_prec)} 4d:{len(sub_prec)} otros:{len(otros_g)}")
    print(f"  SobreGrupos con código igual: {len(set(sg_prec) & set(sg))}/{len(sg)} · desc igual: {sg_iguales}")

    # ============ 6. Descomposiciones ============
    print("\n=== 6. DESCOMPOSICIONES (normas) ===")
    # ¿PRECODI tiene normas para los códigos compartidos con PRECOST?
    normas_rv = set()
    for t in ("Norma de Materiales", "Norma de Mano de Obra", "Norma de Equipos",
              "Norma de Juegos", "Norma de Semielaborados"):
        try:
            for r in rows(t):
                normas_rv.add(str(r["CodigoRV"]))
        except Exception:  # noqa: BLE001
            pass
    compartidas_con_norma = len(inter & normas_rv)
    resultado["descomposiciones"] = {
        "rvs_precodi_con_norma": len(normas_rv),
        "codigos_compartidos": len(inter),
        "compartidos_con_norma_precodi": compartidas_con_norma,
        "precost_tiene_descomposicion": False,
        "nota": "El catálogo embebido PRECOST solo almacena costos agregados por partida "
                "(mat/mo/eq/total/peso) y precios unitarios de recursos: NO contiene "
                "descomposiciones (coeficientes de consumo). Las normas de consumo "
                "existen únicamente en PRECODI — oportunidad clave de integración.",
    }
    print(f"  RVs PRECODI con norma: {len(normas_rv)} · compartidos con norma: {compartidas_con_norma}")

    with open(os.path.join(REPO, "docs", "datos", "fase3d_conciliacion.json"), "w", encoding="utf-8") as fp:
        json.dump(resultado, fp, ensure_ascii=False, indent=1)
    print("\n-> docs/datos/fase3d_conciliacion.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
