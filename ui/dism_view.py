import threading
import customtkinter as ctk
from tkinter import messagebox
from ui.theme import *
import core.dism_tool as dism

class DismManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Herramienta de Imagen y Componentes (DISM)")
        self.geometry("820x600")
        self.minsize(740, 500)
        self.configure(fg_color=COLOR_BG_DARK)

        self._build_ui()

    def _build_ui(self):
        # Cabecera
        header = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, corner_radius=0)
        header.pack(fill="x")

        lbl = ctk.CTkLabel(
            header, text="🛡️ Mantenimiento de Imagen de Windows (DISM)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        lbl.pack(side="left", padx=20, pady=15)

        # Controles
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=15, pady=10)

        self.btn_analyze = ctk.CTkButton(
            ctrl_frame, text="Analizar WinSxS",
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            command=self.start_analyze_thread
        )
        self.btn_analyze.pack(side="left", padx=5, expand=True, fill="x")

        self.btn_cleanup = ctk.CTkButton(
            ctrl_frame, text="Purgar Versiones Viejas",
            fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER,
            command=self.start_cleanup_thread
        )
        self.btn_cleanup.pack(side="left", padx=5, expand=True, fill="x")

        self.btn_restore = ctk.CTkButton(
            ctrl_frame, text="Reparar Imagen (RestoreHealth)",
            fg_color=COLOR_CARD, hover_color=COLOR_CARD_HOVER,
            command=self.start_restore_thread
        )
        self.btn_restore.pack(side="left", padx=5, expand=True, fill="x")

        # Consola de salida
        self.log_area = ctk.CTkTextbox(
            self, font=("Consolas", 11),
            text_color=COLOR_TEXT_PRIMARY, fg_color="#181818"
        )
        self.log_area.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        self.log_area.configure(state="disabled")

    def log(self, message):
        self.log_area.configure(state="normal")
        self.log_area.insert("end", message + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def set_buttons_state(self, state):
        self.btn_analyze.configure(state=state)
        self.btn_cleanup.configure(state=state)
        self.btn_restore.configure(state=state)

    def start_analyze_thread(self):
        self.set_buttons_state("disabled")
        threading.Thread(target=self._run_analyze, daemon=True).start()

    def _run_analyze(self):
        self.log("\n--- INICIANDO ANÁLISIS DEL COMPONENT STORE ---")
        code = dism.analyze_component_store(log_callback=self.log)
        self.log(f"[✓] Análisis DISM completado (Código: {code}).\n")
        self.set_buttons_state("normal")

    def start_cleanup_thread(self):
        msg = (
            "¿Deseas purgar el almacén de componentes (WinSxS)?\n\n"
            "Esto consolidará las actualizaciones y eliminará archivos obsoletos de Windows Update.\n"
            "Nota: No podrás desinstalar parches acumulativos previos."
        )
        if not messagebox.askyesno("Confirmar Limpieza WinSxS", msg):
            return

        self.set_buttons_state("disabled")
        threading.Thread(target=self._run_cleanup, daemon=True).start()

    def _run_cleanup(self):
        self.log("\n=== LIMPIANDO COMPONENT STORE (/StartComponentCleanup /ResetBase) ===")
        code = dism.cleanup_component_store(reset_base=True, log_callback=self.log)
        self.log(f"[✓] Limpieza WinSxS completada (Código: {code}).\n")
        self.set_buttons_state("normal")

    def start_restore_thread(self):
        if not messagebox.askyesno("Confirmar Reparación", "¿Ejecutar DISM /RestoreHealth para reparar archivos de sistema con origen oficial?"):
            return

        self.set_buttons_state("disabled")
        threading.Thread(target=self._run_restore, daemon=True).start()

    def _run_restore(self):
        self.log("\n=== REPARANDO IMAGEN DE SISTEMA (/RestoreHealth) ===")
        code = dism.restore_health_image(log_callback=self.log)
        self.log(f"[✓] Reparación completada (Código: {code}).\n")
        self.set_buttons_state("normal")