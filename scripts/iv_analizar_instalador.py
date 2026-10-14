#!/usr/bin/env python3
"""MISIÓN IV — Fase C: análisis del instalador SIECONS 11 (Smart Install Maker v5.04).

Objetivo: localizar y extraer el manual del fabricante
(SIECONS 11\\App\\MANUAL\\Manual SIECONS\\...) y cualquier otro activo
documental embebido, sin ejecutar el instalador (entorno sin Windows).

Estrategias:
  1. Detectar CAB embebido (firma MSCF con cabecera válida).
  2. Localizar la tabla de archivos en texto claro (rutas del payload).
  3. Identificar el formato de compresión de los blobs de datos.

Uso: python3 iv_analizar_instalador.py [--extraer DIR]
"""
import re
import struct
import sys
import zlib
from pathlib import Path

EXE = Path("/home/z/my-project/work/recuperacion/analisis/"
           "SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe")


def validar_cab(data: bytes, off: int):
    """Devuelve dict con campos del CFHEADER si es válido, None si no."""
    try:
        sig, r1, cbCab, r2, coffFiles, r3 = struct.unpack(
            "<4sIIIII", data[off:off + 24])
        vmin, vmaj, cFolders, cFiles, flags, setID, iCab = struct.unpack(
            "<BBHHHHH", data[off + 24:off + 36])
    except struct.error:
        return None
    if sig != b"MSCF" or r1 != 0 or r2 != 0 or r3 != 0:
        return None
    if vmin != 3 or vmaj != 1 or iCab != 0:
        return None
    if cbCab <= 0 or cbCab > len(data) - off:
        return None
    return dict(offset=off, cbCabinet=cbCab, coffFiles=coffFiles,
                cFolders=cFolders, cFiles=cFiles, flags=flags, setID=setID)


def listar_cab(data: bytes, cab):
    """Extrae la lista de archivos de un CAB embebido (CFFOLDER/CFFILE)."""
    off = cab["offset"]
    cffolder = off + 36
    carpetas = []
    for i in range(cab["cFolders"]):
        try:
            coffCabStart, cCFData, cFolders_typ, cb = struct.unpack(
                "<I H B H", data[cffolder:cffolder + 9])
        except struct.error:
            break
        carpetas.append(dict(coffCabStart=off + coffCabStart,
                             typeComp=cFolders_typ))
        cffolder += 8 + cb  # entrada variable: 8 fijos + szCAB 1+ cb
    archivos = []
    p = off + cab["coffFiles"]
    for i in range(cab["cFiles"]):
        try:
            cbFile, uoffFolder, iFolder, date, time, attribs = struct.unpack(
                "<IIIHHi", data[p:p + 16])
        except struct.error:
            break
        q = data.find(b"\x00", p + 16)
        if q < 0:
            break
        nombre = data[p + 16:q].decode("latin-1", "replace")
        archivos.append(dict(nombre=nombre, cbFile=cbFile,
                             iFolder=iFolder, uoffFolder=uoffFolder,
                             attribs=attribs))
        p = q + 1
    return carpetas, archivos


def main():
    data = EXE.read_bytes()
    print(f"Instalador: {EXE.name}")
    print(f"Tamaño: {len(data):,} bytes\n")

    # --- 1. CABs válidos ---------------------------------------------
    cabs = []
    for m in re.finditer(rb"MSCF", data):
        c = validar_cab(data, m.start())
        if c:
            cabs.append(c)
    print(f"[1] CABs válidos embebidos: {len(cabs)}")
    for c in cabs:
        print(f"    offset={c['offset']:,} cbCabinet={c['cbCabinet']:,} "
              f"folders={c['cFolders']} files={c['cFiles']} flags={c['flags']}")
        carpetas, archivos = listar_cab(data, c)
        for cf in carpetas:
            tipos = {0: "sin comprimir", 1: "MSZIP", 2: "Quantum", 3: "LZX"}
            print(f"    carpeta: data@{cf['coffCabStart']:,} "
                  f"comp={tipos.get(cf['typeComp'], cf['typeComp'])}")
        for a in archivos[:60]:
            print(f"      {a['nombre']}  ({a['cbFile']:,} B, "
                  f"folder={a['iFolder']}, attr={a['attribs']:#x})")
        if len(archivos) > 60:
            print(f"      ... y {len(archivos) - 60} más")

    # --- 2. Tabla de archivos SIM en texto claro ---------------------
    print("\n[2] Rutas del payload en texto claro (muestra):")
    # Las rutas internas del instalador SIECONS ya mapeadas en Fase II
    rutas = [r.decode("latin-1") for r in re.findall(
        rb"(?:App|BD|Manuales|Manual)[A-Za-z0-9 _\.\-\\\\]{3,60}", data)]
    vistas = []
    for r in rutas:
        if r not in vistas:
            vistas.append(r)
    for r in vistas[:40]:
        print("   ", r)
    print(f"    total rutas únicas: {len(vistas)}")

    # --- 3. Blob de datos: sondeo de compresión ----------------------
    print("\n[3] Sondeo de compresión alrededor del área de datos:")
    # Zona típica tras los recursos PE: buscar bloques de alta entropía
    zona = data[138960:139200]
    print("    hex@138960:", zona[:48].hex())
    # Probar zlib/deflate en offsets alineados dentro de la zona candidata
    hits = 0
    for off in range(0, min(len(data), 200000), 1):
        pass  # (el análisis fino se hace en extraer, aquí solo sondeo)
    # ¿Flujos zlib con cabecera estándar?
    zm = [m.start() for m in re.finditer(rb"\x78[\x01\x9c\xda\x5e]", data)]
    print(f"    candidatos zlib (78 xx): {len(zm)}")
    validos = []
    for o in zm[:5000]:
        try:
            d = zlib.decompressobj()
            out = d.decompress(data[o:o + 200000])
            if len(out) > 4096:
                validos.append((o, len(out)))
        except zlib.error:
            continue
    print(f"    flujos zlib válidos >4KB (muestra 5000): {len(validos)}")
    for o, n in validos[:10]:
        print(f"      @{o:,} -> {n:,} B descomprimidos")


if __name__ == "__main__":
    main()
