"""
Script de automatización para compilar el ejecutable portable con PyInstaller.
"""

import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def build():
    print("=" * 60)
    print("Iniciando compilación de Generador de Asignaciones...")
    print("=" * 60)

    # 1. Limpieza de compilaciones previas
    for folder in [BASE_DIR / "build", BASE_DIR / "dist"]:
        if folder.exists():
            print(f"Limpiando directorio {folder.name}...")
            shutil.rmtree(folder, ignore_errors=True)

    # 2. Comando de PyInstaller
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=GeneradorAsignaciones",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--collect-all=customtkinter",
        f"--paths={BASE_DIR / 'src'}",
        str(BASE_DIR / "src" / "interfaz_grafica.py"),
    ]

    print("\nEjecutando PyInstaller...")
    subprocess.run(cmd, check=True)

    # 3. Preparar paquete portable en dist/
    dist_dir = BASE_DIR / "dist"
    app_dir = dist_dir / "GeneradorAsignaciones"

    # Directorio de datos de la aplicación compilada
    target_data_dir = (app_dir / "data") if app_dir.exists() else (dist_dir / "data")
    target_data_dir.mkdir(parents=True, exist_ok=True)

    target_salida_dir = (app_dir / "salida") if app_dir.exists() else (dist_dir / "salida")
    target_salida_dir.mkdir(parents=True, exist_ok=True)

    # Copiar plantillas y catálogo de roles para distribución
    src_data = BASE_DIR / "data"
    for filename in ["roles.txt", "hermanos.example.json"]:
        source_file = src_data / filename
        if source_file.exists():
            shutil.copy2(source_file, target_data_dir / filename)
            print(f"Copiado recurso base: {filename} -> {target_data_dir.name}/")

    print("\n" + "=" * 60)
    print("¡Compilación finalizada con éxito!")
    print(f"El paquete portable se encuentra en: {app_dir if app_dir.exists() else dist_dir}")
    print("=" * 60)


if __name__ == "__main__":
    build()
