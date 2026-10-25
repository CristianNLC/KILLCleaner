"""Generación de informes de mantenimiento en texto plano y HTML."""

import html
from datetime import datetime

from core.app_paths import system_drive
from core.version import APP_VERSION


def _format_bytes(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TB"


def _audit_rows(entries):
    if not entries:
        return '<tr><td colspan="6" class="empty">Sin registros de auditoría.</td></tr>'

    rows = []
    for item in entries:
        result = str(item.get("result", "ok"))
        css = "ok" if result == "ok" else "error"
        mode = "Simulación" if item.get("dry_run") else "Real"
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('ts', '')))}</td>"
            f"<td><span class='tag'>{html.escape(str(item.get('action', '')))}</span></td>"
            f"<td class='path'>{html.escape(str(item.get('target', '')))}</td>"
            f"<td class='num'>{html.escape(_format_bytes(item.get('bytes', 0)))}</td>"
            f"<td class='num'>{html.escape(str(item.get('files', 0)))}</td>"
            f"<td><span class='badge {css}'>{html.escape(result)}</span>"
            f" <span class='muted'>{mode}</span></td>"
            "</tr>"
        )
    return "".join(rows)


def export_maintenance_report(log_content, stats_dict, target_path):
    """Escribe un informe de auditoría con el estado del sistema y el registro.

    Args:
        log_content: Texto del registro técnico de la sesión.
        stats_dict: Diccionario con las claves smart, disk_free, ram_used, trash.
        target_path: Ruta del archivo .txt a crear.

    Returns:
        (ok: bool, mensaje: str)
    """
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        drive = system_drive()
        report_lines = [
            "============================================================",
            "                KILLCleaner Maintenance Report              ",
            "============================================================",
            f"Fecha de Generación: {now_str}",
            "Sistema Operativo: Windows",
            f"Versión de la aplicación: {APP_VERSION}",
            "------------------------------------------------------------",
            "RESUMEN DE ESTADO Y SALUD DEL SISTEMA:",
            f"  - Salud de Disco (SMART) : {stats_dict.get('smart', 'Desconocido')}",
            f"  - Espacio libre ({drive}) : {stats_dict.get('disk_free', 'Calculando...')}",
            f"  - Memoria RAM en Uso   : {stats_dict.get('ram_used', 'Calculando...')}",
            f"  - Residuos Estimados   : {stats_dict.get('trash', '-- MB')}",
            "------------------------------------------------------------",
            "REGISTRO DE OPERACIONES Y MANTENIMIENTOS REALIZADOS:",
            "",
        ]

        if log_content:
            report_lines.append(log_content)
        else:
            report_lines.append("No se registraron acciones en esta sesión.")

        report_lines.extend(
            [
                "",
                "============================================================",
                f"          Fin del Informe - KILLCleaner v{APP_VERSION}          ",
                "============================================================",
            ]
        )

        with open(target_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        return True, "Informe de mantenimiento exportado con éxito."
    except Exception as e:
        return False, f"Error al guardar el informe: {str(e)}"


_HTML_STYLE = """
:root {
  --bg: #0f1115; --card: #1a1c23; --border: #2a2f3a;
  --text: #e5e7eb; --muted: #9ca3af; --accent: #38bdf8;
  --ok: #22c55e; --error: #ef4444;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 32px; background: var(--bg); color: var(--text);
  font-family: "Segoe UI", system-ui, sans-serif; line-height: 1.5;
}
h1 { margin: 0 0 4px; font-size: 26px; color: var(--accent); }
h2 { margin: 28px 0 12px; font-size: 18px; }
.sub { color: var(--muted); margin-bottom: 24px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }
.card {
  background: var(--card); border: 1px solid var(--border); border-radius: 10px;
  padding: 14px 16px;
}
.card .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
.card .value { font-size: 18px; font-weight: 600; margin-top: 4px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 8px 10px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
td.num { white-space: nowrap; }
td.path { word-break: break-all; color: var(--muted); }
.empty { text-align: center; color: var(--muted); padding: 24px; }
.tag {
  background: #232838; border: 1px solid var(--border); border-radius: 6px;
  padding: 2px 7px; font-family: Consolas, monospace; font-size: 12px;
}
.badge { border-radius: 999px; padding: 2px 9px; font-size: 11px; font-weight: 600; }
.badge.ok { background: rgba(34, 197, 94, .15); color: var(--ok); }
.badge.error { background: rgba(239, 68, 68, .15); color: var(--error); }
.muted { color: var(--muted); font-size: 12px; }
pre {
  background: var(--card); border: 1px solid var(--border); border-radius: 10px;
  padding: 16px; overflow-x: auto; white-space: pre-wrap; word-break: break-word;
  font-family: Consolas, monospace; font-size: 12px;
}
footer { margin-top: 28px; color: var(--muted); font-size: 12px; }
"""


def export_html_report(log_content, stats_dict, target_path, audit_entries=None):
    """Escribe un informe HTML autocontenido (sin recursos externos).

    Args:
        log_content: Registro técnico de la sesión.
        stats_dict: Diccionario con smart, disk_free, ram_used y trash.
        target_path: Ruta del archivo .html a crear.
        audit_entries: Entradas de ``core.audit.read_entries()`` (opcional).

    Returns:
        (ok: bool, mensaje: str)
    """
    try:
        generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        drive = system_drive()
        entries = audit_entries or []
        total_bytes = 0
        total_files = 0
        for item in entries:
            try:
                total_bytes += int(item.get("bytes", 0) or 0)
                total_files += int(item.get("files", 0) or 0)
            except (TypeError, ValueError):
                continue

        def _card(label, value):
            return (
                "<div class='card'>"
                f"<div class='label'>{html.escape(label)}</div>"
                f"<div class='value'>{html.escape(str(value))}</div>"
                "</div>"
            )

        cards = "".join(
            [
                _card("Salud del disco (SMART)", stats_dict.get("smart", "Desconocido")),
                _card(f"Espacio libre ({drive})", stats_dict.get("disk_free", "Calculando...")),
                _card("Memoria RAM en uso", stats_dict.get("ram_used", "Calculando...")),
                _card("Residuos estimados", stats_dict.get("trash", "-- MB")),
                _card("Acciones auditadas", len(entries)),
                _card("Datos liberados (auditoría)", _format_bytes(total_bytes)),
                _card("Archivos procesados (auditoría)", total_files),
            ]
        )

        document = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KILLCleaner - Informe de mantenimiento</title>
<style>{_HTML_STYLE}</style>
</head>
<body>
<h1>KILLCleaner · Informe de mantenimiento</h1>
<div class="sub">Generado el {html.escape(generated)} · Versión {html.escape(APP_VERSION)}</div>
<h2>Estado del sistema</h2>
<div class="cards">{cards}</div>
<h2>Historial de auditoría</h2>
<table>
<thead><tr><th>Fecha</th><th>Acción</th><th>Objetivo</th><th>Tamaño</th><th>Archivos</th><th>Resultado</th></tr></thead>
<tbody>{_audit_rows(entries)}</tbody>
</table>
<h2>Registro de la sesión</h2>
<pre>{html.escape(log_content or "No se registraron acciones en esta sesión.")}</pre>
<footer>KILLCleaner · Informe generado automáticamente. Los datos provienen del equipo local.</footer>
</body>
</html>
"""
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(document)
        return True, "Informe HTML exportado con éxito."
    except Exception as e:
        return False, f"Error al guardar el informe HTML: {str(e)}"
