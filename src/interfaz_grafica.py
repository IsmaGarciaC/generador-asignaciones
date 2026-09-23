import datetime
import json
import os
from pathlib import Path
import sys
import customtkinter as ctk

# Asegurar importaciones locales
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "src"))

from cargador_datos import DatosInvalidosError, cargar_hermanos
from motor_asignacion import generar_mes, listar_puestos_incompletos
from exportador_excel import (
    calcular_semanas_mes,
    exportar_programa_excel,
    grupo_sugerido_para_mes,
)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

ETIQUETAS_PUESTO = {
    "presidente": "Presidente",
    "lector_domingo": "Lector de La Atalaya",
    "audio": "Audio",
    "video": "Video",
    "plataforma": "Plataforma",
    "lector_martes": "Lector Estudio Bíblico",
    "microfonos": "Micrófonos",
    "acomodador": "Acomodadores",
}


class VentanaAusencias(ctk.CTkToplevel):
    """Ventana emergente para registrar hermanos que no estarán disponibles en semanas específicas."""
    def __init__(self, parent, hermanos_nombres: list[str], anio: int, mes_idx: int, num_semanas: int, ruta_ausencias: Path):
        super().__init__(parent)
        self.title("Gestionar Ausencias")
        self.geometry("540x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.parent_app = parent
        self.hermanos_nombres = sorted(hermanos_nombres)
        self.anio = anio
        self.mes_idx = mes_idx
        self.num_semanas = num_semanas
        self.ruta_ausencias = ruta_ausencias
        self.clave_mes = f"{anio}-{mes_idx:02d}"

        self.ausencias_mes = self._cargar_ausencias()
        self.checkboxes_semanas = []

        self._construir_ui()

    def _cargar_ausencias(self) -> dict[str, list[int]]:
        if self.ruta_ausencias.exists():
            try:
                with open(self.ruta_ausencias, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    return datos.get(self.clave_mes, {})
            except Exception:
                return {}
        return {}

    def _guardar_en_disco(self):
        datos = {}
        if self.ruta_ausencias.exists():
            try:
                with open(self.ruta_ausencias, "r", encoding="utf-8") as f:
                    datos = json.load(f)
            except Exception:
                datos = {}

        if self.ausencias_mes:
            datos[self.clave_mes] = self.ausencias_mes
        elif self.clave_mes in datos:
            del datos[self.clave_mes]

        self.ruta_ausencias.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ruta_ausencias, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)

    def _construir_ui(self):
        lbl_tit = ctk.CTkLabel(
            self,
            text=f"Ausencias para {MESES[self.mes_idx - 1]} {self.anio}",
            font=ctk.CTkFont(family="Aptos", size=16, weight="bold")
        )
        lbl_tit.pack(pady=(15, 5))

        lbl_desc = ctk.CTkLabel(
            self,
            text="Selecciona el hermano y marca las semanas en que NO estará disponible.",
            font=ctk.CTkFont(size=12),
            text_color="gray"
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
            command=self._al_cambiar_hermano
        )
        self.combo_hermano.pack(side="left")
        if self.hermanos_nombres:
            self.combo_hermano.set(self.hermanos_nombres[0])

        # Checkboxes de semanas
        frame_sems = ctk.CTkFrame(self)
        frame_sems.pack(fill="x", padx=20, pady=12)

        lbl_sem_tit = ctk.CTkLabel(frame_sems, text="Semanas ausente:", font=ctk.CTkFont(weight="bold"))
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
            command=self._guardar_ausencia_hermano
        )
        btn_asignar.pack(side="left", expand=True, fill="x", padx=(0, 5))

        btn_quitar = ctk.CTkButton(
            frame_btn_h,
            text="Quitar Ausencias",
            fg_color="#A93226",
            hover_color="#7B241C",
            command=self._quitar_ausencia_hermano
        )
        btn_quitar.pack(side="left", padx=(5, 0))

        # Lista de ausentes registrados
        lbl_list = ctk.CTkLabel(self, text="Ausencias Registradas en este Mes:", font=ctk.CTkFont(weight="bold"))
        lbl_list.pack(anchor="w", padx=20, pady=(12, 4))

        self.txt_lista = ctk.CTkTextbox(self, height=120, font=ctk.CTkFont(family="Consolas", size=11))
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


class AppAsignaciones(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Generador de Asignaciones Mensuales")
        self.geometry("820x700")
        self.minsize(780, 640)

        # Rutas de datos
        self.ruta_datos = BASE_DIR / "data" / "hermanos.json"
        self.ruta_estado = BASE_DIR / "data" / "estado.json"
        self.ruta_ausencias = BASE_DIR / "data" / "ausencias.json"
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
            font=ctk.CTkFont(family="Aptos", size=22, weight="bold")
        )
        lbl_tit.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            frame_header,
            text="Distribución equitativa, gestión de ausencias y exportación A4 para ONLYOFFICE.",
            font=ctk.CTkFont(family="Aptos", size=13),
            text_color="gray"
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
            width=100
        )
        self.combo_anio.set(str(anio_defecto))
        self.combo_anio.grid(row=0, column=1, padx=5, pady=12, sticky="w")

        lbl_mes = ctk.CTkLabel(frame_config, text="Mes:", font=ctk.CTkFont(weight="bold"))
        lbl_mes.grid(row=0, column=2, padx=(15, 10), pady=12, sticky="w")

        self.combo_mes = ctk.CTkOptionMenu(
            frame_config,
            values=MESES,
            command=lambda _: self._al_cambiar_fecha(),
            width=130
        )
        self.combo_mes.set(MESES[mes_defecto - 1])
        self.combo_mes.grid(row=0, column=3, padx=5, pady=12, sticky="w")

        self.lbl_semanas_detectadas = ctk.CTkLabel(
            frame_config,
            text="",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#3B8ED0"
        )
        self.lbl_semanas_detectadas.grid(row=0, column=4, padx=15, pady=12, sticky="w")

        # Fila 2: Grupo de Limpieza Inicial y Botón de Ausencias
        lbl_grupo = ctk.CTkLabel(frame_config, text="Limpieza inicial:", font=ctk.CTkFont(weight="bold"))
        lbl_grupo.grid(row=1, column=0, padx=(20, 10), pady=(0, 15), sticky="w")

        siguiente_sugerido = grupo_sugerido_para_mes(
            anio_defecto, mes_defecto, str(self.ruta_estado)
        )
        self.combo_grupo = ctk.CTkOptionMenu(
            frame_config,
            values=["Grupo # 1", "Grupo # 2", "Grupo # 3", "Grupo # 4"],
            width=130
        )
        self.combo_grupo.set(f"Grupo # {siguiente_sugerido}")
        self.combo_grupo.grid(row=1, column=1, columnspan=2, padx=5, pady=(0, 15), sticky="w")

        self.btn_ausencias = ctk.CTkButton(
            frame_config,
            text="🚫 Ausencias del Mes (0)",
            fg_color="#D97706",
            hover_color="#B45309",
            command=self._abrir_ventana_ausencias,
            width=170
        )
        self.btn_ausencias.grid(row=1, column=3, columnspan=2, padx=10, pady=(0, 15), sticky="w")

        # 3. Botón de Acción Principal
        self.btn_generar = ctk.CTkButton(
            self,
            text="✨ Generar Programa Completo",
            font=ctk.CTkFont(family="Aptos", size=14, weight="bold"),
            height=44,
            command=self._ejecutar_generacion
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
            text="📊 Abrir en ONLYOFFICE",
            state="disabled",
            fg_color="#107C41",
            hover_color="#0B5C30",
            command=self._abrir_excel
        )
        self.btn_abrir_excel.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.btn_abrir_carpeta = ctk.CTkButton(
            self.frame_acciones,
            text="📁 Abrir Carpeta",
            state="disabled",
            fg_color="#5A6268",
            hover_color="#43494E",
            command=self._abrir_carpeta
        )
        self.btn_abrir_carpeta.pack(side="left", expand=True, fill="x", padx=5)

        # 6. Vista previa de resultados
        lbl_preview = ctk.CTkLabel(
            self,
            text="Vista Previa Rápida:",
            font=ctk.CTkFont(weight="bold")
        )
        lbl_preview.pack(anchor="w", padx=25, pady=(15, 5))

        self.txt_preview = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_preview.pack(fill="both", expand=True, padx=25, pady=(0, 20))

    def _al_cambiar_fecha(self):
        self._actualizar_info_semanas()
        self._actualizar_grupo_sugerido()
        self.actualizar_conteo_ausencias()

    def _actualizar_info_semanas(self):
        anio = int(self.combo_anio.get())
        mes_idx = MESES.index(self.combo_mes.get()) + 1
        semanas = calcular_semanas_mes(anio, mes_idx)
        self.lbl_semanas_detectadas.configure(text=f"• {len(semanas)} semanas (martes a domingo)")

    def _actualizar_grupo_sugerido(self):
        anio = int(self.combo_anio.get())
        mes_idx = MESES.index(self.combo_mes.get()) + 1
        grupo = grupo_sugerido_para_mes(anio, mes_idx, str(self.ruta_estado))
        self.combo_grupo.set(f"Grupo # {grupo}")

    def actualizar_conteo_ausencias(self):
        anio = int(self.combo_anio.get())
        mes_idx = MESES.index(self.combo_mes.get()) + 1
        clave = f"{anio}-{mes_idx:02d}"

        conteo = 0
        if self.ruta_ausencias.exists():
            try:
                with open(self.ruta_ausencias, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    conteo = len(datos.get(clave, {}))
            except Exception:
                conteo = 0

        self.btn_ausencias.configure(text=f"🚫 Ausencias del Mes ({conteo})")

    def _obtener_mapa_ausencias_motor(self, anio: int, mes_idx: int) -> dict[int, list[str]]:
        """Convierte {nombre: [semanas]} a {semana_int: [lista_nombres]} para el motor."""
        clave = f"{anio}-{mes_idx:02d}"
        mapa_semanas = {}

        if self.ruta_ausencias.exists():
            try:
                with open(self.ruta_ausencias, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    mes_data = datos.get(clave, {})
                    for nombre, sems in mes_data.items():
                        for s in sems:
                            mapa_semanas.setdefault(int(s), []).append(nombre)
            except Exception:
                pass

        return mapa_semanas

    def _abrir_ventana_ausencias(self):
        try:
            hermanos = cargar_hermanos(str(self.ruta_datos))
            nombres = [h["nombre"] for h in hermanos]
            anio = int(self.combo_anio.get())
            mes_idx = MESES.index(self.combo_mes.get()) + 1
            semanas = calcular_semanas_mes(anio, mes_idx)

            VentanaAusencias(
                parent=self,
                hermanos_nombres=nombres,
                anio=anio,
                mes_idx=mes_idx,
                num_semanas=len(semanas),
                ruta_ausencias=self.ruta_ausencias
            )
        except DatosInvalidosError as e:
            self.lbl_estado.configure(text=f"❌ {e}", text_color="#DC3545")
        except Exception as e:
            self.lbl_estado.configure(text=f"❌ Error al cargar hermanos: {e}", text_color="#DC3545")

    def _ejecutar_generacion(self):
        try:
            self.lbl_estado.configure(text="Generando Excel...", text_color="gray")
            self.update_idletasks()

            hermanos = cargar_hermanos(str(self.ruta_datos))

            anio = int(self.combo_anio.get())
            mes_str = self.combo_mes.get()
            mes_idx = MESES.index(mes_str) + 1

            grupo_seleccionado = int(self.combo_grupo.get().replace("Grupo # ", ""))
            semanas = calcular_semanas_mes(anio, mes_idx)

            # Leer ausencias de este mes formateadas para el motor
            ausencias_motor = self._obtener_mapa_ausencias_motor(anio, mes_idx)

            # Generar motor aplicando ausencias
            asignaciones = generar_mes(hermanos, num_semanas=len(semanas), ausencias=ausencias_motor)

            nombre_sugerido = f"programa_{mes_str.lower()}_{anio}"
            ruta_xlsx = self.carpeta_salida / f"{nombre_sugerido}.xlsx"

            exportar_programa_excel(
                mes_asignaciones=asignaciones,
                anio=anio,
                mes=mes_idx,
                grupo_inicio_limpieza=grupo_seleccionado,
                ruta_salida=str(ruta_xlsx),
                ruta_estado=str(self.ruta_estado),
            )

            self.ultimo_excel = ruta_xlsx

            self.btn_abrir_excel.configure(state="normal")
            self.btn_abrir_carpeta.configure(state="normal")

            huecos = listar_puestos_incompletos(asignaciones)
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
                    text="✅ ¡Programa generado respetando ausencias! Presiona 'Abrir en ONLYOFFICE'.",
                    text_color="#28A745",
                )

            self._mostrar_resumen(asignaciones, semanas, mes_str, anio, huecos)

        except DatosInvalidosError as e:
            self.lbl_estado.configure(text=f"❌ {e}", text_color="#DC3545")
        except Exception as e:
            self.lbl_estado.configure(text=f"❌ Error: {e}", text_color="#DC3545")

    def _mostrar_resumen(self, asignaciones, semanas, mes_str, anio, huecos=None):
        self.txt_preview.delete("1.0", "end")
        lineas = [f"=== RESUMEN ASIGNACIONES - {mes_str.upper()} {anio} ===", ""]

        if huecos:
            lineas.append("PUESTOS INCOMPLETOS:")
            for h in huecos:
                etiqueta = ETIQUETAS_PUESTO.get(h["puesto"], h["puesto"])
                lineas.append(
                    f"  • Semana {h['semana']}: {etiqueta} "
                    f"({h['asignados']} de {h['requeridos']})"
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
            lineas.append(f"  Cabina (A/V)    : {', '.join(asig.get('audio', []))} (Aud) | {', '.join(asig.get('video', []))} (Vid)")
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