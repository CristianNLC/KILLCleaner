import os
import sys
import subprocess
import psutil
from datetime import datetime

GAMING_TARGET_PROCESSES = {
    "discord.exe", "spotify.exe", "telegram.exe", 
    "steamwebhelper.exe", "chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"
}

def activate_game_mode():
    """Finaliza apps pesadas en segundo plano y purga portapapeles."""
    terminated = 0
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() in GAMING_TARGET_PROCESSES:
                proc.kill()
                terminated += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Limpieza de portapapeles
    subprocess.run('cmd.exe /c "echo off | clip"', shell=True, capture_output=True)
    return terminated

def check_smart_status():
    """Consulta la salud física del disco principal (S.M.A.R.T.)."""
    try:
        res = subprocess.run("wmic diskdrive get status", shell=True, capture_output=True, text=True)
        lines = [line.strip() for line in res.stdout.splitlines() if line.strip() and "Status" not in line]
        return lines[0] if lines else "Desconocido"
    except Exception:
        return "Error al consultar"

def run_sfc_scan(log_callback=None):
    """Ejecuta sfc /scannow enviando la salida al log."""
    if log_callback:
        log_callback("[*] Iniciando comprobador de archivos de sistema (SFC)...")
    process = subprocess.Popen("sfc /scannow", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        if log_callback and line.strip():
            log_callback(f"[SFC] {line.strip()}")
    process.wait()
    return process.returncode

def optimize_drive_trim(drive_letter="C:"):
    """Ejecuta TRIM u optimización de unidad en Windows."""
    try:
        drive = drive_letter.rstrip("\\").rstrip(":") + ":"
        cmd = f"defrag {drive} /L /O /V"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = res.stdout.strip() if res.stdout else res.stderr.strip()
        if res.returncode == 0 or "completad" in output.lower() or "complete" in output.lower():
            return True, output if output else "Optimización TRIM completada con éxito."
        else:
            fallback = subprocess.run(f"defrag {drive} /U /V", shell=True, capture_output=True, text=True)
            out_fallback = fallback.stdout.strip() if fallback.stdout else "Optimización finalizada."
            return fallback.returncode == 0, out_fallback
    except Exception as e:
        return False, f"Error al ejecutar la optimización: {str(e)}"

def create_restore_point(description="KILLCleaner_Backup"):
    """Crea un punto de restauración del sistema en Windows usando PowerShell."""
    try:
        cmd = f'powershell -ExecutionPolicy Bypass -Command "Checkpoint-Computer -Description \'{description}\' -RestorePointType \'MODIFY_SETTINGS\'"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            return True, "Punto de restauración creado con éxito."
        else:
            err = res.stderr.strip() if res.stderr else "Restauración del sistema deshabilitada o requiere permisos de Administrador."
            return False, err
    except Exception as e:
        return False, str(e)

def configure_scheduled_task(enable=True, frequency="WEEKLY"):
    """Configura o elimina la tarea programada de limpieza en Windows."""
    task_name = "KILLCleaner_AutoClean"
    try:
        if not enable:
            cmd = f'schtasks /delete /tn "{task_name}" /f'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0 or "no existe" in res.stderr.lower() or "not find" in res.stderr.lower():
                return True, "Tarea programada desactivada con éxito."
            else:
                return False, res.stderr.strip()
        else:
            py_exe = sys.executable
            main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.pyw"))
            tr_cmd = f'"{py_exe}" "{main_script}" --silent-clean'
            sc_val = "WEEKLY" if frequency.upper() == "WEEKLY" else "DAILY"
            cmd = f'schtasks /create /tn "{task_name}" /tr "{tr_cmd}" /sc {sc_val} /f'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                return True, f"Tarea programada activada con frecuencia ({sc_val})."
            else:
                return False, res.stderr.strip() if res.stderr else "Error al registrar la tarea programada."
    except Exception as e:
        return False, str(e)

def export_maintenance_report(log_content, stats_dict, target_path):
    """Genera un archivo de informe de auditoría y mantenimiento en formato texto."""
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_lines = [
            "============================================================",
            "                KILLCleaner Maintenance Report              ",
            "============================================================",
            f"Fecha de Generación: {now_str}",
            "Sistema Operativo: Windows",
            "------------------------------------------------------------",
            "RESUMEN DE ESTADO Y SALUD DEL SISTEMA:",
            f"  - Salud de Disco (SMART) : {stats_dict.get('smart', 'Desconocido')}",
            f"  - Espacio Libre en C:   : {stats_dict.get('disk_free', 'Calculando...')}",
            f"  - Memoria RAM en Uso   : {stats_dict.get('ram_used', 'Calculando...')}",
            f"  - Residuos Estimados   : {stats_dict.get('trash', '-- MB')}",
            "------------------------------------------------------------",
            "REGISTRO DE OPERACIONES Y MANTENIMIENTOS REALIZADOS:",
            ""
        ]
        if log_content:
            report_lines.append(log_content)
        else:
            report_lines.append("No se registraron acciones en esta sesión.")
        
        report_lines.extend([
            "",
            "============================================================",
            "            Fin del Informe - KILLCleaner v1.0              ",
            "============================================================"
        ])

        with open(target_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        return True, "Informe de mantenimiento exportado con éxito."
    except Exception as e:
        return False, f"Error al guardar el informe: {str(e)}"