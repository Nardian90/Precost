#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MISIÓN IV — Línea A (paso 3): distribución de diferencias de precio.

Hipótesis a verificar: EMB (catálogo publicado, 2 decimales) y SBD (base
interna de SIECONS, 4 decimales) comparten los mismos valores subyacentes;
las diferencias son ruido de redondeo de la publicación oficial (±0.01).

Se mide:
  1. distribución de (EMB.campo − SBD.campo) y de (EMB.campo − round(SBD,2))
  2. consistencia interna de EMB: total == mat+mo+eq
  3. distribución de ratios en normas 2017↔2025 (cambios reales de versión)
  4. tarifa MO: EMB.O (2 dec) vs SBD.RH (4 dec) — mismo patrón
"""
import json
import os
import re
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
            cmmn=a_numero(rv["CMMN"][i]), chmn=a_numero(rv["CHMN"][i]),
            cemn=a_numero(rv["CEMN"][i]))

    # 1. distribución de diferencias
    print("[1] Distribución de (EMB − SBD) por campo")
    dist = {}
    for campo, idx, col in (("mat", 3, "cmmn"), ("mo", 4, "chmn"),
                            ("eq", 5, "cemn")):
        d_raw = Counter()     # diferencia contra el valor exacto
        d_round = Counter()   # diferencia contra redondeo(SBD, 2)
        for cod, e in emb["P"].items():
            s = sbd_rv.get(cod)
            if not s or s[col] is None:
                continue
            ve = a_numero(e[idx])
            if ve is None:
                continue
            delta = round(ve - s[col], 4)
            d_raw[abs(delta)] += 1
            delta2 = round(ve - round(s[col], 2), 4)
            d_round[delta2] += 1
        # resumen por umbrales
        buckets = Counter()
        for d, n in d_raw.items():
            if d == 0:
                buckets["0 (exacto)"] += n
            elif d <= 0.005:
                buckets["<= 0.005"] += n
            elif d <= 0.011:
                buckets["<= 0.011 (ruido de publicación)"] += n
            elif d <= 0.05:
                buckets["<= 0.05"] += n
            elif d <= 0.5:
                buckets["<= 0.5"] += n
            else:
                buckets["> 0.5"] += n
        dist[campo] = {"buckets_abs": dict(buckets),
                       "histograma_delta_round": dict(sorted(
                           d_round.items())[:20])}
        print(f"  {campo}: {dict(buckets)}")

    # 2. consistencia interna de EMB
    print("\n[2] Consistencia interna EMB: total == mat + mo + eq")
    ok = desvio = 0
    for cod, e in emb["P"].items():
        total, mat, mo, eq = (a_numero(e[2]), a_numero(e[3]),
                              a_numero(e[4]), a_numero(e[5]))
        if None in (total, mat, mo, eq):
            continue
        if abs(total - (mat + mo + eq)) < 1e-9:
            ok += 1
        else:
            desvio += 1
    print(f"  consistentes: {ok:,}; con desvío: {desvio:,}")

    # 3. tarifas MO: EMB.O vs SBD.RH
    print("\n[3] Tarifas de mano de obra EMB.O ↔ SBD.RH")
    rh = db.get_table("Nomenclador RH").parse()
    sbd_rh = {str(c): a_numero(rh["TRH_MN"][i])
              for i, c in enumerate(rh["CodRHum"])}
    b = Counter()
    ej = []
    for cod, v in emb["O"].items():
        ve = a_numero(v[1])
        vs = sbd_rh.get(cod)
        if vs is None or ve is None:
            b["no_verificable"] += 1
            continue
        d = round(ve - vs, 4)
        if d == 0:
            b["exacto"] += 1
        elif abs(d) <= 0.005:
            b["<= 0.005 (publicación)"] += 1
        elif abs(d) <= 0.011:
            b["<= 0.011 (publicación)"] += 1
            if len(ej) < 6:
                ej.append({"codigo": cod, "emb": ve, "sbd": vs})
        else:
            b["> 0.011"] += 1
            if len(ej) < 6:
                ej.append({"codigo": cod, "emb": ve, "sbd": vs})
    print(f"  {dict(b)}")
    print(f"  ejemplos fuera: {ej}")

    # 4. ratios de normas (de fidelidad_iv_fina.json)
    print("\n[4] Ratios de coeficientes de normas 2017→2025 (cambios de versión)")
    fina = json.load(open(os.path.join(
        REPO, "docs", "datos", "fidelidad_iv_fina.json"), encoding="utf-8"))
    # recalcular ratios completos
    import sqlite3
    con = sqlite3.connect(f"file:{os.path.join(REPO, 'bd', 'precodi.db')}?mode=ro",
                          uri=True)
    rv17 = {f[0] for f in con.execute(
        "SELECT codigo FROM partidas WHERE version_id=3")}
    sbd_rv_cod = set(sbd_rv)
    compartidas = rv17 & sbd_rv_cod
    tipo_map = {"Mano de obra": ("Norma de Mano de Obra", "CodigoRV",
                                 "CodRHum", "CantRHum"),
                "Material": ("Norma de Materiales", "CodigoRV", "CodMat",
                             "CantMat"),
                "Equipo": ("Norma de Equipos", "CodigoRV", "CodEquipo",
                           "CantEquipo")}
    normas_sbd = {}
    for tipo, (tabla, c_rv, c_rec, c_cant) in tipo_map.items():
        t = db.get_table(tabla).parse()
        for i in range(len(t[c_rv])):
            rv_c = str(t[c_rv][i])
            if rv_c in compartidas:
                normas_sbd[(rv_c, tipo, str(t[c_rec][i]))] = \
                    a_numero(t[c_cant][i])
    normas_17 = {}
    for fila in con.execute("""
            SELECT p.codigo, tr.nombre, n.codigo_recurso, n.coeficiente
            FROM normas_partida n JOIN partidas p ON n.partida_id = p.id
            JOIN tipos_recurso tr ON n.tipo_recurso_id = tr.id
            WHERE p.version_id = 3"""):
        if fila[0] in compartidas:
            normas_17[(fila[0], fila[1], str(fila[2]))] = fila[3]
    ratios = Counter()
    for k in set(normas_17) & set(normas_sbd):
        a, b2 = normas_17[k], normas_sbd[k]
        if not a or not b2:
            continue
        r = b2 / a
        if abs(r - 1.0) <= 1e-6:
            ratios["1.0 (igual)"] += 1
        elif abs(r - 2.0) < 1e-6:
            ratios["2.0 (duplicado)"] += 1
        elif abs(r - 0.5) < 1e-6:
            ratios["0.5 (mitad)"] += 1
        elif abs(r - round(r)) < 1e-6 and 0 < r < 20:
            ratios[f"{round(r):.0f}.0 (entero)"] += 1
        else:
            ratios["otro"] += 1
    print(f"  {dict(sorted(ratios.items(), key=lambda kv: -kv[1]))}")

    salida = {"1_distribucion_precios": dist,
              "2_emb_interno": {"consistentes": ok, "desvio": desvio},
              "3_tarifas_mo": dict(b), "3_ejemplos": ej,
              "4_ratios_normas": dict(ratios)}
    with open(os.path.join(REPO, "docs", "datos", "fidelidad_iv_paso3.json"),
              "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1, default=str)
    print("\nGuardado: docs/datos/fidelidad_iv_paso3.json")


if __name__ == "__main__":
    main()
