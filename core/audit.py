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


def _audit_files():
    """Rutas de auditoría de más antigua a más reciente (incluye rotados)."""
    try:
        folder = logs_dir()
        names = sorted(
            name
            for name in os.listdir(folder)
            if name.startswith("audit") and name.endswith(".jsonl")
        )
        return [os.path.join(folder, name) for name in names]
    except OSError:
        return []


def read_entries(limit=None, include_rotated=True):
    """Lee las entradas de auditoría, de la más reciente a la más antigua.

    Las líneas dañadas se ignoran para que un archivo a medio escribir no
    rompa el historial. ``limit`` corta la lista después de ordenar.
    """
    entries = []
    paths = _audit_files() if include_rotated else [audit_path()]
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    if isinstance(item, dict):
                        entries.append(item)
        except OSError:
            continue

    entries.sort(key=lambda item: str(item.get("ts", "")), reverse=True)
    if limit is not None:
        entries = entries[:limit]
    return entries


def summarize(entries):
    """Totales útiles para el historial y los informes."""
    total_bytes = 0
    total_files = 0
    by_action = {}
    for item in entries:
        try:
            total_bytes += int(item.get("bytes", 0) or 0)
            total_files += int(item.get("files", 0) or 0)
        except (TypeError, ValueError):
            continue
        action = str(item.get("action", "desconocida"))
        by_action[action] = by_action.get(action, 0) + 1
    return {
        "count": len(entries),
        "bytes": total_bytes,
        "files": total_files,
        "by_action": by_action,
    }


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
