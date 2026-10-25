"""Pruebas del registro rotativo y de los ganchos de excepción."""

import logging
import os

import core.logging_setup as logging_setup


def _reset_logger():
    logger = logging.getLogger("killcleaner")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    if hasattr(logger, "_killcleaner_configured"):
        del logger._killcleaner_configured


def _patch_paths(monkeypatch, folder):
    monkeypatch.setattr(logging_setup, "logs_dir", lambda: str(folder))
    monkeypatch.setattr(
        logging_setup,
        "ensure_dir",
        lambda path: (os.makedirs(path, exist_ok=True) or path),
    )


def test_escribe_en_archivo(tmp_path, monkeypatch):
    _reset_logger()
    _patch_paths(monkeypatch, tmp_path)

    logger = logging_setup.setup_logging()
    logging_setup.get_logger("prueba").info("mensaje de prueba")
    for handler in logger.handlers:
        handler.flush()

    log_file = tmp_path / "killcleaner.log"
    assert log_file.exists()
    assert "mensaje de prueba" in log_file.read_text(encoding="utf-8")
    _reset_logger()


def test_configuracion_idempotente(tmp_path, monkeypatch):
    _reset_logger()
    _patch_paths(monkeypatch, tmp_path)

    logging_setup.setup_logging()
    logging_setup.setup_logging()

    assert len(logging.getLogger("killcleaner").handlers) == 1
    _reset_logger()


def test_sin_permisos_usa_manejador_nulo(tmp_path, monkeypatch):
    _reset_logger()
    monkeypatch.setattr(logging_setup, "logs_dir", lambda: str(tmp_path))

    def _fail(_path):
        raise OSError("sin permisos")

    monkeypatch.setattr(logging_setup, "ensure_dir", _fail)

    logger = logging_setup.setup_logging()
    assert any(isinstance(handler, logging.NullHandler) for handler in logger.handlers)
    _reset_logger()


def test_rotacion_configurada(tmp_path, monkeypatch):
    _reset_logger()
    _patch_paths(monkeypatch, tmp_path)

    logger = logging_setup.setup_logging()
    handler = logger.handlers[0]
    assert handler.maxBytes == logging_setup.MAX_BYTES
    assert handler.backupCount == logging_setup.BACKUP_COUNT
    _reset_logger()


def test_ganchos_de_excepcion(monkeypatch):
    import sys
    import threading

    original_excepthook = sys.excepthook
    original_thread_hook = threading.excepthook
    try:
        logging_setup.install_exception_hooks()
        assert sys.excepthook is not original_excepthook
        assert threading.excepthook is not original_thread_hook
    finally:
        sys.excepthook = original_excepthook
        threading.excepthook = original_thread_hook
