#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE III-E — Ejecutor de migraciones versionadas para la base PRECOST.

Aplica en orden los scripts SQL de bd/migraciones/ a una base SQLite NUEVA
o existente, registrando cada migración en la tabla schema_migrations.
Es idempotente: las migraciones ya aplicadas no se reejecutan.

Uso:
  python3 scripts/fase3e_migrar.py [ruta_bd]
  (por defecto: prueba/db/precost_catalogo.db)
"""
import os
import sqlite3
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_MIG = os.path.join(REPO, "bd", "migraciones")
BD_DEFECTO = os.path.join(REPO, "prueba", "db", "precost_catalogo.db")

SQL_MIG = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    aplicada_en TEXT NOT NULL DEFAULT (datetime('now')),
    script      TEXT NOT NULL
);
"""


def listar_migraciones():
    """Devuelve [(version, ruta)] ordenadas por versión."""
    out = []
    for nombre in sorted(os.listdir(DIR_MIG)):
        if nombre.endswith(".sql") and nombre[0].isdigit():
            version = nombre.split("_", 1)[0]
            out.append((version, os.path.join(DIR_MIG, nombre)))
    return out


def main():
    ruta_bd = sys.argv[1] if len(sys.argv) > 1 else BD_DEFECTO
    os.makedirs(os.path.dirname(ruta_bd), exist_ok=True)
    nueva = not os.path.exists(ruta_bd)
    con = sqlite3.connect(ruta_bd)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SQL_MIG)
    aplicadas = {r[0] for r in con.execute("SELECT version FROM schema_migrations")}
    print(f"Base: {ruta_bd} ({'NUEVA' if nueva else 'existente'})")
    print(f"Migraciones aplicadas: {sorted(aplicadas) if aplicadas else 'ninguna'}")
    for version, ruta in listar_migraciones():
        if version in aplicadas:
            print(f"  = {version} ya aplicada (salta)")
            continue
        sql = open(ruta, encoding="utf-8").read()
        try:
            con.executescript(sql)
            con.execute("INSERT INTO schema_migrations (version, script) VALUES (?, ?)",
                        (version, os.path.basename(ruta)))
            con.commit()
            print(f"  + {version} aplicada: {os.path.basename(ruta)}")
        except sqlite3.Error as e:
            con.rollback()
            print(f"  !! ERROR en {ruta}: {e}", file=sys.stderr)
            return 1
    # resumen
    tablas = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    print(f"\nTablas ({len(tablas)}): {', '.join(tablas)}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
