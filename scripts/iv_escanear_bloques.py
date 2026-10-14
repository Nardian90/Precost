#!/usr/bin/env python3
"""MISIÓN IV — Fase C: escáner de bloques comprimidos del instalador SIM.

Estrategia: escanear el instalador buscando flujos comprimidos con varios
métodos (raw deflate, bz2, lzma, aplib) y quedarse con los que produzcan
salidas grandes y reconocibles (PDF, Jet DB, OLE, RIFF, PE, etc.).

El objetivo es el payload documental: Manual Básico SIECONS.pdf y demás
manuales de App\\MANUAL.
"""
import bz2
import lzma
import re
import sys
import zlib
from pathlib import Path

import aplib

EXE = Path("/home/z/my-project/work/recuperacion/analisis/"
           "SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe")

MAGIAS = [
    (b"%PDF", "PDF"),
    (b"Standard Jet DB", "MDB (Jet)"),
    (b"Standard ACE DB", "ACCDB/ACCDE (ACE)"),
    (b"\xd0\xcf\x11\xe0", "OLE (doc/xls)"),
    (b"RIFF", "RIFF (avi/wav)"),
    (b"MZ", "PE (exe/dll)"),
    (b"{\\rtf", "RTF"),
    (b"<html", "HTML"),
    (b"<?xml", "XML"),
]


def clasificar(out: bytes):
    for magia, nombre in MAGIAS:
        if out[:64].startswith(magia):
            return nombre
    # búsqueda dentro de los primeros 4 KB (cabeceras previas posibles)
    for magia, nombre in MAGIAS:
        idx = out[:4096].find(magia)
        if idx >= 0 and idx < 1024:
            return f"{nombre} (+{idx})"
    return None


def probar_zlib(data, off, min_out=16384):
    try:
        d = zlib.decompressobj()
        out = d.decompress(data[off:off + 2_000_000], 4_000_000)
        if len(out) >= min_out:
            return ("zlib", out, d.eof, len(out))
    except zlib.error:
        pass
    return None


def probar_raw(data, off, min_out=16384):
    try:
        d = zlib.decompressobj(-15)
        out = d.decompress(data[off:off + 2_000_000], 4_000_000)
        if len(out) >= min_out:
            return ("raw-deflate", out, d.eof, len(out))
    except zlib.error:
        pass
    return None


def probar_bz2(data, off, min_out=16384):
    try:
        d = bz2.BZ2Decompressor()
        out = d.decompress(data[off:off + 2_000_000])
        if len(out) >= min_out:
            return ("bz2", out, d.eof, len(out))
    except Exception:
        pass
    return None


def probar_lzma(data, off, min_out=16384):
    for formato in (lzma.FORMAT_AUTO, lzma.FORMAT_ALONE, lzma.FORMAT_RAW):
        try:
            filt = [{"id": lzma.FILTER_LZMA1}] if formato == lzma.FORMAT_RAW else None
            d = lzma.LZMADecompressor(format=formato, filters=filt)
            out = d.decompress(data[off:off + 2_000_000])
            if len(out) >= min_out:
                return (f"lzma-{formato}", out, d.eof, len(out))
        except Exception:
            continue
    return None


def probar_aplib(data, off, min_out=16384):
    try:
        out = aplib.decompress(data[off:off + 300_000])
        if out and len(out) >= min_out:
            return ("aplib", out, True, len(out))
    except Exception:
        pass
    return None


def main():
    data = EXE.read_bytes()
    n = len(data)
    print(f"Escaneando {n:,} bytes con 5 métodos…")

    hallazgos = []
    # Puntos de partida: cada offset donde el byte podría iniciar un flujo.
    # Para zlib/bz2/lzma usamos firmas probables; para raw/aplib barrido denso
    # por bloques grandes de alta entropía.
    candidatos = set()
    # firmas zlib
    for m in re.finditer(rb"\x78[\x01\x5e\x9c\xda]", data):
        candidatos.add(("zlib", m.start()))
    # firmas bz2
    for m in re.finditer(rb"BZh[1-9]\x31\x41\x59\x26\x53\x59", data):
        candidatos.add(("bz2", m.start()))
    # lzma alone típico: props 5d/6d/00 + dict
    for m in re.finditer(rb"[\x00\x5d\x5e\x5f\x60\x61\x62\x63\x64\x66\x67\x68\x69\x6a\x6b\x6c\x6d\x6e\x6f\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79\x7a]\x00{2}", data):
        candidatos.add(("lzma", m.start()))

    print(f"Candidatos con firma: {len(candidatos)}")
    vistos = set()
    for tipo, off in sorted(candidatos, key=lambda x: x[1]):
        if off in vistos:
            continue
        if tipo == "zlib":
            r = probar_zlib(data, off)
        elif tipo == "bz2":
            r = probar_bz2(data, off)
        else:
            r = probar_lzma(data, off)
        if r:
            metodo, out, eof, largo = r
            clase = clasificar(out)
            if clase or largo > 200_000:
                print(f"[{metodo}] @{off:,} -> {largo:,} B eof={eof} "
                      f"clase={clase} cabecera={out[:24]!r}")
                hallazgos.append((off, metodo, largo, clase, out[:64]))
            vistos.add(off)

    # raw-deflate y aplib: barrido por zonas de alta entropía (>4 KB libres
    # de texto) para limitar el coste.
    print("\nBarrido raw-deflate/aplib en zonas de alta entropía…")
    paso = 1
    zona = []
    entropia_alta = bytearray(n)
    # marca zonas de texto/estructura conocida para saltarlas
    for m in re.finditer(rb"[\x20-\x7e]{32,}", data):
        entropia_alta[m.start():m.end()] = b"\x00" * len(m.group())
    for off in range(190_000, n, paso):
        if entropia_alta[off]:
            continue
        r = probar_raw(data, off, 32768)
        if r and r[3] > 65536:
            clase = clasificar(r[1])
            print(f"[raw-deflate] @{off:,} -> {r[3]:,} B eof={r[2]} clase={clase} "
                  f"cab={r[1][:24]!r}")
            hallazgos.append((off, "raw-deflate", r[3], clase, r[1][:64]))

    print(f"\nTotal hallazgos: {len(hallazgos)}")
    for off, metodo, largo, clase, cab in sorted(hallazgos)[:50]:
        print(f"  @{off:>10,}  {metodo:<12} {largo:>10,} B  {clase}")


if __name__ == "__main__":
    main()
