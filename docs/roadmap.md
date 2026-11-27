# Roadmap hacia la versión 2.0.0

Las entregas se organizan por lo que la persona puede hacer en la aplicación. Los identificadores RF, RNF y D remiten a los [requisitos y criterios de aceptación](requirements.md). La [guía de desarrollo](../AGENTS.md) recoge los límites arquitectónicos.

## Estado actual

- Fase 1 completada con la guía, los requisitos y la referencia V1.
- Fase 2 completada. Se adoptaron Python 3.12 x64 en Windows, NiceGUI con pywebview y OR-Tools CP-SAT. El usuario confirmó el arranque desconectado, el rechazo de acceso desde otro equipo y la apertura externa de WhatsApp. [Resultados de escritorio](../spikes/nicegui_desktop/RESULTADOS.md) · [Resultados del solver](../spikes/assignment_solver/RESULTADOS.md)
- Fase 3 completada con paquete V2 independiente, catálogo semanal y regla de dobletes. Se comprobó el arranque desde el acceso directo con escucha en `127.0.0.1`. Pytest y Ruff se ejecutan en Windows mediante GitHub Actions. [Guía de la V2](../v2/README.md)
- Ya se implementaron SQLite, SQLAlchemy, migraciones y respaldos. Los ensayos con datos ficticios conservan identidades y referencias, revierten escrituras interrumpidas y recuperan el programa en otra ubicación privada. [Respaldo y recuperación](../v2/README.md#base-local-y-respaldo)
- El flujo mensual reúne importación verificable, padrón, calendario, CP-SAT, edición, publicación y Excel. Tras la cobertura y los dobletes, se prioriza evitar repetir puesto. La carga mensual y la equidad histórica desempatan en ese orden (D-03). [Flujo mensual](../v2/README.md#preparar-un-programa-mensual)
- El editor guarda bloqueos de plazas y regenera un puesto, una semana o todo el mes. Las plazas fuera del alcance se conservan y se informa el motivo de los bloqueos inválidos (RF-09).
- El programa tiene dos meses de historial. La importación desde respaldo cubre el alcance acordado y se retira la fase de recuperación histórica adicional (RF-12 y D-07).

## Punto de partida

| Evidencia de la versión anterior | Consecuencia para la V2 |
| --- | --- |
| El [motor](../src/motor_asignacion.py) recorre las semanas en orden y reinicia sus contadores al crear la instancia. Las [reglas por defecto](../src/modelos.py) admiten como auxilio del lector a micrófonos, audio y video. Micrófonos se procesa después del lector, mientras que la [prueba del doblete](../tests/test_motor.py) lo sitúa antes. | La prueba heredada cubre un orden particular. Verificar la lista exacta de RF-04 independientemente del orden de los puestos, el horizonte histórico y la prioridad de cobertura de todo el mes. |
| El [padrón](../src/modelos.py) tiene ID, pero el [repositorio](../src/repositorio.py) guarda programas y ausencias por nombre. Algunos lectores de archivos devuelven una estructura vacía o `None` ante errores. `estado.json` solo conserva el último mes y los grupos último y siguiente. | Recuperar las relaciones comprobables del respaldo JSON en el período de RF-12. Registrar los casos incompletos o ambiguos en el resumen de importación. |
| El [editor y la vista de recordatorios](../src/interfaz_grafica.py) guardan directamente las selecciones y abren un enlace por puesto y nombre. No existe estado de publicación ni registro de confirmaciones. | Comprobar la validez del cambio completo antes de persistirlo y vincular cada ronda de recordatorios al programa publicado. |
| El [exportador](../src/exportador_excel.py) calcula los grupos por índice de semana, presenta los huecos con «—» y configura A4 horizontal a una página solo en «Programa General». El [README](../README.md) describe los huecos como celdas en blanco. | Tomar el libro producido como referencia. Conservar la configuración individual de cada hoja y alimentar el contenido con las excepciones y la rotación del dominio. El repositorio carece de pruebas de regresión de exportación. |
| El [README](../README.md) pide Python 3.12+, mientras que los [metadatos](../pyproject.toml) declaran 3.10+ y Ruff apunta a 3.10. La [compilación](../build.py) copia los archivos de `data/` al paquete. | Resolver la versión compatible en Windows y probar la distribución con datos privados externos. Un archivo ignorado por Git aún puede terminar en el paquete heredado. |

## Entregas y criterios de finalización

La V2 emite Excel, PDF y PNG de la misma publicación. Las pruebas de RF-11 comparan ambas hojas contra V1 con meses de cuatro y cinco semanas. La pestaña WhatsApp permite preparar la ronda semanal y registrar sus confirmaciones (RF-10). Queda la comprobación del flujo de WhatsApp en la laptop y la preparación de la distribución de Windows.

| Entrega | Resultado verificable |
| --- | --- |
| Preparar y emitir el mes en Excel | Cargar el padrón y el historial reciente verificable desde un respaldo, configurar reuniones y ausencias, generar meses de cuatro y cinco semanas, editar, publicar, reabrir y exportar. Verificar el cruce de año, la reversión de cambios inválidos, las vacantes, la estabilidad de los grupos y la equivalencia de ambas hojas con V1. |
| Completar salidas y recordatorios | Emitir PDF y PNG desde la misma publicación y verificar la impresión de ambas hojas según RF-11. Abrir la ronda semanal publicada, confirmar envíos y preservar su registro según RF-10. |
| Distribuir V2.0.0 | Ensayar en la laptop el flujo completo sin Internet, restaurar un respaldo y revisar el paquete de Windows para excluir datos reales. Resolver D-04 con cambios de rotación que preserven programas confirmados y cerrar los criterios RF y RNF que faltan. |
