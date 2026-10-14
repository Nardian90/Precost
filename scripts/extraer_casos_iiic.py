#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MISIÓN III-C — Extracción de casos de prueba con valores EXACTOS de la fuente.

Genera datos_prueba/casos_iiic.json a partir de bd/precodi.db (importación
III-B verificada). Los valores son de origen: no se ajustan ni se inventan.
Regenerable: python3 scripts/extraer_casos_iiic.py
"""
import json
import os
import sqlite3
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BD = os.path.join(REPO, "bd", "precodi.db")
SALIDA = os.path.join(REPO, "datos_prueba", "casos_iiic.json")


def con_bd():
    c = sqlite3.connect(f"file:{BD}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def partida(con, codigo, version_id=3):
    return dict(con.execute(
        "SELECT codigo, descripcion, unidad, costo_mat_mn, costo_mo_mn, costo_eq_mn,"
        " costo_total_mn FROM partidas WHERE version_id=? AND codigo=?",
        (version_id, codigo)).fetchone())


def normas(con, codigo, version_id=3):
    filas = con.execute("""
        SELECT tr.codigo tipo, np.codigo_recurso, np.coeficiente, np.cod_norma,
               r.descripcion, r.unidad, r.precio_mn
        FROM normas_partida np
        JOIN tipos_recurso tr ON tr.id = np.tipo_recurso_id
        LEFT JOIN recursos r ON r.version_id=np.version_id
             AND r.tipo_id=np.tipo_recurso_id AND r.codigo=np.codigo_recurso
        JOIN partidas p ON p.id=np.partida_id AND p.version_id=np.version_id
        WHERE np.version_id=? AND p.codigo=?
        ORDER BY tr.id, np.codigo_recurso""", (version_id, codigo)).fetchall()
    return [dict(f) for f in filas]


def main():
    con = con_bd()
    fx = {
        "descripcion": ("Fixtures MISIÓN III-C extraídos de bd/precodi.db "
                        "(valores EXACTOS de la fuente; regenerable con "
                        "scripts/extraer_casos_iiic.py)"),
        "fuente_sha256_html": "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2",
        "versiones_012141": {},
        "casos": {},
    }

    # 012141 en cada versión (diferencias de precio entre versiones — caso 12).
    # Se referencia por ETIQUETA de versión (estable); los ids numéricos son
    # autoincrement y cambian tras purgar/reimportar.
    for v in con.execute("""SELECT vc.id, c.codigo cat, vc.version FROM versiones_catalogo vc
                            JOIN catalogos c ON c.id=vc.catalogo_id ORDER BY vc.id"""):
        p = con.execute("SELECT costo_total_mn, unidad FROM partidas WHERE version_id=? AND codigo='012141'",
                        (v["id"],)).fetchone()
        if p:
            fx["versiones_012141"][v["version"]] = {
                "catalogo": v["cat"], "version": v["version"],
                "costo_total_mn": p["costo_total_mn"], "unidad": p["unidad"]}

    # caso 1/3/4/5/9/16: 012141 (norma completa, por categorías, Float32, regresión III-B)
    fx["casos"]["partida_012141"] = {
        **partida(con, "012141"),
        "n_componentes": len(normas(con, "012141")),
        "por_tipo": {t: sum(1 for n in normas(con, "012141") if n["tipo"] == t)
                     for t in ("material", "mano_obra", "equipo", "juego", "semielaborado")},
        "normas": normas(con, "012141"),
    }

    # caso 2: partida sin norma
    fx["casos"]["partida_999999_sin_norma"] = partida(con, "999999")

    # caso 6/8: 096231 (multi-categoría con juego+semi y duplicado real de MO)
    n96 = normas(con, "096231")
    dup = {}
    for n in n96:
        k = (n["tipo"], n["codigo_recurso"])
        dup[k] = dup.get(k, 0) + 1
    fx["casos"]["partida_096231"] = {
        **partida(con, "096231"),
        "n_componentes": len(n96),
        "por_tipo": {t: sum(1 for n in n96 if n["tipo"] == t)
                     for t in ("material", "mano_obra", "equipo", "juego", "semielaborado")},
        "duplicados_reales": [{"tipo": k[0], "codigo": k[1], "veces": v}
                              for k, v in dup.items() if v > 1],
        "juego_con_hijos": bool(con.execute("""
            SELECT 1 FROM componentes_recurso cr
            JOIN recursos r ON r.id = cr.recurso_id AND r.version_id=3
            JOIN tipos_recurso tr ON tr.id = r.tipo_id
            JOIN partidas p ON p.id = (SELECT partida_id FROM normas_partida np
                WHERE np.version_id=3 AND np.codigo_recurso=r.codigo AND np.tipo_recurso_id=r.tipo_id
                AND np.partida_id=(SELECT id FROM partidas WHERE version_id=3 AND codigo='096231') LIMIT 1)
            WHERE tr.codigo IN ('juego','semielaborado') LIMIT 1""").fetchone()),
        "normas": n96,
    }

    # caso 10: partida con recurso de precio de 4 decimales exactos
    fx["casos"]["partida_063611_precio_4dec"] = {
        **partida(con, "063611"),
        "recurso_4dec": {"codigo": "4641011001", "precio_mn": 5191.9199,
                         "coeficiente": 0.013100000098347664},
        "normas": normas(con, "063611"),
    }

    # caso 12 (recursos): cruce de claves de las normas de 012141 hacia otras
    # versiones — medido como el API lo mide: precio DISPONIBLE (LEFT JOIN +
    # precio_mn IS NOT NULL), no mera existencia del código
    fx["casos"]["cruce_012141"] = {}
    for vdest, etiqueta in ((2, "2007-v7.22"), (5, "2025-06-06"), (6, "2011-sbd2008")):
        # resolver id por etiqueta (los ids son autoincrement: nunca asumirlos)
        vid = con.execute("""SELECT vc.id FROM versiones_catalogo vc
                             JOIN catalogos c ON c.id=vc.catalogo_id
                             WHERE c.codigo='PRECONS_III' AND vc.version=?
                             OR c.codigo='PRECODI' AND vc.version=?""",
                           (etiqueta, etiqueta)).fetchone()
        if vid is None:
            continue
        vid = vid[0]
        r = con.execute(f"""
            SELECT COUNT(*) total,
             SUM(CASE WHEN pr.id IS NOT NULL AND pr.precio_mn IS NOT NULL THEN 1 ELSE 0 END) resueltos
            FROM normas_partida np
            LEFT JOIN recursos pr ON pr.version_id={vid}
                 AND pr.tipo_id=np.tipo_recurso_id AND pr.codigo=np.codigo_recurso
            WHERE np.version_id=3 AND np.partida_id=(SELECT id FROM partidas WHERE version_id=3 AND codigo='012141')
            """).fetchone()
        fx["casos"]["cruce_012141"][etiqueta] = {"total": r["total"], "resueltos": r["resueltos"]}

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(fx, f, ensure_ascii=False, indent=1)
    print(f"Fixtures escritos en {SALIDA}")
    print("  012141:", fx["casos"]["partida_012141"]["n_componentes"], "componentes ·",
          fx["casos"]["partida_012141"]["por_tipo"])
    print("  096231:", fx["casos"]["partida_096231"]["n_componentes"], "componentes · duplicados:",
          fx["casos"]["partida_096231"]["duplicados_reales"])
    print("  999999 sin norma:", fx["casos"]["partida_999999_sin_norma"]["descripcion"])
    print("  063611 recurso 4dec:", fx["casos"]["partida_063611_precio_4dec"]["recurso_4dec"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
