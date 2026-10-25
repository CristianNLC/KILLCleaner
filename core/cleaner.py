"""Limpieza de temporales del sistema: %TEMP%, Temp de Windows y Prefetch."""

import ctypes
import os

from core.app_paths import display_path, extended_path
from core.config import get_exclusions
from core.walker import iter_tree

# Rutas que nunca deben tocarse aunque se pasen por error.
# USERPROFILE solo bloquea coincidencias exactas: dentro vive %TEMP%.
_EXACT_PROTECTED_ENV = ("SystemDrive", "USERPROFILE")
_CONTAINMENT_PROTECTED_ENV = (
    "SystemRoot",
    "windir",
    "ProgramFiles",
    "ProgramFiles(x86)",
    "ProgramData",
    "PUBLIC",
)

# Carpetas personales: contienen datos del usuario, no residuos.
_USER_FOLDERS = (
    "Desktop",
    "Documents",
    "Downloads",
    "Pictures",
    "Videos",
    "Music",
    "OneDrive",
    "Favorites",
    "Contacts",
    "Links",
    "Searches",
    "Saved Games",
)

# Carpetas críticas en la raíz del sistema.
_FIXED_PROTECTED = (
    "$Recycle.Bin",
    "Recovery",
    "System Volume Information",
    "Boot",
    "EFI",
    "PerfLogs",
)


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


def _norm(path):
    return os.path.normcase(os.path.normpath(os.path.abspath(display_path(str(path)))))


def _is_within(child, parent):
    """True si *child* es *parent* o está dentro de él."""
    try:
        child_n = _norm(child)
        parent_n = _norm(parent).rstrip(os.sep)
    except Exception:
        return False
    return child_n == parent_n or child_n.startswith(parent_n + os.sep)


def protected_paths():
    """Devuelve (rutas_exactas, carpetas_protegidas).

    Las exactas solo bloquean coincidencias literales (el perfil del usuario
    debe poder contener ``AppData\\Local\\Temp``); las carpetas bloquean también
    cualquier subcarpeta.
    """
    exact = set()
    for var in _EXACT_PROTECTED_ENV:
        value = os.environ.get(var)
        if value:
            exact.add(value)

    folders = set()
    for var in _CONTAINMENT_PROTECTED_ENV:
        value = os.environ.get(var)
        if value:
            folders.add(value)

    home = os.environ.get("USERPROFILE")
    if home:
        for name in _USER_FOLDERS:
            folders.add(os.path.join(home, name))
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        value = os.environ.get(var)
        if value:
            folders.add(value)

    drive = os.environ.get("SystemDrive", "C:")
    for name in _FIXED_PROTECTED:
        folders.add(os.path.join(drive + os.sep, name))

    return exact, folders


def is_safe_target(path, exclusions=None):
    """Comprueba que la ruta sea una subcarpeta concreta y no una ruta crítica.

    Rechaza raíces de unidad, carpetas del sistema, carpetas personales del
    usuario y cualquier ruta incluida en las exclusiones configuradas.
    """
    if not path:
        return False

    try:
        full = _norm(path)
        if not os.path.isdir(extended_path(full)):
            return False
        _, rest = os.path.splitdrive(full)
        parts = [p for p in rest.split(os.sep) if p]
    except Exception:
        return False

    # Debe ser al menos "Carpeta\Subcarpeta"
    if len(parts) < 2:
        return False

    exact, folders = protected_paths()
    if exclusions is None:
        exclusions = get_exclusions()

    # Se valida tanto la ruta literal como su destino real: un punto de unión
    # o enlace podría apuntar a una carpeta protegida.
    candidates = {full}
    try:
        candidates.add(_norm(os.path.realpath(extended_path(full))))
    except Exception:
        pass

    for candidate in candidates:
        for protected in exact:
            try:
                if candidate == _norm(protected):
                    return False
            except Exception:
                continue
        for protected in folders:
            if _is_within(candidate, protected):
                return False
        for excluded in exclusions:
            if _is_within(candidate, excluded):
                return False

    return True


def _is_excluded(path, exclusions):
    return any(_is_within(path, excluded) for excluded in exclusions)


def _cancelled(cancel_event):
    return cancel_event is not None and cancel_event.is_set()


def scan_target(path, exclusions=None, cancel_event=None):
    """Calcula el peso total en bytes y cantidad de elementos a limpiar.

    Respeta las exclusiones configuradas para que el tamaño anunciado coincida
    con lo que realmente se va a limpiar. ``cancel_event`` permite detener el
    recorrido entre archivos.
    """
    if exclusions is None:
        exclusions = get_exclusions()
    if not is_safe_target(path, exclusions):
        return 0, 0

    total_bytes = 0
    file_count = 0
    for _directory, files in iter_tree(
        path,
        cancel_event=cancel_event,
        skip_dir=lambda candidate: _is_excluded(candidate, exclusions),
    ):
        for entry in files:
            if _cancelled(cancel_event):
                break
            try:
                total_bytes += entry.stat(follow_symlinks=False).st_size
                file_count += 1
            except OSError:
                continue
    return total_bytes, file_count


def clean_directory(path, log_callback=None, dry_run=False, exclusions=None, cancel_event=None):
    """Elimina los archivos temporales omitiendo los que estén en uso.

    Args:
        path: Carpeta a purgar.
        log_callback: Función opcional para reportar cada elemento.
        dry_run: Si es True no borra nada, solo informa qué se borraría.
        exclusions: Carpetas a respetar. Por defecto, las de ``config.json``.
        cancel_event: ``threading.Event`` opcional para detener la limpieza.

    Returns:
        (bytes_afectados, archivos_afectados)
    """
    if exclusions is None:
        exclusions = get_exclusions()

    if not is_safe_target(path, exclusions):
        if log_callback:
            log_callback(f"[x] Ruta no válida o protegida, se omite por seguridad: {path}")
        return 0, 0

    total_bytes = 0
    total_count = 0
    prefix = "[SIMULACIÓN] " if dry_run else "[BORRADO] "
    visited_dirs = []

    def _log_excluded(candidate):
        if log_callback:
            log_callback(f"[i] Excluida por configuración: {display_path(candidate)}")

    for current, files in iter_tree(
        path,
        cancel_event=cancel_event,
        skip_dir=lambda candidate: _is_excluded(candidate, exclusions),
        on_skip=_log_excluded,
    ):
        visited_dirs.append(current)

        for entry in files:
            if _cancelled(cancel_event):
                break
            try:
                sz = entry.stat(follow_symlinks=False).st_size
                if not dry_run:
                    os.remove(entry.path)
                total_bytes += sz
                total_count += 1
                if log_callback:
                    log_callback(f"{prefix}{entry.name}")
            except Exception:
                # Archivo en uso o sin permisos: se deja intacto
                continue

    if not dry_run and not _cancelled(cancel_event):
        # De más profunda a menos: las hijas deben quedar vacías antes que la madre.
        for dp in reversed(visited_dirs):
            if _norm(dp) == _norm(path):
                continue
            try:
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
