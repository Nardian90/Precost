#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE III-B — Diccionario de datos y verificación de relaciones.

Lee SOLO las bases .mdb PRECODI (nunca las modifica) y produce:

  docs/datos/fase3b_diccionario.json    — estadísticas por tabla/columna
  docs/datos/fase3b_relaciones.json     — verificación de FK con datos reales
  docs/datos/fase3b_comparativa.json    — comparativa de esquemas entre versiones

Para cada tabla de las bases codigo.mdb (canónica: raíz 2017) calcula:
  - nulos por columna, distinct de columnas de código, duplicados de PK
  - muestras de valores, longitudes máximas, dominios de unidades
Para las relaciones declaradas (ver LISTA_RELACIONES) calcula huérfanos
reales: claves presentes en la tabla hija que no existen en la padre.

Uso:  python3 scripts/fase3b_diccionario.py
"""
import json
import logging
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

logging.getLogger("access_parser").setLevel(logging.CRITICAL)
from access_parser import AccessParser  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE = "/home/z/my-project/work/recuperacion/analisis/PRECODI"
INV = json.load(open(os.path.join(REPO, "docs", "datos", "fase3a_inventario.json"), encoding="utf-8"))

# Interpretación de finalidad por tabla (basada en nombres, columnas y muestras reales)
FINALIDAD = {
    "AGIT_Indicadores Hijos": "Indicadores económicos de construcción (AGIT) desglosados por grupos de salario; catálogo de indicadores para análisis.",
    "Actividades de Estimación": "Catálogo de actividades de estimación con precio por unidad y tiempos (pesimista/esperado/optimista), para estimaciones rápidas.",
    "HojaCalculo": "Tabla de trabajo temporal (borrador) que la aplicación Codigo.exe usa para armar descomposiciones; no es un nomenclador.",
    "Nomenclador de Equipos": "Nomenclador maestro de equipos de construcción: código, descripción, unidad (HE), precio/tarifa MN y MLC.",
    "Nomenclador de Grupos RV": "Segundo nivel de la jerarquía de renglones de variante (grupo dentro de sobregrupo).",
    "Nomenclador de Juegos": "Nomenclador de juegos de trabajo (paquetes de materiales que se instalan conjuntamente, p.ej. juegos de tuberías); precio por juego.",
    "Nomenclador de Mano de Obra": "Nomenclador maestro de mano de obra por categoría/oficio: código, descripción, unidad (hh), salario/hora MN y MLC, grupo salarial.",
    "Nomenclador de Materiales": "Nomenclador maestro de materiales: código, descripción, unidad, familia, precio unitario MN/MLC, peso, suministrador.",
    "Nomenclador de RV": "Nomenclador central de renglones de variante (partidas de presupuesto): código, descripción, unidad de medida, costos unitarios desglosados (materiales/mano de obra/equipos, MN y MLC), horas hombre/equipo e indicadores de consumo (cemento, áridos, asfalto, carga, prefabricado).",
    "Nomenclador de Semielaborados": "Nomenclador de productos semielaborados (p.ej. repello monocapa) con precio unitario; se descomponen en recursos vía Norma Semi*.",
    "Nomenclador de SobreGrupos RV": "Primer nivel de la jerarquía de renglones de variante (capítulos).",
    "Nomenclador de SubGrupos RV": "Tercer nivel de la jerarquía de renglones de variante (subgrupos).",
    "Norma Juego Material": "Descomposición de cada juego de trabajo en sus materiales componentes (coeficiente de consumo CantMatJ por unidad de juego).",
    "Norma Propia de Equipos": "Normas de equipos definidas por el usuario (vacía en las copias analizadas).",
    "Norma Propia de Mano de Obra": "Normas de mano de obra definidas por el usuario (vacía en las copias analizadas).",
    "Norma Semi Equipos": "Descomposición de semielaborados en equipos.",
    "Norma Semi Material": "Descomposición de semielaborados en materiales.",
    "Norma Semi RHumanos": "Descomposición de semielaborados en mano de obra.",
    "Norma de Equipos": "Norma de consumo de equipos por renglón de variante: coeficiente CantEquipo por unidad de RV (con código de norma compleja opcional).",
    "Norma de Juegos": "Norma de consumo de juegos de trabajo por renglón de variante.",
    "Norma de Mano de Obra": "Norma de consumo de mano de obra por renglón de variante: coeficiente CantRHum (hh por unidad de RV), con norma compleja opcional.",
    "Norma de Materiales": "Norma de consumo de materiales por renglón de variante: coeficiente CantMat por unidad de RV.",
    "Norma de Semielaborados": "Norma de consumo de semielaborados por renglón de variante.",
}

# Relaciones a VERIFICAR con datos (hija → padre). Verificada = 0 huérfanos.
LISTA_RELACIONES = [
    ("Nomenclador de RV", "CodSobreG", "Nomenclador de SobreGrupos RV", "CodSobreG"),
    ("Nomenclador de RV", "CodG", "Nomenclador de Grupos RV", "CodG"),
    ("Nomenclador de SubGrupos RV", "CodSobreG", "Nomenclador de SobreGrupos RV", "CodSobreG"),
    ("Nomenclador de SubGrupos RV", "CodG", "Nomenclador de Grupos RV", "CodG"),
    ("Nomenclador de Grupos RV", "CodSobreG", "Nomenclador de SobreGrupos RV", "CodSobreG"),
    ("Norma de Materiales", "CodigoRV", "Nomenclador de RV", "CODIGO RV"),
    ("Norma de Materiales", "CodMat", "Nomenclador de Materiales", "CodMat"),
    ("Norma de Mano de Obra", "CodigoRV", "Nomenclador de RV", "CODIGO RV"),
    ("Norma de Mano de Obra", "CodRHum", "Nomenclador de Mano de Obra", "CodRHum"),
    ("Norma de Equipos", "CodigoRV", "Nomenclador de RV", "CODIGO RV"),
    ("Norma de Equipos", "CodEquipo", "Nomenclador de Equipos", "CodEquipo"),
    ("Norma de Juegos", "CodigoRV", "Nomenclador de RV", "CODIGO RV"),
    ("Norma de Juegos", "CodJuego", "Nomenclador de Juegos", "CodJuego"),
    ("Norma de Semielaborados", "CodigoRV", "Nomenclador de RV", "CODIGO RV"),
    ("Norma de Semielaborados", "CodSElab", "Nomenclador de Semielaborados", "CodSElab"),
    ("Norma Juego Material", "CodJuego", "Nomenclador de Juegos", "CodJuego"),
    ("Norma Juego Material", "CodMat", "Nomenclador de Materiales", "CodMat"),
    ("Norma Semi Material", "CodSemi", "Nomenclador de Semielaborados", "CodSElab"),
    ("Norma Semi Material", "CodMat", "Nomenclador de Materiales", "CodMat"),
    ("Norma Semi Equipos", "CodSemi", "Nomenclador de Semielaborados", "CodSElab"),
    ("Norma Semi Equipos", "CodEquipo", "Nomenclador de Equipos", "CodEquipo"),
    ("Norma Semi RHumanos", "CodSemi", "Nomenclador de Semielaborados", "CodSElab"),
    ("Norma Semi RHumanos", "CodRHum", "Nomenclador de Mano de Obra", "CodRHum"),
]

# Columnas cuyo dominio conviene documentar (unidades de medida)
COLS_DOMINIO = [
    ("Nomenclador de Materiales", "UmRec"),
    ("Nomenclador de Mano de Obra", "UmRec"),
    ("Nomenclador de Equipos", "UmRec"),
    ("Nomenclador de Juegos", "UmRec"),
    ("Nomenclador de Semielaborados", "UmRec"),
    ("Nomenclador de RV", "UNIDAD DE MEDIDA"),
    ("Nomenclador de RV", "TIPO"),
]


def cargar(db_id, tablas_deseadas=None):
    """Abre la base y parsea las tablas indicadas (o todas las de usuario)."""
    base = next(b for b in INV["bases"] if b["id"] == db_id)
    ruta = os.path.join(FUENTE, base["archivo"])
    db = AccessParser(ruta)
    out = {}
    for nombre in db.catalog:
        if nombre.startswith("MSys"):
            continue
        if tablas_deseadas and nombre not in tablas_deseadas:
            continue
        try:
            out[nombre] = db.parse_table(nombre)
        except Exception as e:  # noqa: BLE001
            out[nombre] = None
            print(f"  !! {nombre}: {e}", file=sys.stderr)
    return out


def columnas_de(datos):
    if not datos:
        return []
    return list(datos.keys())


def stats_columna(valores):
    n = len(valores)
    nulos = sum(1 for v in valores if v is None or (isinstance(v, str) and v.strip() == ""))
    distintos = len({str(v) for v in valores if v is not None})
    return {"n": n, "nulos": nulos, "distintos": distintos}


def main():
    print("=== FASE III-B: diccionario y relaciones (codigo.mdb raíz 2017) ===")
    tablas_necesarias = set(FINALIDAD) | {r[0] for r in LISTA_RELACIONES} | {r[2] for r in LISTA_RELACIONES}
    datos = cargar("codigo_raiz", tablas_necesarias)

    dic = {"generado": datetime.now(timezone.utc).isoformat(),
           "base": "codigo.mdb raíz (2017)", "tablas": {}}

    # --- Estadísticas por tabla ---
    for nombre, tdatos in sorted(datos.items()):
        meta_inv = None
        base_inv = next(b for b in INV["bases"] if b["id"] == "codigo_raiz")
        meta_inv = next((t for t in base_inv["tablas"] if t["tabla"] == nombre), None)
        entrada = {
            "finalidad": FINALIDAD.get(nombre, "(sin interpretación)"),
            "filas": meta_inv["filas"] if meta_inv else None,
            "pk": meta_inv["claves_primarias"] if meta_inv else [],
            "columnas": {},
        }
        if tdatos:
            for col, valores in tdatos.items():
                st = stats_columna(valores)
                # duplicados de PK
                entrada["columnas"][col] = st
            # calidad: PK duplicada / nula
            pk = entrada["pk"]
            if pk and all(k in tdatos for k in pk):
                tuplas = [tuple(str(tdatos[k][i]) for k in pk) for i in range(entrada["filas"] or 0)]
                dups = [t for t, c in Counter(tuplas).items() if c > 1]
                entrada["pk_duplicadas"] = len(dups)
                entrada["pk_nulas"] = sum(1 for t in tuplas if any(v == "None" or v.strip() in ("", "None") for v in t))
        dic["tablas"][nombre] = entrada

    # --- Dominios (unidades, tipos) ---
    dominios = {}
    for tabla, col in COLS_DOMINIO:
        tdatos = datos.get(tabla)
        if tdatos and col in tdatos:
            c = Counter(str(v) for v in tdatos[col] if v is not None)
            dominios[f"{tabla}.{col}"] = c.most_common(30)
    dic["dominios"] = dominios

    # --- Verificación de relaciones (huérfanos reales) ---
    print("\nVerificando relaciones con datos reales...")
    rels = []
    for hija, col_h, padre, col_p in LISTA_RELACIONES:
        dh, dp = datos.get(hija), datos.get(padre)
        if not dh or not dp:
            rels.append({"hija": hija, "col_hija": col_h, "padre": padre, "col_padre": col_p,
                         "estado": "NO VERIFICABLE (tabla sin datos/ilegible)"})
            continue
        if col_h not in dh or col_p not in dp:
            rels.append({"hija": hija, "col_hija": col_h, "padre": padre, "col_padre": col_p,
                         "estado": "NO VERIFICABLE (columna ausente)"})
            continue
        h = {str(v).strip() for v in dh[col_h] if v is not None and str(v).strip() not in ("", "None")}
        p = {str(v).strip() for v in dp[col_p] if v is not None and str(v).strip() not in ("", "None")}
        huerfanos = h - p
        rel = {"hija": hija, "col_hija": col_h, "padre": padre, "col_padre": col_p,
               "valores_hija": len(h), "valores_padre": len(p),
               "huerfanos": len(huerfanos)}
        rel["estado"] = "VERIFICADA" if not huerfanos else "VIOLADA"
        if huerfanos:
            rel["ejemplos_huerfanos"] = sorted(huerfanos)[:10]
        # cardinalidad
        rel["cobertura_padre"] = round(len(h & p) / len(p), 4) if p else None
        rels.append(rel)
        print(f"  {hija}.{col_h} -> {padre}.{col_p}: {rel['estado']}"
              + (f" ({len(huerfanos)} huérfanos)" if huerfanos else ""))

    # --- Unicidad de CODIGO RV por separado (PK compuesta vs código simple) ---
    drv = datos.get("Nomenclador de RV")
    if drv and "CODIGO RV" in drv:
        codigos = [str(v).strip() for v in drv["CODIGO RV"] if v is not None]
        unicos = len(set(codigos))
        dic["unicidad_codigo_rv"] = {
            "filas": len(codigos), "codigos_distintos": unicos,
            "duplicados": len(codigos) - unicos,
            "longitudes": dict(Counter(len(c) for c in codigos)),
        }
        print(f"\nUnicidad CODIGO RV: {unicos} distintos / {len(codigos)} filas")

    # --- Estructura del código RV: relación con jerarquía ---
    if drv:
        prefijos_ok = 0
        analizados = 0
        for i in range(len(drv["CODIGO RV"])):
            sg, g, sg3, crv = (drv["CodSobreG"][i], drv["CodG"][i],
                               drv["CodSubG"][i], str(drv["CODIGO RV"][i]))
            if crv and len(crv) >= 4:
                analizados += 1
                if crv[:2] == str(sg) and crv[2:4] != "":
                    prefijos_ok += 1
        dic["estructura_codigo_rv"] = {
            "analizados": analizados,
            "prefijo_sobregrupo_coincide": prefijos_ok,
        }

    with open(os.path.join(REPO, "docs", "datos", "fase3b_diccionario.json"), "w", encoding="utf-8") as f:
        json.dump(dic, f, ensure_ascii=False, indent=1)
    with open(os.path.join(REPO, "docs", "datos", "fase3b_relaciones.json"), "w", encoding="utf-8") as f:
        json.dump(rels, f, ensure_ascii=False, indent=1)
    print(f"\n-> docs/datos/fase3b_diccionario.json ({len(dic['tablas'])} tablas)")
    print(f"-> docs/datos/fase3b_relaciones.json ({len(rels)} relaciones)")

    # ================= COMPARATIVA DE ESQUEMAS ENTRE VERSIONES =================
    print("\n=== Comparativa de esquemas entre versiones ===")
    bases_cmp = ["codigo_721", "codigo_722", "codigo_raiz", "codigo_preambulos", "sbd2008_815"]
    esquemas = {}
    for bid in bases_cmp:
        b = next(x for x in INV["bases"] if x["id"] == bid)
        esquemas[bid] = {
            t["tabla"]: {c["nombre"]: c["tipo_jet"] for c in t["columnas"]}
            for t in b.get("tablas", [])
        }
    comparativa = {}
    todas = sorted({t for e in esquemas.values() for t in e})
    for t in todas:
        fila = {}
        for bid in bases_cmp:
            cols = esquemas[bid].get(t)
            if cols is None:
                fila[bid] = None
            else:
                fila[bid] = {"n_cols": len(cols)}
        # diferencias de columnas entre 7.21 (jet3) y raíz (jet4)
        c721, craiz = esquemas["codigo_721"].get(t), esquemas["codigo_raiz"].get(t)
        if c721 is not None and craiz is not None:
            solo721 = set(c721) - set(craiz)
            soloRaiz = set(craiz) - set(c721)
            tip_dist = {c for c in set(c721) & set(craiz) if c721[c] != craiz[c]}
            if solo721 or soloRaiz or tip_dist:
                fila["dif_721_vs_raiz"] = {
                    "solo_721": sorted(solo721), "solo_raiz": sorted(soloRaiz),
                    "tipo_distinto": sorted(tip_dist)}
        comparativa[t] = fila
    with open(os.path.join(REPO, "docs", "datos", "fase3b_comparativa.json"), "w", encoding="utf-8") as f:
        json.dump({
            "bases": {bid: next(x for x in INV["bases"] if x["id"] == bid)["etiqueta"] for bid in bases_cmp},
            "tablas": comparativa}, f, ensure_ascii=False, indent=1)
    print("-> docs/datos/fase3b_comparativa.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
