#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE III-F — Prueba de concepto: importación de muestra en base nueva.

Crea (si no existe) la base SQLite de prueba —SEPARADA de los archivos
originales— y le importa una muestra representativa y verificable:

  PRECODI 2017 (codigo.mdb raíz):
    - Jerarquía completa de grupos (SobreGrupos/Grupos/SubGrupos)
    - Partidas: sobregrupo '01' completo (470) + primeras 20 partidas con
      juegos + primeras 20 con semielaborados (para cubrir los 5 tipos)
    - Normas de consumo de esas partidas (5 tipos)
    - Recursos referidos (recursivo: componentes de juegos y semis)
    - Componentes de juegos y semielaborados importados
  PRECONS III MICONS 2025 (catálogo embebido de PRECOST, extraído en III-D):
    - Grupos (G)
    - Partidas del capítulo '01' (615)
    - Recursos M/O/E cuyos códigos coinciden con la muestra PRECODI
      (comparación de precios entre fuentes, con procedencia)

Regla: NADA se sobrescribe; cada catálogo entra como versión propia.
Los archivos .mdb y el HTML original NO se modifican (verificación de
integridad al final).

Uso:  python3 scripts/fase3f_importar_poc.py
"""
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

logging.getLogger("access_parser").setLevel(logging.CRITICAL)
from access_parser import AccessParser  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE = os.path.join("/home/z/my-project/work/recuperacion/analisis/PRECODI",
                      "Codigo (PRECODI)/codigo.mdb")
HTML = os.path.join(REPO, "app", "PRECOST-v9.17.html")
BD = os.path.join(REPO, "prueba", "db", "precost_catalogo.db")
EXTRACTO = os.path.join(REPO, "docs", "datos", "fase3d_precost_db.json")

SHA_HTML = "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"
SHA_MDB = None  # se calcula y registra (el original queda intacto)


def f(v):
    try:
        if v is None:
            return None
        x = float(v)
        return x
    except (TypeError, ValueError):
        return None


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as fp:
        for b in iter(lambda: fp.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def norm_um(s):
    """unidad → (unidad_base, factor) para '100 m2' etc."""
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


def main():
    # ---------- 0. Integridad de los originales ANTES de empezar ----------
    global SHA_MDB
    sha_html_antes = sha256(HTML)
    sha_mdb_antes = sha256(FUENTE)
    SHA_MDB = sha_mdb_antes
    assert sha_html_antes == SHA_HTML, "¡El HTML original cambió! Abortando."
    print(f"HTML original intacto (SHA-256 {sha_html_antes[:16]}…)")
    print(f"codigo.mdb (copia de análisis) SHA-256 {sha_mdb_antes[:16]}…")

    # ---------- 1. Migraciones ----------
    r = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "fase3e_migrar.py"), BD],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        return 1

    con = sqlite3.connect(BD)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    # ---------- 2. Catálogos y versiones ----------
    cur.execute("INSERT OR IGNORE INTO catalogos (codigo, nombre, descripcion) VALUES (?,?,?)",
                ("PRECODI", "PRECODI (codigo.mdb)",
                 "Nomencladores y normas de PRECODI, ecosistema Codigo.exe (Jet 4, copia raíz 2017 del RAR auxiliar)"))
    cur.execute("INSERT OR IGNORE INTO catalogos (codigo, nombre, descripcion) VALUES (?,?,?)",
                ("PRECONS_III", "PRECONS III MICONS 2025",
                 "Catálogo normativo embebido en PRECOST v9.17 (const DB), extraído sin modificar el HTML"))
    con.commit()
    cat_precodi = cur.execute("SELECT id FROM catalogos WHERE codigo='PRECODI'").fetchone()[0]
    cat_precons = cur.execute("SELECT id FROM catalogos WHERE codigo='PRECONS_III'").fetchone()[0]

    # ¿ya existe esta versión? → la PoC es idempotente: no duplica
    ya = cur.execute("SELECT id FROM versiones_catalogo WHERE catalogo_id=? AND version=?",
                     (cat_precodi, "2017-raiz")).fetchone()
    if ya:
        print("\nLa versión PRECODI 2017-raiz ya existe: no se importa nada (idempotente).")
        con.close()
        return 0

    cur.execute("""INSERT INTO versiones_catalogo
        (catalogo_id, version, fecha_publicacion, fuente_archivo, fuente_sha256, fuente_detalle, estado)
        VALUES (?,?,?,?,?,?, 'importada')""",
        (cat_precodi, "2017-raiz", None,
         "AUXILIAR_PRECODI.rar → Codigo (PRECODI)/codigo.mdb", sha_mdb_antes,
         "Jet 4 (Access 2000), 24 tablas; mtime del archivo: 2017"))
    cur.execute("""INSERT INTO versiones_catalogo
        (catalogo_id, version, fecha_publicacion, fuente_archivo, fuente_sha256, fuente_detalle, estado)
        VALUES (?,?,?,?,?,?, 'importada')""",
        (cat_precons, "2025-06-06", "2025-06-06",
         "PRECOST-v9.17.html (const DB)", sha_html_antes,
         "PRECONS III MICONS 2025 · publicada 06/06/25 · fuentes PDF oficiales MICONS"))
    con.commit()
    ver_precodi = cur.execute("SELECT id FROM versiones_catalogo WHERE catalogo_id=? AND version='2017-raiz'",
                              (cat_precodi,)).fetchone()[0]
    ver_precons = cur.execute("SELECT id FROM versiones_catalogo WHERE catalogo_id=? AND version='2025-06-06'",
                              (cat_precons,)).fetchone()[0]

    # ---------- 3. Cargar PRECODI ----------
    print("\nCargando PRECODI (solo lectura)…")
    db = AccessParser(FUENTE)

    def rows(nombre):
        t = db.parse_table(nombre)
        return [dict(zip(t, v)) for v in zip(*t.values())]

    r_sg = rows("Nomenclador de SobreGrupos RV")
    r_gr = rows("Nomenclador de Grupos RV")
    r_sub = rows("Nomenclador de SubGrupos RV")
    r_rv = rows("Nomenclador de RV")
    r_mat = rows("Nomenclador de Materiales")
    r_rh = rows("Nomenclador de Mano de Obra")
    r_eq = rows("Nomenclador de Equipos")
    r_jg = rows("Nomenclador de Juegos")
    r_se = rows("Nomenclador de Semielaborados")
    n_mat = rows("Norma de Materiales")
    n_rh = rows("Norma de Mano de Obra")
    n_eq = rows("Norma de Equipos")
    n_jg = rows("Norma de Juegos")
    n_se = rows("Norma de Semielaborados")
    nj_mat = rows("Norma Juego Material")
    ns_mat = rows("Norma Semi Material")
    ns_rh = rows("Norma Semi RHumanos")
    ns_eq = rows("Norma Semi Equipos")
    print("  tablas de PRECODI cargadas")

    # ---------- 4. Muestra de partidas ----------
    rvs_por_codigo = {}
    for r in r_rv:
        c = str(r.get("CODIGO RV", "")).strip()
        if c and c not in rvs_por_codigo:
            rvs_por_codigo[c] = r
    muestra = {c: r for c, r in rvs_por_codigo.items() if str(r.get("CodSobreG")) == "01"}
    con_juegos = [c for c in (str(r["CodigoRV"]) for r in n_jg) if c in rvs_por_codigo and c not in muestra][:20]
    con_semis = [c for c in (str(r["CodigoRV"]) for r in n_se) if c in rvs_por_codigo and c not in muestra][:20]
    for c in con_juegos + con_semis:
        muestra[c] = rvs_por_codigo[c]
    print(f"  Muestra: 470 (SG 01) + {len(con_juegos)} con juegos + {len(con_semis)} con semis = {len(muestra)}")

    # recursos referidos (recursivo)
    tipos = {c: i for c, i in cur.execute("SELECT codigo, id FROM tipos_recurso").fetchall()}
    referidos = defaultdict(set)  # tipo → {codigos}
    normas_a_insertar = []        # (tipo, cod_rv, cod_rec, coef, cod_norma)
    for r in n_mat:
        c = str(r["CodigoRV"])
        if c in muestra:
            normas_a_insertar.append(("material", c, str(r["CodMat"]), f(r["CantMat"]), str(r.get("CodNorma") or "S/C")))
            referidos["material"].add(str(r["CodMat"]))
    for r in n_rh:
        c = str(r["CodigoRV"])
        if c in muestra:
            normas_a_insertar.append(("mano_obra", c, str(r["CodRHum"]), f(r["CantRHum"]), str(r.get("CodNorma") or "S/C")))
            referidos["mano_obra"].add(str(r["CodRHum"]))
    for r in n_eq:
        c = str(r["CodigoRV"])
        if c in muestra:
            normas_a_insertar.append(("equipo", c, str(r["CodEquipo"]), f(r["CantEquipo"]), str(r.get("CodNorma") or "S/C")))
            referidos["equipo"].add(str(r["CodEquipo"]))
    for r in n_jg:
        c = str(r["CodigoRV"])
        if c in muestra:
            normas_a_insertar.append(("juego", c, str(r["CodJuego"]), f(r["CantJuego"]), "S/C"))
            referidos["juego"].add(str(r["CodJuego"]))
    for r in n_se:
        c = str(r["CodigoRV"])
        if c in muestra:
            normas_a_insertar.append(("semielaborado", c, str(r["CodSElab"]), f(r["CantSElab"]), "S/C"))
            referidos["semielaborado"].add(str(r["CodSElab"]))

    # componentes de juegos/semis (recursivo un nivel, suficiente aquí)
    comp_juegos = [r for r in nj_mat if str(r["CodJuego"]) in referidos["juego"]]
    for r in comp_juegos:
        referidos["material"].add(str(r["CodMat"]))
    comp_semis = {"material": [r for r in ns_mat if str(r["CodSemi"]) in referidos["semielaborado"]],
                  "mano_obra": [r for r in ns_rh if str(r["CodSemi"]) in referidos["semielaborado"]],
                  "equipo": [r for r in ns_eq if str(r["CodSemi"]) in referidos["semielaborado"]]}
    for r in comp_semis["material"]:
        referidos["material"].add(str(r["CodMat"]))
    for r in comp_semis["mano_obra"]:
        referidos["mano_obra"].add(str(r["CodRHum"]))
    for r in comp_semis["equipo"]:
        referidos["equipo"].add(str(r["CodEquipo"]))

    # ---------- 5. Insertar jerarquía PRECODI ----------
    n_ins = defaultdict(int)
    for r in r_sg:
        cur.execute("INSERT OR IGNORE INTO grupos (catalogo_id, nivel, codigo, padre_codigo, descripcion) VALUES (?,?,?,?,?)",
                    (cat_precodi, 1, str(r["CodSobreG"]), None, str(r["SubreGrupo"])))
        n_ins["grupos_sg"] += cur.rowcount
    for r in r_gr:
        cur.execute("INSERT OR IGNORE INTO grupos (catalogo_id, nivel, codigo, padre_codigo, descripcion) VALUES (?,?,?,?,?)",
                    (cat_precodi, 2, str(r["CodG"]), str(r["CodSobreG"]), str(r["Grupo"])))
        n_ins["grupos_g"] += cur.rowcount
    for r in r_sub:
        cur.execute("INSERT OR IGNORE INTO grupos (catalogo_id, nivel, codigo, padre_codigo, descripcion) VALUES (?,?,?,?,?)",
                    (cat_precodi, 3, str(r["CodSubG"]), str(r["CodG"]), str(r["SubGrupo"])))
        n_ins["grupos_sub"] += cur.rowcount

    # ---------- 6. Insertar partidas PRECODI ----------
    for c, r in sorted(muestra.items()):
        um, fu = norm_um(r.get("UNIDAD DE MEDIDA"))
        cur.execute("""INSERT INTO partidas
            (version_id, codigo, descripcion, unidad, factor_unidad, capitulo,
             costo_mat_mn, costo_mo_mn, costo_eq_mn, costo_total_mn, costo_mat_mlc,
             horas_hombre, horas_equipo, peso_kg, es_oficial, resolucion_aprob, fecha_aprobacion)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ver_precodi, c, str(r.get("Desc Rv") or "").strip(), um, fu, str(r.get("CodSobreG")),
             f(r.get("CMMN")), f(r.get("CHMN")), f(r.get("CEMN")),
             (f(r.get("CMMN")) or 0) + (f(r.get("CHMN")) or 0) + (f(r.get("CEMN")) or 0),
             f(r.get("CMMLC")), f(r.get("HORAS HOMBRE")), f(r.get("HORAS EQUIPO")), f(r.get("PESO")),
             1 if r.get("Oficial") else 0, str(r.get("Res_Aprov")) if r.get("Res_Aprov") else None,
             str(r.get("Fecha_Aprov"))[:10] if r.get("Fecha_Aprov") else None))
        n_ins["partidas"] += cur.rowcount

    # ---------- 7. Insertar recursos PRECODI ----------
    def insertar_recurso(tipo, codigo, desc, um, pmn, pmlc, pu, peso, grupo_sal=None, esp=None):
        cur.execute("""INSERT INTO recursos
            (version_id, tipo_id, codigo, descripcion, unidad, precio_mn, precio_mlc, precio_total,
             peso_unidad, grupo_salarial, especialidad)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (ver_precodi, tipos[tipo], codigo, str(desc or "").strip(), um, pmn, pmlc, pu, peso, grupo_sal, esp))
        n_ins[f"rec_{tipo}"] += cur.rowcount

    mat_idx = {str(r["CodMat"]): r for r in r_mat}
    for cod in sorted(referidos["material"]):
        r = mat_idx.get(cod)
        if r:
            insertar_recurso("material", cod, r["Material"], str(r.get("UmRec") or ""),
                             f(r.get("PMN")), f(r.get("PMLC")), f(r.get("PrecioU")), f(r.get("PesoU")))
    for cod in sorted(referidos["mano_obra"]):
        r = next((x for x in r_rh if str(x["CodRHum"]) == cod), None)
        if r:
            insertar_recurso("mano_obra", cod, r["RHum"], str(r.get("UmRec") or ""),
                             f(r.get("PMN")), f(r.get("PMLC")), f(r.get("PrecioU")), None,
                             str(r.get("Grupo") or ""), str(r.get("Especialidad") or "") or None)
    for cod in sorted(referidos["equipo"]):
        r = next((x for x in r_eq if str(x["CodEquipo"]) == cod), None)
        if r:
            insertar_recurso("equipo", cod, r["Equipo"], str(r.get("UmRec") or ""),
                             f(r.get("PMN")), f(r.get("PMLC")), f(r.get("PrecioU")), None)
    for cod in sorted(referidos["juego"]):
        r = next((x for x in r_jg if str(x["CodJuego"]) == cod), None)
        if r:
            insertar_recurso("juego", cod, r["Juego"], str(r.get("UmRec") or ""),
                             f(r.get("PMN")), f(r.get("PMLC")), f(r.get("PrecioU")), f(r.get("PesoU")))
    for cod in sorted(referidos["semielaborado"]):
        r = next((x for x in r_se if str(x["CodSElab"]) == cod), None)
        if r:
            insertar_recurso("semielaborado", cod, r["SElab"], str(r.get("UmRec") or ""),
                             f(r.get("PMN")), f(r.get("PMLC")), f(r.get("PrecioU")), f(r.get("PesoU")))

    # ---------- 8. Normas de partidas ----------
    id_partida = {c: i for c, i in cur.execute(
        "SELECT codigo, id FROM partidas WHERE version_id=?", (ver_precodi,)).fetchall()}
    for tipo, cod_rv, cod_rec, coef, cod_norma in normas_a_insertar:
        if coef is None:
            continue
        cur.execute("""INSERT OR IGNORE INTO normas_partida
            (partida_id, version_id, tipo_recurso_id, codigo_recurso, coeficiente, cod_norma)
            VALUES (?,?,?,?,?,?)""",
            (id_partida[cod_rv], ver_precodi, tipos[tipo], cod_rec, coef, cod_norma))
        n_ins["normas"] += cur.rowcount

    # ---------- 9. Componentes de juegos y semis ----------
    id_recurso = {(t, c): i for t, c, i in cur.execute(
        "SELECT (SELECT codigo FROM tipos_recurso WHERE id=tipo_id), codigo, id FROM recursos WHERE version_id=?",
        (ver_precodi,)).fetchall()}
    for r in comp_juegos:
        rid = id_recurso.get(("juego", str(r["CodJuego"])))
        if rid is None:
            continue
        cur.execute("""INSERT OR IGNORE INTO componentes_recurso
            (recurso_id, version_id, tipo_componente_id, codigo_componente, coeficiente, cod_norma)
            VALUES (?,?,?,?,?, 'S/C')""",
            (rid, ver_precodi, tipos["material"], str(r["CodMat"]), f(r["CantMatJ"])))
        n_ins["comp_juego"] += cur.rowcount
    for r in comp_semis["material"]:
        rid = id_recurso.get(("semielaborado", str(r["CodSemi"])))
        if rid is None:
            continue
        cur.execute("""INSERT OR IGNORE INTO componentes_recurso
            (recurso_id, version_id, tipo_componente_id, codigo_componente, coeficiente, cod_norma)
            VALUES (?,?,?,?,?, 'S/C')""",
            (rid, ver_precodi, tipos["material"], str(r["CodMat"]), f(r["CantMatSE"])))
        n_ins["comp_semi"] += cur.rowcount
    for r in comp_semis["mano_obra"]:
        rid = id_recurso.get(("semielaborado", str(r["CodSemi"])))
        if rid is None:
            continue
        cur.execute("""INSERT OR IGNORE INTO componentes_recurso
            (recurso_id, version_id, tipo_componente_id, codigo_componente, coeficiente, cod_norma)
            VALUES (?,?,?,?,?,?)""",
            (rid, ver_precodi, tipos["mano_obra"], str(r["CodRHum"]), f(r["CantRHumSE"]),
             str(r.get("CodNorma") or "S/C")))
        n_ins["comp_semi"] += cur.rowcount
    for r in comp_semis["equipo"]:
        rid = id_recurso.get(("semielaborado", str(r["CodSemi"])))
        if rid is None:
            continue
        cur.execute("""INSERT OR IGNORE INTO componentes_recurso
            (recurso_id, version_id, tipo_componente_id, codigo_componente, coeficiente, cod_norma)
            VALUES (?,?,?,?,?, 'S/C')""",
            (rid, ver_precodi, tipos["equipo"], str(r["CodEquipo"]), f(r["CantEquipoSE"])))
        n_ins["comp_semi"] += cur.rowcount

    # ---------- 10. PRECOST 2025: grupos, partidas cap. 01, recursos compartidos ----------
    precost = json.load(open(EXTRACTO, encoding="utf-8"))
    G, P, M, O, E = precost["G"], precost["P"], precost["M"], precost["O"], precost["E"]
    advertencias = []
    for cod, v in sorted(G.items()):
        nivel = {2: 1, 3: 2, 4: 3}.get(len(cod))
        if nivel is None:
            continue
        padre = cod[:-1] if nivel > 1 else None  # '011'→'01', '0111'→'011'
        if padre is not None and padre not in G:
            # Hallazgo de calidad (documentado): 32 códigos G sin padre en G
            # (p.ej. '2810' con partidas reales debajo pero sin grupo '281').
            advertencias.append(f"G {cod!r} ({str(v[0])[:40]!r}): padre {padre!r} ausente en G; importado sin padre")
            padre = None
        cur.execute("INSERT OR IGNORE INTO grupos (catalogo_id, nivel, codigo, padre_codigo, descripcion) VALUES (?,?,?,?,?)",
                    (cat_precons, nivel, cod, padre, str(v[0])))
        n_ins["grupos_precons"] += cur.rowcount
    for cod, p in sorted(P.items()):
        if p[7] != "01":
            continue
        um, fu = norm_um(p[1])
        cur.execute("""INSERT INTO partidas
            (version_id, codigo, descripcion, unidad, factor_unidad, capitulo,
             costo_mat_mn, costo_mo_mn, costo_eq_mn, costo_total_mn, peso_kg)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (ver_precons, cod, str(p[0]).strip(), um, fu, str(p[7]),
             f(p[3]), f(p[4]), f(p[5]), f(p[2]), f(p[6]) if len(p) > 6 else None))
        n_ins["partidas_precons"] += cur.rowcount

    # recursos PRECOST con código compartido con la muestra PRECODI
    compartidos = {"material": referidos["material"] & set(M),
                   "mano_obra": referidos["mano_obra"] & set(O),
                   "equipo": referidos["equipo"] & set(E)}
    for tipo, fuente in (("material", M), ("mano_obra", O), ("equipo", E)):
        for cod in sorted(compartidos[tipo]):
            v = fuente[cod]
            desc = v[0]
            um = str(v[1]).lower() if len(v) > 1 and tipo == "material" else ("hh" if tipo == "mano_obra" else "he")
            precio = f(v[2]) if len(v) > 2 else None
            peso = f(v[3]) if (tipo == "material" and len(v) > 3) else None
            cur.execute("""INSERT INTO recursos
                (version_id, tipo_id, codigo, descripcion, unidad, precio_mn, peso_unidad)
                VALUES (?,?,?,?,?,?,?)""",
                (ver_precons, tipos[tipo], cod, str(desc).strip(), um, precio, peso))
            rid = cur.lastrowid
            cur.execute("""INSERT INTO precios_recurso (recurso_id, fuente, fecha, precio_mn, moneda)
                VALUES (?,?,?,?, 'CUP')""", (rid, "PRECONS_III_2025", "2025-06-06", precio))
            n_ins[f"rec_precons_{tipo}"] += cur.rowcount

    # ---------- 11. Registro de importaciones ----------
    filas_json = json.dumps(dict(n_ins), ensure_ascii=False)
    resultado_precons = "ok" if not advertencias else "ok_con_advertencias"
    for ver, filas, res in ((ver_precodi, {k: v for k, v in n_ins.items() if not k.endswith("precons")}, "ok"),
                            (ver_precons, {k: v for k, v in n_ins.items() if k.endswith("precons")}, resultado_precons)):
        cur.execute("""INSERT INTO importaciones (version_id, script, filas_por_tabla, advertencias, resultado, finalizada_en)
            VALUES (?,?,?,?,?, datetime('now'))""",
            (ver, os.path.basename(__file__), json.dumps(filas, ensure_ascii=False),
             json.dumps(advertencias, ensure_ascii=False), res))
    con.commit()

    print("\nResumen de inserciones:")
    for k, v in sorted(n_ins.items()):
        print(f"  {k}: {v}")

    # ---------- 12. Integridad de los originales DESPUÉS ----------
    assert sha256(HTML) == SHA_HTML, "¡El HTML original cambió durante la importación!"
    assert sha256(FUENTE) == sha_mdb_antes, "¡codigo.mdb cambió durante la importación!"
    print("\nIntegridad verificada: HTML y .mdb permanecen intactos.")
    con.close()
    print(f"Base de prueba: {BD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
