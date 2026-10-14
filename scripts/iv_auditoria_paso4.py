#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MISIÓN IV — Línea A (paso 4): cierre de la auditoría de fidelidad.

  1. Descripciones: normalización agresiva (sin espacios / sin puntuación)
     para separar artefactos de PDF de diferencias reales.
  2. Diferencias de precio > 0.5 (reales): lista completa.
  3. Inconsistencias internas de EMB (total != mat+mo+eq).
  4. Verificación semántica de unidades EMB 'u' vs SBD 'ct'/'cu'/'dc' y
     'm2' vs 'd2'/'mm': ¿el precio cambia con la unidad o es solo notación?
"""
import json
import os
import re
import sqlite3
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import precision_precodi  # noqa: E402
precision_precodi.parchear_money_exacto()
from access_parser import AccessParser  # noqa: E402

SBD_RUTA = ("/home/z/my-project/work/siecons_extract/payload/"
            "BD/SBD_11/SBD_11_MICONS_2025/SBD_MICONS_2025.mdb")


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


def sin_espacios(s):
    return re.sub(r"\s+", "", str(s or "").upper())


def sin_puntuacion(s):
    return re.sub(r"[^A-Z0-9]", "", str(s or "").upper())


def main():
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
            desc=str(rv["Desc Rv"][i] or ""),
            um=str(rv["UNIDAD DE MEDIDA"][i] or ""),
            cmmn=a_numero(rv["CMMN"][i]), chmn=a_numero(rv["CHMN"][i]),
            cemn=a_numero(rv["CEMN"][i]))

    con = sqlite3.connect(f"file:{os.path.join(REPO, 'bd', 'precodi.db')}?mode=ro",
                          uri=True)
    cur = con.cursor()
    p17 = {f[0]: f[1] for f in cur.execute(
        "SELECT codigo, unidad FROM partidas WHERE version_id=3")}

    resultado = {}

    # ------------------------------------------- 1. descripciones agresivo
    print("[1] Descripciones EMB↔SBD con normalización agresiva")
    clases = Counter()
    ej_real = []
    for cod, e in emb["P"].items():
        s = sbd_rv.get(cod)
        if not s:
            continue
        de, ds = str(e[0]).strip(), s["desc"].strip()
        if de == ds:
            clases["exacta"] += 1
        elif sin_espacios(de) == sin_espacios(ds):
            clases["equivalente_espaciado_pdf"] += 1
        elif sin_puntuacion(de) == sin_puntuacion(ds):
            clases["equivalente_puntuacion_pdf"] += 1
        else:
            # artefactos de sufijo
            d1 = re.sub(r"\s*LISTA DE COSTOS\s*$", "", de, flags=re.I)
            d2 = re.sub(r"\s+\d+(\.\d+)?\s*$", "", de)
            if sin_puntuacion(d1) == sin_puntuacion(ds) or \
                    sin_puntuacion(d2) == sin_puntuacion(ds):
                clases["artefacto_sufijo_pdf"] += 1
            elif sin_puntuacion(de).startswith(sin_puntuacion(ds)) or \
                    sin_puntuacion(ds).startswith(sin_puntuacion(de)):
                clases["truncada_pdf"] += 1
            else:
                clases["diferente_real"] += 1
                if len(ej_real) < 15:
                    ej_real.append({"codigo": cod, "emb": de, "sbd": ds})
    resultado["1_descripciones"] = {"clases": dict(clases),
                                    "ejemplos_reales": ej_real}
    print(f"  {dict(clases)}")

    # ------------------------------------------- 2. precios > 0.5
    print("\n[2] Diferencias de precio EMB↔SBD mayores que 0.5")
    grandes = []
    for campo, idx, col in (("mat", 3, "cmmn"), ("mo", 4, "chmn"),
                            ("eq", 5, "cemn")):
        for cod, e in emb["P"].items():
            s = sbd_rv.get(cod)
            if not s or s[col] is None:
                continue
            ve = a_numero(e[idx])
            if ve is None:
                continue
            if abs(ve - s[col]) > 0.5:
                grandes.append({"campo": campo, "codigo": cod,
                                "emb": ve, "sbd": s[col],
                                "delta": round(ve - s[col], 2),
                                "um_emb": e[1], "um_sbd": s["um"]})
    grandes.sort(key=lambda x: -abs(x["delta"]))
    resultado["2_precios_grandes"] = grandes
    print(f"  total: {len(grandes)}")
    for g in grandes[:15]:
        print(f"  {g['campo']} {g['codigo']}: EMB {g['emb']} vs "
              f"SBD {g['sbd']} (Δ {g['delta']}, um {g['um_emb']!r}/"
              f"{g['um_sbd']!r})")

    # ------------------------------------------- 3. inconsistencia interna
    print("\n[3] Inconsistencias internas EMB (total != mat+mo+eq)")
    incons = []
    for cod, e in emb["P"].items():
        total, mat, mo, eq = (a_numero(e[2]), a_numero(e[3]),
                              a_numero(e[4]), a_numero(e[5]))
        if None in (total, mat, mo, eq):
            continue
        if abs(total - (mat + mo + eq)) >= 1e-9:
            incons.append({"codigo": cod, "total": total, "mat": mat,
                           "mo": mo, "eq": eq,
                           "desvio": round(total - (mat + mo + eq), 4)})
    resultado["3_inconsistencias_emb"] = incons
    print(f"  total: {len(incons)}")
    for i2 in incons[:10]:
        print(f"  {i2}")

    # ------------------------------------------- 4. unidades semántica
    print("\n[4] Unidades EMB↔SBD: verificación semántica")
    # pares a examinar: los que NO son notación obvia (t/tm, m/ml, 100m/cm…)
    pares_riesgo = {"ct", "cu", "dc", "d2", "mm", "hl"}
    casos = []
    for cod, e in emb["P"].items():
        s = sbd_rv.get(cod)
        if not s:
            continue
        um_s = s["um"].strip().lower()
        um_e = str(e[1]).strip().lower()
        if um_s in pares_riesgo and um_e != um_s:
            casos.append({
                "codigo": cod, "um_emb": e[1], "um_sbd": s["um"],
                "um_p17": p17.get(cod),
                "total_emb": a_numero(e[2]),
                "total_sbd": (s["cmmn"] or 0) + (s["chmn"] or 0)
                             + (s["cemn"] or 0),
                "desc": str(e[0])[:50]})
    resultado["4_unidades_riesgo"] = casos
    print(f"  casos con UM SBD de riesgo (ct/cu/dc/d2/mm/hl): {len(casos)}")
    # análisis: ¿precio igual (notación) o distinto (semántica)?
    mismo_precio = sum(1 for c in casos
                       if c["total_emb"] is not None and
                       abs(c["total_emb"] - c["total_sbd"]) <= 0.011)
    print(f"  con el MISMO precio (solo notación): {mismo_precio}")
    print(f"  con precio DISTINTO (posible semántica): "
          f"{len(casos) - mismo_precio}")
    for c in casos[:12]:
        print(f"    {c['codigo']}: um EMB {c['um_emb']!r} / SBD {c['um_sbd']!r}"
              f" / P17 {c['um_p17']!r} — total EMB {c['total_emb']} vs "
              f"SBD {round(c['total_sbd'], 2)}")

    with open(os.path.join(REPO, "docs", "datos", "fidelidad_iv_paso4.json"),
              "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1, default=str)
    print("\nGuardado: docs/datos/fidelidad_iv_paso4.json")
    con.close()


if __name__ == "__main__":
    main()
