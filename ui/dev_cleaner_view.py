import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from ui.theme import (
    COLOR_BG_DARK, COLOR_SIDEBAR, COLOR_CARD, COLOR_CARD_HOVER,
    COLOR_ACCENT, COLOR_ACCENT_HOVER, COLOR_DANGER, COLOR_DANGER_HOVER,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, FONT_FAMILY
)
from core.dev_cleaner import (
    get_dev_cache_targets,
    scan_path_size,
    purge_dev_target,
    purge_pycache_recursive
)
from core.disk_analyzer import format_size


class DevCleanerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Limpiador de Paquetes y Entornos de Desarrollo")
        self.geometry("820x560")
        self.minsize(740, 480)
        self.configure(fg_color=COLOR_BG_DARK)

        self.targets = {}
        self.action_buttons = []
        self._build_ui()
        self._refresh_targets()

    def _build_ui(self):
        # Cabecera
        header = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, corner_radius=0)
        header.pack(fill="x")

        lbl = ctk.CTkLabel(
            header,
            text="🛠️ Cachés de Desarrollo y Gestores de Paquetes",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        lbl.pack(side="left", padx=20, pady=15)

        self.btn_clean_all = ctk.CTkButton(
            header,
            text="Purgar Todo",
            width=110,
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            command=self._clean_all_targets
        )
        self.btn_clean_all.pack(side="right", padx=15, pady=15)

        # Sección PyCache
        pycache_card = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=8)
        pycache_card.pack(fill="x", padx=15, pady=(15, 10))

        lbl_py = ctk.CTkLabel(
            pycache_card,
            text="Python: Purgar __pycache__ y .pyc huérfanos de un proyecto",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        lbl_py.pack(side="left", padx=15, pady=10)

        self.btn_pycache = ctk.CTkButton(
            pycache_card,
            text="Examinar Proyecto...",
            width=140,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._clean_project_pycache
        )
        self.btn_pycache.pack(side="right", padx=15, pady=10)

        # Barra de estado inferior
        self.status_lbl = ctk.CTkLabel(
            self, text="Listo.",
            font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_SECONDARY
        )
        self.status_lbl.pack(fill="x", padx=20, pady=(0, 5))

        # Lista de Targets
        self.scroll_list = ctk.CTkScrollableFrame(self, fg_color="#18191d", corner_radius=8)
        self.scroll_list.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def _set_ui_state(self, state: str):
        self.btn_clean_all.configure(state=state)
        self.btn_pycache.configure(state=state)
        for btn in self.action_buttons:
            try:
                btn.configure(state=state)
            except Exception:
                pass

    def _refresh_targets(self):
        self.action_buttons.clear()
        for w in self.scroll_list.winfo_children():
            w.destroy()

        self.targets = get_dev_cache_targets()
        if not self.targets:
            lbl = ctk.CTkLabel(
                self.scroll_list,
                text="No se detectaron cachés de desarrollo conocidas en el sistema.",
                text_color=COLOR_TEXT_SECONDARY
            )
            lbl.pack(pady=30)
            return

        lbl_wait = ctk.CTkLabel(
            self.scroll_list,
            text="Calculando uso de espacio en cachés de paquetes...",
            text_color=COLOR_TEXT_SECONDARY
        )
        lbl_wait.pack(pady=20)
        self.status_lbl.configure(text="Calculando tamaños de carpetas...")

        threading.Thread(target=self._calculate_sizes_thread, daemon=True).start()

    def _calculate_sizes_thread(self):
        data = []
        for name, path in self.targets.items():
            b, count = scan_path_size(path)
            data.append({"name": name, "path": path, "bytes": b, "files": count})
        self.after(0, self._render_targets, data)

    def _render_targets(self, data):
        self.action_buttons.clear()
        for w in self.scroll_list.winfo_children():
            w.destroy()

        self.status_lbl.configure(text="Listo.")

        for item in data:
            row = ctk.CTkFrame(self.scroll_list, fg_color=COLOR_CARD, corner_radius=6)
            row.pack(fill="x", padx=5, pady=4)

            info_col = ctk.CTkFrame(row, fg_color="transparent")
            info_col.pack(side="left", fill="x", expand=True, padx=12, pady=8)

            lbl_title = ctk.CTkLabel(
                info_col,
                text=f"📦 {item['name']}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                anchor="w"
            )
            lbl_title.pack(fill="x")

            lbl_sub = ctk.CTkLabel(
                info_col,
                text=f"{item['path']} — ({item['files']} archivos)",
                font=ctk.CTkFont(size=10),
                text_color=COLOR_TEXT_SECONDARY,
                anchor="w"
            )
            lbl_sub.pack(fill="x")

            lbl_size = ctk.CTkLabel(
                row,
                text=format_size(item["bytes"]),
                width=90,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#eab308"
            )
            lbl_size.pack(side="left", padx=10)

            target_path = item["path"]
            btn_clean = ctk.CTkButton(
                row,
                text="Vaciar",
                width=75,
                height=26,
                fg_color=COLOR_SIDEBAR,
                hover_color=COLOR_DANGER_HOVER,
                command=lambda p=target_path: self._clean_single_target(p)
            )
            btn_clean.pack(side="right", padx=12, pady=8)
            self.action_buttons.append(btn_clean)

    # --- Operaciones Asíncronas en Hilos de Fondo ---

    def _clean_single_target(self, path):
        if not messagebox.askyesno("Confirmar", f"¿Eliminar la caché en:\n{path}?"):
            return

        self._set_ui_state("disabled")
        self.status_lbl.configure(text=f"Purgando: {path} ... por favor espera")
        threading.Thread(target=self._worker_single_target, args=(path,), daemon=True).start()

    def _worker_single_target(self, path):
        try:
            b, f = purge_dev_target(path)
            self.after(0, self._on_single_complete, b, f, None)
        except Exception as e:
            self.after(0, self._on_single_complete, 0, 0, str(e))

    def _on_single_complete(self, b, f, err):
        self._set_ui_state("normal")
        self.status_lbl.configure(text="Listo.")
        if err:
            messagebox.showwarning("Aviso", f"Limpieza finalizada con advertencias: {err}")
        else:
            messagebox.showinfo("Listo", f"Se liberaron {format_size(b)} ({f} archivos eliminados).")
        self._refresh_targets()

    def _clean_all_targets(self):
        if not messagebox.askyesno("Confirmar", "¿Deseas vaciar todas las cachés de paquetes detectadas?"):
            return

        self._set_ui_state("disabled")
        self.status_lbl.configure(text="Purgando todas las cachés en segundo plano...")
        threading.Thread(target=self._worker_all_targets, daemon=True).start()

    def _worker_all_targets(self):
        total_b, total_f = 0, 0
        err = None
        try:
            for path in list(self.targets.values()):
                b, f = purge_dev_target(path)
                total_b += b
                total_f += f
        except Exception as e:
            err = str(e)
        self.after(0, self._on_all_complete, total_b, total_f, err)

    def _on_all_complete(self, total_b, total_f, err):
        self._set_ui_state("normal")
        self.status_lbl.configure(text="Listo.")
        if err:
            messagebox.showwarning("Aviso", f"Limpieza completada con advertencias: {err}")
        else:
            messagebox.showinfo(
                "Listo",
                f"Limpieza global completada: {format_size(total_b)} liberados ({total_f} archivos eliminados)."
            )
        self._refresh_targets()

    def _clean_project_pycache(self):
        folder = filedialog.askdirectory(title="Selecciona la carpeta de tu proyecto Python")
        if not folder:
            return

        self._set_ui_state("disabled")
        self.status_lbl.configure(text=f"Buscando __pycache__ en {folder}...")
        threading.Thread(target=self._worker_project_pycache, args=(folder,), daemon=True).start()

    def _worker_project_pycache(self, folder):
        try:
            dirs_c, files_c = purge_pycache_recursive(folder)
            self.after(0, self._on_pycache_complete, dirs_c, files_c, None)
        except Exception as e:
            self.after(0, self._on_pycache_complete, 0, 0, str(e))

    def _on_pycache_complete(self, dirs_c, files_c, err):
        self._set_ui_state("normal")
        self.status_lbl.configure(text="Listo.")
        if err:
            messagebox.showerror("Error", f"Fallo al limpiar el proyecto: {err}")
        else:
            messagebox.showinfo(
                "PyCache Purgado",
                f"Se eliminaron {dirs_c} carpetas '__pycache__' y {files_c} archivos compilados (.pyc)."
            )