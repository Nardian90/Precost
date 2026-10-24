#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MISIÓN VI/VIII — Constructor de la versión web estática para GitHub Pages.

Genera un artefacto público 100 % estático a partir del código fuente,
SIN modificar el HTML original protegido:

  dist/index.html        = app/PRECOST-v9.17.html + inyección de <script>
                           (rutas RELATIVAS, compatible con /Precost/)
  dist/overlay/*.js      = overlays (5) con degradación offline diseñada
  dist/data/*.json       = datos PRECODI/PRECOST embebidos (MISIÓN VIII)

Decisiones técnicas (ver docs/INFORME_FASE_VI.md, INFORME_FASE_VIII.md y
README §Arquitectura):
  * El HTML original NUNCA se escribe: se lee, se inyecta en memoria y el
    resultado va a dist/. El original en app/ queda byte a byte intacto.
  * Se verifica el SHA-256 del original antes de construir: si cambia, el
    build FALLA (protección del activo protegido).
  * MISIÓN VIII — paridad «literal» en la web: se incluyen los CINCO
    overlays. estatico.js (web-only, cargado primero) expone la capa de
    datos embebidos; precodi.js YA PUEDE incluirse porque TODOS sus fetch
    tienen .catch y resuelven desde dist/data cuando no hay servidor local
    (antes se excluía: sus búsquedas quedaban colgadas sin servidor).
  * dist/data/ se copia de app/web-datos/ (generado por
    scripts/generar_datos_web.py desde bd/precodi.db, conteos verificados).
    Se verifica el manifest (sha256 de cada archivo) al copiar: el artefacto
    publicado es exactamente el generado, sin deriva.
  * No se copian bases de datos, pruebas, dumps ni documentos internos:
    el artefacto público solo contiene la aplicación, sus overlays y los
    datos publicados.

Uso:
  python3 scripts/construir_web.py [--salida dist] [--repo RAÍZ]

Salida: 0 si el artefacto es válido; distinto de 0 ante cualquier problema.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys

# SHA-256 de referencia del HTML protegido (verificado en la auditoría de
# MISIÓN VI y en los registros de las misiones I–V; tag v9.17-original).
SHA_ORIGINAL = "50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2"

# Overlays incluidos en la versión estática.
# VIII: estatico.js PRIMERO (capa de datos embebidos, web-only) y precodi.js
# ahora SÍ incluido (todos sus fetch tienen .catch + fallback a dist/data).
OVERLAYS_WEB = ["estatico.js", "recursos.js", "calculadora.js", "respaldo.js", "precodi.js"]
# Overlay excluido: ninguno (MISIÓN VI excluía precodi.js; VIII lo integra).
OVERLAYS_EXCLUIDOS = []

# Datos embebidos (MISIÓN VIII): app/web-datos -> dist/data.
DIR_DATOS_FUENTE = "web-datos"
DIR_DATOS_DESTINO = "data"

# Inyección con rutas RELATIVAS para funcionar bajo /Precost/ de GitHub Pages.
# (estatico.js primero: la capa de datos debe existir antes de que los demás
# overlays la consulten en sus fallbacks.)
PLANTILLA_INYECCION = (b'\n<script src="overlay/estatico.js" defer></script>\n'
                       b'<script src="overlay/recursos.js" defer></script>\n'
                       b'<script src="overlay/calculadora.js" defer></script>\n'
                       b'<script src="overlay/respaldo.js" defer></script>\n'
                       b'<script src="overlay/precodi.js" defer></script>\n')


def sha256_de(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main():
    raiz_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description="Constructor de la versión estática de PRECOST para GitHub Pages")
    ap.add_argument("--repo", default=raiz_repo, help="raíz del repositorio (defecto: autodetección)")
    ap.add_argument("--salida", default="dist", help="directorio de salida (defecto: dist)")
    args = ap.parse_args()

    html_origen = os.path.join(args.repo, "app", "PRECOST-v9.17.html")
    dir_overlay = os.path.join(args.repo, "app", "overlay")
    destino = os.path.join(args.repo, args.salida) if not os.path.isabs(args.salida) else args.salida

    # --- 1. Verificación del activo protegido --------------------------------
    if not os.path.exists(html_origen):
        sys.exit(f"ERROR: no existe {html_origen}")
    real = sha256_de(html_origen)
    if real != SHA_ORIGINAL:
        sys.exit("ERROR: el HTML original ha cambiado (SHA-256 no coincide).\n"
                 f"  esperado: {SHA_ORIGINAL}\n"
                 f"  real:     {real}\n"
                 "  El build se detiene: el original debe permanecer intacto.")

    # --- 2. Reconstrucción limpia del directorio de salida -------------------
    if os.path.exists(destino):
        shutil.rmtree(destino)
    os.makedirs(os.path.join(destino, "overlay"), exist_ok=True)

    # --- 3. index.html = original + inyección (SOLO en memoria) --------------
    with open(html_origen, "rb") as f:
        contenido = f.read()
    i = contenido.rfind(b"</body>")
    if i < 0:
        sys.exit("ERROR: el HTML original no contiene </body>; no se puede inyectar.")
    contenido = contenido[:i] + PLANTILLA_INYECCION + contenido[i:]
    with open(os.path.join(destino, "index.html"), "wb") as f:
        f.write(contenido)

    # --- 4. Overlays con degradación offline ---------------------------------
    for nombre in OVERLAYS_WEB:
        origen = os.path.join(dir_overlay, nombre)
        if not os.path.exists(origen):
            sys.exit(f"ERROR: falta el overlay {origen}")
        shutil.copyfile(origen, os.path.join(destino, "overlay", nombre))

    # --- 4b. Datos embebidos (MISIÓN VIII) -----------------------------------
    #    app/web-datos/*.json -> dist/data/, con verificación de manifest
    dir_datos = os.path.join(args.repo, "app", DIR_DATOS_FUENTE)
    if not os.path.isdir(dir_datos) or not os.listdir(dir_datos):
        sys.exit(f"ERROR: faltan los datos embebidos en {dir_datos}: "
                 "ejecute scripts/generar_datos_web.py")
    dir_datos_dest = os.path.join(destino, DIR_DATOS_DESTINO)
    os.makedirs(dir_datos_dest, exist_ok=True)
    manifest_ruta = os.path.join(dir_datos, "manifest.json")
    if not os.path.exists(manifest_ruta):
        sys.exit("ERROR: falta app/web-datos/manifest.json (regenere los datos)")
    with open(manifest_ruta, encoding="utf-8") as fp:
        manifest = json.load(fp)
    for nombre in sorted(manifest["archivos"]):
        origen = os.path.join(dir_datos, nombre)
        shutil.copyfile(origen, os.path.join(dir_datos_dest, nombre))
        real = sha256_de(origen)
        if real != manifest["archivos"][nombre]["sha256"]:
            sys.exit(f"ERROR: {nombre} no coincide con el manifest "
                     f"(esperado {manifest['archivos'][nombre]['sha256'][:12]}, real {real[:12]}): "
                     "regenere con scripts/generar_datos_web.py")

    # --- 5. Verificación del artefacto ---------------------------------------
    #    a) el original en disco sigue intacto
    if sha256_de(html_origen) != SHA_ORIGINAL:
        sys.exit("ERROR: el HTML original resultó modificado durante el build.")
    #    b) sin bases de datos ni archivos privados en el artefacto
    prohibidos = []
    for raiz, _dirs, ficheros in os.walk(destino):
        for fn in ficheros:
            if fn.endswith((".db", ".sqlite", ".mdb", ".env", ".rar", ".zip", ".exe")):
                prohibidos.append(os.path.join(raiz, fn))
    if prohibidos:
        sys.exit("ERROR: archivos no permitidos en el artefacto público: " + ", ".join(prohibidos))
    #    c) los scripts inyectados existen con rutas relativas válidas
    for nombre in OVERLAYS_WEB:
        if not os.path.exists(os.path.join(destino, "overlay", nombre)):
            sys.exit(f"ERROR: el artefacto no contiene overlay/{nombre}")
    #    d) MISIÓN VIII: datos embebidos completos e íntegros en dist/data
    with open(os.path.join(destino, DIR_DATOS_DESTINO, "i.json"), encoding="utf-8") as fp:
        indice = json.load(fp)
    if not indice.get("versiones"):
        sys.exit("ERROR: dist/data/i.json sin versiones")
    for nombre in manifest["archivos"]:
        ruta_d = os.path.join(destino, DIR_DATOS_DESTINO, nombre)
        if not os.path.exists(ruta_d):
            sys.exit(f"ERROR: el artefacto no contiene data/{nombre}")
        if sha256_de(ruta_d) != manifest["archivos"][nombre]["sha256"]:
            sys.exit(f"ERROR: data/{nombre} diverge del manifest tras la copia")

    # --- 6. Resumen -----------------------------------------------------------
    total_datos = sum(manifest["archivos"][n]["bytes"] for n in manifest["archivos"])

    resumen = {
        "index_html_bytes": os.path.getsize(os.path.join(destino, "index.html")),
        "overlays": OVERLAYS_WEB,
        "datos_embebidos": {
            "archivos": len(manifest["archivos"]),
            "bytes": total_datos,
            "versiones": [v["version"] for v in indice["versiones"]],
        },

        "overlays_excluidos": OVERLAYS_EXCLUIDOS,
        "sha256_original_verificado": SHA_ORIGINAL,
        "salida": destino,
    }
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    print("OK: artefacto estático generado. El HTML original permanece intacto.")


if __name__ == "__main__":
    main()
