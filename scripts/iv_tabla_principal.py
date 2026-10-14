#!/usr/bin/env python3
"""MISIÓN IV — Fase C: deducir el formato de la tabla principal de archivos.

Vuelca los 64 bytes anteriores a varias rutas @$&%04\\... del payload para
identificar los campos binarios (tamaños, offsets, fecha, atributos).
"""
import struct
from pathlib import Path

EXE = Path("/home/z/my-project/work/recuperacion/analisis/"
           "SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe")


def hexdump(data, start, end):
    for off in range(start, end, 16):
        chunk = data[off:off + 16]
        hexs = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"{off:08x}  {hexs:<47}  {asc}")


RUTAS = [
    b"@$&%04\\App\\MANUAL\\Manual SIECONS\\Manual B",
    b"@$&%04\\BD\\SBD_11\\SBD_11_MICONS_2025\\SBD_MICONS_2025.mdb",
    b"@$&%04\\App\\SIECONS\\Siecons_11_13.accde",
    b"@$&%04\\App\\MANUAL\\Como Quitar Vencimiento del SIECONS",
    b"@$&%04\\App\\Auxiliar\\PLANTILLA 2021.xls",
    b"@$&%04\\App\\MANUAL\\Como Instalar SIECONS\\Como Instalar",
    b"@$&%04\\App\\BIN\\dynapdf.dll",
]


def main():
    data = EXE.read_bytes()
    vistos = []
    for r in RUTAS:
        idx = 0
        while True:
            idx = data.find(r, idx + 1)
            if idx < 0:
                break
            if idx in vistos:
                continue
            vistos.append(idx)
            print(f"\n=== Ruta en {idx:,} ===")
            # contexto: 80 bytes antes, 40 después
            hexdump(data, max(0, idx - 80), idx + 80)

    # Todos los @$&%04 en orden con offsets
    print("\n\n=== Todas las apariciones de @$&%04 ===")
    idx = 0
    todas = []
    while True:
        idx = data.find(b"@$&%04", idx + 1)
        if idx < 0:
            break
        fin = data.find(b"\x00", idx)
        ruta = data[idx:fin].decode("latin-1", "replace")
        todas.append((idx, ruta))
    print(f"Total: {len(todas)}")
    for idx, ruta in todas:
        print(f"  {idx:>9,}  {ruta[:80]}")


if __name__ == "__main__":
    main()
