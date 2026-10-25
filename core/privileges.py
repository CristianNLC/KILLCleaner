"""Utilidades de privilegios para KILLCleaner.

La mayoría de funciones (Prefetch, SFC, DISM, servicios HKLM, winsock reset)
requieren permisos de administrador. Aquí se centraliza la detección y la
reelevación voluntaria del proceso.
"""

import ctypes
import os
import sys


def is_admin() -> bool:
    """Devuelve True si el proceso actual tiene privilegios elevados."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    """Relanza la aplicación elevada (UAC). Devuelve True si se lanzó.

    La instancia actual debe cerrarse después de llamar a esta función.
    """
    try:
        if getattr(sys, "frozen", False):
            exe = sys.executable
            params = ""
        else:
            exe = sys.executable
            params = f'"{os.path.abspath(sys.argv[0])}"'

        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, params, os.getcwd(), 1
        )
        # ShellExecuteW devuelve un valor > 32 cuando tuvo éxito
        return result > 32
    except Exception:
        return False
