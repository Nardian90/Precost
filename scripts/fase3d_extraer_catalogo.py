#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE III-D (paso 1) — Extracción del catálogo embebido de PRECOST.

Extrae SIN MODIFICAR el HTML original la constante `DB` (catálogo normativo
PRECONS III MICONS 2025) y la vuelca a JSON analyzable:

  docs/datos/fase3d_precost_db.json  — catálogo extraído íntegro
  stdout — estructura y conteos

Uso:  python3 scripts/fase3d_extraer_catalogo.py
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, "app", "PRECOST-v9.17.html")


def extraer_objeto_js(texto, inicio):
    """Extrae el objeto {…} que empieza en `inicio` ('{') respetando strings."""
    profundidad = 0
    i = inicio
    en_str = None
    while i < len(texto):
        c = texto[i]
        if en_str:
            if c == "\\":
                i += 2
                continue
            if c == en_str:
                en_str = None
        elif c in ('"', "'", "`"):
            en_str = c
        elif c == "{":
            profundidad += 1
        elif c == "}":
            profundidad -= 1
            if profundidad == 0:
                return texto[inicio:i + 1]
        i += 1
    raise ValueError("objeto sin cerrar")


def main():
    html = open(HTML, encoding="utf-8").read()
    m = re.search(r'const\s+DB\s*=\s*', html)
    if not m:
        print("No se encontró const DB")
        return 1
    ini = m.end() + html[m.end():].index("{")
    obj_txt = extraer_objeto_js(html, ini)
    print(f"DB extraída: {len(obj_txt):,} caracteres")
    # El objeto usa claves entre comillas → intentar JSON directo
    try:
        db = json.loads(obj_txt)
        print("Parseado como JSON puro: OK")
    except json.JSONDecodeError as e:
        print(f"JSON estricto falló ({e}); normalizando comillas simples…")
        # reemplazo conservador: claves/strings con comilla simple
        norm = re.sub(r"'([^'\\]*)'", r'"\1"', obj_txt)
        db = json.loads(norm)
        print("Normalizado y parseado: OK")

    print("\nClaves de nivel superior:", list(db.keys()))
    print("\nmeta:", json.dumps(db.get("meta", {}), ensure_ascii=False, indent=1)[:800])

    # Conteos por conjunto
    resumen = {}
    for k, v in db.items():
        if isinstance(v, dict) and k != "meta":
            resumen[k] = len(v)
    print("\nConjuntos y conteos:", resumen)

    # Muestras de cada conjunto
    for k, v in db.items():
        if isinstance(v, dict) and k != "meta" and v:
            kk = next(iter(v))
            print(f"\nMuestra {k}[{kk!r}] = {json.dumps(v[kk], ensure_ascii=False)[:200]}")

    salida = os.path.join(REPO, "docs", "datos", "fase3d_precost_db.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)
    print(f"\n-> {salida}")

    # Verificar que el HTML no cambió
    import hashlib
    h = hashlib.sha256(open(HTML, "rb").read()).hexdigest()
    esperado = "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"
    print(f"HTML intacto: {'SÍ' if h == esperado else '¡NO! ' + h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
