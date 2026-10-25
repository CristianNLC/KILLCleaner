"""Limpieza de temporales del sistema: %TEMP%, Temp de Windows y Prefetch."""

import ctypes
import os


def get_target_directories():
    """Retorna las rutas esenciales de limpieza del sistema."""
    user_temp = os.environ.get("TEMP", "")
    system_root = os.environ.get("SystemRoot", "C:\\Windows")
    win_temp = os.path.join(system_root, "Temp")
    prefetch = os.path.join(system_root, "Prefetch")

    targets = {
        "Temporales de Usuario": user_temp,
        "Temporales de Windows": win_temp,
        "Caché Prefetch": prefetch,
    }
    return {k: v for k, v in targets.items() if v and os.path.exists(v)}


def is_safe_target(path: str) -> bool:
    """Comprueba que la ruta sea una subcarpeta concreta y no una raíz crítica.

    Evita que un error de configuración borre C:\\, C:\\Windows, C:\\Users o el
    perfil del usuario.
    """
    if not path:
        return False

    try:
        full = os.path.normcase(os.path.abspath(path))
        _, rest = os.path.splitdrive(full)
        parts = [p for p in rest.split(os.sep) if p]
    except Exception:
        return False

    # Debe ser al menos "Carpeta\Subcarpeta"
    if len(parts) < 2:
        return False

    protected = set()
    for var in ("SystemRoot", "USERPROFILE", "ProgramFiles", "ProgramData"):
        value = os.environ.get(var)
        if value:
            protected.add(os.path.normcase(os.path.abspath(value)))

    return full not in protected


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


def clean_directory(path, log_callback=None, dry_run=False):
    """Elimina los archivos temporales omitiendo los que estén en uso.

    Args:
        path: Carpeta a purgar.
        log_callback: Función opcional para reportar cada elemento.
        dry_run: Si es True no borra nada, solo informa qué se borraría.

    Returns:
        (bytes_afectados, archivos_afectados)
    """
    if not is_safe_target(path):
        if log_callback:
            log_callback(f"[x] Ruta protegida, se omite por seguridad: {path}")
        return 0, 0

    total_bytes = 0
    total_count = 0
    prefix = "[SIMULACIÓN] " if dry_run else "[BORRADO] "

    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            fp = os.path.join(root, f)
            try:
                sz = os.path.getsize(fp)
                if not dry_run:
                    os.remove(fp)
                total_bytes += sz
                total_count += 1
                if log_callback:
                    log_callback(f"{prefix}{f}")
            except Exception:
                # Archivo en uso o sin permisos: se deja intacto
                continue

        for d in dirs:
            dp = os.path.join(root, d)
            try:
                if dry_run:
                    continue
                os.rmdir(dp)
            except Exception:
                continue

    return total_bytes, total_count


def empty_recycle_bin():
    """Vacía la papelera de reciclaje mediante la API nativa de Windows."""
    try:
        flags = 0x00000007  # SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        return result == 0
    except Exception:
        return False
