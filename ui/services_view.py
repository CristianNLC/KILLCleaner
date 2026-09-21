import threading
import customtkinter as ctk
from tkinter import messagebox
from ui.theme import *
from core.services_optimizer import TWEAKABLE_SERVICES, get_service_status, toggle_service

class ServicesOptimizerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Optimizador de Servicios Innecesarios de Windows")
        self.geometry("820x540")
        self.minsize(740, 460)
        self.configure(fg_color=COLOR_BG_DARK)

        self._build_ui()
        self._load_services()

    def _build_ui(self):
        # Cabecera
        header = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, corner_radius=0)
        header.pack(fill="x")

        lbl = ctk.CTkLabel(
            header, text="⚙️ Servicios en Segundo Plano y Telemetría",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        lbl.pack(side="left", padx=20, pady=15)

        btn_refresh = ctk.CTkButton(
            header, text="Actualizar", width=90,
            fg_color=COLOR_CARD, hover_color=COLOR_CARD_HOVER,
            command=self._load_services
        )
        btn_refresh.pack(side="right", padx=20, pady=15)

        # Panel scrollable de servicios
        self.scroll_list = ctk.CTkScrollableFrame(self, fg_color="#18191d", corner_radius=8)
        self.scroll_list.pack(fill="both", expand=True, padx=15, pady=15)

    def _load_services(self):
        for w in self.scroll_list.winfo_children():
            w.destroy()

        for s in TWEAKABLE_SERVICES:
            status = get_service_status(s["name"])
            is_disabled = (status["start_type"] == "Deshabilitado")

            row = ctk.CTkFrame(self.scroll_list, fg_color=COLOR_CARD, corner_radius=6)
            row.pack(fill="x", padx=5, pady=4)

            # Badge de Estado
            badge_color = COLOR_DANGER if is_disabled else COLOR_SUCCESS
            badge_text = "DESACTIVADO" if is_disabled else "ACTIVO"

            badge = ctk.CTkLabel(
                row, text=badge_text, width=95,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                text_color=badge_color
            )
            badge.pack(side="left", padx=(10, 5), pady=8)

            # Datos del servicio
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=5, pady=6)

            title_lbl = ctk.CTkLabel(
                info_frame, text=s["title"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                anchor="w"
            )
            title_lbl.pack(fill="x")

            desc_text = f"{s['desc']} (Inicio: {status['start_type']})"
            desc_lbl = ctk.CTkLabel(
                info_frame, text=desc_text,
                font=ctk.CTkFont(size=10),
                text_color=COLOR_TEXT_SECONDARY,
                anchor="w"
            )
            desc_lbl.pack(fill="x")

            # Botón conmutador
            btn_text = "Activar" if is_disabled else "Desactivar"
            btn_color = COLOR_SUCCESS if is_disabled else COLOR_DANGER
            btn_hover = COLOR_SUCCESS_HOVER if is_disabled else COLOR_DANGER_HOVER

            btn_toggle = ctk.CTkButton(
                row, text=btn_text, width=85, height=26,
                fg_color=btn_color, hover_color=btn_hover,
                font=ctk.CTkFont(size=11),
                command=lambda name=s["name"], dis=not is_disabled: self._handle_toggle(name, dis)
            )
            btn_toggle.pack(side="right", padx=15, pady=8)

    def _handle_toggle(self, service_name: str, disable: bool):
        ok, msg = toggle_service(service_name, disable)
        if not ok:
            messagebox.showerror("Aviso de Privilegios", f"No se pudo alterar el servicio:\n{msg}\n\nAsegúrate de ejecutar la app como Administrador.")
        self._load_services()