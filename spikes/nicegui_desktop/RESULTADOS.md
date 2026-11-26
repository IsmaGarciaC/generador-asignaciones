# Resultados de la prueba de escritorio en Windows

**Recomendación provisional.** Continuar la evaluación de NiceGUI con pywebview. La ventana real mostró 50 celdas editables y las dos ediciones ensayadas actualizaron las coordenadas correctas. El acceso directo arrancó desde el código y el servidor escuchó en bucle local. Antes de adoptar el stack falta observar la pestaña externa, arrancar la laptop desconectada y probar el acceso desde un segundo equipo. El solver tiene su propia prueba pendiente en la [fase 2](../../docs/roadmap.md).

## Entorno y compatibilidad

| Componente | Versión comprobada | Evidencia |
| --- | --- | --- |
| Windows 11 x64 | Compilación 26200 | Identificación del sistema desde el intérprete utilizado. |
| CPython x64 | 3.12.10 | Intérprete base presente en la laptop. El prototipo tiene un entorno virtual propio. |
| NiceGUI / pywebview | 4.1.0 / 6.2.1 | Versiones instaladas y utilizadas para abrir la ventana y editar la matriz. |
| WebView2 Runtime / pythonnet | 158.0.4370.45 / 3.2.1 | Runtime registrado en Windows y puente .NET instalado. Se utilizó el backend `edgechromium`. |
| Uvicorn / pip | 0.54.0 / 25.0.1 | Servidor local y gestor de paquetes del entorno ensayado. `pip check` terminó sin conflictos. |

Se eligió Python 3.12 x64 por estar disponible en la laptop y disponer de una distribución oficial de OR-Tools para Windows y esa ABI. La simulación de resolución con `pip install --dry-run` sobre el entorno anterior encontró una combinación con OR-Tools 9.15.6755, SQLAlchemy 2.1.9, Alembic 1.20.1, Openpyxl 3.1.5, Pytest 9.2.0 y Ruff 0.17.6. Son resultados del resolvedor. La instalación y las pruebas de ejecución se limitaron al stack de escritorio. Las versiones directas y transitivas utilizadas se conservan en [requirements.txt](requirements.txt). [Distribuciones oficiales de OR-Tools](https://pypi.org/project/ortools/9.15.6755/#files) · [Requisitos de pywebview en Windows](https://pywebview.flowrl.com/guide/installation)

## Elección de la matriz

Para cinco semanas y diez plazas basta una tabla con encabezados de fila y columna y un `ui.select` por celda. Cada selector lleva su plaza y semana al manejador de cambios. Este escribe en el diccionario en memoria y muestra la coordenada y el valor seleccionados. La tabla se desplaza horizontalmente al reducir la ventana. Se evaluó AG Grid mediante su documentación. Sus definiciones de columnas, editores y eventos aportarían complejidad para estas 50 celdas. No se hizo una comparativa de rendimiento. [Selectores de NiceGUI](https://nicegui.io/documentation/select) · [AG Grid en NiceGUI](https://nicegui.io/documentation/aggrid)

El arranque fija `native=True`, `host='127.0.0.1'` y `reload=False`. WebView2 presenta la página en la ventana nativa. Solo el botón solicita al navegador predeterminado que abra una URL externa. [Modo nativo de NiceGUI](https://nicegui.io/documentation/section_configuration_deployment#native_mode)

## Comprobaciones ejecutadas

| Comprobación | Método | Resultado observado |
| --- | --- | --- |
| Inicio y reinicio desde código | Abrir el acceso `.lnk` mediante Windows, cambiar el título en el código, cerrar y volver a abrir el mismo acceso | Apareció primero «Asignaciones mensuales» y después «Programa mensual de asignaciones». El destino fue `venv\Scripts\pythonw.exe`. No hubo paso de compilación. |
| Matriz y edición | Leer los 50 selectores mediante accesibilidad de Windows, editar Video en la semana 3 y comparar todos los valores | «Persona 04» cambió a «Persona 12». El resumen identificó Video y la semana 3. Las otras 49 celdas coincidieron con la lectura inicial. |
| Ventana estrecha y datos en memoria | En WebView2 a 740 × 550, desplazar la tabla hasta la última columna y elegir «Persona 11» en la última fila | Cambió únicamente la clave «Lector de La Atalaya», semana 5. Se compararon las 50 entradas en memoria y las 50 celdas renderizadas. La última celda y el resumen reflejaron la edición. |
| Recursos locales | Repetir el arranque y la edición con WebView2 configurado para usar un proxy inaccesible salvo en bucle local. Inspeccionar los recursos HTTP(S) del documento | La matriz se cargó y aceptó el cambio. Todos los recursos HTTP(S) observados procedían de `127.0.0.1`. La laptop mantuvo su conectividad durante este ensayo. |
| Escucha | Consultar con `Get-NetTCPConnection` las escuchas de los procesos de la instancia | Una sola escucha en `127.0.0.1:8000` durante el ensayo. El acceso HTTP local devolvió 200. El puerto puede variar en otros arranques. |
| Cierre | Identificar los procesos Python y WebView2 de la instancia, cerrar la ventana nativa y consultar los PID y las escuchas | En el ensayo instrumentado se observaron nueve procesos, cero supervivientes y cero escuchas tras cerrar. |
| Botón externo | Pulsar el botón dentro de WebView2 y observar la llamada real a `webbrowser.open` | Windows aceptó `https://wa.me/` con resultado `True`. La ventana nativa siguió en la URL local con sus 50 selectores. La automatización no identificó la pestaña del navegador externo. |
| Aislamiento | Comprobar el prefijo del intérprete, las dependencias y el estado de Git | El entorno reside en esta carpeta. Los archivos versionados de la aplicación heredada no presentan cambios. |

## Incidencias y validación pendiente

- La consola de la prueba no resolvía `py` ni `python` por nombre. Se utilizó la ruta del intérprete base de 3.12.10. La política de PowerShell también bloqueó un archivo `.ps1` de preparación. El generador de acceso entregado usa `.cmd` y se verificaron su destino, argumento y directorio de trabajo.
- Un primer intento de editar la esquina inferior mediante accesibilidad no recuperó el resumen esperado. Se repitió sobre el DOM de WebView2 y se contrastó el resultado con el diccionario Python. Una solicitud de cierre mediante `CloseMainWindow` tampoco liberó la instancia en el tiempo observado. El cierre por el control nativo y el ensayo instrumentado posterior sí liberaron el servidor.
- La confirmación visual de la pestaña de WhatsApp, la apertura con desconexión física y la conexión desde otro dispositivo siguen pendientes. El doble clic físico y el cierre con la X se pueden reproducir en la misma revisión de usuario. El [checklist de Windows](README.md#checklist-manual-en-windows) detalla cómo comprobarlos.
