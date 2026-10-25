import subprocess

TWEAKABLE_SERVICES = [
    {
        "name": "DiagTrack",
        "title": "Telemetría y Diagnóstico (DiagTrack)",
        "desc": "Recopila y envía datos de telemetría a los servidores de Microsoft."
    },
    {
        "name": "dmwappushservice",
        "title": "Servicio de Enrutamiento Push WAP",
        "desc": "Asociado a la telemetría y recolección de eventos de Windows."
    },
    {
        "name": "WerSvc",
        "title": "Informe de Errores de Windows (WerSvc)",
        "desc": "Envía volcados de error y reportes de cuelgues del sistema."
    },
    {
        "name": "Spooler",
        "title": "Cola de Impresión (Spooler)",
        "desc": "Gestor de trabajos de impresora. Puede apagarse si no usas impresora."
    }
]

def get_service_status(service_name: str) -> dict:
    """Consulta si el servicio está corriendo y cuál es su modo de inicio."""
    info = {"running": False, "start_type": "Desconocido"}
    try:
        # Consulta de estado de ejecución
        query = subprocess.run(f"sc query {service_name}", shell=True, capture_output=True, text=True)
        if "RUNNING" in query.stdout:
            info["running"] = True

        # Consulta del tipo de inicio (BOOT, SYSTEM, AUTO_START, DEMAND_START, DISABLED)
        qc = subprocess.run(f"sc qc {service_name}", shell=True, capture_output=True, text=True)
        if "DISABLED" in qc.stdout:
            info["start_type"] = "Deshabilitado"
        elif "AUTO_START" in qc.stdout:
            info["start_type"] = "Automático"
        elif "DEMAND_START" in qc.stdout:
            info["start_type"] = "Manual"
    except Exception:
        pass
    return info

def toggle_service(service_name: str, disable: bool) -> tuple[bool, str]:
    """Habilita o deshabilita un servicio de Windows."""
    try:
        if disable:
            # Detener y deshabilitar
            subprocess.run(f"net stop {service_name} /y", shell=True, capture_output=True)
            res = subprocess.run(f"sc config {service_name} start= disabled", shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                return True, "Servicio detenido y deshabilitado."
            return False, res.stderr or "Error al configurar servicio."
        else:
            # Poner en automático e iniciar
            res = subprocess.run(f"sc config {service_name} start= auto", shell=True, capture_output=True, text=True)
            subprocess.run(f"net start {service_name}", shell=True, capture_output=True)
            if res.returncode == 0:
                return True, "Servicio reactivado e iniciado."
            return False, res.stderr or "Error al iniciar servicio."
    except Exception as e:
        return False, str(e)
