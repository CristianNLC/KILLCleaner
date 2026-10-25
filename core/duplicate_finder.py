import hashlib
import os
from collections import defaultdict

from core.app_paths import display_path, extended_path
from core.walker import iter_tree

BUFFER_SIZE = 65536  # Lectura en bloques de 64 KB
PARTIAL_BYTES = 65536  # Cabeza y cola que se comparan antes del hash completo


def calculate_sha256(filepath: str) -> str:
    """Calcula el hash SHA-256 de un archivo en streaming sin saturar la RAM."""
    sha = hashlib.sha256()
    with open(extended_path(filepath), "rb") as f:
        while chunk := f.read(BUFFER_SIZE):
            sha.update(chunk)
    return sha.hexdigest()


def calculate_partial_hash(filepath: str, size: int | None = None) -> str:
    """Hash rápido de los primeros y últimos 64 KB de un archivo.

    Dos archivos con el mismo tamaño pero distinto contenido casi siempre
    difieren aquí, lo que evita leer entero cada candidato. Para archivos de
    hasta 128 KB el resultado es el SHA-256 completo.
    """
    if size is None:
        size = os.path.getsize(extended_path(filepath))

    sha = hashlib.sha256()
    with open(extended_path(filepath), "rb") as f:
        if size <= PARTIAL_BYTES * 2:
            while chunk := f.read(BUFFER_SIZE):
                sha.update(chunk)
        else:
            sha.update(f.read(PARTIAL_BYTES))
            f.seek(-PARTIAL_BYTES, os.SEEK_END)
            sha.update(f.read(PARTIAL_BYTES))
    return sha.hexdigest()


def find_duplicate_files(target_dir: str, min_size_bytes: int = 1024, log_callback=None, cancel_event=None):
    """
    Escanea el directorio objetivo buscando archivos duplicados por hash.
    Retorna un diccionario: {sha256: [lista_de_rutas_duplicadas]}

    Si ``cancel_event`` se activa, detiene el trabajo y devuelve ``{}``.
    """
    if not os.path.isdir(extended_path(target_dir)):
        return {}

    if log_callback:
        log_callback(f"[*] Indexando archivos en: {target_dir}...")

    # Fase 1: Agrupar por tamaño (una sola pasada con scandir)
    size_map = defaultdict(list)
    total_files = 0

    for _directory, files in iter_tree(target_dir, cancel_event=cancel_event):
        for entry in files:
            if cancel_event is not None and cancel_event.is_set():
                return {}
            try:
                sz = entry.stat(follow_symlinks=False).st_size
                if sz >= min_size_bytes:
                    size_map[sz].append(display_path(entry.path))
                    total_files += 1
            except OSError:
                continue

    # Filtrar solo tamaños con 2 o más archivos
    potential_candidates = {sz: paths for sz, paths in size_map.items() if len(paths) > 1}

    if log_callback:
        log_callback(f"[+] Total indexado: {total_files} archivos. Grupos sospechosos: {len(potential_candidates)}")

    # Fase 2: descarte rápido por cabeza/cola y confirmación con SHA-256
    hash_map = defaultdict(list)
    for size, paths in potential_candidates.items():
        if cancel_event is not None and cancel_event.is_set():
            return {}

        if size <= PARTIAL_BYTES * 2:
            # El hash parcial ya cubre el archivo completo.
            for path in paths:
                if cancel_event is not None and cancel_event.is_set():
                    return {}
                try:
                    hash_map[calculate_sha256(path)].append(path)
                except Exception:
                    continue
            continue

        buckets = defaultdict(list)
        for path in paths:
            if cancel_event is not None and cancel_event.is_set():
                return {}
            try:
                buckets[calculate_partial_hash(path, size)].append(path)
            except Exception:
                continue

        for group in buckets.values():
            if len(group) < 2:
                continue
            for path in group:
                if cancel_event is not None and cancel_event.is_set():
                    return {}
                try:
                    hash_map[calculate_sha256(path)].append(path)
                except Exception:
                    continue

    # Filtrar únicamente los hashes que tengan duplicados reales
    duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    return duplicates
