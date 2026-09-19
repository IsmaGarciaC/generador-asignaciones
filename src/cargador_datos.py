import json
import pathlib

roles = {"acomodador", "microfonos", "plataforma", "lector_martes", "lector_domingo", "presidente", "sonido"}

def cargar_hermanos(ruta_archivo):
    with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
        hermanos = json.load(archivo)

        campos_requeridos = ["id", "nombre", "telefono", "roles"]
        
        for hermano in hermanos:
            for campo in campos_requeridos:
                if campo not in hermano:
                    print('Campo invalido')
                    return
            for rol in hermano["roles"]:
                if rol not in roles:
                    print(f'Rol desconocido: {rol}')
    return hermanos


if __name__ == "__main__":
    datos = cargar_hermanos("data/hermanos.json")
    print(f"Total cargados: {len(datos)}")
