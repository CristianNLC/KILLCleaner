"""Pruebas del paquete C: rendimiento, rutas largas y seguridad de enlaces."""
import os
import shutil
import subprocess
import sys
import tempfile
import threading

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import core.config as cfg
from core.app_paths import display_path, extended_path, system_drive
from core.cleaner import clean_directory, is_safe_target, scan_target
from core.dev_cleaner import purge_pycache_recursive, scan_path_size
from core.duplicate_finder import (
    PARTIAL_BYTES,
    calculate_partial_hash,
    calculate_sha256,
    find_duplicate_files,
)
from core.reporter import export_maintenance_report
from core.walker import iter_tree

ok, fail = [], []


def check(name, cond, extra=""):
    (ok if cond else fail).append(f"{name} {extra}")


base = tempfile.mkdtemp(prefix="kc_c_")
cfg.config_path = lambda: os.path.join(base, "config.json")


def make_junction(link, target):
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", link, target],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and os.path.exists(link)


# --- 1. Rutas largas: helpers ---
short = os.path.join(base, "corto")
check("extended_path corta sin prefijo", extended_path(short) == os.path.abspath(short))
already = "\\\\?\\C:\\Windows"
check("extended_path idempotente", extended_path(already) == already)

long_plain = "C:\\" + "\\".join(["carpeta_larga"] * 30)
long_ext = extended_path(long_plain)
check("extended_path larga con prefijo", long_ext.startswith("\\\\?\\"), f"({long_ext[:20]}...)")
check("display_path quita prefijo", display_path(long_ext) == long_plain)
unc = "\\\\servidor\\recurso\\" + "\\".join(["carpeta"] * 40)
check("extended_path UNC", extended_path(unc).startswith("\\\\?\\UNC\\"))
check("display_path UNC", display_path(extended_path(unc)) == unc)

# --- 2. iter_tree: recorrido, poda y cancelación ---
root = os.path.join(base, "tree")
keep = os.path.join(root, "keep")
sub = os.path.join(root, "sub")
deep = os.path.join(sub, "deep")
for d in (root, keep, sub, deep):
    os.makedirs(d, exist_ok=True)
for path in (
    os.path.join(root, "a.tmp"),
    os.path.join(keep, "b.tmp"),
    os.path.join(sub, "c.tmp"),
    os.path.join(deep, "d.tmp"),
):
    with open(path, "wb") as f:
        f.write(b"x" * 512)

visited, skipped = [], []
for current, files in iter_tree(root, skip_dir=lambda p: p.lower().endswith("keep"), on_skip=skipped.append):
    visited.append(current)
    check(f"iter_tree archivos en {os.path.basename(current) or current}", all(e.is_file() for e in files))

names = {os.path.basename(p) for p in visited}
check("iter_tree visita raíz y subcarpetas", {"tree", "sub", "deep"} <= names, f"({sorted(names)})")
check("iter_tree poda carpeta excluida", "keep" not in names)
check("iter_tree avisa de la poda", len(skipped) == 1, f"({len(skipped)})")
check("iter_tree no pierde archivos", sum(1 for _d, f in iter_tree(root) for _ in f) == 4)

ev = threading.Event()
ev.set()
check("iter_tree cancelado no genera nada", list(iter_tree(root, cancel_event=ev)) == [])

# --- 3. Punto de unión: no se sigue ni se borra fuera del objetivo ---
junction_root = os.path.join(base, "junction_root")
outside = os.path.join(base, "outside")
os.makedirs(junction_root)
os.makedirs(outside)
outside_file = os.path.join(outside, "importante.txt")
with open(outside_file, "wb") as f:
    f.write(b"no borrar")
with open(os.path.join(junction_root, "basura.tmp"), "wb") as f:
    f.write(b"x" * 100)

link = os.path.join(junction_root, "enlace")
junction_ok = make_junction(link, outside)
if junction_ok:
    check("junction no se recorre", all(os.path.basename(p) != "enlace" for p, _f in iter_tree(junction_root)))
    freed_b, freed_n = clean_directory(junction_root)
    check("clean borra solo lo propio", freed_n == 1, f"(n={freed_n})")
    check("clean no toca el destino del junction", os.path.exists(outside_file))
    check("clean conserva el junction", os.path.isdir(link))
    os.rmdir(link)
else:
    check("junction no se recorre (omitido: no se pudo crear)", True)

check("is_safe_target rechaza ruta inexistente", is_safe_target(os.path.join(base, "winlink")) is False)

# Junction a una carpeta protegida: debe rechazarse por su destino real
win_link = os.path.join(base, "winlink")
if make_junction(win_link, os.environ.get("SystemRoot", "C:\\Windows")):
    check("junction a SystemRoot se rechaza", is_safe_target(win_link) is False)
    os.rmdir(win_link)
else:
    check("junction a SystemRoot se rechaza (omitido)", True)

shutil.rmtree(outside, ignore_errors=True)
shutil.rmtree(junction_root, ignore_errors=True)

# --- 4. scan_target / clean_directory con exclusiones ---
b, n = scan_target(root, exclusions=[keep])
check("scan cuenta bytes con scandir", b == 3 * 512, f"(b={b})")
check("scan cuenta archivos con scandir", n == 3, f"(n={n})")

from core.system_cleaner import _path_size  # noqa: E402

check("dev_cleaner cuenta todo el árbol", scan_path_size(root) == (4 * 512, 4), f"({scan_path_size(root)})")
check("system_cleaner cuenta todo el árbol", _path_size(root) == 4 * 512, f"({_path_size(root)})")

freed_b, freed_n = clean_directory(root, exclusions=[keep])
check("clean borra con scandir", (freed_b, freed_n) == (3 * 512, 3), f"({freed_n}, {freed_b})")
check("clean respeta exclusión", os.path.exists(os.path.join(keep, "b.tmp")))
check("clean elimina subcarpetas vacías", not os.path.exists(deep))

# --- 5. Hash parcial ---
small = os.path.join(base, "small.bin")
with open(small, "wb") as f:
    f.write(os.urandom(1000))
check("hash parcial = completo en archivo pequeño", calculate_partial_hash(small) == calculate_sha256(small))

dups_dir = os.path.join(base, "dups")
os.makedirs(dups_dir)
head, tail = b"A" * PARTIAL_BYTES, b"B" * PARTIAL_BYTES
middle = b"X" * 5000
same_a = os.path.join(dups_dir, "a.bin")
same_b = os.path.join(dups_dir, "b.bin")
different = os.path.join(dups_dir, "c.bin")
for path, body in ((same_a, head + middle + tail), (same_b, head + middle + tail), (different, head + b"Y" * 5000 + tail)):
    with open(path, "wb") as f:
        f.write(body)

check(
    "hash parcial coincide con misma cabeza/cola",
    calculate_partial_hash(same_a) == calculate_partial_hash(different),
)
found = find_duplicate_files(dups_dir, min_size_bytes=1)
groups = [sorted(os.path.basename(p) for p in paths) for paths in found.values()]
check("duplicados reales detectados", groups == [["a.bin", "b.bin"]], f"({groups})")
check("contenido distinto no es duplicado", not any("c.bin" in g for g in groups))

# --- 6. Rutas largas de verdad ---
long_base = os.path.join(base, "largo")
nested = long_base
for _ in range(14):
    nested = os.path.join(nested, "carpeta_muy_larga_0123456789")
long_file = os.path.join(nested, "temporal.tmp")
long_created = False
try:
    os.makedirs(extended_path(nested), exist_ok=True)
    with open(extended_path(long_file), "wb") as f:
        f.write(b"z" * 2048)
    long_created = os.path.exists(extended_path(long_file))
except OSError:
    long_created = False

check("se creó una ruta > 260 caracteres", long_created, f"(len={len(long_file)})")
if long_created:
    check("is_safe_target acepta ruta larga", is_safe_target(nested) is True)
    lb, ln = clean_directory(nested)
    check("clean borra en ruta larga", (lb, ln) == (2048, 1), f"({ln}, {lb})")
    check("archivo largo eliminado", not os.path.exists(extended_path(long_file)))
    shutil.rmtree(extended_path(long_base), ignore_errors=True)

# --- 8. Purga de __pycache__ sin seguir uniones ---
py_root = os.path.join(base, "pyproj")
os.makedirs(os.path.join(py_root, "__pycache__"))
with open(os.path.join(py_root, "__pycache__", "mod.cpython-314.pyc"), "wb") as f:
    f.write(b"x" * 100)
with open(os.path.join(py_root, "suelto.pyc"), "wb") as f:
    f.write(b"y" * 50)

folders, files = purge_pycache_recursive(py_root)
check("purga __pycache__ real", (folders, files) == (1, 2), f"({folders}, {files})")
check("__pycache__ eliminado", not os.path.exists(os.path.join(py_root, "__pycache__")))

py_nested = os.path.join(base, "pyproj2")
os.makedirs(py_nested)
outside_py = os.path.join(base, "outside_py")
os.makedirs(outside_py)
outside_pyc = os.path.join(outside_py, "valioso.pyc")
with open(outside_pyc, "wb") as f:
    f.write(b"z" * 10)
py_link = os.path.join(py_nested, "__pycache__")
if make_junction(py_link, outside_py):
    folders, files = purge_pycache_recursive(py_nested)
    check("junction __pycache__ no se recorre", os.path.exists(outside_pyc))
    check("junction __pycache__ no se cuenta", (folders, files) == (0, 0), f"({folders}, {files})")
    os.rmdir(py_link)
else:
    check("junction __pycache__ no se recorre (omitido)", True)

# --- 9. Informe con unidad real ---
report = os.path.join(base, "informe.txt")
good, msg = export_maintenance_report("registro", {"disk_free": "10 GB Libres"}, report)
check("informe se genera", good, msg)
if good:
    text = open(report, encoding="utf-8").read()
    check("informe usa unidad real", f"({system_drive()})" in text, f"({system_drive()})")
    check("informe sin C: fijo", "Espacio Libre en C:" not in text)

shutil.rmtree(base, ignore_errors=True)

print("OK  :", len(ok))
for item in fail:
    print("FALLO:", item)
sys.exit(1 if fail else 0)
