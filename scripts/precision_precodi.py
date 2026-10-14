#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MISIÓN III-B · Fase 3 — Reglas de precisión numérica para la importación PRECODI.

Problema verificado (docs/AUDITORIA_PREVIA_IIIB.md §6): access_parser devuelve
los tipos Money de Jet 4/Jet 3 en representaciones inconsistentes:

  * sin propiedad Format (7.21/7.22, Jet 3): ENTERO ESCALADO ×10 000
    (CHMN=40683 ⇒ valor real 4.0683)
  * con propiedad Format (raíz 2017, SBD): STRING formateado a 2 decimales
    ('4.07' ⇒ valor real 4.0683, con PÉRDIDA de decimales 3-4) y con coma de
    miles para valores ≥1000 ('1,234.57' ⇒ float() fallaría)
  * valor cero con Format: lista vacía o string por defecto ('0.00')

Este módulo garantiza:

  1. Money  → Decimal EXACTO con 4 decimales (parcheando parse_money_type para
     que devuelva Decimal(entero)/10 000 directamente del dato binario).
  2. Float32/Float64 → se preserva el valor recuperado tal cual (float64
     amplía float32 sin pérdida: 1.2 → 1.2000000476837158).
  3. Tolerancias POR TIPO Y MAGNITUD (nunca una tolerancia universal de 0,01):
       - round-trip de almacenamiento REAL:  max(1e-9, |v|·1e-13)
       - comparación de coeficientes float32: relativa 1.2e-7 (épsilon float32)
       - verificación de sumas (Σ coef×precio): 0.0001·N + Σ|términos|·6e-8
  4. Separación explícita entre fidelidad de importación (nunca redondear)
     y redondeo de presentación (capa visual, 2 decimales).

La conversión es DIRIGIDA POR EL TIPO JET DE COLUMNA (registrado en
docs/datos/fase3a_inventario.json), no por el valor.
"""
from decimal import Decimal, InvalidOperation

ESCALA_MONEY = Decimal(10000)      # Jet Currency: entero de 64 bits escalado ×10 000
ESCALA_PERCENT = Decimal(100)      # formato porcentaje: escalado ×100

# Épsilon relativo de un float32 (2^-23 ≈ 1.19e-7): cota del error relativo
# de un coeficiente recuperado desde Float32.
TOL_FLOAT32_REL = 1.2e-7


def parchear_money_exacto():
    """Parchea access_parser.utils.parse_money_type para que Money (≠0, con
    Format) devuelva el Decimal exacto entero/escala en lugar de un string
    formateado con pérdida.

    El caso Money SIN Format (entero escalado) y el caso cero-con-Format
    (lista/string por defecto) no pasan por parse_money_type: los cubre
    money_a_decimal().
    """
    import access_parser.utils as ap_utils

    if getattr(ap_utils.parse_money_type, "_parche_exacto", False):
        return  # ya parcheado (idempotente)

    def _money_exacto(parsed, prop_format):
        try:
            esc = ESCALA_PERCENT if prop_format == ap_utils.FORMAT_PERCENT else ESCALA_MONEY
            return Decimal(parsed) / esc
        except Exception:  # noqa: BLE001 — valor imprevisible: delegar al original
            return _original(parsed, prop_format)

    _original = ap_utils.parse_money_type
    _money_exacto._parche_exacto = True
    ap_utils.parse_money_type = _money_exacto
    return _money_exacto


def parchear_jet3_textos():
    """Corrige un bug VERIFICADO de access_parser 0.0.6 en registros Jet 3.

    En Jet 3 los offsets de columnas variables al final del registro se
    almacenan módulo 256, junto con una 'tabla de saltos' que indica a partir
    de qué índice de columna hay que sumar 0x100. La librería acumula el
    salto según la columna que LEE, pero calcula el FIN del dato con el
    offset de la columna SIGUIENTE sin aplicarle su salto correspondiente:
    el intervalo queda invertido y las columnas de texto posteriores al
    primer salto decodifican como ''.

    Evidencia (codigo.mdb 7.21, Nomenclador de RV, registro de 277 bytes):
      offsets = [225,227,230,234,240, 1, 1, 3, 3, 3], salto = [5]
      → 'DE MANIGUA MANUAL' ocupa [240, 240+17) = [240, 257): fin real 257 =
        offsets[5] + 0x100 (1+256). La librería calcula record[240:1] = ''.

    La corrección aplica la suma por OFFSET (según el índice al que pertenece
    cada offset, incluido var_len_count) y solo actúa en version 3; Jet 4
    conserva el método original (offsets Int16 completos, sin saltos).
    """
    import access_parser.access_parser as ap_mod
    from access_parser.utils import TYPE_MEMO, TYPE_OLE, parse_type
    try:
        from access_parser.utils import TYPE_96_bit_17_BYTES
    except ImportError:  # pragma: no cover
        TYPE_96_bit_17_BYTES = None
    try:
        from access_parser.utils import numeric_to_string
    except ImportError:  # pragma: no cover
        numeric_to_string = None
    from construct import ConstructError

    AccessTable = ap_mod.AccessTable
    if getattr(AccessTable._parse_dynamic_length_data, "_parche_jet3", False):
        return  # idempotente

    _original = AccessTable._parse_dynamic_length_data

    def _corregido(self, original_record, relative_record_metadata,
                   relative_records_column_map, null_table):
        if getattr(self, "version", 4) != 3:
            return _original(self, original_record, relative_record_metadata,
                             relative_records_column_map, null_table)

        offsets = list(relative_record_metadata.variable_length_field_offsets)
        saltos = sorted(relative_record_metadata.variable_length_jump_table or [])
        n = len(offsets)

        def adicion(idx):
            a = 0
            for e in saltos:
                if idx >= e:
                    a += 0x100
            return a

        for i, column_index in enumerate(relative_records_column_map):
            column = relative_records_column_map[column_index]
            col_name = column.col_name_str
            if column.column_id > len(null_table):
                has_value = True
            else:
                has_value = null_table[column.column_id]
            if not has_value:
                self.parsed_table[col_name].append(None)
                continue
            ini = offsets[i] + adicion(i)
            fin = (relative_record_metadata.var_len_count + adicion(n)) if i + 1 == n \
                else (offsets[i + 1] + adicion(i + 1))
            if fin <= ini:
                self.parsed_table[col_name].append("")
                continue
            data = original_record[ini:fin]
            if column.type == TYPE_MEMO:
                try:
                    parsed = self._parse_memo(data)
                except ConstructError:
                    parsed = data
            elif column.type == TYPE_OLE:
                try:
                    parsed = self._parse_memo(data, return_raw=True)
                except ConstructError:
                    parsed = data
            elif (TYPE_96_bit_17_BYTES is not None and column.type == TYPE_96_bit_17_BYTES
                  and numeric_to_string is not None):
                if len(data) != 17:
                    parsed = data
                else:
                    scale = column.get("various", {}).get("scale", 6)
                    parsed = numeric_to_string(data, scale)
            else:
                parsed = parse_type(column.type, data, len(data), version=self.version)
            self.parsed_table[col_name].append(parsed)

    _corregido._parche_jet3 = True
    AccessTable._parse_dynamic_length_data = _corregido


def money_a_decimal(v):
    """Cualquier representación Money de access_parser → Decimal exacto.

    int    → Decimal(v)/10 000            (sin Format: entero escalado)
    Decimal→ tal cual                      (parche aplicado, valor ≠ 0)
    list   → Decimal(0)                    (cero con formato: artifacto de parse_type)
    str    → limpieza de moneda/miles/%     (defensivo: ceros por defecto o parche ausente)
    None   → None                          (nulo real: NO es cero)
    """
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, bool):
        raise TypeError(f"booleano no es Money: {v!r}")
    if isinstance(v, int):
        return Decimal(v) / ESCALA_MONEY
    if isinstance(v, float):
        # No debería ocurrir con Money; si ocurre, conservar dígitos del repr
        return Decimal(repr(v))
    if isinstance(v, list):
        return Decimal(0)
    if isinstance(v, str):
        s = v.strip().replace(" ", "").replace("$", "").replace("€", "")
        if s.endswith("%"):
            try:
                return Decimal(s[:-1].replace(",", "")) / Decimal(100)
            except InvalidOperation:
                return Decimal(0)
        s = s.replace(",", "")  # separador de miles
        if s in ("", "-", "--"):
            return Decimal(0)
        try:
            return Decimal(s)
        except InvalidOperation:
            # String por defecto de un formato desconocido con valor cero
            return Decimal(0)
    raise TypeError(f"tipo Money no manejado: {type(v).__name__} {v!r}")


def a_real(v):
    """Float32/Float64 → float preservando el valor recuperado (sin redondear).

    None → None. Los enteros se amplían sin pérdida. Los strings numéricos
    (defensivo) se interpretan con coma decimal.
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def decimal_a_real(d):
    """Decimal exacto → REAL de SQLite (float64).

    float64 conserva 15-16 dígitos significativos: cualquier valor de 4
    decimales con magnitud ≤ 1e11 viaja sin pérdida del VALOR (verificado por
    las pruebas de round-trip con tol max(1e-9, |v|·1e-13)).
    """
    return None if d is None else float(d)


# ----------------------------------------------------------------------------
# Tolerancias por tipo y magnitud (NADA de tolerancia universal 0,01)
# ----------------------------------------------------------------------------

def tol_roundtrip_money(v):
    """Tolerancia absoluta al comparar un Money almacenado (REAL) con su
    Decimal exacto: max(1e-9, |v|·1e-13)."""
    mag = abs(float(v)) if v is not None else 0.0
    return max(1e-9, mag * 1e-13)


def tol_suma_formula(n_terminos, suma_abs_terminos):
    """Tolerancia al verificar Σ coef×precio contra un costo almacenado:
    0.0001·N (acumulación de redondeo de 4 decimales) más el error relativo
    float32 (6e-8) acumulado sobre la magnitud de los términos."""
    return max(0.0001 * max(1, n_terminos), suma_abs_terminos * 6e-8)


def redondear_presentacion(v, decimales=2):
    """SOLO capa de presentación (UI). Nunca aplicar durante la importación."""
    if v is None:
        return None
    return round(v, decimales)


# ----------------------------------------------------------------------------
# Tipos Jet por columna (del inventario verificado fase3a)
# ----------------------------------------------------------------------------

def cargar_tipos_inventario(ruta_json, base_id):
    """Lee fase3a_inventario.json y devuelve {(tabla, columna): 'money'|'real'|
    'texto'|'entero'|'booleano'|'fecha'|'memo'|'binario'|desconocido}."""
    import json
    with open(ruta_json, encoding="utf-8") as f:
        inv = json.load(f)
    base = next((b for b in inv["bases"] if b["id"] == base_id), None)
    tipos = {}
    if not base:
        return tipos
    for t in base.get("tablas", []):
        for c in t.get("columnas", []):
            nombre_tipo = c.get("tipo", "")
            if nombre_tipo.startswith("Moneda"):
                k = "money"
            elif nombre_tipo.startswith("Real simple"):
                k = "real32"
            elif nombre_tipo.startswith("Real doble"):
                k = "real64"
            elif nombre_tipo.startswith("Entero") or nombre_tipo.startswith("Byte"):
                k = "entero"
            elif nombre_tipo.startswith("Booleano"):
                k = "booleano"
            elif nombre_tipo.startswith("Fecha"):
                k = "fecha"
            elif nombre_tipo.startswith("Texto") or nombre_tipo.startswith("Memo"):
                k = "texto"
            else:
                k = "desconocido"
            tipos[(t["tabla"], c["nombre"])] = k
    return tipos


def convertir_por_tipo(valor, tipo):
    """Aplica la conversión canónica según el tipo Jet de la columna."""
    if tipo == "money":
        return money_a_decimal(valor)
    if tipo in ("real32", "real64"):
        return a_real(valor)
    if tipo == "entero":
        return valor if (valor is None or isinstance(valor, int)) else a_real(valor)
    return valor  # texto / booleano / fecha / desconocido: tal cual
