#!/usr/bin/env python3
"""MISIÓN IV — Fase C: generar mapeo índice CAB -> ruta real (39 archivos).

La lista de archivos del instalador empieza en el offset 183,430
(PLANTILLA 2021.xls) y contiene exactamente 39 tripletas (ruta, flag1,
flag2) que corresponden a los archivos numerados 0-38 del CAB.
"""
from pathlib import Path

EXE = Path("/home/z/my-project/work/recuperacion/analisis/"
           "SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe")
SALIDA = Path("/home/z/my-project/work/siecons_extract")
INICIO_LISTA = 183_430


def main():
    data = EXE.read_bytes()
    pos = INICIO_LISTA
    entradas = []
    while pos < 186_600:
        f = data.find(b"\x00", pos)
        if f < 0:
            break
        entradas.append(data[pos:f].decode("latin-1", "replace"))
        pos = f + 1

    archivos = []
    i = 0
    while i + 2 < len(entradas):
        ruta, f1, f2 = entradas[i], entradas[i + 1], entradas[i + 2]
        if ruta.startswith("@") and len(f1) == 1 and len(f2) == 1:
            archivos.append(ruta)
            i += 3
        else:
            break

    print(f"Archivos mapeados: {len(archivos)}")
    with open(SALIDA / "mapeo.txt", "w", encoding="utf-8") as f:
        for ruta in archivos:
            rel = ruta.replace("@$&%04\\", "").replace("\\", "/")
            f.write(rel + "\n")
    for i, ruta in enumerate(archivos):
        print(f"  [{i:>2}] {ruta.replace('@$&%04', 'C:/SIECONS 11')}")


if __name__ == "__main__":
    main()
