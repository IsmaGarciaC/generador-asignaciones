# Prueba de asignaciones mensuales con CP-SAT

Prototipo con datos ficticios para comprobar cobertura, dobletes, equidad experimental y rotación. Cada semana recibe las plazas requeridas directamente. Una semana cancelada se excluye por completo.

Desde la raíz, en Windows con CPython 3.12 x64:

```powershell
py -3.12 -m venv spikes/assignment_solver/venv
$solverPython = '.\spikes\assignment_solver\venv\Scripts\python.exe'
& $solverPython -m pip install -r spikes/assignment_solver/requirements.txt
& $solverPython -m pip check
& $solverPython -m pytest -q -c spikes/assignment_solver/pytest.ini spikes/assignment_solver
& $solverPython spikes/assignment_solver/medir.py --segundos 5
```

Si `py` no está en PATH, ejecuta `-m venv` con la ruta completa de tu intérprete. Para comprobar la compatibilidad con el stack de escritorio mediante el resolvedor:

```powershell
& $solverPython -m pip install --dry-run -r spikes/nicegui_desktop/requirements.txt -r spikes/assignment_solver/requirements.txt
```

Si ya tienes el entorno V1 con Python 3.12 y Pydantic, ejecuta `.\venv\Scripts\python.exe -B spikes/assignment_solver/comparar_v1.py` para reproducir la comparación de cobertura.

- `datos.py` genera escenarios deterministas y define personas, semanas e historial.
- `solver.py` construye el modelo y ejecuta las etapas de optimización.
- `evaluacion.py` verifica las restricciones y recalcula los resultados desde el plan materializado.
- `pruebas_solver.py` y `pytest.ini` contienen y aíslan la suite del prototipo.
- `medir.py` emite un resultado JSON por escenario, con métricas y cotas por etapa. `comparar_v1.py` ejecuta el motor V1 con el mismo padrón y ausencias ficticias.
- `requirements.txt` fija las versiones instaladas y `.gitignore` excluye el entorno y las cachés.

[Modelo, mediciones y limitaciones](RESULTADOS.md)
