"""Comparativa rápida: recorrido con os.walk (antes) vs os.scandir (ahora)."""
import os
import shutil
import sys
import tempfile
import time

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import core.config as cfg
from core.cleaner import scan_target
from core.duplicate_finder import find_duplicate_files

base = tempfile.mkdtemp(prefix="kc_bench_")
cfg.config_path = lambda: os.path.join(base, "config.json")

tree = os.path.join(base, "tree")
for i in range(120):
    folder = os.path.join(tree, f"dir{i:03d}")
    os.makedirs(folder)
    for j in range(25):
        with open(os.path.join(folder, f"f{j}.tmp"), "wb") as f:
            f.write(b"x" * (256 + j * 16))


def old_scan(path):
    total, count = 0, 0
    for root, _dirs, files in os.walk(path, topdown=True):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
                count += 1
            except OSError:
                continue
    return total, count


def best(fn, rounds=3):
    times = []
    for _ in range(rounds):
        start = time.perf_counter()
        result = fn()
        times.append(time.perf_counter() - start)
    return min(times), result


old_t, old_r = best(lambda: old_scan(tree))
new_t, new_r = best(lambda: scan_target(tree))
print(f"scan_target: {old_t*1000:.1f} ms (os.walk) -> {new_t*1000:.1f} ms (scandir)")
print(f"resultado idéntico: {old_r == new_r} {new_r}")
print(f"mejora: {(old_t/new_t):.2f}x")

# Duplicados: muchos archivos del mismo tamaño con contenido distinto.
dups = os.path.join(base, "dups")
os.makedirs(dups)
for i in range(60):
    with open(os.path.join(dups, f"d{i:02d}.bin"), "wb") as f:
        f.write(os.urandom(1024 * 1024))


def old_dups(target):
    import hashlib
    size_map = {}
    for root, _dirs, files in os.walk(target):
        for name in files:
            fp = os.path.join(root, name)
            try:
                size_map.setdefault(os.path.getsize(fp), []).append(fp)
            except OSError:
                pass
    hash_map = {}
    for paths in size_map.values():
        if len(paths) < 2:
            continue
        for path in paths:
            sha = hashlib.sha256()
            with open(path, "rb") as f:
                while chunk := f.read(65536):
                    sha.update(chunk)
            hash_map.setdefault(sha.hexdigest(), []).append(path)
    return {h: p for h, p in hash_map.items() if len(p) > 1}


old_dup_t, old_dup_r = best(lambda: old_dups(dups))
new_dup_t, new_dup_r = best(lambda: find_duplicate_files(dups, min_size_bytes=1))
print(f"duplicados (60 MB, mismo tamaño): {old_dup_t*1000:.0f} ms (hash completo) -> {new_dup_t*1000:.0f} ms (hash parcial)")
print(f"resultado idéntico: {old_dup_r == new_dup_r}, grupos={len(new_dup_r)}")
print(f"mejora: {(old_dup_t/new_dup_t):.2f}x")

shutil.rmtree(base, ignore_errors=True)
