"""Pruebas del paquete B: casillas reales, cancelación, geometría y unidad."""
import os
import shutil
import sys
import tempfile
import threading

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import core.config as cfg
from core.app_paths import system_drive
from core.cleaner import clean_directory, scan_target
from core.duplicate_finder import find_duplicate_files

ok, fail = [], []


def check(name, cond, extra=""):
    (ok if cond else fail).append(f"{name} {extra}")


base = tempfile.mkdtemp(prefix="kc_b_")
cfg.config_path = lambda: os.path.join(base, "config.json")

# --- 1. Unidad del sistema ---
drive = system_drive()
check("system_drive formato", len(drive) == 2 and drive[1] == ":" and drive[0].isalpha(), f"({drive})")
check("system_drive existe", os.path.isdir(drive + os.sep))

# --- 2. Cancelación ya solicitada ---
root = os.path.join(base, "tree")
os.makedirs(root)
for i in range(5):
    with open(os.path.join(root, f"f{i}.tmp"), "wb") as f:
        f.write(b"x" * 100)

ev = threading.Event()
ev.set()
check("scan cancelado devuelve cero", scan_target(root, cancel_event=ev) == (0, 0))
check("clean cancelado devuelve cero", clean_directory(root, cancel_event=ev) == (0, 0))
check("clean cancelado conserva archivos", len(os.listdir(root)) == 5, f"(={len(os.listdir(root))})")

# --- 3. Cancelación a mitad del recorrido ---
class CountingEvent:
    def __init__(self, after):
        self.calls = 0
        self.after = after

    def is_set(self):
        self.calls += 1
        return self.calls > self.after


partial_ev = CountingEvent(after=10)
b, n = scan_target(root, cancel_event=partial_ev)
check("scan cancelado a mitad devuelve parcial", 0 < n < 5, f"(n={n})")

# --- 4. Duplicados ---
ev2 = threading.Event()
ev2.set()
check("duplicados cancelado devuelve vacío", find_duplicate_files(root, cancel_event=ev2) == {})

dup_root = os.path.join(base, "dups")
os.makedirs(dup_root)
data = b"contenido duplicado" * 100
for name in ("a.bin", "b.bin"):
    with open(os.path.join(dup_root, name), "wb") as f:
        f.write(data)

dups = find_duplicate_files(dup_root, min_size_bytes=1)
check("duplicados normales funcionan", len(dups) == 1 and len(next(iter(dups.values()))) == 2)

if os.environ.get("KILLCLEANER_SKIP_GUI") == "1":
    print("OK  :", len(ok))
    for item in fail:
        print("FALLO:", item)
    sys.exit(1 if fail else 0)

# --- 5. UI: casillas, cancelar y geometría ---
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from ui.main_window import CleanerWindow  # noqa: E402

app = CleanerWindow()
app.update()
check("casilla temporales marcada", app.chk_temp.get() == 1)
check("casilla prefetch marcada", app.chk_prefetch.get() == 1)
check("targets por defecto", len(app._selected_targets()) >= 1, f"(={len(app._selected_targets())})")

app.chk_prefetch.deselect()
selected = app._selected_targets()
check("prefetch desmarcado se excluye", not any("Prefetch" in label for label in selected), f"({list(selected)})")

app.chk_temp.deselect()
check("sin áreas no hay targets", app._selected_targets() == {})

app.chk_temp.select()
app.chk_prefetch.select()

check("cancelar empieza deshabilitado", app.btn_cancel_task.cget("state") == "disabled")
app._set_task_running(True)
app.update()
check("cancelar se habilita al trabajar", app.btn_cancel_task.cget("state") == "normal")
app.cancel_current_task()
app.update()
check("cancelar activa el evento", app._cancel_event.is_set())
app._set_task_running(False)
app.update()
check("cancelar se deshabilita al terminar", app.btn_cancel_task.cget("state") == "disabled")

app.geometry("1000x650+30+40")
app.update()
app._save_window_geometry()
saved = cfg.get_value("window_geometry") or ""
check("geometría guardada", saved.startswith("1000x650"), f"(={saved})")
app.destroy()

app2 = CleanerWindow()
app2.update()
app2.update()
geom = app2.geometry()
check("geometría restaurada", geom.startswith("1000x650"), f"(={geom})")
check("métrica muestra unidad real", system_drive() in app2.card_disk["sub"].cget("text"), f"(={app2.card_disk['sub'].cget('text')})")
app2.destroy()

shutil.rmtree(base, ignore_errors=True)

print("OK  :", len(ok))
for item in fail:
    print("FALLO:", item)
sys.exit(1 if fail else 0)
