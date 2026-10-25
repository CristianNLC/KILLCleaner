"""Pruebas del paquete de seguridad de datos (A) de KILLCleaner.

No toca la configuración real: redirige config y auditoría a carpetas temporales.
"""
import json
import os
import shutil
import sys
import tempfile

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import core.config as cfg
import core.audit as audit
from core.cleaner import clean_directory, is_safe_target, scan_target
from core.recycle import move_to_recycle_bin

ok, fail = [], []


def check(name, cond, extra=""):
    (ok if cond else fail).append(f"{name} {extra}")


base = tempfile.mkdtemp(prefix="kc_safety_")

# --- 1. Configuración ---
cfg.config_path = lambda: os.path.join(base, "config.json")

defaults = cfg.load_config()
check("config: tema por defecto", defaults["theme"] == "Dark")
check("config: sin exclusiones al inicio", defaults["exclusions"] == [])
check("config: restore point activo por defecto", defaults["restore_point_before_clean"] is True)

check("config: guarda tema", cfg.set_value("theme", "Light"))
cfg.set_value("exclusions", [])
folder_a = os.path.join(base, "carpeta_a")
folder_b = os.path.join(base, "carpeta_b")
os.makedirs(folder_a)
os.makedirs(folder_b)

ok_add, msg_add = cfg.add_exclusion(folder_a)
check("config: añade exclusión", ok_add, msg_add)
check("config: no duplica", cfg.add_exclusion(folder_a)[0] is False)
check("config: tema se conserva", cfg.get_value("theme") == "Light")
check("config: exclusión persistida", cfg.get_exclusions() == [os.path.abspath(folder_a)])
check("config: rechaza inexistente", cfg.add_exclusion(os.path.join(base, "nope"))[0] is False)
check("config: rechaza raíz de unidad", cfg.add_exclusion("C:\\")[0] is False)
check("config: elimina exclusión", cfg.remove_exclusion(folder_a)[0] is True)
check("config: lista vacía tras eliminar", cfg.get_exclusions() == [])

with open(cfg.config_path(), "w", encoding="utf-8") as f:
    f.write("{ esto no es json")
check("config: JSON dañado no rompe", cfg.load_config()["theme"] == "Dark")

# --- 2. Auditoría ---
audit.logs_dir = lambda: os.path.join(base, "logs")
audit.ensure_dir = lambda p: (os.makedirs(p, exist_ok=True) or p)

check("audit: escribe", audit.log_action("clean_temp", target="x", bytes_freed=2048, files=2, dry_run=True))
check("audit: escribe error", audit.log_action("recycle_duplicate", target="y", result="error", details={"message": "boom"}))
with open(audit.audit_path(), encoding="utf-8") as f:
    lines = [json.loads(line) for line in f if line.strip()]
check("audit: dos entradas", len(lines) == 2, f"(={len(lines)})")
check("audit: bytes correctos", lines[0]["bytes"] == 2048)
check("audit: dry_run marcado", lines[0]["dry_run"] is True)
check("audit: resultado error", lines[1]["result"] == "error")
check("audit: detalles", lines[1]["details"]["message"] == "boom")
check("audit: timestamp", "T" in lines[0]["ts"])

# --- 3. Papelera de reciclaje ---
sample = os.path.join(os.environ["TEMP"], f"kc_recycle_{os.getpid()}.tmp")
with open(sample, "wb") as f:
    f.write(b"basura de prueba")
rec_ok, rec_msg = move_to_recycle_bin(sample)
check("recycle: mueve a papelera", rec_ok, rec_msg)
check("recycle: archivo ya no está", not os.path.exists(sample))
check("recycle: archivo inexistente falla", move_to_recycle_bin(sample)[0] is False)

# --- 4. Rutas protegidas ---
check("protegida: C:\\", is_safe_target("C:\\") is False)
check("protegida: C:\\Windows", is_safe_target("C:\\Windows") is False)
check("protegida: System32", is_safe_target(os.path.join(os.environ["SystemRoot"], "System32")) is False)
check("protegida: Program Files", is_safe_target(os.environ["ProgramFiles"]) is False)
check("protegida: USERPROFILE", is_safe_target(os.environ["USERPROFILE"]) is False)
check("protegida: Documentos", is_safe_target(os.path.join(os.environ["USERPROFILE"], "Documents")) is False)
check("protegida: Escritorio", is_safe_target(os.path.join(os.environ["USERPROFILE"], "Desktop")) is False)
check("protegida: $Recycle.Bin", is_safe_target("C:\\$Recycle.Bin") is False)
check("protegida: ruta inexistente", is_safe_target(os.path.join(base, "fantasma")) is False)
check("permitida: %TEMP%", is_safe_target(os.environ["TEMP"]) is True)

# --- 5. Exclusiones durante la limpieza ---
root = os.path.join(base, "tree")
keep = os.path.join(root, "keep")
sub = os.path.join(root, "sub")
for d in (root, keep, sub):
    os.makedirs(d, exist_ok=True)
targets = {
    os.path.join(root, "a.tmp"): 1024,
    os.path.join(keep, "b.tmp"): 1024,
    os.path.join(sub, "c.tmp"): 1024,
}
for path, size in targets.items():
    with open(path, "wb") as f:
        f.write(b"x" * size)

total_b, total_f = scan_target(root, exclusions=[keep])
check("scan: respeta exclusión (bytes)", total_b == 2048, f"(b={total_b})")
check("scan: respeta exclusión (archivos)", total_f == 2, f"(n={total_f})")

freed_b, freed_n = clean_directory(root, exclusions=[keep])
check("clean: borra lo permitido", freed_n == 2 and freed_b == 2048, f"({freed_n}, {freed_b})")
check("clean: conserva carpeta excluida", os.path.exists(os.path.join(keep, "b.tmp")))
check("clean: borra subcarpeta permitida", not os.path.exists(sub))
check("clean: raíz intacta", os.path.isdir(root))

blocked_b, blocked_n = clean_directory(keep, exclusions=[keep])
check("clean: no limpia objetivo excluido", (blocked_b, blocked_n) == (0, 0))
check("clean: archivo excluido intacto", os.path.exists(os.path.join(keep, "b.tmp")))

if os.environ.get("KILLCLEANER_SKIP_GUI") == "1":
    print("OK  :", len(ok))
    for item in fail:
        print("FALLO:", item)
    sys.exit(1 if fail else 0)

# --- 6. UI ---
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from ui.main_window import CleanerWindow  # noqa: E402

app = CleanerWindow()
app.update()
check("ui: casilla de restauración existe", hasattr(app, "chk_restore"))
check("ui: restauración marcada por defecto", app.chk_restore.get() == 1)
try:
    app.open_exclusions_modal()
    app.update()
    tops = [w for w in app.winfo_children() if w.winfo_class() == "Toplevel"]
    check("ui: modal de exclusiones abre", len(tops) >= 1)
    for t in tops:
        t.destroy()
except Exception as e:
    check("ui: modal de exclusiones abre", False, f"({e})")
app.destroy()

shutil.rmtree(base, ignore_errors=True)

print("OK  :", len(ok))
for item in fail:
    print("FALLO:", item)
sys.exit(1 if fail else 0)
