import datetime
import os
from pathlib import Path
import sys
import customtkinter as ctk

# Asegurar importaciones locales
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "src"))

from cargador_datos import cargar_hermanos
from motor_asignacion import generar_mes
from exportador_excel import (
    calcular_semanas_mes,
    exportar_programa_excel,
    obtener_siguiente_grupo,
)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


class AppAsignaciones(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Generador de Asignaciones Mensuales")
        self.geometry("800x680")
        self.minsize(760, 620)

        # Rutas de datos
        self.ruta_datos = BASE_DIR / "data" / "hermanos.json"
        self.ruta_estado = BASE_DIR / "data" / "estado.json"
        self.carpeta_salida = BASE_DIR / "salida"
        self.carpeta_salida.mkdir(parents=True, exist_ok=True)

        self.ultimo_excel = None

        self._crear_interfaz()
        self._actualizar_info_semanas()

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
            text="Distribución equitativa y exportación optimizada para ONLYOFFICE.",
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

        lbl_anio = ctk.CTkLabel(frame_config, text="Año:", font=ctk.CTkFont(weight="bold"))
        lbl_anio.grid(row=0, column=0, padx=(20, 10), pady=15, sticky="w")

        anios_disponibles = [str(a) for a in range(hoy.year - 1, hoy.year + 4)]
        self.combo_anio = ctk.CTkOptionMenu(
            frame_config,
            values=anios_disponibles,
            command=lambda _: self._actualizar_info_semanas(),
            width=110
        )
        self.combo_anio.set(str(anio_defecto))
        self.combo_anio.grid(row=0, column=1, padx=10, pady=15, sticky="w")

        lbl_mes = ctk.CTkLabel(frame_config, text="Mes:", font=ctk.CTkFont(weight="bold"))
        lbl_mes.grid(row=0, column=2, padx=(20, 10), pady=15, sticky="w")

        self.combo_mes = ctk.CTkOptionMenu(
            frame_config,
            values=MESES,
            command=lambda _: self._actualizar_info_semanas(),
            width=140
        )
        self.combo_mes.set(MESES[mes_defecto - 1])
        self.combo_mes.grid(row=0, column=3, padx=10, pady=15, sticky="w")

        self.lbl_semanas_detectadas = ctk.CTkLabel(
            frame_config,
            text="",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#3B8ED0"
        )
        self.lbl_semanas_detectadas.grid(row=0, column=4, padx=15, pady=15, sticky="w")

        lbl_grupo = ctk.CTkLabel(frame_config, text="Limpieza inicial:", font=ctk.CTkFont(weight="bold"))
        lbl_grupo.grid(row=1, column=0, padx=(20, 10), pady=(0, 15), sticky="w")

        siguiente_sugerido = obtener_siguiente_grupo(str(self.ruta_estado))
        self.combo_grupo = ctk.CTkOptionMenu(
            frame_config,
            values=["Grupo # 1", "Grupo # 2", "Grupo # 3", "Grupo # 4"],
            width=140
        )
        self.combo_grupo.set(f"Grupo # {siguiente_sugerido}")
        self.combo_grupo.grid(row=1, column=1, columnspan=2, padx=10, pady=(0, 15), sticky="w")

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
            font=ctk.CTkFont(size=12)
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

    def _actualizar_info_semanas(self):
        anio = int(self.combo_anio.get())
        mes_idx = MESES.index(self.combo_mes.get()) + 1
        semanas = calcular_semanas_mes(anio, mes_idx)
        self.lbl_semanas_detectadas.configure(text=f"• {len(semanas)} semanas detectadas")

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

            asignaciones = generar_mes(hermanos, num_semanas=len(semanas))

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

            self.lbl_estado.configure(
                text="✅ ¡Programa generado! Presiona 'Abrir' y usa Win + Shift + S para enviar por WhatsApp.",
                text_color="#28A745"
            )

            siguiente = obtener_siguiente_grupo(str(self.ruta_estado))
            self.combo_grupo.set(f"Grupo # {siguiente}")

            self._mostrar_resumen(asignaciones, semanas, mes_str, anio)

        except Exception as e:
            self.lbl_estado.configure(text=f"❌ Error: {e}", text_color="#DC3545")

    def _mostrar_resumen(self, asignaciones, semanas, mes_str, anio):
        self.txt_preview.delete("1.0", "end")
        lineas = [f"=== RESUMEN ASIGNACIONES - {mes_str.upper()} {anio} ===", ""]

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