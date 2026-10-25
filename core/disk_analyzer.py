import os
import ctypes
from ctypes import wintypes

# Carga de API Win32 para medir tamaño físico real en disco
kernel32 = ctypes.windll.kernel32

def get_real_file_size(filepath: str) -> int:
    """
    Obtiene el tamaño físico real ocupado en disco (Size on disk) en Windows,
    gestionando Sparse Files, compresión NTFS y enlaces virtuales.
    Si falla la llamada nativa, recurre a os.path.getsize.
    """
    try:
        high = wintypes.DWORD(0)
        low = kernel32.GetCompressedFileSizeW(filepath, ctypes.byref(high))
        if low == 0xFFFFFFFF and kernel32.GetLastError() != 0:
            return os.path.getsize(filepath)
        return (high.value << 32) + low
    except Exception:
        try:
            return os.path.getsize(filepath)
        except Exception:
            return 0

def format_size(size_bytes: int) -> str:
    """Convierte bytes a formato legible (B, KB, MB, GB, TB)."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"

def get_dir_size_fast(path: str) -> int:
    """Calcula el tamaño acumulado real de un directorio ignorando accesos denegados."""
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += get_real_file_size(entry.path)
                    elif entry.is_dir(follow_symlinks=False):
                        total += get_dir_size_fast(entry.path)
                except (PermissionError, FileNotFoundError, OSError):
                    continue
    except (PermissionError, FileNotFoundError, OSError):
        pass
    return total

def analyze_directory_top_items(target_path: str, max_items: int = 15, progress_callback=None):
    """
    Inspecciona la raíz seleccionada y retorna los elementos directos más pesados
    basados en su espacio físico real en disco.
    Retorna: (total_size, top_items_list)
    """
    if not os.path.isdir(target_path):
        return 0, []

    items = []
    try:
        entries = list(os.scandir(target_path))
    except Exception:
        return 0, []

    for entry in entries:
        try:
            if progress_callback:
                progress_callback(f"Analizando: {entry.name}")

            if entry.is_file(follow_symlinks=False):
                sz = get_real_file_size(entry.path)
                items.append({"name": entry.name, "path": entry.path, "size": sz, "is_dir": False})
            elif entry.is_dir(follow_symlinks=False):
                sz = get_dir_size_fast(entry.path)
                items.append({"name": entry.name, "path": entry.path, "size": sz, "is_dir": True})
        except (PermissionError, FileNotFoundError, OSError):
            continue

    total_dir_size = sum(item["size"] for item in items)
    items.sort(key=lambda x: x["size"], reverse=True)

    top_items = items[:max_items]
    for item in top_items:
        item["percent"] = (item["size"] / total_dir_size * 100.0) if total_dir_size > 0 else 0.0
        item["size_formatted"] = format_size(item["size"])

    return total_dir_size, top_items
