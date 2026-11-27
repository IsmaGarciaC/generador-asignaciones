# Requisitos de la versión 2.0

El usuario prepara desde su laptop un programa mensual que puede corregir y publicar. Una **plaza** es el lugar de una persona en un puesto durante una semana. La cobertura cuenta plazas individuales, incluso cuando un puesto requiere dos personas. Los criterios siguientes se pueden comprobar con datos ficticios. Las interpretaciones que requieren confirmación figuran al final.

## Requisitos funcionales

### RF-01 · Programa mensual

Una generación resuelve conjuntamente todas las semanas del mes. La asignación es semanal y la misma persona sirve en ambas reuniones cuando el puesto corresponde a ambas. El programa admite cambios puntuales posteriores y distingue borrador y publicado.

**Aceptación.** En un mes con cinco semanas, una sola generación produce las cinco. Al consultar ambas reuniones de una semana se conserva el responsable de cada plaza compartida. Se puede sustituir a una persona sin generar otro programa semanal. Al reabrir el mes se recuperan los cambios y su estado de publicación.

### RF-02 · Puestos y cupos habituales

| Puesto | Plazas semanales | Clave heredada |
| --- | ---: | --- |
| Audio | 1 | `audio` |
| Video | 1 | `video` |
| Acomodadores | 2 | `acomodador` |
| Micrófonos | 2 | `microfonos` |
| Plataforma | 1 | `plataforma` |
| Lector del martes (Estudio Bíblico) | 1 | `lector_martes` |
| Presidente | 1 | `presidente` |
| Lector de La Atalaya | 1 | `lector_domingo` |

**Aceptación.** Una semana sin excepciones requiere diez plazas personales. Con una sola persona asignada a micrófonos queda exactamente una plaza pendiente en ese puesto. Limpieza y hospitalidad se registran por grupo según RF-08.

### RF-03 · Calendario, cancelaciones y cobertura

La semana comienza el martes y termina el domingo. El usuario puede cancelar una reunión, cancelar una semana completa y desactivar un puesto en cualquier semana. Una plaza requerida sin persona queda **pendiente**. Un puesto desactivado o inaplicable queda **no requerido** y se excluye del cálculo de huecos.

La correspondencia de puestos con reuniones en las dos filas de cancelación parcial es una **interpretación pendiente de validación explícita (D-01)**.

| Escenario de aceptación | Resultado esperado |
| --- | --- |
| Solo se cancela el martes | El lector del martes deja de ser requerido. Se mantienen los dos puestos propios del domingo y los cinco puestos compartidos. |
| Solo se cancela el domingo | Presidente y lector de La Atalaya dejan de ser requeridos. Se mantienen lector del martes y los cinco puestos compartidos. |
| Ambas reuniones canceladas, individualmente o como semana completa | Cero asignaciones, alertas de cobertura y recordatorios. La rotación de grupos queda en pausa. |
| Se desactiva video y falta una persona en audio, con reuniones activas | Video figura como no requerido. Solo la vacante de audio aporta un hueco entre esos dos puestos. |

### RF-04 · Validez de las asignaciones

Solo puede ocupar una plaza requerida una persona activa, capacitada para ese puesto y disponible esa semana. Se prefiere una asignación semanal por persona. En caso extremo se admite exclusivamente un doblete del **lector del martes** con **micrófonos**, **plataforma** o **presidente**. Cualquier otra combinación y cualquier tercera asignación semanal están prohibidas.

**Aceptación.** Probar cada pareja permitida en un caso donde hace falta para cubrir una plaza más. Probar las demás combinaciones y un intento de añadir una tercera plaza a una pareja admisible. Tanto al generar como al editar, los resultados deben respetar las prohibiciones, incluidos los intentos de cubrir las dos plazas del mismo puesto con una persona. Un puesto desactivado, una ausencia, la falta de capacitación o un estado inactivo impiden guardar esa asignación.

### RF-05 · Optimización y diagnóstico

El motor propuesto es OR-Tools CP-SAT, sujeto a la prueba de concepto. El orden de decisión es el siguiente. Una mejora de menor prioridad nunca compensa un deterioro de una prioridad superior.

1. Cumplir todas las restricciones obligatorias.
2. Maximizar las plazas requeridas cubiertas en el mes.
3. Minimizar los dobletes excepcionales.
4. Equilibrar la carga histórica.
5. Favorecer descanso y rotación.

**Aceptación.** Con dos planes válidos de igual cobertura, preferir el que usa menos dobletes aun si el otro reparte mejor la carga. Una plaza sin candidatos se informa por semana y puesto y puede formar parte de una solución factible. Distinguir óptimo demostrado, factible sin prueba de optimalidad e inviabilidad demostrada. Si la búsqueda termina sin solución ni prueba de inviabilidad, expresar esa incertidumbre. Un bloqueo incompatible debe identificarse y nunca producir una solución aparentemente válida.

### RF-06 · Equidad, descanso y rotación de personas

Evaluar el mes en planificación y los tres meses anteriores con la información disponible. Considerar el número de asignaciones y la proporción de semanas disponibles en que se trabajó. Una semana con doblete cuenta como una semana trabajada y dos asignaciones. Excluir las ausencias del denominador y conservar como desconocido lo que el historial no acredite. Tener más capacitaciones amplía las opciones y no justifica por sí mismo mayor carga.

Después de dos semanas consecutivas de servicio se procura una de descanso. Se procura evitar la repetición de puestos dentro del mes y de parejas en acomodadores y micrófonos. Son preferencias subordinadas a RF-05.

**Aceptación.** Con cuatro semanas conocidas, dos de ausencia y servicio en una, la proporción es 1/2. Un mes sin datos no aporta semanas de disponibilidad supuesta. Comparar alternativas de igual cobertura y dobletes con cargas distintas, incluida una persona con varias capacitaciones. A igual carga, probar alternativas que permitan descanso tras dos semanas o que eviten repetir un puesto o una pareja. Si repetir es la única forma de cubrir una plaza con validez, se permite.

### RF-07 · Hermanos y disponibilidad

Administrar nombres, teléfonos y capacitaciones desde la interfaz. Referenciar a cada persona por un identificador estable. La desactivación conserva el historial. En una nueva planificación, cada hermano activo está disponible por defecto en todas las semanas salvo aquellas con una ausencia registrada. En el historial importado, la disponibilidad sigue siendo desconocida cuando faltan datos que la acrediten. Las ausencias abarcan exclusivamente semanas completas. Quedan fuera del alcance las ausencias diarias y las restricciones temporales por puesto.

**Aceptación.** Crear una persona, corregir su nombre y teléfono, cambiar una capacitación y reabrir su ficha. Las asignaciones anteriores siguen vinculadas al mismo identificador. Al crear un mes y registrar una única ausencia semanal para esa persona activa, queda disponible en las demás semanas y se impide asignarla durante la ausencia. Comprobar que una semana importada sin datos de disponibilidad sigue figurando como desconocida. Tras desactivarla, sigue siendo consultable en su historial y queda excluida de nuevas asignaciones.

### RF-08 · Limpieza y hospitalidad

El usuario puede seleccionar el grupo inicial y configurar el número de grupos, con cuatro por defecto. Cada semana con al menos una reunión activa consume un turno de limpieza. Hospitalidad corresponde al grupo anterior en el ciclo, incluido el paso del primero al último. Conservar la secuencia histórica a través de cambios de mes y año. Regenerar un programa no consume turnos adicionales.

**Aceptación.** Con cuatro grupos y limpieza inicial en el 4, tres semanas consecutivas (activa, cancelada, activa) producen limpieza 4, sin grupo, 1 y hospitalidad 3, sin grupo, 4. Repetir la generación, incluso al cruzar diciembre y enero, conserva estos resultados y el siguiente turno. Repetir con un número de grupos distinto de cuatro y comprobar el cierre del ciclo.

### RF-09 · Edición y regeneración

Permitir sustituciones, intercambios, plazas vacías y bloqueo de asignaciones. Regenerar un puesto, una semana o el mes completo respetando el alcance elegido y los bloqueos válidos. Si un bloqueo pierde validez, identificar la semana, el puesto y el motivo del conflicto. La edición y el motor comparten las reglas de validación. Una infracción obligatoria impide guardar. Una preferencia incumplida genera una advertencia.

**Aceptación.** Intercambiar dos personas capacitadas en una sola edición y comprobar el resultado completo. Dejar vacía una plaza requerida la vuelve pendiente. Probar los tres alcances con una plaza bloqueada válida y comprobar que se conserva. Registrar luego una ausencia para esa persona y verificar que el conflicto se muestra y que el cambio inválido no se guarda. Una repetición de puesto que solo afecte una preferencia se puede guardar con advertencia.

### RF-10 · Recordatorios semanales

Usar exclusivamente programas publicados para la ronda del martes por la tarde, una vez por semana. Al abrir los recordatorios, detectar y seleccionar automáticamente la semana actual. Permitir que el usuario seleccione otra semana manualmente. Agrupar en un único mensaje por hermano sus responsabilidades habilitadas. Por defecto se incluyen audio, video, acomodadores, micrófonos, plataforma y lector del martes. Se excluyen por defecto presidente y lector de La Atalaya. El usuario puede configurar los puestos y editar las plantillas desde la interfaz.

Abrir el enlace oficial `wa.me` con el mensaje preparado. El usuario envía el mensaje en WhatsApp y confirma manualmente el envío en la aplicación. Registrar la confirmación, prevenir duplicados accidentales y permitir reenvíos explícitos. Se excluyen WhatsApp Business y las automatizaciones no oficiales.

**Aceptación.** Con dos semanas publicadas con responsables distintos, abrir la vista el martes de la primera y comprobar que aparece seleccionada con sus destinatarios. Seleccionar la segunda manualmente y verificar que los destinatarios y mensajes corresponden a esa semana. Un borrador o una semana cancelada no genera recordatorios. Un lector del martes que también lleva micrófonos recibe un único mensaje con ambas responsabilidades. Cambiar los puestos habilitados o el texto de la plantilla se refleja en el mensaje preparado. Si falta el teléfono, se muestra una advertencia. Abrir el enlace sin confirmar deja el envío sin confirmar. Tras confirmar y reabrir la aplicación, la ronda ordinaria no repite ese envío. Un reenvío requiere una acción explícita del usuario.

### RF-11 · Fidelidad de Excel, PDF y PNG

**Es crítico conservar exactamente el formato visual y de impresión del Excel existente.** Mantener por orden las hojas «Programa General» y «Audio y Video», sus estructuras, combinaciones de celdas, fuentes, bordes, alineaciones, colores, dimensiones, márgenes y configuración de impresión propios. Reutilizar el exportador heredado siempre que sea posible. Excel, PDF y PNG deben generarse a partir de la misma versión del programa publicado. PDF y PNG deben reproducir el diseño original. Las semanas canceladas, puestos no requeridos y plazas pendientes deben distinguirse con el mínimo cambio de contenido necesario.

**Aceptación.** Con datos ficticios idénticos, generar referencias V1 para meses de cuatro y cinco semanas y comparar con V2 las propiedades del libro y la representación visual de ambas hojas en el mismo entorno. Verificar la impresión de «Programa General» en una página A4 horizontal y respetar la configuración propia de «Audio y Video». Exportar una misma versión publicada en los tres formatos y comprobar que las semanas, las asignaciones, los grupos y los estados de cobertura coinciden con esa versión en cada archivo. Comparar PDF y PNG con la referencia renderizada, incluidos saltos, textos y bordes, sin recortes. Probar además los tres estados nuevos con la representación que se acuerde en D-06. Incorporar las comparaciones a las pruebas de regresión.

### RF-12 · Importación histórica

Migrar todos los datos recuperables mediante un script de una sola ejecución. Inventariar el padrón, catálogo de roles, ausencias, programas mensuales, estado de grupos y exportaciones disponibles. Preservar los archivos originales, crear un respaldo antes de importar y validar registros y relaciones. Importar en transacciones y reconocer una fuente ya importada al reintentar. Contrastar nombres históricos con identificadores, señalar conflictos y conservar las evidencias pendientes de resolver. Las reglas nuevas rigen la planificación V2. Las asignaciones históricas se conservan tal como constan.

**Aceptación.** Ensayar con un nombre inequívoco, un nombre ambiguo, una referencia inexistente, un doblete histórico hoy prohibido y un período sin información. Recuperar las relaciones comprobables, conservar el doblete y señalar los casos sin evidencia suficiente. Verificar que un fallo durante una transacción revierte sus escrituras y que repetir el proceso deja los mismos registros. El resumen concilia los datos leídos, importados, previamente importados y pendientes o rechazados, con sus motivos. Comprobar que el respaldo es legible y los originales siguen íntegros.

## Requisitos no funcionales

| ID | Requisito | Comprobación de aceptación |
| --- | --- | --- |
| RNF-01 | Uso local por una persona, sin alojamiento, servidores externos, sincronización ni autenticación multiusuario. | Sin Internet, abrir, generar, editar, publicar y exportar un mes en la laptop. Solo la interacción externa con WhatsApp requiere conectividad. |
| RNF-02 | Inicio por doble clic en Windows, sin terminal ni comandos cotidianos y sin recompilar después de cada modificación. | Probar el inicio desde el escritorio y un cambio seguido de reapertura sin ejecutar una compilación. Validar el mecanismo en la prueba de concepto. |
| RNF-03 | Datos privados fuera del repositorio, con copias de seguridad y protección contra pérdida. Ninguna información real de hermanos en GitHub. | Restaurar una copia en otra ubicación local y comprobar personas, programas e historial. Inspeccionar repositorio y artefactos de distribución o CI con un caso sintético. |
| RNF-04 | Monolito modular sencillo, mantenible y tipado. Negocio independiente de interfaz y persistencia. Evitar abstracciones prematuras y dependencias innecesarias. | Ejecutar pruebas de reglas sin abrir la interfaz ni una base real. Revisar dependencias entre módulos, pruebas con Pytest, análisis con Ruff y automatización prevista con GitHub Actions. |
| RNF-05 | Documentación en español y límites arquitectónicos de la V2. | Revisar la documentación y comprobar que la solución respeta las exclusiones y la selección tecnológica provisional de la [guía de desarrollo](../AGENTS.md). |

## Decisiones de producto

| ID | Tema | Acuerdo o comprobación pendiente |
| --- | --- | --- |
| D-01 | Aplicabilidad de los puestos al cancelar una reunión y adscripción de semanas limítrofes. | Se confirmó que la semana pertenece al mes de su martes. El flujo aplica las cancelaciones parciales descritas en RF-03 para su validación en uso. |
| D-02 | Publicación y correcciones posteriores. | Se permite publicar con vacantes tras ver el detalle y confirmar. Una edición posterior se guarda en borrador y la última publicación sigue vigente hasta volver a publicar. |
| D-03 | Cálculo de equidad con información incompleta. | Acordar cómo comparar conteo y proporción, tratar disponibilidad desconocida o denominador cero y desempatar preferencias del mismo nivel. |
| D-04 | Cambios posteriores en la rotación. | Acordar desde qué semana surte efecto un cambio de número de grupos, de grupo inicial o de cancelación cuando ya existen meses posteriores. Preservar el historial confirmado. |
| D-05 | Operación de la ronda semanal. | Precisar hora local del martes por la tarde, actuación si la aplicación está cerrada y tratamiento de cambios de destinatario o puesto tras una confirmación. |
| D-06 | Representación y conversión de exportaciones. | El Excel usa «—» para una vacante, «No requerido» para un puesto inaplicable y «Cancelada» para una semana sin reuniones. Queda verificar la conversión local a PDF y PNG frente a ambas hojas de referencia. |
| D-07 | Recuperación de fuentes heredadas incompletas o discordantes. | Definir cómo resolver manualmente identidades y divergencias entre JSON y Excel, y qué estado de publicación dar a meses importados sin evidencia de publicación. |
| D-08 | Viabilidad técnica, distribución y respaldo. | Validar versiones compatibles, inicio local y capacidad de CP-SAT en Windows. Definir ubicación privada, frecuencia y retención de copias y demostrar la restauración. |
