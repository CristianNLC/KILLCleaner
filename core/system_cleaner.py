import os
import shutil
import subprocess

def clean_browser_caches():
    """Cierra navegadores y limpia sus cachés."""
    local_app = os.environ.get("LOCALAPPDATA", "")
    targets = [
        os.path.join(local_app, r"Google\Chrome\User Data\Default\Cache"),
        os.path.join(local_app, r"Microsoft\Edge\User Data\Default\Cache"),
        os.path.join(local_app, r"BraveSoftware\Brave-Browser\User Data\Default\Cache")
    ]
    
    # Cerrar navegadores para liberar bloqueos de archivos
    subprocess.run("taskkill /f /im chrome.exe /im msedge.exe /im brave.exe", shell=True, capture_output=True)
    
    deleted_paths = []
    for path in targets:
        if os.path.exists(path):
            try:
                shutil.rmtree(path, ignore_errors=True)
                deleted_paths.append(path)
            except Exception:
                continue
    return deleted_paths

def clean_windows_update():
    """Detiene wuauserv/bits, purga descargas de Update y reactiva servicios."""
    win_dir = os.environ.get("SystemRoot", "C:\\Windows")
    download_dir = os.path.join(win_dir, "SoftwareDistribution", "Download")

    subprocess.run("net stop wuauserv", shell=True, capture_output=True)
    subprocess.run("net stop bits", shell=True, capture_output=True)

    cleared = False
    if os.path.exists(download_dir):
        try:
            shutil.rmtree(download_dir, ignore_errors=True)
            os.makedirs(download_dir, exist_ok=True)
            cleared = True
        except Exception:
            pass

    subprocess.run("net start bits", shell=True, capture_output=True)
    subprocess.run("net start wuauserv", shell=True, capture_output=True)
    return cleared

def clean_logs_and_dumps():
    """Elimina volcados de memoria (.dmp), crash dumps y logs del sistema."""
    win_dir = os.environ.get("SystemRoot", "C:\\Windows")
    local_app = os.environ.get("LOCALAPPDATA", "")
    
    purged = 0
    paths = [
        os.path.join(win_dir, "MEMORY.DMP"),
        os.path.join(win_dir, "Minidump"),
        os.path.join(local_app, "CrashDumps")
    ]

    for p in paths:
        if os.path.isfile(p):
            try:
                os.remove(p)
                purged += 1
            except Exception:
                pass
        elif os.path.isdir(p):
            try:
                shutil.rmtree(p, ignore_errors=True)
                os.makedirs(p, exist_ok=True)
                purged += 1
            except Exception:
                pass
    return purged

def flush_dns_and_network():
    """Limpia caché de resolución DNS y restablece sockets de red."""
    r1 = subprocess.run("ipconfig /flushdns", shell=True, capture_output=True, text=True)
    r2 = subprocess.run("netsh winsock reset", shell=True, capture_output=True, text=True)
    return r1.returncode == 0 and r2.returncode == 0

def clean_thumbnail_cache():
    """Reinicia Explorer y purga bases thumbcache_*.db."""
    local_app = os.environ.get("LOCALAPPDATA", "")
    thumb_dir = os.path.join(local_app, r"Microsoft\Windows\Explorer")
    
    subprocess.run("taskkill /f /im explorer.exe", shell=True, capture_output=True)
    cleared = 0
    if os.path.exists(thumb_dir):
        for f in os.listdir(thumb_dir):
            if f.startswith("thumbcache_") and f.endswith(".db"):
                try:
                    os.remove(os.path.join(thumb_dir, f))
                    cleared += 1
                except Exception:
                    pass
    subprocess.Popen("explorer.exe", shell=True)
    return cleared