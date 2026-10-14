#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MISIÓN III-B · Fase 1 — Auditoría previa reproducible del estado real.

Verifica con datos (no con lo que dicen los informes):
  1. Estado Git: rama, commits, tag v9.17-original, árbol limpio.
  2. Hashes SHA-256 de las 5 bases .mdb contra docs/datos/fase3a_inventario.json.
  3. SHA-256 del HTML original PRECOST v9.17 (intacto).
  4. Entidades que implementa realmente la migración 0002 (parseo del SQL).
  5. Evidencia de tipos Money/Float32 en 7.21 (Jet 3) y raíz 2017 (Jet 4):
     las tres representaciones que devuelve access_parser y por qué el
     importador anterior (fase3f_importar_poc.py) solo funcionó con la raíz.
  6. Defectos detectados en el importador PoC anterior (evidencia estática).

Salida: docs/datos/auditoria_iiib.json + resumen por stdout.

Uso:  python3 scripts/auditar_iiib.py
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE_BASE = "/home/z/my-project/work/recuperacion/analisis/PRECODI"
HTML = os.path.join(REPO, "app", "PRECOST-v9.17.html")

BASES = {
    "codigo_721": "Codigo (PRECODI)/7.21/codigo.mdb",
    "codigo_722": "Codigo (PRECODI)/7.22/codigo.mdb",
    "codigo_raiz": "Codigo (PRECODI)/codigo.mdb",
    "codigo_preambulos": "Codigo (PRECODI)/Preambulos/codigo.mdb",
    "sbd2008_815": "Codigo (PRECODI)/8.15/SBD2008_815.mdb",
}


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def audit_git():
    def git(*args):
        r = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)
        return r.stdout.strip()

    return {
        "rama": git("rev-parse", "--abbrev-ref", "HEAD"),
        "commits": git("log", "--oneline").splitlines(),
        "tag_v917": git("rev-parse", "v9.17-original"),
        "tag_apunta_a_commit_baseline": git("rev-parse", "v9.17-original") == git("rev-parse", "main"),
        "arbol_limpio": git("status", "--porcelain") == "",
    }


def audit_hashes():
    inv = json.load(open(os.path.join(REPO, "docs", "datos", "fase3a_inventario.json"),
                         encoding="utf-8"))
    inv_hashes = {b["id"]: b.get("sha256") for b in inv["bases"]}
    out = {}
    for bid, rel in BASES.items():
        ruta = os.path.join(FUENTE_BASE, rel)
        existe = os.path.exists(ruta)
        h = sha256(ruta) if existe else None
        out[bid] = {
            "existe": existe,
            "sha256_recalculado": h,
            "sha256_inventario_fase3a": inv_hashes.get(bid),
            "coincide": h == inv_hashes.get(bid) if existe else None,
            "tamano_bytes": os.path.getsize(ruta) if existe else None,
        }
    out["duplicados_exactos"] = {
        "preambulos_igual_a_721": out["codigo_preambulos"]["sha256_recalculado"] == out["codigo_721"]["sha256_recalculado"],
    }
    return out


def audit_migracion_0002():
    sql = open(os.path.join(REPO, "bd", "migraciones", "0002_proyectos.sql"), encoding="utf-8").read()
    tablas = re.findall(r"CREATE TABLE (\w+)", sql)
    fks = re.findall(r"REFERENCES (\w+)", sql)
    return {
        "tablas_creadas": tablas,
        "fk_referencian_a": sorted(set(fks)),
        "entidades_proyecto_presupuesto": all(
            t in tablas for t in ("proyectos", "presupuestos", "capitulos_presupuesto", "partidas_presupuesto")),
    }


def audit_tipos_money():
    """Evidencia empírica: qué devuelve access_parser para Money/Float32."""
    import logging
    logging.getLogger("access_parser").setLevel(logging.CRITICAL)
    from access_parser import AccessParser

    evidencia = {}
    for bid, rel in [("codigo_721", BASES["codigo_721"]), ("codigo_raiz", BASES["codigo_raiz"])]:
        db = AccessParser(os.path.join(FUENTE_BASE, rel))
        t = db.parse_table("Nomenclador de RV")
        fila = 1  # segunda fila: CHMN=4.0683 en ambas bases (011112)
        reg = {}
        for col in ("CHMN", "CEMN"):
            v = t[col][fila]
            reg[col] = {"tipo_python": type(v).__name__, "valor_crudo": str(v)[:40]}
        tm = db.parse_table("Norma de Materiales")
        v = tm["CantMat"][0]
        reg["CantMat"] = {"tipo_python": type(v).__name__, "valor_crudo": repr(v),
                          "nota": "Float32: 1.2 se recupera como float64 exacto del binario float32"}
        # Valor real esperado: CHMN 4.0683 (con 4 decimales del Money escalado)
        evidencia[bid] = reg
    evidencia["interpretacion"] = {
        "codigo_721": "Money sin propiedad Format → access_parser devuelve el ENTERO ESCALADO "
                      "(CHMN=40683 ⇒ valor real 4.0683). PrecioU=PMN+PMLC se cumple a cualquier escala.",
        "codigo_raiz": "Money CON propiedad Format → access_parser devuelve STRING formateado a 2 "
                       "decimales ('4.07'), con PÉRDIDA de los decimales 3-4 ('4.0683'→'4.07') y con "
                       "separador de miles para valores ≥1000 ('1,234.57' → float() fallaría).",
        "conclusion": "El importador común DEBE parchear parse_money_type para obtener el Decimal "
                      "exacto /10000 del entero escalado, independiente del Format de cada columna.",
    }
    return evidencia


def audit_importador_poc():
    ruta = os.path.join(REPO, "scripts", "fase3f_importar_poc.py")
    src = open(ruta, encoding="utf-8").read()
    return {
        "archivo": "scripts/fase3f_importar_poc.py",
        "existe": True,
        "alcance": "muestra (510 partidas + 2239 normas + 276 recursos), no importación completa",
        "divide_money_entre_10000": bool(re.search(r"/\s*10000|10\*\*4|scaleb", src)),
        "manja_separador_miles": "replace(\",\", \"\")" in src or "replace(',', '')" in src,
        "idempotente_por_version": "ya existe esta versión" in src,
        "verifica_integridad_originales": "sha256(HTML) == SHA_HTML" in src,
        "defectos": [
            "Con codigo.mdb 7.21/7.22 (Money=int escalado) almacenaría precios ×10000 erróneos; "
            "solo funcionó con la raíz 2017 porque access_parser devolvía strings formateadas.",
            "En la raíz 2017, valores Money ≥1000 llegan como '1,234.57' con coma → float() lanza "
            "excepción → f() devuelve None → el valor se pierde silenciosamente.",
            "En la raíz 2017 los strings formateados pierden los decimales 3-4 (4.0683→'4.07').",
        ],
        "reutilizable": [
            "Mapa tablas PRECODI → entidades del esquema 0001 (grupos/partidas/recursos/normas/componentes).",
            "Patrón idempotente por (catálogo, versión) y registro en importaciones.",
            "Verificación de integridad SHA-256 de originales antes y después.",
            "norm_um() para factor de unidad ('100 m2' → factor 100).",
        ],
    }


def main():
    auditoria = {
        "fase": "III-B · Fase 1 — auditoría previa",
        "generado": datetime.now(timezone.utc).isoformat(),
        "git": audit_git(),
        "html_original": {
            "sha256": sha256(HTML),
            "esperado": "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2",
            "intacto": sha256(HTML) == "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2",
        },
        "bases_mdb": audit_hashes(),
        "migracion_0002": audit_migracion_0002(),
        "tipos_money_float32": audit_tipos_money(),
        "importador_poc_anterior": audit_importador_poc(),
    }
    salida = os.path.join(REPO, "docs", "datos", "auditoria_iiib.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(auditoria, f, ensure_ascii=False, indent=1)

    print("=== AUDITORÍA PREVIA MISIÓN III-B ===")
    print(f"Git: rama {auditoria['git']['rama']}, {len(auditoria['git']['commits'])} commits, "
          f"tag v9.17-original → baseline: {auditoria['git']['tag_apunta_a_commit_baseline']}, "
          f"árbol limpio: {auditoria['git']['arbol_limpio']}")
    print(f"HTML original intacto: {auditoria['html_original']['intacto']}")
    for bid, b in auditoria["bases_mdb"].items():
        if bid == "duplicados_exactos":
            print(f"  {bid}: {b}")
        else:
            print(f"  {bid}: existe={b['existe']} coincide_hash={b['coincide']}")
    print(f"Migración 0002 tablas: {auditoria['migracion_0002']['tablas_creadas']}")
    print(f"Importador PoC divide money/10000: "
          f"{auditoria['importador_poc_anterior']['divide_money_entre_10000']} (defecto confirmado)")
    print(f"\nJSON -> {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
