#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MISIÓN VIII — Generador de los datos embebidos de la versión web estática.

Exporta la BD (solo lectura) a JSON compactos que app/overlay/estatico.js
consume en la web pública (GitHub Pages) para ofrecer PARIDAD LITERAL con el
servidor local SIN backend: mismas versiones, mismas búsquedas, mismas
descomposiciones (normas), mismo nomenclador y mismas reglas de cálculo.

Archivos generados en app/web-datos/ (se commitean: el build de Pages NO
requiere la BD ni los .mdb originales — ver construir_web.py):

  i.json            índice: versiones (ids de BD, conteos, slugs) + tipos_recurso
  p-<slug>.json     partidas por versión: [codigo, desc, um, factor, capitulo,
                    mat_mn, mo_mn, eq_mn, total_mn, mat_mlc] — orden código
  n-<slug>.json     normas por partida (solo partidas con norma):
                    codigo → [[tipo, tipo_nombre, codigo_recurso, coeficiente,
                    cod_norma, um_norma, desc_propia, um_propia, precio_propio,
                    precio_mlc_propio, hijos[[tipo, tipo_nombre, codigo,
                    coeficiente, desc, um, precio, precio_mlc]]]]
  r-<slug>.json     nomenclador: [[tipo, tipo_nombre, codigo, desc, um,
                    precio_mn, precio_mlc]] — orden (tipo_id, codigo)
  manifest.json     sha256+bytes de cada archivo (verificación en build/tests)

Garantías:
  * SOLO LECTURA de la BD (mode=ro); el HTML original jamás se toca.
  * Determinista: mismas entradas → mismos bytes de salida (orden estable).
  * Verificación: al terminar, relee cada JSON y compara conteos con la BD;
    cualquier discrepancia aborta con exit != 0.
  * Ids de versión = ids de la BD (los que usa el API local): el overlay
    estático replica las respuestas del servidor SIN re-mapear ids.

Uso:
  python3 scripts/generar_datos_web.py [--bd bd/precodi.db] [--salida app/web-datos]
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BD_DEFECTO = os.path.join(REPO, "bd", "precodi.db")
SALIDA_DEFECTO = os.path.join(REPO, "app", "web-datos")
SHA_HTML = "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"


def slug_de(version):
    """Slug de archivo: la versión sin caracteres problemáticos de ruta."""
    return "".join(c if (c.isalnum() or c in "-._") else "-" for c in version)


def volcar(ruta, objeto):
    """JSON compacto determinista (utf-8, sin espacios, claves en orden fijo)."""
    with open(ruta, "w", encoding="utf-8") as fp:
        json.dump(objeto, fp, ensure_ascii=False, separators=(",", ":"))
    return os.path.getsize(ruta)


def sha256_de(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Generador de datos embebidos para la web estática (MISIÓN VIII)")
    ap.add_argument("--bd", default=BD_DEFECTO)
    ap.add_argument("--salida", default=SALIDA_DEFECTO)
    args = ap.parse_args()

    if not os.path.exists(args.bd):
        sys.exit(f"No existe {args.bd}: ejecute antes scripts/importar_precodi.py --todas "
                 "y --base sbd --priorizadas")
    con = sqlite3.connect(f"file:{args.bd}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    os.makedirs(args.salida, exist_ok=True)

    # ---------------- tipos de recurso (globales, orden id como el API) --------
    tipos = [{"codigo": r["codigo"], "nombre": r["nombre"]}
             for r in con.execute("SELECT codigo, nombre FROM tipos_recurso ORDER BY id")]
    tipo_cod = {r["id"]: r["codigo"] for r in con.execute("SELECT id, codigo FROM tipos_recurso")}
    tipo_nom = {r["id"]: r["nombre"] for r in con.execute("SELECT id, nombre FROM tipos_recurso")}

    # ---------------- versiones -------------------------------------------------
    versiones = []
    for v in con.execute("""SELECT vc.id, vc.catalogo_id, vc.version, vc.estado,
                                    vc.fecha_importacion, vc.fuente_archivo, vc.fuente_sha256,
                                    vc.fecha_publicacion, vc.fuente_detalle, c.codigo AS catalogo
                             FROM versiones_catalogo vc JOIN catalogos c ON c.id = vc.catalogo_id
                             ORDER BY vc.id"""):
        vid = v["id"]
        conteo = {
            "partidas": con.execute("SELECT COUNT(*) FROM partidas WHERE version_id=?", (vid,)).fetchone()[0],
            "recursos": con.execute("SELECT COUNT(*) FROM recursos WHERE version_id=?", (vid,)).fetchone()[0],
            "normas": con.execute("SELECT COUNT(*) FROM normas_partida WHERE version_id=?", (vid,)).fetchone()[0],
            "descomponibles": con.execute(
                "SELECT COUNT(DISTINCT partida_id) FROM normas_partida WHERE version_id=?",
                (vid,)).fetchone()[0],
        }
        if conteo["partidas"] == 0 and conteo["recursos"] == 0:
            continue          # referencias sin filas propias (p. ej. Preambulos ≡ 7.21)
        versiones.append({
            "id": vid, "slug": slug_de(v["version"]), "catalogo": v["catalogo"],
            "version": v["version"], "estado": v["estado"],
            "fecha_importacion": v["fecha_importacion"],
            "fuente_archivo": v["fuente_archivo"], "fuente_sha256": v["fuente_sha256"],
            "fecha_publicacion": v["fecha_publicacion"], "fuente_detalle": v["fuente_detalle"],
            **conteo,
        })

    indice = {
        "formato": 1,
        "mision": "VIII",
        "generado": datetime.now(timezone.utc).isoformat(),
        "html_original_intacto": True,
        "sha256_html_original": SHA_HTML,
        "nota": "Datos PRECODI/PRECOST exportados de bd/precodi.db para la web "
                "estática (paridad con el servidor local sin backend). Solo lectura.",
        "tipos_recurso": tipos,
        "versiones": versiones,
    }

    generados = {"i.json": volcar(os.path.join(args.salida, "i.json"), indice)}
    verificacion = []

    for v in versiones:
        vid, slug = v["id"], v["slug"]

        # ---------- p-<slug>.json: partidas (orden código) --------------------
        filas = []
        for r in con.execute("""SELECT codigo, descripcion, unidad, factor_unidad, capitulo,
                                        costo_mat_mn, costo_mo_mn, costo_eq_mn, costo_total_mn,
                                        costo_mat_mlc
                                 FROM partidas WHERE version_id=? ORDER BY codigo""", (vid,)):
            filas.append([r["codigo"], r["descripcion"], r["unidad"], r["factor_unidad"],
                          r["capitulo"], r["costo_mat_mn"], r["costo_mo_mn"], r["costo_eq_mn"],
                          r["costo_total_mn"], r["costo_mat_mlc"]])
        ruta_p = os.path.join(args.salida, f"p-{slug}.json")
        generados[os.path.basename(ruta_p)] = volcar(ruta_p, {"partidas": filas})
        verificacion.append(("partidas", slug, v["partidas"], len(filas)))

        # ---------- n-<slug>.json: normas por partida --------------------------
        if v["normas"] > 0:
            # componentes de juegos/semielaborados (hijos), agrupados por recurso
            hijos = {}
            for c in con.execute("""SELECT cr.recurso_id, tr2.codigo AS tipo, tr2.nombre AS tipo_nombre,
                                            cr.codigo_componente, cr.coeficiente,
                                            r2.descripcion, r2.unidad, r2.precio_mn, r2.precio_mlc
                                     FROM componentes_recurso cr
                                     JOIN tipos_recurso tr2 ON tr2.id = cr.tipo_componente_id
                                     LEFT JOIN recursos r2 ON r2.version_id = cr.version_id
                                          AND r2.tipo_id = cr.tipo_componente_id
                                          AND r2.codigo = cr.codigo_componente
                                     WHERE cr.version_id=? ORDER BY cr.recurso_id, tr2.id,
                                          cr.codigo_componente""", (vid,)):
                hijos.setdefault(c["recurso_id"], []).append(
                    [c["tipo"], c["tipo_nombre"], c["codigo_componente"], c["coeficiente"],
                     c["descripcion"], c["unidad"], c["precio_mn"], c["precio_mlc"]])
            # recurso (tipo, codigo) → id, para adjuntar hijos
            rec_id = {}
            for r in con.execute("""SELECT id, tipo_id, codigo FROM recursos
                                    WHERE version_id=?""", (vid,)):
                rec_id[(r["tipo_id"], r["codigo"])] = r["id"]

            normas = {}
            n_filas = 0
            for n in con.execute("""SELECT np.partida_id, p.codigo AS partida_codigo,
                                            np.tipo_recurso_id, np.codigo_recurso, np.coeficiente,
                                            np.cod_norma, np.um_norma,
                                            r.descripcion AS desc_propia, r.unidad AS um_propia,
                                            r.precio_mn AS precio_propio, r.precio_mlc AS precio_mlc_propio
                                     FROM normas_partida np
                                     JOIN partidas p ON p.id = np.partida_id
                                     JOIN tipos_recurso tr ON tr.id = np.tipo_recurso_id
                                     LEFT JOIN recursos r ON r.version_id = np.version_id
                                          AND r.tipo_id = np.tipo_recurso_id
                                          AND r.codigo = np.codigo_recurso
                                     WHERE np.version_id=? ORDER BY np.partida_id, tr.id,
                                          np.codigo_recurso""", (vid,)):
                comp = [tipo_cod[n["tipo_recurso_id"]], tipo_nom[n["tipo_recurso_id"]],
                        n["codigo_recurso"], n["coeficiente"], n["cod_norma"], n["um_norma"],
                        n["desc_propia"], n["um_propia"], n["precio_propio"], n["precio_mlc_propio"],
                        hijos.get(rec_id.get((n["tipo_recurso_id"], n["codigo_recurso"]), -1), [])]
                normas.setdefault(n["partida_codigo"], []).append(comp)
                n_filas += 1
            ruta_n = os.path.join(args.salida, f"n-{slug}.json")
            generados[os.path.basename(ruta_n)] = volcar(ruta_n, {"normas": normas})
            verificacion.append(("normas", slug, v["normas"], n_filas))

        # ---------- r-<slug>.json: nomenclador ---------------------------------
        if v["recursos"] > 0:
            filas_r = []
            for r in con.execute("""SELECT r.tipo_id, r.codigo, r.descripcion, r.unidad,
                                           r.precio_mn, r.precio_mlc
                                    FROM recursos r WHERE r.version_id=?
                                    ORDER BY r.tipo_id, r.codigo""", (vid,)):
                filas_r.append([tipo_cod[r["tipo_id"]], tipo_nom[r["tipo_id"]], r["codigo"],
                                r["descripcion"], r["unidad"], r["precio_mn"], r["precio_mlc"]])
            ruta_r = os.path.join(args.salida, f"r-{slug}.json")
            generados[os.path.basename(ruta_r)] = volcar(ruta_r, {"recursos": filas_r})
            verificacion.append(("recursos", slug, v["recursos"], len(filas_r)))

    # ---------------- manifest con sha256 --------------------------------------
    manifest = {"formato": 1, "generado": indice["generado"],
                "archivos": {nombre: {"bytes": b, "sha256": None}
                             for nombre, b in sorted(generados.items())}}
    for nombre in manifest["archivos"]:
        manifest["archivos"][nombre]["sha256"] = sha256_de(os.path.join(args.salida, nombre))
    generados["manifest.json"] = volcar(os.path.join(args.salida, "manifest.json"), manifest)

    # ---------------- verificación de conteos ----------------------------------
    errores = []
    for tabla, slug, esperado, obtenido in verificacion:
        if esperado != obtenido:
            errores.append(f"{tabla} de {slug}: BD={esperado} JSON={obtenido}")
    # relectura real de cada archivo (JSON válido y conteos exactos)
    for v in versiones:
        slug = v["slug"]
        with open(os.path.join(args.salida, f"p-{slug}.json"), encoding="utf-8") as fp:
            n_p = len(json.load(fp)["partidas"])
        if n_p != v["partidas"]:
            errores.append(f"relectura partidas {slug}: {n_p} != {v['partidas']}")
        if v["normas"] > 0:
            with open(os.path.join(args.salida, f"n-{slug}.json"), encoding="utf-8") as fp:
                n_n = sum(len(x) for x in json.load(fp)["normas"].values())
            if n_n != v["normas"]:
                errores.append(f"relectura normas {slug}: {n_n} != {v['normas']}")
        if v["recursos"] > 0:
            with open(os.path.join(args.salida, f"r-{slug}.json"), encoding="utf-8") as fp:
                n_r = len(json.load(fp)["recursos"])
            if n_r != v["recursos"]:
                errores.append(f"relectura recursos {slug}: {n_r} != {v['recursos']}")

    con.close()
    if errores:
        for e in errores:
            print(f"ERROR de verificación: {e}", file=sys.stderr)
        sys.exit(1)

    total = sum(generados.values())
    print(json.dumps({
        "versiones": [{"id": v["id"], "slug": v["slug"], "version": v["version"],
                       "partidas": v["partidas"], "recursos": v["recursos"], "normas": v["normas"]}
                      for v in versiones],
        "archivos": {k: f"{b:,} B" for k, b in sorted(generados.items())},
        "total_bytes": f"{total:,} B ({total / 1048576:.1f} MiB)",
        "salida": args.salida,
    }, ensure_ascii=False, indent=1))
    print("OK: datos web generados y verificados contra la BD (conteos exactos).")


if __name__ == "__main__":
    main()
