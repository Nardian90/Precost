#!/usr/bin/env python3
"""MISIÓN IV — Fase C: parser del contenedor .pak de Smart Install Maker v5.04.

Hipótesis verificada: la tabla de recursos usa entradas
    [u32 tamaño][u32 offset][u16 ?][u32 crc32][u16 flags][nombre\\0]
donde offset es relativo al inicio del área de datos (el PNG#1 @190,859).

Este script:
  1. Parsea la tabla $inst y valida hipótesis contra PNG#1/PNG#2.
  2. Vuelca y clasifica cada blob (¿raw?, ¿deflate?).
  3. Busca la tabla principal de archivos (rutas @$&%04\\...) con el mismo
     formato de entrada, para localizar el Manual Básico SIECONS.pdf.
"""
import re
import struct
import zlib
from pathlib import Path

EXE = Path("/home/z/my-project/work/recuperacion/analisis/"
           "SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe")

DATA_BASE = None  # se calcula: inicio del área de datos (PNG#1)


def parsear_entrada(buf, p):
    """Parsea [u32 tam][u32 off][u16 ?][u32 crc][u16 flags][nombre\\0].
    Devuelve (dict, siguiente_p) o (None, p)."""
    if p + 16 > len(buf):
        return None, p
    tam, off = struct.unpack("<II", buf[p:p + 8])
    pad = struct.unpack("<H", buf[p + 8:p + 10])[0]
    crc = struct.unpack("<I", buf[p + 10:p + 14])[0]
    flags = struct.unpack("<H", buf[p + 14:p + 16])[0]
    q = buf.find(b"\x00", p + 16)
    if q < 0:
        return None, p
    nombre = buf[p + 16:q].decode("latin-1")
    if not nombre:
        return None, p
    return dict(tam=tam, off=off, pad=pad, crc=crc, flags=flags,
                nombre=nombre), q + 1


def main():
    data = EXE.read_bytes()
    global DATA_BASE
    DATA_BASE = data.find(b"\x89PNG\r\n\x1a\n", 190_000)
    print(f"Área de datos (base) @ {DATA_BASE:,}")

    # --- 1. Validar la tabla $inst ------------------------------------
    # La tabla empieza donde está la primera entrada de 4.tmp.
    p = data.find(b"$inst\\4.tmp")
    # retroceder 16 bytes (campos binarios) desde el nombre
    ini = p - 16
    print(f"\n=== Tabla $inst (entradas hacia adelante desde {ini:,}) ===")
    entradas = []
    q = ini
    while True:
        e, q2 = parsear_entrada(data, q)
        if e is None or not (e["nombre"].startswith("$inst") or
                             e["nombre"].startswith("MAINICON")):
            break
        entradas.append(e)
        q = q2
    for e in entradas:
        print(f"  {e['nombre']:<16} tam={e['tam']:>10,} off={e['off']:>10,} "
              f"pad={e['pad']} crc={e['crc']:#010x} flags={e['flags']:#x}")

    # Validación: 4.tmp debe apuntar al PNG#1 con tamaño exacto
    print("\n=== Validación de blobs $inst ===")
    for e in entradas:
        abs_off = DATA_BASE + e["off"]
        blob = data[abs_off:abs_off + min(e["tam"] + 64, 4_000_000)]
        tipo = "¿?"
        # ¿está almacenado tal cual?
        if len(blob) >= e["tam"]:
            trozo = blob[:e["tam"]]
            import binascii
            crc_calc = binascii.crc32(trozo) & 0xFFFFFFFF
            if crc_calc == e["crc"]:
                tipo = f"RAW (crc OK, {e['tam']:,} B)"
            else:
                tipo = f"¿raw? crc {crc_calc:#x} != {e['crc']:#x}"
        # ¿deflate crudo?
        try:
            d = zlib.decompressobj(-15)
            out = d.decompress(blob, e["tam"] + 1)
            if d.eof:
                import binascii
                crc_calc = binascii.crc32(out) & 0xFFFFFFFF
                tipo = (f"DEFLATE crudo: out={len(out):,} B "
                        f"(esperado {e['tam']:,}), "
                        f"consumidos={len(blob) - len(d.unused_data):,}, "
                        f"crc={'OK' if crc_calc == e['crc'] else 'X'})")
        except zlib.error:
            pass
        # ¿zlib?
        try:
            d = zlib.decompressobj()
            out = d.decompress(blob, e["tam"] + 1)
            if d.eof:
                import binascii
                crc_calc = binascii.crc32(out) & 0xFFFFFFFF
                tipo = (f"ZLIB: out={len(out):,} B "
                        f"(esperado {e['tam']:,}), "
                        f"consumidos={len(blob) - len(d.unused_data):,}, "
                        f"crc={'OK' if crc_calc == e['crc'] else 'X'})")
        except zlib.error:
            pass
        print(f"  {e['nombre']:<16} @abs {abs_off:>10,}: {tipo}")
        print(f"      primeros bytes: {data[abs_off:abs_off+24].hex()}")

    # --- 2. Buscar tabla principal con el mismo formato ----------------
    print("\n=== Búsqueda de la tabla principal (rutas @$&%04\\...) ===")
    # Buscar entradas válidas cuyo nombre empiece por la ruta de instalación
    # variable. Patrón: 16 bytes binarios + "@$&%04\\"
    idx = 0
    encontradas = []
    while True:
        idx = data.find(b"@$&%04\\", idx + 1)
        if idx < 0:
            break
        e, _ = parsear_entrada(data, idx - 16)
        if e and e["nombre"].startswith("@$&%04\\") and 0 < e["tam"] < 400_000_000:
            encontradas.append((idx - 16, e))
    print(f"Entradas de tabla principal candidatas: {len(encontradas)}")
    for off, e in encontradas[:60]:
        print(f"  @{off:>9,}  {e['nombre'][:70]:<70} "
              f"tam={e['tam']:>11,} off={e['off']:>11,} "
              f"crc={e['crc']:#010x} flags={e['flags']:#06x}")
    if len(encontradas) > 60:
        print(f"  ... y {len(encontradas) - 60} más")


if __name__ == "__main__":
    main()
