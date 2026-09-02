# HEIC to JPEG

A small Windows desktop app that converts iPhone **HEIC/HEIF photos to JPEG in bulk**. Select as many photos (or whole folders) as you like, press **Convert to JPEG**, done. Everything runs on the PC — nothing is uploaded.

It ships as a normal Windows installer wizard (`HeicToJpeg-Setup-<version>.exe`) with every dependency bundled, so setup is Next → Next → Finish.

## For the person installing it

1. Download `HeicToJpeg-Setup-1.0.0.exe` from the latest release (or the `HeicToJpeg-windows` artifact on the Actions tab).
2. Double-click it. Windows SmartScreen may say the publisher is unknown because the installer is not code-signed — choose **More info → Run anyway**.
3. Click through the wizard. You can tick **Create a desktop icon** and **Add to the right-click Send to menu**.
4. Open **HEIC to JPEG** from the Start menu or desktop.

No Python, no codecs, no extra downloads are needed — the installer contains everything.

### Using the app

- **Add photos…** — pick one or many `.heic` files (Ctrl+A / Shift-click works in the picker).
- **Add folder…** — pull in every HEIC in a folder and its subfolders.
- Choose whether JPEGs are saved **next to the originals** or into **one folder** you pick.
- Optional: adjust **JPEG quality** (default 92) and what to do **if a JPEG already exists** (keep both / skip / replace).
- Press **Convert to JPEG**. The Status column shows each photo as it finishes; a bad photo is marked *Failed* and the rest keep going.
- **Open output folder** jumps to the results.

Originals are never modified or deleted. Orientation is corrected and EXIF data is carried over when available.

## For whoever builds it

The app is Python (Tkinter UI, Pillow + `pillow-heif` for decoding) packaged with PyInstaller into a single `HeicToJpeg.exe`, then wrapped in an Inno Setup wizard.

### Automatic builds (recommended)

GitHub Actions builds on a Windows runner for every push to this folder — see `.github/workflows/heic-to-jpeg-windows.yml`.

- Every run uploads an artifact named **HeicToJpeg-windows** containing `HeicToJpeg.exe` and `HeicToJpeg-Setup-<version>.exe`.
- Pushing a tag like `heic-to-jpeg-v1.0.0` also publishes a GitHub Release with both files attached.

### Building on a Windows PC

Requirements: Python 3.11+ and [Inno Setup 6](https://jrsoftware.org/isdl.php).

```powershell
cd projects\heic-to-jpeg
.\packaging\build_windows.ps1
```

Outputs land in `dist\`:

- `HeicToJpeg.exe` — portable, runs with no install
- `HeicToJpeg-Setup-<version>.exe` — the installer wizard

### Running from source / tests

```powershell
python -m pip install -r requirements-build.txt
python -m pytest -q
python -m heic_to_jpeg          # launches the app (PYTHONPATH=src on Linux/macOS)
```

## Layout

```
src/heic_to_jpeg/
  converter.py      HEIC discovery + conversion core (no UI)
  app.py            Tkinter desktop UI, background worker, progress
packaging/
  HeicToJpeg.spec   PyInstaller one-file build
  HeicToJpeg.iss    Inno Setup installer wizard
  build_windows.ps1 One-shot build script
  make_icon.py      Generates icon.ico at build time
tests/              pytest suite (core + headless GUI)
```
