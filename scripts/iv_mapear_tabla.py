#!/usr/bin/env python3
"""MISIÓN IV — Fase C: mapeo de la tabla de archivos SIM y sondeo de blobs.

1) Enumera las cadenas de la tabla (offset, contenido) para entender el formato.
2) Localiza el final de la tabla y el inicio de los datos comprimidos.
3) Prueba métodos de descompresión (zlib raw, aplib, lzma) sobre los blobs.
"""
import re
import struct
import zlib
from pathlib import Path

EXE = Path("/home/z/my-project/work/recuperacion/analisis/"
           "SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe")


def main():
    data = EXE.read_bytes()

    # --- 1. Extensión de la tabla: cadenas en 178000..240000 -------------
    print("=== Tabla de archivos: cadenas con offset ===")
    for m in re.finditer(rb"[\x20-\x7e\xe1\xe9\xed\xf3\xf1\xe1]{4,120}", data[178000:240000]):
        off = 178000 + m.start()
        s = m.group().decode("latin-1")
        print(f"{off:>8}  {s}")

    # --- 2. ¿Qué contiene el único flujo zlib válido? --------------------
    print("\n=== Flujo zlib válido @190900 ===")
    try:
        d = zlib.decompressobj()
        out = d.decompress(data[190900:190900 + 200000])
        print(f"Descomprimido: {len(out)} bytes")
        print("Primeros 128 bytes:", out[:128])
        print("ASCII:", "".join(chr(b) if 32 <= b < 127 else "." for b in out[:128]))
    except Exception as e:
        print("error:", e)


if __name__ == "__main__":
    main()
