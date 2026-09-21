import random


# Diccionario de puestos requeridos cada semana en las dos reuniones
PUESTOS_REQUERIDOS = {
    "presidente": 1,
    "lector_domingo": 1,
    "audio": 1,
    "video": 1,
    "plataforma": 1,
    "lector_martes": 1,
    "microfonos": 2,
    "acomodador": 2
}


# Funcion para filtrar el grupo de hermanos por rol
def filtrar_por_rol(hermanos: list[dict], rol: str) -> list[dict]:
    candidatos = []

    for hermano in hermanos:
        if rol in hermano["roles"]:
            candidatos.append(hermano)
    return candidatos # Regresa una lista con los hermanos del rol


# Funcion para llevar un historial de las veces que los hermanos han participado
# durante el mes y evitar escoger solo a los primeros.
def inicializar_historial(hermanos: list[dict]) -> dict[str, int]:
    diccionario_historial = {}

    for hermano in hermanos:
        diccionario_historial[hermano["nombre"]] = 0
    return diccionario_historial


# Funcion para asignar una semana real
def asignar_semana(
    hermanos: list[dict],
    historial_carga: dict[str, int],
    asignados_semana_anterior: dict[str, str] = None
) -> dict[str, list[str]]:
    if asignados_semana_anterior is None:
        asignados_semana_anterior = {}

    asignaciones_semana = {}
    ocupados_esta_semana = set()
    roles_esta_semana = {}  # Rastrear qué rol tiene cada hermano esta semana

    for puesto, cantidad in PUESTOS_REQUERIDOS.items():
        capacitados = filtrar_por_rol(hermanos, puesto)
        
        # 1. Candidatos ideales: capacitados y 100% libres esta semana
        disponibles = [h for h in capacitados if h["nombre"] not in ocupados_esta_semana]

        # 2. VÁLVULA DE ESCAPE: Exclusiva para lector_martes si se agotó el personal libre
        es_caso_emergencia = False
        if puesto == "lector_martes" and len(disponibles) < cantidad:
            es_caso_emergencia = True
            puestos_compatibles = {"microfonos", "audio", "video"}
            
            # Buscamos a capacitados que solo estén en puestos compatibles
            candidatos_auxilio = [
                h for h in capacitados 
                if roles_esta_semana.get(h["nombre"]) in puestos_compatibles
            ]
            disponibles.extend(candidatos_auxilio)

        random.shuffle(disponibles)

        def calcular_prioridad(hermano):
            nombre = hermano["nombre"]
            puntos = historial_carga[nombre]

            # Penalización por haber servido la semana pasada
            if nombre in asignados_semana_anterior:
                puntos += 2
                if asignados_semana_anterior[nombre] == puesto:
                    puntos += 5

            # Penalización masiva si es un doblete de emergencia en la misma semana
            if es_caso_emergencia and nombre in ocupados_esta_semana:
                puntos += 25

            return puntos

        disponibles.sort(key=calcular_prioridad)
        seleccionados = disponibles[:cantidad]

        asignaciones_semana[puesto] = [h["nombre"] for h in seleccionados]

        for h in seleccionados:
            nombre = h["nombre"]
            ocupados_esta_semana.add(nombre)
            roles_esta_semana[nombre] = puesto
            historial_carga[nombre] += 1

    return asignaciones_semana


# Generar el mes completo
def generar_mes(hermanos: list[dict], num_semanas: int = 4) -> dict[int, dict]:
    historial_carga = inicializar_historial(hermanos)
    mes_completo = {}

    asignados_previa = {}
 
    for semana in range(1, num_semanas + 1):
        semana_actual = asignar_semana(hermanos, historial_carga, asignados_previa)
        mes_completo[semana] = semana_actual

        asignados_previa = {}
        for puesto, lista_hermanos in semana_actual.items():
            for nombre in lista_hermanos:
                asignados_previa[nombre] = puesto

    return mes_completo


if __name__ == "__main__":
    from cargador_datos import cargar_hermanos
    
    hermanos = cargar_hermanos("data/hermanos.json")
    mes = generar_mes(hermanos, num_semanas=4)
    
    for semana, asignaciones in mes.items():
        print(f"\n=== SEMANA {semana} ===")
        for puesto, asignados in asignaciones.items():
            print(f"  {puesto}: {asignados}")

