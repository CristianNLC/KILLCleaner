import os
import subprocess
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from ui.theme import *
from core.disk_analyzer import analyze_directory_top_items, format_size

class DiskVisualizerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Analizador de Espacio en Disco")
        self.geometry("780x560")
        self.minsize(700, 480)
        self.configure(fg_color=COLOR_BG_DARK)

        self._build_ui()

    def _build_ui(self):
        # 1. Cabecera y Selección
        header_frame = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, corner_radius=0)
        header_frame.pack(fill="x", padx=0, pady=0)

        lbl = ctk.CTkLabel(
            header_frame, text="📊 Inspector Visual de Espacio Ocupado",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        lbl.pack(side="left", padx=20, pady=15)

        self.btn_select = ctk.CTkButton(
            header_frame, text="Examinar Directorio...",
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            command=self._select_and_scan
        )
        self.btn_select.pack(side="right", padx=20, pady=15)

        # 2. Resumen Superior
        self.summary_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=8)
        self.summary_frame.pack(fill="x", padx=15, pady=10)

        self.lbl_path = ctk.CTkLabel(
            self.summary_frame, text="Ruta: Ninguna seleccionada",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=COLOR_TEXT_SECONDARY
        )
        self.lbl_path.pack(anchor="w", padx=15, pady=(8, 2))

        self.lbl_total = ctk.CTkLabel(
            self.summary_frame, text="Espacio total evaluado: --",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_TEXT_PRIMARY
        )
        self.lbl_total.pack(anchor="w", padx=15, pady=(0, 8))

        # 3. Lista con barras de progreso (Scrollable)
        self.scroll_list = ctk.CTkScrollableFrame(self, fg_color="#18191d", corner_radius=8)
        self.scroll_list.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def _select_and_scan(self):
        folder = filedialog.askdirectory(title="Selecciona unidad o carpeta a analizar")
        if not folder:
            return

        self.btn_select.configure(state="disabled")
        self.lbl_path.configure(text=f"Analizando: {folder} ...")
        self.lbl_total.configure(text="Calculando tamaños de directorios, por favor espera...")

        # Limpiar resultados previos
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        threading.Thread(target=self._run_scan_thread, args=(folder,), daemon=True).start()

    def _run_scan_thread(self, folder):
        total_sz, top_items = analyze_directory_top_items(folder, max_items=20)
        self.after(0, self._render_results, folder, total_sz, top_items)

    def _render_results(self, folder, total_sz, items):
        self.lbl_path.configure(text=f"Ruta: {folder}")
        self.lbl_total.configure(text=f"Total ocupado en la raíz: {format_size(total_sz)}")

        if not items:
            lbl_empty = ctk.CTkLabel(self.scroll_list, text="Directorio vacío o inaccesible.", text_color=COLOR_TEXT_SECONDARY)
            lbl_empty.pack(pady=20)
            self.btn_select.configure(state="normal")
            return

        for it in items:
            row = ctk.CTkFrame(self.scroll_list, fg_color=COLOR_CARD, corner_radius=6)
            row.pack(fill="x", padx=5, pady=4)

            icon = "📁" if it["is_dir"] else "📄"
            name_text = f"{icon} {it['name']}"
            if len(name_text) > 42:
                name_text = name_text[:39] + "..."

            lbl_name = ctk.CTkLabel(
                row, text=name_text, width=280, anchor="w",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")
            )
            lbl_name.pack(side="left", padx=10, pady=8)

            # Barra visual de uso
            bar = ctk.CTkProgressBar(row, width=180, height=10, fg_color="#121316", progress_color="#eab308")
            bar.set(it["percent"] / 100.0)
            bar.pack(side="left", padx=10, pady=8)

            lbl_stat = ctk.CTkLabel(
                row, text=f"{it['size_formatted']} ({it['percent']:.1f}%)",
                width=110, anchor="e", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_SECONDARY
            )
            lbl_stat.pack(side="left", padx=5, pady=8)

            # Botón Explorar
            target_p = it["path"]
            btn_open = ctk.CTkButton(
                row, text="Abrir", width=55, height=24,
                fg_color=COLOR_SIDEBAR, hover_color=COLOR_CARD_HOVER,
                font=ctk.CTkFont(size=11),
                command=lambda p=target_p: self._open_in_explorer(p)
            )
            btn_open.pack(side="right", padx=10, pady=6)

        self.btn_select.configure(state="normal")

    def _open_in_explorer(self, path):
        """Abre la ruta o selecciona el archivo en el explorador de Windows."""
        try:
            if os.path.isfile(path):
                subprocess.run(f'explorer /select,"{os.path.abspath(path)}"', shell=True)
            elif os.path.isdir(path):
                subprocess.run(f'explorer "{os.path.abspath(path)}"', shell=True)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el elemento: {e}")
