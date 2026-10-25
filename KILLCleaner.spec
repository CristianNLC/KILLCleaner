# -*- mode: python ; coding: utf-8 -*-
import os
import sys

from PyInstaller.utils.hooks import collect_all

sys.path.insert(0, SPECPATH)
from core.version import APP_VERSION  # noqa: E402

datas = [('core', 'core'), ('ui', 'ui'), ('assets', 'assets')]
binaries = []
hiddenimports = []
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Credenciales locales: se empaquetan SOLO si existen y nunca se versionan.
# Se acepta secrets.json en la raíz o en data/ (el primero que exista).
for _secrets in (
    os.path.join(SPECPATH, 'secrets.json'),
    os.path.join(SPECPATH, 'data', 'secrets.json'),
):
    if os.path.exists(_secrets):
        datas += [(_secrets, '.')]
        break

# Recurso de versión del .exe: se genera desde core/version.py para que las
# propiedades del archivo nunca se queden atrás respecto a la aplicación.
_ver_parts = [int(part) for part in APP_VERSION.split(".") if part.isdigit()]
while len(_ver_parts) < 4:
    _ver_parts.append(0)
_ver_tuple = tuple(_ver_parts[:4])
_ver_text = APP_VERSION

_version_file = os.path.join(SPECPATH, "build", "version_info.txt")
os.makedirs(os.path.dirname(_version_file), exist_ok=True)
with open(_version_file, "w", encoding="utf-8") as _handle:
    _handle.write(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={_ver_tuple},
    prodvers={_ver_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'CristianNLC'),
         StringStruct('FileDescription', 'KILLCleaner - Suite de mantenimiento para Windows'),
         StringStruct('FileVersion', '{_ver_text}'),
         StringStruct('InternalName', 'KILLCleaner'),
         StringStruct('LegalCopyright', 'Copyright (c) 2026 CristianNLC'),
         StringStruct('OriginalFilename', 'KILLCleaner.exe'),
         StringStruct('ProductName', 'KILLCleaner'),
         StringStruct('ProductVersion', '{_ver_text}')])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    )


a = Analysis(
    ['app.pyw'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='KILLCleaner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.ico'],
    version=_version_file,
    # La app necesita privilegios para Prefetch, SFC, DISM y servicios del sistema
    uac_admin=True,
)
