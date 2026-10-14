#!/usr/bin/env python3
"""MISIÓN IV — Fase C: análisis criptográfico y de formato de los blobs.

Pruebas:
  1. ¿15.tmp y 20.tmp (mismo CRC, mismo tamaño) tienen ciphertext idéntico?
     → determina si hay keystream por-archivo o continuo.
  2. Buscar cadenas de cifrado/compresión en el instalador.
  3. Probar LZMA raw con todas las combinaciones lc/lp/pb.
  4. Validar el campo CRC: ¿crc32 del contenido? ¿de la ruta? ¿fecha?
"""
import binascii
import lzma
import re
import struct
import zlib
from pathlib import Path

EXE = Path("/home/z/my-project/work/recuperacion/analisis/"
           "SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe")
DATA_BASE = 190_859


def main():
    data = EXE.read_bytes()

    # --- 1. Comparar 15.tmp y 20.tmp -----------------------------------
    b15 = data[DATA_BASE + 3_533_723: DATA_BASE + 3_533_723 + 10_089]
    b20 = data[DATA_BASE + 3_543_812: DATA_BASE + 3_543_812 + 10_089]
    print("=== 15.tmp vs 20.tmp ===")
    print(f"Idénticos byte a byte: {b15 == b20}")
    dif = [i for i in range(10_089) if b15[i] != b20[i]]
    print(f"Bytes distintos: {len(dif):,} de 10,089")
    if 0 < len(dif) < 10_089:
        print(f"Primeras 8 diferencias en índices: {dif[:8]}")
        print(f"XOR de las diferencias (primeros 16): "
              f"{[b15[i] ^ b20[i] for i in dif[:16]]}")
    # ¿y el desplazamiento? keystream continuo: diff uniforme
    if len(dif) == 10_089:
        print("Todos los bytes difieren → cifrado de flujo con posición "
              "o datos realmente distintos")

    # --- 2. Cadenas de cifrado/compresión en el instalador -------------
    print("\n=== Cadenas de interés en el PE (0-190,859) ===")
    pe = data[:DATA_BASE]
    for pat in [rb"[Rr][Cc]4", rb"[Aa][Ee][Ss]", rb"[Bb]lowfish",
                rb"[Cc]ipher", rb"[Cc]rypt", rb"aPLib", rb"aplib",
                rb"LZMA", rb"[Bb]zip", rb"[Zz]lib", rb"[Dd]eflate",
                rb"\.pak", rb"[Pp]ack", rb"[Cc]ompress"]:
        for m in list(re.finditer(pat, pe))[:6]:
            ini = max(0, m.start() - 24)
            ctx = pe[ini:m.end() + 24]
            ctx_txt = "".join(chr(b) if 32 <= b < 127 else "." for b in ctx)
            print(f"  {pat}: @{m.start():,} …{ctx_txt}…")

    # --- 3. LZMA raw con todas las combinaciones ------------------------
    print("\n=== LZMA raw (todas las lc/lp/pb) sobre $inst\\6.tmp ===")
    blob = data[DATA_BASE + 47_155: DATA_BASE + 47_155 + 200_000]
    aciertos = 0
    for lc in range(0, 9):
        for lp in range(0, 5):
            for pb in range(0, 5):
                if lc + lp > 4:
                    continue
                try:
                    filt = [{"id": lzma.FILTER_LZMA1, "lc": lc, "lp": lp,
                             "pb": pb, "dict_size": 1 << 24}]
                    d = lzma.LZMADecompressor(format=lzma.FORMAT_RAW,
                                              filters=filt)
                    out = d.decompress(blob)
                    if len(out) > 1000:
                        print(f"  lc={lc} lp={lp} pb={pb}: {len(out):,} B "
                              f"cab={out[:24]!r}")
                        aciertos += 1
                except Exception:
                    pass
    if not aciertos:
        print("  (ninguna combinación válida)")

    # --- 4. Validación del campo CRC ------------------------------------
    print("\n=== Validación del campo CRC de la tabla $inst ===")
    png1 = data[DATA_BASE:DATA_BASE + 4_278]
    png2 = data[DATA_BASE + 4_278:DATA_BASE + 4_278 + 42_877]
    print(f"crc32(PNG#1 almacenado)   = {binascii.crc32(png1) & 0xFFFFFFFF:#010x} "
          f"(campo: 0xad723f7b)")
    print(f"crc32(PNG#2 almacenado)   = {binascii.crc32(png2) & 0xFFFFFFFF:#010x} "
          f"(campo: 0xb4d34c55)")
    for nombre in [b"$inst\\4.tmp", b"$inst\\4.tmp\x00",
                   b"4.tmp", b"MAINICON"]:
        print(f"crc32({nombre!r}) = {binascii.crc32(nombre) & 0xFFFFFFFF:#010x}")
    # buscar crc32(PNG#1) en formato LE en los metadatos
    objetivo = struct.pack("<I", binascii.crc32(png1) & 0xFFFFFFFF)
    idx = data.find(objetivo, 178_000, 200_000)
    print(f"crc32(PNG#1) LE en metadatos: {idx}")
    objetivo2 = struct.pack("<I", binascii.crc32(png2) & 0xFFFFFFFF)
    idx2 = data.find(objetivo2, 178_000, 200_000)
    print(f"crc32(PNG#2) LE en metadatos: {idx2}")

    # --- 5. ¿Y si el PNG está comprimido DENTRO del blob? ---------------
    # crc del contenido real del archivo 4.tmp si fuera el PNG sin cabecera
    # p.ej. crc32 de la IDAT descomprimida (RGBA)
    d = zlib.decompressobj()
    print("\n=== ¿Qué podría ser 0xad723f7b? ===")
    # fecha DOS (31/10/2025?) o tamaño
    v = 0xAD723F7B
    print(f"Como fecha DOS: {((v >> 21) & 0x7F) + 1980}-"
          f"{(v >> 16) & 0xF:02d}-{(v >> 11) & 0x1F:02d} "
          f"{(v >> 5) & 0x1F:02d}:{v & 0x1F:02d} (poco plausible)")
    print(f"Como tamaño: {v:,} B")
    for v2, nom in ((0xAD723F7B, "4.tmp"), (0xB4D34C55, "5.tmp"),
                    (0x9CB43F7B, "7.tmp"), (0x83265AF6, "15.tmp")):
        # probar como crc de trozos del PNG (IDAT, etc.)
        pass


if __name__ == "__main__":
    main()
