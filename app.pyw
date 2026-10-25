"""KILLCleaner - Centro de optimización y mantenimiento de Windows.

Uso:
    python app.pyw                 Abre la interfaz gráfica.
    python app.pyw --silent-clean  Limpieza automática sin interfaz (tareas
                                   programadas). Escribe un registro en logs/.
"""

import ctypes
import os
import sys
from datetime import datetime

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "killsystem.killcleaner.suite.1.0"
    )
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.single_instance import SingleInstance  # noqa: E402

_instance = SingleInstance(r"Local\KILLCleaner.SingleInstance")


def _write_log(lines):
    """Escribe el registro de la limpieza automática en logs/."""
    from core.app_paths import ensure_dir, logs_dir

    try:
        folder = ensure_dir(logs_dir())
        path = os.path.join(folder, f"auto_clean_{datetime.now():%Y-%m-%d}.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass


def _run_silent_clean() -> int:
    """Limpieza no interactiva: solo temporales y Prefetch.

    No vacía la papelera ni cierra aplicaciones: una tarea programada nunca
    debe destruir datos del usuario sin supervisión.
    """
    from core.audit import log_action
    from core.cleaner import clean_directory, get_target_directories

    started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"\n===== Limpieza automática: {started} ====="]

    if not _instance.acquire():
        lines.append("[!] Otra instancia de KILLCleaner está activa. Se omite la limpieza.")
        _write_log(lines)
        return 0

    total_bytes = 0
    total_files = 0
    try:
        for label, path in get_target_directories().items():
            freed, count = clean_directory(path)
            total_bytes += freed
            total_files += count
            lines.append(
                f"[>] {label}: {count} archivos, {round(freed / (1024 * 1024), 2)} MB"
            )
        lines.append(
            f"[✓] Total: {round(total_bytes / (1024 * 1024), 2)} MB liberados "
            f"en {total_files} archivos."
        )
        log_action(
            "clean_temp_silent",
            target="temporales",
            bytes_freed=total_bytes,
            files=total_files,
            details={"origin": "scheduled_task"},
        )
        _write_log(lines)
        return 0
    except Exception as e:
        lines.append(f"[x] Error durante la limpieza automática: {e}")
        log_action(
            "clean_temp_silent",
            target="temporales",
            result="error",
            details={"origin": "scheduled_task", "message": str(e)},
        )
        _write_log(lines)
        return 1
    finally:
        _instance.release()


def main() -> int:
    args = {a.lower() for a in sys.argv[1:]}

    if "--silent-clean" in args:
        return _run_silent_clean()

    if not _instance.acquire():
        try:
            import tkinter.messagebox as messagebox

            messagebox.showinfo(
                "KILLCleaner", "KILLCleaner ya está abierto en otra ventana."
            )
        except Exception:
            pass
        return 0

    from ui.main_window import CleanerWindow

    app = CleanerWindow()
    app.mainloop()
    _instance.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
