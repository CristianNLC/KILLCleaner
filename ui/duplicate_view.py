import os
import subprocess
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from ui.theme import *
from core.duplicate_finder import find_duplicate_files
from core.disk_analyzer import format_size
from core.recycle import move_to_recycle_bin
import core.audit as audit

class DuplicateFinderWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Buscador de Archivos Duplicados (SHA-256)")
        self.geometry("860x580")
        self.minsize(760, 480)
        self.configure(fg_color=COLOR_BG_DARK)

        self._build_ui()

    def _build_ui(self):
        # Cabecera
        header = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, corner_radius=0)
        header.pack(fill="x")

        lbl = ctk.CTkLabel(
            header, text="🔍 Detección de Archivos Duplicados",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        lbl.pack(side="left", padx=20, pady=15)

        self.btn_select = ctk.CTkButton(
            header, text="Examinar y Analizar...",
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            command=self._choose_and_scan
        )
        self.btn_select.pack(side="right", padx=20, pady=15)

        # Barra de estado
        self.card_info = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=8)
        self.card_info.pack(fill="x", padx=15, pady=10)

        self.lbl_status = ctk.CTkLabel(
            self.card_info, text="Selecciona una carpeta para buscar archivos repetidos.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=COLOR_TEXT_SECONDARY
        )
        self.lbl_status.pack(anchor="w", padx=15, pady=8)

        # Área de resultados (Scrollable)
        self.scroll_list = ctk.CTkScrollableFrame(self, fg_color="#18191d", corner_radius=8)
        self.scroll_list.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def _choose_and_scan(self):
        folder = filedialog.askdirectory(title="Selecciona la carpeta a escanear")
        if not folder:
            return

        self.btn_select.configure(state="disabled")
        self.lbl_status.configure(text=f"Analizando duplicados en: {folder} (Calculando hashes SHA-256)...")

        for w in self.scroll_list.winfo_children():
            w.destroy()

        threading.Thread(target=self._run_scan_thread, args=(folder,), daemon=True).start()

    def _run_scan_thread(self, folder):
        duplicates = find_duplicate_files(folder)
        self.after(0, self._render_duplicates, folder, duplicates)

    def _render_duplicates(self, folder, duplicates: dict):
        self.btn_select.configure(state="normal")
        
        if not duplicates:
            self.lbl_status.configure(text=f"No se encontraron archivos duplicados en: {folder}")
            lbl = ctk.CTkLabel(self.scroll_list, text="Directorio limpio: Sin duplicados detectados.", text_color=COLOR_TEXT_SECONDARY)
            lbl.pack(pady=30)
            return

        total_groups = len(duplicates)
        total_dup_files = sum(len(paths) - 1 for paths in duplicates.values())
        self.lbl_status.configure(text=f"Se detectaron {total_groups} grupos de duplicados ({total_dup_files} archivos repetidos).")

        for sha, paths in duplicates.items():
            # Obtener peso del primer archivo accesible
            size_txt = "Desconocido"
            for p in paths:
                if os.path.exists(p):
                    size_txt = format_size(os.path.getsize(p))
                    break

            group_box = ctk.CTkFrame(self.scroll_list, fg_color=COLOR_CARD, corner_radius=6)
            group_box.pack(fill="x", padx=5, pady=6)

            # Encabezado del grupo con Hash y Peso
            head_lbl = ctk.CTkLabel(
                group_box, text=f"Hash: {sha[:16]}... | Tamaño por copia: {size_txt} ({len(paths)} copias)",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color="#eab308"
            )
            head_lbl.pack(anchor="w", padx=10, pady=(6, 4))

            for path in paths:
                row = ctk.CTkFrame(group_box, fg_color="#1a1c23", corner_radius=4)
                row.pack(fill="x", padx=10, pady=2)

                lbl_p = ctk.CTkLabel(row, text=path, font=ctk.CTkFont(family="Consolas", size=10), text_color=COLOR_TEXT_PRIMARY, anchor="w")
                lbl_p.pack(side="left", fill="x", expand=True, padx=8, pady=4)

                btn_open = ctk.CTkButton(
                    row, text="Ver", width=45, height=22,
                    fg_color=COLOR_SIDEBAR, hover_color=COLOR_CARD_HOVER, font=ctk.CTkFont(size=10),
                    command=lambda p=path: self._open_location(p)
                )
                btn_open.pack(side="right", padx=4, pady=4)

                btn_del = ctk.CTkButton(
                    row, text="Eliminar", width=65, height=22,
                    fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER, font=ctk.CTkFont(size=10),
                    command=lambda p=path, r=row: self._delete_file(p, r)
                )
                btn_del.pack(side="right", padx=4, pady=4)

    def _open_location(self, path):
        try:
            if os.path.exists(path):
                subprocess.run(f'explorer /select,"{os.path.abspath(path)}"', shell=True)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo: {e}")

    def _delete_file(self, path, row_widget):
        if not messagebox.askyesno(
            "Mover a la Papelera",
            "¿Mover este archivo duplicado a la Papelera de reciclaje?\n\n"
            f"{path}\n\n"
            "Podrás restaurarlo desde la Papelera si te equivocas.",
        ):
            return

        ok, msg = move_to_recycle_bin(path)
        if ok:
            audit.log_action("recycle_duplicate", target=path, files=1)
            row_widget.destroy()
            messagebox.showinfo("Listo", msg)
        else:
            audit.log_action(
                "recycle_duplicate", target=path, result="error", details={"message": msg}
            )
            messagebox.showerror(
                "No se pudo reciclar",
                f"{msg}\n\nEl archivo NO se ha eliminado.",
            )
