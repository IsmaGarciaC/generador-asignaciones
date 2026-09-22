import random

# Orden de puestos: de los más restrictivos/técnicos a los más generales
PUESTOS_REQUERIDOS = {
    "presidente": 1,
    "lector_domingo": 1,
    "audio": 1,
    "video": 1,
    "plataforma": 1,
    "lector_martes": 1,
    "microfonos": 2,
    "acomodador": 2,
}


def filtrar_por_rol(hermanos: list[dict], rol: str) -> list[dict]:
    """Retorna los hermanos capacitados para un rol específico."""
    return [h for h in hermanos if rol in h["roles"]]


def inicializar_historial(hermanos: list[dict]) -> dict[str, dict]:
    """Inicializa contadores de equidad, roles previos, parejas y rachas de trabajo."""
    historial = {}
    for h in hermanos:
        historial[h["nombre"]] = {
            "global": 0,
            "cabina": 0,
            "semanas_consecutivas": 0,
            "roles_mes": set(),
            "parejas_mes": set(),
        }
    return historial


def asignar_semana(
    hermanos: list[dict],
    historial_carga: dict[str, dict],
    asignados_semana_anterior: dict[str, str] = None,
    ausentes_esta_semana: set[str] = None,  # <-- 1. NUEVO PARÁMETRO
) -> dict[str, list[str]]:
    """Genera las asignaciones para una semana individual."""
    if asignados_semana_anterior is None:
        asignados_semana_anterior = {}
    if ausentes_esta_semana is None:
        ausentes_esta_semana = set()

    asignaciones_semana = {}
    
    # 2. Los ausentes inician como "ocupados", impidiendo su selección en cualquier puesto
    ocupados_esta_semana = set(ausentes_esta_semana)
    roles_esta_semana = {}

    for puesto, cantidad in PUESTOS_REQUERIDOS.items():
        capacitados = filtrar_por_rol(hermanos, puesto)
        disponibles = [h for h in capacitados if h["nombre"] not in ocupados_esta_semana]

        # Válvula de escape exclusiva para lector_martes si falta personal disponible
        es_caso_emergencia = False
        if puesto == "lector_martes" and len(disponibles) < cantidad:
            es_caso_emergencia = True
            puestos_compatibles = {"microfonos", "audio", "video"}
            candidatos_auxilio = [
                h for h in capacitados
                if roles_esta_semana.get(h["nombre"]) in puestos_compatibles
                and h["nombre"] not in ausentes_esta_semana  # Garantizar que nunca auxilie un ausente
            ]
            disponibles.extend(candidatos_auxilio)

        random.shuffle(disponibles)
        seleccionados = []

        # Selección iterativa para evaluar compatibilidad de compañeros en puestos múltiples
        for _ in range(cantidad):
            candidatos_ronda = [
                h for h in disponibles
                if h["nombre"] not in [s["nombre"] for s in seleccionados]
            ]

            if not candidatos_ronda:
                break

            def calcular_prioridad(hermano):
                nombre = hermano["nombre"]
                registro = historial_carga[nombre]

                # Base de carga según el tipo de labor
                if puesto in ["audio", "video"]:
                    puntos = registro["cabina"]
                else:
                    puntos = registro["global"]

                # 1. Penalización si ya hizo este rol específico en el mes
                if puesto in registro["roles_mes"]:
                    puntos += 16

                # 2. Penalización por servicio en la semana anterior
                if nombre in asignados_semana_anterior:
                    puntos += 3
                    if asignados_semana_anterior[nombre] == puesto:
                        puntos += 10

                # 3. Penalización por fatiga (2 o más semanas seguidas trabajando)
                if registro["semanas_consecutivas"] >= 2:
                    puntos += 12

                # 4. Penalización por pareja repetida en el mes
                if seleccionados:
                    companero_actual = seleccionados[0]["nombre"]
                    if companero_actual in registro["parejas_mes"]:
                        puntos += 14

                # 5. Doblete en la misma semana (solo emergencia)
                if es_caso_emergencia and nombre in ocupados_esta_semana:
                    puntos += 35

                return puntos

            candidatos_ronda.sort(key=calcular_prioridad)
            seleccionados.append(candidatos_ronda[0])

        asignaciones_semana[puesto] = [h["nombre"] for h in seleccionados]

        # Actualizar datos de los seleccionados en este puesto
        nombres_elegidos = [h["nombre"] for h in seleccionados]
        for h in seleccionados:
            nombre = h["nombre"]
            ocupados_esta_semana.add(nombre)
            roles_esta_semana[nombre] = puesto

            historial_carga[nombre]["global"] += 1
            historial_carga[nombre]["roles_mes"].add(puesto)

            if puesto in ["audio", "video"]:
                historial_carga[nombre]["cabina"] += 1

            for otro_nombre in nombres_elegidos:
                if otro_nombre != nombre:
                    historial_carga[nombre]["parejas_mes"].add(otro_nombre)

    # Actualizar contador de semanas consecutivas solo para quienes tuvieron asignación real
    for h in hermanos:
        nombre = h["nombre"]
        if nombre in roles_esta_semana:
            historial_carga[nombre]["semanas_consecutivas"] += 1
        else:
            historial_carga[nombre]["semanas_consecutivas"] = 0

    return asignaciones_semana


def generar_mes(
    hermanos: list[dict],
    num_semanas: int,
    ausencias: dict[int, list[str]] | None = None,
) -> dict[int, dict]:
    """
    Genera las asignaciones mensuales respetando la rotación equitativa.
    
    :param ausencias: Diccionario {semana_int: [lista_nombres_no_disponibles]}
                      Ejemplo: {1: ["Santiago Silva"], 2: ["Santiago Silva", "Josué Briones"]}
    """
    if ausencias is None:
        ausencias = {}

    historial_carga = inicializar_historial(hermanos)
    mes_completo = {}
    asignados_previa = {}

    for semana in range(1, num_semanas + 1):
        # 3. Extraer los ausentes de esta semana y enviarlos al asignador
        ausentes_esta_semana = set(ausencias.get(semana, []))
        semana_actual = asignar_semana(
            hermanos, 
            historial_carga, 
            asignados_previa, 
            ausentes_esta_semana=ausentes_esta_semana
        )
        mes_completo[semana] = semana_actual

        asignados_previa = {}
        for puesto, lista_hermanos in semana_actual.items():
            for nombre in lista_hermanos:
                asignados_previa[nombre] = puesto

    return mes_completo


if __name__ == "__main__":
    from cargador_datos import cargar_hermanos

    hermanos = cargar_hermanos("data/hermanos.json")
    
    # Prueba rápida simulando ausencia del hermano en la semana 1
    ausencias_prueba = {1: ["Santiago Silva"]}
    mes = generar_mes(hermanos, num_semanas=4, ausencias=ausencias_prueba)

    for semana, asignaciones in mes.items():
        print(f"\n=== SEMANA {semana} ===")
        for puesto, asignados in asignaciones.items():
            print(f"  {puesto:15}: {asignados}")