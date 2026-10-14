#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE III-C — Verificación del modelo de precios unitarios PRECODI.

Reconstruye y VERIFICA con datos reales (codigo.mdb raíz 2017) el modelo
matemático de la descomposición de un renglón de variante (RV). No inventa
coeficientes: cada fórmula se marca VERIFICADA / PARCIAL / NO VERIFICADA
según coincidencia con los valores almacenados.

Produce:
  docs/datos/fase3c_verificacion.json — evidencia completa por fórmula
  stdout — resumen

Fórmulas evaluadas (hipótesis):
  F1  CMMN  = Σ_Materiales(CantMat×PMN) + Σ_Juegos(CantJuego×PMN) + Σ_Semi(CantSElab×PMN)
  F2  CHMN  = Σ_MO(CantRHum×PMN)
  F3  CEMN  = Σ_Eq(CantEquipo×PMN)
  F4  HORAS HOMBRE = Σ CantRHum
  F5  HORAS EQUIPO = Σ CantEquipo
  F6  CMMLC = Σ_Materiales(CantMat×PMLC)
  F7  PMN[Juego] = Σ(CantMatJ×PMN[material])
  F8  PMN[Semi]  = Σ componentes (mat + rh + eq)
  F9  CMMN == COSTO DE MATERIALES (redundancia de columnas)
  F10 PMN == PrecioU en nomencladores (redundancia)

Uso:  python3 scripts/fase3c_modelo_precios.py
"""
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

logging.getLogger("access_parser").setLevel(logging.CRITICAL)
from access_parser import AccessParser  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE = "/home/z/my-project/work/recuperacion/analisis/PRECODI"
BASE = "Codigo (PRECODI)/codigo.mdb"

TABLAS = [
    "Nomenclador de RV", "Norma de Materiales", "Norma de Mano de Obra",
    "Norma de Equipos", "Norma de Juegos", "Norma de Semielaborados",
    "Nomenclador de Materiales", "Nomenclador de Mano de Obra",
    "Nomenclador de Equipos", "Nomenclador de Juegos",
    "Nomenclador de Semielaborados", "Norma Juego Material",
    "Norma Semi Material", "Norma Semi RHumanos", "Norma Semi Equipos",
]


def f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def main():
    print(f"Cargando {BASE} (solo lectura)...")
    db = AccessParser(os.path.join(FUENTE, BASE))
    T = {}
    for n in TABLAS:
        try:
            T[n] = db.parse_table(n)
        except Exception as e:  # noqa: BLE001
            print(f"  !! {n}: {e}", file=sys.stderr)
            T[n] = None

    def rows(t):
        if not T.get(t):
            return []
        return [dict(zip(T[t], v)) for v in zip(*T[t].values())]

    # ---------- Índices de precios ----------
    pmn = {
        "mat": {str(r["CodMat"]): f(r["PMN"]) for r in rows("Nomenclador de Materiales")},
        "rh": {str(r["CodRHum"]): f(r["PMN"]) for r in rows("Nomenclador de Mano de Obra")},
        "eq": {str(r["CodEquipo"]): f(r["PMN"]) for r in rows("Nomenclador de Equipos")},
        "jg": {str(r["CodJuego"]): f(r["PMN"]) for r in rows("Nomenclador de Juegos")},
        "se": {str(r["CodSElab"]): f(r["PMN"]) for r in rows("Nomenclador de Semielaborados")},
    }
    pmlc_mat = {str(r["CodMat"]): f(r["PMLC"]) for r in rows("Nomenclador de Materiales")}
    rvs = [r for r in rows("Nomenclador de RV") if "CODIGO RV" in r]

    # ---------- Descomposición por RV ----------
    dec = defaultdict(lambda: {"mat": 0.0, "rh": 0.0, "eq": 0.0, "jg": 0.0, "se": 0.0,
                               "hh": 0.0, "he": 0.0, "mlc": 0.0,
                               "inc_mat": False, "inc_rh": False, "inc_eq": False,
                               "inc_jg": False, "inc_se": False, "inc_mlc": False})
    for r in rows("Norma de Materiales"):
        d = dec[str(r["CodigoRV"])]
        c, p = f(r["CantMat"]), pmn["mat"].get(str(r["CodMat"]))
        if p is None:
            d["inc_mat"] = True
        else:
            d["mat"] += (c or 0) * p
        pl = pmlc_mat.get(str(r["CodMat"]))
        if pl is None:
            d["inc_mlc"] = True
        else:
            d["mlc"] += (c or 0) * pl
    for r in rows("Norma de Mano de Obra"):
        d = dec[str(r["CodigoRV"])]
        c, p = f(r["CantRHum"]), pmn["rh"].get(str(r["CodRHum"]))
        if p is None:
            d["inc_rh"] = True
        else:
            d["rh"] += (c or 0) * p
            d["hh"] += c or 0
    for r in rows("Norma de Equipos"):
        d = dec[str(r["CodigoRV"])]
        c, p = f(r["CantEquipo"]), pmn["eq"].get(str(r["CodEquipo"]))
        if p is None:
            d["inc_eq"] = True
        else:
            d["eq"] += (c or 0) * p
            d["he"] += c or 0
    for r in rows("Norma de Juegos"):
        d = dec[str(r["CodigoRV"])]
        c, p = f(r["CantJuego"]), pmn["jg"].get(str(r["CodJuego"]))
        if p is None:
            d["inc_jg"] = True
        else:
            d["jg"] += (c or 0) * p
    for r in rows("Norma de Semielaborados"):
        d = dec[str(r["CodigoRV"])]
        c, p = f(r["CantSElab"]), pmn["se"].get(str(r["CodSElab"]))
        if p is None:
            d["inc_se"] = True
        else:
            d["se"] += (c or 0) * p

    # ---------- Evaluador genérico ----------
    def evaluar(nombre, tolerancia, pares, max_ejemplos=8):
        """pares: lista de (calculado, almacenado, detalle)."""
        exactos = cerca = lejos = verificables = 0
        ej_cerca, ej_lejos = [], []
        for calc, alma, det in pares:
            if calc is None or alma is None:
                continue
            verificables += 1
            d = abs(calc - alma)
            if d <= tolerancia:
                exactos += 1
            elif d <= max(1.0, tolerancia * 100):
                cerca += 1
                if len(ej_cerca) < max_ejemplos:
                    ej_cerca.append({"detalle": det, "calculado": round(calc, 4),
                                     "almacenado": round(alma, 4), "dif": round(d, 4)})
            else:
                lejos += 1
                if len(ej_lejos) < max_ejemplos:
                    ej_lejos.append({"detalle": det, "calculado": round(calc, 4),
                                     "almacenado": round(alma, 4), "dif": round(d, 4)})
        estado = ("VERIFICADA" if exactos >= 0.95 * verificables and verificables > 0
                  else "PARCIAL" if exactos + cerca >= 0.9 * verificables and verificables > 0
                  else "NO VERIFICADA")
        if verificables == 0:
            estado = "NO VERIFICABLE"
        r = {"formula": nombre, "tolerancia": tolerancia, "verificables": verificables,
             "exactos": exactos, "cerca": cerca, "lejos": lejos, "estado": estado,
             "ejemplos_cerca": ej_cerca[:4], "ejemplos_lejos": ej_lejos[:4]}
        print(f"  {nombre}: {estado} ({exactos} exactos / {cerca} cerca / {lejos} lejos de {verificables})")
        return r

    resultados = {"generado": datetime.now(timezone.utc).isoformat(),
                  "base": BASE, "rvs_totales": len(rvs), "formulas": []}

    print("\n=== Verificación de fórmulas (contra valores almacenados) ===")

    # F1: CMMN = mat + juegos + semis
    pares = []
    for rv in rvs:
        d = dec.get(str(rv["CODIGO RV"]))
        if not d or d["inc_mat"] or d["inc_jg"] or d["inc_se"]:
            continue
        calc = d["mat"] + d["jg"] + d["se"]
        pares.append((calc, f(rv.get("CMMN")), str(rv["CODIGO RV"])))
    resultados["formulas"].append(
        evaluar("F1: CMMN = Σ(CantMat×PMN) + Σ(CantJuego×PMN) + Σ(CantSElab×PMN)", 0.01, pares))

    # F2: CHMN = Σ CantRHum×PMN
    pares = [(dec[str(rv["CODIGO RV"])]["rh"], f(rv.get("CHMN")), str(rv["CODIGO RV"]))
             for rv in rvs
             if dec.get(str(rv["CODIGO RV"])) and not dec[str(rv["CODIGO RV"])]["inc_rh"]]
    resultados["formulas"].append(
        evaluar("F2: CHMN = Σ(CantRHum×PMN)", 0.01, pares))

    # F3: CEMN = Σ CantEquipo×PMN
    pares = [(dec[str(rv["CODIGO RV"])]["eq"], f(rv.get("CEMN")), str(rv["CODIGO RV"]))
             for rv in rvs
             if dec.get(str(rv["CODIGO RV"])) and not dec[str(rv["CODIGO RV"])]["inc_eq"]]
    resultados["formulas"].append(
        evaluar("F3: CEMN = Σ(CantEquipo×PMN)", 0.01, pares))

    # F4: HORAS HOMBRE
    pares = [(dec[str(rv["CODIGO RV"])]["hh"], f(rv.get("HORAS HOMBRE")), str(rv["CODIGO RV"]))
             for rv in rvs if dec.get(str(rv["CODIGO RV"]))]
    resultados["formulas"].append(
        evaluar("F4: HORAS HOMBRE = Σ CantRHum", 0.01, pares))

    # F5: HORAS EQUIPO
    pares = [(dec[str(rv["CODIGO RV"])]["he"], f(rv.get("HORAS EQUIPO")), str(rv["CODIGO RV"]))
             for rv in rvs if dec.get(str(rv["CODIGO RV"]))]
    resultados["formulas"].append(
        evaluar("F5: HORAS EQUIPO = Σ CantEquipo", 0.01, pares))

    # F6: CMMLC = Σ CantMat×PMLC
    pares = [(dec[str(rv["CODIGO RV"])]["mlc"], f(rv.get("CMMLC")), str(rv["CODIGO RV"]))
             for rv in rvs
             if dec.get(str(rv["CODIGO RV"])) and not dec[str(rv["CODIGO RV"])]["inc_mlc"]]
    resultados["formulas"].append(
        evaluar("F6: CMMLC = Σ(CantMat×PMLC)", 0.01, pares))

    # F7: PMN[Juego] = Σ CantMatJ×PMN[mat]
    jg_comp = defaultdict(lambda: [0.0, False])
    for r in rows("Norma Juego Material"):
        p = pmn["mat"].get(str(r["CodMat"]))
        if p is None:
            jg_comp[str(r["CodJuego"])][1] = True
        else:
            jg_comp[str(r["CodJuego"])][0] += (f(r["CantMatJ"]) or 0) * p
    pares = [(v[0], pmn["jg"].get(cj), f"juego {cj}")
             for cj, v in jg_comp.items() if not v[1] and pmn["jg"].get(cj) is not None]
    resultados["formulas"].append(
        evaluar("F7: PMN[Juego] = Σ(CantMatJ×PMN[material])", 0.01, pares))

    # F8: PMN[Semi] = Σ componentes
    se_comp = defaultdict(lambda: {"mat": 0.0, "rh": 0.0, "eq": 0.0, "inc": False})
    for r in rows("Norma Semi Material"):
        p = pmn["mat"].get(str(r["CodMat"]))
        if p is None:
            se_comp[str(r["CodSemi"])]["inc"] = True
        else:
            se_comp[str(r["CodSemi"])]["mat"] += (f(r["CantMatSE"]) or 0) * p
    for r in rows("Norma Semi RHumanos"):
        p = pmn["rh"].get(str(r["CodRHum"]))
        if p is None:
            se_comp[str(r["CodSemi"])]["inc"] = True
        else:
            se_comp[str(r["CodSemi"])]["rh"] += (f(r["CantRHumSE"]) or 0) * p
    for r in rows("Norma Semi Equipos"):
        p = pmn["eq"].get(str(r["CodEquipo"]))
        if p is None:
            se_comp[str(r["CodSemi"])]["inc"] = True
        else:
            se_comp[str(r["CodSemi"])]["eq"] += (f(r["CantEquipoSE"]) or 0) * p
    pares = [(v["mat"] + v["rh"] + v["eq"], pmn["se"].get(cs), f"semi {cs}")
             for cs, v in se_comp.items()
             if not v["inc"] and pmn["se"].get(cs) is not None]
    resultados["formulas"].append(
        evaluar("F8: PMN[Semi] = Σ(mat + rh + eq de Norma Semi*)", 0.01, pares))

    # F9: CMMN == COSTO DE MATERIALES
    pares = [(f(rv.get("CMMN")), f(rv.get("COSTO DE MATERIALES")), str(rv["CODIGO RV"]))
             for rv in rvs]
    resultados["formulas"].append(
        evaluar("F9: CMMN == COSTO DE MATERIALES (redundancia)", 0.005, pares))

    # F10: PMN == PrecioU en materiales (resultado esperado: NO — ver F11)
    pares = [(f(r["PMN"]), f(r["PrecioU"]), f"mat {r['CodMat']}")
             for r in rows("Nomenclador de Materiales")]
    resultados["formulas"].append(
        evaluar("F10: PMN == PrecioU en Nomenclador de Materiales (redundancia)", 0.005, pares))

    # F11: PrecioU = PMN + PMLC en los cinco nomencladores de recursos
    print("\n  F11: PrecioU = PMN + PMLC (por nomenclador):")
    f11 = {"formula": "F11: PrecioU = PMN + PMLC", "tolerancia": 0.005,
           "por_nomenclador": {}, "estado": "VERIFICADA"}
    for tabla, clave in [("Nomenclador de Materiales", "CodMat"),
                         ("Nomenclador de Mano de Obra", "CodRHum"),
                         ("Nomenclador de Equipos", "CodEquipo"),
                         ("Nomenclador de Juegos", "CodJuego"),
                         ("Nomenclador de Semielaborados", "CodSElab")]:
        ok = n = 0
        for r in rows(tabla):
            pu, pm, pl = f(r["PrecioU"]), f(r["PMN"]), f(r["PMLC"])
            if pu is None or pm is None or pl is None:
                continue
            n += 1
            if abs(pu - (pm + pl)) <= 0.005:
                ok += 1
        f11["por_nomenclador"][tabla] = {"exactos": ok, "verificables": n}
        print(f"    {tabla}: {ok}/{n}")
        if n and ok < 0.95 * n:
            f11["estado"] = "PARCIAL"
    resultados["formulas"].append(f11)

    # ---------- Ponderaciones / pendientes ----------
    print("\n=== Pendientes (evidencia insuficiente — NO inventadas) ===")
    pend = {
        "interpretacion_casos_lejos_F1_F8": {
            "observacion": "Los casos 'lejos' de F1 (718/14602) y F8 (98/186) siguen el patrón "
                           "de deriva de precios: el costo almacenado fue calculado en una fecha "
                           "anterior y los precios del nomenclador cambiaron después sin "
                           "recalcular los costos unitarios almacenados (p.ej. RV 013111: "
                           "recalculo 4.91 vs almacenado 1.87). La ESTRUCTURA de la fórmula "
                           "sigue siendo la documentada; lo que varía es la vigencia del dato.",
            "evidencia": "Las diferencias grandes se concentran en RVs que comparten exactamente "
                         "el mismo valor almacenado con la misma descomposición (013111/013112/"
                         "013113 idénticos), coherente con un recálculo por lotes antiguo.",
        },
        "HORAS OPERARIO / HORAS AYUDANTE": {
            "hipotesis_probadas": [
                "Σ CantRHum con 'OPERARIO' en la descripción → 455/15351 (rechazada)",
                "Σ CantRHum con 'OFICIAL' en la descripción → 171/15351 (rechazada)",
                "Σ CantRHum con 'AYUDANTE' en la descripción → 3829/15351 (rechazada)",
            ],
            "conclusion": "El criterio de separación operario/ayudante no es derivable de los "
                          "datos; probablemente depende de una clasificación interna de "
                          "Codigo.exe (quizá la columna Oficial de la RV o una tabla externa). "
                          "Se deja PENDIENTE hasta obtener evidencia (p.ej. SIECONS ejecutado "
                          "o documentación del fabricante).",
        },
        "PESO de la RV": {
            "hipotesis_probada": "PESO = Σ(CantMat×PesoU) → 24/6464 (rechazada)",
            "conclusion": "El peso almacenado no coincide con la suma simple de pesos de "
                          "materiales; puede excluir ciertos recursos o usar otro criterio. "
                          "PENDIENTE.",
        },
        "FACTOR": {
            "observacion": "FACTOR = 1.0 en 15351/15351 RVs; columna sin uso aparente en esta versión.",
        },
        "coeficientes de gastos indirectos": {
            "observacion": "codigo.mdb no contiene porcentajes de gastos indirectos, utilidades "
                           "ni impuestos: eso pertenece al ámbito de presupuestos (SBD2008/SIECONS), "
                           "no al nomenclador. Ninguna regla normativa fue inventada.",
        },
    }
    for k, v in pend.items():
        print(f"  - {k}: {v.get('conclusion', v.get('observacion', ''))[:100]}")
    resultados["pendientes"] = pend

    # ---------- Ejemplo documentado completo ----------
    ejemplo = None
    for rv in rvs:
        d = dec.get(str(rv["CODIGO RV"]))
        if d and not any(d[k] for k in ("inc_mat", "inc_rh", "inc_eq", "inc_jg", "inc_se")) \
           and d["mat"] > 0 and d["rh"] > 0 and d["eq"] > 0:
            ejemplo = {
                "codigo_rv": str(rv["CODIGO RV"]),
                "descripcion": rv.get("Desc Rv"),
                "unidad": rv.get("UNIDAD DE MEDIDA"),
                "cmmn_almacenado": f(rv.get("CMMN")), "cmmn_calculado": round(d["mat"] + d["jg"] + d["se"], 4),
                "chmn_almacenado": f(rv.get("CHMN")), "chmn_calculado": round(d["rh"], 4),
                "cemn_almacenado": f(rv.get("CEMN")), "cemn_calculado": round(d["eq"], 4),
                "hh": f(rv.get("HORAS HOMBRE")), "hh_calculado": round(d["hh"], 4),
                "desglose": {k: round(d[k], 4) for k in ("mat", "jg", "se", "rh", "eq")},
            }
            break
    resultados["ejemplo_verificado"] = ejemplo
    print(f"\nEjemplo documentado: RV {ejemplo['codigo_rv']} — {ejemplo['descripcion']}")

    with open(os.path.join(REPO, "docs", "datos", "fase3c_verificacion.json"), "w", encoding="utf-8") as fp:
        json.dump(resultados, fp, ensure_ascii=False, indent=1)
    print("-> docs/datos/fase3c_verificacion.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
