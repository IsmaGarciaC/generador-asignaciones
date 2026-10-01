"""
Script de automatización para compilar el ejecutable portable con PyInstaller.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def build():
    print("=" * 60)
    print("Iniciando compilación de Generador de Asignaciones...")
    print("=" * 60)

    dist_dir = BASE_DIR / "dist"
    app_dir = dist_dir / "GeneradorAsignaciones"
    data_dir = app_dir / "data"
    salida_dir = app_dir / "salida"

    # 0. Respaldar datos de usuario existentes para no perderlos en la recompilación
    temp_dir = Path(tempfile.mkdtemp(prefix="asignaciones_backup_"))
    backup_data = temp_dir / "data"
    backup_salida = temp_dir / "salida"

    if data_dir.exists():
        shutil.copytree(data_dir, backup_data)
        print("Copia de seguridad de datos de usuario creada.")

    if salida_dir.exists():
        shutil.copytree(salida_dir, backup_salida)
        print("Copia de seguridad de archivos Excel generados creada.")

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
    target_data_dir = (app_dir / "data") if app_dir.exists() else (dist_dir / "data")
    target_data_dir.mkdir(parents=True, exist_ok=True)

    target_salida_dir = (app_dir / "salida") if app_dir.exists() else (dist_dir / "salida")
    target_salida_dir.mkdir(parents=True, exist_ok=True)

    # Copiar plantillas, catálogo de roles y datos existentes para distribución
    src_data = BASE_DIR / "data"
    if src_data.exists():
        for item in src_data.iterdir():
            if item.is_file():
                dest = target_data_dir / item.name
                shutil.copy2(item, dest)
                print(f"Copiado a distribución: {item.name} -> {target_data_dir.name}/")

    # Restaurar datos respaldados del usuario
    if backup_data.exists():
        for item in backup_data.iterdir():
            if item.is_file():
                dest = target_data_dir / item.name
                shutil.copy2(item, dest)
                print(f"Restaurado archivo de usuario: {item.name}")

    if backup_salida.exists():
        for item in backup_salida.iterdir():
            if item.is_file():
                dest = target_salida_dir / item.name
                shutil.copy2(item, dest)
                print(f"Restaurado reporte Excel: {item.name}")

    # Limpiar directorio temporal
    shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n" + "=" * 60)
    print("¡Compilación finalizada con éxito!")
    print(f"El paquete portable se encuentra en: {app_dir if app_dir.exists() else dist_dir}")
    print("=" * 60)


if __name__ == "__main__":
    build()
