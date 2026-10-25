"""Historial de auditoría: consulta y exportación de logs/audit.jsonl."""

import csv
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox

from ui.theme import *
from core.disk_analyzer import format_size
import core.audit as audit

_MAX_ENTRIES = 2000
_MAX_ROWS = 400


def _fmt_ts(value):
    return str(value).replace("T", " ")[:19]


class AuditHistoryWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Historial de Auditoría")
        self.geometry("1000x640")
        self.minsize(860, 520)
        self.configure(fg_color=COLOR_BG_DARK)

        self._entries = []
        self._filtered = []

        self.transient(parent)
        self._build_ui()
        self.after(50, self._refresh)
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

    # --- INTERFAZ ---
    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header, text="📜 Historial de Auditoría",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        ).pack(side="left", padx=20, pady=15)

        self.btn_export = ctk.CTkButton(
            header, text="Exportar CSV", width=110,
            fg_color=COLOR_SUCCESS, hover_color="#16a34a",
            command=self._export_csv,
        )
        self.btn_export.pack(side="right", padx=(0, 20), pady=15)

        self.btn_refresh = ctk.CTkButton(
            header, text="Actualizar", width=100,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            command=self._refresh,
        )
        self.btn_refresh.pack(side="right", padx=(0, 8), pady=15)

        summary = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=8)
        summary.pack(fill="x", padx=15, pady=(10, 0))
        self.lbl_summary = ctk.CTkLabel(
            summary, text="Cargando historial...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY, anchor="w",
        )
        self.lbl_summary.pack(fill="x", padx=14, pady=10)

        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", padx=15, pady=8)

        self.entry_search = ctk.CTkEntry(
            filters, placeholder_text="Buscar en acción, objetivo o detalles...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
        )
        self.entry_search.pack(side="left", fill="x", expand=True)
        self.entry_search.bind("<KeyRelease>", lambda _event: self._apply_filters())

        self.opt_action = ctk.CTkOptionMenu(
            filters, values=["Todas"], width=170,
            fg_color=COLOR_SIDEBAR, button_color=COLOR_CARD_HOVER,
            command=lambda _value: self._apply_filters(),
        )
        self.opt_action.set("Todas")
        self.opt_action.pack(side="left", padx=(8, 0))

        table = ctk.CTkFrame(self, fg_color="#18191d", corner_radius=8)
        table.pack(fill="both", expand=True, padx=15, pady=(0, 8))

        header_row = ctk.CTkFrame(table, fg_color=COLOR_CARD, corner_radius=0)
        header_row.pack(fill="x")
        for text, width in (
            ("Fecha", 140), ("Acción", 150), ("Objetivo", 0),
            ("Tamaño", 80), ("Archivos", 60), ("Resultado", 90),
        ):
            label = ctk.CTkLabel(
                header_row, text=text, width=width, anchor="w",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=COLOR_TEXT_SECONDARY,
            )
            if width:
                label.pack(side="left", padx=8, pady=6)
            else:
                label.pack(side="left", fill="x", expand=True, padx=8, pady=6)

        self.scroll_rows = ctk.CTkScrollableFrame(table, fg_color="transparent", corner_radius=0)
        self.scroll_rows.pack(fill="both", expand=True)

        self.lbl_footer = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_SECONDARY, anchor="w",
        )
        self.lbl_footer.pack(fill="x", padx=20, pady=(0, 10))

    # --- CARGA ---
    def _refresh(self):
        if not self._alive():
            return
        self.btn_refresh.configure(state="disabled")
        self.lbl_summary.configure(text="Cargando historial...")
        threading.Thread(target=self._load_thread, daemon=True).start()

    def _load_thread(self):
        entries = audit.read_entries(limit=_MAX_ENTRIES)
        try:
            self.after(0, self._render, entries)
        except Exception:
            pass

    def _render(self, entries):
        if not self._alive():
            return
        self.btn_refresh.configure(state="normal")
        self._entries = entries

        actions = sorted({str(item.get("action", "")) for item in entries if item.get("action")})
        values = ["Todas"] + actions
        self.opt_action.configure(values=values)
        if self.opt_action.get() not in values:
            self.opt_action.set("Todas")

        self._apply_filters()

    def _apply_filters(self):
        query = self.entry_search.get().strip().lower()
        action = self.opt_action.get()

        filtered = []
        for item in self._entries:
            if action != "Todas" and str(item.get("action", "")) != action:
                continue
            if query:
                haystack = " ".join(
                    [
                        str(item.get("action", "")),
                        str(item.get("target", "")),
                        str(item.get("details", "")),
                        str(item.get("ts", "")),
                    ]
                ).lower()
                if query not in haystack:
                    continue
            filtered.append(item)

        self._filtered = filtered
        self._draw_rows(filtered)

        totals = audit.summarize(filtered)
        self.lbl_summary.configure(
            text=(
                f"{totals['count']} acciones · "
                f"{format_size(totals['bytes'])} liberados · "
                f"{totals['files']} archivos procesados"
            )
        )
        self.lbl_footer.configure(
            text=(
                f"Mostrando {min(len(filtered), _MAX_ROWS)} de {len(filtered)} entradas "
                f"(historial cargado: {len(self._entries)})."
            )
        )

    def _draw_rows(self, entries):
        for widget in self.scroll_rows.winfo_children():
            widget.destroy()

        if not entries:
            ctk.CTkLabel(
                self.scroll_rows,
                text="No hay registros que coincidan con el filtro.",
                text_color=COLOR_TEXT_SECONDARY,
            ).pack(pady=30)
            return

        for index, item in enumerate(entries[:_MAX_ROWS]):
            background = COLOR_CARD if index % 2 == 0 else "#1d1f27"
            row = ctk.CTkFrame(self.scroll_rows, fg_color=background, corner_radius=0)
            row.pack(fill="x")

            result = str(item.get("result", "ok"))
            result_color = COLOR_SUCCESS if result == "ok" else COLOR_DANGER
            mode = "Sim." if item.get("dry_run") else "Real"

            values = [
                (_fmt_ts(item.get("ts", "")), 140, COLOR_TEXT_SECONDARY),
                (str(item.get("action", ""))[:22], 150, COLOR_ACCENT),
                (str(item.get("target", "")), 0, COLOR_TEXT_PRIMARY),
                (format_size(item.get("bytes", 0)), 80, COLOR_TEXT_PRIMARY),
                (str(item.get("files", 0)), 60, COLOR_TEXT_SECONDARY),
                (f"{result} · {mode}", 90, result_color),
            ]
            for text, width, color in values:
                label = ctk.CTkLabel(
                    row, text=text, width=width, anchor="w",
                    font=ctk.CTkFont(family="Consolas", size=10),
                    text_color=color,
                )
                if width:
                    label.pack(side="left", padx=8, pady=3)
                else:
                    label.pack(side="left", fill="x", expand=True, padx=8, pady=3)

    # --- EXPORTACIÓN ---
    def _export_csv(self):
        if not self._filtered:
            messagebox.showinfo("Sin datos", "No hay entradas para exportar con el filtro actual.")
            return

        target = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="historial_killcleaner.csv",
            filetypes=[("CSV compatible con Excel", "*.csv"), ("Todos los archivos", "*.*")],
            title="Guardar historial de auditoría",
        )
        if not target:
            return

        try:
            with open(target, "w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle, delimiter=";")
                writer.writerow(
                    ["Fecha", "Acción", "Objetivo", "Bytes", "Archivos", "Simulación", "Resultado", "Detalles"]
                )
                for item in self._filtered:
                    writer.writerow(
                        [
                            item.get("ts", ""),
                            item.get("action", ""),
                            item.get("target", ""),
                            item.get("bytes", 0),
                            item.get("files", 0),
                            "Sí" if item.get("dry_run") else "No",
                            item.get("result", "ok"),
                            item.get("details", ""),
                        ]
                    )
        except OSError as exc:
            messagebox.showerror("Error al exportar", f"No se pudo guardar el CSV:\n{exc}")
            return

        audit.log_action("export_audit_csv", target=target, files=len(self._filtered))
        messagebox.showinfo(
            "Historial exportado",
            f"Se guardaron {len(self._filtered)} entradas en:\n{target}\n\n"
            "El archivo usa punto y coma como separador para abrirse bien en Excel.",
        )
