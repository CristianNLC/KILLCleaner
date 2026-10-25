"""Envío de archivos a la Papelera de reciclaje con la API nativa de Windows.

Se usa ``SHFileOperationW`` con ``FOF_ALLOWUNDO``, sin dependencias externas.
Si Windows no puede reciclar el archivo (unidad de red, ruta demasiado larga,
archivo mayor que la papelera...), la función devuelve un error y **el archivo
permanece intacto**: nunca se degrada a borrado permanente.
"""

import ctypes
import os
from ctypes import wintypes

FO_DELETE = 0x0003
FOF_SILENT = 0x0004
FOF_NOCONFIRMATION = 0x0010
FOF_ALLOWUNDO = 0x0040
FOF_NOERRORUI = 0x0400
FOF_WANTNUKEWARNING = 0x4000

MAX_RECYCLE_PATH = 259


class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_uint16),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def move_to_recycle_bin(path):
    """Mueve *path* a la Papelera. Devuelve (ok, mensaje).

    En caso de error el archivo no se toca.
    """
    try:
        full = os.path.abspath(path)
    except Exception as e:
        return False, f"Ruta no válida: {e}"

    if not os.path.isfile(full):
        return False, "El archivo ya no existe o no es un archivo."

    if len(full) > MAX_RECYCLE_PATH:
        return False, (
            "La ruta supera los 259 caracteres y la Papelera no puede procesarla. "
            "El archivo no se eliminó."
        )

    operation = _SHFILEOPSTRUCTW()
    operation.hwnd = None
    operation.wFunc = FO_DELETE
    # Doble terminador nulo: SHFileOperationW espera una lista de rutas.
    operation.pFrom = full + "\0"
    operation.pTo = None
    operation.fFlags = (
        FOF_ALLOWUNDO
        | FOF_NOCONFIRMATION
        | FOF_SILENT
        | FOF_NOERRORUI
        | FOF_WANTNUKEWARNING
    )

    try:
        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
    except Exception as e:
        return False, f"La API de Windows falló: {e}"

    if result != 0:
        return False, f"Windows devolvió el código de error {result}."
    if operation.fAnyOperationsAborted:
        return False, "La operación se canceló."
    if os.path.exists(full):
        return False, "El archivo sigue en su sitio: no llegó a moverse a la Papelera."

    return True, "Archivo movido a la Papelera de reciclaje."
