import pytest

from modelos import Hermano, ReglasAsignacion
from motor_asignacion import MotorAsignacion


@pytest.fixture
def hermanos_base():
    """Genera un listado balanceado de hermanos para pruebas."""
    return [
        Hermano(id=1, nombre="Hno 1", roles=["presidente", "lector_domingo"]),
        Hermano(id=2, nombre="Hno 2", roles=["presidente", "lector_martes"]),
        Hermano(id=3, nombre="Hno 3", roles=["audio", "video"]),
        Hermano(id=4, nombre="Hno 4", roles=["audio", "video"]),
        Hermano(id=5, nombre="Hno 5", roles=["plataforma", "microfonos"]),
        Hermano(id=6, nombre="Hno 6", roles=["plataforma", "acomodador"]),
        Hermano(id=7, nombre="Hno 7", roles=["microfonos", "acomodador"]),
        Hermano(id=8, nombre="Hno 8", roles=["microfonos", "acomodador"]),
        Hermano(id=9, nombre="Hno 9", roles=["lector_martes", "acomodador"]),
        Hermano(id=10, nombre="Hno 10", roles=["lector_domingo", "acomodador"]),
    ]


def test_determinismo_con_semilla(hermanos_base):
    motor_a = MotorAsignacion(hermanos=hermanos_base, seed=42)
    mes_a = motor_a.generar_mes(num_semanas=3)

    motor_b = MotorAsignacion(hermanos=hermanos_base, seed=42)
    mes_b = motor_b.generar_mes(num_semanas=3)

    assert mes_a == mes_b


def test_motor_respeta_ausencias(hermanos_base):
    # Declaramos que Hno 3 (capacitado para audio/video) está ausente en la semana 1
    ausencias = {1: ["Hno 3"]}
    motor = MotorAsignacion(hermanos=hermanos_base, seed=10)
    mes = motor.generar_mes(num_semanas=2, ausencias=ausencias)

    # Verificar que Hno 3 no aparece en ninguna asignación de la semana 1
    for puesto, asignados in mes[1].items():
        assert "Hno 3" not in asignados, f"Hno 3 fue asignado a {puesto} estando ausente!"


def test_listar_puestos_incompletos():
    # Si tenemos muy pocos hermanos, deben detectarse los puestos que faltan llenar
    pocos_hermanos = [
        Hermano(id=1, nombre="Hno Solo", roles=["audio"]),
    ]
    motor = MotorAsignacion(hermanos=pocos_hermanos, seed=1)
    mes = motor.generar_mes(num_semanas=1)

    huecos = motor.listar_puestos_incompletos(mes)
    assert len(huecos) > 0
    puestos_faltantes = [h["puesto"] for h in huecos]
    assert "video" in puestos_faltantes
    assert "presidente" in puestos_faltantes


def test_valvula_emergencia_lector_martes():
    # Solo 2 hermanos: uno hace microfonos y además puede leer el martes
    # El otro solo hace audio
    hermanos = [
        Hermano(id=1, nombre="Hermano Polifacético", roles=["microfonos", "lector_martes"]),
        Hermano(id=2, nombre="Hermano Audio", roles=["audio"]),
    ]
    # Reglas donde solo requerimos microfonos y lector_martes
    reglas = ReglasAsignacion(puestos_requeridos={"microfonos": 1, "lector_martes": 1})
    motor = MotorAsignacion(hermanos=hermanos, reglas=reglas, seed=1)
    mes = motor.generar_mes(num_semanas=1)

    # Hermano Polifacético debió tomar micrófonos primero y luego auxiliar en lector_martes
    assert "Hermano Polifacético" in mes[1]["microfonos"]
    assert "Hermano Polifacético" in mes[1]["lector_martes"]
