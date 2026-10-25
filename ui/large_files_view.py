"""Buscador de archivos grandes con envío seguro a la Papelera."""

import os
import subprocess
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox

from ui.theme import *
from core.app_paths import system_drive
from core.disk_analyzer import format_size
from core.large_files import find_large_files
from core.recycle import move_to_recycle_bin
import core.audit as audit

_THRESHOLDS = {
    "50 MB": 50 * 1024 * 1024,
    "100 MB": 100 * 1024 * 1024,
    "500 MB": 500 * 1024 * 1024,
    "1 GB": 1024 * 1024 * 1024,
    "5 GB": 5 * 1024 * 1024 * 1024,
}


class LargeFilesWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Archivos Grandes")
        self.geometry("920x620")
        self.minsize(780, 500)
        self.configure(fg_color=COLOR_BG_DARK)

        self._cancel_event = threading.Event()
        self._items = []

        self.transient(parent)
        self._build_ui()
        self._refresh_summary()
        self.after(120, self._safe_grab)

    def _safe_grab(self):
        try:
            self.grab_set()
        except Exception:
            pass

    def _alive(self):
        try:
            return bool(self.winfo_exists())
        except Exception:
            return False

    def destroy(self):
        self._cancel_event.set()
        super().destroy()

    # --- INTERFAZ ---
    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="🐘 Archivos Grandes",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        ).pack(side="left", padx=20, pady=15)

        self.btn_cancel = ctk.CTkButton(
            header, text="✖ Cancelar", width=100,
            fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER,
            state="disabled", command=self._cancel_scan,
        )
        self.btn_cancel.pack(side="right", padx=(0, 20), pady=15)

        self.btn_scan = ctk.CTkButton(
            header, text="🔍 Analizar", width=110,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            command=self._start_scan,
        )
        self.btn_scan.pack(side="right", padx=(0, 8), pady=15)

        controls = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=8)
        controls.pack(fill="x", padx=15, pady=(10, 0))

        row = ctk.CTkFrame(controls, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=10)

        self.entry_folder = ctk.CTkEntry(
            row, placeholder_text="Carpeta o unidad a analizar",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
        )
        self.entry_folder.pack(side="left", fill="x", expand=True)
        self.entry_folder.insert(0, system_drive() + os.sep)

        ctk.CTkButton(
            row, text="Examinar", width=90,
            fg_color=COLOR_SIDEBAR, hover_color=COLOR_CARD_HOVER,
            command=self._choose_folder,
        ).pack(side="left", padx=(8, 0))

        self.opt_threshold = ctk.CTkOptionMenu(
            row, values=list(_THRESHOLDS), width=100,
            fg_color=COLOR_SIDEBAR, button_color=COLOR_CARD_HOVER,
            command=lambda _value: self._refresh_summary(),
        )
        self.opt_threshold.set("100 MB")
        self.opt_threshold.pack(side="left", padx=(8, 0))

        self.lbl_status = ctk.CTkLabel(
            self, text="Elige una carpeta y un tamaño mínimo. Solo se leen metadatos.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        self.lbl_status.pack(fill="x", padx=20, pady=(8, 4))

        self.scroll_list = ctk.CTkScrollableFrame(self, fg_color="#18191d", corner_radius=8)
        self.scroll_list.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        self.lbl_summary = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY, anchor="w",
        )
        self.lbl_summary.pack(fill="x", padx=20, pady=(0, 12))

    def _choose_folder(self):
        folder = filedialog.askdirectory(title="Selecciona la carpeta o unidad")
        if folder:
            self.entry_folder.delete(0, "end")
            self.entry_folder.insert(0, folder)

    # --- ANÁLISIS ---
    def _threshold_bytes(self):
        return _THRESHOLDS.get(self.opt_threshold.get(), 100 * 1024 * 1024)

    def _start_scan(self):
        folder = self.entry_folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("Carpeta no válida", "Selecciona una carpeta o unidad existente.")
            return

        self._cancel_event.clear()
        self._set_running(True)
        self._clear_rows()
        self.lbl_summary.configure(text="")
        self.lbl_status.configure(
            text=f"Buscando archivos de más de {self.opt_threshold.get()} en {folder}..."
        )

        threading.Thread(
            target=self._scan_thread,
            args=(folder, self._threshold_bytes(), self._cancel_event),
            daemon=True,
        ).start()

    def _scan_thread(self, folder, min_bytes, cancel_event):
        results = find_large_files(folder, min_bytes, cancel_event=cancel_event)
        cancelled = cancel_event.is_set()
        try:
            self.after(0, self._finish_scan, folder, results, cancelled)
        except Exception:
            pass

    def _finish_scan(self, folder, results, cancelled):
        if not self._alive():
            return
        self._set_running(False)
        if cancelled:
            self.lbl_status.configure(text="Análisis cancelado por el usuario.")
            ctk.CTkLabel(
                self.scroll_list,
                text="Análisis cancelado. No se modificó ningún archivo.",
                text_color=COLOR_TEXT_SECONDARY,
            ).pack(pady=30)
            return

        if not results:
            self.lbl_status.configure(text=f"No se encontraron archivos de más de {self.opt_threshold.get()}.")
            ctk.CTkLabel(
                self.scroll_list,
                text="Sin coincidencias en la carpeta seleccionada.",
                text_color=COLOR_TEXT_SECONDARY,
            ).pack(pady=30)
            return

        self._items = list(results)
        self.lbl_status.configure(text=f"Se encontraron {len(results)} archivos en {folder}.")
        for item in results:
            self._add_row(item)
        self._refresh_summary()

    def _add_row(self, item):
        row = ctk.CTkFrame(self.scroll_list, fg_color=COLOR_CARD, corner_radius=6)
        row.pack(fill="x", padx=5, pady=3)

        ctk.CTkLabel(
            row, text=format_size(item["size"]), width=90,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_AMBER, anchor="w",
        ).pack(side="left", padx=(10, 6), pady=6)

        ctk.CTkLabel(
            row, text=item["path"], font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_PRIMARY, anchor="w",
        ).pack(side="left", fill="x", expand=True, padx=4, pady=6)

        ctk.CTkButton(
            row, text="Papelera", width=72, height=24,
            fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER,
            font=ctk.CTkFont(size=10),
            command=lambda it=item, widget=row: self._delete_file(it, widget),
        ).pack(side="right", padx=4, pady=4)

        ctk.CTkButton(
            row, text="Ver", width=45, height=24,
            fg_color=COLOR_SIDEBAR, hover_color=COLOR_CARD_HOVER,
            font=ctk.CTkFont(size=10),
            command=lambda path=item["path"]: self._open_location(path),
        ).pack(side="right", padx=4, pady=4)

    def _delete_file(self, item, row_widget):
        path = item["path"]
        if not os.path.exists(path):
            messagebox.showwarning("Archivo no encontrado", "El archivo ya no existe en esa ruta.")
            row_widget.destroy()
            return

        if not messagebox.askyesno(
            "Mover a la Papelera",
            "¿Mover este archivo a la Papelera de reciclaje?\n\n"
            f"{path}\n\n"
            f"Tamaño: {format_size(item['size'])}\n\n"
            "Podrás restaurarlo desde la Papelera si te equivocas.",
        ):
            return

        ok, msg = move_to_recycle_bin(path)
        if ok:
            audit.log_action("recycle_large_file", target=path, bytes_freed=item["size"], files=1)
            row_widget.destroy()
            self._items = [current for current in self._items if current["path"] != path]
            self._refresh_summary()
            messagebox.showinfo("Listo", msg)
        else:
            audit.log_action(
                "recycle_large_file", target=path, result="error", details={"message": msg}
            )
            messagebox.showerror(
                "No se pudo reciclar",
                f"{msg}\n\nEl archivo NO se ha eliminado.",
            )

    def _open_location(self, path):
        try:
            if os.path.exists(path):
                subprocess.run(f'explorer /select,"{os.path.abspath(path)}"', shell=True)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo abrir la ubicación: {exc}")

    # --- ESTADO ---
    def _set_running(self, running):
        self.btn_scan.configure(state="disabled" if running else "normal")
        self.btn_cancel.configure(state="normal" if running else "disabled")
        self.opt_threshold.configure(state="disabled" if running else "normal")

    def _cancel_scan(self):
        if self._cancel_event.is_set():
            return
        self._cancel_event.set()
        self.btn_cancel.configure(state="disabled")
        self.lbl_status.configure(text="Cancelando el análisis...")

    def _clear_rows(self):
        for widget in self.scroll_list.winfo_children():
            widget.destroy()
        self._items = []

    def _refresh_summary(self):
        total = len(self._items)
        if not total:
            self.lbl_summary.configure(text="")
            return
        size = sum(item["size"] for item in self._items)
        self.lbl_summary.configure(
            text=f"{total} archivos listados · {format_size(size)} en total"
        )
