"""Diagnóstico de arranque a partir del registro de eventos de Windows.

Lee el canal ``Microsoft-Windows-Diagnostics-Performance/Operational``
(evento 100), que Windows rellena con la duración de cada arranque. Es una
operación de solo lectura.
"""

import json
import shutil
import subprocess

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell") or "powershell"

_SCRIPT = """
$ErrorActionPreference = 'Stop'
$events = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Diagnostics-Performance/Operational'; Id=100} -MaxEvents __LIMIT__
$result = foreach ($ev in $events) {
  $xml = [xml]$ev.ToXml()
  $data = @{}
  foreach ($d in $xml.Event.EventData.Data) { $data[$d.Name] = $d.'#text' }
  [pscustomobject]@{
    time = $ev.TimeCreated.ToString('o')
    boot_ms = [int]$data['BootTime']
    main_path_ms = [int]$data['MainPathBootTime']
    post_boot_ms = [int]$data['BootPostBootTime']
  }
}
$result | ConvertTo-Json -Compress
"""


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def get_boot_history(limit=10, timeout=25):
    """Devuelve los últimos arranques medidos por Windows.

    Returns:
        ``{"ok": bool, "events": [...], "error": str}``. Cada evento incluye
        ``time`` (ISO 8601), ``boot_ms``, ``main_path_ms`` y ``post_boot_ms``.
    """
    try:
        limit = max(1, int(limit))
    except (TypeError, ValueError):
        limit = 10

    try:
        result = subprocess.run(
            [
                _POWERSHELL,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                _SCRIPT.replace("__LIMIT__", str(limit)),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=_CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "events": [], "error": "Windows tardó demasiado en responder."}
    except Exception as exc:
        return {"ok": False, "events": [], "error": f"No se pudo consultar el registro: {exc}"}

    stderr = (result.stderr or "").strip()
    if result.returncode != 0:
        lowered = stderr.lower()
        if "no events" in lowered or "no se encontr" in lowered:
            return {"ok": True, "events": [], "error": ""}
        return {"ok": False, "events": [], "error": stderr or f"PowerShell terminó con código {result.returncode}."}

    raw = (result.stdout or "").strip()
    if not raw or raw == "null":
        return {"ok": True, "events": [], "error": ""}

    try:
        data = json.loads(raw)
    except ValueError:
        return {"ok": False, "events": [], "error": "La respuesta del registro no es válida."}

    if isinstance(data, dict):
        data = [data]

    events = []
    for item in data:
        if not isinstance(item, dict):
            continue
        events.append(
            {
                "time": str(item.get("time", "")),
                "boot_ms": _as_int(item.get("boot_ms")),
                "main_path_ms": _as_int(item.get("main_path_ms")),
                "post_boot_ms": _as_int(item.get("post_boot_ms")),
            }
        )
    return {"ok": True, "events": events, "error": ""}


def summarize(events):
    """Resumen de duraciones. El primer evento es el arranque más reciente."""
    durations = [event["boot_ms"] for event in events if event.get("boot_ms", 0) > 0]
    if not durations:
        return {}
    return {
        "count": len(durations),
        "last": durations[0],
        "average": int(sum(durations) / len(durations)),
        "min": min(durations),
        "max": max(durations),
    }


def format_duration(milliseconds):
    """Convierte milisegundos en un texto legible (``3 min 1 s``)."""
    try:
        milliseconds = max(0, int(milliseconds))
    except (TypeError, ValueError):
        return "—"
    seconds = milliseconds / 1000
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes, remainder = divmod(int(round(seconds)), 60)
    return f"{minutes} min {remainder} s"
