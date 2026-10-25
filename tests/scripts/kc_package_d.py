"""Pruebas del paquete D: archivos grandes, historial, actualizaciones, HTML y arranque."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import core.audit as audit
import core.boot_diagnostics as boot
import core.config as cfg
import core.updates as updates
from core.app_paths import system_drive
from core.large_files import find_large_files
from core.reporter import export_html_report, export_maintenance_report
from core.version import APP_VERSION

ok, fail = [], []


def check(name, cond, extra=""):
    (ok if cond else fail).append(f"{name} {extra}")


base = tempfile.mkdtemp(prefix="kc_d_")
cfg.config_path = lambda: os.path.join(base, "config.json")
audit.logs_dir = lambda: os.path.join(base, "logs")
audit.ensure_dir = lambda path: (os.makedirs(path, exist_ok=True) or path)

# --- 1. Versión y consistencia con el instalador ---
check("version con formato semver", APP_VERSION.count(".") == 2, f"({APP_VERSION})")
installer = open(ROOT / "installer.iss", encoding="utf-8").read()
check("instalador usa la misma versión", f"AppVersion={APP_VERSION}" in installer)

# --- 2. Lectura de auditoría ---
log_path = audit.audit_path()
os.makedirs(os.path.dirname(log_path), exist_ok=True)
with open(log_path, "w", encoding="utf-8") as f:
    f.write(json.dumps({"ts": "2026-01-01T10:00:00-03:00", "action": "clean_temp", "bytes": 100, "files": 1}) + "\n")
    f.write("esto no es json\n")
    f.write(json.dumps({"ts": "2026-01-02T10:00:00-03:00", "action": "recycle_duplicate", "bytes": 200, "files": 2, "result": "error"}) + "\n")

entries = audit.read_entries()
check("audit: ignora líneas dañadas", len(entries) == 2, f"({len(entries)})")
check("audit: ordena de reciente a antiguo", entries[0]["action"] == "recycle_duplicate", f"({entries[0]['action']})")
check("audit: limit funciona", len(audit.read_entries(limit=1)) == 1)

rotated = os.path.join(os.path.dirname(log_path), "audit-20251231-235959.jsonl")
with open(rotated, "w", encoding="utf-8") as f:
    f.write(json.dumps({"ts": "2025-12-31T23:59:59-03:00", "action": "old", "bytes": 50, "files": 1}) + "\n")
check("audit: incluye archivos rotados", len(audit.read_entries()) == 3)
check("audit: excluye rotados si se pide", len(audit.read_entries(include_rotated=False)) == 2)

totals = audit.summarize(audit.read_entries())
check("audit: suma bytes", totals["bytes"] == 350, f"({totals['bytes']})")
check("audit: suma archivos", totals["files"] == 4, f"({totals['files']})")
check("audit: cuenta por acción", totals["by_action"]["old"] == 1)

check("audit: escribe nuevas entradas", audit.log_action("test_action", target="x", bytes_freed=10, files=1))
check("audit: lee lo recién escrito", audit.read_entries(limit=1)[0]["action"] == "test_action")

# --- 3. Archivos grandes ---
tree = os.path.join(base, "large")
os.makedirs(os.path.join(tree, "sub"))
sizes = {
    os.path.join(tree, "grande.bin"): 10 * 1024 * 1024,
    os.path.join(tree, "sub", "mediano.bin"): 2 * 1024 * 1024,
    os.path.join(tree, "sub", "pequeno.bin"): 100 * 1024,
}
for path, size in sizes.items():
    with open(path, "wb") as f:
        f.seek(size - 1)
        f.write(b"\0")

found = find_large_files(tree, min_size_bytes=1024 * 1024)
check("grandes: encuentra 2", len(found) == 2, f"({len(found)})")
check("grandes: ordena por tamaño", [item["size"] for item in found] == sorted([item["size"] for item in found], reverse=True))
check("grandes: devuelve ruta y fecha", "path" in found[0] and "mtime" in found[0])
check("grandes: respeta límite", len(find_large_files(tree, min_size_bytes=1, limit=1)) == 1)
check("grandes: umbral alto no devuelve nada", find_large_files(tree, min_size_bytes=100 * 1024 * 1024) == [])
check("grandes: ruta inexistente", find_large_files(os.path.join(base, "nope")) == [])

ev = threading.Event()
ev.set()
check("grandes: cancelado devuelve vacío", find_large_files(tree, min_size_bytes=1, cancel_event=ev) == [])

# --- 4. Actualizaciones ---
check("version: parsea v1.2.3", updates.parse_version("v1.2.3") == (1, 2, 3))
check("version: parsea 1.0", updates.parse_version("1.0") == (1, 0, 0))
check("version: texto sin números", updates.parse_version("ultima") == ())
check("version: 1.1.1 > 1.1.0", updates.is_newer("v1.1.1", "1.1.0") is True)
check("version: igual no es nueva", updates.is_newer("1.1.0", "1.1.0") is False)
check("version: anterior no es nueva", updates.is_newer("1.0.9", "1.1.0") is False)


class FakeResponse:
    def __init__(self, status=200, payload=None, bad_json=False):
        self.status_code = status
        self._payload = payload
        self._bad_json = bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("json inválido")
        return self._payload


class FakeSession:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.calls = []

    def get(self, url, timeout=None, headers=None):
        self.calls.append((url, timeout, headers))
        if self.exc:
            raise self.exc
        return self.response


session = FakeSession(FakeResponse(payload={"tag_name": "v9.9.9", "html_url": "https://example.test/v999"}))
result = updates.check_for_update(session=session)
check("updates: detecta versión nueva", result["ok"] and result["newer"], f"({result})")
check("updates: conserva URL", result["url"] == "https://example.test/v999")
check("updates: envía User-Agent", "KILLCleaner/" in session.calls[0][2]["User-Agent"])

same = updates.check_for_update(session=FakeSession(FakeResponse(payload={"tag_name": f"v{APP_VERSION}"})))
check("updates: versión igual no es nueva", same["ok"] and not same["newer"])

limited = updates.check_for_update(session=FakeSession(FakeResponse(status=403)))
check("updates: maneja límite de GitHub", not limited["ok"] and "limit" in limited["error"].lower())

offline = updates.check_for_update(session=FakeSession(exc=OSError("sin red")))
check("updates: maneja falta de red", not offline["ok"] and "Sin conexión" in offline["error"])

broken = updates.check_for_update(session=FakeSession(FakeResponse(bad_json=True)))
check("updates: maneja JSON inválido", not broken["ok"])

# --- 5. Diagnóstico de arranque ---
check("boot: formato segundos", boot.format_duration(45000) == "45.0 s")
check("boot: formato minutos", boot.format_duration(181000) == "3 min 1 s")
check("boot: formato cero", boot.format_duration(0) == "0.0 s")
check("boot: formato inválido", boot.format_duration(None) == "—")

sample_events = [
    {"time": "2026-01-02T10:00:00", "boot_ms": 60000, "main_path_ms": 30000, "post_boot_ms": 30000},
    {"time": "2026-01-01T10:00:00", "boot_ms": 120000, "main_path_ms": 60000, "post_boot_ms": 60000},
]
summary = boot.summarize(sample_events)
check("boot: último arranque", summary["last"] == 60000)
check("boot: promedio", summary["average"] == 90000)
check("boot: mínimo y máximo", (summary["min"], summary["max"]) == (60000, 120000))
check("boot: sin datos", boot.summarize([]) == {})


class FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


original_run = boot.subprocess.run
try:
    payload = json.dumps(sample_events)
    boot.subprocess.run = lambda *args, **kwargs: FakeCompleted(stdout=payload)
    parsed = boot.get_boot_history(2)
    check("boot: parsea lista JSON", parsed["ok"] and len(parsed["events"]) == 2)
    check("boot: convierte boot_ms", parsed["events"][0]["boot_ms"] == 60000)

    boot.subprocess.run = lambda *args, **kwargs: FakeCompleted(stdout=json.dumps(sample_events[0]))
    check("boot: parsea objeto JSON único", len(boot.get_boot_history(1)["events"]) == 1)

    boot.subprocess.run = lambda *args, **kwargs: FakeCompleted(stdout="null")
    empty = boot.get_boot_history(1)
    check("boot: null se trata como vacío", empty["ok"] and empty["events"] == [])

    boot.subprocess.run = lambda *args, **kwargs: FakeCompleted(returncode=1, stderr="No events were found")
    missing = boot.get_boot_history(1)
    check("boot: sin eventos no es error", missing["ok"] and missing["events"] == [])

    boot.subprocess.run = lambda *args, **kwargs: FakeCompleted(returncode=1, stderr="Access is denied")
    denied = boot.get_boot_history(1)
    check("boot: acceso denegado se informa", not denied["ok"] and "Access" in denied["error"])

    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="powershell", timeout=1)

    boot.subprocess.run = _timeout
    timed = boot.get_boot_history(1)
    check("boot: timeout controlado", not timed["ok"])
finally:
    boot.subprocess.run = original_run

real = boot.get_boot_history(2)
check("boot: consulta real no rompe", isinstance(real, dict) and "ok" in real and "events" in real)

# --- 6. Informes ---
txt_path = os.path.join(base, "informe.txt")
good, msg = export_maintenance_report("registro de prueba", {"disk_free": "10 GB", "smart": "OK"}, txt_path)
check("informe txt: se crea", good, msg)
txt = open(txt_path, encoding="utf-8").read()
check("informe txt: incluye versión", APP_VERSION in txt)
check("informe txt: incluye unidad", f"({system_drive()})" in txt)

html_path = os.path.join(base, "informe.html")
html_entries = [
    {"ts": "2026-01-02T10:00:00", "action": "clean_temp", "target": "C:\\Temp", "bytes": 2048, "files": 2, "result": "ok"},
    {"ts": "2026-01-01T10:00:00", "action": "recycle_duplicate", "target": "<script>alert(1)</script>", "bytes": 0, "files": 1, "result": "error"},
]
good, msg = export_html_report(
    "<b>no interpretar</b>", {"disk_free": "10 GB", "smart": "OK"}, html_path, html_entries
)
check("informe html: se crea", good, msg)
html_text = open(html_path, encoding="utf-8").read()
check("informe html: doctype y charset", "<!DOCTYPE html>" in html_text and 'charset="utf-8"' in html_text)
check("informe html: incluye versión", APP_VERSION in html_text)
check("informe html: escapa el registro", "&lt;b&gt;no interpretar&lt;/b&gt;" in html_text)
check("informe html: escapa objetivos", "<script>alert(1)</script>" not in html_text and "&lt;script&gt;" in html_text)
check("informe html: muestra acciones", "clean_temp" in html_text and "recycle_duplicate" in html_text)
check("informe html: marca errores", "badge error" in html_text)

empty_html = os.path.join(base, "vacio.html")
good, msg = export_html_report("", {}, empty_html, [])
check("informe html: funciona sin datos", good, msg)
check("informe html: mensaje sin registros", "Sin registros de auditoría" in open(empty_html, encoding="utf-8").read())

if os.environ.get("KILLCLEANER_SKIP_GUI") == "1":
    print("OK  :", len(ok))
    for item in fail:
        print("FALLO:", item)
    sys.exit(1 if fail else 0)

# --- 7. UI ---
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from unittest import mock  # noqa: E402

import ui.main_window as main_window_module  # noqa: E402
import ui.audit_view as audit_view_module  # noqa: E402
from ui.main_window import CleanerWindow  # noqa: E402
from ui.large_files_view import LargeFilesWindow  # noqa: E402
from ui.audit_view import AuditHistoryWindow  # noqa: E402
from ui.boot_view import BootDiagnosticsWindow  # noqa: E402

app = CleanerWindow()
app.update()
for method in ("open_large_files", "open_audit_history", "open_boot_diagnostics", "check_updates_action"):
    check(f"ui: existe {method}", hasattr(app, method))

large = LargeFilesWindow(app)
large.update()
large._items = [{"path": "C:\\x\\grande.bin", "size": 2048, "mtime": 0}]
large._refresh_summary()
check("ui grandes: resumen", "2.00 KB" in large.lbl_summary.cget("text"), f"({large.lbl_summary.cget('text')})")
large.destroy()

history = AuditHistoryWindow(app)
history.update()
history._render([])
check("ui historial: resumen vacío", "0 acciones" in history.lbl_summary.cget("text"))
history.destroy()

boot_win = BootDiagnosticsWindow(app)
boot_win.update()
boot_win._render({"ok": True, "events": sample_events, "error": ""})
check("ui arranque: último", boot_win.cards["last"].cget("text") == "1 min 0 s", f"({boot_win.cards['last'].cget('text')})")
boot_win._render({"ok": False, "events": [], "error": "denegado"})
check("ui arranque: muestra error", "denegado" in boot_win.lbl_status.cget("text"))
boot_win.destroy()

# --- 8. Exportación CSV del historial ---
csv_path = os.path.join(base, "historial.csv")
csv_window = AuditHistoryWindow(app)
csv_window.update()
csv_window._entries = list(html_entries)
csv_window._filtered = list(html_entries)
with mock.patch.object(
    audit_view_module.filedialog, "asksaveasfilename", return_value=csv_path
), mock.patch.object(audit_view_module.messagebox, "showinfo") as csv_info:
    csv_window._export_csv()

check("ui historial: crea el CSV", os.path.exists(csv_path))
if os.path.exists(csv_path):
    raw_csv = open(csv_path, encoding="utf-8-sig").read()
    lines = [line for line in raw_csv.splitlines() if line.strip()]
    check("ui historial: CSV con encabezado", raw_csv.startswith("Fecha;Acción;Objetivo"))
    check("ui historial: CSV con una fila por entrada", len(lines) == 3, f"({len(lines)})")
    check("ui historial: CSV incluye acciones", "clean_temp" in raw_csv and "recycle_duplicate" in raw_csv)
    check("ui historial: CSV marca simulación", ";No;" in raw_csv)
check("ui historial: avisa al exportar", csv_info.called)
csv_window.destroy()

no_data_window = AuditHistoryWindow(app)
no_data_window.update()
no_data_window._filtered = []
with mock.patch.object(audit_view_module.messagebox, "showinfo") as no_data_info:
    no_data_window._export_csv()
check("ui historial: sin datos no exporta", no_data_info.called)
no_data_window.destroy()

# --- 9. Exportación desde la ventana principal ---
html_out = os.path.join(base, "app_reporte.html")
with mock.patch.object(
    main_window_module.filedialog, "asksaveasfilename", return_value=html_out
), mock.patch.object(app, "_show_modal_alert") as html_alert:
    app.export_report_action()

check("ui app: exporta HTML", os.path.exists(html_out))
if os.path.exists(html_out):
    app_html = open(html_out, encoding="utf-8").read()
    check("ui app: HTML autocontenido", "<!DOCTYPE html>" in app_html and APP_VERSION in app_html)
    check("ui app: HTML con auditoría", "clean_temp" in app_html)
check("ui app: confirma la exportación", html_alert.called)

txt_out = os.path.join(base, "app_reporte.txt")
with mock.patch.object(
    main_window_module.filedialog, "asksaveasfilename", return_value=txt_out
), mock.patch.object(app, "_show_modal_alert"):
    app.export_report_action()
check("ui app: exporta TXT", os.path.exists(txt_out))

with mock.patch.object(
    main_window_module.filedialog, "asksaveasfilename", return_value=""
):
    app.export_report_action()
check("ui app: cancelar no rompe", True)


def _pump(seconds=1.5):
    """Deja correr el bucle de Tk para que el hilo de trabajo entregue su resultado."""
    app.after(int(seconds * 1000), app.quit)
    app.mainloop()


# --- 10. Comprobación de actualizaciones desde la UI ---
with mock.patch.object(
    main_window_module.updates,
    "check_for_update",
    return_value={
        "ok": True,
        "latest": "v9.9.9",
        "url": "https://example.test/v999",
        "newer": True,
        "error": "",
    },
), mock.patch.object(
    main_window_module.messagebox, "askyesno", return_value=False
) as ask_mock:
    app.check_updates_action()
    _pump()

check("ui updates: avisa de versión nueva", ask_mock.called)
check(
    "ui updates: estado muestra la versión",
    "9.9.9" in app.lbl_status_text.cget("text"),
    f"({app.lbl_status_text.cget('text')})",
)

with mock.patch.object(
    main_window_module.updates,
    "check_for_update",
    return_value={"ok": True, "latest": f"v{APP_VERSION}", "url": "", "newer": False, "error": ""},
), mock.patch.object(app, "_show_modal_alert") as uptodate_alert:
    app.check_updates_action()
    _pump()

check("ui updates: al día informa", uptodate_alert.called)
check(
    "ui updates: estado al día",
    "al día" in app.lbl_status_text.cget("text"),
    f"({app.lbl_status_text.cget('text')})",
)

with mock.patch.object(
    main_window_module.updates,
    "check_for_update",
    return_value={"ok": False, "latest": "", "url": "", "newer": False, "error": "sin red"},
), mock.patch.object(app, "_show_modal_alert") as offline_alert:
    app.check_updates_action()
    _pump()

check("ui updates: error informa", offline_alert.called)

app._on_close()
shutil.rmtree(base, ignore_errors=True)

print("OK  :", len(ok))
for item in fail:
    print("FALLO:", item)
sys.exit(1 if fail else 0)
