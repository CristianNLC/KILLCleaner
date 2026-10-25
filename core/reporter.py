"""Generación de informes de mantenimiento en texto plano (UTF-8)."""

from datetime import datetime


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
        report_lines = [
            "============================================================",
            "                KILLCleaner Maintenance Report              ",
            "============================================================",
            f"Fecha de Generación: {now_str}",
            "Sistema Operativo: Windows",
            "------------------------------------------------------------",
            "RESUMEN DE ESTADO Y SALUD DEL SISTEMA:",
            f"  - Salud de Disco (SMART) : {stats_dict.get('smart', 'Desconocido')}",
            f"  - Espacio Libre en C:   : {stats_dict.get('disk_free', 'Calculando...')}",
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
                "            Fin del Informe - KILLCleaner v1.0              ",
                "============================================================",
            ]
        )

        with open(target_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        return True, "Informe de mantenimiento exportado con éxito."
    except Exception as e:
        return False, f"Error al guardar el informe: {str(e)}"
