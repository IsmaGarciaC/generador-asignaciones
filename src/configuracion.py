import logging
import sys
from pathlib import Path


def obtener_ruta_base() -> Path:
    """
    Obtiene la ruta base del ejecutable o del script.
    Esto permite que el programa sea portable al compilarse con PyInstaller.
    """
    if getattr(sys, "frozen", False):
        # Si está congelado por PyInstaller, sys.executable apunta al .exe
        return Path(sys.executable).parent
    else:
        # Si se ejecuta como script, __file__ apunta a src/configuracion.py
        # El padre del padre es el directorio raíz del proyecto
        return Path(__file__).resolve().parent.parent


BASE_DIR = obtener_ruta_base()


def configurar_logging():
    """
    Configura el sistema de logging para escribir en un archivo y en la consola.
    """
    log_file = BASE_DIR / "generador.log"

    logger = logging.getLogger("generador_asignaciones")
    logger.setLevel(logging.DEBUG)

    # Evitar handlers duplicados si se llama varias veces
    if not logger.handlers:
        # File handler (INFO y superior al archivo)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.INFO)

        # Console handler (DEBUG y superior a consola)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


logger = configurar_logging()
