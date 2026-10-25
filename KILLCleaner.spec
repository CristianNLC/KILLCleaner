# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_all

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
    # La app necesita privilegios para Prefetch, SFC, DISM y servicios del sistema
    uac_admin=True,
)
