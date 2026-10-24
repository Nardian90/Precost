#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MISIÓN III-B · Fase 5 — Capa de acceso local para consultar el catálogo
PRECODI importado desde la propia aplicación PRECOST v9.17.

DECISIÓN DE ARQUITECTURA (justificada):
  PRECOST es un HTML autónomo que el usuario abre localmente (incluso con
  file://). Un navegador NO puede abrir SQLite directamente ni hacer fetch de
  file:// con garantías. Las opciones eran:
    (a) sql.js (SQLite WASM) + servir el .db por HTTP: requiere dependencia
        externa (~1.5 MB de WASM) y sigue necesitando un servidor HTTP para
        el fetch inicial.
    (b) CAPA DE ACCESO LOCAL (elegida): servidor HTTP mínimo de la librería
        estándar (cero dependencias, 100% offline) que:
          - sirve el HTML ORIGINAL desde disco SIN modificarlo, inyectando
            al vuelo una única etiqueta <script> aditiva antes de </body>
            (el archivo en disco permanece byte-idéntico, verificable por
            SHA-256);
          - expone /api/* en modo SOLO LECTURA sobre bd/precodi.db;
          - escucha ÚNICAMENTE en 127.0.0.1 (no es un servicio público).
  La opción (b) es reversible (apagar el proceso y no queda nada), no toca
  el catálogo embebido de PRECOST ni su contrato PRECOST-AI-JSON, y no
  depende de terceros. La vía sql.js/OPFS queda documentada como evolución
  futura si se quiere eliminar el proceso local.

Uso:  python3 scripts/servidor_precodi.py [--puerto 8765] [--bd bd/precodi.db]
      → abrir http://127.0.0.1:8765/
"""
import argparse
import json
import os
import re
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, "app", "PRECOST-v9.17.html")
OVERLAY = os.path.join(REPO, "app", "overlay", "precodi.js")
OVERLAY_RECURSOS = os.path.join(REPO, "app", "overlay", "recursos.js")
OVERLAY_CALCULADORA = os.path.join(REPO, "app", "overlay", "calculadora.js")
OVERLAY_RESPALDO = os.path.join(REPO, "app", "overlay", "respaldo.js")
BD_DEFECTO = os.path.join(REPO, "bd", "precodi.db")
SHA_HTML = "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"

# IV: tres overlays aditivos — catálogo (III-B), descomposiciones (III-C) y
# calculadora de costos de actividad (IV, S-80 del manual SIECONS)
# VII: cuarto overlay aditivo — respaldo/restauración completa (S-005)
INYECCION = (b'\n<script src="/overlay/precodi.js" defer></script>\n'
             b'<script src="/overlay/recursos.js" defer></script>\n'
             b'<script src="/overlay/calculadora.js" defer></script>\n'
             b'<script src="/overlay/respaldo.js" defer></script>\n')


def conectar_ro(ruta_bd):
    """Conexión SOLO LECTURA (mode=ro): el importador es el único que escribe."""
    con = sqlite3.connect(f"file:{ruta_bd}?mode=ro", uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    return con


class Manejador(BaseHTTPRequestHandler):
    bd = None  # se inyecta al arrancar

    # ------------------------------------------------------------------ util
    def _json(self, obj, codigo=200):
        cuerpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, fmt, *args):  # log compacto
        print(f"  {self.address_string()} {fmt % args}")

    # ------------------------------------------------------------------ GET
    def do_GET(self):
        try:
            u = urlparse(self.path)
            if u.path in ("/", "/index.html"):
                return self._servir_html()
            if u.path == "/overlay/precodi.js":
                return self._servir_archivo(OVERLAY, "application/javascript; charset=utf-8")
            if u.path == "/overlay/recursos.js":
                return self._servir_archivo(OVERLAY_RECURSOS, "application/javascript; charset=utf-8")
            if u.path == "/overlay/calculadora.js":
                return self._servir_archivo(OVERLAY_CALCULADORA, "application/javascript; charset=utf-8")
            if u.path == "/overlay/respaldo.js":
                return self._servir_archivo(OVERLAY_RESPALDO, "application/javascript; charset=utf-8")
            if u.path.startswith("/api/"):
                return self._api(u.path, parse_qs(u.query))
            self._json({"error": "no encontrado", "ruta": u.path}, 404)
        except Exception as e:  # noqa: BLE001
            self._json({"error": f"{type(e).__name__}: {e}"}, 500)

    def _servir_html(self):
        """Sirve el HTML original INYECTANDO solo la etiqueta del overlay.

        El archivo en disco no se toca: la inyección ocurre en la copia
        servida, inmediatamente antes del </body> real (última aparición).
        """
        with open(HTML, "rb") as f:
            contenido = f.read()
        i = contenido.rfind(b"</body>")
        if i >= 0:
            contenido = contenido[:i] + INYECCION + contenido[i:]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(contenido)))
        self.end_headers()
        self.wfile.write(contenido)

    def _servir_archivo(self, ruta, tipo):
        with open(ruta, "rb") as f:
            cuerpo = f.read()
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    # ------------------------------------------------------------------ API
    def _api(self, ruta, q):
        con = conectar_ro(self.bd)
        try:
            if ruta == "/api/versiones":
                return self._api_versiones(con)
            if ruta == "/api/partidas":
                return self._api_partidas(con, q)
            m = re.match(r"^/api/partida/([0-9A-Za-z%_\-]+)$", ruta)
            if m:
                return self._api_partida(con, m.group(1), q)
            m = re.match(r"^/api/descomposicion/([0-9A-Za-z%_\-]+)$", ruta)
            if m:
                return self._api_descomposicion(con, m.group(1), q)
            if ruta == "/api/normas_disponibles":
                return self._api_normas_disponibles(con, q)
            if ruta == "/api/recursos":
                return self._api_recursos(con, q)
            if ruta == "/api/stats":
                return self._api_stats(con)
            self._json({"error": "endpoint desconocido"}, 404)
        finally:
            con.close()

    def _api_versiones(self, con):
        filas = con.execute("""
            SELECT vc.id, c.codigo AS catalogo, vc.version, vc.estado, vc.fecha_importacion,
                   vc.fuente_archivo, vc.fuente_sha256, vc.fecha_publicacion, vc.fuente_detalle
            FROM versiones_catalogo vc JOIN catalogos c ON c.id = vc.catalogo_id
            ORDER BY vc.id""").fetchall()
        out = []
        for f in filas:
            v = dict(f)
            v["partidas"] = con.execute(
                "SELECT COUNT(*) FROM partidas WHERE version_id=?", (f["id"],)).fetchone()[0]
            v["recursos"] = con.execute(
                "SELECT COUNT(*) FROM recursos WHERE version_id=?", (f["id"],)).fetchone()[0]
            v["normas"] = con.execute(
                "SELECT COUNT(*) FROM normas_partida WHERE version_id=?", (f["id"],)).fetchone()[0]
            v["descomponibles"] = con.execute(
                """SELECT COUNT(DISTINCT partida_id) FROM normas_partida WHERE version_id=?""",
                (f["id"],)).fetchone()[0]
            out.append(v)
        self._json({"versiones": out, "html_original_intacto": self._html_intacto()})

    @staticmethod
    def _html_intacto():
        import hashlib
        h = hashlib.sha256()
        with open(HTML, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest() == SHA_HTML

    def _api_partidas(self, con, q):
        texto = (q.get("q", [""])[0] or "").strip()
        version_id = q.get("version_id", [None])[0]
        limite = min(int(q.get("limit", [30])[0]), 200)
        sql = """SELECT p.codigo, p.descripcion, p.unidad, p.factor_unidad, p.capitulo,
                        p.costo_mat_mn, p.costo_mo_mn, p.costo_eq_mn, p.costo_total_mn,
                        p.costo_mat_mlc, vc.version, c.codigo AS catalogo
                 FROM partidas p JOIN versiones_catalogo vc ON vc.id = p.version_id
                 JOIN catalogos c ON c.id = vc.catalogo_id"""
        condiciones, params = [], []
        if version_id:
            condiciones.append("p.version_id = ?")
            params.append(version_id)
        if texto:
            condiciones.append("(p.codigo LIKE ? OR p.descripcion LIKE ? COLLATE NOCASE)")
            params += [f"%{texto}%", f"%{texto}%"]
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " ORDER BY p.codigo LIMIT ?"
        params.append(limite)
        filas = [dict(r) for r in con.execute(sql, params).fetchall()]
        self._json({"q": texto, "resultados": filas, "n": len(filas)})

    def _api_partida(self, con, codigo, q):
        version_id = q.get("version_id", [None])[0]
        fila = con.execute("""
            SELECT p.*, vc.version, vc.fecha_importacion, vc.fuente_archivo, vc.fuente_sha256,
                   c.codigo AS catalogo
            FROM partidas p JOIN versiones_catalogo vc ON vc.id = p.version_id
            JOIN catalogos c ON c.id = vc.catalogo_id
            WHERE p.codigo = ?""" + (" AND p.version_id=?" if version_id else "") + """
            ORDER BY vc.fecha_importacion DESC LIMIT 1""",
            (codigo, version_id) if version_id else (codigo,)).fetchone()
        if not fila:
            return self._json({"error": "partida no encontrada", "codigo": codigo}, 404)
        p = dict(fila)

        # descomposición: normas + recurso + componentes de compuestos
        normas = []
        for n in con.execute("""
                SELECT np.tipo_recurso_id, tr.codigo AS tipo, np.codigo_recurso, np.coeficiente,
                       np.cod_norma, np.um_norma, r.descripcion AS recurso_desc, r.unidad AS recurso_um,
                       r.precio_mn, r.precio_mlc
                FROM normas_partida np
                JOIN tipos_recurso tr ON tr.id = np.tipo_recurso_id
                LEFT JOIN recursos r ON r.version_id = np.version_id
                     AND r.tipo_id = np.tipo_recurso_id AND r.codigo = np.codigo_recurso
                WHERE np.partida_id = ? ORDER BY tr.id, np.codigo_recurso""",
                (p["id"],)).fetchall():
            n = dict(n)
            componentes = []
            if n["tipo"] in ("juego", "semielaborado"):
                for c in con.execute("""
                        SELECT cr.codigo_componente, tr2.codigo AS tipo_componente, cr.coeficiente,
                               r2.descripcion, r2.unidad, r2.precio_mn
                        FROM componentes_recurso cr
                        JOIN tipos_recurso tr2 ON tr2.id = cr.tipo_componente_id
                        LEFT JOIN recursos r2 ON r2.version_id = cr.version_id
                             AND r2.tipo_id = cr.tipo_componente_id AND r2.codigo = cr.codigo_componente
                        WHERE cr.recurso_id = (SELECT id FROM recursos WHERE version_id=? AND codigo=?
                                               AND tipo_id=(SELECT id FROM tipos_recurso WHERE codigo=?))
                        ORDER BY tr2.id, cr.codigo_componente""",
                        (p["version_id"], n["codigo_recurso"], n["tipo"])).fetchall():
                    c = dict(c)
                    c["subtotal"] = (c["coeficiente"] or 0) * (c["precio_mn"] or 0)
                    componentes.append(c)
            n["subtotal"] = (n["coeficiente"] or 0) * (n["precio_mn"] or 0)
            n["componentes"] = componentes
            normas.append(n)

        # subtotales por tipo (Decimal para la verificación, float para la respuesta)
        from decimal import Decimal
        sumas, n_terms, suma_abs = {}, 0, 0.0
        for n in normas:
            d = (Decimal(str(n["coeficiente"] or 0)) * Decimal(str(n["precio_mn"] or 0)))
            sumas[n["tipo"]] = sumas.get(n["tipo"], Decimal(0)) + d
            n_terms += 1
            suma_abs += abs(float(d))
        import math
        tol = max(0.0001 * max(1, n_terms), suma_abs * 6e-8)

        def cmp(almacenado, recalculado):
            if almacenado is None:
                return None
            delta = float(recalculado) - almacenado
            return {"almacenado": almacenado, "recalculado": float(recalculado),
                    "delta": delta, "coincide": abs(delta) <= tol, "tolerancia": tol}

        verificacion = {
            "cmmn": cmp(p["costo_mat_mn"], sumas.get("material", 0) + sumas.get("juego", 0)
                        + sumas.get("semielaborado", 0)),
            "chmn": cmp(p["costo_mo_mn"], sumas.get("mano_obra", 0)),
            "cemn": cmp(p["costo_eq_mn"], sumas.get("equipo", 0)),
            "regla": "|Δ| ≤ max(0.0001·N, Σ|coef·precio|·6e-8) — tolerancia por número de "
                     "términos y magnitud, documentada en docs/FASE_III_INTEGRACION.md",
        }
        # el mismo código en otras versiones (comparación de precios)
        otras = [dict(r) for r in con.execute("""
                SELECT vc.version, c.codigo AS catalogo, p.costo_total_mn, p.unidad
                FROM partidas p JOIN versiones_catalogo vc ON vc.id=p.version_id
                JOIN catalogos c ON c.id=vc.catalogo_id
                WHERE p.codigo=? AND p.version_id != ? ORDER BY vc.id""", (codigo, p["version_id"]))]

        self._json({"partida": p, "normas": normas,
                    "subtotales": {k: float(v) for k, v in sumas.items()},
                    "verificacion": verificacion, "otras_versiones": otras,
                    "html_original_intacto": self._html_intacto()})

    # ------------------------------------------------------------------ III-C
    @staticmethod
    def _version_normas_defecto(con):
        """Versión PRECODI con normas más reciente (orden documentado):
        2017-raíz > 2011-sbd2008 > 2007-v7.22 > 2007-v7.21."""
        filas = con.execute("""
            SELECT vc.id, vc.version FROM versiones_catalogo vc
            JOIN catalogos c ON c.id = vc.catalogo_id
            WHERE c.codigo = 'PRECODI'""").fetchall()
        con_normas = [f for f in filas if con.execute(
            "SELECT COUNT(*) FROM normas_partida WHERE version_id=?", (f["id"],)).fetchone()[0] > 0]
        if not con_normas:
            return None
        return sorted(con_normas, key=lambda f: f["version"], reverse=True)[0]["id"]

    @staticmethod
    def _version_recursos_defecto(con):
        """MISIÓN V — versión por defecto para búsquedas de recursos del
        nomenclador (endpoint /api/recursos). Orden documentado: la versión de
        normas por defecto SI tiene nomenclador; si no, la de importación más
        reciente que sí tenga recursos. Con la BD completa: PRECODI 2017-raíz;
        solo con la base 2025: PRECONS_III 2025-06-06 (documentado en el
        INFORME_FASE_V: regeneración parcial tras pérdida de fuentes)."""
        vn = Manejador._version_normas_defecto(con)
        if vn is not None and con.execute(
                "SELECT COUNT(*) FROM recursos WHERE version_id=?", (vn,)).fetchone()[0] > 0:
            return vn
        fila = con.execute("""
            SELECT vc.id FROM versiones_catalogo vc
            WHERE (SELECT COUNT(*) FROM recursos WHERE version_id=vc.id) > 0
            ORDER BY vc.fecha_importacion DESC, vc.id DESC LIMIT 1""").fetchone()
        return fila[0] if fila else None

    def _api_recursos(self, con, q):
        """MISIÓN V (S-052/S-050) — búsqueda del NOMENCLADOR de recursos para
        «añadir recurso propio» a la especificación de un A.C. del presupuesto.

        SOLO LECTURA y 100 % aditivo: no modifica los endpoints de III-B/III-C
        ni sus contratos. Parámetros:
          q=            texto (código o descripción, LIKE, sin distinguir mayúsculas)
          tipo=         material | mano_obra | equipo | juego | semielaborado
          version_id=   versión del nomenclador (default: _version_recursos_defecto)
          limit=        máx. 200
        Respuesta: cada recurso con tipo, código, descripción, um, precio_mn
        (null → aviso explícito «sin precio», nunca se inventa) y versiones
        donde el mismo código existe como otro tipo (ambigüedad, estilo III-C)."""
        texto = (q.get("q", [""])[0] or "").strip()
        tipo = (q.get("tipo", [""])[0] or "").strip()
        version_id = q.get("version_id", [None])[0]
        try:
            limite = min(int(q.get("limit", [30])[0]), 200)
        except ValueError:
            limite = 30
        if version_id is None:
            version_id = self._version_recursos_defecto(con)
            if version_id is None:
                return self._json({"error": "ninguna versión con recursos en la BD"}, 404)
        version_id = int(version_id)

        tipo_id = None
        if tipo:
            f = con.execute("SELECT id FROM tipos_recurso WHERE codigo=?", (tipo,)).fetchone()
            if not f:
                tipos = [dict(r) for r in con.execute(
                    "SELECT codigo, nombre FROM tipos_recurso ORDER BY id")]
                return self._json({"error": "tipo desconocido", "tipos_validos": tipos}, 400)
            tipo_id = f[0]

        sql = """SELECT r.tipo_id, tr.codigo AS tipo, tr.nombre AS tipo_nombre,
                        r.codigo, r.descripcion, r.unidad, r.precio_mn, r.precio_mlc
                 FROM recursos r JOIN tipos_recurso tr ON tr.id = r.tipo_id
                 WHERE r.version_id = ?"""
        params = [version_id]
        if tipo_id:
            sql += " AND r.tipo_id = ?"
            params.append(tipo_id)
        if texto:
            sql += " AND (r.codigo LIKE ? OR r.descripcion LIKE ? COLLATE NOCASE)"
            params += [f"%{texto}%", f"%{texto}%"]
        sql += " ORDER BY tr.id, r.codigo LIMIT ?"
        params.append(limite)

        resultados = []
        for r in con.execute(sql, params).fetchall():
            r = dict(r)
            r["sin_precio"] = r["precio_mn"] is None
            # ambigüedad: el mismo código existe como OTRO tipo en esta versión
            # (estilo III-C: advertir, nunca descartar en silencio)
            otros = [x[0] for x in con.execute(
                """SELECT tr2.codigo FROM recursos r2 JOIN tipos_recurso tr2 ON tr2.id=r2.tipo_id
                   WHERE r2.version_id=? AND r2.codigo=? AND r2.tipo_id != ? LIMIT 3""",
                (version_id, r["codigo"], r["tipo_id"]))]
            r["mismo_codigo_otro_tipo"] = otros
            resultados.append(r)

        ver = con.execute("""SELECT vc.version, vc.fecha_importacion, c.codigo AS catalogo
                              FROM versiones_catalogo vc JOIN catalogos c ON c.id=vc.catalogo_id
                              WHERE vc.id=?""", (version_id,)).fetchone()
        self._json({
            "q": texto, "tipo": tipo or None, "n": len(resultados),
            "version_id": version_id,
            "version": {"catalogo": ver["catalogo"], "version": ver["version"]} if ver else None,
            "resultados": resultados,
            "html_original_intacto": self._html_intacto(),
        })

    def _api_descomposicion(self, con, codigo, q):
        """MISIÓN III-C — payload de la descomposición para la pestaña Recursos.

        Reutiliza el esquema existente (normas_partida / recursos /
        componentes_recurso / tipos_recurso); NO crea entidades nuevas y NO
        modifica los endpoints de III-B. Añade:
          - resolución del precio por versión fuente (precio_version_id),
          - advertencias explícitas (referencias sin resolver, códigos
            duplicados, unidades distintas entre versiones, ambigüedades de
            tipo), conservando siempre el dato de origen,
          - descomposición anidada de juegos y semielaborados,
          - verificación contra los costos almacenados (solo cuando los
            precios son de la misma versión) con la tolerancia documentada,
          - comparación de la misma partida en otras versiones.
        """
        version_id = q.get("version_id", [None])[0]
        if version_id is None:
            version_id = self._version_normas_defecto(con)
            if version_id is None:
                # MISIÓN V: degradación honesta cuando la BD no tiene normas
                # (regeneración parcial documentada). Con la BD completa el
                # comportamiento es idéntico al de III-C (resuelve 2017-raíz).
                return self._json({
                    "error": "ninguna versión con normas disponible en la BD "
                             "(solo PRECOST 2025, sin normas de composición: "
                             "regeneración parcial, ver INFORME_FASE_V)",
                    "codigo": codigo}, 404)
        version_id = int(version_id)
        precio_version_id = int(q.get("precio_version_id", [version_id])[0])

        fila = con.execute("""
            SELECT p.*, vc.version, vc.fecha_importacion, vc.fuente_archivo, vc.fuente_sha256,
                   c.codigo AS catalogo
            FROM partidas p JOIN versiones_catalogo vc ON vc.id = p.version_id
            JOIN catalogos c ON c.id = vc.catalogo_id
            WHERE p.codigo = ? AND p.version_id = ?""", (codigo, version_id)).fetchone()
        if not fila:
            otras = [dict(r) for r in con.execute("""
                SELECT vc.id AS version_id, vc.version FROM partidas p
                JOIN versiones_catalogo vc ON vc.id = p.version_id
                WHERE p.codigo = ? ORDER BY vc.id""", (codigo,))]
            return self._json({"error": "partida no encontrada en la versión solicitada",
                               "codigo": codigo, "versiones_disponibles": otras}, 404)
        p = dict(fila)

        advertencias = []
        componentes, duplicados = [], []
        vistos = {}
        for n in con.execute("""
                SELECT np.tipo_recurso_id, tr.codigo AS tipo, tr.nombre AS tipo_nombre,
                       np.codigo_recurso, np.coeficiente, np.cod_norma, np.um_norma,
                       r.descripcion, r.unidad AS unidad, r.precio_mn AS precio_propio,
                       pr.descripcion AS desc_precio, pr.unidad AS unidad_precio,
                       pr.precio_mn AS precio_mn, pr.tipo_id AS tipo_precio_id
                FROM normas_partida np
                JOIN tipos_recurso tr ON tr.id = np.tipo_recurso_id
                LEFT JOIN recursos r ON r.version_id = np.version_id
                     AND r.tipo_id = np.tipo_recurso_id AND r.codigo = np.codigo_recurso
                LEFT JOIN recursos pr ON pr.version_id = ?
                     AND pr.tipo_id = np.tipo_recurso_id AND pr.codigo = np.codigo_recurso
                WHERE np.partida_id = ? AND np.version_id = ?
                ORDER BY tr.id, np.codigo_recurso""",
                (precio_version_id, p["id"], version_id)).fetchall():
            n = dict(n)
            clave = (n["tipo"], n["codigo_recurso"])
            vistos[clave] = vistos.get(clave, 0) + 1
            if vistos[clave] == 2:
                duplicados.append({"tipo": n["tipo"], "codigo": n["codigo_recurso"]})
            comp = {
                "tipo": n["tipo"], "tipo_nombre": n["tipo_nombre"],
                "codigo": n["codigo_recurso"], "descripcion": n["descripcion"],
                "unidad": n["unidad"], "coeficiente": n["coeficiente"],
                "cod_norma": n["cod_norma"], "um_norma": n["um_norma"],
                "precio_mn": n["precio_mn"], "resuelto": n["descripcion"] is not None,
                "precio_resuelto": n["precio_mn"] is not None,
                "hijos": [],
            }
            if not comp["resuelto"]:
                comp["advertencia"] = ("referencia no resuelta en el nomenclador de "
                                       f"la versión {p['version']}: se conserva código y "
                                       "coeficiente de origen")
                advertencias.append(f"{n['tipo']} {n['codigo_recurso']}: sin nomenclador "
                                    f"en versión {p['version']}")
            elif not comp["precio_resuelto"]:
                amb = con.execute("""
                    SELECT tr.codigo FROM recursos r JOIN tipos_recurso tr ON tr.id = r.tipo_id
                    WHERE r.version_id=? AND r.codigo=? AND r.tipo_id != ? LIMIT 1""",
                    (precio_version_id, n["codigo_recurso"], n["tipo_recurso_id"])).fetchone()
                comp["advertencia"] = (
                    f"sin precio en la versión de precios solicitada"
                    + (f" (el código existe allí como tipo «{amb[0]}») — se usa el precio "
                       "propio de la versión de la norma" if amb else
                       " — se usa el precio propio de la versión de la norma"))
                # precio de respaldo: nomenclador de la propia versión de la norma
                comp["precio_mn"] = n["precio_propio"]
                comp["precio_respaldo"] = True
                advertencias.append(f"{n['tipo']} {n['codigo_recurso']}: sin precio en "
                                    "la versión de precios seleccionada")
            elif n["unidad_precio"] and n["unidad"] and n["unidad_precio"] != n["unidad"]:
                comp["advertencia"] = (f"unidad distinta entre versiones: norma "
                                       f"«{n['unidad']}» vs precios «{n['unidad_precio']}»")
            if comp["precio_mn"] is not None:
                comp["importe"] = (n["coeficiente"] or 0) * comp["precio_mn"]
            else:
                comp["importe"] = None
            # descomposición anidada de juegos y semielaborados (F7/F8 del modelo)
            if n["tipo"] in ("juego", "semielaborado") and n["descripcion"] is not None:
                for h in con.execute("""
                        SELECT tr2.codigo AS tipo, tr2.nombre AS tipo_nombre,
                               cr.codigo_componente, cr.coeficiente,
                               r2.descripcion, r2.unidad, pr2.precio_mn,
                               pr2.unidad AS unidad_precio
                        FROM componentes_recurso cr
                        JOIN tipos_recurso tr2 ON tr2.id = cr.tipo_componente_id
                        LEFT JOIN recursos r2 ON r2.version_id = cr.version_id
                             AND r2.tipo_id = cr.tipo_componente_id
                             AND r2.codigo = cr.codigo_componente
                        LEFT JOIN recursos pr2 ON pr2.version_id = ?
                             AND pr2.tipo_id = cr.tipo_componente_id
                             AND pr2.codigo = cr.codigo_componente
                        WHERE cr.recurso_id = (SELECT id FROM recursos WHERE version_id=?
                                               AND codigo=? AND tipo_id=?)
                        ORDER BY tr2.id, cr.codigo_componente""",
                        (precio_version_id, version_id, n["codigo_recurso"],
                         n["tipo_recurso_id"])).fetchall():
                    h = dict(h)
                    hijo = {
                        "tipo": h["tipo"], "tipo_nombre": h["tipo_nombre"],
                        "codigo": h["codigo_componente"], "descripcion": h["descripcion"],
                        "unidad": h["unidad"], "coeficiente": h["coeficiente"],
                        "precio_mn": h["precio_mn"],
                        "resuelto": h["descripcion"] is not None,
                        "precio_resuelto": h["precio_mn"] is not None,
                    }
                    if h["unidad_precio"] and h["unidad"] and h["unidad_precio"] != h["unidad"]:
                        hijo["advertencia"] = (f"unidad distinta entre versiones: norma "
                                               f"«{h['unidad']}» vs precios «{h['unidad_precio']}»")
                    hijo["importe"] = ((h["coeficiente"] or 0) * h["precio_mn"]
                                       if h["precio_mn"] is not None else None)
                    comp["hijos"].append(hijo)
            componentes.append(comp)

        if duplicados:
            for d in duplicados:
                advertencias.append(f"código duplicado en la norma: {d['tipo']} {d['codigo']} "
                                    "(se muestran todas las filas de origen)")

        # subtotales por tipo sobre componentes de primer nivel (modelo F1/F2/F3)
        from decimal import Decimal
        subtotales, n_terms, suma_abs = {}, 0, 0.0
        for c in componentes:
            if c["importe"] is None:
                continue
            d = Decimal(str(c["coeficiente"] or 0)) * Decimal(str(c["precio_mn"]))
            subtotales[c["tipo"]] = subtotales.get(c["tipo"], Decimal(0)) + d
            n_terms += 1
            suma_abs += abs(float(d))
        total = sum(subtotales.values(), Decimal(0))

        # verificación SOLO con precios de la misma versión (comparables con lo almacenado)
        verificacion = None
        if precio_version_id == version_id and componentes:
            import math
            tol = max(0.0001 * max(1, n_terms), suma_abs * 6e-8)

            def cmp(almacenado, recalculado):
                if almacenado is None:
                    return None
                delta = float(recalculado) - almacenado
                return {"almacenado": almacenado, "recalculado": float(recalculado),
                        "delta": delta, "coincide": abs(delta) <= tol, "tolerancia": tol}
            verificacion = {
                "cmmn": cmp(p["costo_mat_mn"],
                            subtotales.get("material", 0) + subtotales.get("juego", 0)
                            + subtotales.get("semielaborado", 0)),
                "chmn": cmp(p["costo_mo_mn"], subtotales.get("mano_obra", 0)),
                "cemn": cmp(p["costo_eq_mn"], subtotales.get("equipo", 0)),
                "regla": "|Δ| ≤ max(0.0001·N, Σ|coef·precio|·6e-8) — tolerancia por número "
                         "de términos y magnitud (docs/FASE_III_INTEGRACION.md)",
            }

        # informe de compatibilidad de la fuente de precios
        fuentes_precio = None
        if precio_version_id != version_id:
            tot = len(componentes)
            resueltos = sum(1 for c in componentes if c["precio_resuelto"])
            unidades_distintas = []
            for c in componentes:
                if c["resuelto"] and c["precio_resuelto"] and "advertencia" in c and \
                        "unidad distinta" in c["advertencia"]:
                    unidades_distintas.append({"tipo": c["tipo"], "codigo": c["codigo"]})
            vn = con.execute("""SELECT vc.version, c.codigo AS catalogo FROM versiones_catalogo vc
                                JOIN catalogos c ON c.id=vc.catalogo_id WHERE vc.id=?""",
                             (version_id,)).fetchone()
            vp = con.execute("""SELECT vc.version, c.codigo AS catalogo FROM versiones_catalogo vc
                                JOIN catalogos c ON c.id=vc.catalogo_id WHERE vc.id=?""",
                             (precio_version_id,)).fetchone()
            fuentes_precio = {
                "version_normas": dict(vn) if vn else None,
                "version_precios": dict(vp) if vp else None,
                "resueltos": resueltos, "total": tot,
                "porcentaje": round(100.0 * resueltos / tot, 1) if tot else 0.0,
                "sin_resolver": [f"{c['tipo']} {c['codigo']}" for c in componentes
                                 if not c["precio_resuelto"]],
                "recursos_unidad_distinta": unidades_distintas,
            }

        otras = [dict(r) for r in con.execute("""
                SELECT vc.id AS version_id, c.codigo AS catalogo, vc.version,
                       p.costo_total_mn, p.unidad,
                       (SELECT COUNT(*) FROM normas_partida np
                         WHERE np.partida_id = p.id AND np.version_id = p.version_id) AS n_normas
                FROM partidas p JOIN versiones_catalogo vc ON vc.id=p.version_id
                JOIN catalogos c ON c.id=vc.catalogo_id
                WHERE p.codigo=? AND p.version_id != ? ORDER BY vc.id""",
                (codigo, version_id))]

        self._json({
            "partida": p, "tiene_norma": bool(componentes),
            "componentes": componentes,
            "subtotales": {k: float(v) for k, v in subtotales.items()},
            "total": float(total),
            "verificacion": verificacion, "fuentes_precio": fuentes_precio,
            "duplicados": duplicados, "advertencias": advertencias,
            "otras_versiones": otras,
            "html_original_intacto": self._html_intacto(),
        })

    def _api_normas_disponibles(self, con, q):
        """MISIÓN III-C — ¿qué códigos del presupuesto tienen norma en una versión?
        Consulta por lotes para marcar las partidas del editor sin pedir la
        descomposición completa de cada una."""
        codigos = [c.strip() for c in (q.get("codigos", [""])[0] or "").split(",") if c.strip()]
        if not codigos:
            return self._json({"error": "parámetro codigos requerido (separados por coma)"}, 400)
        if len(codigos) > 500:
            return self._json({"error": "máximo 500 códigos por consulta"}, 400)
        version_id = q.get("version_id", [None])[0]
        if version_id is None:
            version_id = self._version_normas_defecto(con)
            if version_id is None:
                # MISIÓN V: degradación honesta (BD sin normas, ver arriba)
                return self._json({
                    "error": "ninguna versión con normas disponible en la BD "
                             "(regeneración parcial, ver INFORME_FASE_V)",
                    "codigos": {}}, 400)
        version_id = int(version_id)
        ph = ",".join(["?"] * len(codigos))
        filas = con.execute(f"""
            SELECT p.codigo,
                   (SELECT COUNT(*) FROM normas_partida np
                     WHERE np.partida_id = p.id AND np.version_id = p.version_id) AS n_normas
            FROM partidas p WHERE p.version_id = ? AND p.codigo IN ({ph})""",
            (version_id, *codigos)).fetchall()
        mapa = {f["codigo"]: {"en_catalogo": True, "tiene_norma": f["n_normas"] > 0,
                              "n_normas": f["n_normas"]} for f in filas}
        for c in codigos:
            if c not in mapa:
                mapa[c] = {"en_catalogo": False, "tiene_norma": False, "n_normas": 0}
        self._json({"version_id": version_id, "codigos": mapa,
                    "html_original_intacto": self._html_intacto()})

    def _api_stats(self, con):
        out = {}
        for f in con.execute("""SELECT vc.id, c.codigo||'/'||vc.version AS clave FROM versiones_catalogo vc
                                JOIN catalogos c ON c.id=vc.catalogo_id ORDER BY vc.id"""):
            conteo = {}
            for tabla in ("partidas", "recursos", "normas_partida", "componentes_recurso"):
                conteo[tabla] = con.execute(
                    f"SELECT COUNT(*) FROM {tabla} WHERE version_id=?", (f["id"],)).fetchone()[0]
            out[f["clave"]] = conteo
        self._json({"stats": out})


def main():
    ap = argparse.ArgumentParser(description="Capa de acceso local PRECODI para PRECOST (solo lectura)")
    ap.add_argument("--puerto", type=int, default=8765)
    ap.add_argument("--bd", default=BD_DEFECTO)
    args = ap.parse_args()

    if not os.path.exists(args.bd):
        sys.exit(f"No existe {args.bd}: ejecute antes scripts/importar_precodi.py --todas")
    Manejador.bd = args.bd
    srv = ThreadingHTTPServer(("127.0.0.1", args.puerto), Manejador)
    print(f"Capa de acceso local PRECODI (SOLO LECTURA, 127.0.0.1)")
    print(f"  Base:   {args.bd}")
    print(f"  App:    http://127.0.0.1:{args.puerto}/  (PRECOST original + overlay aditivo)")
    print(f"  API:    http://127.0.0.1:{args.puerto}/api/versiones")
    print(f"  HTML original en disco intacto: {Manejador._html_intacto()}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")


if __name__ == "__main__":
    sys.exit(main())
