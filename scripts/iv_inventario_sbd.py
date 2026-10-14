#!/usr/bin/env python3
"""MISIÓN IV — Línea A: inventario de las bases de datos del payload SIECONS.

SBD_MICONS_2025.mdb es la base de precios que SIECONS 11 usa por defecto
(MICONS 2025). Compararla con el catálogo embebido de PRECOST 2025 ofrece
una verificación de fidelidad independiente y de la misma época.

También se inventaría Config.sie (resultó ser un MDB Jet) y
BD_SIFCBIM_11.mdb.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/home/z/my-project/precost/scripts")
from access_parser import AccessParser  # noqa: E402

BASES = [
    ("SBD_MICONS_2025", Path("/home/z/my-project/work/siecons_extract/payload/"
                             "BD/SBD_11/SBD_11_MICONS_2025/SBD_MICONS_2025.mdb")),
    ("Config.sie", Path("/home/z/my-project/work/siecons_extract/payload/"
                        "App/SIECONS/Config.sie")),
    ("BD_SIFCBIM_11", Path("/home/z/my-project/work/siecons_extract/payload/"
                           "App/SIFCBIM/BD_SIFCBIM/BD_SIFCBIM_11.mdb")),
]


def main():
    for nombre, ruta in BASES:
        print(f"\n{'='*72}\n=== {nombre} ({ruta.name}) ===")
        print(f"Tamaño: {ruta.stat().st_size:,} B")
        try:
            db = AccessParser(str(ruta))
            tablas = db.catalog
            print(f"Tablas: {len(tablas)}")
            con_datos = 0
            for t in sorted(tablas):
                try:
                    tabla = db.get_table(t).parse()
                    filas = len(next(iter(tabla.values()))) if tabla else 0
                except Exception as e:
                    filas = f"error: {type(e).__name__}"
                if isinstance(filas, int) and filas > 0:
                    con_datos += 1
                print(f"  {t:<44} {filas}")
            print(f"Tablas con datos: {con_datos}")
        except Exception as e:
            print(f"ERROR abriendo: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
