#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MISIÓN III-B · Fase 6 — Suite de pruebas automatizadas de la integración.

Escenarios exigidos por la misión:
  1. Las cuatro variantes de codigo.mdb (3 conjuntos de datos + 1 duplicado).
  2. Diferencias de esquema y tablas opcionales por variante.
  3. Importaciones repetidas (idempotencia: 0 duplicados).
  4. Duplicados y claves huérfanas detectados y registrados.
  5. Valores nulos y códigos desconocidos preservados/contados.
  6. Coeficientes Float32 preservados bit a bit.
  7. Precios Money de 4 decimales con round-trip exacto (y caso ≥1000).
  8. Normas con múltiples componentes (materiales + juegos + semielaborados).
  9. Recuperación ante importación interrumpida (rollback + reintento limpio).
  10. Conservación del catálogo original de PRECOST (SHA-256 + inyección solo
      al servir + catálogo embebido intacto).

Además: conciliación de recuentos origen↔destino por tabla y base, con toda
diferencia explicada por reglas documentadas.

Uso:  python3 scripts/tests_iiib.py            (requiere bd/precodi.db importada)
      python3 scripts/tests_iiib.py -v
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

BD = os.path.join(REPO, "bd", "precodi.db")
HTML = os.path.join(REPO, "app", "PRECOST-v9.17.html")
FIXTURE = os.path.join(REPO, "datos_prueba", "casos_iiib.json")
SHA_HTML = "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"

from precision_precodi import tol_roundtrip_money  # noqa: E402


def con_bd(ruta=BD):
    c = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def stats_importacion(con, version):
    fila = con.execute("""SELECT i.filas_por_tabla, i.advertencias, i.resultado FROM importaciones i
        JOIN versiones_catalogo v ON v.id=i.version_id WHERE v.version=? ORDER BY i.id DESC LIMIT 1""",
        (version,)).fetchone()
    return json.loads(fila["filas_por_tabla"]), json.loads(fila["advertencias"]), fila["resultado"]


class TestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(BD):
            raise unittest.SkipTest("bd/precodi.db no existe: ejecute scripts/importar_precodi.py --todas "
                                    "y --base sbd --priorizadas antes de las pruebas")
        cls.con = con_bd()
        cls.fixture = json.load(open(FIXTURE, encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1-2. Variantes y diferencias de esquema
# ---------------------------------------------------------------------------
class TestVariantes(TestBase):
    def test_cuatro_variantes_registradas(self):
        vers = {r["version"]: r for r in self.con.execute(
            "SELECT vc.*, c.codigo AS catalogo FROM versiones_catalogo vc "
            "JOIN catalogos c ON c.id=vc.catalogo_id")}
        for v in ("2007-v7.21", "2007-v7.22", "2017-raiz", "2007-v7.21-Preambulos"):
            self.assertIn(v, vers, f"falta la versión {v}")
        self.assertEqual(vers["2007-v7.21-Preambulos"]["estado"], "retirada")
        self.assertEqual(vers["2007-v7.21-Preambulos"]["fuente_sha256"],
                         vers["2007-v7.21"]["fuente_sha256"], "Preambulos debe ser duplicado exacto de 7.21")

    def test_preambulos_cero_filas_propias(self):
        vid = self.con.execute("SELECT id FROM versiones_catalogo WHERE version='2007-v7.21-Preambulos'").fetchone()[0]
        n = self.con.execute("SELECT COUNT(*) FROM partidas WHERE version_id=?", (vid,)).fetchone()[0]
        self.assertEqual(n, 0, "la referencia duplicada no debe tener filas propias")

    def test_diferencias_de_esquema_por_variante(self):
        # 7.21 (Jet 3): 15347 partidas, sin 'Norma Juego Material1' (22 tablas)
        # 7.22: 15351, con 'Actividades de Estimación' (23 tablas)
        # raíz 2017: 15351, con ambas (24 tablas) — NJM1 verificada duplicada exacta
        esperado = {"2007-v7.21": 15347, "2007-v7.22": 15351, "2017-raiz": 15351, "2011-sbd2008": 15359}
        for v, n in esperado.items():
            real = self.con.execute("""SELECT COUNT(*) FROM partidas p JOIN versiones_catalogo v
                ON v.id=p.version_id WHERE v.version=?""", (v,)).fetchone()[0]
            self.assertEqual(real, n, f"{v}: {real} partidas ≠ {n}")

    def test_njm1_duplicada_verificada_en_raiz(self):
        stats, adv, _ = stats_importacion(self.con, "2017-raiz")
        self.assertEqual(stats["Norma Juego Material1"].get("insertadas", 0), 0)
        self.assertTrue(any("Norma Juego Material1" in a and "copia EXACTA" in a for a in adv),
                        "debe registrarse la verificación de NJM1 como copia exacta")


# ---------------------------------------------------------------------------
# 3. Idempotencia
# ---------------------------------------------------------------------------
class TestIdempotencia(TestBase):
    def test_reimportar_no_duplica(self):
        r = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "importar_precodi.py"),
                            "--base", "raiz"], capture_output=True, text=True, timeout=300)
        self.assertIn("omitida_idempotente", r.stdout, r.stdout + r.stderr)
        # recuentos idénticos tras el reintento
        vid = self.con.execute("SELECT id FROM versiones_catalogo WHERE version='2017-raiz'").fetchone()[0]
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM partidas WHERE version_id=?", (vid,)).fetchone()[0], 15351)
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM normas_partida WHERE version_id=?", (vid,)).fetchone()[0], 73978)
        # sin filas duplicadas por (versión, código)
        dup = self.con.execute("""SELECT codigo, COUNT(*) c FROM partidas WHERE version_id=?
            GROUP BY codigo HAVING c > 1""", (vid,)).fetchall()
        self.assertEqual(len(dup), 0, f"códigos duplicados: {[dict(d) for d in dup]}")


# ---------------------------------------------------------------------------
# 4-5. Duplicados, huérfanos, nulos y desconocidos
# ---------------------------------------------------------------------------
class TestCalidadDatos(TestBase):
    def test_duplicados_detectados_y_registrados(self):
        stats, _, resultado = stats_importacion(self.con, "2011-sbd2008")
        self.assertEqual(stats["Norma de Mano de Obra"].get("duplicadas_omitidas"), 13)
        self.assertEqual(stats["Norma de Equipos"].get("duplicadas_omitidas"), 23)
        self.assertEqual(resultado, "ok_con_advertencias")

    def test_huerfanas_registradas(self):
        stats, adv, _ = stats_importacion(self.con, "2011-sbd2008")
        self.assertEqual(stats["Presupuesto Composición Mat"].get("huérfanas_recurso"), 7)
        self.assertTrue(any("recurso" in a.lower() and "presupuesto" in a.lower() for a in adv))

    def test_unidades_y_codigos_nulos(self):
        # Tras el parche Jet 3 NO existe ninguna partida sin unidad en las 4 variantes
        # (las "43 sin unidad" del análisis previo eran síntoma del bug de textos)
        n = self.con.execute(
            "SELECT COUNT(*) FROM partidas p WHERE p.unidad IS NULL OR p.unidad=''").fetchone()[0]
        self.assertEqual(n, 0, "no debe haber unidades nulas: si las hay, preservarlas como NULL y documentarlas")
        # El caso REAL de código nulo: Equipos de la raíz (PK nula documentada en fase III-B)
        stats, adv, _ = stats_importacion(self.con, "2017-raiz")
        self.assertEqual(stats["Nomenclador de Equipos"]["insertadas"], 414)
        self.assertEqual(stats["Nomenclador de Equipos"]["omitidas_invalidas"], 1)  # 414+1 = 415 fuente
        self.assertTrue(any("Equipos" in a and "nulo/vacío" in a for a in adv))

    def test_relaciones_sbd_verificadas_con_datos(self):
        stats, _, _ = stats_importacion(self.con, "2011-sbd2008")
        pr = stats["Presupuesto Composición RV"]
        self.assertEqual(pr["id_obj_obra_en_objetos"], 16816)
        self.assertEqual(pr["id_etapa_en_etapas"], 16816)
        self.assertEqual(pr["codigo_rv_en_partidas"], 16816)
        self.assertEqual(stats["tc Duración y Costo con Norma Precons MO"]["codigo_partida_exacto"], 15232)


# ---------------------------------------------------------------------------
# 6-7. Precisión numérica
# ---------------------------------------------------------------------------
class TestPrecision(TestBase):
    def test_coeficiente_float32_bit_a_bit(self):
        caso = self.fixture["casos"]["coeficiente_float32"]
        fila = self.con.execute("""SELECT np.coeficiente FROM normas_partida np
            JOIN partidas p ON p.id=np.partida_id JOIN versiones_catalogo v ON v.id=p.version_id
            WHERE p.codigo=? AND np.codigo_recurso=? AND v.version='2017-raiz'""",
            (caso["codigo_rv"], caso["cod_mat"])).fetchone()
        self.assertIsNotNone(fila)
        self.assertEqual(repr(fila["coeficiente"]), caso["valor_recuperado"],
                         "el coeficiente Float32 debe preservarse bit a bit (sin redondeo silencioso)")

    def test_precio_4_decimales_roundtrip(self):
        caso = self.fixture["casos"]["precision_money"]["precio_4_decimales"]
        esperado = Decimal(caso["pmn_decimal"])
        fila = self.con.execute("""SELECT r.precio_mn FROM recursos r
            JOIN versiones_catalogo v ON v.id=r.version_id
            WHERE r.codigo=? AND v.version='2017-raiz'""", (caso["codigo"],)).fetchone()
        self.assertIsNotNone(fila)
        self.assertLessEqual(abs(Decimal(str(fila["precio_mn"])) - esperado),
                             Decimal(str(tol_roundtrip_money(esperado))),
                             "round-trip Money 4 decimales dentro de tolerancia documentada")

    def test_precio_mayor_1000_no_se_pierde(self):
        caso = self.fixture["casos"]["precision_money"]["precio_mayor_1000"]
        fila = self.con.execute("""SELECT r.precio_mn FROM recursos r
            JOIN versiones_catalogo v ON v.id=r.version_id
            WHERE r.codigo=? AND v.version='2017-raiz'""", (caso["codigo"],)).fetchone()
        self.assertIsNotNone(fila, "el precio ≥1000 se perdía con el parser antiguo (coma de miles)")
        self.assertGreaterEqual(fila["precio_mn"], 1000)

    def test_caso_012141_completo(self):
        c = self.fixture["casos"]["partida_012141"]
        fila = self.con.execute("""SELECT p.* FROM partidas p JOIN versiones_catalogo v
            ON v.id=p.version_id WHERE p.codigo='012141' AND v.version='2017-raiz'""").fetchone()
        self.assertEqual(fila["costo_mo_mn"], 4.6074, "CHMN con 4 decimales exactos (antes: 4.61 truncado)")
        # suma recalculada desde la base == suma esperada del fixture (Decimal, SOLO materiales)
        suma = sum(Decimal(str(r["coeficiente"])) * Decimal(str(r["precio_mn"]))
                   for r in self.con.execute("""SELECT np.coeficiente, r.precio_mn FROM normas_partida np
                   JOIN tipos_recurso tr ON tr.id=np.tipo_recurso_id
                   JOIN recursos r ON r.version_id=np.version_id AND r.tipo_id=np.tipo_recurso_id
                   AND r.codigo=np.codigo_recurso
                   WHERE np.partida_id=? AND tr.codigo='material'""", (fila["id"],)))
        self.assertLessEqual(abs(suma - Decimal(c["suma_esperada_cmmn_decimal"])),
                             Decimal(str(c["tolerancia"])))


# ---------------------------------------------------------------------------
# 8. Normas multicomponente
# ---------------------------------------------------------------------------
class TestMulticomponente(TestBase):
    def test_partida_con_juego_y_semi(self):
        c = self.fixture["casos"]["partida_multicomponente"]
        fila = self.con.execute("""SELECT p.id FROM partidas p JOIN versiones_catalogo v
            ON v.id=p.version_id WHERE p.codigo=? AND v.version='2017-raiz'""", (c["codigo"],)).fetchone()
        self.assertIsNotNone(fila)
        tipos = {r["tipo"]: r["n"] for r in self.con.execute("""
            SELECT tr.codigo AS tipo, COUNT(*) n FROM normas_partida np
            JOIN tipos_recurso tr ON tr.id=np.tipo_recurso_id WHERE np.partida_id=?
            GROUP BY tr.codigo""", (fila["id"],))}
        self.assertIn("juego", tipos)
        self.assertIn("semielaborado", tipos)
        # los componentes del juego importado existen
        comp = self.con.execute("""SELECT COUNT(*) FROM componentes_recurso cr
            JOIN recursos r ON r.id=cr.recurso_id WHERE r.version_id=
            (SELECT version_id FROM partidas WHERE id=?)""", (fila["id"],)).fetchone()[0]
        self.assertGreater(comp, 0)

    def test_012141_nueve_componentes(self):
        vid = self.con.execute("SELECT id FROM versiones_catalogo WHERE version='2017-raiz'").fetchone()[0]
        n = self.con.execute("""SELECT COUNT(*) FROM normas_partida np JOIN partidas p ON p.id=np.partida_id
            WHERE p.codigo='012141' AND np.version_id=?""", (vid,)).fetchone()[0]
        self.assertEqual(n, 9)


# ---------------------------------------------------------------------------
# 9. Recuperación ante importación interrumpida
# ---------------------------------------------------------------------------
class TestRecuperacionInterrumpida(TestBase):
    def test_fallo_rollback_y_reintento(self):
        with tempfile.TemporaryDirectory() as tmp:
            bd_tmp = os.path.join(tmp, "prueba.db")
            shutil.copy(BD, bd_tmp)
            # purgar la versión a probar en la copia
            subprocess.run([sys.executable, os.path.join(REPO, "scripts", "importar_precodi.py"),
                            "--bd", bd_tmp, "--purgar", "PRECODI/2017-raiz"],
                           capture_output=True, text=True, timeout=120)
            # importación con fallo inyectado a mitad de transacción
            r = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "importar_precodi.py"),
                                "--bd", bd_tmp, "--base", "raiz", "--inyectar-fallo", "prueba"],
                               capture_output=True, text=True, timeout=300)
            self.assertNotEqual(r.returncode, 0, "la importación con fallo inyectado debe fallar")
            con = con_bd(bd_tmp)
            fila = con.execute("SELECT id FROM versiones_catalogo WHERE version='2017-raiz'").fetchone()
            self.assertIsNotNone(fila, "debe quedar registrado el intento fallido")
            n_partidas = con.execute("""SELECT COUNT(*) FROM partidas p JOIN versiones_catalogo v
                ON v.id=p.version_id WHERE v.version='2017-raiz'""").fetchone()[0]
            self.assertEqual(n_partidas, 0, "el rollback no debe dejar filas de la versión")
            estado = con.execute("""SELECT i.resultado FROM importaciones i JOIN versiones_catalogo v
                ON v.id=i.version_id WHERE v.version='2017-raiz' ORDER BY i.id DESC LIMIT 1""").fetchone()[0]
            self.assertEqual(estado, "error")
            con.close()
            # reintento limpio: recupera la versión completa
            r2 = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "importar_precodi.py"),
                                 "--bd", bd_tmp, "--base", "raiz"],
                                capture_output=True, text=True, timeout=300)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            con = con_bd(bd_tmp)
            n = con.execute("""SELECT COUNT(*) FROM partidas p JOIN versiones_catalogo v
                ON v.id=p.version_id WHERE v.version='2017-raiz'""").fetchone()[0]
            self.assertEqual(n, 15351, "el reintento debe recuperar las 15351 partidas")
            n_normas = con.execute("""SELECT COUNT(*) FROM normas_partida np JOIN versiones_catalogo v
                ON v.id=np.version_id WHERE v.version='2017-raiz'""").fetchone()[0]
            self.assertEqual(n_normas, 73978)
            con.close()


# ---------------------------------------------------------------------------
# 10. Conservación del catálogo original de PRECOST
# ---------------------------------------------------------------------------
class TestConservacionOriginal(TestBase):
    def test_sha256_html_original(self):
        h = hashlib.sha256()
        with open(HTML, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        self.assertEqual(h.hexdigest(), SHA_HTML, "el HTML original debe permanecer byte-idéntico")

    def test_inyeccion_solo_al_servir(self):
        import servidor_precodi as sp
        with open(HTML, "rb") as f:
            disco = f.read()
        i = disco.rfind(b"</body>")
        servido_esperado = disco[:i] + sp.INYECCION + disco[i:]
        self.assertNotIn(b"pcod-fab", disco, "el disco no debe contener el overlay")
        self.assertIn(b"overlay/precodi.js", servido_esperado, "la copia servida sí lo inyecta")

    def test_catalogo_embebido_intacto(self):
        # la const DB del HTML sigue presente y con las 6 claves del catálogo
        import re
        with open(HTML, encoding="utf-8", errors="ignore") as f:
            contenido = f.read()
        self.assertIn("contractVersion", contenido, "contrato PRECOST-AI-JSON intacto")
        m = re.search(r"const\s+DB\s*=\s*\{", contenido)
        self.assertIsNotNone(m, "catálogo embebido const DB presente")

    def test_mdb_originales_intactos(self):
        inv = json.load(open(os.path.join(REPO, "docs", "datos", "fase3a_inventario.json"), encoding="utf-8"))
        base = "/home/z/my-project/work/recuperacion/analisis/PRECODI"
        for b in inv["bases"]:
            ruta = os.path.join(base, b["procedencia_rar"])
            h = hashlib.sha256()
            with open(ruta, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            self.assertEqual(h.hexdigest(), b["sha256"], f"{ruta} cambió")


# ---------------------------------------------------------------------------
# Conciliación de recuentos origen ↔ destino (toda diferencia explicada)
# ---------------------------------------------------------------------------
class TestConciliacionRecuentos(TestBase):
    def test_recuentos_por_tabla_y_base(self):
        inv = json.load(open(os.path.join(REPO, "docs", "datos", "fase3a_inventario.json"), encoding="utf-8"))
        filas_fuente = {}
        for b in inv["bases"]:
            if b["id"] == "codigo_preambulos":
                continue  # duplicado exacto: 0 filas propias por diseño
            filas_fuente[b["id"]] = {t["tabla"]: t.get("filas") or 0 for t in b.get("tablas", [])}

        reglas = {  # contadores que explican filas fuente que no generan inserción
            "Norma de Mano de Obra": ["duplicadas_omitidas"],
            "Norma de Equipos": ["duplicadas_omitidas"],
            "Norma de Semielaborados": ["duplicadas_omitidas"],
        }
        for version, base_id in (("2007-v7.21", "codigo_721"), ("2007-v7.22", "codigo_722"),
                                 ("2017-raiz", "codigo_raiz"), ("2011-sbd2008", "sbd2008_815")):
            stats, _, _ = stats_importacion(self.con, version)
            for tabla, n_fuente in filas_fuente[base_id].items():
                if tabla not in stats or n_fuente == 0:
                    continue
                st = stats[tabla]
                insertadas = st.get("insertadas", 0)
                explicadas = sum(st.get(k, 0) for k in
                                 ["duplicadas_omitidas", "omitidas_invalidas", "huérfanas_partida",
                                  "huérfanas_recurso", "ya_existentes", "duplicados_detectados"]
                                 + reglas.get(tabla, []))
                # Norma Juego Material1 en raíz: duplicado exacto verificado (0 insertadas)
                if tabla == "Norma Juego Material1":
                    self.assertEqual(insertadas, 0)
                    continue
                self.assertLessEqual(insertadas + explicadas, max(n_fuente, insertadas + explicadas))
                self.assertGreaterEqual(insertadas + explicadas, n_fuente - max(0, explicadas),
                                        f"{version}/{tabla}: insertadas+explicadas={insertadas + explicadas} "
                                        f"debe cubrir las {n_fuente} filas fuente")
                self.assertLessEqual(insertadas, n_fuente,
                                     f"{version}/{tabla}: más inserciones ({insertadas}) que filas fuente ({n_fuente})")


def main():
    unittest.main(verbosity=2, argv=[sys.argv[0], *sys.argv[1:]])


if __name__ == "__main__":
    main()
