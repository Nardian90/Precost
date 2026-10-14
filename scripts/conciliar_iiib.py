#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MISIÓN III-B · Fase 6 — Conciliación PRECODI ↔ PRECOST con los datos importados.

Produce docs/datos/iiib_conciliacion.json con:
  1. Recuentos origen (fase3a_inventario.json) ↔ destino (importaciones/stats)
     por base y tabla, con cada diferencia explicada por reglas documentadas.
  2. Cruce del catálogo PRECODI (raíz 2017, precios EXACTOS de 4 decimales)
     contra el catálogo embebido PRECOST 2025: códigos compartidos,
     descripciones, unidades y evolución de precios.
  3. Evolución entre versiones PRECODI (7.21 → 7.22 → raíz → SBD).

NO modifica nada: solo lee bd/precodi.db y los JSON de evidencia.

Uso:  python3 scripts/conciliar_iiib.py
"""
import json
import os
import sqlite3
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BD = os.path.join(REPO, "bd", "precodi.db")
INV = os.path.join(REPO, "docs", "datos", "fase3a_inventario.json")
SALIDA = os.path.join(REPO, "docs", "datos", "iiib_conciliacion.json")

VERSIONES = {"codigo_721": "2007-v7.21", "codigo_722": "2007-v7.22",
             "codigo_raiz": "2017-raiz", "sbd2008_815": "2011-sbd2008"}
# reglas que explican filas fuente sin inserción (documentadas en FASE_III_INTEGRACION.md)
REGLAS = ["duplicadas_omitidas", "omitidas_invalidas", "huérfanas_partida", "huérfanas_recurso",
          "ya_existentes", "duplicados_detectados"]


def recuentos(con):
    inv = json.load(open(INV, encoding="utf-8"))
    out = {}
    for b in inv["bases"]:
        bid = b["id"]
        if bid == "codigo_preambulos":
            out[bid] = {"regla": "duplicado exacto de 7.21 por SHA-256: 0 filas propias, versión de referencia"}
            continue
        version = VERSIONES[bid]
        fila = con.execute("""SELECT i.filas_por_tabla FROM importaciones i
            JOIN versiones_catalogo v ON v.id=i.version_id WHERE v.version=?
            ORDER BY i.id DESC LIMIT 1""", (version,)).fetchone()
        stats = json.loads(fila[0]) if fila else {}
        tablas = {}
        for t in b.get("tablas", []):
            nombre, n_fuente = t["tabla"], t.get("filas") or 0
            if nombre not in stats or n_fuente == 0:
                continue
            st = stats[nombre]
            insertadas = st.get("insertadas", 0)
            explicadas = sum(st.get(k, 0) for k in REGLAS if k in st)
            nota = ""
            if insertadas + explicadas != n_fuente:
                nota = "pendiente de explicar" if insertadas + explicadas < n_fuente else "sobreconteo"
            if nombre == "Norma Juego Material1":
                nota = "duplicado exacto verificado: 0 insertadas por diseño"
            tablas[nombre] = {"fuente": n_fuente, "insertadas": insertadas,
                              "explicadas_por_reglas": explicadas, "detalle": st, "nota": nota}
        out[bid] = {"version": version, "tablas": tablas}
    return out


def cruce_precodi_precost(con):
    vid_raiz = con.execute("SELECT id FROM versiones_catalogo WHERE version='2017-raiz'").fetchone()[0]
    vid_2025 = con.execute("SELECT id FROM versiones_catalogo WHERE version='2025-06-06'").fetchone()[0]
    raiz = {r["codigo"]: r for r in con.execute(
        "SELECT * FROM partidas WHERE version_id=?", (vid_raiz,))}
    p25 = {r["codigo"]: r for r in con.execute(
        "SELECT * FROM partidas WHERE version_id=?", (vid_2025,))}

    inter = set(raiz) & set(p25)
    solo_precodi = set(raiz) - set(p25)
    solo_precost = set(p25) - set(raiz)

    def norm_desc(s):
        return " ".join(str(s or "").upper().split())

    desc_iguales = sum(1 for c in inter if norm_desc(raiz[c]["descripcion"]) == norm_desc(p25[c]["descripcion"]))
    um_eq = um_dist = 0
    detalle_um = Counter()
    ratios = []
    for c in inter:
        u1, u2 = (raiz[c]["unidad"] or "").strip().lower(), (p25[c]["unidad"] or "").strip().lower()
        if u1 == u2:
            um_eq += 1
        else:
            um_dist += 1
            detalle_um[(u1, u2)] += 1
        t17, t25 = raiz[c]["costo_total_mn"], p25[c]["costo_total_mn"]
        if t17 and t25 and t17 > 0:
            ratios.append(t25 / t17)

    # cobertura de descomposiciones (lo que PRECOST gana con la integración)
    con_descomp = con.execute("""SELECT COUNT(DISTINCT p.codigo) FROM normas_partida np
        JOIN partidas p ON p.id=np.partida_id WHERE np.version_id=?""", (vid_raiz,)).fetchone()[0]
    descomp_en_comunes = con.execute("""SELECT COUNT(DISTINCT p.codigo) FROM normas_partida np
        JOIN partidas p ON p.id=np.partida_id
        WHERE np.version_id=? AND p.codigo IN (SELECT codigo FROM partidas WHERE version_id=?)""",
        (vid_raiz, vid_2025)).fetchone()[0]

    return {
        "compartidos": len(inter),
        "solo_precodi_2017": len(solo_precodi),
        "solo_precost_2025": len(solo_precost),
        "descripciones_identicas": desc_iguales,
        "unidades_iguales": um_eq,
        "unidades_distintas": um_dist,
        "unidades_distintas_detalle": {f"{a} ↔ {b}": n for (a, b), n in detalle_um.most_common(10)},
        "ratio_precio_2025_2017": {
            "n": len(ratios),
            "mediana": round(statistics.median(ratios), 2) if ratios else None,
            "p10": round(statistics.quantiles(ratios, n=10)[0], 2) if len(ratios) >= 10 else None,
            "p90": round(statistics.quantiles(ratios, n=10)[8], 2) if len(ratios) >= 10 else None,
            "nota": "precios 2017 con 4 decimales EXACTOS (mejora frente a fase III-D que usaba "
                    "el string truncado a 2 decimales del parser original)",
        },
        "descomposiciones": {
            "partidas_con_normas_raiz_2017": con_descomp,
            "de_las_cuales_compartidas_con_precost_2025": descomp_en_comunes,
            "nota": "PRECOST 2025 no trae descomposiciones: esta es la aportación central de la integración",
        },
    }


def evolucion_versiones(con):
    vers = ["2007-v7.21", "2007-v7.22", "2017-raiz", "2011-sbd2008"]
    out = {}
    cods = {}
    for v in vers:
        vid = con.execute("SELECT id FROM versiones_catalogo WHERE version=?", (v,)).fetchone()[0]
        cods[v] = {r[0] for r in con.execute("SELECT codigo FROM partidas WHERE version_id=?", (vid,))}
    for a, b in zip(vers, vers[1:]):
        out[f"{a} → {b}"] = {
            "agregadas": len(cods[b] - cods[a]),
            "eliminadas": len(cods[a] - cods[b]),
            "comunes": len(cods[a] & cods[b]),
        }
    return out


def main():
    con = sqlite3.connect(f"file:{BD}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    res = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "recuentos_origen_destino": recuentos(con),
        "cruce_precodi_raiz_precost_2025": cruce_precodi_precost(con),
        "evolucion_versiones_precodi": evolucion_versiones(con),
    }
    con.close()
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    print("=== CONCILIACIÓN MISIÓN III-B ===")
    pendientes = []
    for base, r in res["recuentos_origen_destino"].items():
        if "tablas" not in r:
            print(f"  {base}: {r['regla']}")
            continue
        mal = [t for t, d in r["tablas"].items() if d["nota"] == "pendiente de explicar"]
        tot_ins = sum(d["insertadas"] for d in r["tablas"].values())
        print(f"  {base} ({r['version']}): {len(r['tablas'])} tablas, {tot_ins:,} insertadas, "
              f"sin explicar: {len(mal)}")
        pendientes += [(base, t) for t in mal]
    c = res["cruce_precodi_raiz_precost_2025"]
    print(f"\nCruce raíz 2017 ↔ PRECOST 2025: {c['compartidos']} códigos compartidos, "
          f"{c['descripciones_identicas']} descripciones idénticas, ratio de precios mediana "
          f"×{c['ratio_precio_2025_2017']['mediana']}")
    print(f"Descomposiciones PRECODI disponibles para {c['descomposiciones']['partidas_con_normas_raiz_2017']:,}"
          f" partidas ({c['descomposiciones']['de_las_cuales_compartidas_con_precost_2025']:,} compartidas con 2025)")
    if pendientes:
        print("\nPENDIENTES DE EXPLICAR:", pendientes)
    print(f"\nJSON → {SALIDA}")
    return 0 if not pendientes else 1


if __name__ == "__main__":
    sys.exit(main())
