# Generador de Asignaciones V2

La aplicación prepara el programa mensual desde una ventana nativa de Windows. La base SQLite local se prepara al iniciar.

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

## Preparar un programa mensual

1. Elige el mes y pulsa **Cargar mes**. En **Importar V1**, indica la ruta de una copia privada de la carpeta que contiene `hermanos.json`. Revisa el resultado antes de aplicar. El alcance incluye el padrón, las ausencias del mes y el historial JSON comprobable de los tres meses anteriores. Si V1 indica un grupo inicial para ese periodo, la importación lo muestra para trasladarlo al calendario.
2. En **Padrón**, actualiza las capacitaciones y registra ausencias de semanas completas. En **Programa mensual**, ajusta reuniones, puestos desactivados y grupos si corresponde.
3. Pulsa **Generar mes** y revisa **Carga y descanso** para ver las asignaciones y la mayor racha por persona. Si al regenerar sale el mismo programa, la aplicación busca otro reparto de igual calidad. El resumen refleja las ediciones del borrador. Para intercambiar personas, ajusta las dos plazas antes de pulsar **Guardar borrador**.
4. Pulsa **Publicar**. Si hay vacantes, revisa la lista antes de confirmar. **Exportar Excel** guarda las hojas «Programa General» y «Audio y Video» de la última versión publicada en `exportaciones`, junto a la base local. Las correcciones posteriores aparecen en el Excel al publicar una nueva versión.

Para conservar una asignación al regenerar, pulsa su candado. **Guardar borrador** conserva los bloqueos. En **Alcance** puedes elegir todo el mes, una semana o un puesto durante todo el mes. Las asignaciones bloqueadas y las plazas fuera del alcance, incluidas las vacantes, se conservan. Si una ausencia u otro cambio invalida un bloqueo, la ventana indica la fecha, el puesto y el motivo.

## Exportar PDF y PNG

Instala [LibreOffice con Calc](https://www.libreoffice.org/download/download-libreoffice/) en Windows para habilitar la conversión local. Si ya tenías instalada la V2, actualiza sus dependencias desde la raíz con `.\v2\venv\Scripts\python.exe -m pip install -e .\v2`. Luego vuelve a abrir la aplicación.

En un mes publicado, pulsa **Exportar PDF y PNG** y después **Abrir carpeta**. La carpeta contiene el Excel, un PDF y dos PNG, todos de la misma versión publicada. La primera página es «Programa General», en A4 horizontal. La segunda es «Audio y Video», en A4 vertical con el ancho ajustado para que se vean todas las semanas. La conversión funciona sin conexión.

## Recordatorios de WhatsApp

En **Padrón**, registra los teléfonos con el código de país. Después de publicar el mes, abre **WhatsApp**. La vista selecciona la semana que comenzó el martes más reciente. Puedes elegir otra semana del programa publicado.

Usa **Abrir WhatsApp** para revisar y enviar el mensaje preparado en el navegador. Vuelve a la aplicación y pulsa **Confirmar envío**. La confirmación se conserva aunque cierres la aplicación o vuelvas a publicar el mes. Usa **Reenviar por WhatsApp** si corresponde avisar nuevamente a una persona ya confirmada.

En **Configurar recordatorios**, selecciona los puestos y edita el mensaje con `{nombre}`, `{semana}` y `{puestos}`. La app prepara un mensaje por persona con todos sus puestos incluidos.

## Base local y respaldo

La base se guarda en `%LOCALAPPDATA%\GeneradorAsignacionesV2\programa.sqlite3`. Alembic crea el esquema en el primer arranque. Cuando una base existente necesita una migración, la aplicación conserva un respaldo verificado de la revisión anterior antes de actualizarla.

En una base al día se crea un respaldo al primer arranque de cada día. El botón **Crear respaldo** guarda además una copia cuando la necesitas. Las copias verificadas quedan en `respaldos`, dentro del mismo directorio privado. Se conservan hasta que la persona responsable decida archivarlas o retirarlas.

Para recuperar una copia, ejecuta el siguiente comando con su ruta. La salida indica el archivo restaurado en una nueva carpeta privada bajo `recuperaciones`. Comprueba esa copia antes de usarla y conserva la base original.

```powershell
.\v2\venv\Scripts\python.exe -m generador_asignaciones_v2 recuperar "C:\ruta\al\respaldo.sqlite3"
```

La aplicación comprueba la integridad de SQLite y sus claves foráneas antes de publicar la copia. El comando `respaldar` sin argumentos también crea una copia manual desde PowerShell. Una migración se detiene si falla su respaldo previo. Ante un error de arranque, la ventana informa el motivo y el mismo comando de inicio puede ejecutarse desde la consola para consultarlo.

## Comprobaciones de desarrollo

```powershell
.\v2\venv\Scripts\python.exe -m pip install . -e './v2[dev]'
.\v2\venv\Scripts\python.exe -m pytest tests/ v2/tests/
.\v2\venv\Scripts\python.exe -m ruff check .
```

GitHub Actions ejecuta las dos suites y Ruff en Windows para los cambios hacia `v2`. Las pruebas del dominio V2 usan el catálogo y combinaciones en memoria. Consulta el [roadmap](../docs/roadmap.md) para el estado de las fases.

Las pruebas visuales de exportación se ejecutan cuando LibreOffice está instalado. Para usar una instalación por fuera de la ruta habitual, indica la ruta completa a `soffice.com` en la variable `ASIGNACIONES_LIBREOFFICE`.
