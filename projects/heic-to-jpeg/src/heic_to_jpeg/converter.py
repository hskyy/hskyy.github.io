from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Literal

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

HEIC_SUFFIXES = {".heic", ".heif", ".hif"}

Status = Literal["converted", "skipped", "failed"]


@dataclass(frozen=True)
class ConvertResult:
    source: Path
    destination: Path
    status: Status
    error: str | None = None


def is_heic(path: Path) -> bool:
    return path.suffix.lower() in HEIC_SUFFIXES


def collect_heic_files(paths: Iterable[Path], *, recursive: bool = True) -> list[Path]:
    """Expand files and folders into a sorted, de-duplicated list of HEIC files."""
    found: set[Path] = set()
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            if is_heic(path):
                found.add(path.resolve())
        elif path.is_dir():
            walker = path.rglob("*") if recursive else path.iterdir()
            for child in walker:
                if child.is_file() and is_heic(child):
                    found.add(child.resolve())
    return sorted(found, key=lambda p: (str(p.parent).lower(), p.name.lower()))


def destination_for(source: Path, output_dir: Path | None) -> Path:
    """JPEG path for a source. Same folder as the source when output_dir is None."""
    name = source.with_suffix(".jpg").name
    return (output_dir / name) if output_dir else source.with_name(name)


def unique_path(path: Path) -> Path:
    """Return path, or path with ' (n)' appended if it already exists."""
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for index in range(1, 10_000):
        candidate = path.with_name(f"{stem} ({index}){suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Could not find a free name for {path}")


def convert_file(
    source: Path,
    destination: Path,
    *,
    quality: int = 92,
    on_conflict: Literal["skip", "overwrite", "rename"] = "rename",
    keep_timestamps: bool = True,
) -> ConvertResult:
    """Convert one HEIC file to JPEG. Failures are returned, never raised."""
    if destination.exists():
        if on_conflict == "skip":
            return ConvertResult(source, destination, "skipped")
        if on_conflict == "rename":
            destination = unique_path(destination)

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image)
            exif = image.info.get("exif")
            rgb = image.convert("RGB")
            save_kwargs = {"quality": quality, "optimize": True}
            if exif:
                save_kwargs["exif"] = exif
            rgb.save(destination, "JPEG", **save_kwargs)
        if keep_timestamps:
            stat = source.stat()
            os.utime(destination, (stat.st_atime, stat.st_mtime))
        return ConvertResult(source, destination, "converted")
    except Exception as exc:  # noqa: BLE001 - one bad photo must not stop the batch
        if destination.exists():
            try:
                destination.unlink()
            except OSError:
                pass
        return ConvertResult(source, destination, "failed", error=f"{type(exc).__name__}: {exc}")


def convert_many(
    sources: Iterable[Path],
    *,
    output_dir: Path | None,
    quality: int = 92,
    on_conflict: Literal["skip", "overwrite", "rename"] = "rename",
    progress: Callable[[int, int, ConvertResult], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[ConvertResult]:
    """Convert files one at a time (HEIC decoding is memory heavy) with progress callbacks."""
    items = list(sources)
    results: list[ConvertResult] = []
    for index, source in enumerate(items, start=1):
        if should_stop and should_stop():
            break
        result = convert_file(
            source,
            destination_for(source, output_dir),
            quality=quality,
            on_conflict=on_conflict,
        )
        results.append(result)
        if progress:
            progress(index, len(items), result)
    return results
