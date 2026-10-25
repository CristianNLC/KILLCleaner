"""Recorrido de carpetas con ``os.scandir``.

Sustituye a ``os.walk`` en las operaciones de limpieza y de búsqueda de
duplicados. Ventajas:

* Usa la información que ya entrega ``scandir`` (tipo y tamaño), evitando un
  ``stat`` adicional por archivo.
* No sigue enlaces simbólicos ni puntos de unión, por lo que nunca sale de la
  carpeta objetivo (``os.walk`` puede descender en uniones de Windows).
* Soporta rutas largas mediante el prefijo ``\\\\?\\``.
"""

import os
import stat

from core.app_paths import extended_path

_FILE_ATTRIBUTE_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _cancelled(cancel_event):
    return cancel_event is not None and cancel_event.is_set()


def _is_reparse_point(entry):
    try:
        info = entry.stat(follow_symlinks=False)
    except OSError:
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    return bool(attributes & _FILE_ATTRIBUTE_REPARSE_POINT)


def iter_tree(root, cancel_event=None, skip_dir=None, on_skip=None):
    """Recorre ``root`` y genera ``(directorio, [entradas de archivo])``.

    Args:
        root: Carpeta inicial.
        cancel_event: ``threading.Event`` opcional para detenerse.
        skip_dir: Función ``(ruta) -> bool`` para podar carpetas.
        on_skip: Función ``(ruta)`` llamada al podar una carpeta.

    Solo se devuelven archivos regulares; enlaces y uniones se omiten.
    """
    pending = [extended_path(root)]
    while pending:
        if _cancelled(cancel_event):
            return

        current = pending.pop()
        try:
            with os.scandir(current) as iterator:
                entries = list(iterator)
        except OSError:
            continue

        files = []
        subdirs = []
        for entry in entries:
            if _cancelled(cancel_event):
                return
            try:
                if entry.is_dir(follow_symlinks=False):
                    if _is_reparse_point(entry):
                        continue
                    child = entry.path
                    if skip_dir is not None and skip_dir(child):
                        if on_skip is not None:
                            on_skip(child)
                        continue
                    subdirs.append(child)
                elif entry.is_file(follow_symlinks=False):
                    files.append(entry)
            except OSError:
                continue

        yield current, files
        # Pila: el último en entrar es el primero en salir; se invierte para
        # conservar el orden natural (primero la primera subcarpeta).
        pending.extend(reversed(subdirs))
