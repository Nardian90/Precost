#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE III-F — Pruebas automatizadas de la prueba de concepto.

Ejecuta pruebas REALES contra la base de prueba (prueba/db/precost_catalogo.db)
y contra las fuentes originales (recalcula, no usa constantes mágicas):

  T1  Migraciones aplicadas (0001, 0002 y las añadidas después: 0003 de la
      Misión III-C — precisión SBD) y tablas esperadas.
  T2  Conteos de la muestra importada == recalculados desde codigo.mdb y
      desde el extracto del catálogo PRECOST (fase3d_precost_db.json).
  T3  Formato de códigos: partidas 6 dígitos; recursos 10 dígitos.
  T4  Integridad referencial: PRAGMA foreign_key_check vacío y normas sin
      partida/recurso huérfano DENTRO de la muestra importada.
  T5  Partidas PRECOST 2025: costo_total == mat + mo + eq (tol. 0,01).
  T6  Fórmulas PRECODI (F1/F2/F3 de la FASE III-C) recalculadas SOLO con
      datos de la base: Σ coef×precio por componente vs costo almacenado.
  T7  Procedencia: toda partida/recurso tiene versión con fuente y hash.
  T8  Originales intactos: SHA-256 del HTML y del .mdb sin cambios.
  T9  Unidades no vacías; precios y factores de unidad no negativos.
  T10 Consulta de demostración: buscar partida por código y por texto y
      recuperar sus recursos con coeficientes y precios.

Produce: docs/datos/fase3f_resultados_tests.json + resumen por stdout.
Código de salida: 0 si todas pasan, 1 si alguna falla.
"""
import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

logging.getLogger("access_parser").setLevel(logging.CRITICAL)
from access_parser import AccessParser  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BD = os.path.join(REPO, "prueba", "db", "precost_catalogo.db")
HTML = os.path.join(REPO, "app", "PRECOST-v9.17.html")
MDB = "/home/z/my-project/work/recuperacion/analisis/PRECODI/Codigo (PRECODI)/codigo.mdb"
EXTRACTO = os.path.join(REPO, "docs", "datos", "fase3d_precost_db.json")
SHA_HTML = "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"

RESULTADOS = []


def prueba(nombre, condicion, detalle=""):
    estado = "PASS" if condicion else "FAIL"
    RESULTADOS.append({"prueba": nombre, "estado": estado, "detalle": detalle})
    print(f"  [{estado}] {nombre}" + (f" — {detalle}" if detalle else ""))
    return condicion


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as fp:
        for b in iter(lambda: fp.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    con = sqlite3.connect(BD)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()
    ok_global = True

    # ---------- T1: migraciones ----------
    print("T1 — Migraciones y tablas")
    migrs = [r[0] for r in cur.execute("SELECT version FROM schema_migrations ORDER BY version")]
    # MISIÓN VIII: el contrato es «migraciones en orden, sin huecos»: 0001 y
    # 0002 (originales de 3F) más las añadidas después (0003, Misión III-C).
    migrs_esperadas = [m for m in ("0001", "0002", "0003") if m <= (migrs[-1] if migrs else "")]
    ok_global &= prueba(f"Migraciones aplicadas == {migrs_esperadas}",
                        migrs == migrs_esperadas, str(migrs))
    tablas_esperadas = {"catalogos", "versiones_catalogo", "importaciones", "grupos", "partidas",
                        "tipos_recurso", "recursos", "normas_partida", "componentes_recurso",
                        "precios_recurso", "auditoria", "proyectos", "presupuestos",
                        "capitulos_presupuesto", "partidas_presupuesto"}
    tablas = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    ok_global &= prueba("Tablas del esquema presentes", tablas_esperadas <= tablas,
                        f"{len(tablas)} tablas")

    # ---------- T2: conteos vs fuentes ----------
    print("T2 — Conteos de la muestra (recalculados desde las fuentes)")
    db = AccessParser(MDB)

    def rows(nombre):
        t = db.parse_table(nombre)
        return [dict(zip(t, v)) for v in zip(*t.values())]

    r_rv = rows("Nomenclador de RV")
    codigos_sg01 = {str(r["CODIGO RV"]).strip() for r in r_rv if str(r.get("CodSobreG")) == "01"}
    n_jg = rows("Norma de Juegos")
    n_se = rows("Norma de Semielaborados")
    con_juegos = {str(r["CodigoRV"]) for r in n_jg if str(r["CodigoRV"]) in
                  {str(x["CODIGO RV"]).strip() for x in r_rv}} - codigos_sg01
    con_semis = {str(r["CodigoRV"]) for r in n_se if str(r["CodigoRV"]) in
                 {str(x["CODIGO RV"]).strip() for x in r_rv}} - codigos_sg01
    muestra_esperada = codigos_sg01 | set(sorted(con_juegos)[:20]) | set(sorted(con_semis)[:20])
    n_db = cur.execute("SELECT COUNT(*) FROM partidas p JOIN versiones_catalogo v ON p.version_id=v.id "
                       "JOIN catalogos c ON v.catalogo_id=c.id WHERE c.codigo='PRECODI'").fetchone()[0]
    ok_global &= prueba("Partidas PRECODI == muestra esperada", n_db == len(muestra_esperada),
                        f"bd={n_db} esperado={len(muestra_esperada)} (SG01={len(codigos_sg01)})")
    precost = json.load(open(EXTRACTO, encoding="utf-8"))
    n_pp_esperado = sum(1 for p in precost["P"].values() if p[7] == "01")
    n_pp = cur.execute("SELECT COUNT(*) FROM partidas p JOIN versiones_catalogo v ON p.version_id=v.id "
                       "JOIN catalogos c ON v.catalogo_id=c.id WHERE c.codigo='PRECONS_III'").fetchone()[0]
    ok_global &= prueba("Partidas PRECONS 2025 (cap. 01) == fuente", n_pp == n_pp_esperado,
                        f"bd={n_pp} fuente={n_pp_esperado}")
    # normas: contar desde mdb para la muestra
    n_normas_esperado = 0
    for tabla in ("Norma de Materiales", "Norma de Mano de Obra", "Norma de Equipos",
                  "Norma de Juegos", "Norma de Semielaborados"):
        n_normas_esperado += sum(1 for r in rows(tabla) if str(r["CodigoRV"]) in muestra_esperada)
    n_normas = cur.execute("SELECT COUNT(*) FROM normas_partida np "
                           "JOIN partidas p ON np.partida_id=p.id "
                           "JOIN versiones_catalogo v ON p.version_id=v.id "
                           "JOIN catalogos c ON v.catalogo_id=c.id WHERE c.codigo='PRECODI'").fetchone()[0]
    ok_global &= prueba("Normas importadas == normas de la muestra en .mdb",
                        n_normas == n_normas_esperado, f"bd={n_normas} mdb={n_normas_esperado}")

    # ---------- T3: formato de códigos ----------
    print("T3 — Formato de códigos")
    mal_p = cur.execute("SELECT COUNT(*) FROM partidas WHERE codigo NOT GLOB '[0-9][0-9][0-9][0-9][0-9][0-9]'").fetchone()[0]
    ok_global &= prueba("Todas las partidas con código de 6 dígitos", mal_p == 0, f"malas={mal_p}")
    mal_r = cur.execute("SELECT COUNT(*) FROM recursos WHERE codigo NOT GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'").fetchone()[0]
    ok_global &= prueba("Todos los recursos con código de 10 dígitos", mal_r == 0, f"malos={mal_r}")

    # ---------- T4: integridad referencial ----------
    print("T4 — Integridad referencial")
    fk = cur.execute("PRAGMA foreign_key_check").fetchall()
    ok_global &= prueba("PRAGMA foreign_key_check vacío", not fk, f"{len(fk)} violaciones")
    # normas → recursos dentro de la versión PRECODI (por diseño no es FK, se verifica aquí)
    huerfanas = cur.execute("""
        SELECT COUNT(*) FROM normas_partida np
        JOIN partidas p ON np.partida_id = p.id
        WHERE p.version_id = (SELECT v.id FROM versiones_catalogo v
                              JOIN catalogos c ON v.catalogo_id=c.id
                              WHERE c.codigo='PRECODI' AND v.version='2017-raiz')
          AND NOT EXISTS (SELECT 1 FROM recursos r WHERE r.version_id = np.version_id
                          AND r.tipo_id = np.tipo_recurso_id AND r.codigo = np.codigo_recurso)
    """).fetchone()[0]
    ok_global &= prueba("Normas sin recurso huérfano (dentro de la muestra)", huerfanas == 0,
                        f"huérfanas={huerfanas}")

    # ---------- T5: suma de componentes PRECOST ----------
    print("T5 — PRECOST: total == mat+mo+eq (tol 0,01)")
    mal_suma = cur.execute("""SELECT p.codigo, p.costo_total_mn,
        (COALESCE(p.costo_mat_mn,0)+COALESCE(p.costo_mo_mn,0)+COALESCE(p.costo_eq_mn,0))
        FROM partidas p JOIN versiones_catalogo v ON p.version_id=v.id
        JOIN catalogos c ON v.catalogo_id=c.id
        WHERE c.codigo='PRECONS_III' AND ABS(COALESCE(p.costo_total_mn,0)
          - (COALESCE(p.costo_mat_mn,0)+COALESCE(p.costo_mo_mn,0)+COALESCE(p.costo_eq_mn,0))) > 0.01""").fetchall()
    # discrepancias esperadas: las que trae la PROPIA FUENTE (redondeo del PDF)
    mal_fuente = {c for c, p in precost["P"].items()
                  if p[7] == "01" and abs(float(p[2]) - (float(p[3]) + float(p[4]) + float(p[5]))) > 0.01}
    mal_bd = {c for c, *_ in mal_suma}
    ok_global &= prueba("Discrepancias total≠suma == las de la fuente (redondeo del PDF)",
                        mal_bd == mal_fuente,
                        f"bd={sorted(mal_bd)} fuente={sorted(mal_fuente)}")

    # ---------- T6: fórmulas PRECODI recalculadas desde la base ----------
    print("T6 — Fórmulas PRECODI recalculadas (F1/F2/F3 de FASE III-C)")
    filas = cur.execute("""
        SELECT p.id, p.codigo, p.costo_mat_mn, p.costo_mo_mn, p.costo_eq_mn,
               (SELECT COALESCE(SUM(np.coeficiente * r.precio_mn), 0) FROM normas_partida np
                 JOIN recursos r ON r.version_id = np.version_id AND r.tipo_id = np.tipo_recurso_id
                                AND r.codigo = np.codigo_recurso
                 WHERE np.partida_id = p.id AND r.tipo_id = (SELECT id FROM tipos_recurso WHERE codigo='material')) AS mat_calc,
               (SELECT COALESCE(SUM(np.coeficiente * r.precio_mn), 0) FROM normas_partida np
                 JOIN recursos r ON r.version_id = np.version_id AND r.tipo_id = np.tipo_recurso_id
                                AND r.codigo = np.codigo_recurso
                 WHERE np.partida_id = p.id AND r.tipo_id = (SELECT id FROM tipos_recurso WHERE codigo='mano_obra')) AS mo_calc,
               (SELECT COALESCE(SUM(np.coeficiente * r.precio_mn), 0) FROM normas_partida np
                 JOIN recursos r ON r.version_id = np.version_id AND r.tipo_id = np.tipo_recurso_id
                                AND r.codigo = np.codigo_recurso
                 WHERE np.partida_id = p.id AND r.tipo_id = (SELECT id FROM tipos_recurso WHERE codigo='equipo')) AS eq_calc
        FROM partidas p JOIN versiones_catalogo v ON p.version_id=v.id JOIN catalogos c ON v.catalogo_id=c.id
        WHERE c.codigo='PRECODI'
    """).fetchall()
    # NOTA: los recursos importados son solo los referidos; los materiales de
    # juegos/semis contribuyen vía componentes_recurso, que aquí se evalúa aparte.
    ok_mat = ok_mo = ok_eq = n = 0
    escala10_mo = otros_mo = 0
    for pid, cod, cmmn, chmn, cemn, mat_c, mo_c, eq_c in filas:
        n += 1
        if cmmn is not None and abs(mat_c - cmmn) <= 0.01:
            ok_mat += 1
        if chmn is not None:
            if abs(mo_c - chmn) <= 0.01:
                ok_mo += 1
            elif chmn > 0 and 9.5 <= chmn / mo_c <= 10.5:
                # patrón documentado (FASE III-C): ~259 partidas en PRECODI con
                # CHMN = 10 × Σ(CantRHum×PMN) — inconsistencia de escala de los
                # coeficientes en la fuente; NO es una variante de fórmula.
                escala10_mo += 1
            else:
                otros_mo += 1
        if cemn is not None and abs(eq_c - cemn) <= 0.01:
            ok_eq += 1
    tasa_min = 0.85  # umbrales derivados de las tasas globales verificadas en III-C
    ok_global &= prueba("F2 CHMN = Σ(CantRHum×PMN) en la muestra",
                        n and (ok_mo + escala10_mo) / n >= 0.98 and otros_mo <= 0.02 * n,
                        f"{ok_mo}/{n} exactos ({100*ok_mo/max(n,1):.1f}%) + {escala10_mo} con patrón ×10 "
                        f"documentado + {otros_mo} sin explicar")
    ok_global &= prueba("F3 CEMN = Σ(CantEquipo×PMN) en la muestra", n and ok_eq / n >= tasa_min,
                        f"{ok_eq}/{n} exactos ({100*ok_eq/max(n,1):.1f}%)")
    ok_global &= prueba("F1 CMMN = Σ(CantMat×PMN) en la muestra (sin expandir juegos/semis)",
                        n and ok_mat / n >= 0.80,
                        f"{ok_mat}/{n} exactos ({100*ok_mat/max(n,1):.1f}%) — "
                        "las partidas con juegos/semis requieren expansión de componentes")

    # ---------- T7: procedencia ----------
    print("T7 — Procedencia")
    sin_fuente = cur.execute("""
        SELECT COUNT(*) FROM partidas p JOIN versiones_catalogo v ON p.version_id=v.id
        WHERE v.fuente_archivo IS NULL OR v.fuente_sha256 IS NULL""").fetchone()[0]
    ok_global &= prueba("Toda partida tiene versión con fuente y hash", sin_fuente == 0, f"sin_fuente={sin_fuente}")
    sin_fuente_r = cur.execute("""
        SELECT COUNT(*) FROM recursos r JOIN versiones_catalogo v ON r.version_id=v.id
        WHERE v.fuente_archivo IS NULL""").fetchone()[0]
    ok_global &= prueba("Todo recurso tiene versión con fuente", sin_fuente_r == 0, f"sin_fuente={sin_fuente_r}")
    n_imp = cur.execute("SELECT COUNT(*) FROM importaciones").fetchone()[0]
    ok_global &= prueba("Importaciones registradas (2)", n_imp == 2, f"registros={n_imp}")

    # ---------- T8: originales intactos ----------
    print("T8 — Integridad de los archivos originales")
    sha_html = sha256(HTML)
    ok_global &= prueba("PRECOST-v9.17.html sin cambios", sha_html == SHA_HTML, sha_html[:16] + "…")
    sha_mdb_reg = cur.execute("SELECT fuente_sha256 FROM versiones_catalogo v "
                              "JOIN catalogos c ON v.catalogo_id=c.id "
                              "WHERE c.codigo='PRECODI'").fetchone()[0]
    ok_global &= prueba("codigo.mdb sin cambios desde la importación",
                        sha256(MDB) == sha_mdb_reg, sha_mdb_reg[:16] + "…")

    # ---------- T9: unidades y precios ----------
    print("T9 — Unidades y precios")
    sin_um = cur.execute("SELECT COUNT(*) FROM partidas WHERE unidad IS NULL OR unidad=''").fetchone()[0]
    ok_global &= prueba("Partidas con unidad definida", sin_um == 0, f"sin_unidad={sin_um}")
    precios_neg = cur.execute("""SELECT COUNT(*) FROM partidas WHERE costo_total_mn < 0
        OR costo_mat_mn < 0 OR costo_mo_mn < 0 OR costo_eq_mn < 0""").fetchone()[0]
    ok_global &= prueba("Sin costos negativos", precios_neg == 0, f"negativos={precios_neg}")
    mal_factor = cur.execute("SELECT COUNT(*) FROM partidas WHERE factor_unidad <= 0").fetchone()[0]
    ok_global &= prueba("Factor de unidad positivo", mal_factor == 0, f"malos={mal_factor}")

    # ---------- T10: consulta de demostración ----------
    print("T10 — Consulta: buscar partida y recuperar recursos")
    # por código exacto
    fila = cur.execute("""
        SELECT p.codigo, p.descripcion, p.unidad, COUNT(np.id)
        FROM partidas p JOIN normas_partida np ON np.partida_id=p.id
        JOIN versiones_catalogo v ON p.version_id=v.id JOIN catalogos c ON v.catalogo_id=c.id
        WHERE c.codigo='PRECODI' AND p.codigo='012141'
        GROUP BY p.id""").fetchone()
    ok_global &= prueba("Partida 012141 existe con recursos asociados",
                        fila is not None and fila[3] > 0,
                        f"{fila[0]} · {fila[1][:40]}… · {fila[3]} recursos" if fila else "no encontrada")
    # por texto
    fila2 = cur.execute("""
        SELECT p.codigo, p.descripcion FROM partidas p
        JOIN versiones_catalogo v ON p.version_id=v.id JOIN catalogos c ON v.catalogo_id=c.id
        WHERE c.codigo='PRECODI' AND p.descripcion LIKE '%ROCA%' LIMIT 1""").fetchone()
    ok_global &= prueba("Búsqueda por texto ('%ROCA%') funcional", fila2 is not None,
                        f"{fila2[0]} · {fila2[1][:50]}…" if fila2 else "sin resultados")
    # descomposición completa con precios y procedencia
    comp = cur.execute("""
        SELECT t.codigo AS tipo, np.codigo_recurso, r.descripcion, np.coeficiente,
               r.precio_mn, r.unidad, v.version, c.codigo AS catalogo
        FROM normas_partida np
        JOIN partidas p ON np.partida_id=p.id
        JOIN recursos r ON r.version_id=np.version_id AND r.tipo_id=np.tipo_recurso_id
                       AND r.codigo=np.codigo_recurso
        JOIN tipos_recurso t ON t.id=np.tipo_recurso_id
        JOIN versiones_catalogo v ON v.id=p.version_id
        JOIN catalogos c ON c.id=v.catalogo_id
        WHERE p.codigo='012141' ORDER BY t.codigo LIMIT 3""").fetchall()
    ok_global &= prueba("Descomposición con precios y procedencia recuperable",
                        len(comp) > 0 and all(c[7] == "PRECODI" for c in comp),
                        f"{len(comp)}+ filas, ejemplo: {comp[0][1]} ×{comp[0][3]} @ {comp[0][4]} CUP" if comp else "vacía")

    # ---------- resumen ----------
    resumen = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "base": BD,
        "total": len(RESULTADOS),
        "pasadas": sum(1 for r in RESULTADOS if r["estado"] == "PASS"),
        "fallidas": sum(1 for r in RESULTADOS if r["estado"] == "FAIL"),
        "resultados": RESULTADOS,
    }
    ruta = os.path.join(REPO, "docs", "datos", "fase3f_resultados_tests.json")
    with open(ruta, "w", encoding="utf-8") as fp:
        json.dump(resumen, fp, ensure_ascii=False, indent=1)
    print(f"\n{'='*60}\nRESULTADO: {resumen['pasadas']}/{resumen['total']} pruebas superadas"
          f" · {resumen['fallidas']} fallidas -> {ruta}")
    con.close()
    return 0 if resumen["fallidas"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
