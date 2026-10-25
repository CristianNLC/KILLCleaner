"""Búsqueda de los archivos más grandes de una carpeta o unidad.

Solo lee metadatos: no abre, mueve ni borra nada. La interfaz se encarga de
enviar a la Papelera lo que el usuario confirme.
"""

import os

from core.app_paths import display_path
from core.walker import iter_tree

DEFAULT_MIN_BYTES = 100 * 1024 * 1024  # 100 MB
DEFAULT_LIMIT = 200


def find_large_files(
    root,
    min_size_bytes=DEFAULT_MIN_BYTES,
    limit=DEFAULT_LIMIT,
    cancel_event=None,
):
    """Devuelve los archivos de ``root`` que superan ``min_size_bytes``.

    El resultado se ordena de mayor a menor y se corta en ``limit`` elementos.
    Si se activa ``cancel_event`` devuelve una lista vacía.
    """
    if not root or not os.path.isdir(root):
        return []

    found = []
    for _directory, files in iter_tree(root, cancel_event=cancel_event):
        for entry in files:
            if cancel_event is not None and cancel_event.is_set():
                return []
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            if info.st_size < min_size_bytes:
                continue
            found.append(
                {
                    "path": display_path(entry.path),
                    "size": info.st_size,
                    "mtime": info.st_mtime,
                }
            )
            # Podar de vez en cuando para no acumular millones de entradas.
            if len(found) > limit * 4:
                found.sort(key=lambda item: item["size"], reverse=True)
                del found[limit:]

    found.sort(key=lambda item: item["size"], reverse=True)
    return found[:limit]
