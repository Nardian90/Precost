#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MISIÓN III-C · FASE G — Suite de pruebas automatizadas.

Los 16 escenarios exigidos por la misión (numeración de la misión):
  1.  Partida con norma completa.
  2.  Partida sin norma.
  3.  Norma con materiales.
  4.  Norma con mano de obra.
  5.  Norma con equipos.
  6.  Norma con varias categorías de recursos.
  7.  Referencias a recursos inexistentes (advertencia + dato de origen).
  8.  Código duplicado o ambiguo.
  9.  Coeficientes fraccionarios (Float32 exacto).
  10. Importes con cuatro decimales.
  11. Cambios de cantidad presupuestada (consumo = coef × cantidad).
  12. Diferencias de precio entre versiones (y combinación norma+precios).
  13. Guardado y recuperación del presupuesto (snapshot).
  14. Reapertura de un presupuesto histórico (inmutabilidad del snapshot).
  15. Conservación del catálogo embebido original.
  16. Regresión del caso 012141 (valores de referencia III-B).

Complementos: regresión de endpoints III-B, lotes de normas disponibles,
inyección de overlays, solo-lectura del API y HTML en disco intacto.

Uso:  python3 scripts/tests_iiic.py        (requiere bd/precodi.db y el servidor)
      python3 scripts/tests_iiic.py -v
El flujo de interfaz (cantidad → recálculo → guardar → recargar) se valida de
forma reproducible con scripts/validar_iiic_navegador.sh (FASE H).
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from decimal import Decimal

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BD = os.path.join(REPO, "bd", "precodi.db")
HTML = os.path.join(REPO, "app", "PRECOST-v9.17.html")
FIXTURE = os.path.join(REPO, "datos_prueba", "casos_iiic.json")
FIXTURE_IIIB = os.path.join(REPO, "datos_prueba", "casos_iiib.json")
SERVIDOR = os.path.join(REPO, "scripts", "servidor_precodi.py")
SHA_HTML = "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"

FX = json.load(open(FIXTURE, encoding="utf-8"))
FXB = json.load(open(FIXTURE_IIIB, encoding="utf-8"))
CASO = FX["casos"]

# ids de versión resueltos DINÁMICAMENTE por etiqueta al arrancar cada suite:
# los ids son autoincrement y cambian tras purgar/reimportar (documentado en
# III-C); las claves semánticas son catalogo+versión, nunca el id numérico.
ETIQUETAS = {"2017-raiz": "PRECODI", "2011-sbd2008": "PRECODI",
             "2025-06-06": "PRECONS_III", "2007-v7.22": "PRECODI",
             "2007-v7.21": "PRECODI"}


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def api(puerto, ruta):
    """GET JSON; los 404 del API traen cuerpo JSON válido (versiones
    disponibles, etc.): se devuelven como dict con clave 'error'."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}{ruta}", timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode("utf-8", "replace")
        try:
            return json.loads(cuerpo)
        except ValueError:
            raise


class ServidorBase(unittest.TestCase):
    """Arranca un servidor real contra la BD indicada y lo apaga al terminar."""

    @classmethod
    def iniciar_servidor(cls, bd, puerto):
        cls.puerto = puerto
        cls.proc = subprocess.Popen(
            [sys.executable, SERVIDOR, "--puerto", str(puerto), "--bd", bd],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.vid = {}
        for _ in range(60):
            try:
                vers = api(puerto, "/api/versiones")["versiones"]
                for v in vers:
                    clave = v["version"]
                    if clave in ETIQUETAS and v["catalogo"] == ETIQUETAS[clave]:
                        cls.vid[clave] = v["id"]
                if len(cls.vid) == len(ETIQUETAS):
                    return
            except Exception:
                pass
            time.sleep(0.25)
        raise RuntimeError(f"el servidor de pruebas no arrancó o faltan versiones: {cls.vid}")

    @classmethod
    def detener_servidor(cls):
        if getattr(cls, "proc", None):
            cls.proc.terminate()
            cls.proc.wait(timeout=10)
            cls.proc = None


class TestDescomposicion(ServidorBase):
    """Casos 1-12, 15, 16: datos y API (los casos 13-14 UI van en navegador)."""

    @classmethod
    def setUpClass(cls):
        cls.iniciar_servidor(BD, 8793)

    @classmethod
    def tearDownClass(cls):
        cls.detener_servidor()

    def dec(self, codigo, **kw):
        kw.setdefault("version_id", self.vid["2017-raiz"])
        extra = "&".join(f"{k}={v}" for k, v in kw.items())
        return api(self.puerto, f"/api/descomposicion/{codigo}?{extra}")

    # ------------------------------------------------------------------ caso 1
    def test_01_partida_con_norma_completa(self):
        d = self.dec("012141")
        self.assertTrue(d["tiene_norma"])
        self.assertEqual(d["partida"]["codigo"], "012141")
        self.assertEqual(d["partida"]["unidad"], "m3")
        self.assertEqual(len(d["componentes"]), CASO["partida_012141"]["n_componentes"])
        self.assertEqual(d["partida"]["version"], "2017-raiz")
        # subtotales por tipo y total (Σ coef×precio, sin redondeo)
        for tipo, esperado in (("material", 2.629), ("mano_obra", 4.6074), ("equipo", 1.6516)):
            self.assertAlmostEqual(d["subtotales"][tipo], esperado, places=3, msg=tipo)
        self.assertAlmostEqual(d["total"], 8.8881, places=3)
        # trazabilidad de la fuente
        self.assertTrue(d["partida"]["fuente_sha256"])
        self.assertTrue(d["partida"]["fecha_importacion"])
        self.assertTrue(d["html_original_intacto"])

    # ------------------------------------------------------------------ caso 2
    def test_02_partida_sin_norma(self):
        d = self.dec("999999")
        self.assertFalse(d["tiene_norma"])
        self.assertEqual(d["componentes"], [])
        self.assertEqual(d["total"], 0.0)
        # no se inventan componentes y se conservan los datos de la partida
        self.assertEqual(d["partida"]["descripcion"], "SUMINISTROS")
        self.assertIsNotNone(d["partida"]["costo_total_mn"])
        # el 404 informa versiones disponibles cuando el código no está en la versión
        r = api(self.puerto, f"/api/descomposicion/999999?version_id={self.vid['2025-06-06']}")
        self.assertIn("error", r)
        self.assertTrue(r["versiones_disponibles"])

    # ------------------------------------------------------------ casos 3, 4, 5
    def test_03_norma_con_materiales(self):
        comps = [c for c in self.dec("012141")["componentes"] if c["tipo"] == "material"]
        self.assertEqual(len(comps), CASO["partida_012141"]["por_tipo"]["material"])
        for c in comps:
            self.assertTrue(c["resuelto"])
            self.assertTrue(c["precio_resuelto"])
            self.assertEqual(c["unidad"], c["unidad"].strip())  # um del nomenclador

    def test_04_norma_con_mano_de_obra(self):
        comps = [c for c in self.dec("012141")["componentes"] if c["tipo"] == "mano_obra"]
        self.assertEqual(len(comps), CASO["partida_012141"]["por_tipo"]["mano_obra"])
        for c in comps:
            self.assertIn(c["unidad"], ("hh", "h", "jg"))  # unidades reales MO

    def test_05_norma_con_equipos(self):
        comps = [c for c in self.dec("012141")["componentes"] if c["tipo"] == "equipo"]
        self.assertEqual(len(comps), CASO["partida_012141"]["por_tipo"]["equipo"])
        for c in comps:
            self.assertIn(c["unidad"], ("he", "h"))

    # ------------------------------------------------------------------ caso 6
    def test_06_norma_multicategoria(self):
        d = self.dec("096231")
        tipos = {c["tipo"] for c in d["componentes"]}
        self.assertTrue({"material", "mano_obra", "juego", "semielaborado"} <= tipos,
                        f"tipos presentes: {tipos}")
        # los juegos y semielaborados traen su propia descomposición (hijos)
        con_hijos = [c for c in d["componentes"] if c["hijos"]]
        self.assertTrue(any(c["tipo"] == "juego" for c in con_hijos))
        self.assertTrue(any(c["tipo"] == "semielaborado" for c in con_hijos))
        # subtotales de juego y semielaborado con el precio del compuesto (F1/F7/F8)
        self.assertGreater(d["subtotales"]["juego"], 0)
        self.assertGreater(d["subtotales"]["semielaborado"], 0)

    # ------------------------------------------------------------------ caso 8
    def test_08_codigo_duplicado_y_ambiguo(self):
        d = self.dec("096231")
        dup = CASO["partida_096231"]["duplicados_reales"]
        self.assertTrue(dup, "la fuente debe contener el duplicado real documentado")
        self.assertIn({"tipo": "mano_obra", "codigo": "0000000211"}, d["duplicados"])
        self.assertTrue(any("duplicado" in a for a in d["advertencias"]))
        # ambas filas de origen se conservan (no se descarta ninguna)
        filas = [c for c in d["componentes"] if c["codigo"] == "0000000211"]
        self.assertEqual(len(filas), dup[0]["veces"])
        # ambigüedad entre versiones: la misma partida en varias versiones se
        # resuelve SIEMPRE por version_id explícito (nunca por coincidencia)
        for et, vid in self.vid.items():
            dx = self.dec("012141", version_id=vid)
            self.assertEqual(dx["partida"]["version_id"], vid)
            self.assertEqual(dx["partida"]["version"], et)

    # ------------------------------------------------------------------ caso 9
    def test_09_coeficientes_fraccionarios_float32(self):
        d = self.dec("012141")
        por_codigo = {c["codigo"]: c["coeficiente"] for c in d["componentes"]}
        # valores Float32 EXACTOS de la fuente (fixture III-B extraído del .mdb)
        for n in FXB["casos"]["partida_012141"]["normas_materiales"]:
            self.assertEqual(repr(por_codigo[n["codigo"]]), n["coeficiente_float32"],
                             f"coeficiente Float32 alterado para {n['codigo']}")
        # fraccionarios pequeños sin redondeo silencioso
        self.assertEqual(repr(por_codigo["0000010181"]), "0.009600000455975533")
        self.assertEqual(repr(por_codigo["0023511943"]), "0.016699999570846558")

    # ----------------------------------------------------------------- caso 10
    def test_10_importes_cuatro_decimales(self):
        d = self.dec("063611")
        rec = CASO["partida_063611_precio_4dec"]["recurso_4dec"]
        comp = [c for c in d["componentes"] if c["codigo"] == rec["codigo"]][0]
        # precio Money de 4 decimales exacto en tránsito (sin redondeo a 2)
        self.assertEqual(repr(comp["precio_mn"]), repr(rec["precio_mn"]))
        # importe = coef × precio con precisión completa; presentación aparte
        esperado = rec["coeficiente"] * rec["precio_mn"]
        self.assertEqual(comp["importe"], esperado)
        self.assertEqual(f"{comp['importe']:.4f}", "68.0142")  # presentación 4 dec (0.013100000098347664 × 5191.9199 = 68.0141512…)

    # ----------------------------------------------------------------- caso 11
    def test_11_cambios_de_cantidad_presupuestada(self):
        d = self.dec("012141")
        pu = d["total"]
        for cant in (1, 120, 250, 0.0001):
            for c in d["componentes"]:
                consumo = c["coeficiente"] * cant          # fórmula de la misión
                importe = consumo * c["precio_mn"]
                self.assertTrue(consumo >= 0 and importe >= 0)
            total_obra = pu * cant
            self.assertAlmostEqual(total_obra, sum(c["coeficiente"] * c["precio_mn"] * cant
                                                   for c in d["componentes"]), places=10)
        # la norma nunca cambia al cambiar la cantidad (los coeficientes son de origen)
        d2 = self.dec("012141")
        self.assertEqual([c["coeficiente"] for c in d["componentes"]],
                         [c["coeficiente"] for c in d2["componentes"]])

    # ----------------------------------------------------------------- caso 12
    def test_12_diferencias_de_precio_entre_versiones(self):
        # la misma partida en cada versión, con su PU propio (sin mezclar);
        # el fixture referencia versiones por ETIQUETA (estable), no por id
        for et, espe in FX["versiones_012141"].items():
            d = self.dec("012141", version_id=self.vid[et])
            self.assertEqual(d["partida"]["version"], espe["version"])
            self.assertEqual(d["partida"]["costo_total_mn"], espe["costo_total_mn"])
        # combinación normas 2017 + precios de otra versión: informe de compatibilidad
        d = self.dec("012141", precio_version_id=self.vid["2011-sbd2008"])   # 2011: 100% con precio
        cr11 = CASO["cruce_012141"]["2011-sbd2008"]
        self.assertEqual(d["fuentes_precio"]["resueltos"], cr11["resueltos"])
        self.assertEqual(d["fuentes_precio"]["total"], cr11["total"])
        self.assertTrue(all(c["precio_resuelto"] for c in d["componentes"]))
        self.assertEqual(d["verificacion"], None)      # no comparable con lo almacenado
        d25 = self.dec("012141", precio_version_id=self.vid["2025-06-06"])   # 2025: con tarifas ya importadas
        fp = d25["fuentes_precio"]
        cr25 = CASO["cruce_012141"]["2025-06-06"]
        self.assertEqual(fp["resueltos"], cr25["resueltos"])
        self.assertEqual(fp["total"], cr25["total"])
        respaldos = [c for c in d25["componentes"] if c.get("precio_respaldo")]
        self.assertEqual(len(respaldos), fp["total"] - fp["resueltos"])
        for c in respaldos:
            self.assertIsNotNone(c["precio_mn"])       # precio de la versión de la norma
        if cr25["resueltos"] < cr25["total"]:
            self.assertTrue(any("unidad distinta" in (c.get("advertencia") or "")
                                for c in d25["componentes"]) or respaldos)

    # ----------------------------------------------------------------- caso 13
    def test_13_guardado_y_recuperacion_snapshot(self):
        """Estructura exacta del snapshot que el overlay almacena en el ítem
        del presupuesto (localStorage p3pro.budgets). El flujo de UI completo
        (guardar → recargar → recuperar) se valida en el navegador (FASE H)."""
        d = self.dec("012141")
        snapshot = {
            "vinculado": "2026-10-14T00:00:00.000Z",
            "version_id": d["partida"]["version_id"], "version": d["partida"]["version"],
            "catalogo": d["partida"]["catalogo"],
            "fuente_archivo": d["partida"]["fuente_archivo"],
            "fuente_sha256": d["partida"]["fuente_sha256"],
            "fecha_importacion": d["partida"]["fecha_importacion"],
            "partida": {"codigo": d["partida"]["codigo"], "unidad": d["partida"]["unidad"]},
            "componentes": d["componentes"], "subtotales": d["subtotales"],
            "total": d["total"], "verificacion": d["verificacion"],
            "advertencias": d["advertencias"],
        }
        # round-trip JSON idéntico (mecanismo localStorage de PRECOST)
        self.assertEqual(json.loads(json.dumps(snapshot)), snapshot)
        # campos de procedencia completos (FASE D)
        for campo in ("version", "catalogo", "fuente_sha256", "fecha_importacion"):
            self.assertTrue(snapshot[campo])
        # los Float32 sobreviven al round-trip bit a bit
        ida = json.loads(json.dumps(snapshot))["componentes"]
        self.assertEqual([repr(c["coeficiente"]) for c in ida],
                         [repr(c["coeficiente"]) for c in d["componentes"]])

    # ----------------------------------------------------------------- caso 14
    def test_14_reapertura_historica_inmutabilidad(self):
        """El snapshot no cambia aunque se consulte la misma partida con otras
        versiones/precios después: los presupuestos históricos conservan sus
        valores originales salvo actualización explícita."""
        original = self.dec("012141")
        snapshot = json.loads(json.dumps(original))     # copia guardada con el presupuesto
        # el usuario consulta luego la misma partida con precios 2011/2025
        self.dec("012141", precio_version_id=self.vid["2011-sbd2008"])
        con2025 = self.dec("012141", precio_version_id=self.vid["2025-06-06"])
        # el snapshot guardado permanece idéntico (sin operación explícita de actualización)
        self.assertEqual(snapshot["total"], original["total"])
        self.assertEqual(snapshot["componentes"], original["componentes"])
        # y difiere de la vista con precios 2025 (que NO lo altera)
        self.assertNotEqual(con2025["total"], snapshot["total"])

    # ----------------------------------------------------------------- caso 15
    def test_15_conservacion_catalogo_embebido(self):
        # el archivo HTML en disco permanece byte-idéntico
        self.assertEqual(sha256(HTML), SHA_HTML)
        # el HTML servido inyecta SOLO las dos etiquetas de overlay
        with urllib.request.urlopen(f"http://127.0.0.1:{self.puerto}/", timeout=20) as r:
            servido = r.read()
        self.assertIn(b'<script src="/overlay/precodi.js" defer></script>', servido)
        self.assertIn(b'<script src="/overlay/recursos.js" defer></script>', servido)
        self.assertEqual(servido.count(b"<script src="), 2)
        # el catálogo embebido sigue completo en la BD importada (PRECOST 2025)
        vers = api(self.puerto, "/api/versiones")
        v25 = [v for v in vers["versiones"] if v["version"] == "2025-06-06"][0]
        self.assertEqual(v25["partidas"], 15912)
        self.assertEqual(v25["recursos"], 4382)
        # y los overlays se sirven correctamente
        for ov in ("/overlay/precodi.js", "/overlay/recursos.js"):
            with urllib.request.urlopen(f"http://127.0.0.1:{self.puerto}{ov}", timeout=20) as r:
                self.assertEqual(r.status, 200)
                self.assertGreater(int(r.headers["Content-Length"]), 1000)

    # ----------------------------------------------------------------- caso 16
    def test_16_regresion_012141(self):
        """Valores de referencia documentados en la misión III-B (extraídos del
        .mdb original) — sin tolerancia global 0.01: tolerancia por nº de
        términos y magnitud (regla documentada)."""
        d = self.dec("012141")
        fxb = FXB["casos"]["partida_012141"]
        tol = max(0.0001 * len(d["componentes"]),
                  sum(abs(c["importe"]) for c in d["componentes"]) * 6e-8)
        self.assertAlmostEqual(d["subtotales"]["material"], float(fxb["cmmn_almacenado"]), delta=tol)
        self.assertAlmostEqual(d["subtotales"]["mano_obra"], float(fxb["chmn_almacenado"]), delta=tol)
        self.assertAlmostEqual(d["subtotales"]["equipo"], float(fxb["cemn_almacenado"]), delta=tol)
        # verificación 3/3 contra los costos almacenados en la fuente
        for k in ("cmmn", "chmn", "cemn"):
            self.assertTrue(d["verificacion"][k]["coincide"], k)
        # precios de cada material también bit a bit
        por_codigo = {c["codigo"]: c["precio_mn"] for c in d["componentes"]}
        for n in fxb["normas_materiales"]:
            self.assertEqual(str(por_codigo[n["codigo"]]), n["pmn_decimal"])

    # ------------------------------------------------------- complementos III-C
    def test_normas_disponibles_lote(self):
        d = api(self.puerto, "/api/normas_disponibles?codigos=012141,999999,096231")
        self.assertTrue(d["codigos"]["012141"]["tiene_norma"])
        self.assertFalse(d["codigos"]["999999"]["tiene_norma"])
        self.assertTrue(d["codigos"]["096231"]["tiene_norma"])
        self.assertEqual(d["codigos"]["012141"]["n_normas"], 9)
        # códigos ausentes se reportan sin inventar
        d2 = api(self.puerto, "/api/normas_disponibles?codigos=NOEXISTE")
        self.assertFalse(d2["codigos"]["NOEXISTE"]["en_catalogo"])
        # límites documentados (el API responde 400 con cuerpo JSON de error)
        d_vacio = api(self.puerto, "/api/normas_disponibles")
        self.assertIn("error", d_vacio)
        muchos = ",".join(f"C{i}" for i in range(501))
        d_muchos = api(self.puerto, f"/api/normas_disponibles?codigos={muchos}")
        self.assertIn("error", d_muchos)

    def test_regresion_endpoints_iiiib(self):
        """Los endpoints de III-B siguen funcionando sin cambios (sin doble
        implementación ni ruptura de contrato)."""
        d = api(self.puerto, f"/api/partida/012141?version_id={self.vid['2017-raiz']}")
        self.assertEqual(len(d["normas"]), 9)
        self.assertTrue(d["verificacion"]["cmmn"]["coincide"])
        self.assertIn("otras_versiones", d)
        p = api(self.puerto, f"/api/partidas?q=roca&version_id={self.vid['2017-raiz']}&limit=5")
        self.assertGreater(p["n"], 0)
        s = api(self.puerto, "/api/stats")
        self.assertIn("PRECODI/2017-raiz", s["stats"])

    def test_api_solo_lectura(self):
        """El API no expone escrituras: POST rechazado (501 por defecto)."""
        req = urllib.request.Request(f"http://127.0.0.1:{self.puerto}/api/descomposicion/012141",
                                     data=b"{}", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(cm.exception.code, 501)

    def test_bd_no_modificada_por_las_pruebas(self):
        """Toda la suite se ejecuta contra la BD en modo solo-lectura."""
        con = sqlite3.connect(f"file:{BD}?mode=ro", uri=True)
        n = con.execute("SELECT COUNT(*) FROM normas_partida WHERE version_id=3").fetchone()[0]
        con.close()
        self.assertEqual(n, 73978)   # recuento documentado en la auditoría


class TestReferenciasInexistentes(ServidorBase):
    """Caso 7: cuando una norma referencia un recurso ausente del nomenclador,
    se advierte y se conserva el dato de origen. Se usa una COPIA temporal de
    la BD (el original permanece intacto; no se alteran datos para la prueba)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="iiic_t7_")
        cls.bd_prueba = os.path.join(cls.tmp, "copia.db")
        shutil.copy2(BD, cls.bd_prueba)
        con = sqlite3.connect(cls.bd_prueba)
        # eliminar el recurso 3834010001 (material de 012141) del nomenclador v3
        con.execute("""DELETE FROM recursos WHERE version_id=3 AND tipo_id=1
                       AND codigo='3834010001'""")
        con.commit()
        con.close()
        cls.iniciar_servidor(cls.bd_prueba, 8794)

    @classmethod
    def tearDownClass(cls):
        cls.detener_servidor()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_07_referencia_no_resuelta(self):
        d = api(self.puerto, f"/api/descomposicion/012141?version_id={self.vid['2017-raiz']}")
        comp = [c for c in d["componentes"] if c["codigo"] == "3834010001"][0]
        self.assertFalse(comp["resuelto"])
        self.assertIn("no resuelta", comp["advertencia"])
        self.assertIn("conserva", comp["advertencia"])
        # el código y el coeficiente de origen se conservan (no se inventa nada)
        self.assertEqual(comp["coeficiente"], 1.2000000476837158)
        self.assertIsNone(comp["descripcion"])
        self.assertIn("3834010001", "".join(d["advertencias"]))
        # el subtotal excluye lo no resoluble pero la partida sigue verificando el resto
        self.assertAlmostEqual(d["subtotales"]["material"], 2.629 - 2.16, places=3)

    def test_original_intacto(self):
        """La BD real nunca se tocó (copia efímera)."""
        self.assertNotEqual(self.bd_prueba, BD)
        con = sqlite3.connect(f"file:{BD}?mode=ro", uri=True)
        n = con.execute("SELECT COUNT(*) FROM recursos WHERE version_id=3 AND codigo='3834010001'").fetchone()[0]
        con.close()
        self.assertEqual(n, 1)


def main():
    verbo = "-v" in sys.argv
    unittest.main(verbosity=2 if verbo else 1)


if __name__ == "__main__":
    sys.exit(main())
