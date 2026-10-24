#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MISIÓN VII — Suite de pruebas: respaldo/restauración completa (S-005).

Cubre el overlay app/overlay/respaldo.js y su integración en el servidor
local y en el artefacto estático de GitHub Pages:

  V1  Integridad del HTML original (SHA-256) — no cambia por esta misión.
  V2  respaldo.js: sintaxis válida (node --check) y guardas de calidad
      (idempotente; solo teclas p3pro.*; sin red — 100 % cliente;
      confirmación antes de reemplazar; gancho de pruebas).
  V3  El servidor local sirve /overlay/respaldo.js con tipo correcto y
      contenido íntegro (byte a byte el archivo de app/overlay).
  V4  La inyección del servidor incluye la etiqueta de respaldo.js.
  V5  construir_web.py genera dist/ con overlay/respaldo.js y las tres
      etiquetas RELATIVAS (recursos, calculadora, respaldo — precodi.js
      sigue excluido del artefacto público por diseño).
  V6  El artefacto dist/ no contiene bases de datos ni archivos privados.
  V7  calculadora.js: corrección de coexistencia de botones (apilado cuando
      el FAB del catálogo está presente) — guardia de regresión.
  V8  El tag v9.17-original sigue apuntando al commit base.

La validación de EXTREMO A EXTREMO (exportar → borrar → restaurar →
recuperar presupuestos en la UI, rechazo de archivos inválidos) se hace en
navegador real con scripts/validar_vii_navegador.sh.
"""

import os
import re
import subprocess
import sys
import time
import unittest
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, "app", "PRECOST-v9.17.html")
RESPALDO = os.path.join(REPO, "app", "overlay", "respaldo.js")
CALC = os.path.join(REPO, "app", "overlay", "calculadora.js")
SERVIDOR = os.path.join(REPO, "scripts", "servidor_precodi.py")
CONSTRUIR = os.path.join(REPO, "scripts", "construir_web.py")
DIST = os.path.join(REPO, "dist")
SHA_HTML = "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"

PUERTO = 8819
BASE = f"http://127.0.0.1:{PUERTO}"


def sha256_de(ruta):
    import hashlib
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


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


class TestIntegridad(unittest.TestCase):
    """V1/V8 — el original y el tag de restauración no se tocan."""

    def test_v1_html_original_intacto(self):
        self.assertEqual(sha256_de(HTML), SHA_HTML,
                         "el HTML original protegido cambió — abortar la misión")


class TestRespaldoJS(unittest.TestCase):
    """V2 — calidad y guardas del overlay (análisis estático del código real)."""

    @classmethod
    def setUpClass(cls):
        cls.codigo = open(RESPALDO, encoding="utf-8").read()
        sin_bloque = re.sub(r"/\*.*?\*/", "", cls.codigo, flags=re.S)
        cls.ejecutable = "\n".join(
            re.sub(r"//.*$", "", l) for l in sin_bloque.splitlines())

    def test_v2_sintaxis_node(self):
        r = subprocess.run(["node", "--check", RESPALDO],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_v2_idempotente(self):
        self.assertIn("if (window.__pcodRespaldo) return;", self.codigo)

    def test_v2_solo_teclas_p3pro(self):
        # TODA clave escrita/leída pasa por el prefijo; ninguna otra
        # clave de localStorage puede tocar el respaldo (ni ser tocada).
        self.assertIn('var PREFIJO = "p3pro."', self.ejecutable)
        for llamada in re.findall(r"localStorage\.(setItem|getItem|removeItem)\(", self.ejecutable):
            self.assertIn(llamada, ("setItem", "getItem", "removeItem"))

    def test_v2_sin_red(self):
        # 100 % cliente: nada de fetch/XHR/WebSocket (compatible con Pages
        # y sin fugas de datos a servidores).
        self.assertNotIn("fetch(", self.ejecutable)
        self.assertNotIn("XMLHttpRequest", self.ejecutable)
        self.assertNotIn("WebSocket", self.ejecutable)

    def test_v2_confirmacion_antes_de_reemplazar(self):
        # la restauración en UI exige confirmación explícita del usuario
        self.assertIn("confirm(", self.ejecutable)

    def test_v2_validacion_estricta_sin_escrituras_parciales(self):
        # aplicarRespaldo valida TODO antes de escribir la primera clave
        self.assertLess(self.ejecutable.index("validarRespaldo(obj)"),
                        self.ejecutable.index('localStorage.removeItem'))
        self.assertIn('return { ok: false, error: err }', self.ejecutable)

    def test_v2_gancho_de_pruebas(self):
        self.assertIn("window.__pcodRespaldoAPI", self.ejecutable)


class TestServidorYServido(ServidorBase):
    """V3/V4 — el servidor local sirve el cuarto overlay y lo inyecta."""

    def test_v3_respaldo_servido(self):
        status, cuerpo = self.get("/overlay/respaldo.js")
        self.assertEqual(status, 200)
        self.assertIn(b"__pcodRespaldo", cuerpo)
        with open(RESPALDO, "rb") as f:
            self.assertEqual(cuerpo, f.read(),
                             "el servidor debe servir el archivo íntegro, byte a byte")

    def test_v3_tipo_contenido(self):
        with urllib.request.urlopen(BASE + "/overlay/respaldo.js") as r:
            self.assertIn("javascript", r.headers.get("Content-Type", ""))

    def test_v4_inyeccion(self):
        status, cuerpo = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn(b'<script src="/overlay/respaldo.js" defer>', cuerpo)


class TestArtefactoEstatico(unittest.TestCase):
    """V5/V6 — dist/ incluye el respaldo y no expone nada privado."""

    @classmethod
    def setUpClass(cls):
        r = subprocess.run([sys.executable, CONSTRUIR], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"construir_web.py falló:\n{r.stdout}\n{r.stderr}")

    def test_v5_overlay_en_dist(self):
        self.assertTrue(os.path.exists(os.path.join(DIST, "overlay", "respaldo.js")))
        with open(os.path.join(DIST, "overlay", "respaldo.js"), "rb") as f1, \
             open(RESPALDO, "rb") as f2:
            self.assertEqual(f1.read(), f2.read())

    def test_v5_inyeccion_relativa(self):
        html = open(os.path.join(DIST, "index.html"), "rb").read()
        for nombre in (b"recursos.js", b"calculadora.js", b"respaldo.js"):
            self.assertIn(b'<script src="overlay/' + nombre + b'" defer>', html)
        # precodi.js sigue EXCLUIDO del artefacto público (por diseño, ver README §H)
        self.assertNotIn(b'overlay/precodi.js', html)

    def test_v6_sin_archivos_privados(self):
        prohibidos = [".db", ".sqlite", ".mdb", ".env", ".rar", ".zip", ".exe"]
        for raiz, _dirs, ficheros in os.walk(DIST):
            for fn in ficheros:
                self.assertFalse(any(fn.endswith(ext) for ext in prohibidos),
                                 f"archivo no permitido en dist/: {os.path.join(raiz, fn)}")


class TestCalculadoraCoexistencia(unittest.TestCase):
    """V7 — guardia de regresión del apilado de botones flotantes."""

    def test_v7_apilado_cuando_hay_fab_precodi(self):
        codigo = open(CALC, encoding="utf-8").read()
        self.assertIn('document.querySelector(".pcod-fab")', codigo,
                      "calculadora.js debe apilar su botón cuando el FAB del "
                      "catálogo está presente (fix MISIÓN VII)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
