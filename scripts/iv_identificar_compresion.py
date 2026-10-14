#!/usr/bin/env python3
"""MISIÓN IV — Fase C: identificar la compresión de los blobs del .pak.

Prueba sobre los inicios EXACTOS de cada blob conocido ($inst y payload
principal) todos los métodos plausibles:
  zlib, raw deflate, bz2, lzma (alone/raw/xz), aplib,
  XOR 1 byte + zlib/deflate, RLE, y variantes con salto de cabecera.
Valida contra el CRC32 de la entrada cuando es conocido.
"""
import binascii
import bz2
import lzma
import struct
import zlib
from pathlib import Path

import aplib

EXE = Path("/home/z/my-project/work/recuperacion/analisis/"
           "SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe")
DATA_BASE = 190_859

BLOBS = [
    # (nombre, offset_absoluto, tam_almacenado, crc32)
    ("$inst\\4.tmp", DATA_BASE + 0, 4_278, 0xAD723F7B),
    ("$inst\\5.tmp", DATA_BASE + 4_278, 42_877, 0xB4D34C55),
    ("$inst\\6.tmp", DATA_BASE + 47_155, 3_483_702, 0x470D548B),
    ("$inst\\7.tmp", DATA_BASE + 3_530_857, 2_866, 0x9CB43F7B),
    ("$inst\\15.tmp", DATA_BASE + 3_533_723, 10_089, 0x83265AF6),
    ("$inst\\20.tmp", DATA_BASE + 3_543_812, 10_089, 0x83265AF6),
    ("payload_principal", DATA_BASE + 3_553_901, 39_477_691, None),
]


def intentos(data, off, tam, crc):
    """Generador de (metodo, salida) para todos los métodos."""
    blob = data[off:off + min(tam, 2_000_000)]
    # zlib estándar
    try:
        d = zlib.decompressobj()
        out = d.decompress(blob, 50_000_000)
        if out:
            yield "zlib", out, d.eof
    except zlib.error:
        pass
    # raw deflate
    try:
        d = zlib.decompressobj(-15)
        out = d.decompress(blob, 50_000_000)
        if out:
            yield "raw-deflate", out, d.eof
    except zlib.error:
        pass
    # bz2
    try:
        d = bz2.BZ2Decompressor()
        out = d.decompress(blob)
        if out:
            yield "bz2", out, d.eof
    except Exception:
        pass
    # lzma en 3 formatos
    for fmt, nombre in ((lzma.FORMAT_ALONE, "lzma-alone"),
                        (lzma.FORMAT_XZ, "xz"),
                        (lzma.FORMAT_RAW, "lzma-raw")):
        try:
            filt = [{"id": lzma.FILTER_LZMA1}] if fmt == lzma.FORMAT_RAW else None
            d = lzma.LZMADecompressor(format=fmt, filters=filt)
            out = d.decompress(blob)
            if out:
                yield nombre, out, d.eof
        except Exception:
            pass
    # aplib
    try:
        out = aplib.decompress(blob[:300_000])
        if out:
            yield "aplib", out, True
    except Exception:
        pass
    # XOR con clave de 1 byte + zlib/deflate
    for clave in range(1, 256):
        dec = bytes(b ^ clave for b in blob[:4096])
        for wbits, nom in ((15, "xor+zlib"), (-15, "xor+deflate")):
            try:
                d = zlib.decompressobj(wbits)
                out = d.decompress(dec, 1_000_000)
                if len(out) > 256:
                    yield f"{nom}(k={clave:#x})", out, d.eof
            except zlib.error:
                pass
    # cabecera de 4 bytes (tamaño) + deflate/zlib
    if len(blob) > 8:
        for salto in (2, 4, 8, 12, 16):
            for wbits, nom in ((15, f"skip{salto}+zlib"), (-15, f"skip{salto}+deflate")):
                try:
                    d = zlib.decompressobj(wbits)
                    out = d.decompress(blob[salto:], 1_000_000)
                    if len(out) > 256:
                        yield nom, out, d.eof
                except zlib.error:
                    pass


def main():
    data = EXE.read_bytes()
    for nombre, off, tam, crc in BLOBS:
        print(f"\n=== {nombre} @ {off:,} (tam={tam:,}, crc={crc and hex(crc)}) ===")
        print(f"  inicio: {data[off:off+32].hex()}")
        hallado = False
        for metodo, out, eof in intentos(data, off, tam, crc):
            crc_calc = binascii.crc32(out) & 0xFFFFFFFF
            marca = "CRC-OK" if crc and crc_calc == crc else f"crc={crc_calc:#x}"
            print(f"  [{metodo}] out={len(out):,} B eof={eof} {marca} "
                  f"cab={out[:32]!r}")
            hallado = True
        if not hallado:
            print("  (ningún método produjo salida)")

    # Estadística de bytes del blob grande: ¿parece cifrado o comprimido?
    print("\n=== Entropía y patrón de $inst\\6.tmp (primeros 64 KB) ===")
    trozo = data[DATA_BASE + 47_155: DATA_BASE + 47_155 + 65_536]
    freq = [0] * 256
    for b in trozo:
        freq[b] += 1
    import math
    ent = -sum((c / len(trozo)) * math.log2(c / len(trozo))
               for c in freq if c)
    print(f"Entropía: {ent:.3f} bits/byte (8 = aleatorio)")
    ceros = freq[0]
    print(f"Bytes 0x00: {ceros:,} ({100*ceros/len(trozo):.2f}%)")
    # distribución de nibbles altos
    altos = [sum(freq[i*16:(i+1)*16]) for i in range(16)]
    print("Distribución nibble alto:", [f"{a//64}" for a in altos])


if __name__ == "__main__":
    main()
