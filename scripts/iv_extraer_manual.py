#!/usr/bin/env python3
"""MISIÓN IV — Línea B: extraer texto e imágenes del Manual Básico SIECONS.pdf.

El manual del fabricante es la evidencia primaria de la matriz de paridad.
Este script extrae:
  - texto por página (docs/datos/manual_siecons_texto/)
  - imágenes (capturas de pantalla) por página con su contexto
  - inventario JSON con metadatos de página
"""
import json
from pathlib import Path

import fitz  # PyMuPDF

PDF = Path("/home/z/my-project/work/siecons_extract/payload/"
           "App/MANUAL/Manual SIECONS/Manual Básico SIECONS.pdf")
SALIDA = Path("/home/z/my-project/precost/docs/datos/manual_siecons")
SALIDA.mkdir(parents=True, exist_ok=True)
(SALIDA / "imagenes").mkdir(exist_ok=True)


def main():
    doc = fitz.open(PDF)
    print(f"Manual: {PDF.name}")
    print(f"Páginas: {len(doc)}")
    print(f"Metadatos: {doc.metadata}")

    inventario = []
    todo_texto = []
    total_imagenes = 0
    for i, pagina in enumerate(doc):
        texto = pagina.get_text("text")
        todo_texto.append(f"\n===== PÁGINA {i + 1} =====\n{texto}")
        # imágenes de la página
        imagenes = pagina.get_images(full=True)
        n_img_pag = 0
        for j, img in enumerate(imagenes):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.width < 60 or pix.height < 60:
                    continue  # ignorar iconitos
                if pix.n - pix.alpha >= 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                nombre = f"pag{i + 1:03d}_img{j + 1:02d}.png"
                pix.save(SALIDA / "imagenes" / nombre)
                n_img_pag += 1
                total_imagenes += 1
            except Exception as e:
                print(f"  [pág {i+1} img {j+1}] error: {e}")
        inventario.append(dict(pagina=i + 1, caracteres=len(texto),
                               imagenes=n_img_pag))
        if n_img_pag:
            print(f"  pág {i + 1}: {len(texto):,} car., {n_img_pag} imagen(es)")

    (SALIDA / "manual_texto_completo.txt").write_text(
        "".join(todo_texto), encoding="utf-8")
    (SALIDA / "inventario.json").write_text(
        json.dumps(dict(pdf=str(PDF), paginas=len(doc),
                        total_imagenes=total_imagenes,
                        por_pagina=inventario), ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"\nTotal: {len(doc)} páginas, {total_imagenes} imágenes extraídas")
    print(f"Texto completo: {sum(len(t) for t in todo_texto):,} caracteres")
    print(f"Salida: {SALIDA}")


if __name__ == "__main__":
    main()
