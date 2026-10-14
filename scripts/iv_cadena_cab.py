#!/usr/bin/env python3
"""MISIÓN IV — Fase C: extraer la cadena completa de CABs del instalador.

El payload de Smart Install Maker v5.04 es una cadena de CABs (flags
NEXT_CABINET) donde cada CAB pierde los 4 bytes de firma MSCF.
Este script recorre la cadena, valida cada CAB y lista su contenido.
"""
import struct
import sys
from pathlib import Path

EXE = Path("/home/z/my-project/work/recuperacion/analisis/"
           "SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe")
SALIDA = Path("/home/z/my-project/work/siecons_extract")

TIPOS_COMP = {0: "SIN COMPRIMIR", 1: "MSZIP (deflate)", 2: "QUANTUM", 3: "LZX"}


def read_str(buf, off):
    fin = buf.find(b"\x00", off)
    if fin < 0:
        return "", len(buf)
    return buf[off:fin].decode("latin-1", "replace"), fin + 1


def parsear_cab(cab: bytes, etiqueta: str):
    """Parsea un CAB completo (con firma). Devuelve dict o None."""
    if len(cab) < 36:
        print(f"  [{etiqueta}] demasiado pequeño")
        return None
    (sig, r1, cbCabinet, r2, coffFiles, r3, vMinor, vMajor,
     cFolders, cFiles, flags, setID, iCabinet) = struct.unpack(
        "<4sIIIIIBBHHHHH", cab[:36])
    if sig != b"MSCF":
        print(f"  [{etiqueta}] firma inválida: {sig!r}")
        return None
    print(f"  [{etiqueta}] v{vMajor}.{vMinor} cbCabinet={cbCabinet:,} "
          f"folders={cFolders} files={cFiles} flags={flags:#x} "
          f"setID={setID} iCab={iCabinet} coffFiles={coffFiles}")
    if r1 or r2 or r3 or vMinor != 3 or vMajor != 1:
        print(f"  [{etiqueta}] cabecera inesperada: r={r1},{r2},{r3} "
              f"v={vMajor}.{vMinor}")
    p = 36
    reserve = b""
    if flags & 0x0004:  # cfheadRESERVE_PRESENT
        cbCFHeader, cbCFFolder, cbCFData = struct.unpack("<HBB", cab[p:p+4])
        p += 4 + cbCFHeader
    prev_cab, prev_disk, next_cab, disk_next = "", "", "", ""
    if flags & 0x0001:  # cfheadPREV_CABINET: szCabinetPrev + szDiskPrev
        prev_cab, p = read_str(cab, p)
        prev_disk, p = read_str(cab, p)
    if flags & 0x0002:  # cfheadNEXT_CABINET: szCabinetNext + szDiskNext
        next_cab, p = read_str(cab, p)
        disk_next, p = read_str(cab, p)
    if next_cab:
        print(f"      prev: {prev_cab!r}/{prev_disk!r} "
              f"next: {next_cab!r}/{disk_next!r}")

    carpetas = []
    for i in range(cFolders):
        coffCabStart, cCFData, typeComp = struct.unpack("<IHH", cab[p:p+8])
        carpetas.append(dict(coffCabStart=coffCabStart, cCFData=cCFData,
                             typeComp=typeComp))
        print(f"      carpeta {i}: data@{coffCabStart:,} "
              f"bloques={cCFData} comp={typeComp:#06x} "
              f"({TIPOS_COMP.get(typeComp & 0xF, '?')})")
        p += 8

    archivos = []
    p = coffFiles
    for i in range(cFiles):
        if p + 18 > len(cab):
            print(f"      [!] tabla de archivos corta en {i}")
            break
        # CFFILE NO ESTÁNDAR de SIM: cbFile u32, uoffFolder u32,
        # iFolder u16 (no u32), date u16, time u16, attribs u16, nombre\0
        cbFile, uoffFolder, iFolder, fecha, hora, atribs = struct.unpack(
            "<IIHHHH", cab[p:p+16])
        nombre, p2 = read_str(cab, p + 16)
        archivos.append(dict(nombre=nombre, cbFile=cbFile, iFolder=iFolder,
                             uoffFolder=uoffFolder, fecha=fecha,
                             hora=hora, atribs=atribs))
        p = p2
    return dict(cbCabinet=cbCabinet, carpetas=carpetas, archivos=archivos,
                flags=flags, next_cab=next_cab, setID=setID,
                iCabinet=iCabinet)


def main():
    data = EXE.read_bytes()
    n = len(data)
    vals = struct.unpack("<8I4B", data[-36:])
    payload = vals[6]

    print(f"Payload inicial @ {payload:,}")
    print(f"Overlay config: {data[-36:].hex()}")

    offset = payload
    numero = 0
    total_archivos = 0
    while offset < n - 36:
        numero += 1
        print(f"\n=== CAB #{numero} @ {offset:,} ===")
        # ¿la firma MSCF está presente o hay que reponerla?
        trozo = data[offset:offset + 40]
        if trozo[:4] == b"MSCF":
            cab = trozo
            completa = data[offset:]
        else:
            # sin firma: reponerla
            completa = b"MSCF" + data[offset:]
        cab = completa
        info = parsear_cab(cab[:200_000], f"#{numero}")
        if info is None:
            print("  Fin de la cadena (no es CAB válido)")
            break
        # guardar el CAB completo para análisis
        SALIDA.mkdir(parents=True, exist_ok=True)
        nombre_cab = SALIDA / f"cab_{numero:02d}.cab"
        nombre_cab.write_bytes(cab[:info["cbCabinet"]])
        total_archivos += len(info["archivos"])
        for a in info["archivos"]:
            print(f"      archivo {a['nombre']:<6} {a['cbFile']:>12,} B "
                  f"folder={a['iFolder']} uoff={a['uoffFolder']:,}")
        offset += info["cbCabinet"] - 4  # el siguiente CAB también sin firma
        if not (info["flags"] & 0x0002):
            print("  (sin continuación: fin de la cadena)")
            break

    print(f"\nTotal CABs: {numero}, archivos: {total_archivos}")
    print(f"CABs guardados en {SALIDA}/")


if __name__ == "__main__":
    main()
