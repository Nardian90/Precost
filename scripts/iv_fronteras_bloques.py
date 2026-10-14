#!/usr/bin/env python3
"""MISIÓN IV — Fase C: mapeo de fronteras de bloques del payload SIM.

Con el flujo raw-deflate @195,230 como referencia, rastrea hacia atrás para
identificar la cabecera del bloque (tamaños, CRC, nombre) y hacia adelante
para encontrar el siguiente bloque. Objetivo: deducir el formato del
contenedor .pak de Smart Install Maker v5.04.
"""
import struct
import zlib
from pathlib import Path

EXE = Path("/home/z/my-project/work/recuperacion/analisis/"
           "SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe")


def hexdump(data, start, end):
    for off in range(start, end, 16):
        chunk = data[off:off + 16]
        hexs = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"{off:08x}  {hexs:<47}  {asc}")


def main():
    data = EXE.read_bytes()
    # 1. Tamaño exacto del PNG almacenado en 190,860
    png_start = data.find(b"\x89PNG\r\n\x1a\n", 190_000)
    print(f"PNG @ {png_start:,}")
    p = png_start + 8
    while p < len(data):
        largo = struct.unpack(">I", data[p:p + 4])[0]
        tipo = data[p + 4:p + 8]
        fin = p + 8 + largo + 4
        if tipo == b"IEND":
            break
        p = fin
    png_fin = fin
    print(f"PNG termina en {png_fin:,} (tamaño {png_fin - png_start:,} B)")

    # 2. Volcado entre el fin del PNG y el flujo deflate
    print(f"\n--- Entre PNG ({png_fin:,}) y deflate (195,230) ---")
    hexdump(data, png_fin - 16, 195_230 + 32)

    # 3. Fin exacto del flujo deflate @195,230
    d = zlib.decompressobj(-15)
    out = d.decompress(data[195_230:195_230 + 5_000_000])
    usado = len(data[195_230:]) - len(d.unused_data) - 195_230 + 195_230
    fin_deflate = 195_230 + (len(data) - 195_230 - len(d.unused_data)) - (len(data) - 195_230) + (len(data[195_230:]) - len(d.unused_data))
    # cálculo directo:
    consumido = len(data[195_230:]) - len(d.unused_data)
    fin_flujo = 195_230 + consumido
    print(f"\nDeflate @195,230: out={len(out):,} B, consumido={consumido:,}, "
          f"fin={fin_flujo:,}, eof={d.eof}")
    print(f"Salida: primeros 64 B = {out[:64].hex()}")
    print(f"Contenido detectable: "
          f"{''.join(chr(b) if 32 <= b < 127 else '.' for b in out[:96])}")

    # 4. Después del fin del flujo: ¿cabecera del siguiente bloque?
    print(f"\n--- Tras el fin del flujo deflate ---")
    hexdump(data, fin_flujo, fin_flujo + 128)

    # 5. ¿Y antes del PNG? (entre la tabla $inst y el PNG)
    print(f"\n--- Entre tabla $inst (~190,899) y PNG ({png_start:,}) ---")
    hexdump(data, 190_890, png_start + 8)


if __name__ == "__main__":
    main()
