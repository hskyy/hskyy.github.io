from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()


@pytest.fixture
def sample_heic(tmp_path: Path) -> Path:
    """A real HEIC file encoded on the fly, so no binary fixture is committed."""
    path = tmp_path / "IMG_0001.HEIC"
    image = Image.new("RGB", (320, 240), (200, 80, 40))
    for x in range(0, 320, 40):
        for y in range(0, 240, 40):
            if (x // 40 + y // 40) % 2 == 0:
                image.paste((40, 120, 200), (x, y, x + 40, y + 40))
    image.save(path, format="HEIF", quality=80)
    return path
