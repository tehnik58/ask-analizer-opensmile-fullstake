# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Translation Confidence Analyzer (Windows, onedir)."""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

BLOCK_CIPHER = None

DESKTOP = Path(SPECPATH)
PROJECT_ROOT = DESKTOP.parent
BACKEND = PROJECT_ROOT / "backend"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

# --- Data files ---
datas = []

# Frontend dist → web/
if FRONTEND_DIST.is_dir():
    for f in FRONTEND_DIST.rglob("*"):
        if f.is_file():
            rel = f.relative_to(FRONTEND_DIST)
            datas.append((str(f), str(Path("web") / rel.parent)))

# opensmile config files
datas += collect_data_files("opensmile")

# imageio_ffmpeg binaries (ffmpeg exe)
datas += collect_data_files("imageio_ffmpeg")

# audresample/audinterface may have data
datas += collect_data_files("audinterface", include_py_files=False)
datas += collect_data_files("audresample", include_py_files=False)

# --- Hidden imports ---
hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "opensmile",
    "audinterface",
    "audobject",
    "audformat",
    "audiofile",
    "audresample",
    "audmath",
    "noisereduce",
    "imageio_ffmpeg",
    "pywebview",
    "pywebview.platforms.edgechromium",
    "clr_loader",
    "pythonnet",
    "soundfile",
    "librosa",
    "scipy",
    "scipy.signal",
    "numpy",
    "pandas",
]

# --- Analysis ---
a = Analysis(
    [str(DESKTOP / "main.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "tkinter", "PyQt5", "PyQt6"],
    noarchive=False,
    cipher=BLOCK_CIPHER,
)

pyz = PYZ(a.pure, cipher=BLOCK_CIPHER)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TCA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="TCA",
)
