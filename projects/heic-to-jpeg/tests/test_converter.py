from __future__ import annotations

from pathlib import Path

from PIL import Image

from heic_to_jpeg.converter import (
    collect_heic_files,
    convert_file,
    convert_many,
    destination_for,
    is_heic,
    unique_path,
)


def test_is_heic_case_insensitive():
    assert is_heic(Path("a.HEIC"))
    assert is_heic(Path("a.heif"))
    assert is_heic(Path("a.hif"))
    assert not is_heic(Path("a.jpg"))


def test_collect_from_files_and_folders(tmp_path: Path, sample_heic: Path):
    nested = tmp_path / "album" / "day1"
    nested.mkdir(parents=True)
    (nested / "second.heic").write_bytes(sample_heic.read_bytes())
    (tmp_path / "ignore.jpg").write_bytes(b"x")
    found = collect_heic_files([tmp_path, sample_heic])
    assert {p.name for p in found} == {"IMG_0001.HEIC", "second.heic"}
    assert found[0].name == "IMG_0001.HEIC"  # top-level folder sorts before album/day1
    assert collect_heic_files([tmp_path], recursive=False) == [sample_heic.resolve()]


def test_destination_next_to_source_or_in_folder(tmp_path: Path):
    src = tmp_path / "pics" / "IMG_1.HEIC"
    assert destination_for(src, None) == tmp_path / "pics" / "IMG_1.jpg"
    assert destination_for(src, tmp_path / "out") == tmp_path / "out" / "IMG_1.jpg"


def test_unique_path_appends_counter(tmp_path: Path):
    target = tmp_path / "IMG_1.jpg"
    assert unique_path(target) == target
    target.write_bytes(b"a")
    assert unique_path(target) == tmp_path / "IMG_1 (1).jpg"
    (tmp_path / "IMG_1 (1).jpg").write_bytes(b"b")
    assert unique_path(target) == tmp_path / "IMG_1 (2).jpg"


def test_convert_file_produces_valid_jpeg(tmp_path: Path, sample_heic: Path):
    dest = tmp_path / "out" / "IMG_0001.jpg"
    result = convert_file(sample_heic, dest, quality=90)
    assert result.status == "converted", result.error
    with Image.open(dest) as img:
        assert img.format == "JPEG"
        assert img.size == (320, 240)


def test_conflict_modes(tmp_path: Path, sample_heic: Path):
    dest = tmp_path / "IMG_0001.jpg"
    dest.write_bytes(b"existing")

    skipped = convert_file(sample_heic, dest, on_conflict="skip")
    assert skipped.status == "skipped"
    assert dest.read_bytes() == b"existing"

    renamed = convert_file(sample_heic, dest, on_conflict="rename")
    assert renamed.status == "converted"
    assert renamed.destination == tmp_path / "IMG_0001 (1).jpg"
    assert dest.read_bytes() == b"existing"

    replaced = convert_file(sample_heic, dest, on_conflict="overwrite")
    assert replaced.status == "converted"
    assert dest.stat().st_size > 100


def test_corrupt_file_fails_without_partial_output(tmp_path: Path):
    bad = tmp_path / "bad.heic"
    bad.write_bytes(b"definitely not a heic")
    dest = tmp_path / "bad.jpg"
    result = convert_file(bad, dest)
    assert result.status == "failed"
    assert result.error
    assert not dest.exists()


def test_convert_many_isolates_failures_and_reports_progress(tmp_path: Path, sample_heic: Path):
    bad = tmp_path / "bad.heic"
    bad.write_bytes(b"nope")
    out = tmp_path / "out"
    seen: list[tuple[int, int, str]] = []
    results = convert_many(
        [sample_heic, bad],
        output_dir=out,
        progress=lambda done, total, r: seen.append((done, total, r.status)),
    )
    assert [r.status for r in results] == ["converted", "failed"]
    assert seen == [(1, 2, "converted"), (2, 2, "failed")]
    assert (out / "IMG_0001.jpg").exists()
    assert not (out / "bad.jpg").exists()


def test_convert_many_stops_when_asked(tmp_path: Path, sample_heic: Path):
    second = tmp_path / "second.heic"
    second.write_bytes(sample_heic.read_bytes())
    calls = {"n": 0}

    def should_stop() -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    results = convert_many([sample_heic, second], output_dir=tmp_path / "out", should_stop=should_stop)
    assert len(results) == 1
