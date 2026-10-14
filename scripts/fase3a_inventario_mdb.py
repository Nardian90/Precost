#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE III-A — Inventario y extracción de metadatos de las bases .mdb PRECODI.

Lee SOLO (nunca modifica) las 5 bases .mdb extraídas del RAR auxiliar
(AUXILIAR_PRECODI.rar, Drive 2) y produce:

  docs/datos/fase3a_inventario.json   — inventario completo machine-readable
  docs/datos/fase3a_resumen.md        — resumen legible
  stdout                              — resumen de verificación

Por cada base registra: tamaño, SHA-256, procedencia (ruta original dentro
del RAR), versión del formato Jet, fecha de archivo, tablas de usuario,
columnas (nombre, tipo Jet, longitud, decimales, nulabilidad, autonumérico),
claves primarias VERIFICADAS (definición de tabla), número de filas y
muestras de valores (truncadas, no sensibles).

Uso:  python3 scripts/fase3a_inventario_mdb.py
"""
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone

# Silenciar el ruido de access_parser (errores de chunks MSys* esperados)
logging.getLogger("access_parser").setLevel(logging.CRITICAL)

from access_parser import AccessParser  # noqa: E402
from access_parser import utils as ap_utils  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE_BASE = "/home/z/my-project/work/recuperacion/analisis/PRECODI"

# --- Mapa de tipos Jet (valores tomados de access_parser.utils, no inventados) ---
def construir_mapa_tipos():
    mapa = {}
    for nombre in [
        "TYPE_BOOLEAN", "TYPE_INT8", "TYPE_INT16", "TYPE_INT32", "TYPE_COMPLEX",
        "TYPE_MONEY", "TYPE_FLOAT32", "TYPE_FLOAT64", "TYPE_DATETIME",
        "TYPE_BINARY", "TYPE_TEXT", "TYPE_OLE", "TYPE_GUID", "TYPE_MEMO",
        "TYPE_96_bit_17_BYTES",
    ]:
        v = getattr(ap_utils, nombre, None)
        if v is not None:
            mapa[v] = nombre.replace("TYPE_", "")
    return mapa

TIPOS = construir_mapa_tipos()
NOMBRE_TIPO = {
    "BOOLEAN": "Booleano (Sí/No)",
    "INT8": "Byte (entero 8 bits)",
    "INT16": "Entero (16 bits)",
    "INT32": "Entero largo (32 bits)",
    "COMPLEX": "Complejo (multivalor)",
    "MONEY": "Moneda (4 decimales, entero escalado)",
    "FLOAT32": "Real simple (32 bits)",
    "FLOAT64": "Real doble (64 bits)",
    "DATETIME": "Fecha/Hora",
    "BINARY": "Binario",
    "TEXT": "Texto (varchar)",
    "OLE": "Objeto OLE",
    "GUID": "GUID",
    "MEMO": "Memo (texto largo)",
    "TYPE_96_bit_17_BYTES": "Decimal de 96 bits (17 bytes)",
}
NOMBRE_TIPO["TYPE_96_bit_17_BYTES"] = "Decimal de 96 bits (17 bytes)"

BASES = [
    {
        "id": "codigo_721",
        "archivo": "Codigo (PRECODI)/7.21/codigo.mdb",
        "etiqueta": "codigo.mdb v7.21 (carpeta 7.21)",
        "procedencia_rar": "Codigo (PRECODI)/7.21/codigo.mdb",
    },
    {
        "id": "codigo_722",
        "archivo": "Codigo (PRECODI)/7.22/codigo.mdb",
        "etiqueta": "codigo.mdb v7.22 (carpeta 7.22)",
        "procedencia_rar": "Codigo (PRECODI)/7.22/codigo.mdb",
    },
    {
        "id": "codigo_raiz",
        "archivo": "Codigo (PRECODI)/codigo.mdb",
        "etiqueta": "codigo.mdb raíz (junto a Codigo.exe)",
        "procedencia_rar": "Codigo (PRECODI)/codigo.mdb",
    },
    {
        "id": "codigo_preambulos",
        "archivo": "Codigo (PRECODI)/Preambulos/codigo.mdb",
        "etiqueta": "codigo.mdb (carpeta Preambulos)",
        "procedencia_rar": "Codigo (PRECODI)/Preambulos/codigo.mdb",
    },
    {
        "id": "sbd2008_815",
        "archivo": "Codigo (PRECODI)/8.15/SBD2008_815.mdb",
        "etiqueta": "SBD2008_815.mdb (carpeta 8.15)",
        "procedencia_rar": "Codigo (PRECODI)/8.15/SBD2008_815.mdb",
    },
]

JET_VERSIONES = {0: "Jet 3 (formato Access 97)", 1: "Jet 4 (formato Access 2000)",
                 2: "Jet 4 (formato Access 2002/2003)", 3: "Access 2010+"}


def sha256_de(ruta, trozo=1024 * 1024):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        while True:
            b = f.read(trozo)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def valor_muestra(v, largo=60):
    """Representación no sensible y serializable de un valor."""
    if v is None:
        return None
    if isinstance(v, bytes):
        return f"<binario {len(v)} bytes>"
    if isinstance(v, (int, float, bool)):
        return v
    s = str(v)
    if len(s) > largo:
        s = s[:largo] + "…"
    if s.strip() == "":
        return ""
    return s


def inventariar_tabla(db, nombre_tabla):
    """Metadatos + conteo + muestras de una tabla (solo lectura)."""
    info = {"tabla": nombre_tabla, "columnas": [], "claves_primarias": [],
            "filas": None, "muestras": [], "error": None}
    try:
        t = db.get_table(nombre_tabla)
        for idx in sorted(t.columns):
            c = t.columns[idx]
            tipo_id = c.type
            tipo_nombre_corto = TIPOS.get(tipo_id, f"Desconocido({tipo_id})")
            col = {
                "nombre": c.col_name_str,
                "tipo_jet": tipo_id,
                "tipo": NOMBRE_TIPO.get(tipo_nombre_corto, tipo_nombre_corto),
                "longitud": c.length,
                "nulable": bool(c.column_flags.can_be_null),
                "autonumerico": bool(c.column_flags.autonumber),
            }
            varios = getattr(c, "various", None)
            if varios is not None and hasattr(varios, "number_of_decimal"):
                col["decimales"] = varios.number_of_decimal
                col["digitos_max"] = varios.max_number_of_digits
            info["columnas"].append(col)
        if t.primary_keys:
            info["claves_primarias"] = list(t.primary_keys)
        # Datos: conteo + 3 muestras
        datos = t.parse()
        if datos:
            info["filas"] = max(len(v) for v in datos.values())
            n_cols = len(datos)
            for i in range(min(3, info["filas"])):
                fila = {}
                for col_name, valores in datos.items():
                    if i < len(valores):
                        fila[col_name] = valor_muestra(valores[i])
                info["muestras"].append(fila)
            info["_cols_datos"] = n_cols
    except Exception as e:  # noqa: BLE001
        info["error"] = f"{type(e).__name__}: {e}"
    return info


def main():
    salida = {
        "fase": "III-A",
        "generado": datetime.now(timezone.utc).isoformat(),
        "herramienta": "access-parser (Python puro, solo lectura)",
        "bases": [],
        "notas": [
            "Las claves primarias provienen de la definición interna de tabla Jet "
            "(tddef) leída por access-parser: son VERIFICADAS, no inferidas.",
            "Los conteos de filas se obtienen parseando todas las páginas de datos.",
            "MSysObjects y demás tablas de sistema se excluyen del inventario.",
        ],
    }
    for base in BASES:
        ruta = os.path.join(FUENTE_BASE, base["archivo"])
        print(f"\n=== {base['etiqueta']} ===")
        if not os.path.exists(ruta):
            print(f"  !! NO ENCONTRADA: {ruta}")
            salida["bases"].append({**base, "error": "archivo no encontrado"})
            continue
        reg = {**base}
        reg["ruta_analisis"] = ruta
        reg["tamano_bytes"] = os.path.getsize(ruta)
        reg["sha256"] = sha256_de(ruta)
        reg["mtime"] = datetime.fromtimestamp(
            os.path.getmtime(ruta), tz=timezone.utc).isoformat()
        with open(ruta, "rb") as f:
            cab = f.read(32)
        reg["formato_jet"] = JET_VERSIONES.get(cab[0x14], f"byte 0x14={cab[0x14]:#x}")
        try:
            db = AccessParser(ruta)
            tablas_usuario = [n for n in db.catalog if not n.startswith("MSys")]
            reg["total_tablas_sistema_y_usuario"] = len(db.catalog)
            reg["tablas"] = []
            for i, nombre in enumerate(sorted(tablas_usuario)):
                ti = inventariar_tabla(db, nombre)
                reg["tablas"].append(ti)
                estado = f"{ti['filas']} filas" if ti["filas"] is not None else "sin datos"
                if ti["error"]:
                    estado = f"ERROR: {ti['error'][:60]}"
                print(f"  [{i+1:3d}/{len(tablas_usuario)}] {nombre}: {estado}")
        except Exception as e:  # noqa: BLE001
            reg["error_general"] = f"{type(e).__name__}: {e}"
            print(f"  !! ERROR GENERAL: {e}")
        reg["num_tablas_usuario"] = len(reg.get("tablas", []))
        salida["bases"].append(reg)

    # --- Guardar salidas ---
    ruta_json = os.path.join(REPO, "docs", "datos", "fase3a_inventario.json")
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    print(f"\nJSON  -> {ruta_json}")

    # --- Resumen markdown ---
    lineas = ["# FASE III-A — Inventario de bases .mdb PRECODI (resumen automático)", ""]
    lineas.append(f"Generado: {salida['generado']} · Herramienta: access-parser (solo lectura)")
    lineas.append("")
    for reg in salida["bases"]:
        lineas.append(f"## {reg.get('etiqueta', reg.get('id'))}")
        lineas.append("")
        lineas.append(f"- Archivo: `{reg.get('procedencia_rar')}`")
        lineas.append(f"- Tamaño: {reg.get('tamano_bytes', 0):,} bytes · SHA-256: `{reg.get('sha256', '')[:32]}…`")
        lineas.append(f"- Formato: {reg.get('formato_jet')} · Fecha de archivo: {reg.get('mtime', '')[:10]}")
        if "error_general" in reg:
            lineas.append(f"- **ERROR GENERAL: {reg['error_general']}**")
            continue
        lineas.append(f"- Tablas de usuario: {reg['num_tablas_usuario']}")
        lineas.append("")
        lineas.append("| Tabla | Filas | Clave primaria (verificada) | Columnas |")
        lineas.append("|---|---:|---|---|")
        for t in reg["tablas"]:
            pk = ", ".join(t["claves_primarias"]) or "—"
            filas = "?" if t["filas"] is None else f"{t['filas']:,}"
            lineas.append(f"| {t['tabla']} | {filas} | {pk} | {len(t['columnas'])} |")
        lineas.append("")
    ruta_md = os.path.join(REPO, "docs", "datos", "fase3a_resumen.md")
    with open(ruta_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    print(f"Resumen -> {ruta_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
