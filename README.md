# Generador de Asignaciones Mensuales

Sistema automatizado en Python para la planificación, balance de carga y rotación equitativa de asignaciones de la congregación, con interfaz gráfica moderna y exportación a Excel / ONLYOFFICE.

## Características

- **Rotación Equitativa:** Penalización inteligente para evitar repetición de roles, evitar fatiga por semanas consecutivas y alternar compañeros en puestos dobles (Micrófonos y Acomodadores).
- **Válvula de Emergencia:** Regla especial para Lector del Estudio de Libro (Martes) si falta personal disponible.
- **Gestión de Ausencias:** Interfaz visual para marcar hermanos no disponibles por semana específica.
- **Memoria de Limpieza:** Rotación continua persistente de los 4 grupos de limpieza y hospitalidad a lo largo del año.
- **Matriz Única para Tablero:** Hoja de cálculo optimizada para impresión A4 horizontal (alineada arriba a la izquierda para recorte rápido de guillotina) y hoja separada para Audio y Video.

## Requisitos e Instalación

1. Clonar el repositorio.
2. Crear y activar el entorno virtual:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
