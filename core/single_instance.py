"""Control de instancia única mediante un mutex nativo de Windows.

Evita que dos copias de KILLCleaner limpien el sistema al mismo tiempo (lo que
podría provocar borrados parciales o bloqueos de archivos).
"""

import ctypes
from ctypes import wintypes

ERROR_ALREADY_EXISTS = 183


class SingleInstance:
    """Mutex con nombre: solo una instancia puede mantenerlo adquirido."""

    def __init__(self, name: str = r"Local\KILLCleaner.SingleInstance"):
        self._name = name
        self._handle = None

    def acquire(self) -> bool:
        """Intenta tomar el mutex.

        Devuelve True si esta instancia es la única activa. Si el sistema no
        permite crear el mutex (entorno no Windows o error inesperado), se
        devuelve True para no bloquear la aplicación por un fallo ajeno.
        """
        if self._handle:
            return True

        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            kernel32.CreateMutexW.argtypes = [
                wintypes.LPVOID,
                wintypes.BOOL,
                wintypes.LPCWSTR,
            ]
            handle = kernel32.CreateMutexW(None, False, self._name)
            last_error = ctypes.get_last_error()
        except Exception:
            return True

        if not handle:
            return True

        if last_error == ERROR_ALREADY_EXISTS:
            self._close(handle)
            return False

        self._handle = handle
        return True

    def release(self) -> None:
        """Libera el mutex (se libera solo al terminar el proceso)."""
        if self._handle:
            self._close(self._handle)
            self._handle = None

    @staticmethod
    def _close(handle) -> None:
        try:
            ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(handle)
        except Exception:
            pass
