# Generador de Asignaciones V2

La aplicación abre en una ventana nativa de Windows y muestra los puestos y cupos de una semana habitual. El catálogo y la regla de dobletes están en `dominio/puestos.py` dentro del paquete. La ventana consume el catálogo desde `escritorio.py`.

## Preparación en Windows

Se necesita Windows x64, CPython 3.12 x64 y Microsoft Edge WebView2 Runtime. La preparación requiere conexión y se ejecuta una sola vez desde la raíz del repositorio en PowerShell.

```powershell
py -3.12 -m venv v2\venv
.\v2\venv\Scripts\python.exe -m pip install -e .\v2
.\v2\crear_acceso.cmd
```

Si `py` no está disponible, usa la ruta de tu instalación de Python 3.12 para ejecutar `-m venv v2\venv`.

Haz doble clic en **Generador de Asignaciones V2.lnk** dentro de `v2`. Puedes copiar ese acceso al escritorio. Al cerrar y volver a abrir, el acceso ejecuta el código instalado en modo editable. Si mueves el proyecto, vuelve a preparar el entorno y el acceso.

Para diagnosticar un fallo de inicio desde la raíz, ejecuta `.\v2\venv\Scripts\python.exe -m generador_asignaciones_v2`.

## Comprobaciones de desarrollo

```powershell
.\v2\venv\Scripts\python.exe -m pip install . -e './v2[dev]'
.\v2\venv\Scripts\python.exe -m pytest tests/ v2/tests/
.\v2\venv\Scripts\python.exe -m ruff check .
```

GitHub Actions ejecuta las dos suites y Ruff en Windows para los cambios hacia `v2`. Las pruebas del dominio V2 usan el catálogo y combinaciones en memoria. Consulta el [roadmap](../docs/roadmap.md) para el estado de las fases.
