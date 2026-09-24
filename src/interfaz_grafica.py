import datetime
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import customtkinter as ctk

# Asegurar importaciones locales tanto en desarrollo como en ejecutable
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "src"))

from configuracion import BASE_DIR, logger  # noqa: E402
from exportador_excel import (  # noqa: E402
    calcular_semanas_mes,
    exportar_programa_excel,
)
from modelos import EstadoMes, ReglasAsignacion  # noqa: E402
from motor_asignacion import MotorAsignacion  # noqa: E402
from repositorio import DatosInvalidosError, Repositorio  # noqa: E402

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

MESES = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

_reglas = ReglasAsignacion()
ETIQUETAS_PUESTO = {
    item["key"]: item["label"]
    for item in _reglas.estructura_programa
    if not item["es_seccion"] and item["key"] not in ("limpieza", "hospitalidad")
}


class VentanaAusencias(ctk.CTkToplevel):
    """
    Ventana emergente para registrar hermanos que no estarán disponibles
    en semanas específicas.
    """

    def __init__(
        self,
        parent,
        repo: Repositorio,
        hermanos_nombres: List[str],
        anio: int,
        mes_idx: int,
        num_semanas: int,
    ):
        super().__init__(parent)
        self.title("Gestionar Ausencias")
        self.geometry("540x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.parent_app = parent
        self.repo = repo
        self.hermanos_nombres = sorted(hermanos_nombres)
        self.anio = anio
        self.mes_idx = mes_idx
        self.num_semanas = num_semanas

        self.ausencias_mes = self.repo.leer_ausencias_mes(self.anio, self.mes_idx)
        self.checkboxes_semanas: list[ctk.CTkCheckBox] = []

        self._construir_ui()

    def _guardar_en_disco(self):
        self.repo.guardar_ausencias_mes(self.anio, self.mes_idx, self.ausencias_mes)

    def _construir_ui(self):
        lbl_tit = ctk.CTkLabel(
            self,
            text=f"Ausencias para {MESES[self.mes_idx - 1]} {self.anio}",
            font=ctk.CTkFont(family="Aptos", size=16, weight="bold"),
        )
        lbl_tit.pack(pady=(15, 5))

        lbl_desc = ctk.CTkLabel(
            self,
            text="Selecciona el hermano y marca las semanas en que NO estará disponible.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        lbl_desc.pack(pady=(0, 10))

        # Selector de hermano
        frame_sel = ctk.CTkFrame(self, fg_color="transparent")
        frame_sel.pack(fill="x", padx=20, pady=5)

        lbl_h = ctk.CTkLabel(frame_sel, text="Hermano:", font=ctk.CTkFont(weight="bold"))
        lbl_h.pack(side="left", padx=(0, 10))

        self.combo_hermano = ctk.CTkComboBox(
            frame_sel,
            values=self.hermanos_nombres,
            width=260,
            command=self._al_cambiar_hermano,
        )
        self.combo_hermano.pack(side="left")
        if self.hermanos_nombres:
            self.combo_hermano.set(self.hermanos_nombres[0])

        # Checkboxes de semanas
        frame_sems = ctk.CTkFrame(self)
        frame_sems.pack(fill="x", padx=20, pady=12)

        lbl_sem_tit = ctk.CTkLabel(
            frame_sems, text="Semanas ausente:", font=ctk.CTkFont(weight="bold")
        )
        lbl_sem_tit.pack(anchor="w", padx=10, pady=(8, 4))

        frame_checks = ctk.CTkFrame(frame_sems, fg_color="transparent")
        frame_checks.pack(pady=6)

        for s in range(1, self.num_semanas + 1):
            var = ctk.BooleanVar(value=False)
            chk = ctk.CTkCheckBox(frame_checks, text=f"Sem {s}", variable=var)
            chk.pack(side="left", padx=8)
            self.checkboxes_semanas.append((s, var))

        # Botones para guardar / quitar ausencia
        frame_btn_h = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn_h.pack(fill="x", padx=20, pady=5)

        btn_asignar = ctk.CTkButton(
            frame_btn_h,
            text="Guardar Ausencia para este Hermano",
            command=self._guardar_ausencia_hermano,
        )
        btn_asignar.pack(side="left", expand=True, fill="x", padx=(0, 5))

        btn_quitar = ctk.CTkButton(
            frame_btn_h,
            text="Quitar Ausencias",
            fg_color="#A93226",
            hover_color="#7B241C",
            command=self._quitar_ausencia_hermano,
        )
        btn_quitar.pack(side="left", padx=(5, 0))

        # Lista de ausentes registrados
        lbl_list = ctk.CTkLabel(
            self,
            text="Ausencias Registradas en este Mes:",
            font=ctk.CTkFont(weight="bold"),
        )
        lbl_list.pack(anchor="w", padx=20, pady=(12, 4))

        self.txt_lista = ctk.CTkTextbox(
            self, height=120, font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.txt_lista.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Botón Cerrar
        btn_cerrar = ctk.CTkButton(self, text="Listo / Cerrar", command=self.destroy)
        btn_cerrar.pack(pady=(0, 12))

        self._al_cambiar_hermano(self.combo_hermano.get())
        self._actualizar_visor_lista()

    def _al_cambiar_hermano(self, nombre: str):
        sems_ausente = self.ausencias_mes.get(nombre, [])
        for s, var in self.checkboxes_semanas:
            var.set(s in sems_ausente)

    def _guardar_ausencia_hermano(self):
        nombre = self.combo_hermano.get()
        if not nombre:
            return

        sems_marcadas = [s for s, var in self.checkboxes_semanas if var.get()]
        if sems_marcadas:
            self.ausencias_mes[nombre] = sems_marcadas
        elif nombre in self.ausencias_mes:
            del self.ausencias_mes[nombre]

        self._guardar_en_disco()
        self._actualizar_visor_lista()
        self.parent_app.actualizar_conteo_ausencias()

    def _quitar_ausencia_hermano(self):
        nombre = self.combo_hermano.get()
        if nombre in self.ausencias_mes:
            del self.ausencias_mes[nombre]
            self._guardar_en_disco()
            self._al_cambiar_hermano(nombre)
            self._actualizar_visor_lista()
            self.parent_app.actualizar_conteo_ausencias()

    def _actualizar_visor_lista(self):
        self.txt_lista.delete("1.0", "end")
        if not self.ausencias_mes:
            self.txt_lista.insert("1.0", "No hay ausencias registradas para este mes.")
            return

        lineas = []
        for nombre, sems in sorted(self.ausencias_mes.items()):
            sems_str = ", ".join(f"Semana {s}" for s in sorted(sems))
            lineas.append(f"• {nombre}: No disponible en {sems_str}")

        self.txt_lista.insert("1.0", "\n".join(lineas))


class VentanaRecordatorios(ctk.CTkToplevel):
    def __init__(
        self, parent, repo: Repositorio, anio: int, mes: int, semanas: list, asignaciones: dict
    ):
        super().__init__(parent)
        self.title(f"Recordatorios - Mes {mes}/{anio}")
        self.geometry("650x550")
        self.grab_set()

        self.repo = repo
        self.asignaciones = asignaciones

        # Mapeo rápido de nombre a teléfono
        self.telefonos = {h.nombre: h.telefono for h in repo.cargar_hermanos()}

        lbl_tit = ctk.CTkLabel(
            self, text="Envío Semiautomático (WhatsApp)", font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_tit.pack(pady=(15, 5))

        lbl_info = ctk.CTkLabel(
            self,
            text=(
                "Selecciona una semana. Abre tu WhatsApp Web o de Escritorio "
                "y haz clic en 'Enviar' para cada hermano. El mensaje ya estará escrito."
            ),
            text_color="gray",
            wraplength=550,
        )
        lbl_info.pack(pady=(0, 15))

        # Selector de Semana
        frame_sem = ctk.CTkFrame(self, fg_color="transparent")
        frame_sem.pack(pady=5)

        ctk.CTkLabel(frame_sem, text="Semana:", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=5
        )
        self.combo_semana = ctk.CTkOptionMenu(
            frame_sem,
            values=[f"Semana {i + 1} - {semanas[i]['fecha_semana']}" for i in range(len(semanas))],
            command=self._al_cambiar_semana,
        )
        self.combo_semana.pack(side="left", padx=5)

        self.btn_enviar_todos = ctk.CTkButton(
            frame_sem,
            text="Enviar a Todos",
            fg_color="#25D366",
            hover_color="#128C7E",
            command=self._enviar_wa_masivo,
        )
        self.btn_enviar_todos.pack(side="left", padx=10)

        self.frame_lista = ctk.CTkScrollableFrame(self)
        self.frame_lista.pack(fill="both", expand=True, padx=20, pady=15)

        if self.asignaciones:
            self._al_cambiar_semana(self.combo_semana.get())
        else:
            ctk.CTkLabel(
                self.frame_lista,
                text="No hay asignaciones guardadas para este mes. Genera el programa primero.",
            ).pack(pady=20)

    def _al_cambiar_semana(self, sel: str):
        for widget in self.frame_lista.winfo_children():
            widget.destroy()

        if not self.asignaciones:
            return

        idx = int(sel.split(" ")[1])
        fecha_semana = sel.split(" - ", 1)[1] if " - " in sel else ""
        asigs_semana = self.asignaciones.get(idx, {})

        # Crear lista
        for rol, nombres in asigs_semana.items():
            if rol in ("limpieza", "hospitalidad"):
                continue

            rol_etiqueta = ETIQUETAS_PUESTO.get(rol, rol)

            for nombre in nombres:
                f_item = ctk.CTkFrame(self.frame_lista)
                f_item.pack(fill="x", pady=2, padx=5)

                telf = self.telefonos.get(nombre, "")

                lbl_n = ctk.CTkLabel(
                    f_item, text=nombre, font=ctk.CTkFont(weight="bold"), width=150, anchor="w"
                )
                lbl_n.pack(side="left", padx=10, pady=5)

                lbl_r = ctk.CTkLabel(f_item, text=rol_etiqueta, width=150, anchor="w")
                lbl_r.pack(side="left", padx=10, pady=5)

                if telf:
                    btn = ctk.CTkButton(
                        f_item,
                        text="Enviar WA",
                        width=100,
                        fg_color="#25D366",
                        hover_color="#128C7E",
                        command=lambda n=nombre, r=rol_etiqueta, t=telf, f=fecha_semana: (
                            self._enviar_wa(n, r, t, f)
                        ),
                    )
                    btn.pack(side="right", padx=10, pady=5)
                else:
                    lbl_t = ctk.CTkLabel(f_item, text="Sin teléfono", text_color="#DC3545")
                    lbl_t.pack(side="right", padx=10, pady=5)

    def _enviar_wa(self, nombre: str, rol: str, telf: str, fecha: str = ""):
        import urllib.parse
        import webbrowser

        fecha_str = f" ({fecha})" if fecha else ""
        msg = (
            f"Buenos días querido hermano: {nombre}. Le recordamos su asignación de *{rol}* "
            f"para esta semana{fecha_str} en la reunión. ¡Gracias por su disposición, y buen trabajo!"
        )
        url = f"https://wa.me/{telf}?text={urllib.parse.quote(msg)}"
        webbrowser.open(url)

    def _enviar_wa_masivo(self):
        sel = self.combo_semana.get()
        if not self.asignaciones or not sel:
            return

        idx = int(sel.split(" ")[1])
        fecha_semana = sel.split(" - ", 1)[1] if " - " in sel else ""
        asigs_semana = self.asignaciones.get(idx, {})

        import threading
        import time
        import urllib.parse
        import webbrowser

        def enviar_lote():
            self.btn_enviar_todos.configure(state="disabled", text="Enviando...")
            try:
                for rol, nombres in asigs_semana.items():
                    if rol in ("limpieza", "hospitalidad"):
                        continue

                    rol_etiqueta = ETIQUETAS_PUESTO.get(rol, rol)
                    for nombre in nombres:
                        telf = self.telefonos.get(nombre, "")
                        if telf:
                            fecha_str = f" ({fecha_semana})" if fecha_semana else ""
                            msg = (
                                f"Buenos días querido hermano: {nombre}. Le recordamos su asignación de *{rol_etiqueta}* "
                                f"para esta semana{fecha_str} en la reunión. ¡Gracias por su disposición, y buen trabajo!"
                            )
                            url = f"https://wa.me/{telf}?text={urllib.parse.quote(msg)}"
                            webbrowser.open(url)
                            time.sleep(1.5)  # Breve pausa para no saturar al navegador
            finally:
                self.btn_enviar_todos.configure(state="normal", text="Enviar a Todos")

        threading.Thread(target=enviar_lote, daemon=True).start()


class VentanaEdicionAsignaciones(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        repo: Repositorio,
        anio: int,
        mes: int,
        semanas: list,
        asignaciones: dict,
        grupo_limpieza: int,
        reglas: ReglasAsignacion,
    ):
        super().__init__(parent)
        self.title(f"Editar Asignaciones - Mes {mes}/{anio}")
        self.geometry("800x650")
        self.grab_set()

        self.parent_app = parent
        self.repo = repo
        self.anio = anio
        self.mes = mes
        self.semanas = semanas
        self.asignaciones = asignaciones or {}
        self.grupo_limpieza = grupo_limpieza
        self.reglas = reglas

        self.hermanos = self.repo.cargar_hermanos()
        self.candidatos_por_rol = {
            rol: ["—"] + [h.nombre for h in self.hermanos if rol in h.roles]
            for rol in self.reglas.puestos_requeridos.keys()
        }

        self.comboboxes: dict[tuple[int, str, int], ctk.CTkComboBox] = {}  # (semana_idx, rol, indice): widget
        self.semana_activa = None

        self._construir_ui()

    def _construir_ui(self):
        lbl_tit = ctk.CTkLabel(
            self, text="Modificar Programa Generado", font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_tit.pack(pady=(15, 5))

        lbl_info = ctk.CTkLabel(
            self,
            text="Al guardar los cambios aquí, se actualizarán los mensajes de WhatsApp automáticamente y se exportará un nuevo archivo Excel.",
            text_color="gray",
            wraplength=650,
        )
        lbl_info.pack(pady=(0, 15))

        frame_sem = ctk.CTkFrame(self, fg_color="transparent")
        frame_sem.pack(pady=5)

        ctk.CTkLabel(frame_sem, text="Semana:", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=5
        )

        self.combo_semana = ctk.CTkOptionMenu(
            frame_sem,
            values=[f"Semana {s['semana']} - {s['fecha_semana']}" for s in self.semanas],
            command=self._al_cambiar_semana,
        )
        self.combo_semana.pack(side="left", padx=5)

        self.frame_lista = ctk.CTkScrollableFrame(self)
        self.frame_lista.pack(fill="both", expand=True, padx=20, pady=10)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)

        btn_guardar = ctk.CTkButton(
            btn_frame,
            text="💾 Guardar y Regenerar Excel",
            font=ctk.CTkFont(weight="bold"),
            command=self._guardar_cambios,
        )
        btn_guardar.pack(side="right", padx=5)

        if self.asignaciones:
            self._al_cambiar_semana(self.combo_semana.get())
        else:
            ctk.CTkLabel(self.frame_lista, text="No hay asignaciones para este mes.").pack(pady=20)

    def _guardar_estado_semana_actual(self):
        if self.semana_activa is None or not self.comboboxes:
            return

        sem_idx = self.semana_activa
        asigs_semana = self.asignaciones.setdefault(sem_idx, {})

        for rol, cantidad in self.reglas.puestos_requeridos.items():
            if rol in ("limpieza", "hospitalidad"):
                continue

            nuevos_nombres = []
            for i in range(cantidad):
                cb = self.comboboxes.get((sem_idx, rol, i))
                if cb:
                    val = cb.get()
                    if val != "—":
                        nuevos_nombres.append(val)

            asigs_semana[rol] = nuevos_nombres

    def _al_cambiar_semana(self, sel: str):
        self._guardar_estado_semana_actual()

        for widget in self.frame_lista.winfo_children():
            widget.destroy()

        self.comboboxes.clear()

        if not self.asignaciones:
            return

        sem_idx = int(sel.split(" ")[1])
        self.semana_activa = sem_idx
        asigs_semana = self.asignaciones.get(sem_idx, {})

        for rol, cantidad in self.reglas.puestos_requeridos.items():
            if rol in ("limpieza", "hospitalidad"):
                continue

            rol_etiqueta = ETIQUETAS_PUESTO.get(rol, rol)
            nombres_actuales = asigs_semana.get(rol, [])

            f_row = ctk.CTkFrame(self.frame_lista)
            f_row.pack(fill="x", pady=4, padx=5)

            lbl_r = ctk.CTkLabel(
                f_row, text=rol_etiqueta, width=150, anchor="w", font=ctk.CTkFont(weight="bold")
            )
            lbl_r.pack(side="left", padx=10, pady=5)

            for i in range(cantidad):
                nombre_actual = nombres_actuales[i] if i < len(nombres_actuales) else "—"
                cb = ctk.CTkComboBox(f_row, values=self.candidatos_por_rol[rol], width=200)
                if nombre_actual in self.candidatos_por_rol[rol]:
                    cb.set(nombre_actual)
                else:
                    cb.set("—")
                cb.pack(side="left", padx=5, pady=5)

                self.comboboxes[(sem_idx, rol, i)] = cb

    def _guardar_cambios(self):
        self._guardar_estado_semana_actual()

        # Guardar en base de datos
        self.repo.guardar_asignaciones_mes(self.anio, self.mes, self.asignaciones)

        # Regenerar Excel
        ruta_salida = self.parent_app.ultimo_excel or (
            self.parent_app.carpeta_salida
            / f"programa_{MESES[self.mes - 1].lower()}_{self.anio}.xlsx"
        )

        try:
            exportar_programa_excel(
                mes_asignaciones=self.asignaciones,
                anio=self.anio,
                mes=self.mes,
                grupo_inicio_limpieza=self.grupo_limpieza,
                ruta_salida=str(ruta_salida),
                reglas=self.reglas,
            )
            self.parent_app.ultimo_excel = ruta_salida

            huecos = MotorAsignacion(
                hermanos=self.hermanos, reglas=self.reglas
            ).listar_puestos_incompletos(self.asignaciones)
            self.parent_app._mostrar_resumen(
                self.asignaciones, self.semanas, MESES[self.mes - 1], self.anio, huecos
            )

            self.parent_app.lbl_estado.configure(
                text="✅ Cambios manuales guardados y Excel regenerado exitosamente.",
                text_color="#28A745",
            )
            self.destroy()
        except Exception as e:
            from configuracion import logger

            logger.exception("Error al regenerar excel tras edición: %s", e)
            self.parent_app.lbl_estado.configure(
                text=f"❌ Error al guardar y exportar: {e}", text_color="#DC3545"
            )
            self.destroy()


class AppAsignaciones(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Generador de Asignaciones Mensuales")
        self.geometry("820x700")
        self.minsize(780, 640)

        # Repositorio centralizado y carpeta de salida
        self.repo = Repositorio()
        self.carpeta_salida = BASE_DIR / "salida"
        self.carpeta_salida.mkdir(parents=True, exist_ok=True)

        self.ultimo_excel = None

        self._crear_interfaz()
        self._actualizar_info_semanas()
        self.actualizar_conteo_ausencias()

    def _crear_interfaz(self):
        # 1. Cabecera
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=25, pady=(20, 10))

        lbl_tit = ctk.CTkLabel(
            frame_header,
            text="Generador de Asignaciones",
            font=ctk.CTkFont(family="Aptos", size=22, weight="bold"),
        )
        lbl_tit.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            frame_header,
            text="Distribución equitativa, gestión de ausencias y exportación A4 para impresión.",
            font=ctk.CTkFont(family="Aptos", size=13),
            text_color="gray",
        )
        lbl_sub.pack(anchor="w")

        # 2. Panel de Configuración
        frame_config = ctk.CTkFrame(self, corner_radius=12)
        frame_config.pack(fill="x", padx=25, pady=10)

        hoy = datetime.date.today()
        mes_defecto = hoy.month + 1 if hoy.month < 12 else 1
        anio_defecto = hoy.year if hoy.month < 12 else hoy.year + 1

        # Fila 1: Año y Mes
        lbl_anio = ctk.CTkLabel(frame_config, text="Año:", font=ctk.CTkFont(weight="bold"))
        lbl_anio.grid(row=0, column=0, padx=(20, 10), pady=12, sticky="w")

        anios_disponibles = [str(a) for a in range(hoy.year - 1, hoy.year + 4)]
        self.combo_anio = ctk.CTkOptionMenu(
            frame_config,
            values=anios_disponibles,
            command=lambda _: self._al_cambiar_fecha(),
            width=100,
        )
        self.combo_anio.set(str(anio_defecto))
        self.combo_anio.grid(row=0, column=1, padx=5, pady=12, sticky="w")

        lbl_mes = ctk.CTkLabel(frame_config, text="Mes:", font=ctk.CTkFont(weight="bold"))
        lbl_mes.grid(row=0, column=2, padx=(15, 10), pady=12, sticky="w")

        self.combo_mes = ctk.CTkOptionMenu(
            frame_config,
            values=MESES,
            command=lambda _: self._al_cambiar_fecha(),
            width=130,
        )
        self.combo_mes.set(MESES[mes_defecto - 1])
        self.combo_mes.grid(row=0, column=3, padx=5, pady=12, sticky="w")

        self.lbl_semanas_detectadas = ctk.CTkLabel(
            frame_config,
            text="",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#3B8ED0",
        )
        self.lbl_semanas_detectadas.grid(row=0, column=4, padx=15, pady=12, sticky="w")

        lbl_grupo = ctk.CTkLabel(
            frame_config, text="Limpieza inicial:", font=ctk.CTkFont(weight="bold")
        )
        lbl_grupo.grid(row=1, column=0, padx=(20, 10), pady=(0, 15), sticky="w")
        siguiente_sugerido = self._grupo_sugerido_para_mes(anio_defecto, mes_defecto)
        self.combo_grupo = ctk.CTkOptionMenu(
            frame_config,
            values=[f"Grupo # {i}" for i in range(1, _reglas.num_grupos_limpieza + 1)],
            width=130,
        )
        self.combo_grupo.set(f"Grupo # {siguiente_sugerido}")
        self.combo_grupo.grid(row=1, column=1, columnspan=2, padx=5, pady=(0, 15), sticky="w")

        self.btn_ausencias = ctk.CTkButton(
            frame_config,
            text="🚫 Ausencias del Mes (0)",
            fg_color="#D97706",
            hover_color="#B45309",
            command=self._abrir_ventana_ausencias,
            width=170,
        )
        self.btn_ausencias.grid(row=1, column=3, columnspan=2, padx=10, pady=(0, 15), sticky="w")

        # Fila 3: Carpeta de Salida
        lbl_salida = ctk.CTkLabel(frame_config, text="Guardar en:", font=ctk.CTkFont(weight="bold"))
        lbl_salida.grid(row=2, column=0, padx=(20, 10), pady=(0, 15), sticky="w")

        self.lbl_ruta_salida = ctk.CTkLabel(
            frame_config,
            text=str(self.carpeta_salida),
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=250,
            justify="left",
        )
        self.lbl_ruta_salida.grid(row=2, column=1, columnspan=2, padx=5, pady=(0, 15), sticky="w")

        self.btn_cambiar_salida = ctk.CTkButton(
            frame_config,
            text="📂 Cambiar destino",
            command=self._cambiar_carpeta_salida,
            width=170,
            fg_color="#2B2B2B",
            hover_color="#333333",
            border_width=1,
            border_color="gray",
        )
        self.btn_cambiar_salida.grid(
            row=2, column=3, columnspan=2, padx=10, pady=(0, 15), sticky="w"
        )

        # 3. Botón de Acción Principal
        self.btn_generar = ctk.CTkButton(
            self,
            text="✨ Generar Programa Completo",
            font=ctk.CTkFont(family="Aptos", size=14, weight="bold"),
            height=44,
            command=self._ejecutar_generacion,
        )
        self.btn_generar.pack(fill="x", padx=25, pady=10)

        # 4. Estado / Notificación
        self.lbl_estado = ctk.CTkLabel(
            self,
            text="Listo para generar asignaciones.",
            font=ctk.CTkFont(size=12),
            wraplength=740,
            justify="left",
        )
        self.lbl_estado.pack(padx=25, pady=(0, 10))

        # 5. Panel de Acciones Rápidas
        self.frame_acciones = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_acciones.pack(fill="x", padx=25, pady=5)

        self.btn_abrir_excel = ctk.CTkButton(
            self.frame_acciones,
            text="📊 Abrir Archivo Excel",
            state="disabled",
            fg_color="#107C41",
            hover_color="#0B5C30",
            command=self._abrir_excel,
        )
        self.btn_abrir_excel.pack(side="left", expand=True, fill="x", padx=(0, 2))

        self.btn_editar_asig = ctk.CTkButton(
            self.frame_acciones,
            text="📝 Editar Programa",
            state="disabled",
            fg_color="#D4AC0D",
            hover_color="#B7950B",
            command=self._abrir_ventana_edicion,
        )
        self.btn_editar_asig.pack(side="left", expand=True, fill="x", padx=2)

        self.btn_abrir_carpeta = ctk.CTkButton(
            self.frame_acciones,
            text="📁 Abrir Carpeta",
            state="disabled",
            fg_color="#5A6268",
            hover_color="#43494E",
            command=self._abrir_carpeta,
        )
        self.btn_abrir_carpeta.pack(side="left", expand=True, fill="x", padx=2)

        self.btn_recordatorios = ctk.CTkButton(
            self.frame_acciones,
            text="🔔 Recordatorios",
            fg_color="#25D366",
            hover_color="#128C7E",
            command=self._abrir_ventana_recordatorios,
        )
        self.btn_recordatorios.pack(side="left", expand=True, fill="x", padx=(2, 0))

        # 6. Vista previa de resultados
        lbl_preview = ctk.CTkLabel(
            self,
            text="Vista Previa Rápida:",
            font=ctk.CTkFont(weight="bold"),
        )
        lbl_preview.pack(anchor="w", padx=25, pady=(15, 5))

        self.txt_preview = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_preview.pack(fill="both", expand=True, padx=25, pady=(0, 20))

    def _cambiar_carpeta_salida(self):
        from customtkinter import filedialog

        carpeta = filedialog.askdirectory(
            initialdir=str(self.carpeta_salida), title="Seleccionar carpeta para guardar el Excel"
        )
        if carpeta:
            self.carpeta_salida = Path(carpeta)
            self.lbl_ruta_salida.configure(text=str(self.carpeta_salida))

    def _al_cambiar_fecha(self):
        self._actualizar_info_semanas()
        self._actualizar_grupo_sugerido()
        self.actualizar_conteo_ausencias()

    def _actualizar_info_semanas(self):
        anio = int(self.combo_anio.get())
        mes_idx = MESES.index(self.combo_mes.get()) + 1
        semanas = calcular_semanas_mes(anio, mes_idx)
        self.lbl_semanas_detectadas.configure(text=f"• {len(semanas)} semanas (martes a domingo)")

    def _grupo_sugerido_para_mes(self, anio: int, mes: int) -> int:
        estado = self.repo.leer_estado()
        if not estado:
            return 1

        if estado.ultimo_anio == anio and estado.ultimo_mes == mes:
            ultimo = estado.ultimo_grupo_limpieza
            num_semanas = len(calcular_semanas_mes(anio, mes))
            return ((ultimo - 1 - (num_semanas - 1)) % _reglas.num_grupos_limpieza) + 1

        return estado.siguiente_grupo_limpieza

    def _actualizar_grupo_sugerido(self):
        anio = int(self.combo_anio.get())
        mes_idx = MESES.index(self.combo_mes.get()) + 1
        grupo = self._grupo_sugerido_para_mes(anio, mes_idx)
        self.combo_grupo.set(f"Grupo # {grupo}")

    def actualizar_conteo_ausencias(self):
        anio = int(self.combo_anio.get())
        mes_idx = MESES.index(self.combo_mes.get()) + 1
        datos_mes = self.repo.leer_ausencias_mes(anio, mes_idx)
        conteo = len(datos_mes)
        self.btn_ausencias.configure(text=f"🚫 Ausencias del Mes ({conteo})")

    def _obtener_mapa_ausencias_motor(self, anio: int, mes_idx: int) -> dict[int, list[str]]:
        """Convierte {nombre: [semanas]} a {semana_int: [lista_nombres]} para el motor."""
        mes_data = self.repo.leer_ausencias_mes(anio, mes_idx)
        mapa_semanas: dict[int, list[str]] = {}
        for nombre, sems in mes_data.items():
            for s in sems:
                mapa_semanas.setdefault(int(s), []).append(nombre)
        return mapa_semanas

    def _abrir_ventana_ausencias(self):
        try:
            hermanos = self.repo.cargar_hermanos()
            nombres = [h.nombre for h in hermanos]
            anio = int(self.combo_anio.get())
            mes_idx = MESES.index(self.combo_mes.get()) + 1
            semanas = calcular_semanas_mes(anio, mes_idx)

            VentanaAusencias(
                parent=self,
                repo=self.repo,
                hermanos_nombres=nombres,
                anio=anio,
                mes_idx=mes_idx,
                num_semanas=len(semanas),
            )
        except DatosInvalidosError as e:
            logger.error("Error abriendo ventana ausencias: %s", e)
            self.lbl_estado.configure(text=f"❌ {e}", text_color="#DC3545")
        except Exception as e:
            logger.exception("Error inesperado al abrir ausencias: %s", e)
            self.lbl_estado.configure(
                text=f"❌ Error al cargar hermanos: {e}", text_color="#DC3545"
            )

    def _abrir_ventana_recordatorios(self):
        anio = int(self.combo_anio.get())
        mes_idx = MESES.index(self.combo_mes.get()) + 1
        semanas = calcular_semanas_mes(anio, mes_idx)
        asignaciones = self.repo.leer_asignaciones_mes(anio, mes_idx)

        try:
            VentanaRecordatorios(
                parent=self,
                repo=self.repo,
                anio=anio,
                mes=mes_idx,
                semanas=semanas,
                asignaciones=asignaciones,
            )
        except Exception as e:
            logger.exception("Error al abrir ventana de recordatorios: %s", e)
            self.lbl_estado.configure(text=f"❌ Error: {e}", text_color="#DC3545")

    def _abrir_ventana_edicion(self):
        anio = int(self.combo_anio.get())
        mes_idx = MESES.index(self.combo_mes.get()) + 1
        semanas = calcular_semanas_mes(anio, mes_idx)
        asignaciones = self.repo.leer_asignaciones_mes(anio, mes_idx)
        grupo = int(self.combo_grupo.get().replace("Grupo # ", ""))

        if not asignaciones:
            self.lbl_estado.configure(
                text="❌ No hay asignaciones guardadas para editar.", text_color="#DC3545"
            )
            return

        try:
            VentanaEdicionAsignaciones(
                parent=self,
                repo=self.repo,
                anio=anio,
                mes=mes_idx,
                semanas=semanas,
                asignaciones=asignaciones,
                grupo_limpieza=grupo,
                reglas=_reglas,
            )
        except Exception as e:
            logger.exception("Error al abrir ventana de edición: %s", e)
            self.lbl_estado.configure(text=f"❌ Error: {e}", text_color="#DC3545")

    def _ejecutar_generacion(self):
        try:
            self.lbl_estado.configure(text="Generando Excel...", text_color="gray")
            self.update_idletasks()

            hermanos = self.repo.cargar_hermanos()

            anio = int(self.combo_anio.get())
            mes_str = self.combo_mes.get()
            mes_idx = MESES.index(mes_str) + 1

            grupo_seleccionado = int(self.combo_grupo.get().replace("Grupo # ", ""))
            semanas = calcular_semanas_mes(anio, mes_idx)

            # Leer ausencias de este mes formateadas para el motor
            ausencias_motor = self._obtener_mapa_ausencias_motor(anio, mes_idx)

            # Generar motor aplicando ausencias
            motor = MotorAsignacion(hermanos=hermanos)
            asignaciones = motor.generar_mes(num_semanas=len(semanas), ausencias=ausencias_motor)

            # Guardar en base de datos para recordatorios
            self.repo.guardar_asignaciones_mes(anio, mes_idx, asignaciones)

            nombre_sugerido = f"programa_{mes_str.lower()}_{anio}"
            ruta_xlsx = self.carpeta_salida / f"{nombre_sugerido}.xlsx"

            exportar_programa_excel(
                mes_asignaciones=asignaciones,
                anio=anio,
                mes=mes_idx,
                grupo_inicio_limpieza=grupo_seleccionado,
                ruta_salida=str(ruta_xlsx),
                reglas=_reglas,
            )

            # Actualizar estado para el mes siguiente
            ultimo_grupo = (
                (grupo_seleccionado - 1 + (len(semanas) - 1)) % _reglas.num_grupos_limpieza
            ) + 1
            siguiente_grupo = (ultimo_grupo % _reglas.num_grupos_limpieza) + 1

            nuevo_estado = EstadoMes(
                ultimo_anio=anio,
                ultimo_mes=mes_idx,
                ultimo_grupo_limpieza=ultimo_grupo,
                siguiente_grupo_limpieza=siguiente_grupo,
            )
            self.repo.guardar_estado(nuevo_estado)

            self.ultimo_excel = ruta_xlsx

            self.btn_abrir_excel.configure(state="normal")
            self.btn_abrir_carpeta.configure(state="normal")
            self.btn_editar_asig.configure(state="normal")

            huecos = motor.listar_puestos_incompletos(asignaciones)
            self.combo_grupo.set(f"Grupo # {grupo_seleccionado}")

            if huecos:
                resumen_huecos = "; ".join(
                    f"Sem {h['semana']} {ETIQUETAS_PUESTO.get(h['puesto'], h['puesto'])} "
                    f"({h['asignados']}/{h['requeridos']})"
                    for h in huecos
                )
                self.lbl_estado.configure(
                    text=f"⚠️ Programa exportado con puestos incompletos: {resumen_huecos}",
                    text_color="#DC3545",
                )
            else:
                self.lbl_estado.configure(
                    text="✅ ¡Programa generado respetando ausencias! "
                    "Presiona 'Abrir Archivo Excel'.",
                    text_color="#28A745",
                )

            self._mostrar_resumen(asignaciones, semanas, mes_str, anio, huecos)

        except DatosInvalidosError as e:
            logger.error("Error validando datos en generación: %s", e)
            self.lbl_estado.configure(text=f"❌ {e}", text_color="#DC3545")
        except Exception as e:
            logger.exception("Error general en generación: %s", e)
            self.lbl_estado.configure(text=f"❌ Error: {e}", text_color="#DC3545")

    def _mostrar_resumen(
        self,
        asignaciones: Dict[int, Dict[str, List[str]]],
        semanas: List[dict],
        mes_str: str,
        anio: int,
        huecos: Optional[List[dict]] = None,
    ) -> None:
        self.txt_preview.delete("1.0", "end")
        lineas = [f"=== RESUMEN ASIGNACIONES - {mes_str.upper()} {anio} ===", ""]

        if huecos:
            lineas.append("PUESTOS INCOMPLETOS:")
            for h in huecos:
                etiqueta = ETIQUETAS_PUESTO.get(h["puesto"], h["puesto"])
                lineas.append(
                    f"  • Semana {h['semana']}: {etiqueta} ({h['asignados']} de {h['requeridos']})"
                )
            lineas.append("")

        for s in semanas:
            num = s["semana"]
            asig = asignaciones[num]
            lineas.append(f"--- SEMANA {num} ({s['fecha_semana'].replace(chr(10), ' ')}) ---")
            lineas.append(f"  Presidente      : {', '.join(asig.get('presidente', []))}")
            lineas.append(f"  Lector Atalaya  : {', '.join(asig.get('lector_domingo', []))}")
            lineas.append(f"  Lector E.B.     : {', '.join(asig.get('lector_martes', []))}")
            lineas.append(f"  Plataforma      : {', '.join(asig.get('plataforma', []))}")
            lineas.append(f"  Micrófonos      : {' / '.join(asig.get('microfonos', []))}")
            lineas.append(f"  Acomodadores    : {' / '.join(asig.get('acomodador', []))}")
            cabina_txt = (
                f"{', '.join(asig.get('audio', []))} (Aud) | "
                f"{', '.join(asig.get('video', []))} (Vid)"
            )
            lineas.append(f"  Cabina (A/V)    : {cabina_txt}")
            lineas.append("")

        self.txt_preview.insert("1.0", "\n".join(lineas))

    def _abrir_excel(self):
        if self.ultimo_excel and self.ultimo_excel.exists():
            os.startfile(str(self.ultimo_excel))

    def _abrir_carpeta(self):
        os.startfile(str(self.carpeta_salida))


if __name__ == "__main__":
    app = AppAsignaciones()
    app.mainloop()
