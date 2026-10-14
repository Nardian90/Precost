#!/usr/bin/env python3
"""MISIÓN IV — Línea A: esquemas y muestras de las tablas clave de SBD_MICONS_2025.

Tablas nomencladores (catálogos) y normas (composiciones) de la base que
SIECONS 11 usa por defecto, para el cotejo de fidelidad con PRECOST.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/home/z/my-project/precost/scripts")
from access_parser import AccessParser  # noqa: E402

SBD = Path("/home/z/my-project/work/siecons_extract/payload/"
           "BD/SBD_11/SBD_11_MICONS_2025/SBD_MICONS_2025.mdb")

TABLAS = [
    "Nomenclador de RV",
    "Nomenclador de Materiales",
    "Nomenclador de Equipos",
    "Nomenclador de RH",
    "Nomenclador de Juegos",
    "Nomenclador de Semielaborados",
    "Nomenclador de SubGrupos RV",
    "Nomenclador de Grupos RV",
    "Nomenclador de SobreGrupos RV",
    "Norma de Materiales",
    "Norma de Mano de Obra",
    "Norma de Equipos",
    "Norma de Juegos",
    "Norma de Semielaborados",
    "Normas RH",
    "Normas Descriptivas",
    "Tarifas de T",
    "Categorias Salariales",
]


def main():
    db = AccessParser(str(SBD))
    for t in TABLAS:
        print(f"\n=== {t} ===")
        try:
            tabla = db.get_table(t).parse()
            if not tabla:
                print("  (vacía)")
                continue
            cols = list(tabla.keys())
            print(f"  Columnas ({len(cols)}): {cols}")
            n = len(next(iter(tabla.values())))
            print(f"  Filas: {n}")
            # primeras 3 filas
            for i in range(min(3, n)):
                fila = {c: tabla[c][i] for c in cols}
                fila_s = {c: (str(v)[:40] if v is not None else None)
                          for c, v in fila.items()}
                print(f"  [{i}] {fila_s}")
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
