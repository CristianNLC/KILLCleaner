"""Prueba rápida de la GUI: crear, abrir modales y cerrar sin excepciones."""
import os
import shutil
import sys
import tempfile

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import core.config as cfg

if os.environ.get("KILLCLEANER_SKIP_GUI") == "1":
    print("GUI omitida: no hay entorno gráfico disponible.")
    sys.exit(0)

base = tempfile.mkdtemp(prefix="kc_gui_")
cfg.config_path = lambda: os.path.join(base, "config.json")

from ui.main_window import CleanerWindow  # noqa: E402

app = CleanerWindow()
app.update()

for opener in (
    "open_user_manual",
    "open_feedback_modal",
    "open_donation_modal",
    "open_exclusions_modal",
    "open_large_files",
    "open_audit_history",
    "open_boot_diagnostics",
):
    getattr(app, opener)()
    app.update()
    tops = [w for w in app.winfo_children() if w.winfo_class() == "Toplevel"]
    for top in tops:
        top.destroy()
    app.update()

app._on_close()
shutil.rmtree(base, ignore_errors=True)
print("GUI OK: ventana y modales creados y cerrados sin excepciones")
