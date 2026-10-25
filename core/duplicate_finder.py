import os
import hashlib
from collections import defaultdict
from core.disk_analyzer import format_size

BUFFER_SIZE = 65536  # Lectura en bloques de 64 KB

def calculate_sha256(filepath: str) -> str:
    """Calcula el hash SHA-256 de un archivo en streaming sin saturar la RAM."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(BUFFER_SIZE):
            sha.update(chunk)
    return sha.hexdigest()

def find_duplicate_files(target_dir: str, min_size_bytes: int = 1024, log_callback=None, cancel_event=None):
    """
    Escanea el directorio objetivo buscando archivos duplicados por hash.
    Retorna un diccionario: {sha256: [lista_de_rutas_duplicadas]}

    Si ``cancel_event`` se activa, detiene el trabajo y devuelve ``{}``.
    """
    if not os.path.isdir(target_dir):
        return {}

    if log_callback:
        log_callback(f"[*] Indexando archivos en: {target_dir}...")

    # Fase 1: Agrupar por tamaño
    size_map = defaultdict(list)
    total_files = 0

    for root, _, files in os.walk(target_dir):
        if cancel_event is not None and cancel_event.is_set():
            return {}
        for f in files:
            if cancel_event is not None and cancel_event.is_set():
                return {}
            fp = os.path.join(root, f)
            try:
                sz = os.path.getsize(fp)
                if sz >= min_size_bytes:
                    size_map[sz].append(fp)
                    total_files += 1
            except (PermissionError, FileNotFoundError, OSError):
                continue

    # Filtrar solo tamaños con 2 o más archivos
    potential_candidates = {sz: paths for sz, paths in size_map.items() if len(paths) > 1}
    
    if log_callback:
        log_callback(f"[+] Total indexado: {total_files} archivos. Grupos sospechosos: {len(potential_candidates)}")

    # Fase 2: Comprobación por Hash SHA-256
    hash_map = defaultdict(list)
    for sz, paths in potential_candidates.items():
        for path in paths:
            if cancel_event is not None and cancel_event.is_set():
                return {}
            try:
                file_hash = calculate_sha256(path)
                hash_map[file_hash].append(path)
            except Exception:
                continue

    # Filtrar únicamente los hashes que tengan duplicados reales
    duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    return duplicates