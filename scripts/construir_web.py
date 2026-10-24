#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MISIÓN VI — Constructor de la versión web estática para GitHub Pages.

Genera un artefacto público 100 % estático a partir del código fuente,
SIN modificar el HTML original protegido:

  dist/index.html        = app/PRECOST-v9.17.html + inyección de <script>
                           (rutas RELATIVAS, compatible con /Precost/)
  dist/overlay/*.js      = overlays con degradación offline diseñada

Decisiones técnicas (ver docs/INFORME_FASE_VI.md y README §Arquitectura):
  * El HTML original NUNCA se escribe: se lee, se inyecta en memoria y el
    resultado va a dist/. El original en app/ queda byte a byte intacto.
  * Se verifica el SHA-256 del original antes de construir: si cambia, el
    build FALLA (protección del activo protegido).
  * Se incluyen recursos.js y calculadora.js porque ambos degradan con
    aviso honesto cuando no hay servidor local (snapshots guardados,
    especificación manual S-050, edición S-052 cliente, calculadora S-080
    en modo embebido).
  * Se EXCLUYE precodi.js (buscador FAB del catálogo PRECODI): el 100 % de
    sus funciones requiere /api/* del servidor local; sin servidor las
    búsquedas quedarían colgadas en «Buscando…» sin mensaje. Excluirlo es
    la opción honesta; se documenta en el README.
  * No se copian bases de datos, pruebas, dumps ni documentos internos:
    el artefacto público solo contiene la aplicación y sus overlays.

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

# Overlays incluidos en la versión estática (degradación offline diseñada).
# VII: respaldo.js (S-005) es 100 % cliente — funciona igual en Pages y local.
OVERLAYS_WEB = ["recursos.js", "calculadora.js", "respaldo.js"]
# Overlay excluido: 100 % dependiente del servidor local (ver docstring).
OVERLAYS_EXCLUIDOS = ["precodi.js"]

# Inyección idéntica a la de scripts/servidor_precodi.py (rfind </body>),
# pero con rutas RELATIVAS para funcionar bajo /Precost/ de GitHub Pages.
PLANTILLA_INYECCION = (b'\n<script src="overlay/recursos.js" defer></script>\n'
                       b'<script src="overlay/calculadora.js" defer></script>\n'
                       b'<script src="overlay/respaldo.js" defer></script>\n')


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

    # --- 6. Resumen -----------------------------------------------------------
    resumen = {
        "index_html_bytes": os.path.getsize(os.path.join(destino, "index.html")),
        "overlays": OVERLAYS_WEB,
        "overlays_excluidos": OVERLAYS_EXCLUIDOS,
        "sha256_original_verificado": SHA_ORIGINAL,
        "salida": destino,
    }
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    print("OK: artefacto estático generado. El HTML original permanece intacto.")


if __name__ == "__main__":
    main()
