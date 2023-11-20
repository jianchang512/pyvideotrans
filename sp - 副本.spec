# -*- mode: python ; coding: utf-8 -*-
import shutil

a = Analysis(
    ['sp.py'],
    pathex=[],
    binaries=[],
    datas=[('./venv//Lib/site-packages/whisper', './whisper'), ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='sp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    icon="./icon.ico",
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='sp',
)

shutil.copy("./ffmpeg.exe","./dist/sp/ffmpeg.exe")
shutil.copy("./ffprobe.exe","./dist/sp/ffprobe.exe")
shutil.copy("./icon.ico","./dist/sp/icon.ico")
shutil.copytree("./models","./dist/sp/models")
