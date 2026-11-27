"""Referencia V1. Ejecutar con su Python 3.12 y -B para evitar escrituras en src/."""

import logging
import sys
from collections import Counter
from pathlib import Path

from datos import escenario

if __name__ == "__main__":
    sys.dont_write_bytecode = True
    logging.getLogger("generador_asignaciones").addHandler(logging.NullHandler())
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from modelos import ReglasAsignacion
    from motor_asignacion import MotorAsignacion

    for n, semanas in ((15, 4), (25, 5), (40, 5)):
        mes = escenario(n, semanas)
        personas = [
            {"id": p.id, "nombre": f"Persona {p.id}", "roles": p.puestos} for p in mes.personas
        ]
        ausencias = {
            s: [f"Persona {p.id}" for p in mes.personas if s in p.ausencias]
            for s in range(1, semanas + 1)
        }
        asignaciones = MotorAsignacion(personas, seed=73).generar_mes(semanas, ausencias)
        cobertura = dobles = 0
        for roles in asignaciones.values():
            carga = Counter(nombre for lista in roles.values() for nombre in lista)
            cobertura += sum(carga.values())
            dobles += sum(n == 2 for n in carga.values())
        print(f"{n} personas, {semanas} semanas: {cobertura} cubiertas, {dobles} dobletes")

    # Mismo orden, candidatos y restricciones efectivas en el contraejemplo mínimo.
    personas = [
        {"id": 1, "nombre": "AB", "roles": {"audio", "video"}},
        {"id": 2, "nombre": "A", "roles": {"audio"}},
    ]
    reglas = ReglasAsignacion(puestos_requeridos={"audio": 1, "video": 1})
    plan = MotorAsignacion(personas, reglas, seed=0).asignar_semana()
    print("Contraejemplo de una semana:", plan)
