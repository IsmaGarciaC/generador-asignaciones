# ⚡ Generador de Asignaciones (Congregation Dispatcher)

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Clean_Architecture-orange?style=flat)]()
[![Build](https://img.shields.io/badge/Build-PyInstaller-success?style=flat)]()
[![Testing](https://img.shields.io/badge/Testing-Pytest-blue?style=flat)]()
[![Code Style](https://img.shields.io/badge/Code_Style-Ruff-black?style=flat)]()

Motor heurístico de satisfacción de restricciones y balance de carga para la asignación mensual de puestos en la congregación. Diseñado para mitigar la fatiga operativa, balancear equitativamente cargas de trabajo mediante penalización multicriterio y exportar matrices listas para impresión y despliegue digital.

---

## 🏗️ Arquitectura y Stack Tecnológico

El proyecto ha sido refactorizado siguiendo principios de **Clean Architecture**, asegurando una alta mantenibilidad, tipado estricto y separación de responsabilidades:

*   **Dominio y Modelado (`src/modelos.py`):** Modelos de datos rigurosos utilizando `Pydantic` para validación en tiempo de ejecución.
*   **Acceso a Datos (`src/repositorio.py`):** Patrón Repositorio como única fuente de verdad para la entrada y salida de archivos JSON.
*   **Motor Heurístico (`src/motor_asignacion.py`):** Lógica pura de asignación (desacoplada de archivos y UI).
*   **Interfaz de Usuario (`src/interfaz_grafica.py`):** Construida con `CustomTkinter` para una UI nativa, con modo oscuro y aceleración de hardware.
*   **Exportación (`src/exportador_excel.py`):** Manipulación de celdas a bajo nivel con `openpyxl` para crear hojas A4 listas para imprimir.
*   **Empaquetado (`pyproject.toml` y `build.py`):** Gestión moderna de dependencias y script de compilación para distribución en `.exe` portátil.

## 🧠 Algoritmo y Resolución de Restricciones

El sistema opera como un despachador determinista guiado por heurísticas de costo mínimo. Para cada semana, el motor evalúa el espacio de candidatos utilizando una función de coste acumulado:

```text
Puntos(h) = CargaBase(h) + P[rol_mes] + P[previa] + P[fatiga] + P[pareja] + P[doblete]
```

*   **Balance Cero-Sesgo:** Ponderación basada en el historial de asignaciones previas del mes (`CargaBase`).
*   **Penalizaciones Estrictas:** Prevención de repetición de roles, fatiga por semanas consecutivas y parejas duplicadas en acomodadores.
*   **Válvula de Emergencia:** Si un rol crítico queda desierto por restricciones cruzadas, el motor flexibiliza exclusiones permitiendo un "doblete" justificado sin colapsar la matriz.

---

## 🚀 Uso y Desarrollo

### 1. Requisitos e Instalación

El proyecto utiliza las herramientas de empaquetado modernas de Python (`pyproject.toml`).
Se requiere **Python 3.12+**.

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno (Windows)
.\venv\Scripts\activate

# Instalar el proyecto en modo editable (con dependencias de desarrollo)
pip install -e .[dev]
```

### 2. Ejecutar la Aplicación (Desarrollo)

Para probar la aplicación desde el código fuente:

```bash
python src/interfaz_grafica.py
```

### 3. Pruebas Automatizadas y Linter

El repositorio cuenta con cobertura de pruebas unitarias (`pytest`) y validación de estilo (`ruff`).

```bash
# Correr la suite de pruebas
pytest tests/

# Correr el linter
ruff check .

# Formatear el código automáticamente
ruff format .
```

### 4. Compilación y Distribución (Build)

Para crear un ejecutable portátil de Windows (`.exe`) que no requiere que el usuario final tenga Python instalado:

```bash
python build.py
```

El ejecutable finalizado y sus archivos de configuración necesarios (`data/` y `salida/`) se generarán en la carpeta `dist/GeneradorAsignaciones/`. Todo lo que se encuentre en esa carpeta puede ser distribuido como un paquete completo.

---

## 📁 Datos, Configuración y Reglas de Negocio

*   **Primer Arranque Automático (Zero-Config):** La lista real de hermanos (`hermanos.json`) se ignora en Git por privacidad. Sin embargo, al arrancar la app por primera vez, el sistema clonará automáticamente `hermanos.example.json` para que puedas empezar a probar la interfaz de inmediato sin ver errores.
*   **Adaptabilidad Total (White-Label):** El programa ya no asume un número estático de grupos ni nombres de puestos fijos.
    *   **Grupos Dinámicos:** Si tu congregación cambia de tener 4 grupos a tener 5 o 3, puedes modificar la variable `num_grupos_limpieza` en `ReglasAsignacion` (`src/modelos.py`) y toda la aplicación (UI y Excel) se adaptará de inmediato.
    *   **Puestos y Etiquetas:** La estructura del Excel y los nombres de las asignaciones están configurados dinámicamente. Puedes agregar, quitar o renombrar asignaciones modificando la lista `estructura_programa` en la configuración central.
*   **Semanas:** Cada martes del mes abre una semana de programa hasta el domingo.
*   **Ciclos Mensuales:** Regenerar el mismo mes no avanza los grupos de limpieza. El sistema guarda la rotación mes a mes de forma atómica para evitar corrupción de datos.
*   **Alertas Visuales:** Si los recursos no son suficientes para cubrir los puestos de una semana, la interfaz gráfica alertará en texto rojo listando detalladamente los "huecos" o puestos vacíos. Estos igualmente se exportan al Excel en blanco para llenarlos a mano.
