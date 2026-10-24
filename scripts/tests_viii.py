#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MISIÓN VIII — Suite de pruebas: paridad «literal» servidor local ↔ web estática.

Verifica que la versión web (GitHub Pages, datos embebidos dist/data) ofrece
la MISMA información que el servidor local con la BD completa:

  E1  Equivalencia de /api/versiones (mismas versiones, conteos y orden).
  E2  Equivalencia de /api/partidas por versión (búsquedas exactas: mismos
      códigos en el mismo orden, mismos costos).
  E3  Equivalencia de /api/partida/<cod> (normas, subtotales, verificación
      CMMN/CHMN/CEMN con el MISMO veredicto, otras versiones).
  E4  Equivalencia de /api/descomposicion/<cod> (componentes con precios,
      advertencias, duplicados, respaldo de precios, fuentes_precio y otras
      versiones) — incluye el caso documentado 012141 y resolución de precios
      de OTRA versión (precio_version_id).
  E5  Equivalencia de /api/recursos (nomenclador: mismos resultados, precios,
      sin_precio y ambigüedades).
  C1  Contratos: el servidor local sigue inyectando SOLO los 4 overlays
      propios (estatico.js es WEB-ONLY) y dist/ lleva 5; orden correcto y
      rutas relativas.
  C2  El HTML original permanece byte-idéntico; dist/data íntegro (manifest).
  C3  Sintaxis (node --check) de los 4 overlays tocados/creados en VIII.
  D1  Los datos embebidos (i.json) coinciden con la BD: conteos por versión.

La equivalencia E2-E5 ejecuta el overlay app/overlay/estatico.js REAL en
Node (scripts/tests_viii_runner.js, shim de fetch al disco) contra el
servidor REAL (scripts/servidor_precodi.py) con la BD completa: paridad
verificada, no asumida. Tolerancias documentadas: subtotales totales ≤ 1e-6
(el servidor suma en Decimal y exporta float; el overlay suma en doble
precisión — la regla de tolerancia de la verificación absorbe la diferencia).

Uso:  python3 scripts/tests_viii.py
Requiere: bd/precodi.db (bases importadas), node, app/web-datos/ generado.
"""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import unittest
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, "app", "PRECOST-v9.17.html")
SERVIDOR = os.path.join(REPO, "scripts", "servidor_precodi.py")
CONSTRUCTOR = os.path.join(REPO, "scripts", "construir_web.py")
RUNNER = os.path.join(REPO, "scripts", "tests_viii_runner.js")
DATOS = os.path.join(REPO, "app", "web-datos")
BD = os.path.join(REPO, "bd", "precodi.db")
DIST = os.path.join(REPO, "dist")
SHA_HTML = "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"
PUERTO = 8841
BASE = f"http://127.0.0.1:{PUERTO}"
TOL = 1e-6           # subtotales: Decimal (servidor) vs double (overlay)


def api(ruta):
    with urllib.request.urlopen(BASE + ruta, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def overlay(tareas):
    """Ejecuta el overlay REAL en Node con la lista de tareas dada."""
    r = subprocess.run([sys.executable, "-c", "pass"] and ["node", RUNNER],
                       input=json.dumps(tareas), capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise AssertionError(f"runner node falló: {r.stderr[:400]}")
    return json.loads(r.stdout)


def cerca(a, b, tol=TOL):
    if a is None or b is None:
        return a is b
    return abs(a - b) <= tol


class BaseConServidor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # artefacto dist/ construido desde cero (verifica el pipeline real)
        r = subprocess.run([sys.executable, CONSTRUCTOR], capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise RuntimeError(f"construir_web.py falló: {r.stderr[:400]}")
        cls.proc = subprocess.Popen(
            [sys.executable, SERVIDOR, "--puerto", str(PUERTO), "--bd", BD],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(80):
            try:
                urllib.request.urlopen(BASE + "/api/versiones", timeout=2)
                break
            except Exception:
                time.sleep(0.25)
        else:
            raise RuntimeError("el servidor de pruebas no arrancó")
        cls.versiones = [v for v in api("/api/versiones")["versiones"] if v["partidas"] > 0]

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "proc", None):
            cls.proc.terminate()
            cls.proc.wait(timeout=10)
            cls.proc = None


class TestEquivalencia(BaseConServidor):
    """E1-E5: servidor local ↔ overlay estático, sobre datos REALES."""

    def muestra_versiones(self):
        """Versiones con normas (para E3/E4) — todas las PRECODI + la 2025."""
        con = sqlite3.connect(f"file:{BD}?mode=ro", uri=True)
        out = []
        for v in self.versiones:
            out.append(v)
        con.close()
        return out

    def test_e1_versiones(self):
        d_api = api("/api/versiones")["versiones"]
        d_est = overlay([{"op": "versiones"}])[0]["versiones"]
        # El índice embebido EXCLUYE las versiones de referencia sin filas
        # propias (p. ej. 2007-v7.21-Preambulos ≡ 7.21, estado retirada, 0
        # partidas): no hay datos que embeber. La UI ya las ocultaba
        # (precodi.js filtra partidas === 0). Contrato documentado.
        d_api_datos = [v for v in d_api if v["partidas"] > 0 or v["recursos"] > 0]
        sin_datos = [v["version"] for v in d_api if v["partidas"] == 0 and v["recursos"] == 0]
        self.assertEqual([v["version"] for v in d_api_datos], [v["version"] for v in d_est])
        for a, e in zip(d_api_datos, d_est):
            for campo in ("catalogo", "version", "estado", "partidas", "recursos",
                          "normas", "descomponibles"):
                self.assertEqual(a[campo], e[campo], f"{campo} de {a['version']}")
        # y ninguna versión sin datos aparece en el índice embebido
        for v in d_est:
            self.assertNotIn(v["version"], sin_datos)

    def test_e2_partidas(self):
        tareas, claves = [], []
        for v in self.versiones:
            for q in ("roca", "cemento", "0121", ""):
                tareas.append({"op": "partidas", "q": q or None,
                               "versionId": v["id"], "limite": 25})
                claves.append((v["version"], q))
        res_est = overlay(tareas)
        for (version, q), e in zip(claves, res_est):
            a = api(f"/api/partidas?q={urllib.parse.quote(q)}&version_id={self._vid(version)}&limit=25")
            self.assertEqual([p["codigo"] for p in a["resultados"]],
                             [p["codigo"] for p in e["resultados"]],
                             f"códigos distintos para q={q!r} en {version}")
            for pa, pe in zip(a["resultados"], e["resultados"]):
                self.assertEqual(pa["descripcion"], pe["descripcion"])
                self.assertEqual(pa["unidad"], pe["unidad"])
                self.assertTrue(cerca(pa["costo_total_mn"], pe["costo_total_mn"]))

    def _vid(self, version):
        return [v["id"] for v in self.versiones if v["version"] == version][0]

    def test_e3_partida(self):
        con = sqlite3.connect(f"file:{BD}?mode=ro", uri=True)
        versiones_normas = [v for v in self.versiones if v["normas"] > 0]
        tareas, claves = [], []
        for v in versiones_normas:
            # muestra determinista: 5 partidas con normas (primera, 1/4, mitad, 3/4, la 012141 si existe)
            cods = [r[0] for r in con.execute(
                """SELECT DISTINCT p.codigo FROM partidas p JOIN normas_partida np
                   ON np.partida_id = p.id AND np.version_id = p.version_id
                   WHERE p.version_id=? ORDER BY p.codigo""", (v["id"],))]
            muestra = {cods[0], cods[len(cods) // 4], cods[len(cods) // 2],
                       cods[3 * len(cods) // 4]}
            if "012141" in cods:
                muestra.add("012141")
            for c in sorted(muestra):
                tareas.append({"op": "partida", "codigo": c, "versionId": v["id"]})
                claves.append((v["version"], c))
        con.close()
        res_est = overlay(tareas)
        for (version, cod), e in zip(claves, res_est):
            a = api(f"/api/partida/{cod}?version_id={self._vid(version)}")
            self.assertEqual(len(a["normas"]), len(e["normas"]),
                             f"número de normas de {cod} en {version}")
            self.assertEqual([n["codigo_recurso"] for n in a["normas"]],
                             [n["codigo_recurso"] for n in e["normas"]])
            for na, ne in zip(a["normas"], e["normas"]):
                self.assertEqual(na["tipo"], ne["tipo"])
                self.assertTrue(cerca(na["subtotal"], ne["subtotal"]))
            for k in ("cmmn", "chmn", "cemn"):
                va, ve = a["verificacion"][k], e["verificacion"][k]
                if va and ve:
                    self.assertEqual(va["coincide"], ve["coincide"],
                                     f"veredicto {k} de {cod}@{version}: {va} vs {ve}")
            self.assertEqual([o["version"] for o in a["otras_versiones"]],
                             [o["version"] for o in e["otras_versiones"]])

    def test_e4_descomposicion(self):
        con = sqlite3.connect(f"file:{BD}?mode=ro", uri=True)
        versiones_normas = [v for v in self.versiones if v["normas"] > 0]
        vid_raiz = self._vid("2017-raiz")
        vid_721 = self._vid("2007-v7.21")
        tareas, claves = [], []
        for v in versiones_normas:
            cods = [r[0] for r in con.execute(
                """SELECT DISTINCT p.codigo FROM partidas p JOIN normas_partida np
                   ON np.partida_id = p.id AND np.version_id = p.version_id
                   WHERE p.version_id=? ORDER BY p.codigo""", (v["id"],))]
            muestra = {cods[0], cods[len(cods) // 2]}
            if "012141" in cods:
                muestra.add("012141")
            for c in sorted(muestra):
                tareas.append({"op": "descomposicion", "codigo": c, "versionId": v["id"]})
                claves.append(((v["version"], c), None))
        # resolución de precios de OTRA versión: normas 7.21 con precios 2017-raíz
        cods721 = [r[0] for r in con.execute(
            """SELECT DISTINCT p.codigo FROM partidas p JOIN normas_partida np
               ON np.partida_id = p.id AND np.version_id = p.version_id
               WHERE p.version_id=? ORDER BY p.codigo""", (vid_721,))]
        for c in sorted({cods721[0], cods721[len(cods721) // 2], "012141"}):
            tareas.append({"op": "descomposicion", "codigo": c,
                           "versionId": vid_721, "precioVersionId": vid_raiz})
            claves.append((("2007-v7.21", c), vid_raiz))
        con.close()
        res_est = overlay(tareas)
        for ((version, cod), vid_precio), e in zip(claves, res_est):
            url = f"/api/descomposicion/{cod}?version_id={self._vid(version)}"
            if vid_precio:
                url += f"&precio_version_id={vid_precio}"
            a = api(url)
            self.assertEqual(a.get("tiene_norma"), e.get("tiene_norma"), f"tiene_norma {cod}@{version}")
            self.assertEqual(len(a["componentes"]), len(e["componentes"]),
                             f"nº componentes de {cod}@{version}")
            for ca, ce in zip(a["componentes"], e["componentes"]):
                self.assertEqual((ca["tipo"], ca["codigo"]), (ce["tipo"], ce["codigo"]))
                self.assertTrue(cerca(ca["coeficiente"], ce["coeficiente"], 1e-12))
                self.assertEqual(ca["resuelto"], ce["resuelto"], f"resuelto {ca['codigo']}@{version}")
                self.assertEqual(ca["precio_resuelto"], ce["precio_resuelto"],
                                 f"precio_resuelto {ca['codigo']}@{version}")
                self.assertTrue(cerca(ca["precio_mn"], ce["precio_mn"], 1e-9),
                                f"precio {ca['codigo']}@{version}")
                self.assertEqual(ca.get("advertencia"), ce.get("advertencia"),
                                 f"advertencia {ca['codigo']}@{version}")
                self.assertEqual(ca.get("precio_respaldo", False), ce.get("precio_respaldo", False))
                self.assertEqual(len(ca["hijos"]), len(ce["hijos"]), f"hijos de {ca['codigo']}")
            self.assertEqual(a["duplicados"], e["duplicados"])
            self.assertEqual(a["advertencias"], e["advertencias"], f"advertencias {cod}@{version}")
            for k in set(a["subtotales"]) | set(e["subtotales"]):
                self.assertTrue(cerca(a["subtotales"].get(k), e["subtotales"].get(k)),
                                f"subtotal {k} de {cod}@{version}")
            if a["verificacion"]:
                for k in ("cmmn", "chmn", "cemn"):
                    va, ve = a["verificacion"][k], e["verificacion"][k]
                    if va and ve:
                        self.assertEqual(va["coincide"], ve["coincide"], f"veredicto {k} {cod}@{version}")
            if vid_precio:
                fa, fe = a["fuentes_precio"], e["fuentes_precio"]
                self.assertEqual(fa["resueltos"], fe["resueltos"])
                self.assertEqual(fa["total"], fe["total"])
                self.assertEqual(fa["sin_resolver"], fe["sin_resolver"])
            self.assertEqual([o["version"] for o in a["otras_versiones"]],
                             [o["version"] for o in e["otras_versiones"]])

    def test_e5_recursos(self):
        tareas, claves = [], []
        for v in self.versiones:
            if v["recursos"] == 0:
                continue
            for q, tipo in (("cemento", ""), ("2259030004", ""), ("ALBAÑIL", "mano_obra"),
                            ("", "equipo")):
                tareas.append({"op": "recursos", "q": q, "tipo": tipo,
                               "versionId": v["id"], "limite": 25})
                claves.append((v["version"], q, tipo))
        res_est = overlay(tareas)
        import urllib.parse
        for (version, q, tipo), e in zip(claves, res_est):
            url = (f"/api/recursos?q={urllib.parse.quote(q)}&limit=25&version_id={self._vid(version)}")
            if tipo:
                url += "&tipo=" + tipo
            a = api(url)
            self.assertEqual([r["codigo"] for r in a["resultados"]],
                             [r["codigo"] for r in e["resultados"]],
                             f"recursos q={q!r} tipo={tipo!r} en {version}")
            for ra, re_ in zip(a["resultados"], e["resultados"]):
                self.assertEqual(ra["tipo"], re_["tipo"])
                self.assertEqual(ra["unidad"], re_["unidad"])
                self.assertTrue(cerca(ra["precio_mn"], re_["precio_mn"], 1e-9))
                self.assertEqual(ra["sin_precio"], re_["sin_precio"])
                self.assertEqual(ra["mismo_codigo_otro_tipo"], re_["mismo_codigo_otro_tipo"])


class TestContratos(BaseConServidor):
    """C1-C3: contratos del artefacto y del servidor local (hereda el
    servidor de pruebas: unittest ejecuta por orden alfabético y esta clase
    corre ANTES que TestEquivalencia)."""

    def test_c1_servidor_local_cuatro_overlays(self):
        """El servidor local inyecta SOLO sus 4 overlays: estatico.js es
        WEB-ONLY (el servidor no debe servirlo ni inyectarlo)."""
        with urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/", timeout=30) as r:
            cuerpo = r.read()
        self.assertEqual(cuerpo.count(b'<script src="/overlay/'), 4)
        for nombre in (b"precodi.js", b"recursos.js", b"calculadora.js", b"respaldo.js"):
            self.assertIn(b'<script src="/overlay/' + nombre + b'" defer>', cuerpo)
        self.assertNotIn(b"estatico.js", cuerpo)

    def test_c1_dist_cinco_overlays_orden_y_rutas(self):
        with open(os.path.join(DIST, "index.html"), "rb") as f:
            cuerpo = f.read()
        esperado = [b"estatico.js", b"recursos.js", b"calculadora.js", b"respaldo.js", b"precodi.js"]
        etiquetas = re.findall(rb'<script src="([^"]+)" defer>', cuerpo)
        self.assertEqual(etiquetas, [b"overlay/" + n for n in esperado])
        for t in etiquetas:
            self.assertFalse(t.startswith(b"/"), f"ruta absoluta en el artefacto: {t!r}")
        self.assertEqual(cuerpo.count(b"<script src="), 5)

    def test_c2_html_original_intacto(self):
        h = hashlib.sha256()
        with open(HTML, "rb") as f:
            for bloque in iter(lambda: f.read(1 << 20), b""):
                h.update(bloque)
        self.assertEqual(h.hexdigest(), SHA_HTML)

    def test_c2_datos_dist_integros(self):
        with open(os.path.join(DATOS, "manifest.json"), encoding="utf-8") as fp:
            manifest = json.load(fp)
        self.assertTrue(os.path.exists(os.path.join(DIST, "data", "i.json")))
        for nombre, info in manifest["archivos"].items():
            ruta = os.path.join(DIST, "data", nombre)
            self.assertTrue(os.path.exists(ruta), f"falta data/{nombre} en dist")
            self.assertEqual(os.path.getsize(ruta), info["bytes"], f"tamaño divergente: {nombre}")
        # sin archivos prohibidos en el artefacto público
        for raiz, _dirs, ficheros in os.walk(DIST):
            for fn in ficheros:
                self.assertFalse(fn.endswith((".db", ".sqlite", ".mdb", ".env", ".rar",
                                              ".zip", ".exe")), f"prohibido en dist: {fn}")

    def test_c3_sintaxis_node(self):
        for fich in ("estatico.js", "precodi.js", "recursos.js", "calculadora.js", "respaldo.js"):
            r = subprocess.run(["node", "--check", os.path.join(REPO, "app", "overlay", fich)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{fich}: {r.stderr}")


class TestDatosWeb(unittest.TestCase):
    """D1: los datos embebidos coinciden con la BD real."""

    def test_d1_indice_contra_bd(self):
        with open(os.path.join(DATOS, "i.json"), encoding="utf-8") as fp:
            indice = json.load(fp)
        con = sqlite3.connect(f"file:{BD}?mode=ro", uri=True)
        for v in indice["versiones"]:
            fila = con.execute("""SELECT c.codigo, vc.version FROM versiones_catalogo vc
                                  JOIN catalogos c ON c.id = vc.catalogo_id WHERE vc.id=?""",
                               (v["id"],)).fetchone()
            self.assertIsNotNone(fila, f"versión {v['version']} no existe en la BD")
            self.assertEqual(fila[1], v["version"])
            n = con.execute("SELECT COUNT(*) FROM partidas WHERE version_id=?", (v["id"],)).fetchone()[0]
            self.assertEqual(n, v["partidas"])
            n = con.execute("SELECT COUNT(*) FROM normas_partida WHERE version_id=?", (v["id"],)).fetchone()[0]
            self.assertEqual(n, v["normas"])
            n = con.execute("SELECT COUNT(*) FROM recursos WHERE version_id=?", (v["id"],)).fetchone()[0]
            self.assertEqual(n, v["recursos"])
        con.close()


if __name__ == "__main__":
    import urllib.parse  # noqa: F401  (usado en E2/E5)
    print("=== MISIÓN VIII — Suite de paridad servidor ↔ web estática ===")
    unittest.main(verbosity=2)
