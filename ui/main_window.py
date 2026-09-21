import os
import shutil
import threading
import psutil
import webbrowser
import requests
import json
import customtkinter as ctk
from tkinter import messagebox, filedialog

from ui.theme import *
from core.cleaner import get_target_directories, scan_target, clean_directory, empty_recycle_bin
import core.system_cleaner as sys_cleaner
import core.optimizer as opt
from ui.disk_view import DiskVisualizerWindow
from ui.startup_view import StartupManagerWindow
from ui.dev_cleaner_view import DevCleanerWindow
from ui.dism_view import DismManagerWindow
from ui.duplicate_view import DuplicateFinderWindow
from ui.services_view import ServicesOptimizerWindow

FEEDBACK_ACCESS_KEY = "6468511d-508d-4078-aa8f-44f33fb19a29"

CONFIG_DIR = os.path.join(os.getcwd(), "data")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def load_theme_preference():
    """Lee el tema guardado en data/config.json, o lo crea con 'Dark' por defecto."""
    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("theme", "Dark")
        else:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({"theme": "Dark"}, f, indent=4)
            return "Dark"
    except Exception:
        return "Dark"


def save_theme_preference(theme_name):
    """Guarda la preferencia de tema en data/config.json."""
    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"theme": theme_name}, f, indent=4)
    except Exception:
        pass


load_theme_config = load_theme_preference
save_theme_config = save_theme_preference


class CleanerWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_default_color_theme("blue")

        self.title("KILLCleaner - Centro de Optimización")
        
        # Centrado automático en la pantalla del usuario
        app_width = 1040
        app_height = 700
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width - app_width) / 2)
        y = int((screen_height - app_height) / 2)
        self.geometry(f"{app_width}x{app_height}+{max(0, x)}+{max(0, y)}")
        self.minsize(940, 620)
        self.configure(fg_color=COLOR_BG_DARK)

        icon_path = os.path.join("assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.console_visible = False
        self._build_layout()
        self._refresh_system_metrics()

    def _build_layout(self):
        # 1. BARRA LATERAL (SIDEBAR)
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand_lbl = ctk.CTkLabel(
            self.sidebar, text="⚡ KILLCleaner",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=COLOR_ACCENT
        )
        brand_lbl.pack(padx=20, pady=(25, 20), anchor="w")

        self.btn_nav_dash = self._create_nav_btn("📊 Resumen / Inicio", lambda: self._show_tab("dashboard"))
        self.btn_nav_maint = self._create_nav_btn("🧹 Mantenimiento", lambda: self._show_tab("maintenance"))
        self.btn_nav_tools = self._create_nav_btn("⚙️ Utilidades & Ajustes", lambda: self._show_tab("tools"))

        # Espaciador vertical en la sidebar
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # Botón de Feedback / Sugerencias en la Sidebar
        self.btn_feedback = ctk.CTkButton(
            self.sidebar, text="💬 Buzón de Dudas & Sugerencias", height=30,
            fg_color=COLOR_CARD, hover_color=COLOR_CARD_HOVER,
            text_color=COLOR_TEXT_PRIMARY, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=self.open_feedback_modal
        )
        self.btn_feedback.pack(fill="x", padx=14, pady=(0, 8))

        # Botón de Donaciones en la Sidebar
        self.btn_donate = ctk.CTkButton(
            self.sidebar, text="☕ Apoyar el Proyecto", height=32,
            fg_color="#eab308", hover_color="#ca8a04",
            text_color="#18181b", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=self.open_donation_modal
        )
        self.btn_donate.pack(fill="x", padx=14, pady=(0, 8))

        # Selector de Tema en la Sidebar
        theme_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        theme_frame.pack(fill="x", padx=14, pady=(0, 8))

        theme_lbl = ctk.CTkLabel(
            theme_frame, text="🎨 Tema:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        theme_lbl.pack(side="left", padx=(0, 4))

        saved_theme = load_theme_preference()
        ctk.set_appearance_mode(saved_theme)

        self.theme_menu = ctk.CTkOptionMenu(
            theme_frame, values=["Dark", "Light", "System"], width=110, height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=COLOR_CARD, button_color=COLOR_CARD_HOVER, button_hover_color="#323744",
            command=self._change_theme_mode
        )
        self.theme_menu.set(saved_theme)
        self.theme_menu.pack(side="right")

        # Botón de Manual de Usuario en la parte inferior de la Sidebar
        self.btn_help = ctk.CTkButton(
            self.sidebar, text="📖 Manual de Usuario", height=34,
            fg_color=COLOR_CARD, hover_color=COLOR_CARD_HOVER,
            text_color=COLOR_TEXT_PRIMARY, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self.open_user_manual
        )
        self.btn_help.pack(fill="x", padx=14, pady=(0, 20))

        # 2. CONTENEDOR DERECHO
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="right", fill="both", expand=True, padx=18, pady=16)

        # 2.1 Tarjetas de métricas
        self.stats_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.stats_frame.pack(fill="x", pady=(0, 10))

        self.card_disk = self._create_stat_card(self.stats_frame, "🖴 DISCO C:", "Calculando...", "Espacio libre")
        self.card_ram = self._create_stat_card(self.stats_frame, "⚡ MEMORIA RAM", "Calculando...", "En uso")
        self.card_trash = self._create_stat_card(self.stats_frame, "🗑️ RESIDUOS ESTIMADOS", "-- MB", "Pendientes de purga")

        # 2.2 MONITOR DE ACTIVIDAD EN VIVO (STATUS OVERLAY)
        self.status_card = ctk.CTkFrame(self.main_container, fg_color=COLOR_CARD, corner_radius=8)
        self.status_card.pack(fill="x", pady=(0, 10))

        status_inner = ctk.CTkFrame(self.status_card, fg_color="transparent")
        status_inner.pack(fill="x", padx=14, pady=(10, 6))

        self.lbl_status_icon = ctk.CTkLabel(
            status_inner, text="🟢", font=ctk.CTkFont(size=16)
        )
        self.lbl_status_icon.pack(side="left", padx=(0, 8))

        self.lbl_status_text = ctk.CTkLabel(
            status_inner, text="Listo para operar — Sistema estable",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY, anchor="w"
        )
        self.lbl_status_text.pack(side="left", fill="x", expand=True)

        self.status_progress = ctk.CTkProgressBar(
            self.status_card, height=6, corner_radius=3,
            progress_color=COLOR_ACCENT, fg_color=("#cbd5e1", "#101216")
        )
        self.status_progress.pack(fill="x", padx=14, pady=(0, 8))
        self.status_progress.set(0)

        # 2.3 Vistas por pestaña
        self.views_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.views_container.pack(fill="both", expand=True)

        self._build_dashboard_tab()
        self._build_maintenance_tab()
        self._build_tools_tab()

        # 2.4 Botón de consola (Oculto por defecto)
        self.btn_toggle_console = ctk.CTkButton(
            self.main_container, text="Mostrar Registro Técnico ▼", height=26,
            fg_color=COLOR_CARD, hover_color=COLOR_CARD_HOVER,
            text_color=COLOR_TEXT_SECONDARY, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=self._toggle_console
        )
        self.btn_toggle_console.pack(fill="x", pady=(8, 0))

        # 2.5 Consola
        self.console_frame = ctk.CTkFrame(self.main_container, fg_color="transparent", height=120)
        self.log_area = ctk.CTkTextbox(
            self.console_frame, font=("Consolas", 10),
            text_color=COLOR_TEXT_PRIMARY, fg_color=("#e2e8f0", "#121316")
        )
        self.log_area.pack(fill="both", expand=True)
        self.log_area.configure(state="disabled")

        self._show_tab("dashboard")

    def set_status(self, icon, message, busy=False, progress_val=None):
        """Actualiza el Monitor de Actividad en Vivo de forma segura entre hilos."""
        def _update():
            self.lbl_status_icon.configure(text=icon)
            self.lbl_status_text.configure(text=message)
            if busy:
                self.status_progress.configure(mode="indeterminate")
                self.status_progress.start()
            else:
                self.status_progress.stop()
                self.status_progress.configure(mode="determinate")
                if progress_val is not None:
                    self.status_progress.set(progress_val)
                else:
                    self.status_progress.set(0)
        self.after(0, _update)

    def _show_modal_alert(self, title, heading, message, icon="🎉", status_type="success"):
        """Muestra una alerta modal emergente moderna estilizada."""
        def _build_modal():
            modal = ctk.CTkToplevel(self)
            modal.title(title)
            modal.geometry("480x230")
            modal.resizable(False, False)
            modal.configure(fg_color=COLOR_BG_DARK)
            modal.transient(self)
            modal.grab_set()

            try:
                self.update_idletasks()
                x = self.winfo_x() + (self.winfo_width() // 2) - 240
                y = self.winfo_y() + (self.winfo_height() // 2) - 115
                modal.geometry(f"480x230+{max(0, x)}+{max(0, y)}")
            except Exception:
                pass

            accent_color = COLOR_SUCCESS if status_type == "success" else (COLOR_ACCENT if status_type == "info" else COLOR_DANGER)

            card = ctk.CTkFrame(modal, fg_color=COLOR_CARD, corner_radius=12)
            card.pack(fill="both", expand=True, padx=16, pady=16)

            header_frame = ctk.CTkFrame(card, fg_color="transparent")
            header_frame.pack(fill="x", padx=16, pady=(16, 8))

            icon_lbl = ctk.CTkLabel(header_frame, text=icon, font=ctk.CTkFont(size=30))
            icon_lbl.pack(side="left", padx=(0, 12))

            head_lbl = ctk.CTkLabel(
                header_frame, text=heading,
                font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
                text_color=accent_color, anchor="w", justify="left"
            )
            head_lbl.pack(side="left", fill="x", expand=True)

            body_lbl = ctk.CTkLabel(
                card, text=message,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=COLOR_TEXT_SECONDARY, anchor="w", justify="left", wraplength=410
            )
            body_lbl.pack(fill="both", expand=True, padx=16, pady=(0, 12))

            btn_close = ctk.CTkButton(
                card, text="Entendido", width=110, height=32,
                fg_color=accent_color, hover_color=COLOR_CARD_HOVER,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                command=modal.destroy
            )
            btn_close.pack(anchor="e", padx=16, pady=(0, 14))

        self.after(0, _build_modal)

    def _create_nav_btn(self, text, command):
        btn = ctk.CTkButton(
            self.sidebar, text=text, fg_color="transparent", hover_color=COLOR_CARD,
            anchor="w", height=38, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY, command=command
        )
        btn.pack(fill="x", padx=12, pady=4)
        return btn

    def _create_stat_card(self, parent, title, val, subtitle):
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=8)
        card.pack(side="left", fill="both", expand=True, padx=4)

        t_lbl = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=COLOR_TEXT_SECONDARY)
        t_lbl.pack(anchor="w", padx=12, pady=(8, 0))

        v_lbl = ctk.CTkLabel(card, text=val, font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), text_color=COLOR_TEXT_PRIMARY)
        v_lbl.pack(anchor="w", padx=12, pady=(2, 0))

        s_lbl = ctk.CTkLabel(card, text=subtitle, font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=COLOR_TEXT_SECONDARY)
        s_lbl.pack(anchor="w", padx=12, pady=(0, 8))

        return {"val": v_lbl, "sub": s_lbl}

    # --- PESTAÑAS ---
    def _build_dashboard_tab(self):
        self.tab_dash = ctk.CTkScrollableFrame(self.views_container, fg_color="transparent")
        
        # Banner Principal
        banner = ctk.CTkFrame(self.tab_dash, fg_color=COLOR_CARD, corner_radius=10)
        banner.pack(fill="x", pady=(0, 10), ipady=10)

        title = ctk.CTkLabel(banner, text="🚀 Optimización Rápida del Sistema", font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"), text_color=COLOR_ACCENT)
        title.pack(anchor="w", padx=20, pady=(6, 2))

        desc = ctk.CTkLabel(banner, text="Inspecciona residuos acumulados en el sistema o realiza una purga de temporales con un clic.", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=COLOR_TEXT_SECONDARY)
        desc.pack(anchor="w", padx=20, pady=(0, 10))

        btn_box = ctk.CTkFrame(banner, fg_color="transparent")
        btn_box.pack(fill="x", padx=20)

        self.btn_quick_scan = ctk.CTkButton(btn_box, text="🔍 Analizar Residuos", fg_color=COLOR_BLUE, hover_color="#2563eb", width=160, height=32, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), command=self.start_analysis_thread)
        self.btn_quick_scan.pack(side="left", padx=(0, 10))

        self.btn_quick_clean = ctk.CTkButton(btn_box, text="⚡ Limpiar Temporales", fg_color=COLOR_DANGER, hover_color="#dc2626", width=160, height=32, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), command=self.start_clean_thread)
        self.btn_quick_clean.pack(side="left")

        # PANEL COMPLEMENTARIO
        dash_grid = ctk.CTkFrame(self.tab_dash, fg_color="transparent")
        dash_grid.pack(fill="both", expand=True, pady=4)

        # 1. Tarjeta de Salud y Diagnóstico
        health_card = ctk.CTkFrame(dash_grid, fg_color=COLOR_CARD, corner_radius=10)
        health_card.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=4, ipady=8)

        ctk.CTkLabel(health_card, text="🩺 Diagnóstico y Salud", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(10, 8))

        self.lbl_smart_status = ctk.CTkLabel(health_card, text="• Salud de Disco (SMART): Consultando...", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=COLOR_TEXT_SECONDARY)
        self.lbl_smart_status.pack(anchor="w", padx=16, pady=3)

        self.lbl_recycle_status = ctk.CTkLabel(health_card, text="• Papelera: Lista para comprobación", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=COLOR_TEXT_SECONDARY)
        self.lbl_recycle_status.pack(anchor="w", padx=16, pady=3)

        btn_smart_diag = ctk.CTkButton(
            health_card, text="Comprobar Salud", width=130, height=28,
            fg_color=COLOR_SIDEBAR, hover_color=COLOR_CARD_HOVER,
            text_color=COLOR_TEXT_PRIMARY, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=self.check_smart_action
        )
        btn_smart_diag.pack(anchor="w", padx=16, pady=(12, 5))

        # 2. Tarjeta de Opciones de Purga Rápida
        options_card = ctk.CTkFrame(dash_grid, fg_color=COLOR_CARD, corner_radius=10)
        options_card.pack(side="right", fill="both", expand=True, padx=(6, 0), pady=4, ipady=8)

        ctk.CTkLabel(options_card, text="⚙️ Áreas de Purga Incluidas", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(10, 8))

        self.chk_temp = ctk.CTkCheckBox(options_card, text="Archivos temporales (%TEMP%)", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=COLOR_TEXT_PRIMARY)
        self.chk_temp.pack(anchor="w", padx=16, pady=3)
        self.chk_temp.select()

        self.chk_prefetch = ctk.CTkCheckBox(options_card, text="Caché de ejecución (Prefetch)", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=COLOR_TEXT_PRIMARY)
        self.chk_prefetch.pack(anchor="w", padx=16, pady=3)
        self.chk_prefetch.select()

        self.chk_recycle = ctk.CTkCheckBox(options_card, text="Vaciar Papelera automáticamente", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=COLOR_TEXT_PRIMARY)
        self.chk_recycle.pack(anchor="w", padx=16, pady=3)

    def _change_theme_mode(self, new_theme):
        """Cambia el modo de apariencia y guarda la preferencia en data/config.json."""
        ctk.set_appearance_mode(new_theme)
        save_theme_preference(new_theme)

    def _build_maintenance_tab(self):
        self.tab_maint = ctk.CTkScrollableFrame(self.views_container, fg_color="transparent")

        self._create_action_row(self.tab_maint, "🛡️ Punto de Restauración del Sistema", "Crea una instantánea del estado de Windows para volver atrás ante cualquier imprevisto.", "Crear", COLOR_SUCCESS, self.start_restore_point_thread, accent_bar=COLOR_SUCCESS)
        self._create_action_row(self.tab_maint, "⚡ Optimización / TRIM de Disco", "Ejecuta comandos de re-trim en SSD y optimización de sectores en el disco C:.", "Optimizar", COLOR_AMBER, self.start_trim_thread, accent_bar=COLOR_AMBER)
        self._create_action_row(self.tab_maint, "🌐 Limpieza de Sistema & Navegadores", "Purga cachés de navegadores, descargas de Windows Update y logs de fallo.", "Limpiar", COLOR_BLUE, self.start_full_sys_clean_thread, accent_bar=COLOR_BLUE)
        self._create_action_row(self.tab_maint, "🗑️ Vaciar Papelera de Reciclaje", "Elimina de forma irreversible todos los archivos reciclados.", "Vaciar", COLOR_DANGER, self.clean_recycle_bin_action, accent_bar=COLOR_DANGER)
        self._create_action_row(self.tab_maint, "📶 Caché de Red y Servidores DNS", "Restablece la pila TCP/IP y vacía el resolver de nombres de dominio.", "Purgar", COLOR_CYAN, self.flush_network_action, accent_bar=COLOR_CYAN)
        self._create_action_row(self.tab_maint, "🩺 Reparar Archivos del Sistema (SFC)", "Ejecuta sfc /scannow para corregir componentes dañados del sistema.", "Escanear", COLOR_BLUE, self.start_sfc_thread, accent_bar=COLOR_BLUE)
        self._create_action_row(self.tab_maint, "📦 Mantenimiento de Imagen (DISM)", "Inspecciona el almacén de componentes WinSxS y repara la imagen oficial.", "Abrir DISM", COLOR_ORANGE, self.open_dism_manager, accent_bar=COLOR_ORANGE)

    def _build_tools_tab(self):
        self.tab_tools = ctk.CTkScrollableFrame(self.views_container, fg_color="transparent")

        self._create_action_row(self.tab_tools, "📊 Inspector Visual de Espacio (TreeSize)", "Examina particiones y ordena las carpetas y archivos más pesados.", "Abrir", COLOR_AMBER, self.open_disk_visualizer, accent_bar=COLOR_AMBER)
        self._create_action_row(self.tab_tools, "🧬 Buscador de Duplicados (SHA-256)", "Encuentra copias exactas de archivos mediante cálculo criptográfico.", "Examinar", COLOR_AMBER, self.open_duplicate_finder, accent_bar=COLOR_AMBER)
        self._create_action_row(self.tab_tools, "🚀 Gestor de Aplicaciones de Inicio", "Administra los programas que arrancan con Windows para acelerar el inicio.", "Gestionar", COLOR_BLUE, self.open_startup_manager, accent_bar=COLOR_BLUE)
        self._create_action_row(self.tab_tools, "📦 Caché Dev / Gestores de Paquetes", "Purga cachés voluminosas de pip, npm, discord, spotify y __pycache__.", "Limpiar", COLOR_PURPLE, self.open_dev_cleaner, accent_bar=COLOR_PURPLE)
        self._create_action_row(self.tab_tools, "🎮 Modo Gaming (Liberador de RAM)", "Finaliza procesos no esenciales en segundo plano y purga el portapapeles.", "Activar", COLOR_SUCCESS, self.start_gaming_mode_thread, accent_bar=COLOR_SUCCESS)
        self._create_action_row(self.tab_tools, "🛡️ Servicios Innecesarios & Telemetría", "Desactiva servicios secundarios como DiagTrack o Spooler.", "Ajustar", COLOR_CYAN, self.open_services_optimizer, accent_bar=COLOR_CYAN)
        self._create_action_row(self.tab_tools, "⏰ Tareas Programadas de Limpieza", "Programa mantenimientos periódicos de limpieza en el Programador de Windows.", "Configurar", COLOR_BLUE, self.open_scheduled_tasks_modal, accent_bar=COLOR_BLUE)
        self._create_action_row(self.tab_tools, "📄 Exportar Reporte de Mantenimiento", "Genera y guarda un informe de auditoría detallado con las acciones realizadas.", "Exportar", COLOR_SUCCESS, self.export_report_action, accent_bar=COLOR_SUCCESS)

    def _create_action_row(self, parent, title, desc, btn_text, btn_color, command, accent_bar=COLOR_BLUE):
        """Construye una fila de tarjeta de acción con altura ampliada (70px) y alta legibilidad."""
        row = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=8, height=70)
        row.pack(fill="x", pady=4, padx=2)
        row.pack_propagate(False)

        badge = ctk.CTkFrame(row, width=4, corner_radius=2, fg_color=accent_bar)
        badge.pack(side="left", fill="y", padx=(0, 4))

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=12, pady=8)

        t_lbl = ctk.CTkLabel(
            info, text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            anchor="w", text_color=COLOR_TEXT_PRIMARY
        )
        t_lbl.pack(fill="x")

        d_lbl = ctk.CTkLabel(
            info, text=desc,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="normal"),
            text_color=COLOR_TEXT_SECONDARY, anchor="w"
        )
        d_lbl.pack(fill="x", pady=(2, 0))

        btn = ctk.CTkButton(
            row, text=btn_text, width=110, height=30,
            fg_color=btn_color, hover_color=COLOR_CARD_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=command
        )
        btn.pack(side="right", padx=14, pady=18)

    # --- MANUAL DE USUARIO (MODAL) ---
    def open_user_manual(self):
        manual = ctk.CTkToplevel(self)
        manual.title("KILLCleaner - Manual de Usuario y Guía de Uso")
        manual.geometry("640x520")
        manual.minsize(580, 420)
        manual.configure(fg_color=COLOR_BG_DARK)
        manual.transient(self)
        manual.grab_set()

        try:
            self.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() // 2) - 320
            y = self.winfo_y() + (self.winfo_height() // 2) - 260
            manual.geometry(f"640x520+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        header = ctk.CTkLabel(
            manual, text="📖 Guía de Herramientas y Mantenimiento",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=COLOR_ACCENT
        )
        header.pack(anchor="w", padx=20, pady=(20, 10))

        content_box = ctk.CTkScrollableFrame(manual, fg_color=COLOR_CARD, corner_radius=10)
        content_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        guide = [
            ("⚡ Limpieza Básica & Temporales", "Elimina los archivos en %TEMP% y Prefetch acumulados por programas cerrados. Seguro para el uso diario sin riesgo para tus documentos."),
            ("🌐 Sistema & Navegadores", "Borra historiales residuales de navegación y las carpetas de instalación que deja Windows Update luego de actualizarse."),
            ("🗑️ Vaciar Papelera de Reciclaje", "Purga de forma definitiva los elementos descartados de todas las unidades del equipo."),
            ("📶 Caché de Red & DNS", "Limpia la tabla de resolución DNS local y reestablece los sockets de Windows; útil si alguna página web falla en cargar."),
            ("🩺 Reparación del Sistema (SFC & DISM)", "Inspecciona y restaura archivos maestros dañados de Windows comparándolos contra la base limpia de Microsoft."),
            ("🛡️ Punto de Restauración", "Crea una instantánea de seguridad en Windows para revertir cualquier cambio del sistema ante imprevistos."),
            ("⚡ Optimización / TRIM de Disco", "Ejecuta el comando de recorte (re-trim) para extender la vida útil y velocidad de discos SSD y desfragmentación de HDD."),
            ("📊 Inspector de Espacio (TreeSize)", "Permite explorar visualmente qué carpetas ocupan más espacio en tu disco para liberar gigabytes a criterio propio."),
            ("🧬 Buscador de Duplicados", "Calcula el hash criptográfico SHA-256 de los archivos para encontrar duplicados exactos aunque tengan nombres distintos."),
            ("🚀 Gestor de Aplicaciones de Inicio", "Administra los programas que arrancan con Windows para acelerar el tiempo de inicio."),
            ("📦 Caché Dev / Gestores de Paquetes", "Purga cachés voluminosas de pip, npm, discord, spotify y carpetas __pycache__."),
            ("🎮 Modo Gaming (Liberador de RAM)", "Finaliza procesos prescindibles en segundo plano (Discord, Spotify, navegadores) para dejar libre el procesador y la memoria."),
            ("🛡️ Servicios & Telemetría", "Permite pausar servicios en segundo plano como DiagTrack (rastreo de diagnóstico) o cola de impresión si no se emplean."),
            ("⏰ Tareas Programadas", "Automatiza la limpieza periódica semanal o diaria mediante el programador de Windows sin interrumpir tu trabajo."),
            ("📄 Exportar Reporte de Mantenimiento", "Guarda auditorías completas de espacio liberado, resumen de acciones y estado SMART en archivo de texto .txt."),
            ("☕ Apoyar & 💬 Buzón de Dudas", "Canal directo de contacto anónimo para enviar sugerencias/dudas y donaciones voluntarias por Cafecito / Mercado Pago.")
        ]

        for title, desc in guide:
            item_frame = ctk.CTkFrame(content_box, fg_color="transparent")
            item_frame.pack(fill="x", pady=6)

            ctk.CTkLabel(item_frame, text=title, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_TEXT_PRIMARY, anchor="w").pack(fill="x")
            ctk.CTkLabel(item_frame, text=desc, font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=COLOR_TEXT_SECONDARY, anchor="w", justify="left", wraplength=550).pack(fill="x", pady=(2, 0))

    # --- VENTANA MODAL DE FEEDBACK / CONTACTO ---
    def open_feedback_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Contacto y Sugerencias")
        modal.geometry("500x420")
        modal.resizable(False, False)
        modal.configure(fg_color=COLOR_BG_DARK)
        modal.transient(self)
        modal.grab_set()

        try:
            self.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() // 2) - 250
            y = self.winfo_y() + (self.winfo_height() // 2) - 210
            modal.geometry(f"500x420+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        header = ctk.CTkLabel(
            modal, text="📬 Envíanos tu Duda, Queja o Sugerencia",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color="#f8fafc"
        )
        header.pack(anchor="w", padx=24, pady=(18, 4))

        sub_lbl = ctk.CTkLabel(
            modal, text="Tu mensaje llegará directamente al equipo de desarrollo.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color="#cbd5e1"
        )
        sub_lbl.pack(anchor="w", padx=24, pady=(0, 12))

        form_box = ctk.CTkFrame(modal, fg_color=COLOR_CARD, corner_radius=10)
        form_box.pack(fill="both", expand=True, padx=24, pady=(0, 18))

        # Categoría
        ctk.CTkLabel(
            form_box, text="Categoría:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(anchor="w", padx=16, pady=(12, 2))

        opt_menu = ctk.CTkOptionMenu(
            form_box,
            values=["Sugerencia / Petición", "Reporte de Error / Queja", "Consulta general"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="#101216", button_color=COLOR_SIDEBAR, button_hover_color=COLOR_CARD_HOVER
        )
        opt_menu.pack(fill="x", padx=16, pady=(0, 8))

        # Email de contacto
        ctk.CTkLabel(
            form_box, text="Tu Correo de Contacto (Opcional):",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(anchor="w", padx=16, pady=(0, 2))

        entry_email = ctk.CTkEntry(
            form_box, placeholder_text="Tu email si deseas recibir respuesta (opcional)",
            height=32, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="#101216", text_color=COLOR_TEXT_PRIMARY
        )
        entry_email.pack(fill="x", padx=16, pady=(0, 8))

        # Mensaje
        ctk.CTkLabel(
            form_box, text="Mensaje:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(anchor="w", padx=16, pady=(0, 2))

        txt_message = ctk.CTkTextbox(
            form_box, height=110, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="#101216", text_color=COLOR_TEXT_PRIMARY
        )
        txt_message.pack(fill="x", padx=16, pady=(0, 8))

        lbl_status = ctk.CTkLabel(
            form_box, text="", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold")
        )
        lbl_status.pack(anchor="w", padx=16, pady=(0, 4))

        def _send_action():
            categoria = opt_menu.get()
            user_email = entry_email.get().strip()
            mensaje_cuerpo = txt_message.get("1.0", "end").strip()

            if not mensaje_cuerpo:
                lbl_status.configure(text="⚠️ El mensaje no puede estar vacío.", text_color=COLOR_DANGER)
                return

            lbl_status.configure(text="⏳ Enviando...", text_color=COLOR_ACCENT)
            btn_send.configure(state="disabled")

            def _worker():
                payload = {
                    "access_key": FEEDBACK_ACCESS_KEY,
                    "subject": f"KILLCleaner: {categoria}",
                    "replyto": user_email if user_email else "no-reply@killcleaner.local",
                    "category": categoria,
                    "message": mensaje_cuerpo
                }

                try:
                    res = requests.post("https://api.web3forms.com/submit", json=payload, timeout=10)
                    res_data = res.json()
                    if res.status_code == 200 and res_data.get("success", False):
                        self.after(0, lambda: lbl_status.configure(text="✓ ¡Mensaje recibido, gracias!", text_color=COLOR_SUCCESS))
                        modal.after(2000, modal.destroy)
                    else:
                        err_text = res_data.get("message", "Error al enviar mensaje.")
                        self.after(0, lambda: (
                            lbl_status.configure(text=f"⚠️ {err_text}", text_color=COLOR_DANGER),
                            btn_send.configure(state="normal")
                        ))
                except Exception:
                    self.after(0, lambda: (
                        lbl_status.configure(text="⚠️ Error de conexión al enviar.", text_color=COLOR_DANGER),
                        btn_send.configure(state="normal")
                    ))

            threading.Thread(target=_worker, daemon=True).start()

        btn_send = ctk.CTkButton(
            form_box, text="📤 Enviar Mensaje", height=32,
            fg_color=COLOR_BLUE, hover_color="#2563eb",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=_send_action
        )
        btn_send.pack(fill="x", padx=16, pady=(0, 10))

    # --- VENTANA MODAL DE DONACIONES ---
    def open_donation_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Apoyar el Desarrollo de KILLCleaner")
        modal.geometry("540x420")
        modal.resizable(False, False)
        modal.configure(fg_color=COLOR_BG_DARK)
        modal.transient(self)
        modal.grab_set()

        try:
            self.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() // 2) - 270
            y = self.winfo_y() + (self.winfo_height() // 2) - 210
            modal.geometry(f"540x420+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        header = ctk.CTkLabel(
            modal, text="☕ Apoyar el Proyecto",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color="#eab308"
        )
        header.pack(anchor="w", padx=24, pady=(20, 6))

        desc_text = (
            "KILLCleaner es una suite de mantenimiento y optimización 100% gratuita y de código abierto. "
            "Si la herramienta te resultó útil y deseas colaborar con su mantenimiento continuo, cualquier aporte es de gran ayuda."
        )
        desc_lbl = ctk.CTkLabel(
            modal, text=desc_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color="#cbd5e1", anchor="w", justify="left", wraplength=490
        )
        desc_lbl.pack(fill="x", padx=24, pady=(0, 14))

        content_box = ctk.CTkFrame(modal, fg_color=COLOR_CARD, corner_radius=10)
        content_box.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        # 1. Cafecito (Argentina)
        cafecito_frame = ctk.CTkFrame(content_box, fg_color="transparent")
        cafecito_frame.pack(fill="x", padx=16, pady=(14, 6))

        btn_cafecito = ctk.CTkButton(
            cafecito_frame, text="❤️ Donar en Cafecito (Argentina)", height=34,
            fg_color="#00C853", hover_color="#00A844", text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=lambda: webbrowser.open("https://cafecito.app/cristian_dev")
        )
        btn_cafecito.pack(fill="x")

        # 2. Ko-fi / PayPal
        kofi_frame = ctk.CTkFrame(content_box, fg_color="transparent")
        kofi_frame.pack(fill="x", padx=16, pady=6)

        btn_kofi = ctk.CTkButton(
            kofi_frame, text="🌍 Donar en Ko-fi / PayPal", height=34,
            fg_color="#2962FF", hover_color="#1E4BD8", text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=lambda: webbrowser.open("https://ko-fi.com/killcleaner")
        )
        btn_kofi.pack(fill="x")

        # 3. Transferencia Directa (Mercado Pago)
        cbu_card = ctk.CTkFrame(content_box, fg_color="#101216", corner_radius=8)
        cbu_card.pack(fill="x", padx=16, pady=8)

        cbu_info = ctk.CTkFrame(cbu_card, fg_color="transparent")
        cbu_info.pack(side="left", fill="both", expand=True, padx=12, pady=8)

        ctk.CTkLabel(
            cbu_info, text="💳 Mercado Pago / Transferencia Directa:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY, anchor="w"
        ).pack(fill="x")

        mp_email = "cgonzalez7060@gmail.com"
        lbl_alias = ctk.CTkLabel(
            cbu_info, text=f"Cuenta MP / Email: {mp_email}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color="#facc15", anchor="w"
        )
        lbl_alias.pack(fill="x", pady=(2, 0))

        def copy_alias_action():
            try:
                self.clipboard_clear()
                self.clipboard_append(mp_email)
                btn_copy_alias.configure(text="¡Copiado! ✓", fg_color=COLOR_SUCCESS)
                modal.after(2000, lambda: btn_copy_alias.configure(text="Copiar Email / MP", fg_color=COLOR_SIDEBAR))
            except Exception:
                pass

        btn_copy_alias = ctk.CTkButton(
            cbu_card, text="Copiar Email / MP", width=120, height=30,
            fg_color=COLOR_SIDEBAR, hover_color=COLOR_CARD_HOVER,
            text_color=COLOR_TEXT_PRIMARY, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=copy_alias_action
        )
        btn_copy_alias.pack(side="right", padx=12, pady=10)

        # 4. GitHub Star Button
        github_frame = ctk.CTkFrame(content_box, fg_color="transparent")
        github_frame.pack(fill="x", padx=16, pady=(6, 14))

        btn_github = ctk.CTkButton(
            github_frame, text="⭐ Dar una estrella en GitHub", height=32,
            fg_color=COLOR_CARD_HOVER, hover_color="#323744", text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=lambda: webbrowser.open("https://github.com/CristianNLC/KILLCleaner")
        )
        btn_github.pack(fill="x")

    # --- NAVEGACIÓN Y MÉTRICAS ---
    def _show_tab(self, tab_name):
        self.tab_dash.pack_forget()
        self.tab_maint.pack_forget()
        self.tab_tools.pack_forget()

        self.btn_nav_dash.configure(fg_color="transparent", text_color=COLOR_TEXT_PRIMARY)
        self.btn_nav_maint.configure(fg_color="transparent", text_color=COLOR_TEXT_PRIMARY)
        self.btn_nav_tools.configure(fg_color="transparent", text_color=COLOR_TEXT_PRIMARY)

        if tab_name == "dashboard":
            self.tab_dash.pack(fill="both", expand=True)
            self.btn_nav_dash.configure(fg_color=COLOR_CARD, text_color=COLOR_ACCENT)
        elif tab_name == "maintenance":
            self.tab_maint.pack(fill="both", expand=True)
            self.btn_nav_maint.configure(fg_color=COLOR_CARD, text_color=COLOR_ACCENT)
        elif tab_name == "tools":
            self.tab_tools.pack(fill="both", expand=True)
            self.btn_nav_tools.configure(fg_color=COLOR_CARD, text_color=COLOR_ACCENT)

    def _refresh_system_metrics(self):
        def _do_refresh():
            try:
                total, used, free = shutil.disk_usage("C:\\")
                free_gb = round(free / (1024**3), 1)
                total_gb = round(total / (1024**3), 1)
                self.card_disk["val"].configure(text=f"{free_gb} GB Libres")
                self.card_disk["sub"].configure(text=f"de {total_gb} GB totales")

                ram = psutil.virtual_memory()
                self.card_ram["val"].configure(text=f"{ram.percent}%")
                self.card_ram["sub"].configure(text=f"{round(ram.used / (1024**3), 1)} / {round(ram.total / (1024**3), 1)} GB")
            except Exception:
                pass
        self.after(0, _do_refresh)

    def _toggle_console(self):
        if self.console_visible:
            self.console_frame.pack_forget()
            self.btn_toggle_console.configure(text="Mostrar Registro Técnico ▼")
            self.console_visible = False
        else:
            self.console_frame.pack(fill="x", pady=(8, 0))
            self.btn_toggle_console.configure(text="Ocultar Registro Técnico ▲")
            self.console_visible = True

    def log(self, message):
        """Escribe mensajes en el registro técnico de forma hilo-segura."""
        def _do_log():
            self.log_area.configure(state="normal")
            self.log_area.insert("end", message + "\n")
            self.log_area.see("end")
            self.log_area.configure(state="disabled")
        self.after(0, _do_log)

    # --- SUBVENTANAS Y ACCIONES ---
    def open_disk_visualizer(self):
        DiskVisualizerWindow(self).grab_set()

    def open_duplicate_finder(self):
        DuplicateFinderWindow(self).grab_set()

    def open_startup_manager(self):
        StartupManagerWindow(self).grab_set()

    def open_dev_cleaner(self):
        DevCleanerWindow(self).grab_set()

    def open_dism_manager(self):
        DismManagerWindow(self).grab_set()

    def open_services_optimizer(self):
        ServicesOptimizerWindow(self).grab_set()

    def check_smart_action(self):
        self.set_status("⏳", "Consultando diagnóstico SMART del disco principal...", busy=True)
        def _task():
            status = opt.check_smart_status()
            def _ui():
                self.lbl_smart_status.configure(text=f"• Salud de Disco (SMART): {status}")
            self.after(0, _ui)
            self.log(f"[*] Comprobación SMART de disco principal: {status}")
            self.set_status("🟢", f"Salud de Disco (SMART): {status}", busy=False, progress_val=1.0)
            self._show_modal_alert("Diagnóstico SMART", "Salud del Disco", f"Resultado del diagnóstico SMART: {status}", icon="🩺", status_type="info" if status == "OK" else "warning")
        threading.Thread(target=_task, daemon=True).start()

    def start_analysis_thread(self):
        self.set_status("⏳", "Analizando residuos acumulados en el sistema...", busy=True)
        threading.Thread(target=self._run_analysis, daemon=True).start()

    def _run_analysis(self):
        self.log("\n--- ANÁLISIS DE RESIDUOS BÁSICOS ---")
        targets = get_target_directories()
        total_b, total_f = 0, 0
        for label, path in targets.items():
            b, count = scan_target(path)
            total_b += b
            total_f += count
            self.log(f"[*] {label}: {count} archivos ({round(b / (1024 * 1024), 2)} MB)")
        total_mb = round(total_b / (1024 * 1024), 2)
        self.log(f"[>] Total recuperable: {total_mb} MB en {total_f} archivos.")
        
        def _update_cards():
            self.card_trash["val"].configure(text=f"~{total_mb} MB")
            self.card_trash["sub"].configure(text=f"{total_f} archivos detectados")
        self.after(0, _update_cards)

        self.set_status("🟢", f"Análisis completado: ~{total_mb} MB detectados ({total_f} archivos).", busy=False, progress_val=1.0)
        self._show_modal_alert("Análisis de Residuos", "¡Análisis Completado!", f"Se detectaron aproximadamente {total_mb} MB de espacio recuperable en {total_f} archivos.", icon="🔍", status_type="info")

    def start_clean_thread(self):
        if not messagebox.askyesno("Confirmar", "¿Eliminar los temporales detectados?"):
            return
        self.set_status("⏳", "Ejecutando purga de archivos temporales...", busy=True)
        threading.Thread(target=self._run_clean, daemon=True).start()

    def _run_clean(self):
        self.log("\n=== LIMPIANDO ARCHIVOS TEMPORALES ===")
        targets = get_target_directories()
        liberados_b, liberados_f = 0, 0
        for label, path in targets.items():
            self.log(f"[>] Purgando {label}...")
            b, count = clean_directory(path, log_callback=self.log)
            liberados_b += b
            liberados_f += count

        # Si el usuario dejó tildada la papelera en el Dashboard, vaciarla también
        if hasattr(self, 'chk_recycle') and self.chk_recycle.get() == 1:
            empty_recycle_bin()
            self.log("[✓] Papelera de reciclaje vaciada en el proceso.")

        total_mb = round(liberados_b / (1024 * 1024), 2)
        self.log(f"[✓] Finalizado: {total_mb} MB liberados ({liberados_f} eliminados).")

        def _update_cards():
            self.card_trash["val"].configure(text="0 MB")
            self.card_trash["sub"].configure(text="Sistema limpio")
        self.after(0, _update_cards)

        self.set_status("🟢", f"Limpieza completada: {total_mb} MB liberados.", busy=False, progress_val=1.0)
        self._refresh_system_metrics()
        self._show_modal_alert("Limpieza de Temporales", "¡Limpieza Completada!", f"Se han eliminado con éxito {total_mb} MB de temporales ({liberados_f} archivos borrados).", icon="⚡", status_type="success")

    def start_full_sys_clean_thread(self):
        if not messagebox.askyesno("Confirmar", "¿Ejecutar limpieza de Windows Update, navegadores y reportes de errores?"):
            return
        self.set_status("⏳", "Ejecutando limpieza de navegadores, Windows Update y logs...", busy=True)
        threading.Thread(target=self._run_full_sys_clean, daemon=True).start()

    def _run_full_sys_clean(self):
        self.log("\n=== LIMPIEZA PROFUNDA DE SISTEMA & NAVEGADORES ===")
        sys_cleaner.clean_browser_caches()
        sys_cleaner.clean_windows_update()
        purged = sys_cleaner.clean_logs_and_dumps()
        sys_cleaner.clean_thumbnail_cache()
        self.log(f"[✓] Mantenimiento profundo completado ({purged} registros/dumps eliminados).")
        
        self.set_status("🟢", f"Mantenimiento profundo completado: {purged} registros/dumps purgados.", busy=False, progress_val=1.0)
        self._refresh_system_metrics()
        self._show_modal_alert("Mantenimiento de Sistema", "¡Mantenimiento Completado!", f"Se purgaron las cachés de navegadores, instalaciones viejas de Windows Update y {purged} archivos de volcados/logs.", icon="🌐", status_type="success")

    def start_gaming_mode_thread(self):
        self.set_status("⏳", "Optimizando memoria RAM y cerrando procesos no esenciales...", busy=True)
        threading.Thread(target=self._run_gaming_mode, daemon=True).start()

    def _run_gaming_mode(self):
        self.log("\n=== MODO RENDIMIENTO (GAMING) ===")
        killed = opt.activate_game_mode()
        self.log(f"[+] Procesos no esenciales finalizados: {killed}. Portapapeles purgado.")
        
        self.set_status("🟢", f"Modo Gaming activo: {killed} procesos finalizados.", busy=False, progress_val=1.0)
        self._refresh_system_metrics()
        self._show_modal_alert("Modo Gaming", "¡Modo Rendimiento Activado!", f"Se finalizaron {killed} procesos secundarios en segundo plano y se liberó el portapapeles de Windows.", icon="🎮", status_type="success")

    def start_sfc_thread(self):
        if not messagebox.askyesno("Confirmar", "El análisis SFC comprobará e integrará archivos dañados de Windows. ¿Iniciar?"):
            return
        self.set_status("⏳", "Ejecutando comprobación de integridad SFC (sfc /scannow)...", busy=True)
        threading.Thread(target=self._run_sfc, daemon=True).start()

    def _run_sfc(self):
        self.log("\n=== COMPROBACIÓN DE INTEGRIDAD SFC ===")
        code = opt.run_sfc_scan(log_callback=self.log)
        self.log(f"[✓] SFC finalizado (Código: {code}).")
        
        self.set_status("🟢", f"Escaneo SFC finalizado (Código: {code}).", busy=False, progress_val=1.0)
        self._show_modal_alert("Reparación SFC", "¡Comprobación SFC Finalizada!", f"El análisis de integridad sfc /scannow culminó con código de salida: {code}.", icon="🩺", status_type="info")

    def clean_recycle_bin_action(self):
        if not messagebox.askyesno("Confirmar", "¿Vaciar la papelera de reciclaje?"):
            return
        self.set_status("⏳", "Vaciando la papelera de reciclaje...", busy=True)
        def _task():
            res = empty_recycle_bin()
            if res:
                self.log("[✓] Papelera vaciada con éxito.")
                self.set_status("🟢", "Papelera vaciada con éxito.", busy=False, progress_val=1.0)
                self._refresh_system_metrics()
                self._show_modal_alert("Papelera de Reciclaje", "¡Papelera Vaciada!", "Todos los archivos de la papelera fueron eliminados permanentemente.", icon="🗑️", status_type="success")
            else:
                self.log("[x] La papelera ya estaba vacía.")
                self.set_status("🟢", "La papelera ya estaba vacía.", busy=False, progress_val=1.0)
                self._show_modal_alert("Papelera de Reciclaje", "Papelera Vacía", "La papelera de reciclaje ya se encuentra vacía.", icon="ℹ️", status_type="info")
        threading.Thread(target=_task, daemon=True).start()

    def flush_network_action(self):
        self.set_status("⏳", "Restableciendo sockets de red y vaciando caché DNS...", busy=True)
        def _task():
            if sys_cleaner.flush_dns_and_network():
                self.log("[✓] Sockets y DNS restablecidos con éxito.")
                self.set_status("🟢", "Red y DNS restablecidos correctamente.", busy=False, progress_val=1.0)
                self._show_modal_alert("Caché de Red", "¡Red y DNS Restablecidos!", "Se vació la tabla de resolución DNS y se restableció la pila de red TCP/IP.", icon="📶", status_type="success")
            else:
                self.log("[x] Error al restablecer la red.")
                self.set_status("⚠️", "No se pudo restablecer la red completamente.", busy=False, progress_val=1.0)
                self._show_modal_alert("Caché de Red", "Atención", "Hubo un inconveniente al restablecer algunas configuraciones de red.", icon="⚠️", status_type="warning")
        threading.Thread(target=_task, daemon=True).start()

    def start_restore_point_thread(self):
        if not messagebox.askyesno("Confirmar", "¿Crear un punto de restauración del sistema en Windows?"):
            return
        self.set_status("⏳", "Creando punto de restauración en Windows...", busy=True)
        threading.Thread(target=self._run_restore_point, daemon=True).start()

    def _run_restore_point(self):
        self.log("\n=== CREANDO PUNTO DE RESTAURACIÓN ===")
        success, msg = opt.create_restore_point("KILLCleaner_Backup")
        if success:
            self.log(f"[✓] {msg}")
            self.set_status("🟢", "Punto de restauración creado con éxito.", busy=False, progress_val=1.0)
            self._show_modal_alert("Punto de Restauración", "¡Punto de Restauración Creado!", msg, icon="🛡️", status_type="success")
        else:
            self.log(f"[x] Error: {msg}")
            self.set_status("⚠️", "No se pudo crear el punto de restauración.", busy=False, progress_val=1.0)
            self._show_modal_alert("Punto de Restauración", "Atención", f"No se pudo crear el punto de restauración: {msg}", icon="⚠️", status_type="warning")

    def start_trim_thread(self):
        if not messagebox.askyesno("Confirmar", "¿Ejecutar optimización TRIM sobre la unidad principal C:?"):
            return
        self.set_status("⏳", "Ejecutando optimización TRIM en el disco C:...", busy=True)
        threading.Thread(target=self._run_trim, daemon=True).start()

    def _run_trim(self):
        self.log("\n=== OPTIMIZACIÓN TRIM DE DISCO ===")
        success, msg = opt.optimize_drive_trim("C:")
        if success:
            self.log(f"[✓] {msg}")
            self.set_status("🟢", "Optimización TRIM finalizada con éxito.", busy=False, progress_val=1.0)
            self._show_modal_alert("Optimización TRIM", "¡Optimización Completada!", "Se ejecutó la optimización TRIM sobre la unidad de almacenamiento principal C:.", icon="⚡", status_type="success")
        else:
            self.log(f"[x] {msg}")
            self.set_status("⚠️", "No se pudo optimizar el disco.", busy=False, progress_val=1.0)
            self._show_modal_alert("Optimización TRIM", "Atención", f"Ocurrió un inconveniente al optimizar la unidad: {msg}", icon="⚠️", status_type="warning")

    def open_scheduled_tasks_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Tareas Programadas de Limpieza")
        modal.geometry("460x300")
        modal.resizable(False, False)
        modal.configure(fg_color=COLOR_BG_DARK)
        modal.transient(self)
        modal.grab_set()

        try:
            self.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() // 2) - 230
            y = self.winfo_y() + (self.winfo_height() // 2) - 150
            modal.geometry(f"460x300+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        ctk.CTkLabel(
            modal, text="⏰ Automatización de Mantenimiento",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_ACCENT
        ).pack(anchor="w", padx=20, pady=(18, 4))

        ctk.CTkLabel(
            modal, text="Programa limpiezas automáticas en segundo plano a través del Programador de Tareas de Windows.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color="#cbd5e1", wraplength=420, justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 12))

        card = ctk.CTkFrame(modal, fg_color=COLOR_CARD, corner_radius=10)
        card.pack(fill="both", expand=True, padx=20, pady=(0, 18))

        ctk.CTkLabel(
            card, text="Frecuencia de Limpieza:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(anchor="w", padx=16, pady=(14, 4))

        freq_menu = ctk.CTkOptionMenu(
            card, values=["Semanal (Recomendado)", "Diaria"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="#101216", button_color=COLOR_SIDEBAR, button_hover_color=COLOR_CARD_HOVER
        )
        freq_menu.pack(fill="x", padx=16, pady=(0, 10))

        lbl_task_status = ctk.CTkLabel(
            card, text="", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold")
        )
        lbl_task_status.pack(anchor="w", padx=16, pady=(0, 8))

        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.pack(fill="x", padx=16, pady=(0, 12))

        def _enable():
            freq = "WEEKLY" if "Semanal" in freq_menu.get() else "DAILY"
            ok, msg = opt.configure_scheduled_task(enable=True, frequency=freq)
            if ok:
                lbl_task_status.configure(text=f"✓ {msg}", text_color=COLOR_SUCCESS)
                self.log(f"[✓] Tarea programada configurada: {msg}")
            else:
                lbl_task_status.configure(text=f"⚠️ {msg}", text_color=COLOR_DANGER)

        def _disable():
            ok, msg = opt.configure_scheduled_task(enable=False)
            if ok:
                lbl_task_status.configure(text=f"✓ {msg}", text_color=COLOR_SUCCESS)
                self.log(f"[✓] {msg}")
            else:
                lbl_task_status.configure(text=f"⚠️ {msg}", text_color=COLOR_DANGER)

        btn_act = ctk.CTkButton(
            btn_box, text="Activar Tarea", height=30, width=120,
            fg_color=COLOR_BLUE, hover_color="#2563eb",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=_enable
        )
        btn_act.pack(side="left", padx=(0, 10))

        btn_deact = ctk.CTkButton(
            btn_box, text="Desactivar", height=30, width=100,
            fg_color=COLOR_DANGER, hover_color="#dc2626",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=_disable
        )
        btn_deact.pack(side="left")

    def export_report_action(self):
        target_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile="report_killcleaner.txt",
            filetypes=[("Archivos de texto (*.txt)", "*.txt"), ("Todos los archivos (*.*)", "*.*")],
            title="Guardar Reporte de Mantenimiento"
        )
        if not target_path:
            return

        log_text = self.log_area.get("1.0", "end").strip()
        stats = {
            "smart": self.lbl_smart_status.cget("text").replace("• Salud de Disco (SMART): ", ""),
            "disk_free": self.card_disk["val"].cget("text"),
            "ram_used": self.card_ram["val"].cget("text"),
            "trash": self.card_trash["val"].cget("text")
        }

        ok, msg = opt.export_maintenance_report(log_text, stats, target_path)
        if ok:
            self.log(f"[✓] Reporte guardado en: {target_path}")
            self._show_modal_alert("Reporte de Mantenimiento", "¡Reporte Exportado!", f"El informe de auditoría se guardó correctamente en:\n{target_path}", icon="📄", status_type="success")
        else:
            self.log(f"[x] Error al exportar reporte: {msg}")
            self._show_modal_alert("Reporte de Mantenimiento", "Error al Exportar", msg, icon="⚠️", status_type="warning")
