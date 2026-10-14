#!/usr/bin/env python3
"""MISIÓN IV — Fase C: extraer el payload CAB del instalador SIECONS 11.

Basado en el formato documentado por 4RAYS-by-SOLAR/sim-unpacker para
Smart Install Maker v5.04:
  - Overlay: últimos 36 bytes <8I4B> con offsets del payload.
  - El payload es un CAB al que falta la firma MSCF (4 bytes).
  - cab_size = int(strings[118]) de la lista de cadenas de configuración.

Este script reconstruye el CAB y analiza su estructura (carpetas, tipo de
compresión, archivos) sin ejecutar nada.
"""
import struct
import sys
from pathlib import Path

EXE = Path("/home/z/my-project/work/recuperacion/analisis/"
           "SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe")
SALIDA = Path("/home/z/my-project/work/siecons_extract")


def read_str(data, off):
    fin = data.find(b"\x00", off)
    if fin < 0:
        return "", len(data)
    return data[off:fin].decode("latin-1", "replace"), fin + 1


def main():
    data = EXE.read_bytes()
    n = len(data)

    # --- 1. Overlay config --------------------------------------------
    vals = struct.unpack("<8I4B", data[-36:])
    cfg = {
        "offset_strings": vals[0], "size_header": vals[2],
        "offset_header": vals[4], "payload": vals[6],
        "compression": vals[8], "installation_type": vals[9],
        "strings_count": vals[10], "magic": vals[11],
    }
    print("=== Config del overlay ===")
    for k, v in cfg.items():
        print(f"  {k}: {v} ({v:#x})")

    # --- 2. Cadenas de configuración ----------------------------------
    print(f"\n=== Cadena de configuración ({cfg['strings_count']} cadenas) ===")
    strings = []
    pos = cfg["offset_strings"]
    for i in range(cfg["strings_count"]):
        s, pos = read_str(data, pos)
        strings.append(s)
    for i, s in enumerate(strings):
        marca = ""
        if i in (0, 28, 118):
            marca = "  <<<<"
        print(f"  [{i:>3}] {s[:90]!r}{marca}")

    cab_size = int(strings[118])
    print(f"\nTamaño del CAB: {cab_size:,} (+4 de firma MSCF)")
    payload = cfg["payload"]
    print(f"Payload @ {payload:,}; disponible hasta el overlay: "
          f"{n - 36 - payload:,}")

    # --- 3. Reconstruir el CAB ----------------------------------------
    cab = b"MSCF" + data[payload:payload + cab_size]
    print(f"\nCAB reconstruido: {len(cab):,} bytes")

    # Validar cabecera CFHEADER
    (sig, r1, cbCabinet, r2, coffFiles, r3, vMinor, vMajor,
     cFolders, cFiles, flags, setID, iCabinet) = struct.unpack(
        "<4sIIIIIBBHHHHH", cab[:36])
    print(f"  sig={sig} v{vMajor}.{vMinor} folders={cFolders} "
          f"files={cFiles} flags={flags:#x} cbCabinet={cbCabinet:,} "
          f"coffFiles={coffFiles:,}")
    assert sig == b"MSCF"
    assert cbCabinet == len(cab), f"cbCabinet {cbCabinet} != {len(cab)}"

    # --- 4. Estructura de carpetas y archivos --------------------------
    tipos = {0: "SIN COMPRIMIR", 1: "MSZIP (deflate)", 2: "QUANTUM",
             3: "LZX"}
    carpetas = []
    p = 36
    for i in range(cFolders):
        coffCabStart, cCFData, typeComp, cb = struct.unpack("<IBHB", cab[p:p+8])
        extra = cab[p+8:p+8+cb]
        carpetas.append(dict(coffCabStart=coffCabStart, cCFData=cCFData,
                             typeComp=typeComp))
        print(f"  Carpeta {i}: data@{coffCabStart:,} bloques={cCFData} "
              f"comp={tipos.get(typeComp, typeComp)}")
        p += 8 + cb

    archivos = []
    p = coffFiles
    for i in range(cFiles):
        cbFile, uoffFolder, iFolder, fecha, hora, atribs = struct.unpack(
            "<IIIHHI", cab[p:p+16])
        nombre, p2 = read_str(cab, p + 16)
        archivos.append(dict(nombre=nombre, cbFile=cbFile,
                             iFolder=iFolder, uoffFolder=uoffFolder,
                             fecha=fecha, hora=hora, atribs=atribs))
        p = p2
    print(f"\n  Archivos en el CAB: {len(archivos)}")
    for a in archivos:
        print(f"    {a['nombre']:<12} {a['cbFile']:>12,} B "
              f"folder={a['iFolder']} uoff={a['uoffFolder']:,} "
              f"attr={a['atribs']:#x}")

    # --- 5. Guardar el CAB --------------------------------------------
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "data.cab").write_bytes(cab)
    print(f"\nCAB guardado en {SALIDA / 'data.cab'}")
    print("PRÓXIMO PASO: decodificar bloques CFDATA con el tipo de "
          "compresión indicado y mapear índices a rutas reales.")


if __name__ == "__main__":
    main()
