"""Registro rotativo de KILLCleaner en ``logs/killcleaner.log``.

La interfaz muestra el registro en memoria, pero un archivo rotativo permite
diagnosticar fallos ocurridos después de cerrar la ventana. Nunca se envía nada
a la red: el archivo se queda en el equipo del usuario.
"""

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler

from core.app_paths import ensure_dir, logs_dir

MAX_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 3
_FORMAT = "%(asctime)s %(levelname)-8s [%(threadName)s] %(name)s: %(message)s"
_ROOT_NAME = "killcleaner"


def log_path():
    """Ruta absoluta del registro rotativo."""
    return os.path.join(logs_dir(), "killcleaner.log")


def setup_logging(level=logging.INFO):
    """Configura el logger de la aplicación una sola vez.

    Si no se puede crear el archivo (por ejemplo, una carpeta de solo lectura),
    se usa un manejador nulo: la aplicación sigue funcionando sin registro.
    """
    logger = logging.getLogger(_ROOT_NAME)
    if getattr(logger, "_killcleaner_configured", False):
        return logger

    logger.setLevel(level)
    logger.propagate = False

    try:
        ensure_dir(logs_dir())
        handler = RotatingFileHandler(
            log_path(),
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
    except OSError:
        handler = logging.NullHandler()

    handler.setFormatter(logging.Formatter(_FORMAT))
    logger.addHandler(handler)
    logger._killcleaner_configured = True
    return logger


def get_logger(name=""):
    """Devuelve un logger hijo de ``killcleaner`` (opcionalmente con nombre)."""
    suffix = f".{name}" if name else ""
    return logging.getLogger(f"{_ROOT_NAME}{suffix}")


def install_exception_hooks():
    """Anota los fallos no controlados en el registro rotativo.

    No escribe en la consola: el ejecutable se distribuye con ``pythonw``, que
    no tiene salida estándar. El objetivo es que un cierre inesperado deje
    rastro en ``logs/killcleaner.log``.
    """
    logger = get_logger("crash")

    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical(
            "Excepción no controlada",
            exc_info=(exc_type, exc_value, exc_tb),
        )

    def _thread_hook(args):
        if args.exc_type is SystemExit:
            return
        logger.critical(
            "Excepción no controlada en el hilo %s",
            getattr(args.thread, "name", "?"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _hook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _thread_hook
