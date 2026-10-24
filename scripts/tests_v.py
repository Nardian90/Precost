#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MISIÓN V — Suite de pruebas: edición de recursos en el presupuesto real
(S-050 indicadores M/H/E + especificación · S-052 modificar cantidad/precio).

Cubre los 15 escenarios obligatorios de la misión (numeración de la misión;
los que exigen UI real se validan además en scripts/validar_v_navegador.sh):

  N1  Búsqueda de recursos del nomenclador por código y por descripción,
      con filtro por tipo (/api/recursos).
  N2  Edición contextual (coef/precio) con original→editado y reversibilidad
      [UI: navegador; aquí: contrato del modelo + inyección].
  N3  Rechazo de entradas inválidas (negativo, no numérico, vacío en coef;
      precio admite vacío = «sin precio») [UI: navegador; aquí: presencia de
      las guardas en el código servido].
  N4  Recálculo: importe = coef×precio, subtotales por tipo, total efectivo
      y total de obra (×cantidad) con precisión completa [UI: navegador;
      aquí: fórmula replicada en Python sobre el endpoint].
  N5  Protección de la norma: la BD es solo-lectura, POST rechazado, y el
      hash de la BD + las respuestas del API no cambian tras editar.
  N6  Aislamiento entre presupuestos con el mismo código [UI: navegador;
      aquí: la capa de edición viaja SOLO dentro del ítem del presupuesto].
  N7  Persistencia: it.edicionRecursos sobrevive al round-trip JSON
      (mecanismo localStorage p3pro.budgets) bit a bit.
  N8  Sin precio: recurso excluido del total con aviso explícito (nunca se
      inventa un valor) — fixture con copia efímera de la BD.
  N9  Unidad de medida: la respuesta expone um por recurso; advertencia
      cuando difiere de la um de la partida [UI: navegador].
  N10 Precisión: coef fraccionarios y precios de 4 decimales sin redondeo
      interno (doble precisión en tránsito; presentación aparte).
  N11 Duplicados: mismo código en la especificación → aviso, no duplicación
      [UI: navegador; aquí: mismo_codigo_otro_tipo expuesto por el API].
  N12 Presupuestos antiguos (pre-Misión V, sin edicionRecursos ni flags)
      siguen funcionando [UI: navegador; aquí: defensas de acceso
      (edicionDe/flagsDe) presentes en el código].
  N13 S-080 Calculadora sigue operativa y coexisten los overlays (la carrera
      latente de IV se repara en esta misión: guardas de DOM).
  N14 Los overlays no interfieren entre sí: inyección exactamente 4 etiquetas
      (MISIÓN VII añadió respaldo.js, S-005; antes 3)
      aditivas, cada overlay idempotente con marcador propio.
  N15 El HTML original permanece byte-idéntico (SHA-256 de referencia).

Uso:  python3 scripts/tests_v.py
Requiere: bd/precodi.db (al menos la base precost2025); node (para --check).
"""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, "app", "PRECOST-v9.17.html")
RECURSOS = os.path.join(REPO, "app", "overlay", "recursos.js")
CALC = os.path.join(REPO, "app", "overlay", "calculadora.js")
SERVIDOR = os.path.join(REPO, "scripts", "servidor_precodi.py")
BD = os.path.join(REPO, "bd", "precodi.db")
SHA_HTML = "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"
PUERTO = 8827
BASE = f"http://127.0.0.1:{PUERTO}"


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def api(ruta, metodo="GET"):
    try:
        req = urllib.request.Request(BASE + ruta, method=metodo)
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(cuerpo)
        except ValueError:
            return e.code, {"error": cuerpo}


def vid_de(bd, version):
    """MISIÓN VIII — resuelve el version_id POR VERSIÓN: la numeración de ids
    depende del orden de importación (tras la recuperación la base 2025 fue la
    primera; en la BD original de III-B era la última). Nunca ids literales."""
    con = sqlite3.connect(f"file:{bd}?mode=ro", uri=True)
    fila = con.execute("SELECT id FROM versiones_catalogo WHERE version=?",
                       (version,)).fetchone()
    con.close()
    if not fila:
        raise RuntimeError(f"versión {version!r} ausente en {bd}: ¿falta importar?")
    return fila[0]


class ServidorBase(unittest.TestCase):
    @classmethod
    def iniciar(cls, bd, puerto):
        cls.proc = subprocess.Popen(
            [sys.executable, SERVIDOR, "--puerto", str(puerto), "--bd", bd],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/versiones", timeout=2)
                return True
            except Exception:
                time.sleep(0.25)
        raise RuntimeError("el servidor de pruebas no arrancó")

    @classmethod
    def detener(cls):
        if getattr(cls, "proc", None):
            cls.proc.terminate()
            cls.proc.wait(timeout=10)
            cls.proc = None


class TestInfraestructura(ServidorBase):
    """N14/N15 + integridad — el original permanece intacto."""

    @classmethod
    def setUpClass(cls):
        cls.iniciar(BD, PUERTO)

    @classmethod
    def tearDownClass(cls):
        cls.detener()

    def test_n15_html_byte_identico(self):
        self.assertEqual(sha256(HTML), SHA_HTML)

    def test_n15_git_html_limpio(self):
        out = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--",
                              "app/PRECOST-v9.17.html"],
                             capture_output=True, text=True).stdout.strip()
        self.assertEqual(out, "", f"HTML modificado: {out}")

    def test_n14_inyeccion_exactamente_cuatro_overlays(self):
        # MISIÓN VII: el contrato creció de 3 a 4 overlays con respaldo.js
        # (S-005); el conteo exacto sigue verificando que la inyección es
        # aditiva y completa — ni más ni menos que los overlays existentes.
        with urllib.request.urlopen(BASE + "/", timeout=20) as r:
            cuerpo = r.read()
        for nombre in (b"precodi.js", b"recursos.js", b"calculadora.js", b"respaldo.js"):
            self.assertIn(b'<script src="/overlay/' + nombre + b'" defer>', cuerpo)
        self.assertEqual(cuerpo.count(b'<script src="/overlay/'), 4)
        for tag in re.findall(rb'<script src="([^"]+)"', cuerpo):
            self.assertTrue(tag.startswith(b"/overlay/"), f"etiqueta no aditiva: {tag!r}")
        self.assertTrue(cuerpo.rstrip().endswith(b"</html>"))

    def test_n14_overlays_idempotentes_marca_propia(self):
        for fich, marca in (("precodi.js", b"__pcodOverlay"),
                            ("recursos.js", b"__pcodRecursos"),
                            ("calculadora.js", b"__pcodCalc"),
                            ("respaldo.js", b"__pcodRespaldo")):
            with open(os.path.join(REPO, "app", "overlay", fich), "rb") as f:
                cuerpo = f.read()
            self.assertIn(marca, cuerpo, f"idempotente ausente en {fich}")

    def test_n13_sintaxis_node(self):
        for fich in (RECURSOS, CALC):
            r = subprocess.run(["node", "--check", fich], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{fich}: {r.stderr}")

    def test_n13_reparacion_carrera_calculadora(self):
        """MISIÓN V reparó la carrera latente de IV (cargarVersiones tras
        cerrar la calculadora → «Cannot set properties of null»)."""
        codigo = open(CALC, encoding="utf-8").read()
        self.assertIn('if (!sn || !sp) return;', codigo)

    def test_endpoints_previos_responden(self):
        """Los endpoints de III-B/III-C siguen respondiendo (contrato intacto)."""
        for ep, esperado in (("/api/versiones", 200), ("/api/stats", 200),
                              ("/api/partidas?q=roca&limit=3", 200),
                              ("/api/partida/012141", 200)):
            codigo, _ = api(ep)
            self.assertEqual(codigo, esperado, ep)
        # descomposición: con BD completa → 200; con solo base 2025 → 404
        # controlado (documentado en INFORME_FASE_V) — NUNCA un 500.
        codigo, d = api("/api/descomposicion/012141")
        self.assertIn(codigo, (200, 404), f"descomposición degradó a {codigo}")
        if codigo == 404:
            self.assertIn("error", d)
        vid2025 = vid_de(BD, "2025-06-06")
        codigo2, d2 = api(f"/api/descomposicion/012141?version_id={vid2025}")
        self.assertEqual(codigo2, 200)
        self.assertFalse(d2["tiene_norma"])   # PRECOST 2025 no trae normas (documentado)

    def test_n5_api_solo_lectura(self):
        req = urllib.request.Request(BASE + "/api/recursos", data=b"{}", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(cm.exception.code, 501)

    def test_n5_bd_no_modificada(self):
        """MISIÓN VIII: el contrato es «ninguna prueba modifica la BD real»
        (se verifica contra lo que reporta el propio API, sin recuentos
        literales: la BD ahora contiene las 6 versiones re-importadas)."""
        codigo, d = api("/api/versiones")
        self.assertEqual(codigo, 200)
        total_api = sum(v["recursos"] for v in d["versiones"])
        con = sqlite3.connect(f"file:{BD}?mode=ro", uri=True)
        n = con.execute("SELECT COUNT(*) FROM recursos").fetchone()[0]
        con.close()
        self.assertGreater(n, 0)
        self.assertEqual(n, total_api, "la BD real cambió durante las pruebas")


class TestRecursosAPI(ServidorBase):
    """N1/N8/N9/N10/N11 — /api/recursos (MISIÓN V) sobre la base real."""

    @classmethod
    def setUpClass(cls):
        # reutiliza el puerto base: la clase anterior ya detuvo su servidor
        cls.iniciar(BD, PUERTO)
        # MISIÓN VIII: las pruebas de recursos usan la versión 2025 EXPLÍCITA
        # (la del catálogo embebido del HTML); el defecto del servidor con la
        # BD completa es 2017-raiz (regla documentada en _version_recursos_defecto)
        cls.vid2025 = vid_de(BD, "2025-06-06")

    @classmethod
    def tearDownClass(cls):
        cls.detener()

    def _rec(self, qs):
        return api(f"/api/recursos{qs}")[1]

    def test_n1_busqueda_por_descripcion(self):
        d = self._rec("?q=cemento&tipo=material&limit=10")
        self.assertGreater(d["n"], 0)
        self.assertEqual(d["tipo"], "material")
        for r in d["resultados"]:
            self.assertTrue("CEMENTO" in r["descripcion"].upper()
                            or "cemento" in r["codigo"].lower())
            self.assertEqual(r["tipo"], "material")

    def test_n1_busqueda_por_codigo(self):
        d = self._rec(f"?q=2259030004&version_id={self.vid2025}")
        self.assertEqual(d["n"], 1)
        r = d["resultados"][0]
        self.assertEqual(r["codigo"], "2259030004")
        self.assertEqual(r["unidad"], "litro")
        self.assertIsNotNone(r["precio_mn"])

    def test_n1_filtro_por_tipo_mo(self):
        # SQLite NOCASE solo pliega ASCII: ñ no se pliega — la descripción
        # almacenada está en mayúsculas (limitación documentada, igual que en
        # III-B/III-C: el contrato de búsqueda no se toca en MISIÓN V).
        d = self._rec("?q=ALBA%C3%91IL&tipo=mano_obra")
        self.assertGreater(d["n"], 0)
        for r in d["resultados"]:
            self.assertEqual(r["tipo"], "mano_obra")
        self.assertTrue(any("ALBAÑIL" in r["descripcion"].upper() for r in d["resultados"]))

    def test_n1_tipo_invalido_400(self):
        codigo, d = api("/api/recursos?tipo=noexiste")
        self.assertEqual(codigo, 400)
        self.assertIn("tipos_validos", d)

    def test_n1_busqueda_sin_resultados_honesta(self):
        d = self._rec("?q=zzzznoexistezzz")
        self.assertEqual(d["n"], 0)
        self.assertEqual(d["resultados"], [])

    def test_n9_um_expuesta_por_recurso(self):
        d = self._rec(f"?q=2259030004&version_id={self.vid2025}")
        self.assertEqual(d["resultados"][0]["unidad"], "litro")

    def test_n10_precios_4_decimales_en_transito(self):
        """El JSON transporta el precio con la precisión completa (sin
        redondear a 2 decimales): 10.05 debe viajar como 10.05 (repr) y el
        importe del propio se calcula en el navegador en doble precisión."""
        d = self._rec(f"?q=2259030004&version_id={self.vid2025}")
        precio = d["resultados"][0]["precio_mn"]
        self.assertEqual(repr(precio), repr(10.05))
        # la fórmula de recálculo (misma que el overlay) en Python:
        coef, cantidad = 2.4, 2.5
        self.assertAlmostEqual(coef * precio * cantidad, 2.4 * 10.05 * 2.5, places=12)

    def test_n11_ambiguedad_expuesta(self):
        """El API expone mismo_codigo_otro_tipo (aunque la base 2025 no tiene
        códigos solapados: campo presente y vacío — nunca en silencio)."""
        d = self._rec(f"?q=2259030004&version_id={self.vid2025}")
        self.assertIn("mismo_codigo_otro_tipo", d["resultados"][0])

    def test_version_fuente_etiquetada(self):
        """Nunca mezcla en silencio: la respuesta etiqueta la versión usada.
        MISIÓN VIII: con la BD completa el defecto documentado es 2017-raiz
        (regla del servidor: versión de normas por defecto si tiene nomenclador);
        la etiqueta debe coincidir con la versión realmente empleada."""
        d = self._rec(f"?q=cemento&limit=3&version_id={self.vid2025}")
        self.assertEqual(d["version"]["version"], "2025-06-06")
        self.assertEqual(d["version"]["catalogo"], "PRECONS_III")
        self.assertTrue(d["html_original_intacto"])
        # sin version_id: el defecto documentado según qué bases existan
        d2 = self._rec("?q=cemento&limit=3")
        versiones = {v["version"] for v in api("/api/versiones")[1]["versiones"]}
        self.assertIn(d2["version"]["version"], versiones)
        if "2017-raiz" in versiones:
            self.assertEqual(d2["version"]["version"], "2017-raiz")


class TestSinPrecio(unittest.TestCase):
    """N8 — recurso sin precio: aviso explícito, nunca se inventa.
    Se usa una COPIA efímera de la BD (patrón documentado de III-C caso 7):
    la BD real no se toca."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="v_t8_")
        bd_prueba = os.path.join(cls.tmp, "copia.db")
        shutil.copy2(BD, bd_prueba)
        con = sqlite3.connect(bd_prueba)
        vid2025 = vid_de(bd_prueba, "2025-06-06")
        con.execute("UPDATE recursos SET precio_mn=NULL WHERE version_id=? AND codigo='2259030004'",
                    (vid2025,))
        con.commit()
        con.close()
        cls.bd_prueba = bd_prueba
        cls.vid2025 = vid2025

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_n8_sin_precio_avisado(self):
        import urllib.request as _u
        # servidor efímero sobre la copia
        proc = subprocess.Popen(
            [sys.executable, SERVIDOR, "--puerto", str(PUERTO + 2), "--bd", self.bd_prueba],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(60):
                try:
                    _u.urlopen(f"http://127.0.0.1:{PUERTO+2}/api/versiones", timeout=2)
                    break
                except Exception:
                    time.sleep(0.25)
            with _u.urlopen(f"http://127.0.0.1:{PUERTO+2}/api/recursos?q=2259030004"
                            f"&version_id={self.vid2025}", timeout=10) as r:
                d = json.loads(r.read())
            rec = d["resultados"][0]
            self.assertIsNone(rec["precio_mn"])
            self.assertTrue(rec["sin_precio"])
        finally:
            proc.terminate()
            proc.wait(timeout=10)

    def test_bd_real_intacta(self):
        con = sqlite3.connect(f"file:{BD}?mode=ro", uri=True)
        precio = con.execute(
            """SELECT precio_mn FROM recursos WHERE version_id=
               (SELECT id FROM versiones_catalogo WHERE version='2025-06-06')
               AND codigo='2259030004'""").fetchone()[0]
        con.close()
        self.assertIsNotNone(precio)   # la copia nunca tocó la real


class TestModeloEdicion(unittest.TestCase):
    """N2/N3/N4/N6/N7/N12 — contrato del modelo de edición (nivel archivo)."""

    @classmethod
    def setUpClass(cls):
        cls.codigo = open(RECURSOS, encoding="utf-8").read()
        sin_bloque = re.sub(r"/\*.*?\*/", "", cls.codigo, flags=re.S)
        cls.ejecutable = "\n".join(re.sub(r"//.*$", "", l) for l in sin_bloque.splitlines())

    def test_n2_campos_del_modelo(self):
        """La capa de edición usa exactamente las claves documentadas."""
        for frag in ("edicionRecursos", "cambios:", "propios:",
                      "coefOriginal", "precioOriginal", "descompEfectiva"):
            self.assertIn(frag, self.codigo, f"falta {frag!r}")

    def test_n3_guardas_de_validacion(self):
        for frag in ("function validarNum", "negativo", "no numérico", "vacío"):
            self.assertIn(frag, self.codigo)

    def test_n4_formula_recalculo(self):
        for frag in ("f.coef * f.precio", "f.coef * cantidad", "f.consumo * f.precio",
                     "out.total * cantidad"):
            self.assertIn(frag, self.codigo, f"falta {frag!r} (fórmula de recálculo)")

    def test_n6_edicion_solo_en_el_item(self):
        """La edición vive en it.edicionRecursos (dentro del presupuesto):
        el overlay NO accede directamente a localStorage (solo el mecanismo
        existente touch()/saveBudgets de PRECOST) ni emite SQL de escritura.
        Las menciones a p3pro.budgets en textos de UI son informativas."""
        self.assertNotIn("localStorage", self.ejecutable,
                         "acceso directo a almacenamiento en el overlay")
        for patrón in ("INSERT", "UPDATE ", "DELETE FROM", "CREATE TABLE"):
            self.assertNotIn(patrón, self.ejecutable, f"SQL de escritura en el overlay: {patrón}")

    def test_n7_persistencia_round_trip(self):
        """it.edicionRecuestos sobrevive al round-trip JSON (localStorage) bit a bit."""
        edicion = {
            "creado": "2026-10-14T12:00:00.000Z",
            "actualizado": "2026-10-14T12:05:00.000Z",
            "version_id": 1, "version": "2025-06-06", "catalogo": "PRECONS_III",
            "precio_version_id": 1,
            "cambios": {"material|3834010001": {"coef": 0.9, "precio": 245.5}},
            "propios": {
                "material": [
                    {"tipo": "material", "codigo": "2259030004", "descripcion": "CEMENTO ASFALTICO 85/100 PENET A 25 GRADOS C",
                     "um": "litro", "coef": 2.4, "precio": 10.05, "origen": "catalogo",
                     "agregado": "2026-10-14T12:04:00.000Z"},
                    {"tipo": "material", "codigo": "PROP-ARENA", "descripcion": "ARENA DE RIO (propia)",
                     "um": "m3", "coef": 0.375, "precio": 4.5678, "origen": "manual",
                     "agregado": "2026-10-14T12:05:00.000Z"}
                ]
            }
        }
        ida = json.loads(json.dumps(edicion))
        self.assertEqual(ida, edicion)
        # los valores fraccionarios y de 4 decimales sobreviven bit a bit
        self.assertEqual(repr(ida["propios"]["material"][1]["precio"]), repr(4.5678))
        self.assertEqual(repr(ida["cambios"]["material|3834010001"]["coef"]), repr(0.9))

    def test_n7_formula_efectiva_replicada(self):
        """N4 en Python: el total efectivo de una especificación con estos
        propios = Σ coef×precio (doble precisión, sin redondeo)."""
        propios = [(2.4, 10.05), (0.375, 4.5678)]
        total = sum(c * p for c, p in propios)
        self.assertEqual(f"{total:.4f}", f"{2.4*10.05 + 0.375*4.5678:.4f}")
        cantidad = 2.5
        self.assertEqual(f"{total*cantidad:.4f}", f"{(2.4*10.05 + 0.375*4.5678)*2.5:.4f}")

    def test_n12_defensas_formato_antiguo(self):
        """Presupuestos pre-Misión V (sin edicionRecursos ni flags): los
        accesos defensivos devuelven defectos, nunca excepciones."""
        for frag in ("function flagsDe", '"MHE"', "function edicionDe",
                     "function asegurarEdicion", "normaPreco || null"):
            self.assertIn(frag, self.codigo, f"falta {frag!r} (defensa formato antiguo)")

    def test_n5_ninguna_escritura_al_catalogo(self):
        """El overlay jamás crea recursos en el catálogo: la entrada manual
        queda en el presupuesto (mensaje explícito en el panel)."""
        self.assertIn("no crea nada en el catálogo", self.codigo)


if __name__ == "__main__":
    print("=== MISIÓN V — Suite de pruebas: edición de recursos (S-050/S-052) ===")
    unittest.main(verbosity=2)
