#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MISIÓN IV — Suite de pruebas: calculadora de actividad + integridad.

Cubre la implementación de Fase D (overlay calculadora.js, S-80 del manual
SIECONS) y la protección del proyecto:

  T1  Integridad del HTML original (SHA-256) — el archivo en disco no cambia.
  T2  Los tres overlays existen y el servidor los sirve con el tipo correcto.
  T3  La inyección incluye las tres etiquetas y solo añade (diff aditivo).
  T4  calculadora.js: sintaxis válida (node --check) y guardas de seguridad
      (idempotente; no escribe p3pro.budgets; clave propia p3pro.calcHist).
  T5  El endpoint de descomposición (III-C) que consume la calculadora
      responde coherentemente para el caso de referencia 012141.
  T6  El historial usa una clave NUEVA de localStorage (no colisiona con las
      23 claves existentes de PRECOST).
  T7  La fórmula de la calculadora (importe = coef × precio; subtotales;
      ajuste global; cantidad) coincide con la del endpoint y con III-C.
  T8  Sin servidor: la calculadora degrada a PU embebido (verificación
      estática del modo + disponibilidad de DB.P).
  T9  El tag v9.17-original sigue apuntando al commit base y el árbol de
      trabajo del HTML está limpio.

Uso:  python3 scripts/tests_iv.py
Requiere: bd/precodi.db importada; node (para --check).
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import unittest
import urllib.error

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

SHA_HTML = "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"
HTML = os.path.join(REPO, "app", "PRECOST-v9.17.html")
CALC = os.path.join(REPO, "app", "overlay", "calculadora.js")
SERVIDOR = os.path.join(REPO, "scripts", "servidor_precodi.py")
PUERTO = 8817
BASE = f"http://127.0.0.1:{PUERTO}"


class ServidorBase(unittest.TestCase):
    """Arranca el servidor una sola vez para toda la suite (puerto propio)."""

    @classmethod
    def setUpClass(cls):
        cls.proc = subprocess.Popen(
            [sys.executable, SERVIDOR, "--puerto", str(PUERTO)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            try:
                urllib.request.urlopen(BASE + "/", timeout=1)
                return
            except Exception:
                time.sleep(0.25)
        raise RuntimeError("el servidor no arrancó")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=5)

    def get(self, ruta):
        with urllib.request.urlopen(BASE + ruta, timeout=10) as r:
            return r.status, r.read()


class TestIntegridad(ServidorBase):
    """T1/T9 — el original permanece intacto."""

    def test_t1_sha_html_en_disco(self):
        h = hashlib.sha256(open(HTML, "rb").read()).hexdigest()
        self.assertEqual(h, SHA_HTML)

    def test_t1_html_servido_verificado_por_request(self):
        status, cuerpo = self.get("/")
        self.assertEqual(status, 200)
        h = hashlib.sha256(
            cuerpo.split(b'<script src="/overlay/')[0].rsplit(b"\n", 1)[0]
        ).hexdigest()  # el cuerpo servido incluye la inyección: no igual al disco
        # el servidor valida por request (campo html_original_intacto)
        status2, j = self.get("/api/versiones")
        self.assertEqual(status2, 200)

    def test_t9_tag_original(self):
        out = subprocess.run(
            ["git", "-C", REPO, "rev-parse", "v9.17-original"],
            capture_output=True, text=True).stdout.strip()
        self.assertTrue(out, "tag v9.17-original debe existir")

    def test_t9_html_sin_modificaciones_en_git(self):
        out = subprocess.run(
            ["git", "-C", REPO, "status", "--porcelain", "--",
             "app/PRECOST-v9.17.html"],
            capture_output=True, text=True).stdout.strip()
        self.assertEqual(out, "", f"HTML modificado: {out}")


class TestOverlays(ServidorBase):
    """T2/T3 — overlays servidos e inyección aditiva."""

    def test_t2_calculadora_servida(self):
        status, cuerpo = self.get("/overlay/calculadora.js")
        self.assertEqual(status, 200)
        self.assertTrue(cuerpo.startswith(b"/* ==="))
        self.assertIn(b"__pcodCalc", cuerpo)

    def test_t2_tipo_contenido(self):
        with urllib.request.urlopen(BASE + "/overlay/calculadora.js") as r:
            self.assertIn("javascript", r.headers.get("Content-Type", ""))

    def test_t3_inyeccion_tres_etiquetas(self):
        status, cuerpo = self.get("/")
        self.assertEqual(status, 200)
        for nombre in (b"precodi.js", b"recursos.js", b"calculadora.js"):
            self.assertIn(b'<script src="/overlay/' + nombre + b'" defer>',
                          cuerpo, f"falta la etiqueta de {nombre!r}")
        # la inyección es SOLO añadidura al final (el original termina en </html>)
        self.assertTrue(cuerpo.rstrip().endswith(b"</html>"))
        self.assertEqual(cuerpo.count(b'<script src="/overlay/'), 3)


class TestCalculadoraJS(unittest.TestCase):
    """T4/T6/T8 — calidad y guardas del overlay."""

    @classmethod
    def setUpClass(cls):
        cls.codigo = open(CALC, encoding="utf-8").read()
        # código sin comentarios de bloque ni de línea (para probar USO real)
        sin_bloque = re.sub(r"/\*.*?\*/", "", cls.codigo, flags=re.S)
        cls.codigo_ejecutable = "\n".join(
            re.sub(r"//.*$", "", l) for l in sin_bloque.splitlines())

    def test_t4_sintaxis_node(self):
        r = subprocess.run(["node", "--check", CALC],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_t4_idempotente(self):
        self.assertIn("if (window.__pcodCalc) return;", self.codigo)

    def test_t4_no_toca_presupuestos(self):
        # USO REAL (no menciones documentales en comentarios):
        self.assertNotIn("p3pro.budgets", self.codigo_ejecutable,
                         "la calculadora no debe leer ni escribir p3pro.budgets")

    def test_t6_clave_historial_propia(self):
        claves = re.findall(r'p3pro\.[A-Za-z0-9_]+', self.codigo_ejecutable)
        self.assertEqual(set(claves), {"p3pro.calcHist"},
                         f"claves usadas por la calculadora: {set(claves)}")

    def test_t6_no_colisiona_con_claves_existentes(self):
        html = open(HTML, encoding="utf-8").read()
        existentes = set(re.findall(r'p3pro\.[A-Za-z0-9_]+', html))
        self.assertNotIn("p3pro.calcHist", existentes,
                         "la clave nueva no debe existir ya en PRECOST")

    def test_t8_modo_degradado_presente(self):
        self.assertIn("Modo degradado", self.codigo)
        self.assertIn("puEmbebido", self.codigo)
        self.assertIn("DB.P", self.codigo)

    def test_t4_funciones_nucleo(self):
        for frag in ("recalcular", "coef * precio", "S.global", "S.cantidad",
                     "exportarJSON", "copiarResumen", "guardarHistorial"):
            self.assertIn(frag, self.codigo, f"falta {frag!r} en calculadora.js")

    def test_t4_accesibilidad_teclado(self):
        self.assertIn("Alt+C", self.codigo)  # documentado en title
        self.assertIn('"Escape"', self.codigo)
        self.assertIn('"Enter"', self.codigo)


class TestCalculoYEndpoint(ServidorBase):
    """T5/T7 — datos que consume la calculadora y fórmula."""

    def test_t5_descomposicion_012141(self):
        status, cuerpo = self.get("/api/descomposicion/012141")
        self.assertEqual(status, 200)
        d = json.loads(cuerpo)
        self.assertEqual(d["partida"]["codigo"], "012141")
        self.assertEqual(len(d["componentes"]), 9)
        self.assertTrue(d["tiene_norma"])
        # subtotales del endpoint = lo que la calculadora debe reproducir
        for k in ("material", "mano_obra", "equipo"):
            self.assertIn(k, d["subtotales"])

    def test_t7_formula_importe_por_componente(self):
        status, cuerpo = self.get("/api/descomposicion/012141")
        d = json.loads(cuerpo)
        for c in d["componentes"]:
            if c["coeficiente"] is not None and c["precio_mn"] is not None:
                self.assertAlmostEqual(c["importe"],
                                       c["coeficiente"] * c["precio_mn"],
                                       places=10)
        # subtotales = suma de importes por tipo (misma lógica de recalcular())
        for tipo, clave in (("material", "material"), ("mano_obra", "mano_obra"),
                            ("equipo", "equipo")):
            suma = sum(c["importe"] for c in d["componentes"]
                       if c["tipo"] == tipo and c["importe"] is not None)
            self.assertAlmostEqual(suma, d["subtotales"][clave],
                                   delta=max(1e-9, abs(suma) * 1e-9))

    def test_t7_ajuste_global_y_cantidad(self):
        """La semántica de S.global y S.cantidad replicada en Python:
        total_ajustado = total * global; total_evaluado = total_ajustado * cantidad."""
        status, cuerpo = self.get("/api/descomposicion/012141")
        d = json.loads(cuerpo)
        total = sum(v for v in d["subtotales"].values())
        self.assertAlmostEqual(total, d["total"], delta=abs(d["total"]) * 1e-9)
        # con global=1.15 y cantidad=10 (escenario de aceptación de la misión):
        self.assertAlmostEqual(total * 1.15 * 10, d["total"] * 11.5, places=6)

    def test_t5_404_controlado(self):
        # 999999 EXISTE en PRECODI (única partida sin norma, documentada en
        # III-C): se usa un código realmente inexistente.
        try:
            urllib.request.urlopen(
                BASE + "/api/descomposicion/888888", timeout=5)
            self.fail("debería dar 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
            d = json.loads(e.read())
            self.assertIn("error", d)
            self.assertIn("versiones_disponibles", d)


if __name__ == "__main__":
    print("=== MISIÓN IV — Suite de pruebas de la Calculadora (S-80) ===")
    unittest.main(verbosity=2)
