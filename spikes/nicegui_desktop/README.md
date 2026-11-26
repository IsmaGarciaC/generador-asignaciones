# Prueba de escritorio con NiceGUI

El prototipo abre una ventana nativa de Windows con cinco semanas, diez plazas y doce personas ficticias. Cambiar un selector actualiza esa plaza en memoria. Al cerrar la aplicación se descartan las ediciones.

## Preparar una vez

Se necesita Windows x64, CPython 3.12 de 64 bits y Microsoft Edge WebView2 Runtime. La instalación inicial de paquetes requiere Internet. La configuración ensayada y los resultados están en el [informe](RESULTADOS.md).

Desde la raíz del repositorio, ejecutar en PowerShell:

```powershell
Set-Location spikes\nicegui_desktop
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m pip check
.\crear_acceso.cmd
```

Si Windows no reconoce `py`, sustituir solo la segunda línea por una llamada al intérprete instalado. Esta fue la ubicación en la laptop ensayada:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv venv
```

## Uso cotidiano

Hacer doble clic en **Asignaciones.lnk**, dentro de esta carpeta. El acceso ejecuta el `pythonw.exe` del entorno propio y abre `app.py` sin consola. Se puede copiar el acceso al escritorio. Si cambia la ubicación del proyecto, volver a crear el entorno y el acceso en la nueva ruta.

Editar una plaza y comprobar el resumen con la semana, la plaza y la persona seleccionada. En una ventana estrecha se puede desplazar la tabla horizontalmente. El botón **Probar enlace de WhatsApp** delega `https://wa.me/` al navegador predeterminado, sin número ni texto preparado.

Cerrar con la **X** antes de reiniciar. El siguiente inicio lee el archivo Python actualizado. Para diagnosticar un fallo de arranque, ejecutar desde esta carpeta:

```powershell
.\venv\Scripts\python.exe .\app.py
```

## Checklist manual en Windows

- [ ] **Ventana e inicio.** Abrir el acceso con doble clic. Verificar que aparece la ventana del programa sin terminal visible ni pestaña de navegador para alojar la matriz.
- [ ] **Edición.** En una sesión nueva, cambiar Video de la semana 3 de «Persona 04» a «Persona 12». Comprobar la celda y el resumen «Semana 3 · Video · Persona 12». Comparar las demás celdas con la matriz inicial.
- [ ] **Tamaño.** Reducir la ventana aproximadamente a 740 × 550, desplazarse a «Lector de La Atalaya» en la semana 5 y editarlo. Comprobar el encabezado de fila, la semana y el resultado.
- [ ] **Sin Internet.** Con las dependencias instaladas, desconectar la laptop de Internet antes de iniciar. Abrir, editar dos celdas, cerrar y reabrir. Debe aparecer de nuevo la matriz ficticia inicial.
- [ ] **Enlace externo.** Con conexión, pulsar el botón. Verificar visualmente que el navegador predeterminado abre el enlace o su redirección oficial y que la ventana nativa sigue mostrando la matriz. Basta con observar la navegación.
- [ ] **Escucha y acceso desde la red.** Ejecutar las comprobaciones de la sección siguiente mientras se ve la matriz.
- [ ] **Cierre.** Cerrar con la X y comprobar la liberación del puerto y de los procesos anotados. Reabrir y repetir el cierre.
- [ ] **Cambio sin compilación.** Con la aplicación cerrada, cambiar temporalmente `TITULO` en `app.py`. Abrir el mismo acceso, verificar el nuevo título, cerrar y restaurar el texto.

### Comprobar la escucha y el cierre

Con una instancia abierta, ejecutar en PowerShell desde la carpeta del prototipo. NiceGUI selecciona un puerto libre al arrancar. Identificarlo por el proceso evita confundirlo con otro servicio.

```powershell
$rutaApp = (Resolve-Path .\app.py).Path
$procesosApp = Get-CimInstance Win32_Process |
    Where-Object { $_.Name -in 'python.exe','pythonw.exe' -and $_.CommandLine -like "*$rutaApp*" }
$escucha = Get-NetTCPConnection -State Listen |
    Where-Object { $_.OwningProcess -in $procesosApp.ProcessId }
$escucha | Format-Table LocalAddress,LocalPort,OwningProcess
Test-NetConnection 127.0.0.1 -Port $escucha.LocalPort -InformationLevel Quiet
```

Debe aparecer una única fila con dirección **127.0.0.1** y la prueba local debe devolver `True`. Una escucha en `0.0.0.0`, `::` o la IP de la red local incumple el criterio. Anotar el PID del servidor y el puerto. En el Administrador de tareas, identificar también los procesos Python y WebView2 de esta instancia por su relación padre-hijo.

Desde **otro dispositivo de la misma red**, usar la IPv4 Wi-Fi o Ethernet de la laptop que muestra `ipconfig` y el puerto recién anotado. En otro Windows, ejecutar `Test-NetConnection <IPv4-de-la-laptop> -Port <puerto> -InformationLevel Quiet`. El resultado esperado es `False` mientras la comprobación local sigue dando `True`. La prueba remota complementa la inspección de la dirección de escucha, ya que el cortafuegos también puede rechazar conexiones.

Después de cerrar la ventana, esta consulta en la misma sesión de PowerShell debe quedar vacía. Comprobar también que los PID de la instancia desaparecen antes de reabrir.

```powershell
Get-NetTCPConnection -State Listen -LocalPort $escucha.LocalPort -ErrorAction SilentlyContinue |
    Where-Object OwningProcess -eq $escucha.OwningProcess
```
