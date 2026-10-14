#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MISIÓN III-B · Fase 5-6 — Extracción del conjunto pequeño de datos de prueba.

Extrae de la raíz 2017 (fuente real, sin modificarla) casos con valores
EXACTOS para las pruebas de precisión y el caso vertical documentado de la
integración:

  * caso principal: partida 012141 (descomposición completa de materiales)
  * caso multicomponente: partida con juego + semielaborado
  * coeficiente Float32 (valor recuperado bit-exacto)
  * precio Money de 4 decimales exactos
  * precio Money ≥ 1000 (antes se perdía por la coma de miles del formato)

Salida: datos_prueba/casos_iiib.json (compromido en el repo, pequeño y
reproducible con este script).

Uso:  python3 scripts/extraer_caso_prueba.py
"""
import json
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importar_precodi import FuenteMdb, REPO, FUENTE_BASE  # noqa: E402
from precision_precodi import tol_suma_formula  # noqa: E402

RUTA_RAIZ = os.path.join(FUENTE_BASE, "Codigo (PRECODI)/codigo.mdb")
SALIDA = os.path.join(REPO, "datos_prueba", "casos_iiib.json")


def partida_con(f, codigo):
    t = f.parse("Nomenclador de RV")
    for i, c in enumerate(t["CODIGO RV"]):
        if str(c).strip() == codigo:
            fila = {col: t[col][i] for col in t}
            return fila
    return None


def normas_de(f, tabla, codigo_col, coef_col, codigo):
    t = f.parse(tabla)
    out = []
    for i, c in enumerate(t["CodigoRV"]):
        if str(c).strip() == codigo:
            out.append({"codigo_recurso": str(t[codigo_col][i]).strip(),
                        "coeficiente": t[coef_col][i]})
    return out


def main():
    f = FuenteMdb(RUTA_RAIZ, "codigo_raiz")
    casos = {"descripcion": "Casos de prueba MISIÓN III-B extraídos de codigo.mdb raíz 2017 "
                            "(valores EXACTOS de la fuente; regenerable con scripts/extraer_caso_prueba.py)",
             "fuente": {"archivo": RUTA_RAIZ,
                        "sha256": __import__("hashlib").sha256(open(RUTA_RAIZ, "rb").read()).hexdigest()},
             "casos": {}}

    # ---- Caso 1: partida 012141 (caso vertical documentado) ----
    p = partida_con(f, "012141")
    normas = normas_de(f, "Norma de Materiales", "CodMat", "CantMat", "012141")
    mat = f.parse("Nomenclador de Materiales")
    precios = {str(c).strip(): v for c, v in zip(mat["CodMat"], mat["PMN"])}
    suma = sum((Decimal(str(n["coeficiente"])) * (precios.get(n["codigo_recurso"]) or Decimal(0))
                for n in normas), Decimal(0))
    casos["casos"]["partida_012141"] = {
        "descripcion": str(p["Desc Rv"]).strip(), "unidad": str(p["UNIDAD DE MEDIDA"]).strip(),
        "cmmn_almacenado": str(p["CMMN"]), "chmn_almacenado": str(p["CHMN"]),
        "cemn_almacenado": str(p["CEMN"]),
        "normas_materiales": [{"codigo": n["codigo_recurso"],
                               "coeficiente_float32": repr(n["coeficiente"]),
                               "coeficiente_decimal": str(Decimal(str(n["coeficiente"]))),
                               "pmn_decimal": str(precios.get(n["codigo_recurso"]))}
                              for n in normas],
        "suma_esperada_cmmn_decimal": str(suma.quantize(Decimal("0.0001"))),
        "n_componentes": len(normas),
        "tolerancia": tol_suma_formula(len(normas), float(suma)),
    }

    # ---- Caso 2: partida con juego y semielaborado (multicomponente) ----
    nj = f.parse("Norma de Juegos")
    ns = f.parse("Norma de Semielaborados")
    con_juego = {str(c).strip() for c in nj["CodigoRV"]}
    con_semi = {str(c).strip() for c in ns["CodigoRV"]}
    ambos = sorted(con_juego & con_semi)
    codigo2 = ambos[0] if ambos else (sorted(con_juego)[0] if con_juego else None)
    if codigo2:
        p2 = partida_con(f, codigo2)
        casos["casos"]["partida_multicomponente"] = {
            "codigo": codigo2,
            "descripcion": str(p2["Desc Rv"]).strip(),
            "juegos": normas_de(f, "Norma de Juegos", "CodJuego", "CantJuego", codigo2),
            "semielaborados": normas_de(f, "Norma de Semielaborados", "CodSElab", "CantSElab", codigo2),
            "cmmn_almacenado": str(p2["CMMN"]),
        }

    # ---- Caso 3: precio Money de 4 decimales y ≥1000 ----
    pmn_vals = [(str(c).strip(), v) for c, v in zip(mat["CodMat"], mat["PMN"]) if v is not None]
    con4 = next((c_v for c_v in pmn_vals if c_v[1].as_tuple().exponent == -4), None)
    mayor1000 = next((c_v for c_v in pmn_vals if c_v[1] >= 1000), None)
    casos["casos"]["precision_money"] = {
        "precio_4_decimales": {"codigo": con4[0], "pmn_decimal": str(con4[1])} if con4 else None,
        "precio_mayor_1000": {"codigo": mayor1000[0], "pmn_decimal": str(mayor1000[1])} if mayor1000 else None,
        "nota": "el caso ≥1000 se perdía con el parser antiguo (coma de miles → float() fallaba → None)",
    }

    # ---- Caso 4: coeficiente Float32 recuperado ----
    nm = f.parse("Norma de Materiales")
    f32 = None
    for i, v in enumerate(nm["CantMat"]):
        if v is not None and v != round(v, 6) and abs(v) < 1e6:
            # artefacto típico de float32 ampliado a float64 (p. ej. 1.2000000476837158 ≠ 1.2)
            f32 = {"codigo_rv": str(nm["CodigoRV"][i]).strip(), "cod_mat": str(nm["CodMat"][i]).strip(),
                   "valor_recuperado": repr(v), "nota": "float32 ampliado a float64 sin pérdida"}
            break
    casos["casos"]["coeficiente_float32"] = f32

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as fp:
        json.dump(casos, fp, ensure_ascii=False, indent=1)
    print(f"Fixture → {SALIDA}")
    print(json.dumps(casos["casos"], ensure_ascii=False, indent=1)[:1200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
