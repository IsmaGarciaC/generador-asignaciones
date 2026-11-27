# Resultados de CP-SAT en Windows

**Recomendación.** Adoptar CP-SAT como base del motor de la V2. En los cuatro escenarios se demostraron la máxima cobertura, el mínimo de dobletes para esa cobertura y el óptimo de la fórmula de equidad experimental. Los planes finales fueron factibles. La última etapa consumió su presupuesto con una brecha de optimalidad.

## Entorno y comprobaciones

Windows 11 x64 (compilación 26200), AMD Ryzen 7 5800H, CPython 3.12.10 x64, OR-Tools 9.15.6755 y Pytest 9.2.0. El intérprete base coincide con el de la prueba de escritorio. Las dependencias se instalaron en el entorno propio y `pip check` pasó. Pip resolvió además los requisitos exactos de NiceGUI 4.1.0 y pywebview 6.2.1 con los del solver mediante `--dry-run`. La compatibilidad conjunta observada corresponde a la resolución de dependencias. [Versiones instaladas](requirements.txt)

**56 pruebas del spike aprobadas** en 1,23 s. Incluyen los 28 pares de puestos distintos, la validación independiente de planes, una búsqueda exhaustiva de las prioridades para un caso pequeño y pruebas que ejercitan los cinco estados reales de CP-SAT. Las regresiones cubren meses sin historial que interrumpen una racha y errores de modelo tras una etapa exitosa. También pasaron las 15 pruebas heredadas y `ruff check .`.

## Modelo y estrategia

Cada variable binaria indica si una persona elegible ocupa una plaza en una semana. Se crean variables únicamente para plazas requeridas y personas activas, capacitadas y disponibles. Cada plaza admite como máximo una persona. Cada persona puede tomar como máximo una plaza entre todos los puestos distintos del lector del martes. Puede añadir el lector del martes únicamente si ese otro puesto es micrófonos, plataforma o presidente. Las plazas vacías son válidas. Cada bloqueo fija su variable a uno. Un bloqueo incompatible vuelve inviable el modelo y el verificador indica su coordenada y motivo.

El solver maximiza cobertura y después minimiza dobletes, equidad y rotación, en ese orden. Tras cada `OPTIMAL` fija ese valor como restricción y usa el plan como pista para la etapa siguiente. Ante `FEASIBLE` devuelve el plan y detiene la secuencia. Ante `UNKNOWN` conserva el plan previo, si existe, con estado global factible. `INFEASIBLE` identifica inviabilidad demostrada y `MODEL_INVALID` señala un error de modelo. Ambos estados dejan la salida sin plan. Cada plan se comprueba por separado y sus métricas se recalculan desde las asignaciones. [Estados oficiales de CP-SAT](https://developers.google.com/optimization/cp/cp_solver#cp-sat_return_values)

## Métricas provisionales

Para cada persona activa, **D** cuenta oportunidades conocidas en los tres meses anteriores y el mes planificado. Se excluyen ausencias, cancelaciones y semanas históricas desconocidas. **A** cuenta asignaciones y **S** semanas trabajadas. Un doblete suma dos a A y uno a S. La etapa de equidad minimiza la suma de `redondear(100×A²/D) + redondear(100×S²/D)` por persona. Las personas con cero oportunidades aportan cero. La fórmula favorece repartir carga con respecto a oportunidades conocidas. Una ausencia jamás cuenta como oportunidad perdida. Una persona con menos oportunidades puede tener una tasa mayor para el mismo número de servicios. Las capacitaciones habilitan opciones y quedan fuera de la fórmula. El redondeo y la influencia de historiales cortos limitan la métrica. **D-03 sigue abierta.**

La última etapa suma ventanas de tres semanas seguidas de servicio, repeticiones de puesto y repeticiones de parejas por puesto. El descanso considera las dos semanas inmediatamente anteriores al mes. Un tramo sin datos interrumpe la racha comprobable. Las parejas de micrófonos y acomodadores se identifican por sus dos IDs ordenados, con independencia de la plaza que ocupó cada integrante. Las repeticiones se cuentan a partir de la segunda aparición en el mes.

## Rendimiento

Una ejecución de `medir.py --segundos 5`, con un trabajador, semilla del solver 73, datos reproducibles por escenario y hasta cinco segundos de búsqueda por etapa. El total incluye la construcción del modelo y la validación. Los tiempos reflejan esta ejecución.

| Personas × semanas | Requeridas | Cubiertas | Vacantes | Dobletes | Equidad (carga + frecuencia) | Descanso / puesto / micrófonos / acomodadores | Total (s) |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: |
| 15 × 4 | 40 | 40 | 0 | 0 | 11 727 + 8 299 = 20 026 | 17 / 20 / 0 / 2 | 5,485 |
| 25 × 5 | 50 | 50 | 0 | 0 | 15 485 + 9 873 = 25 358 | 6 / 22 / 1 / 0 | 5,297 |
| 40 × 5 | 50 | 50 | 0 | 0 | 24 228 + 15 583 = 39 811 | 4 / 21 / 1 / 1 | 5,527 |
| 15 × 5, difícil | 39 | 38 | 1 | 1 | 8 672 + 6 555 = 15 227 | 3 / 20 / 0 / 2 | 5,186 |

| Escenario | Cobertura óptima (s) | Dobletes óptimos (s) | Equidad óptima (s) | Rotación factible (s) | Penalización / cota inferior de rotación |
| --- | ---: | ---: | ---: | ---: | --- |
| 15 × 4 | 0,023 | 0,040 | 0,404 | 5,006 | 39 / 13 |
| 25 × 5 | 0,022 | 0,044 | 0,191 | 5,009 | 29 / 10 |
| 40 × 5 | 0,036 | 0,051 | 0,393 | 5,020 | 27 / 0 |
| Difícil | 0,011 | 0,048 | 0,113 | 5,005 | 25 / 17 |

En el escenario difícil, Video de la semana 2 quedó vacante por ausencia de la única persona capacitada. Se conservaron los dos bloqueos y la semana 3 cancelada aportó cero plazas. El puesto de presidente de la última semana estaba desactivado.

## Comparación con V1 y límites

Con los mismos padrones y ausencias de los tres escenarios ordinarios, V1 cubrió 39/40, 50/50 y 50/50, con cero dobletes en los tres. V1 asigna en orden y tiene otras reglas de dobletes e historial, por lo que la cobertura es descriptiva. El caso mínimo sí tiene restricciones efectivas equivalentes. Con semilla 0, V1 asignó Audio a la única persona capacitada también para Video y cubrió 1/2. CP-SAT reservó esa persona para Video y cubrió 2/2. El escenario difícil exige excepciones propias de V2.

Las resoluciones sucesivas gastan tiempo adicional y una etapa sin optimalidad demostrada deja las posteriores pendientes. La cantidad de candidatos por rol incrementa las combinaciones de parejas y la rotación fue la etapa más costosa. Para el motor definitivo conviene validar la equidad con casos acordados, medir el presupuesto de respuesta y mostrar el último objetivo certificado. Las cuatro mediciones corresponden a datos sintéticos y pueden variar con el entorno y los límites de búsqueda.
