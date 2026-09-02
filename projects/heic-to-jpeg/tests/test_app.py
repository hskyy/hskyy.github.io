"""GUI tests. Skipped automatically when no display (or tkinter) is available."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

tk = pytest.importorskip("tkinter")


@pytest.fixture
def app():
    from heic_to_jpeg.app import HeicToJpegApp

    try:
        window = HeicToJpegApp()
    except tk.TclError as exc:  # no display
        pytest.skip(f"no display available: {exc}")
    window.withdraw()
    yield window
    window.destroy()


def pump(app, seconds: float = 0.1) -> None:
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.01)


def test_add_paths_lists_heic_only(app, tmp_path: Path, sample_heic: Path):
    (tmp_path / "skip.png").write_bytes(b"x")
    app._add_paths([tmp_path])
    assert app.files == [sample_heic.resolve()]
    assert app.tree.set(str(sample_heic.resolve()), "status") == "Ready"
    assert str(app.convert_button["state"]) == "normal"


def test_start_converts_in_background_and_updates_rows(app, tmp_path: Path, sample_heic: Path, monkeypatch):
    bad = tmp_path / "bad.heic"
    bad.write_bytes(b"nope")
    warnings: list[str] = []
    monkeypatch.setattr("heic_to_jpeg.app.messagebox.showwarning", lambda *a, **k: warnings.append(a[1]))

    app._add_paths([sample_heic, bad])
    app.output_dir = tmp_path / "out"
    app.output_mode.set("folder")
    app.start()

    deadline = time.time() + 20
    while app._running() or not app.status_text.get().endswith("."):
        pump(app)
        if time.time() > deadline:
            pytest.fail("conversion did not finish")
    pump(app, 0.2)

    assert (tmp_path / "out" / "IMG_0001.jpg").exists()
    assert app.tree.set(str(sample_heic.resolve()), "status").startswith("Saved")
    assert app.tree.set(str(bad.resolve()), "status").startswith("Failed")
    assert app.status_text.get() == "1 converted, 0 skipped, 1 failed."
    assert warnings and "could not be converted" in warnings[0]


def test_remove_and_clear(app, sample_heic: Path):
    app._add_paths([sample_heic])
    app.tree.selection_set(str(sample_heic.resolve()))
    app.remove_selected()
    assert app.files == []
    assert str(app.convert_button["state"]) == "disabled"
