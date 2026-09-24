import random
from typing import Dict, List, Optional, Set, Union

from configuracion import logger
from modelos import Hermano, ReglasAsignacion


class MotorAsignacion:
    """
    Motor heurístico de satisfacción de restricciones y balance de carga
    para la asignación mensual de puestos en la congregación.
    """

    def __init__(
        self,
        hermanos: List[Union[Hermano, dict]],
        reglas: Optional[ReglasAsignacion] = None,
        seed: Optional[int] = None,
    ):
        self.reglas = reglas or ReglasAsignacion()
        self.rng = random.Random(seed)

        # Normalizar hermanos a objetos Hermano
        self.hermanos: List[Hermano] = []
        for h in hermanos:
            if isinstance(h, Hermano):
                self.hermanos.append(h)
            elif isinstance(h, dict):
                self.hermanos.append(Hermano(**h))
            else:
                raise ValueError(
                    f"Formato de hermano inválido: {type(h)}. Se esperaba Hermano o dict."
                )

        self.historial_carga: Dict[str, dict] = self._inicializar_historial()

    def _inicializar_historial(self) -> Dict[str, dict]:
        """Inicializa contadores de equidad, roles previos, parejas y rachas de trabajo."""
        historial = {}
        for h in self.hermanos:
            historial[h.nombre] = {
                "global": 0,
                "cabina": 0,
                "semanas_consecutivas": 0,
                "roles_mes": set(),
                "parejas_mes": set(),
            }
        return historial

    def reiniciar_historial(self):
        """Reinicia el historial de carga acumulado."""
        self.historial_carga = self._inicializar_historial()

    def filtrar_por_rol(self, rol: str) -> List[Hermano]:
        """Retorna los hermanos capacitados para un rol específico."""
        return [h for h in self.hermanos if rol in h.roles]

    def _calcular_costo_candidato(
        self,
        hermano: Hermano,
        puesto: str,
        seleccionados: List[Hermano],
        asignados_semana_anterior: Dict[str, str],
        ocupados_esta_semana: Set[str],
        es_caso_emergencia: bool,
    ) -> int:
        """Calcula el coste acumulado de asignar a un hermano a un puesto."""
        nombre = hermano.nombre
        registro = self.historial_carga[nombre]

        # 1. Base de carga unificada: siempre usamos la carga global
        # Multiplicamos por 2 para que el balance total del mes tenga más peso (rotación más equitativa).
        puntos = registro["global"] * 2

        # 2. Equilibrio interno para cabina:
        # Si es un puesto técnico, penalizamos adicionalmente si ya ha hecho cabina,
        # para rotarlos internamente, pero sin ignorar su carga global previa.
        if puesto in ["audio", "video"]:
            puntos += registro["cabina"] * 2

        # 1. Penalización si ya hizo este rol específico en el mes
        if puesto in registro["roles_mes"]:
            puntos += self.reglas.penalizacion_rol_repetido_mes

        # 2. Penalización por servicio en la semana anterior
        if nombre in asignados_semana_anterior:
            puntos += self.reglas.penalizacion_semana_anterior
            if asignados_semana_anterior[nombre] == puesto:
                puntos += self.reglas.penalizacion_mismo_rol_semana_anterior

        # 3. Penalización por fatiga (semanas seguidas trabajando)
        if registro["semanas_consecutivas"] >= self.reglas.limite_semanas_fatiga:
            puntos += self.reglas.penalizacion_fatiga

        # 4. Penalización por pareja repetida en el mes
        if seleccionados:
            companero_actual = seleccionados[0].nombre
            if companero_actual in registro["parejas_mes"]:
                puntos += self.reglas.penalizacion_pareja_repetida

        # 5. Doblete en la misma semana (solo emergencia)
        if es_caso_emergencia and nombre in ocupados_esta_semana:
            puntos += self.reglas.penalizacion_doblete_emergencia

        return puntos

    def asignar_semana(
        self,
        semana_idx: int = 1,
        asignados_semana_anterior: Optional[Dict[str, str]] = None,
        ausentes_esta_semana: Optional[Set[str]] = None,
    ) -> Dict[str, List[str]]:
        """Genera las asignaciones para una semana individual."""
        if asignados_semana_anterior is None:
            asignados_semana_anterior = {}
        if ausentes_esta_semana is None:
            ausentes_esta_semana = set()

        asignaciones_semana: Dict[str, List[str]] = {}
        ocupados_esta_semana = set(ausentes_esta_semana)
        roles_esta_semana: Dict[str, str] = {}

        for puesto, cantidad in self.reglas.puestos_requeridos.items():
            capacitados = self.filtrar_por_rol(puesto)
            disponibles = [h for h in capacitados if h.nombre not in ocupados_esta_semana]

            # Válvula de escape para lector_martes si faltan disponibles
            es_caso_emergencia = False
            if puesto == "lector_martes" and len(disponibles) < cantidad:
                es_caso_emergencia = True
                logger.warning(
                    "Semana %d: Válvula de emergencia activada para 'lector_martes'. "
                    "Buscando candidatos de auxilio.",
                    semana_idx,
                )
                candidatos_auxilio = [
                    h
                    for h in capacitados
                    if roles_esta_semana.get(h.nombre) in self.reglas.puestos_emergencia_compatibles
                    and h.nombre not in ausentes_esta_semana
                ]
                disponibles.extend(candidatos_auxilio)

            # Barajado aleatorio para desempates deterministas/estocásticos
            self.rng.shuffle(disponibles)
            seleccionados: List[Hermano] = []

            for _ in range(cantidad):
                candidatos_ronda = [
                    h for h in disponibles if h.nombre not in [s.nombre for s in seleccionados]
                ]

                if not candidatos_ronda:
                    break

                candidatos_ronda.sort(
                    key=lambda h: self._calcular_costo_candidato(
                        h,
                        puesto,
                        seleccionados,
                        asignados_semana_anterior,
                        ocupados_esta_semana,
                        es_caso_emergencia,
                    )
                )
                seleccionados.append(candidatos_ronda[0])

            if len(seleccionados) < cantidad:
                logger.warning(
                    "Semana %d: No se pudo completar el puesto '%s' (%d de %d asignados).",
                    semana_idx,
                    puesto,
                    len(seleccionados),
                    cantidad,
                )

            asignaciones_semana[puesto] = [h.nombre for h in seleccionados]

            # Actualizar estado de los elegidos
            nombres_elegidos = [h.nombre for h in seleccionados]
            for h in seleccionados:
                nombre = h.nombre
                ocupados_esta_semana.add(nombre)
                roles_esta_semana[nombre] = puesto

                self.historial_carga[nombre]["global"] += 1
                self.historial_carga[nombre]["roles_mes"].add(puesto)

                if puesto in ["audio", "video"]:
                    self.historial_carga[nombre]["cabina"] += 1

                for otro_nombre in nombres_elegidos:
                    if otro_nombre != nombre:
                        self.historial_carga[nombre]["parejas_mes"].add(otro_nombre)

        # Actualizar contador de semanas consecutivas
        for h in self.hermanos:
            nombre = h.nombre
            if nombre in roles_esta_semana:
                self.historial_carga[nombre]["semanas_consecutivas"] += 1
            else:
                self.historial_carga[nombre]["semanas_consecutivas"] = 0

        return asignaciones_semana

    def generar_mes(
        self,
        num_semanas: int,
        ausencias: Optional[Dict[int, List[str]]] = None,
    ) -> Dict[int, Dict[str, List[str]]]:
        """Genera las asignaciones mensuales respetando la rotación equitativa."""
        if num_semanas <= 0:
            raise ValueError(f"El número de semanas debe ser mayor a 0, se recibió: {num_semanas}")

        if ausencias is None:
            ausencias = {}

        logger.info(
            "Iniciando generación mensual para %d semanas con %d personas registradas.",
            num_semanas,
            len(self.hermanos),
        )

        mes_completo = {}
        asignados_previa: Dict[str, str] = {}

        for semana in range(1, num_semanas + 1):
            ausentes_esta_semana = set(ausencias.get(semana, []))
            semana_actual = self.asignar_semana(
                semana_idx=semana,
                asignados_semana_anterior=asignados_previa,
                ausentes_esta_semana=ausentes_esta_semana,
            )
            mes_completo[semana] = semana_actual

            # Guardar roles para penalizar repetición inmediata en la siguiente semana
            asignados_previa = {}
            for puesto, lista_hermanos in semana_actual.items():
                for nombre in lista_hermanos:
                    asignados_previa[nombre] = puesto

        logger.info("Generación de asignaciones completada.")
        return mes_completo

    def listar_puestos_incompletos(
        self, mes_asignaciones: Dict[int, Dict[str, List[str]]]
    ) -> List[dict]:
        """Detecta puestos con menos personas que los requeridos en alguna semana."""
        huecos = []
        for semana, asignaciones in sorted(mes_asignaciones.items()):
            for puesto, cantidad in self.reglas.puestos_requeridos.items():
                nombres = asignaciones.get(puesto, [])
                if len(nombres) < cantidad:
                    huecos.append(
                        {
                            "semana": semana,
                            "puesto": puesto,
                            "asignados": len(nombres),
                            "requeridos": cantidad,
                        }
                    )
        return huecos
