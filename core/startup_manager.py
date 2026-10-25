import os
import re
import winreg

STARTUP_LOCATIONS = [
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU\\Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM\\Run")
]

BACKUP_SUBKEY = r"Software\KILLCleaner\DisabledStartup"

def _clean_path(cmd_string: str) -> str:
    cmd = cmd_string.strip()
    if cmd.startswith('"'):
        match = re.match(r'^"([^"]+)"', cmd)
        return match.group(1) if match else cmd
    return cmd.split()[0] if cmd else ""

def list_startup_entries():
    """
    Retorna una lista de diccionarios con las entradas activas y deshabilitadas.
    Cada elemento: {'name', 'command', 'path', 'location', 'root', 'subkey', 'enabled', 'exists'}
    """
    entries = []

    # 1. Entradas Activas
    for root_key, subkey, label in STARTUP_LOCATIONS:
        try:
            with winreg.OpenKey(root_key, subkey, 0, winreg.KEY_READ) as k:
                count = winreg.QueryInfoKey(k)[1]
                for i in range(count):
                    name, val, _ = winreg.EnumValue(k, i)
                    val_str = str(val).strip()
                    raw_p = _clean_path(val_str)
                    entries.append({
                        "name": name,
                        "command": val_str,
                        "path": raw_p,
                        "location": label,
                        "root": root_key,
                        "subkey": subkey,
                        "enabled": True,
                        "exists": os.path.exists(raw_p) if raw_p else False
                    })
        except (FileNotFoundError, PermissionError):
            continue

    # 2. Entradas Deshabilitadas (Almacenadas en el almacén interno de KILLCleaner)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, BACKUP_SUBKEY, 0, winreg.KEY_READ) as bk:
            count = winreg.QueryInfoKey(bk)[1]
            for i in range(count):
                name, val, _ = winreg.EnumValue(bk, i)
                val_str = str(val).strip()
                # El valor guardado contiene "ROOT_LABEL|ORIGINAL_SUBKEY|COMANDO"
                parts = val_str.split("|", 2)
                if len(parts) == 3:
                    orig_label, orig_sub, orig_cmd = parts
                    raw_p = _clean_path(orig_cmd)
                    entries.append({
                        "name": name,
                        "command": orig_cmd,
                        "path": raw_p,
                        "location": f"{orig_label} (Desactivado)",
                        "root": winreg.HKEY_CURRENT_USER if "HKCU" in orig_label else winreg.HKEY_LOCAL_MACHINE,
                        "subkey": orig_sub,
                        "enabled": False,
                        "exists": os.path.exists(raw_p) if raw_p else False
                    })
    except (FileNotFoundError, PermissionError):
        pass

    return entries

def disable_startup_entry(entry: dict):
    """Mueve la entrada del registro a la subclave interna de deshabilitados."""
    try:
        # 1. Guardar en respaldo
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, BACKUP_SUBKEY) as bk:
            orig_root_label = "HKCU" if entry["root"] == winreg.HKEY_CURRENT_USER else "HKLM"
            store_val = f"{orig_root_label}|{entry['subkey']}|{entry['command']}"
            winreg.SetValueEx(bk, entry["name"], 0, winreg.REG_SZ, store_val)

        # 2. Eliminar de la clave activa original
        with winreg.OpenKey(entry["root"], entry["subkey"], 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, entry["name"])

        return True, "Entrada deshabilitada con éxito."
    except PermissionError:
        return False, "Permiso denegado. Se requieren privilegios de Administrador para HKLM."
    except Exception as e:
        return False, f"Error: {e}"

def enable_startup_entry(entry: dict):
    """Restaura la entrada a su clave original de inicio automático."""
    try:
        # 1. Restaurar en el registro activo
        with winreg.OpenKey(entry["root"], entry["subkey"], 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, entry["name"], 0, winreg.REG_SZ, entry["command"])

        # 2. Borrar del almacén de deshabilitados
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, BACKUP_SUBKEY, 0, winreg.KEY_SET_VALUE) as bk:
            winreg.DeleteValue(bk, entry["name"])

        return True, "Entrada reactivada con éxito."
    except PermissionError:
        return False, "Permiso denegado. Se requieren privilegios de Administrador."
    except Exception as e:
        return False, f"Error: {e}"
