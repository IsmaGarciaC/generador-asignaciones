# Guía de desarrollo del Generador de Asignaciones

La V2 es una aplicación de escritorio para una persona que prepara el programa mensual en su laptop Windows. Esta guía, los [requisitos y criterios de aceptación](docs/requirements.md) y el [roadmap](docs/roadmap.md) rigen el desarrollo. La V1 y su README sirven de referencia para importar datos y comparar resultados.

## Arquitectura de la V2

- Mantén un monolito modular en Python. El dominio expresa semanas, plazas, disponibilidad, carga y reglas de validez con tipos independientes de la interfaz, del motor de optimización y de la base de datos. Debe poder probarse en memoria.
- Los casos de uso coordinan generación, edición, publicación y registro de envíos. La interfaz recoge acciones y presenta resultados. El editor y el optimizador deben aplicar el mismo catálogo de reglas y comprobar sus resultados con la misma validación de dominio antes de guardar.
- Usa Python 3.12 x64 en Windows con NiceGUI y pywebview para el escritorio y OR-Tools CP-SAT para la optimización, conforme a la fase 2. La persistencia prevista usa SQLite con SQLAlchemy y Alembic. La exportación usa Openpyxl. Mantén consultas, widgets y detalles del solucionador dentro de sus módulos. Distingue las migraciones de esquema del importador histórico de una sola ejecución.
- El alcance excluye Docker, microservicios, React, una API REST independiente, servidores externos, alojamiento, sincronización y autenticación multiusuario.
- Conserva exactamente el formato visual y de impresión de las dos hojas de Excel según RF-11. Reutiliza el exportador actual donde sea posible. El dominio decide los grupos y la cobertura de cada semana.

## Privacidad y conservación

Guarda la base local, los respaldos, las exportaciones reales y cualquier registro con datos personales fuera del repositorio. Usa únicamente datos ficticios en pruebas, capturas, incidencias, ejemplos, artefactos de CI y GitHub. Comprueba el contenido de los paquetes que se distribuyan. El script heredado de compilación copia archivos de `data/`, incluidos los que Git ignora.

Conserva los originales al importar. Antes de transformar datos privados, trabaja desde un respaldo verificable. Usa transacciones para cambios relacionados y comprueba la recuperación ante un fallo. Un cambio de nombre o la desactivación de una persona deben preservar su identidad histórica.

## Desarrollo y autonomía

1. Inspecciona el estado del repositorio y elige la siguiente tarea del roadmap según sus dependencias. Identifica el requisito y el criterio que se debe demostrar. Revisa el flujo existente y sus pruebas antes de cambiarlo. Agrupa tareas relacionadas en entregas funcionales que respeten el orden de las fases.
2. Como responsable técnico, planifica, diseña, implementa, prueba y revisa cada entrega con autonomía. Resuelve las decisiones técnicas ordinarias y corrige los problemas detectados. Prioriza funcionalidad y mantenibilidad con Python tipado, nombres del dominio y módulos pequeños. Añade dependencias y abstracciones cuando resuelvan una necesidad concreta.
3. Consulta al usuario únicamente por decisiones funcionales que afecten al uso, ambigüedades relevantes de negocio, cambios a requisitos aprobados, riesgo significativo de pérdida de datos, decisiones arquitectónicas importantes, costosas o difíciles de revertir, o validaciones manuales fuera de tu alcance. Presenta una recomendación y su justificación breve. Usa los escenarios para evaluar decisiones pendientes antes de fijar reglas definitivas.
4. Añade pruebas relevantes con datos ficticios y casos límite. Comprueba transacciones, recuperación y reintentos en los cambios de persistencia. Ante cambios de presentación del programa, compara las dos hojas y su impresión con V1. Ejecuta `pytest tests/ v2/tests/`, `ruff check .` y las comprobaciones específicas del cambio según corresponda. GitHub Actions ejecuta las suites y Ruff en Windows. Registra los resultados observados y las verificaciones pendientes.
5. Mantén el roadmap al día con el progreso real, las decisiones relevantes y los bloqueos. Escribe en español. Aprovecha la evidencia disponible, limita las lecturas al alcance de la tarea y da por concluido un prototipo cuando cumpla su criterio de viabilidad.

## Git y entregas

- Trabaja en ramas de funcionalidad con PR hacia `v2`. Puedes crear ramas, commits, hacer push y abrir PR de forma autónoma. Reserva `main` para la versión heredada durante el desarrollo de la V2. La fusión de PR y la eliminación de información requieren autorización del usuario.
- Al entregar, resume qué se implementó, qué pruebas se ejecutaron y sus resultados, las decisiones relevantes y la validación manual pendiente, si corresponde. Incluye el enlace a la PR y la siguiente tarea del roadmap.

## Referencias de la implementación actual

| Para investigar | Punto de partida |
| --- | --- |
| Puestos, cupos y etiquetas del programa | [Modelos y reglas](src/modelos.py) y [catálogo heredado](data/roles.txt) |
| Orden de asignación, penalizaciones y huecos | [Motor heurístico](src/motor_asignacion.py) y [pruebas del motor](tests/test_motor.py) |
| Formatos JSON, estado de rotación y ausencias | [Repositorio](src/repositorio.py) y [pruebas de persistencia](tests/test_repositorio.py) |
| Edición, apertura de WhatsApp y coordinación de la generación | [Interfaz CustomTkinter](src/interfaz_grafica.py) |
| Semanas civiles, libro de referencia e impresión | [Exportador Excel](src/exportador_excel.py) |
| Ubicación de datos, compilación y versiones declaradas | [Configuración](src/configuracion.py), [compilación](build.py) y [metadatos](pyproject.toml) |
