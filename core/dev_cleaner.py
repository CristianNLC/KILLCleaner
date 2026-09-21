import os
import stat
import shutil

def _remove_readonly(func, path, exc_info):
    """Limpia el atributo de solo lectura si Windows bloquea el borrado."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def get_dev_cache_targets():
    """Retorna las rutas estándar de cachés de herramientas de desarrollo y apps."""
    local_app = os.environ.get("LOCALAPPDATA", "")
    roaming_app = os.environ.get("APPDATA", "")

    targets = {
        "Caché de Pip (Python)": os.path.join(local_app, "pip", "cache"),
        "Caché de NPM (Node.js)": os.path.join(roaming_app, "npm-cache"),
        "Caché de Yarn": os.path.join(local_app, "Yarn", "Cache"),
        "Caché de Discord": os.path.join(roaming_app, "discord", "Code Cache"),
        "Caché de Spotify": os.path.join(local_app, "Spotify", "Storage")
    }
    return {name: path for name, path in targets.items() if os.path.exists(path)}

def scan_path_size(path: str):
    """Calcula el tamaño acumulado ignorando enlaces simbólicos para evitar bucles."""
    total_bytes = 0
    file_count = 0
    if not os.path.exists(path):
        return 0, 0

    try:
        for root, _, files in os.walk(path, followlinks=False):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total_bytes += os.path.getsize(fp)
                    file_count += 1
                except (PermissionError, FileNotFoundError, OSError):
                    continue
    except Exception:
        pass

    return total_bytes, file_count

def purge_dev_target(path: str):
    """Elimina el contenido de la caché de forma segura omitiendo archivos retenidos."""
    deleted_bytes = 0
    deleted_files = 0
    if not os.path.exists(path):
        return 0, 0

    try:
        entries = list(os.scandir(path))
    except Exception:
        return 0, 0

    for entry in entries:
        try:
            if entry.is_file(follow_symlinks=False) or entry.is_symlink():
                sz = entry.stat(follow_symlinks=False).st_size
                try:
                    os.remove(entry.path)
                    deleted_bytes += sz
                    deleted_files += 1
                except PermissionError:
                    os.chmod(entry.path, stat.S_IWRITE)
                    os.remove(entry.path)
                    deleted_bytes += sz
                    deleted_files += 1
            elif entry.is_dir(follow_symlinks=False):
                b, f = scan_path_size(entry.path)
                shutil.rmtree(entry.path, ignore_errors=False, onerror=_remove_readonly)
                deleted_bytes += b
                deleted_files += f
        except Exception:
            # Si un archivo sigue tomado por Discord o un proceso activo, continuar sin colapsar
            continue

    return deleted_bytes, deleted_files

def purge_pycache_recursive(target_directory: str):
    """Busca y purga carpetas __pycache__ y ficheros .pyc evitando recursiones infinitas."""
    purged_folders = 0
    purged_files = 0

    if not os.path.isdir(target_directory):
        return 0, 0

    for root, dirs, files in os.walk(target_directory, topdown=False, followlinks=False):
        for d in dirs:
            if d == "__pycache__":
                folder_path = os.path.join(root, d)
                try:
                    shutil.rmtree(folder_path, ignore_errors=True)
                    purged_folders += 1
                except Exception:
                    pass

        for f in files:
            if f.endswith((".pyc", ".pyo")):
                file_path = os.path.join(root, f)
                try:
                    os.remove(file_path)
                    purged_files += 1
                except Exception:
                    pass

    return purged_folders, purged_files