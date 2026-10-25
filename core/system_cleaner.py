"""Limpieza profunda del sistema: navegadores, Windows Update, volcados y miniaturas.

Todas las funciones aceptan ``dry_run=True`` para informar qué se borraría sin
tocar nada, y devuelven los bytes afectados para poder reportarlos en la UI.
"""

import os
import shutil
import subprocess


def _path_size(path: str) -> int:
    """Tamaño aproximado de un archivo o carpeta, ignorando accesos denegados."""
    total = 0
    try:
        if os.path.isfile(path):
            return os.path.getsize(path)
        for root, _, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except Exception:
                    continue
    except Exception:
        pass
    return total


def _close_browsers() -> None:
    """Pide a los navegadores que se cierren de forma amable (sin /F).

    Se envía WM_CLOSE, igual que pulsar la X: el navegador puede guardar su
    sesión. Si el usuario cancela el cierre, la caché bloqueada simplemente no
    se podrá borrar y se omite.
    """
    subprocess.run(
        "taskkill /im chrome.exe /im msedge.exe /im brave.exe",
        shell=True,
        capture_output=True,
    )


def clean_browser_caches(dry_run: bool = False, log_callback=None):
    """Limpia cachés de Chrome, Edge y Brave.

    Returns:
        (rutas_procesadas, bytes_afectados)
    """
    local_app = os.environ.get("LOCALAPPDATA", "")
    targets = [
        os.path.join(local_app, r"Google\Chrome\User Data\Default\Cache"),
        os.path.join(local_app, r"Microsoft\Edge\User Data\Default\Cache"),
        os.path.join(local_app, r"BraveSoftware\Brave-Browser\User Data\Default\Cache"),
    ]
    existing = [p for p in targets if os.path.exists(p)]

    if dry_run:
        total = 0
        for path in existing:
            size = _path_size(path)
            total += size
            if log_callback:
                log_callback(f"[SIMULACIÓN] Se purgaría: {path} ({round(size / (1024 * 1024), 2)} MB)")
        return existing, total

    _close_browsers()

    processed = []
    freed = 0
    for path in existing:
        size = _path_size(path)
        try:
            shutil.rmtree(path, ignore_errors=True)
            processed.append(path)
            freed += size
            if log_callback:
                log_callback(f"[✓] Caché purgada: {path}")
        except Exception:
            continue
    return processed, freed


def clean_windows_update(dry_run: bool = False, log_callback=None):
    """Detiene wuauserv/bits, purga descargas de Update y reactiva los servicios.

    Returns:
        (limpiado: bool, bytes_afectados)
    """
    win_dir = os.environ.get("SystemRoot", "C:\\Windows")
    download_dir = os.path.join(win_dir, "SoftwareDistribution", "Download")

    if not os.path.exists(download_dir):
        return False, 0

    size = _path_size(download_dir)

    if dry_run:
        if log_callback:
            log_callback(f"[SIMULACIÓN] Se purgaría Windows Update: {round(size / (1024 * 1024), 2)} MB")
        return True, size

    subprocess.run("net stop wuauserv", shell=True, capture_output=True)
    subprocess.run("net stop bits", shell=True, capture_output=True)

    cleared = False
    try:
        shutil.rmtree(download_dir, ignore_errors=True)
        os.makedirs(download_dir, exist_ok=True)
        cleared = True
        if log_callback:
            log_callback(f"[✓] Descargas de Windows Update purgadas ({round(size / (1024 * 1024), 2)} MB).")
    except Exception:
        pass
    finally:
        # Los servicios deben quedar activos aunque falle el borrado
        subprocess.run("net start bits", shell=True, capture_output=True)
        subprocess.run("net start wuauserv", shell=True, capture_output=True)

    return cleared, size


def clean_logs_and_dumps(dry_run: bool = False, log_callback=None):
    """Elimina volcados de memoria (.dmp), crash dumps y logs del sistema.

    Returns:
        (cantidad_purgada, bytes_afectados)
    """
    win_dir = os.environ.get("SystemRoot", "C:\\Windows")
    local_app = os.environ.get("LOCALAPPDATA", "")

    paths = [
        os.path.join(win_dir, "MEMORY.DMP"),
        os.path.join(win_dir, "Minidump"),
        os.path.join(local_app, "CrashDumps"),
    ]

    purged = 0
    freed = 0

    for p in paths:
        if not os.path.exists(p):
            continue
        size = _path_size(p)
        if dry_run:
            purged += 1
            freed += size
            if log_callback:
                log_callback(f"[SIMULACIÓN] Se purgaría: {p} ({round(size / (1024 * 1024), 2)} MB)")
            continue

        try:
            if os.path.isfile(p):
                os.remove(p)
            else:
                shutil.rmtree(p, ignore_errors=True)
                os.makedirs(p, exist_ok=True)
            purged += 1
            freed += size
        except Exception:
            pass

    return purged, freed


def flush_dns_and_network():
    """Limpia caché de resolución DNS y restablece sockets de red."""
    r1 = subprocess.run("ipconfig /flushdns", shell=True, capture_output=True, text=True)
    r2 = subprocess.run("netsh winsock reset", shell=True, capture_output=True, text=True)
    return r1.returncode == 0 and r2.returncode == 0


def clean_thumbnail_cache(dry_run: bool = False, log_callback=None):
    """Reinicia Explorer y purga las bases thumbcache_*.db.

    Returns:
        (cantidad_purgada, bytes_afectados)
    """
    local_app = os.environ.get("LOCALAPPDATA", "")
    thumb_dir = os.path.join(local_app, r"Microsoft\Windows\Explorer")

    if not os.path.isdir(thumb_dir):
        return 0, 0

    files = []
    for f in os.listdir(thumb_dir):
        if f.startswith("thumbcache_") and f.endswith(".db"):
            files.append(os.path.join(thumb_dir, f))

    freed = sum(_path_size(f) for f in files)

    if dry_run:
        if log_callback:
            log_callback(f"[SIMULACIÓN] Se purgarían {len(files)} cachés de miniaturas.")
        return len(files), freed

    if not files:
        return 0, 0

    subprocess.run("taskkill /f /im explorer.exe", shell=True, capture_output=True)
    cleared = 0
    try:
        for path in files:
            try:
                os.remove(path)
                cleared += 1
            except Exception:
                pass
    finally:
        # Explorer debe volver a arrancar siempre
        subprocess.Popen("explorer.exe", shell=True)

    if log_callback:
        log_callback(f"[✓] Cachés de miniaturas purgadas: {cleared} archivos.")
    return cleared, freed
