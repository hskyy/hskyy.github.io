"""Generate packaging/icon.ico at build time so no binary is committed."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).with_name("icon.ico")


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = size // 10
    d.rounded_rectangle((pad, pad, size - pad, size - pad), radius=size // 5, fill=(28, 110, 43, 255))
    # Photo "frame" with a mountain + sun motif.
    inner = size // 4
    d.rectangle((inner, inner, size - inner, size - inner), fill=(244, 240, 228, 255))
    sun_r = max(2, size // 14)
    d.ellipse(
        (size - inner - sun_r * 3, inner + sun_r, size - inner - sun_r, inner + sun_r * 3),
        fill=(226, 177, 90, 255),
    )
    base = size - inner
    d.polygon(
        [(inner, base), (size // 2, inner + size // 6), (base, base)],
        fill=(28, 110, 43, 255),
    )
    return img


def main() -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [draw(s) for s in sizes]
    frames[-1].save(OUT, format="ICO", sizes=[(s, s) for s in sizes], append_images=frames[:-1])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
