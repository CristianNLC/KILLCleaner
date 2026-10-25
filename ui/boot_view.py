"""Diagnóstico de arranque: duración de los últimos inicios de Windows."""

import threading

import customtkinter as ctk

from ui.theme import *
from core.boot_diagnostics import format_duration, get_boot_history, summarize


def _fmt_time(value):
    return str(value).replace("T", " ")[:19]


class BootDiagnosticsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Diagnóstico de Arranque")
        self.geometry("820x560")
        self.minsize(700, 460)
        self.configure(fg_color=COLOR_BG_DARK)

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

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header, text="⏱️ Diagnóstico de Arranque",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        ).pack(side="left", padx=20, pady=15)

        self.btn_refresh = ctk.CTkButton(
            header, text="Actualizar", width=100,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            command=self._refresh,
        )
        self.btn_refresh.pack(side="right", padx=20, pady=15)

        self.lbl_status = ctk.CTkLabel(
            self,
            text="Leyendo los últimos arranques registrados por Windows...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT_SECONDARY, anchor="w",
        )
        self.lbl_status.pack(fill="x", padx=20, pady=(10, 6))

        summary = ctk.CTkFrame(self, fg_color="transparent")
        summary.pack(fill="x", padx=15)

        self.cards = {}
        for key, title in (
            ("last", "Último arranque"),
            ("average", "Promedio"),
            ("min", "Más rápido"),
            ("max", "Más lento"),
        ):
            card = ctk.CTkFrame(summary, fg_color=COLOR_CARD, corner_radius=8)
            card.pack(side="left", fill="both", expand=True, padx=4, pady=4)
            ctk.CTkLabel(
                card, text=title,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=COLOR_TEXT_SECONDARY,
            ).pack(anchor="w", padx=12, pady=(8, 0))
            value = ctk.CTkLabel(
                card, text="—",
                font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
                text_color=COLOR_ACCENT,
            )
            value.pack(anchor="w", padx=12, pady=(2, 8))
            self.cards[key] = value

        table = ctk.CTkFrame(self, fg_color="#18191d", corner_radius=8)
        table.pack(fill="both", expand=True, padx=15, pady=(8, 8))

        header_row = ctk.CTkFrame(table, fg_color=COLOR_CARD, corner_radius=0)
        header_row.pack(fill="x")
        for text, width in (
            ("Fecha", 160), ("Arranque total", 130),
            ("Arranque principal", 150), ("Después del inicio de sesión", 190),
        ):
            ctk.CTkLabel(
                header_row, text=text, width=width, anchor="w",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=COLOR_TEXT_SECONDARY,
            ).pack(side="left", padx=10, pady=6)

        self.scroll_rows = ctk.CTkScrollableFrame(table, fg_color="transparent", corner_radius=0)
        self.scroll_rows.pack(fill="both", expand=True)

        self.lbl_footer = ctk.CTkLabel(
            self,
            text="Windows mide el arranque cuando el diagnóstico de rendimiento está activo. "
                 "Los tiempos incluyen el inicio de sesión y los programas de inicio.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_SECONDARY, anchor="w", wraplength=760, justify="left",
        )
        self.lbl_footer.pack(fill="x", padx=20, pady=(0, 12))

    def _refresh(self):
        if not self._alive():
            return
        self.btn_refresh.configure(state="disabled")
        self.lbl_status.configure(text="Leyendo el registro de eventos de Windows...")
        threading.Thread(target=self._load_thread, daemon=True).start()

    def _load_thread(self):
        result = get_boot_history(limit=15)
        try:
            self.after(0, self._render, result)
        except Exception:
            pass

    def _render(self, result):
        if not self._alive():
            return
        self.btn_refresh.configure(state="normal")

        for widget in self.scroll_rows.winfo_children():
            widget.destroy()

        if not result.get("ok"):
            self.lbl_status.configure(
                text=f"No se pudo leer el diagnóstico: {result.get('error', 'error desconocido')}",
                text_color=COLOR_DANGER,
            )
            for card in self.cards.values():
                card.configure(text="—")
            return

        events = result.get("events") or []
        if not events:
            self.lbl_status.configure(
                text="Windows no tiene eventos de arranque registrados en este equipo.",
                text_color=COLOR_AMBER,
            )
            for card in self.cards.values():
                card.configure(text="—")
            return

        totals = summarize(events)
        self.cards["last"].configure(text=format_duration(totals.get("last", 0)))
        self.cards["average"].configure(text=format_duration(totals.get("average", 0)))
        self.cards["min"].configure(text=format_duration(totals.get("min", 0)))
        self.cards["max"].configure(text=format_duration(totals.get("max", 0)))

        self.lbl_status.configure(
            text=f"Se encontraron {len(events)} arranques registrados.",
            text_color=COLOR_TEXT_SECONDARY,
        )

        for index, event in enumerate(events):
            background = COLOR_CARD if index % 2 == 0 else "#1d1f27"
            row = ctk.CTkFrame(self.scroll_rows, fg_color=background, corner_radius=0)
            row.pack(fill="x")

            values = [
                (_fmt_time(event.get("time", "")), 160, COLOR_TEXT_SECONDARY),
                (format_duration(event.get("boot_ms", 0)), 130, COLOR_TEXT_PRIMARY),
                (format_duration(event.get("main_path_ms", 0)), 150, COLOR_TEXT_PRIMARY),
                (format_duration(event.get("post_boot_ms", 0)), 190, COLOR_TEXT_PRIMARY),
            ]
            for text, width, color in values:
                ctk.CTkLabel(
                    row, text=text, width=width, anchor="w",
                    font=ctk.CTkFont(family="Consolas", size=10),
                    text_color=color,
                ).pack(side="left", padx=10, pady=3)
