"""Pruebas de humo de KILLCleaner (no toca archivos del usuario)."""
import os
import sys
import tempfile
import shutil

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.cleaner import clean_directory, is_safe_target
from core.reporter import export_maintenance_report
import core.system_cleaner as sc

ok = []
fail = []

def check(name, cond, extra=""):
    (ok if cond else fail).append(f"{name} {extra}")

# 1. Rutas protegidas
check("bloquea C:\\", is_safe_target("C:\\") is False)
check("bloquea C:\\Windows", is_safe_target("C:\\Windows") is False)
check("bloquea USERPROFILE", is_safe_target(os.environ["USERPROFILE"]) is False)
check("permite %TEMP%", is_safe_target(os.environ["TEMP"]) is True)

# 2. dry-run no borra nada
scratch = os.path.join(tempfile.mkdtemp(prefix="kc_test_"), "cache")
os.makedirs(scratch)
files = []
for i in range(5):
    p = os.path.join(scratch, f"f{i}.tmp")
    with open(p, "wb") as f:
        f.write(b"x" * 1024)
    files.append(p)

b, n = clean_directory(scratch, dry_run=True)
check("dry-run informa bytes", b == 5 * 1024, f"(b={b})")
check("dry-run informa archivos", n == 5, f"(n={n})")
check("dry-run no borra", all(os.path.exists(p) for p in files))

# 3. limpieza real sobre carpeta de prueba
b2, n2 = clean_directory(scratch, dry_run=False)
check("real borra archivos", not any(os.path.exists(p) for p in files))
check("real reporta lo mismo", (b2, n2) == (b, n), f"(b2={b2}, n2={n2})")
shutil.rmtree(os.path.dirname(scratch), ignore_errors=True)

# 4. Informe UTF-8
report = os.path.join(tempfile.mkdtemp(prefix="kc_rep_"), "r.txt")
good, msg = export_maintenance_report("log de prueba", {"smart": "OK"}, report)
check("informe se crea", good, msg)
if good:
    txt = open(report, encoding="utf-8").read()
    check("informe con acentos correctos", "Generación" in txt)
    os.remove(report)
shutil.rmtree(os.path.dirname(report), ignore_errors=True)

# 5. dry-run de system_cleaner no cierra navegadores ni borra
rutas, freed = sc.clean_browser_caches(dry_run=True)
check("system_cleaner dry-run devuelve lista", isinstance(rutas, list))
check("system_cleaner dry-run devuelve bytes", isinstance(freed, int))

print("OK  :", len(ok))
for f in fail:
    print("FALLO:", f)
sys.exit(1 if fail else 0)
