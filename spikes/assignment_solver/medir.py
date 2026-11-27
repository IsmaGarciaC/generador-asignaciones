"""Ejecutar desde el entorno de CP-SAT. Emite resultados JSON en la consola."""

import argparse
import json
from dataclasses import asdict
from time import perf_counter

from datos import escenario
from evaluacion import metricas
from solver import resolver


def medir(segundos: float) -> None:
    for n, semanas, dificil in ((15, 4, False), (25, 5, False), (40, 5, False), (15, 5, True)):
        mes = escenario(n, semanas, dificil=dificil)
        inicio = perf_counter()
        resultado = resolver(mes, segundos)
        total = perf_counter() - inicio
        print(
            json.dumps(
                {
                    "personas": n,
                    "semanas": semanas,
                    "dificil": dificil,
                    "requeridas": len(mes.requeridas()),
                    "estado": resultado.estado,
                    "total_s": round(total, 4),
                    "etapas": [asdict(e) for e in resultado.etapas],
                    "metricas": metricas(mes, resultado.plan)
                    if resultado.plan is not None
                    else None,
                    "vacantes": resultado.vacantes if resultado.plan is not None else None,
                    "diagnostico": resultado.diagnostico,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--segundos", type=float, default=5, help="límite de búsqueda por etapa")
    medir(parser.parse_args().segundos)
