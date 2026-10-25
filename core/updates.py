"""Comprobación de actualizaciones contra las releases de GitHub.

Solo consulta información pública: no descarga ni instala nada. Si hay una
versión nueva, la interfaz ofrece abrir la página de descarga en el navegador.
"""

import re

import requests

from core.version import APP_VERSION

RELEASES_API = "https://api.github.com/repos/CristianNLC/KILLCleaner/releases/latest"
RELEASES_PAGE = "https://github.com/CristianNLC/KILLCleaner/releases/latest"
TIMEOUT = 8


def parse_version(text):
    """Convierte ``v1.2.3`` en ``(1, 2, 3)``; devuelve ``()`` si no hay números."""
    if not text:
        return ()
    match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", str(text))
    if not match:
        return ()
    return tuple(int(part or 0) for part in match.groups())


def is_newer(remote, local=APP_VERSION):
    """True si ``remote`` es una versión superior a ``local``."""
    remote_parts = parse_version(remote)
    local_parts = parse_version(local)
    if not remote_parts:
        return False
    return remote_parts > local_parts


def check_for_update(session=None, timeout=TIMEOUT):
    """Consulta la última release publicada.

    Returns:
        ``{"ok": bool, "latest": str, "url": str, "newer": bool, "error": str}``
    """
    client = session or requests
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"KILLCleaner/{APP_VERSION}",
    }
    try:
        response = client.get(RELEASES_API, timeout=timeout, headers=headers)
    except Exception as exc:
        return {
            "ok": False,
            "latest": "",
            "url": RELEASES_PAGE,
            "newer": False,
            "error": f"Sin conexión con GitHub: {exc}",
        }

    if response.status_code == 403:
        return {
            "ok": False,
            "latest": "",
            "url": RELEASES_PAGE,
            "newer": False,
            "error": "GitHub limitó temporalmente las consultas. Inténtalo más tarde.",
        }
    if response.status_code != 200:
        return {
            "ok": False,
            "latest": "",
            "url": RELEASES_PAGE,
            "newer": False,
            "error": f"GitHub respondió con HTTP {response.status_code}.",
        }

    try:
        data = response.json()
    except ValueError:
        return {
            "ok": False,
            "latest": "",
            "url": RELEASES_PAGE,
            "newer": False,
            "error": "La respuesta de GitHub no es válida.",
        }

    latest = str(data.get("tag_name") or data.get("name") or "").strip()
    url = str(data.get("html_url") or RELEASES_PAGE)
    return {
        "ok": True,
        "latest": latest or APP_VERSION,
        "url": url,
        "newer": is_newer(latest),
        "error": "",
    }
