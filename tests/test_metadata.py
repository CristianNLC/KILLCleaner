"""Consistencia de versión y portabilidad de los archivos del proyecto."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_version_es_semver():
    from core.version import APP_VERSION

    parts = APP_VERSION.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_version_coincide_con_pyproject():
    from core.version import APP_VERSION

    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == APP_VERSION


def test_version_coincide_con_instalador():
    from core.version import APP_VERSION

    installer = (ROOT / "installer.iss").read_text(encoding="utf-8")
    assert f"AppVersion={APP_VERSION}" in installer


def test_spec_genera_recurso_de_version():
    spec = (ROOT / "KILLCleaner.spec").read_text(encoding="utf-8")
    assert "from core.version import APP_VERSION" in spec
    assert "version=_version_file" in spec
    assert "FileVersion" in spec
    assert "ProductVersion" in spec


def test_pruebas_sin_rutas_absolutas():
    # Se construye el literal por partes para que la prueba no se detecte a sí misma.
    forbidden = "D:" + "\\Proyecto_Limpiador"
    offenders = []
    for path in (ROOT / "tests").rglob("*.py"):
        if forbidden in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
