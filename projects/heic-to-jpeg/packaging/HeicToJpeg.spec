# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec. Run from the project root:
#   pyinstaller packaging/HeicToJpeg.spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

project = Path(SPECPATH).parent
src = project / "src"
icon = project / "packaging" / "icon.ico"

binaries = collect_dynamic_libs("pillow_heif")
hiddenimports = collect_submodules("pillow_heif") + ["PIL._tkinter_finder"]

datas = []
if icon.exists():
    datas.append((str(icon), "."))

a = Analysis(
    [str(src / "heic_to_jpeg" / "__main__.py")],
    pathex=[str(src)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["numpy", "scipy", "matplotlib", "pandas"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="HeicToJpeg",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(icon) if icon.exists() else None,
)
