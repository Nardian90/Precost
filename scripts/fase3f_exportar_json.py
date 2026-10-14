#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE III-F — Exportación de la base de prueba a JSON para la PoC de navegador.

Vuelca la base SQLite (prueba/db/precost_catalogo.db) a un JSON que la página
prueba/poc_catalogo_externo.html consulta vía fetch(). Así se demuestra el
patrón "PRECOST consulta un catálogo externo" sin tocar el HTML original.

Salida: prueba/db/catalogo_export.json
"""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BD = os.path.join(REPO, "prueba", "db", "precost_catalogo.db")
SALIDA = os.path.join(REPO, "prueba", "db", "catalogo_export.json")


def main():
    con = sqlite3.connect(BD)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    catalogos = [dict(r) for r in cur.execute(
        "SELECT c.id, c.codigo, c.nombre FROM catalogos c ORDER BY c.id")]
    versiones = [dict(r) for r in cur.execute(
        """SELECT v.id, v.catalogo_id, v.version, v.fecha_publicacion, v.fuente_archivo,
                  v.fuente_sha256, v.fuente_detalle, v.estado
           FROM versiones_catalogo v ORDER BY v.id""")]
    grupos = [dict(r) for r in cur.execute(
        """SELECT g.catalogo_id, g.nivel, g.codigo, g.padre_codigo, g.descripcion
           FROM grupos g ORDER BY g.catalogo_id, g.nivel, g.codigo""")]
    partidas = [dict(r) for r in cur.execute(
        """SELECT p.version_id, p.codigo, p.descripcion, p.unidad, p.factor_unidad,
                  p.capitulo, p.costo_mat_mn, p.costo_mo_mn, p.costo_eq_mn,
                  p.costo_total_mn, p.peso_kg, p.horas_hombre, p.horas_equipo
           FROM partidas p ORDER BY p.version_id, p.codigo""")]
    recursos = [dict(r) for r in cur.execute(
        """SELECT r.version_id, (SELECT codigo FROM tipos_recurso WHERE id=r.tipo_id) AS tipo,
                  r.codigo, r.descripcion, r.unidad, r.precio_mn, r.precio_mlc,
                  r.precio_total, r.peso_unidad
           FROM recursos r ORDER BY r.version_id, r.tipo_id, r.codigo""")]
    normas = [dict(r) for r in cur.execute(
        """SELECT np.partida_id, (SELECT codigo FROM tipos_recurso WHERE id=np.tipo_recurso_id) AS tipo,
                  np.codigo_recurso, np.coeficiente, np.cod_norma
           FROM normas_partida np ORDER BY np.partida_id""")]
    partida_ids = {p["version_id"]: {} for p in partidas}
    for p in partidas:
        partida_ids[p["version_id"]][p["codigo"]] = None
    # mapa codigo → id por versión para las normas
    cod_a_id = {}
    for r in cur.execute("SELECT id, version_id, codigo FROM partidas"):
        cod_a_id[(r["version_id"], r["codigo"])] = r["id"]
    normas_out = []
    for n in normas:
        normas_out.append({**n, "codigo_partida": None})
    # añadir codigo_partida
    id_a_codigo = {v: k for k, v in cod_a_id.items()}
    for n in normas_out:
        clave = id_a_codigo.get(n["partida_id"])
        n["codigo_partida"] = clave[1] if clave else None
        n["version_id"] = clave[0] if clave else None
    componentes = [dict(r) for r in cur.execute(
        """SELECT cr.recurso_id, (SELECT codigo FROM tipos_recurso WHERE id=cr.tipo_componente_id) AS tipo_componente,
                  cr.codigo_componente, cr.coeficiente
           FROM componentes_recurso cr""")]
    # mapear recurso_id → (version, codigo, tipo)
    rid_map = {}
    for r in cur.execute("""SELECT r.id, r.version_id, r.codigo,
                                   (SELECT codigo FROM tipos_recurso WHERE id=r.tipo_id) AS tipo FROM recursos r"""):
        rid_map[r["id"]] = (r["version_id"], r["codigo"], r["tipo"])
    comp_out = []
    for c in componentes:
        m = rid_map.get(c["recurso_id"])
        if m:
            comp_out.append({"version_id": m[0], "codigo_recurso": m[1], "tipo_recurso": m[2],
                             "tipo_componente": c["tipo_componente"],
                             "codigo_componente": c["codigo_componente"],
                             "coeficiente": c["coeficiente"]})
    importaciones = [dict(r) for r in cur.execute(
        "SELECT version_id, script, filas_por_tabla, advertencias, resultado FROM importaciones")]

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "descripcion": "Exportación de la base de prueba PRECOST (Fase III-F). "
                       "Catálogos externos versionados con procedencia; generada desde "
                       "prueba/db/precost_catalogo.db (SQLite) sin modificar el HTML original.",
        "catalogos": catalogos,
        "versiones": versiones,
        "grupos": grupos,
        "partidas": partidas,
        "recursos": recursos,
        "normas": normas_out,
        "componentes": comp_out,
        "importaciones": importaciones,
    }
    with open(SALIDA, "w", encoding="utf-8") as fp:
        json.dump(salida, fp, ensure_ascii=False)
    print(f"-> {SALIDA} ({os.path.getsize(SALIDA):,} bytes)")
    print(f"   partidas={len(partidas)} recursos={len(recursos)} normas={len(normas_out)} "
          f"grupos={len(grupos)} componentes={len(comp_out)}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
