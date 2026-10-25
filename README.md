# ⚡ KILLCleaner v1.0

Suite de escritorio para Windows que reúne limpieza de residuos, mantenimiento
del sistema y utilidades de diagnóstico en una sola interfaz. Hecha en Python
con CustomTkinter; funciona 100 % en local y sin telemetría.

---

## 🚀 Capacidades

- **Limpieza del sistema:** `%TEMP%`, `Temp` de Windows, `Prefetch` y papelera
  de reciclaje (API nativa `SHEmptyRecycleBin`).
- **Mantenimiento profundo:** cachés de Chrome/Edge/Brave, descargas de Windows
  Update, volcados de memoria (`.dmp`) y caché de miniaturas.
- **Reparación de componentes:** `sfc /scannow` y DISM (`AnalyzeComponentStore`,
  `StartComponentCleanup`, `RestoreHealth`).
- **Seguridad y restauración:** creación de puntos de restauración del sistema.
- **Almacenamiento:** TRIM para SSD y optimización de HDD (`defrag /L /O`).
- **Cachés de desarrollo:** `pip`, `npm`, `yarn`, Discord, Spotify y
  `__pycache__` recursivo.
- **Modo Gaming:** cierre *selectivo* de aplicaciones y purga del portapapeles.
- **Auditoría:** estado SMART del disco y exportación de informes `.txt`.

---

## 🛡️ Seguridad por diseño

Estas son las garantías que ofrece la aplicación antes de borrar algo:

1. **Modo simulación (dry-run).** La casilla `🧪 Modo simulación` del Resumen
   calcula qué se borraría y cuánto se liberaría **sin eliminar nada**.
2. **Rutas protegidas.** `clean_directory()` rechaza raíces de unidad, `Windows`,
   `Users`, `Program Files` y el perfil del usuario, aunque se le pasen por error.
3. **Confirmación explícita** antes de cada operación destructiva (papelera,
   SFC, TRIM, servicios, tareas programadas).
4. **Cierre amable de procesos.** El Modo Gaming envía `WM_CLOSE` (como pulsar
   la X) para que las apps guarden su sesión. Solo mata el proceso si el usuario
   marca «Forzar cierre» de forma consciente.
5. **Nunca se cierra el navegador a la fuerza** durante la limpieza profunda: si
   está bloqueando la caché, esa caché se omite.
6. **Instancia única.** Un mutex de Windows impide que dos copias limpien a la vez.
7. **La limpieza automática no destruye datos.** `--silent-clean` solo purga
   temporales y Prefetch: no vacía la papelera ni cierra aplicaciones.

> Aun así, es una herramienta de mantenimiento: **haz una copia de seguridad de
> tus datos importantes** y usa el Modo Simulación la primera vez.

---

## 🔑 Credenciales (nunca versionadas)

El buzón de sugerencias (Web3Forms) y la cuenta de donaciones **no están en el
código**. Se resuelven, por orden, desde:

1. Variables de entorno: `KILLCLEANER_FEEDBACK_KEY` y `KILLCLEANER_DONATION_EMAIL`.
2. `data/secrets.json` (desde fuente) o `%LOCALAPPDATA%\KILLCleaner\secrets.json` (.exe).
3. Un `secrets.json` junto al `.exe`.

Plantilla lista para copiar en `data/secrets.example.json`:

```json
{
  "feedback_access_key": "tu-clave-de-web3forms",
  "donation_email": "tu-cuenta@ejemplo.com"
}
```

Sin clave, el formulario de contacto aparece desactivado y el bloque de Mercado
Pago se oculta; el resto de la aplicación funciona igual. `secrets.json` está en
`.gitignore`.

Para incluirlas en el `.exe`, deja `secrets.json` en la **raíz del proyecto** o en
`data/` antes de ejecutar PyInstaller: el `.spec` empaqueta el primero que exista.

> ℹ️ La *access key* de Web3Forms **no es un secreto**: identifica tu formulario y
> solo sirve para enviarte correos. Web3Forms la describe como «un alias de tu
> email». Aun así, cualquiera puede extraerla de un `.exe`, así que no la uses
> para nada más sensible y apóyate en el filtro antispam del servicio.

---

## 🛠️ Requisitos

- Windows 10 u 11.
- Python 3.10 o superior (probado con 3.14).
- Dependencias: `customtkinter`, `psutil`, `pillow`, `requests`.

---

## ▶️ Ejecución desde el código fuente

```powershell
git clone https://github.com/CristianNLC/KILLCleaner.git
cd KILLCleaner
pip install -r requirements.txt
python app.pyw
```

Muchas funciones (Prefetch, SFC, DISM, servicios de `HKLM`, `winsock reset`)
necesitan permisos de administrador. Si la app se abre sin ellos, muestra un
aviso en la parte superior con el botón **Reiniciar como admin**.

---

## ⏰ Limpieza automática (sin interfaz)

```powershell
python app.pyw --silent-clean
```

Purga únicamente `%TEMP%`, `Temp` de Windows y `Prefetch`, y escribe el
resultado en `logs/auto_clean_AAAA-MM-DD.log`. Pensado para el Programador de
Tareas de Windows, que la propia app configura desde
**Utilidades → Tareas Programadas**.

---

## 📦 Compilación

```powershell
pip install pyinstaller
pyinstaller KILLCleaner.spec
```

El `.spec` genera un único `dist\KILLCleaner.exe` sin consola y con manifiesto
`uac_admin` (pide elevación al abrirse).

Instalador (requiere [Inno Setup](https://jrsoftware.org/isinfo.php)):

```powershell
iscc installer.iss
```

Resultado: `dist_installer\KILLCleaner_Setup.exe`.

---

## 🗂️ Estructura

```
app.pyw                  Punto de entrada (GUI y --silent-clean)
core/
  app_paths.py           Rutas de config/logs (fuente vs .exe)
  privileges.py          Detección de admin y reapertura con UAC
  single_instance.py     Mutex de instancia única
  cleaner.py             Temporales, Prefetch y papelera
  system_cleaner.py      Navegadores, Windows Update, dumps, miniaturas
  dev_cleaner.py         Cachés de pip/npm/yarn/Discord/Spotify/__pycache__
  disk_analyzer.py       Tamaño real en disco (Win32 GetCompressedFileSize)
  duplicate_finder.py    Duplicados por SHA-256 en dos fases
  startup_manager.py     Entradas de inicio del registro (con respaldo)
  services_optimizer.py  Servicios de Windows (DiagTrack, WerSvc, Spooler)
  dism_tool.py           DISM en streaming
  optimizer.py           SFC, TRIM, SMART, restauración, tareas
  reporter.py            Informes de mantenimiento
  secrets.py             Carga de credenciales locales (env o secrets.json)
ui/
  main_window.py         Ventana principal (3 pestañas + modales)
  theme.py               Paleta y tipografía
  *_view.py              Subventanas de cada utilidad
assets/icon.ico
data/                    config.json, secrets.example.json e informe de ejemplo
logs/                    Registros de limpiezas automáticas (no versionado)
secrets.json             Credenciales locales opcionales (no versionado)
```

**Ubicación de datos:** desde el código fuente todo queda dentro del proyecto
(`data/`, `logs/`). El `.exe` instalado usa `%LOCALAPPDATA%\KILLCleaner` para no
intentar escribir en `Program Files`.

---

## 📄 Licencia

Distribuido bajo licencia **MIT**. Consulta el archivo [LICENSE](LICENSE).

