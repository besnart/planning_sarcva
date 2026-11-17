# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller : construit l'executable autonome planning-sarcva (onefile)."""

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

d_django, b_django, h_django = collect_all("django")
d_tzdata = collect_data_files("tzdata")
d_planning = collect_data_files(
    "planning",
    includes=["templates/**/*", "static/**/*", "migrations/**/*"],
)
hiddenimports = h_django + collect_submodules("planning") + collect_submodules("config")

a = Analysis(
    ["run_app.py"],
    pathex=[],
    binaries=b_django,
    datas=d_django + d_tzdata + d_planning,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="planning-sarcva",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
