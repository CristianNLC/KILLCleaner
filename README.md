Set-Content -Path README.md -Value @"
# ⚡ KILLCleaner v1.0 — Windows Optimization & Maintenance Suite

**KILLCleaner** es una suite moderna, gratuita y de código abierto para la optimización, mantenimiento forense y limpieza profunda de sistemas operativos Windows, desarrollada con Python y CustomTkinter.

---

## 🚀 Capacidades Principales

- **Limpieza del Sistema:** Purgado seguro de \`%TEMP%\`, \`Prefetch\`, descargas residuales de Windows Update y vaciado nativo de la Papelera de Reciclaje.
- **Mantenimiento Profundo:** Cachés de navegadores (Chrome, Edge, Brave), reportes de errores y volcados de memoria (\`.dmp\`).
- **Reparación de Componentes:** Integración directa con SFC (\`sfc /scannow\`) y mantenimiento de la imagen de Windows (\`DISM\`).
- **Seguridad y Restauración:** Creación de Puntos de Restauración del Sistema antes de limpiezas críticas.
- **Optimización de Almacenamiento:** Ejecución de comandos TRIM para SSD y desfragmentación inteligente de HDD.
- **Cachés de Desarrollo:** Detección y purga de dependencias en \`pip\`, \`npm\`, \`yarn\`, Spotify, Discord y carpetas \`__pycache__\`.
- **Modo Rendimiento (Gaming):** Liberador de memoria RAM en segundo plano y purga del portapapeles.
- **Auditoría & Diagnóstico:** Consulta de salud SMART del disco principal y exportación de reportes de mantenimiento.

---

## 🛠️ Instalación y Uso

### Ejecutable Listo para Usar
Descarga el instalador oficial desde el apartado de **Releases** (\`KILLCleaner_Setup.exe\`) e instálalo con permisos de administrador.

### Ejecución desde Código Fuente
1. Clonar el repositorio:
   \`\`\`bash
   git clone https://github.com/CristianNLC/KILLCleaner.git
   cd KILLCleaner
   \`\`\`
2. Instalar dependencias:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`
3. Iniciar la aplicación:
   \`\`\`bash
   python app.pyw
   \`\`\`
"@