#!/usr/bin/env python3
"""MISIÓN IV — Fase C: extraer la lista de rutas reales del instalador.

Replica la lógica de sim-unpacker (4RAYS) para Smart Install Maker v5.04:
tras las 120 cadenas de configuración vienen (opcionalmente) entradas de
registro, luego la lista de archivos (ruta + 2 banderas por entrada) y
finalmente los comandos. El índice de cada ruta en la lista corresponde al
nombre numérico del archivo dentro del CAB.
"""
import struct
from pathlib import Path

EXE = Path("/home/z/my-project/work/recuperacion/analisis/"
           "SIECONS_11_64Bit_MSA_13 o Superior_2025_07_22_1603.exe")
SALIDA = Path("/home/z/my-project/work/siecons_extract")

VARS = {
    "@$&%01": "%ProgramFiles%", "@$&%04": "%InstallPath%",
    "@$&%20": "%UserName%", "@$&%21": "%Language%",
    "@$&%22": "%ComputerName%", "@$&%36": "%ProgramFiles64%",
    "@$&%02": "%WindowsDir%", "@$&%03": "%SystemDir%",
    "@$&%16": "%CommonFiles%", "@$&%05": "%TempDir%",
    "@$&%06": "%Desktop%", "@$&%08": "%ProgramsDir%",
    "@$&%09": "%StartMenu%", "@$&%11": "%Favourites%",
    "@$&%14": "%StartUp%", "@$&%34": "%Templates%",
    "@$&%26": "%AppData%", "@$&%17": "%SystemDrive%",
}


def reemplazar_vars(texto):
    for k, v in VARS.items():
        texto = texto.replace(k, v)
    return texto


def leer_str(data, off):
    fin = data.find(b"\x00", off)
    if fin < 0:
        return "", len(data)
    return data[off:fin].decode("latin-1", "replace"), fin + 1


def es_entrada_registro(data):
    pos = 0
    digit, pos = leer_str(data, pos)
    if len(digit) != 1:
        return False
    for _ in range(3):
        _, pos = leer_str(data, pos)
    d1, pos = leer_str(data, pos)
    d2, pos = leer_str(data, pos)
    d3, pos = leer_str(data, pos)
    if len(d1) != 1 and len(d2) != 1 and len(d3) != 1:
        return False
    return True


def parsear_registro(data):
    pos, res = 0, []
    while pos < len(data) and es_entrada_registro(data[pos:]):
        reg_type, pos = leer_str(data, pos)
        subkey, pos = leer_str(data, pos)
        nombre, pos = leer_str(data, pos)
        valor, pos = leer_str(data, pos)
        tipo_valor, pos = leer_str(data, pos)
        _, pos = leer_str(data, pos)
        _, pos = leer_str(data, pos)
        res.append((reg_type, subkey, nombre, valor, tipo_valor))
        if reg_type not in "0123456" or not subkey:
            break
    return res, pos


def parsear_archivos(data):
    res, pos = 0, []
    while True:
        prev = pos
        ruta, pos = leer_str(data, pos)
        flag1, pos = leer_str(data, pos)
        flag2, pos = leer_str(data, pos)
        if len(flag1) != 1 and len(flag2) != 1:
            pos = prev
            break
        if not ruta:
            pos = prev
            break
        res.append((reemplazar_vars(ruta), flag1, flag2))
    return res, pos


def main():
    data = EXE.read_bytes()
    vals = struct.unpack("<8I4B", data[-36:])
    offset_strings, strings_count = vals[0], vals[10]

    # 120 cadenas de configuración
    pos = offset_strings
    strings = []
    for _ in range(strings_count):
        s, pos = leer_str(data, pos)
        strings.append(s)
    pos += 2  # separador documentado por sim-unpacker

    print(f"Cadenas: {strings_count}; posición tras cadenas: {pos:,}")

    # entradas de registro opcionales
    registro = []
    if es_entrada_registro(data[pos:]):
        registro, fpos = parsear_registro(data[pos:])
        pos += fpos
    print(f"Entradas de registro: {len(registro)}")
    for r in registro[:12]:
        print(f"  {r}")

    # lista de archivos
    archivos, fpos = parsear_archivos(data[pos:])
    print(f"\nArchivos en la lista: {len(archivos)}")
    for i, (ruta, f1, f2) in enumerate(archivos):
        print(f"  [{i:>2}] {ruta[:78]:<78} ({f1},{f2})")

    # comandos
    pos += fpos
    print(f"\nContexto tras la lista (comandos): {data[pos:pos+200]!r}")

    # escribir mapeo índice -> ruta relativa limpia
    SALIDA.mkdir(parents=True, exist_ok=True)
    with open(SALIDA / "mapeo.txt", "w", encoding="utf-8") as f:
        for i, (ruta, _, _) in enumerate(archivos):
            # %InstallPath%\... -> ruta relativa
            rel = ruta.replace("%InstallPath%\\", "").replace("\\", "/")
            f.write(rel + "\n")
    print(f"\nMapeo escrito en {SALIDA / 'mapeo.txt'}")


if __name__ == "__main__":
    main()
