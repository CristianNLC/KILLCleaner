"""Registro de auditoría de KILLCleaner.

Cada acción relevante (limpieza, borrado de duplicados, punto de restauración)
se añade como una línea JSON a ``logs/audit.jsonl``. El archivo es de solo
añadir: nunca se reescribe ni se borra desde la aplicación. Si supera 5 MB se
rota a un nombre con fecha para que no crezca sin control, conservando todo el
historial anterior.
"""

import json
import os
import threading
from datetime import datetime

from core.app_paths import ensure_dir, logs_dir

_LOCK = threading.Lock()
MAX_BYTES = 5 * 1024 * 1024


def audit_path():
    """Ruta absoluta del registro de auditoría."""
    return os.path.join(logs_dir(), "audit.jsonl")


def _rotate_if_needed(path):
    try:
        if os.path.getsize(path) < MAX_BYTES:
            return
    except OSError:
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        os.replace(path, os.path.join(os.path.dirname(path), f"audit-{stamp}.jsonl"))
    except OSError:
        pass


def log_action(
    action,
    target="",
    bytes_freed=0,
    files=0,
    dry_run=False,
    result="ok",
    details=None,
):
    """Añade una entrada al registro. Devuelve True si se escribió.

    Nunca lanza excepciones: la auditoría no debe interrumpir una limpieza.
    """
    entry = {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "action": str(action),
        "target": str(target or ""),
        "bytes": int(bytes_freed or 0),
        "files": int(files or 0),
        "dry_run": bool(dry_run),
        "result": str(result),
    }
    if details:
        entry["details"] = details

    try:
        line = json.dumps(entry, ensure_ascii=False)
    except (TypeError, ValueError):
        return False

    try:
        with _LOCK:
            ensure_dir(logs_dir())
            path = audit_path()
            _rotate_if_needed(path)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        return True
    except Exception:
        return False
