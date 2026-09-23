# ⚡ Congregation Assignment Engine & Dispatcher

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Modular_Decoupled-orange?style=flat)]()
[![GUI](https://img.shields.io/badge/GUI-CustomTkinter-blue?style=flat)](https://github.com/TomSchimansky/CustomTkinter)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Motor de satisfacción de restricciones (CSP) para la automatización y despacho de asignaciones mensuales. Diseñado para mitigar la fatiga operativa, balancear equitativamente cargas de trabajo mediante penalización multicriterio y exportar matrices listas para impresión y despliegue digital.

---

## Algoritmo y Resolución de Restricciones

El sistema opera como un despachador determinista guiado por heurísticas de costo mínimo. Para cada semana, el motor evalúa el espacio de candidatos utilizando una función de coste acumulado:

```text
Puntos(h) = CargaBase(h) + P[rol_mes] + P[previa] + P[fatiga] + P[pareja] + P[doblete]
```

- **Balance Cero-Sesgo:** Ponderación basada en el historial del mes (`CargaBase`).
- **Penalizaciones:** Prevención estricta de repetición de roles ($+16$), fatiga por semanas consecutivas ($+12$) y parejas duplicadas ($+14$).
- **Válvula de Emergencia ($+35$):** Si un rol crítico queda desierto por restricciones cruzadas, el motor flexibiliza exclusiones permitiendo un "doblete" justificado sin colapsar la matriz.

---

## Arquitectura del Sistema

Diseño desacoplado basado en capas para separar la interfaz de usuario, la lógica de dominio y el motor de exportación:

```text
┌─────────────────────────────────────────────────────────┐
│              Capa de Presentación (UI)                  │
│       CustomTkinter Desktop App (interfaz_grafica.py)   │
└───────────────────────────┬─────────────────────────────┘
                            │ Dispara ejecución / Parámetros
┌───────────────────────────▼─────────────────────────────┐
│               Capa de Dominio y Lógica                  │
│     Motor Heurístico de Asignación (motor_asignacion.py)│
└──────────────┬───────────────────────────┬──────────────┘
               │ Valida disponibilidad     │ Entrega matriz
┌──────────────▼──────────────┐ ┌──────────▼──────────────┐
│     Persistencia Local      │ │ Motor Editorial XLSX    │
│  - hermanos.json (Perfil)   │ │ (exportador_excel.py)   │
│  - ausencias.json (Temp)    │ └──────────┬──────────────┘
│  - estado.json (Rotación)   │            │ Genera
└─────────────────────────────┘ ┌──────────▼──────────────┐
                                │ Artefacto Final (.xlsx) │
                                │ A4 Horizontal Print/View│
                                └─────────────────────────┘
```

## Stack Tecnológico

- **Python 3.12:** Core del motor, tipado estático (typing) y heurística.

- **Openpyxl:** Manipulación a bajo nivel de XML de celdas para exportación editorial en A4, sin depender de motores ofimáticos instalados.

- **CustomTkinter:** Interfaz gráfica nativa con escalado DPI, modo oscuro y aceleración por hardware.

- **JSON:** Persistencia modular de estado y perfiles sin bases de datos pesadas (Portable I/O).

---

## Datos locales y reglas de producto

La lista real de hermanos **no se versiona**. Copia `data/hermanos.example.json` a `data/hermanos.json` y edita en el PC. Ese archivo, junto con `data/estado.json` y `data/ausencias.json`, queda fuera de git.

**Semanas:** cada martes del mes abre una semana hasta el domingo (cinco días después). Si el domingo es del mes siguiente, igual entra en este programa.

**Regenerar el mismo mes** no avanza los grupos de limpieza. Volver a un mes anterior después de haber generado otro sí puede desfasar la rotación (solo se recuerda el último mes).

**Puestos incompletos** se exportan igual: la interfaz avisa en rojo y lista los huecos.

No hay envío automático por WhatsApp. Los roles válidos están en `data/roles.txt` (`audio` y `video`; no `sonido`). El cargador lee ese archivo al validar `hermanos.json`.
