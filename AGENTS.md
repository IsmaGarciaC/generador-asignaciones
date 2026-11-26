# Guía de desarrollo del Generador de Asignaciones

Este repositorio contiene la aplicación de escritorio actual. La V2 se diseña para una persona que prepara el programa mensual en su laptop Windows. El README describe la versión anterior. Consulta los [requisitos y criterios de aceptación](docs/requirements.md) para decisiones de producto y el [roadmap](docs/roadmap.md) para dependencias y decisiones pendientes.

## Arquitectura de la V2

- Mantén un monolito modular en Python. El dominio expresa semanas, plazas, disponibilidad, carga y reglas de validez con tipos independientes de la interfaz, del motor de optimización y de la base de datos. Debe poder probarse en memoria.
- Los casos de uso coordinan generación, edición, publicación y registro de envíos. La interfaz recoge acciones y presenta resultados. El editor y el optimizador deben aplicar el mismo catálogo de reglas y comprobar sus resultados con la misma validación de dominio antes de guardar.
- La propuesta técnica combina NiceGUI en modo escritorio con pywebview, SQLite mediante SQLAlchemy, migraciones de esquema con Alembic, optimización con OR-Tools CP-SAT y exportación con Openpyxl. Mantén consultas, widgets y detalles del solucionador dentro de sus módulos. Distingue las migraciones de esquema del importador histórico de una sola ejecución.
- Valida la selección tecnológica en la fase 2 antes de basar la implementación definitiva en ella. Si la prueba falla, registra el resultado y la decisión pendiente. El alcance excluye Docker, microservicios, React, una API REST independiente, servidores externos, alojamiento, sincronización y autenticación multiusuario.
- Reutiliza el exportador actual donde sea posible. El dominio decide los grupos y la cobertura de cada semana. El exportador representa esas decisiones con el diseño existente.

## Privacidad y conservación

Guarda la base local, los respaldos, las exportaciones reales y cualquier registro con datos personales fuera del repositorio. Usa únicamente datos ficticios en pruebas, capturas, incidencias, ejemplos, artefactos de CI y GitHub. Comprueba el contenido de los paquetes que se distribuyan. El script heredado de compilación copia archivos de `data/`, incluidos los que Git ignora.

Conserva los originales al importar. Antes de transformar datos privados, trabaja desde un respaldo verificable. Usa transacciones para cambios relacionados y comprueba la recuperación ante un fallo. Un cambio de nombre o la desactivación de una persona deben preservar su identidad histórica.

## Método y convenciones

1. Identifica el requisito y el criterio que habrá que demostrar. Si una decisión figura como pendiente, usa los escenarios para validarla antes de codificarla como regla definitiva.
2. Inspecciona el flujo existente y sus pruebas antes de sustituirlo. Limita cada cambio a su fase y conserva la aplicación anterior como referencia para importar y comparar resultados.
3. Escribe Python tipado, con nombres del dominio y módulos pequeños. Añade dependencias o abstracciones solo cuando resuelvan una necesidad concreta. Redacta la documentación del proyecto en español.
4. Prueba las reglas con datos sintéticos y casos límite. Para cambios de persistencia, comprueba las transacciones y los reintentos. Para cambios de presentación del programa, compara las dos hojas y su impresión con la referencia anterior.
5. El proyecto actual contempla `pytest tests/` y `ruff check .`. La V2 prevé automatizar estas comprobaciones con GitHub Actions. Ejecuta las comprobaciones pertinentes al cambio y documenta qué se verificó.

## Referencias de la implementación actual

| Para investigar | Punto de partida |
| --- | --- |
| Puestos, cupos y etiquetas del programa | [Modelos y reglas](src/modelos.py) y [catálogo heredado](data/roles.txt) |
| Orden de asignación, penalizaciones y huecos | [Motor heurístico](src/motor_asignacion.py) y [pruebas del motor](tests/test_motor.py) |
| Formatos JSON, estado de rotación y ausencias | [Repositorio](src/repositorio.py) y [pruebas de persistencia](tests/test_repositorio.py) |
| Edición, apertura de WhatsApp y coordinación de la generación | [Interfaz CustomTkinter](src/interfaz_grafica.py) |
| Semanas civiles, libro de referencia e impresión | [Exportador Excel](src/exportador_excel.py) |
| Ubicación de datos, compilación y versiones declaradas | [Configuración](src/configuracion.py), [compilación](build.py) y [metadatos](pyproject.toml) |
