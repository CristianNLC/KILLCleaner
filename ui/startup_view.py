import customtkinter as ctk
from tkinter import messagebox
from ui.theme import *
from core.startup_manager import list_startup_entries, disable_startup_entry, enable_startup_entry

class StartupManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Gestor de Programas de Inicio de Windows")
        self.geometry("820x540")
        self.minsize(740, 440)
        self.configure(fg_color=COLOR_BG_DARK)

        self._build_ui()
        self._load_entries()

    def _build_ui(self):
        # Cabecera
        header = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, corner_radius=0)
        header.pack(fill="x")

        lbl = ctk.CTkLabel(
            header, text="🚀 Programas de Inicio del Sistema",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        lbl.pack(side="left", padx=20, pady=15)

        btn_refresh = ctk.CTkButton(
            header, text="Actualizar", width=90,
            fg_color=COLOR_CARD, hover_color=COLOR_CARD_HOVER,
            command=self._load_entries
        )
        btn_refresh.pack(side="right", padx=20, pady=15)

        # Panel scrollable de entradas
        self.scroll_list = ctk.CTkScrollableFrame(self, fg_color="#18191d", corner_radius=8)
        self.scroll_list.pack(fill="both", expand=True, padx=15, pady=15)

    def _load_entries(self):
        for w in self.scroll_list.winfo_children():
            w.destroy()

        entries = list_startup_entries()
        if not entries:
            lbl_empty = ctk.CTkLabel(self.scroll_list, text="No se detectaron entradas de inicio configuradas.", text_color=COLOR_TEXT_SECONDARY)
            lbl_empty.pack(pady=30)
            return

        for item in entries:
            row = ctk.CTkFrame(self.scroll_list, fg_color=COLOR_CARD, corner_radius=6)
            row.pack(fill="x", padx=5, pady=4)

            # Estado visual
            state_color = COLOR_SUCCESS if item["enabled"] else COLOR_DANGER
            state_text = "ACTIVO" if item["enabled"] else "DESHABILITADO"

            badge = ctk.CTkLabel(
                row, text=state_text, width=80,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                text_color=state_color
            )
            badge.pack(side="left", padx=(10, 5), pady=8)

            # Detalles del programa
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=5, pady=6)

            title_text = f"{item['name']} ({item['location']})"
            lbl_name = ctk.CTkLabel(
                info_frame, text=title_text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                anchor="w"
            )
            lbl_name.pack(fill="x")

            cmd_sub = item["command"]
            if len(cmd_sub) > 65:
                cmd_sub = cmd_sub[:62] + "..."
            lbl_cmd = ctk.CTkLabel(
                info_frame, text=cmd_sub,
                font=ctk.CTkFont(family="Consolas", size=10),
                text_color=COLOR_TEXT_SECONDARY, anchor="w"
            )
            lbl_cmd.pack(fill="x")

            # Botón conmutador (Deshabilitar / Habilitar)
            btn_text = "Desactivar" if item["enabled"] else "Activar"
            btn_color = COLOR_DANGER if item["enabled"] else COLOR_SUCCESS
            btn_hover = COLOR_DANGER_HOVER if item["enabled"] else COLOR_SUCCESS_HOVER

            btn_toggle = ctk.CTkButton(
                row, text=btn_text, width=85, height=26,
                fg_color=btn_color, hover_color=btn_hover,
                font=ctk.CTkFont(size=11),
                command=lambda e=item: self._toggle_entry(e)
            )
            btn_toggle.pack(side="right", padx=15, pady=8)

    def _toggle_entry(self, entry: dict):
        if entry["enabled"]:
            ok, msg = disable_startup_entry(entry)
        else:
            ok, msg = enable_startup_entry(entry)

        if not ok:
            messagebox.showerror("Error", msg)
        self._load_entries()
