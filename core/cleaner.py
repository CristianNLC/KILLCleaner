import os
import shutil
import ctypes

def get_target_directories():
    """Retorna las rutas esenciales de limpieza del sistema."""
    user_temp = os.environ.get("TEMP", "")
    system_root = os.environ.get("SystemRoot", "C:\\Windows")
    win_temp = os.path.join(system_root, "Temp")
    prefetch = os.path.join(system_root, "Prefetch")

    targets = {
        "Temporales de Usuario": user_temp,
        "Temporales de Windows": win_temp,
        "Caché Prefetch": prefetch
    }
    return {k: v for k, v in targets.items() if os.path.exists(v)}

def scan_target(path):
    """Calcula el peso total en bytes y cantidad de elementos a limpiar."""
    total_bytes = 0
    file_count = 0
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total_bytes += os.path.getsize(fp)
                file_count += 1
            except Exception:
                continue
    return total_bytes, file_count

def clean_directory(path, log_callback=None):
    """Elimina los archivos temporales omitiendo los que estén en uso."""
    deleted_bytes = 0
    deleted_count = 0

    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            fp = os.path.join(root, f)
            try:
                sz = os.path.getsize(fp)
                os.remove(fp)
                deleted_bytes += sz
                deleted_count += 1
                if log_callback:
                    log_callback(f"[BORRADO] {f}")
            except Exception:
                continue

        for d in dirs:
            dp = os.path.join(root, d)
            try:
                os.rmdir(dp)
            except Exception:
                continue

    return deleted_bytes, deleted_count

def empty_recycle_bin():
    """Vacía la papelera de reciclaje mediante la API nativa de Windows."""
    try:
        flags = 0x00000007  # SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        return result == 0
    except Exception:
        return False