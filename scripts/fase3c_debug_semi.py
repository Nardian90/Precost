#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Depuración de F8 (precio de semielaborados) — exploración, no entregable final."""
import logging
import os
from collections import defaultdict

logging.getLogger("access_parser").setLevel(logging.CRITICAL)
from access_parser import AccessParser

FUENTE = "/home/z/my-project/work/recuperacion/analisis/PRECODI"
db = AccessParser(os.path.join(FUENTE, "Codigo (PRECODI)/codigo.mdb"))
NOMBRES = ["Nomenclador de Materiales", "Nomenclador de Mano de Obra", "Nomenclador de Equipos",
           "Nomenclador de Semielaborados", "Norma Semi Material", "Norma Semi RHumanos",
           "Norma Semi Equipos"]
T = {n: db.parse_table(n) for n in NOMBRES}


def rows(t):
    return [dict(zip(T[t], v)) for v in zip(*T[t].values())]


def f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


pmn = {
    "mat": {str(r["CodMat"]): f(r["PMN"]) for r in rows("Nomenclador de Materiales")},
    "rh": {str(r["CodRHum"]): f(r["PMN"]) for r in rows("Nomenclador de Mano de Obra")},
    "eq": {str(r["CodEquipo"]): f(r["PMN"]) for r in rows("Nomenclador de Equipos")},
}
pmn_se = {str(r["CodSElab"]): f(r["PMN"]) for r in rows("Nomenclador de Semielaborados")}

# descomposición por semi, por separado (sin dobles conteos)
comp = defaultdict(lambda: {"mat": 0.0, "rh": 0.0, "eq": 0.0, "inc": False,
                            "n_mat": 0, "n_rh": 0, "n_eq": 0})
for r in rows("Norma Semi Material"):
    p = pmn["mat"].get(str(r["CodMat"]))
    d = comp[str(r["CodSemi"])]
    if p is None:
        d["inc"] = True
    else:
        d["mat"] += (f(r["CantMatSE"]) or 0) * p
    d["n_mat"] += 1
for r in rows("Norma Semi RHumanos"):
    p = pmn["rh"].get(str(r["CodRHum"]))
    d = comp[str(r["CodSemi"])]
    if p is None:
        d["inc"] = True
    else:
        d["rh"] += (f(r["CantRHumSE"]) or 0) * p
    d["n_rh"] += 1
for r in rows("Norma Semi Equipos"):
    p = pmn["eq"].get(str(r["CodEquipo"]))
    d = comp[str(r["CodSemi"])]
    if p is None:
        d["inc"] = True
    else:
        d["eq"] += (f(r["CantEquipoSE"]) or 0) * p
    d["n_eq"] += 1

res = defaultdict(int)
ejemplos = defaultdict(list)
for cs, d in comp.items():
    obj = pmn_se.get(cs)
    if d["inc"] or obj is None:
        continue
    total = d["mat"] + d["rh"] + d["eq"]
    solo_mat = d["mat"]
    if abs(total - obj) < 0.01:
        res["mat+rh+eq"] += 1
    elif abs(solo_mat - obj) < 0.01:
        res["solo_mat"] += 1
    elif abs(total - obj) < 1.0:
        res["mat+rh+eq (cerca)"] += 1
        if len(ejemplos["cerca"]) < 5:
            ejemplos["cerca"].append((cs, round(total, 2), obj, dict(d)))
    else:
        res["ninguna"] += 1
        if len(ejemplos["lejos"]) < 5:
            ejemplos["lejos"].append((cs, round(total, 2), obj, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in d.items()}))

print("Resultados F8:", dict(res))
print("\nEjemplos CERCA (mat+rh+eq ± 1.0):")
for e in ejemplos["cerca"]:
    print("  ", e)
print("\nEjemplos LEJOS (ninguna hipótesis):")
for e in ejemplos["lejos"]:
    print("  ", e)

# ¿los semis sin descomposición?
sin_desc = [cs for cs in pmn_se if cs not in comp]
print(f"\nSemielaborados SIN descomposición: {len(sin_desc)}/{len(pmn_se)}")
con_desc = [cs for cs in pmn_se if cs in comp]
print(f"Con descomposición: {len(con_desc)}")
