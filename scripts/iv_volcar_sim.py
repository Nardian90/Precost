#!/usr/bin/env python3
"""MISIÓN IV — Fase C: volcado estructurado de la cabecera de datos SIM.

El instalador SIECONS 11 (Smart Install Maker v5.04) contiene la tabla de
archivos en texto claro a partir de la cadena "Smart Install Maker".
Este script vuelca esa zona para mapear el formato del contenedor.
"""
import struct
import sys
from pathlib import Path

EXE = Path("/home/z/my-project/work/recuperacion/analisis/"
           "SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe")


def hexdump(data, base, start, length):
    for off in range(start, start + length, 16):
        chunk = data[off:off + 16]
        hexs = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"{base + off:08x}  {hexs:<47}  {asc}")


def main():
    data = EXE.read_bytes()
    inicio = data.find(b"Smart Install Maker\x00")
    print(f"Inicio de metadatos SIM: {inicio} (0x{inicio:x})")
    print(f"Tamaño total: {len(data):,}\n")

    # Volcar los primeros 2048 bytes de la zona de metadatos
    hexdump(data, 0, inicio, 2048)

    # Localizar la zona de la tabla de archivos (donde aparecen las rutas)
    print("\n--- Zona de rutas (contexto antes de 'App\\SIECONS') ---")
    p = data.find(b"App\\SIECONS\\Siecons")
    print(f"Primera ruta del payload en: {p}")
    hexdump(data, 0, max(0, p - 256), 512)


if __name__ == "__main__":
    main()
