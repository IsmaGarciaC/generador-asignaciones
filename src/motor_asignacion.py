# Diccionario de puestos requeridos cada semana en las dos reuniones
PUESTOS_REQUERIDOS = {
    "acomodador": 2,
    "microfonos": 2,
    "sonido": 2,
    "plataforma": 1,
    "lector_martes": 1,
    "lector_domingo": 1
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
def asignar_semana(hermanos: list[dict], historial_carga: dict[str, int]) -> dict[str, list[str]]:
    asignaciones_semana = {}
    ocupados_esta_semana = set()

    for puesto, cantidad in PUESTOS_REQUERIDOS.items():
        capacitados = filtrar_por_rol(hermanos, puesto)
        disponibles = []

        for hermano in capacitados:
            if hermano["nombre"] not in ocupados_esta_semana:
                disponibles.append(hermano)
        
        # Ordenar por quien menos ha trabajado
        disponibles.sort(key=lambda h: historial_carga[h["nombre"]])
        
        # Tomar a los que necesitamos
        seleccionados = disponibles[:cantidad]

        # Guardar solo los nombres en el cuadro de la semana
        asignaciones_semana[puesto] = [h["nombre"] for h in seleccionados]

        # Actualizar ocupados y la carga de cada uno
        for h in seleccionados:
            nombre = h["nombre"]
            ocupados_esta_semana.add(nombre)
            historial_carga[nombre] += 1
            
    return asignaciones_semana

if __name__ == "__main__":
    from cargador_datos import cargar_hermanos
    
    hermanos = cargar_hermanos("data/hermanos.json")
    historial = inicializar_historial(hermanos)
    
    print("--- ASIGNACIONES SEMANA 1 ---")
    semana_1 = asignar_semana(hermanos, historial)
    for puesto, asignados in semana_1.items():
        print(f"{puesto}: {asignados}")
        
    print("\nCarga acumulada tras la primera semana:")
    print(historial)

