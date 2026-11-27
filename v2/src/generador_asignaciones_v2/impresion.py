"""Conversión local del Excel a PDF e imágenes de las páginas impresas."""

import os
import shutil
import subprocess
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock

from openpyxl import load_workbook

_PDFIUM = Lock()
DPI = 180
TIEMPO_CONVERSION = 60


def localizar_libreoffice() -> Path:
    indicada = os.environ.get("ASIGNACIONES_LIBREOFFICE")
    if indicada:
        ruta = Path(indicada)
        if ruta.is_absolute() and ruta.is_file():
            return ruta
        raise ValueError("ASIGNACIONES_LIBREOFFICE debe indicar la ruta completa a soffice.com.")
    if os.name == "nt":
        for clave in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
            if carpeta := os.environ.get(clave):
                ruta = Path(carpeta) / "LibreOffice" / "program" / "soffice.com"
                if ruta.is_file():
                    return ruta
    ejecutable = shutil.which("soffice.com" if os.name == "nt" else "soffice")
    if ejecutable:
        return Path(ejecutable)
    raise ValueError("Para exportar PDF y PNG, instala LibreOffice Calc en Windows.")


def convertir_a_pdf(excel: Path) -> Path:
    ejecutable = localizar_libreoffice()
    excel = excel.resolve()
    pdf = excel.with_suffix(".pdf")
    # Calc crea archivos internos bajo el perfil. Una ruta corta evita el límite de Windows.
    with TemporaryDirectory(prefix="asignaciones-") as temporal:
        carpeta = Path(temporal).resolve()
        entrada = carpeta / "programa.xlsx"
        with closing(load_workbook(excel)) as libro:
            hoja = libro["Audio y Video"]
            # Conserva A4 vertical con el ajuste de ancho para el encabezado combinado.
            hoja.page_setup.paperSize = hoja.page_setup.paperSize or hoja.PAPERSIZE_A4
            hoja.page_setup.orientation = hoja.page_setup.orientation or hoja.ORIENTATION_PORTRAIT
            hoja.sheet_properties.pageSetUpPr.fitToPage = True
            hoja.page_setup.fitToWidth = 1
            hoja.page_setup.fitToHeight = 0
            libro.save(entrada)
        uri = (carpeta / "perfil").as_uri()
        try:
            proceso = subprocess.run(
                [
                    str(ejecutable),
                    f"-env:UserInstallation={uri}",
                    "--headless",
                    "--norestore",
                    "--convert-to",
                    "pdf:calc_pdf_Export",
                    "--outdir",
                    str(carpeta),
                    str(entrada),
                ],
                capture_output=True,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=TIEMPO_CONVERSION,
            )
        except subprocess.TimeoutExpired as error:
            raise ValueError("LibreOffice agotó el tiempo para exportar el PDF.") from error
        salida = entrada.with_suffix(".pdf")
        if proceso.returncode or not salida.is_file() or salida.stat().st_size == 0:
            raise ValueError("LibreOffice no pudo generar el PDF del programa.")
        shutil.copyfile(salida, pdf)
    return pdf


def renderizar_paginas(pdf: Path) -> tuple[Path, ...]:
    try:
        from pypdfium2 import PdfDocument, PdfiumError
    except ImportError as error:
        raise ValueError("Actualiza las dependencias de V2 para exportar a PNG.") from error
    imagenes = []
    try:
        # PDFium comparte estado global. Una exportación por vez puede abrir y renderizar páginas.
        with _PDFIUM, closing(PdfDocument(pdf)) as documento:
            if len(documento) != 2:
                raise ValueError("El PDF debe contener una página por cada hoja del programa.")
            for numero, pagina in enumerate(documento, 1):
                ruta = pdf.with_name(f"{pdf.stem}-pagina-{numero:02d}.png")
                with closing(pagina), closing(pagina.render(scale=DPI / 72)) as mapa:
                    with closing(mapa.to_pil()) as imagen:
                        imagen.save(ruta, dpi=(DPI, DPI))
                imagenes.append(ruta)
    except ImportError as error:
        raise ValueError("Actualiza las dependencias de V2 para exportar a PNG.") from error
    except PdfiumError as error:
        raise ValueError("No se pudieron leer las páginas del PDF generado.") from error
    return tuple(imagenes)
