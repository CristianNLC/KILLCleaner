"""Ejecuta las suites de regresión que viven en ``tests/scripts``.

Cada script imprime cuántas comprobaciones pasaron y devuelve un código de
salida distinto de cero si alguna falló. Se ejecutan en un subproceso para
aillar el estado global (configuración, auditoría y ventanas de Tk) entre
suites.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "tests" / "scripts"

CORE_SCRIPTS = [
    "kc_smoke.py",
    "kc_safety.py",
    "kc_package_b.py",
    "kc_package_c.py",
    "kc_package_d.py",
]

GUI_ENV_VAR = "KILLCLEANER_SKIP_GUI"


def _run(script, extra_env=None):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env.pop(GUI_ENV_VAR, None)
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        [sys.executable, str(SCRIPTS / script)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )


def _tk_available():
    """Comprueba si Tk puede crear una ventana (falla en sesiones sin escritorio)."""
    if sys.platform != "win32":
        return False
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import tkinter as tk; root = tk.Tk(); root.destroy()"],
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


GUI_AVAILABLE = _tk_available()
SKIP_GUI = {} if GUI_AVAILABLE else {GUI_ENV_VAR: "1"}


@pytest.mark.parametrize("script", CORE_SCRIPTS)
def test_regression_script(script):
    result = _run(script, SKIP_GUI)
    output = f"{result.stdout}\n{result.stderr}".strip()
    assert result.returncode == 0, f"{script} falló:\n{output}"
    assert "FALLO" not in result.stdout, f"{script} reportó fallos:\n{output}"


@pytest.mark.skipif(not GUI_AVAILABLE, reason="Tk no disponible en esta sesión")
def test_gui_smoke():
    result = _run("kc_gui.py")
    output = f"{result.stdout}\n{result.stderr}".strip()
    assert result.returncode == 0, f"kc_gui.py falló:\n{output}"
    assert "GUI OK" in result.stdout, output
