#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MISIÓN III-B · Fase 4 — Clasificación de las 284 tablas de SBD2008_815.mdb.

NO importa nada: solo clasifica (estructura) y documenta. La verificación de
relaciones CON DATOS la hace el importador al importar cada tabla priorizada
(comprobación de huérfanos contra el núcleo).

Categorías (según la misión):
  1. Integrable directamente        — núcleo PRECODI con esquema igual al de
                                      codigo.mdb (verificado por columnas).
  2. Integrable mediante transformación — tablas priorizadas con semántica
                                      comprendida: colecciones y composiciones,
                                      normas RH y variantes de tarifas, normas
                                      descriptivas, duración y costo, macros,
                                      composiciones presupuestarias existentes
                                      y sus tablas padre mínimas.
  3. Solo documental o de referencia — tablas empresariales (AGIT, contratos,
                                      certificaciones, bancos…) que se quedan
                                      en la base original sin importar.
  4. Pendiente de interpretación    — vacías (112) o sin semántica verificada.

Salida: docs/datos/sbd_clasificacion.json + resumen stdout.

Uso:  python3 scripts/clasificar_sbd.py
"""
import json
import os
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = os.path.join(REPO, "docs", "datos", "fase3a_inventario.json")

# Núcleo PRECODI (esquema verificado en codigo.mdb): si las columnas coinciden
# con las de la raíz 2017 → categoría 1.
NUCLEO_CORE = [
    "Nomenclador de SobreGrupos RV", "Nomenclador de Grupos RV", "Nomenclador de SubGrupos RV",
    "Nomenclador de RV", "Nomenclador de Materiales", "Nomenclador de Mano de Obra",
    "Nomenclador de Equipos", "Nomenclador de Juegos", "Nomenclador de Semielaborados",
    "Norma de Materiales", "Norma de Mano de Obra", "Norma de Equipos", "Norma de Juegos",
    "Norma de Semielaborados", "Norma Juego Material", "Norma Semi Material",
    "Norma Semi RHumanos", "Norma Semi Equipos",
]

# Prioritarias de la misión (categoría 2) — transformación documentada en el JSON.
PRIORITARIAS = {
    # Normas RH y variantes de tarifas
    "Normas RH": "Normas de rendimiento de mano de obra (variante RH del núcleo)",
    "Normas RH Extendida": "Variante extendida de normas RH (57 838 filas)",
    "Normas Eq": "Normas de equipos (variante)",
    "Normas Eq Comp": "Componentes de normas de equipos (vacía)",
    "Normas RH Comp": "Componentes de normas RH (vacía)",
    "Tarifas de T": "Tarifas de transporte origen-destino × servicio × distancia",
    "Tarifas_AD_TD": "Tarifas adicionales/descargas (tipo × sub_servicio)",
    "Tarifas de Demora": "Tarifas de demora de transporte",
    "Tarifas de Recorrido Vacio": "Tarifas de recorrido en vacío",
    # Normas descriptivas
    "Normas Descriptivas": "Normas descriptivas con especificación y composición de cuadrillas",
    # Duración y costo
    "tc Duración y Costo con Norma Precons MO": "Duración y costo por RV con norma PRECONS de mano de obra",
    "Actividades de Estimación": "Actividades de estimación con tiempos PERT y precios",
    # Colecciones y sus composiciones
    "Colecciones": "Cabeceras de colecciones de precios por suministrador",
    "Colecciones Composición": "Recursos con precio por colección",
    "ColecRV Composición": "Variantes salariales por RV en cada colección",
    # Macros
    "Macros Composicion RV": "Agrupaciones macro de RV",
    # Composiciones presupuestarias existentes + padres mínimos
    "Presupuesto Composición RV": "Partidas presupuestadas de obras existentes en la base",
    "Presupuesto Composición Mat": "Materiales de las partidas presupuestadas",
    "Presupuesto Composición RH": "Mano de obra de las partidas presupuestadas",
    "Presupuesto Composición Equipo": "Equipos de las partidas presupuestadas",
    "Presupuesto Composición SE": "Semielaborados de las partidas presupuestadas",
    "Objetos de Obra": "Padre (IdObjObra) de Presupuesto Composición RV — importación mínima",
    "Etapas": "Padre (IdEtapa) de Presupuesto Composición RV",
    "Obras": "Contexto de Objetos de Obra — importación mínima",
}

PATRONES_DOCUMENTALES = [
    ("AGIT", "módulo empresarial AGIT (contratos, certificaciones, solicitudes)"),
    ("Contrato", "gestión de contratos"),
    ("Certificaci", "certificaciones de obra"),
    ("Factura", "facturación"),
    ("Banco", "entidades bancarias"),
    ("Cuenta", "cuentas contables"),
    ("Recibo", "recibos"),
    ("Cliente", "clientes"),
    ("Suministrador", "suministradores (referencia)"),
    ("Entidad", "entidades"),
    ("Provincia", "provincias (referencia)"),
    ("Usuario", "usuarios del sistema legado"),
]


def clasificar():
    inv = json.load(open(INV, encoding="utf-8"))
    sbd = next(b for b in inv["bases"] if b["id"] == "sbd2008_815")
    raiz = next(b for b in inv["bases"] if b["id"] == "codigo_raiz")
    cols_raiz = {t["tabla"]: [c["nombre"] for c in t.get("columnas", [])]
                 for t in raiz.get("tablas", [])}

    resultado = {"generado": datetime.now(timezone.utc).isoformat(),
                 "base": "sbd2008_815", "total_tablas": sbd["num_tablas_usuario"],
                 "tablas": {}, "resumen": {}}
    conteos = {1: 0, 2: 0, 3: 0, 4: 0}
    filas_por_cat = {1: 0, 2: 0, 3: 0, 4: 0}

    for t in sbd["tablas"]:
        nombre, filas = t["tabla"], t.get("filas") or 0
        cols = [c["nombre"] for c in t.get("columnas", [])]
        reg = {"filas": filas, "columnas_n": len(cols),
               "columnas": cols, "categoria": None, "nota": ""}

        if nombre in NUCLEO_CORE:
            iguales = cols_raiz.get(nombre) == cols
            reg["categoria"] = 1 if iguales else 2
            reg["nota"] = ("esquema idéntico al núcleo de codigo.mdb raíz → importador común"
                           if iguales else
                           "núcleo con esquema DIFERENTE a la raíz 2017 → requiere adaptación "
                           "(columnas: " + ", ".join(cols) + ")")
        elif nombre in PRIORITARIAS:
            reg["categoria"] = 2
            reg["nota"] = PRIORITARIAS[nombre]
            reg["prioritaria"] = True
        elif filas == 0:
            reg["categoria"] = 4
            reg["nota"] = "tabla vacía: sin datos no hay semántica verificable"
        else:
            doc = next((mot for pat, mot in PATRONES_DOCUMENTALES if pat.lower() in nombre.lower()), None)
            if doc:
                reg["categoria"] = 3
                reg["nota"] = doc + " — queda en la base original sin importar"
            elif nombre.startswith("Esp "):
                reg["categoria"] = 4
                reg["nota"] = "específicos por obra: pendiente de interpretar su relación con el modelo"
            else:
                reg["categoria"] = 4
                reg["nota"] = "sin patrón reconocido ni semántica verificada en esta fase"

        resultado["tablas"][nombre] = reg
        conteos[reg["categoria"]] += 1
        filas_por_cat[reg["categoria"]] += filas

    resultado["resumen"] = {
        "categoria_1_integrable_directamente": conteos[1],
        "categoria_2_integrable_transformacion": conteos[2],
        "categoria_3_documental_referencia": conteos[3],
        "categoria_4_pendiente": conteos[4],
        "filas_por_categoria": filas_por_cat,
    }
    return resultado


def main():
    r = clasificar()
    salida = os.path.join(REPO, "docs", "datos", "sbd_clasificacion.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)

    print(f"SBD2008_815: {r['total_tablas']} tablas clasificadas")
    for k, v in r["resumen"].items():
        print(f"  {k}: {v}")
    print("\nCategoría 2 priorizadas (se importarán con verificación de relaciones):")
    for n, reg in r["tablas"].items():
        if reg.get("prioritaria"):
            print(f"  - {n} [{reg['filas']} filas]")
    print("\nNúcleo (cat 1):")
    for n in NUCLEO_CORE:
        reg = r["tablas"].get(n)
        if reg and reg["categoria"] == 1:
            print(f"  - {n} [{reg['filas']} filas] ✓ esquema igual a raíz")
        elif reg:
            print(f"  - {n} [{reg['filas']} filas] ⚠ esquema DISTINTO: {reg['nota'][:80]}")
    print(f"\nJSON -> {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
