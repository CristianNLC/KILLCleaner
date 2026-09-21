import subprocess

def run_dism_command(cmd_args: str, log_callback=None) -> int:
    """Ejecuta un comando DISM en modo streaming hacia la consola de la UI."""
    full_cmd = f"dism.exe /Online /Cleanup-Image {cmd_args}"
    if log_callback:
        log_callback(f"[DISM] Ejecutando: {full_cmd}\n")

    process = subprocess.Popen(
        full_cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace"
    )

    for line in process.stdout:
        line_clean = line.strip()
        if line_clean and log_callback:
            log_callback(f"[DISM] {line_clean}")

    process.wait()
    return process.returncode

def analyze_component_store(log_callback=None) -> int:
    """Analiza WinSxS e informa si se recomienda limpieza."""
    return run_dism_command("/AnalyzeComponentStore", log_callback)

def cleanup_component_store(reset_base: bool = False, log_callback=None) -> int:
    """
    Purga versiones viejas de actualizaciones de Windows.
    Si reset_base es True, no se podrán desinstalar actualizaciones previas,
    pero libera el máximo de espacio posible.
    """
    args = "/StartComponentCleanup /ResetBase" if reset_base else "/StartComponentCleanup"
    return run_dism_command(args, log_callback)

def restore_health_image(log_callback=None) -> int:
    """Repara corrupción de la imagen del sistema descargando archivos originales."""
    return run_dism_command("/RestoreHealth", log_callback)