"""Operaciones de mantenimiento y optimización de Windows."""

import os
import re
import subprocess
import sys

import psutil

from core.reporter import export_maintenance_report  # reexportado por compatibilidad

# Aplicaciones que el Modo Gaming puede cerrar. El usuario decide cuáles.
GAMING_CANDIDATES = {
    "discord.exe": "Discord",
    "spotify.exe": "Spotify",
    "telegram.exe": "Telegram",
    "steamwebhelper.exe": "Steam (web helper)",
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "brave.exe": "Brave",
    "firefox.exe": "Firefox",
    "opera.exe": "Opera",
    "vlc.exe": "VLC",
}

_HEALTH_MAP = {
    "healthy": "OK",
    "warning": "Advertencia",
    "unhealthy": "Falla",
    "unknown": "Desconocido",
}


# --------------------------------------------------------------------------- #
# Modo Gaming (cierre seguro de procesos)
# --------------------------------------------------------------------------- #
def list_running_candidates():
    """Lista las apps de GAMING_CANDIDATES que están abiertas ahora mismo.

    Returns:
        [{"name": "chrome.exe", "label": "Google Chrome", "pids": [123, 456]}]
    """
    found = {}
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = (proc.info.get("name") or "").lower()
            pid = proc.info.get("pid")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if name in GAMING_CANDIDATES and pid:
            found.setdefault(name, []).append(pid)

    return [
        {"name": name, "label": GAMING_CANDIDATES[name], "pids": sorted(pids)}
        for name, pids in sorted(found.items())
    ]


def _close_process(pid: int, force: bool = False, timeout: float = 6.0) -> bool:
    """Pide el cierre amable de un proceso y solo fuerza si se autorizó."""
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return True
    except psutil.AccessDenied:
        return False

    # taskkill sin /F envía WM_CLOSE: la app puede guardar su estado.
    try:
        subprocess.run(
            f"taskkill /PID {int(pid)}", shell=True, capture_output=True, timeout=20
        )
    except Exception:
        pass

    try:
        proc.wait(timeout=timeout)
        return True
    except psutil.NoSuchProcess:
        return True
    except psutil.TimeoutExpired:
        if not force:
            return False
        try:
            proc.kill()
            proc.wait(timeout=5)
            return True
        except Exception:
            return False
    except Exception:
        return False


def activate_game_mode(process_names=None, force=False, log_callback=None):
    """Cierra las apps seleccionadas y purga el portapapeles.

    Args:
        process_names: Nombres de ejecutable a cerrar (p. ej. ["chrome.exe"]).
            Si es None, no se cierra nada.
        force: Si True, mata el proceso cuando el cierre amable no responde.
        log_callback: Función opcional para registrar el progreso.

    Returns:
        {"closed": [nombres], "failed": [nombres], "skipped": bool}
    """
    candidates = list_running_candidates()
    if process_names is not None:
        wanted = {n.lower() for n in process_names}
        candidates = [c for c in candidates if c["name"] in wanted]

    closed, failed = [], []
    for candidate in candidates:
        for pid in candidate["pids"]:
            ok = _close_process(pid, force=force)
            if ok:
                closed.append(candidate["label"])
                if log_callback:
                    log_callback(f"[✓] Cerrado: {candidate['label']} (PID {pid})")
            else:
                failed.append(candidate["label"])
                if log_callback:
                    log_callback(f"[!] No se pudo cerrar: {candidate['label']} (PID {pid})")

    # Limpieza de portapapeles (inocua)
    subprocess.run('cmd.exe /c "echo off | clip"', shell=True, capture_output=True)

    return {"closed": closed, "failed": failed}


# --------------------------------------------------------------------------- #
# Diagnóstico
# --------------------------------------------------------------------------- #
def check_smart_status():
    """Consulta la salud física del disco principal (solo lectura).

    Usa Get-PhysicalDisk (PowerShell) y recurre a wmic solo como respaldo,
    porque wmic fue eliminado en Windows 11 24H2.
    """
    ps_cmd = (
        "powershell -NoProfile -NonInteractive -Command "
        '"Get-PhysicalDisk | Select-Object -ExpandProperty HealthStatus"'
    )
    try:
        res = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True, timeout=25)
        values = [line.strip() for line in (res.stdout or "").splitlines() if line.strip()]
        if values:
            mapped = [_HEALTH_MAP.get(v.lower(), v) for v in values]
            problemas = sorted({m for m in mapped if m != "OK"})
            return "OK" if not problemas else ", ".join(problemas)
    except Exception:
        pass

    try:
        res = subprocess.run(
            "wmic diskdrive get status",
            shell=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        lines = [
            line.strip()
            for line in (res.stdout or "").splitlines()
            if line.strip() and "Status" not in line
        ]
        if lines:
            return lines[0]
    except Exception:
        pass

    return "Desconocido"


def run_sfc_scan(log_callback=None):
    """Ejecuta sfc /scannow enviando la salida al log."""
    if log_callback:
        log_callback("[*] Iniciando comprobador de archivos de sistema (SFC)...")
    try:
        process = subprocess.Popen(
            "sfc /scannow",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        for line in process.stdout:
            if log_callback and line.strip():
                log_callback(f"[SFC] {line.strip()}")
        process.wait()
        return process.returncode
    except Exception as e:
        if log_callback:
            log_callback(f"[x] No se pudo ejecutar SFC: {e}")
        return -1


# --------------------------------------------------------------------------- #
# Optimización de disco
# --------------------------------------------------------------------------- #
def optimize_drive_trim(drive_letter="C:"):
    """Ejecuta TRIM u optimización de unidad en Windows."""
    drive = (drive_letter or "C:").strip().upper()
    if not re.fullmatch(r"[A-Z]:", drive):
        return False, f"Unidad no válida: {drive_letter!r}. Se esperaba algo como 'C:'."

    try:
        cmd = f"defrag {drive} /L /O /V"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600)
        output = res.stdout.strip() if res.stdout else res.stderr.strip()
        if res.returncode == 0 or "completad" in output.lower() or "complete" in output.lower():
            return True, output if output else "Optimización TRIM completada con éxito."

        fallback = subprocess.run(
            f"defrag {drive} /U /V", shell=True, capture_output=True, text=True, timeout=3600
        )
        out_fallback = fallback.stdout.strip() if fallback.stdout else "Optimización finalizada."
        return fallback.returncode == 0, out_fallback
    except subprocess.TimeoutExpired:
        return False, "La optimización superó el tiempo máximo de espera."
    except Exception as e:
        return False, f"Error al ejecutar la optimización: {str(e)}"


def create_restore_point(description="KILLCleaner_Backup"):
    """Crea un punto de restauración del sistema en Windows usando PowerShell."""
    safe_desc = re.sub(r"[^\w\-\. ]", "", description)[:60] or "KILLCleaner_Backup"
    try:
        cmd = (
            "powershell -NoProfile -ExecutionPolicy Bypass -Command "
            f'"Checkpoint-Computer -Description \'{safe_desc}\' -RestorePointType \'MODIFY_SETTINGS\'"'
        )
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)
        if res.returncode == 0:
            return True, "Punto de restauración creado con éxito."

        err = (
            res.stderr.strip()
            if res.stderr
            else "Restauración del sistema deshabilitada o requiere permisos de Administrador."
        )
        return False, err
    except subprocess.TimeoutExpired:
        return False, "La creación del punto de restauración superó el tiempo de espera."
    except Exception as e:
        return False, str(e)


# --------------------------------------------------------------------------- #
# Tareas programadas
# --------------------------------------------------------------------------- #
def configure_scheduled_task(enable=True, frequency="WEEKLY"):
    """Configura o elimina la tarea programada de limpieza en Windows."""
    task_name = "KILLCleaner_AutoClean"
    try:
        if not enable:
            cmd = f'schtasks /delete /tn "{task_name}" /f'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            if (
                res.returncode == 0
                or "no existe" in (res.stderr or "").lower()
                or "not find" in (res.stderr or "").lower()
            ):
                return True, "Tarea programada desactivada con éxito."
            return False, (res.stderr or "").strip()

        # Comando correcto tanto desde fuente como desde el .exe empaquetado
        if getattr(sys, "frozen", False):
            tr_cmd = f'"{sys.executable}" --silent-clean'
        else:
            main_script = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "app.pyw")
            )
            tr_cmd = f'"{sys.executable}" "{main_script}" --silent-clean'

        sc_val = "WEEKLY" if str(frequency).upper() == "WEEKLY" else "DAILY"
        cmd = f'schtasks /create /tn "{task_name}" /tr "{tr_cmd}" /sc {sc_val} /f'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if res.returncode == 0:
            return True, f"Tarea programada activada con frecuencia ({sc_val})."
        return False, (res.stderr or "").strip() or "Error al registrar la tarea programada."
    except subprocess.TimeoutExpired:
        return False, "El Programador de Tareas no respondió a tiempo."
    except Exception as e:
        return False, str(e)
