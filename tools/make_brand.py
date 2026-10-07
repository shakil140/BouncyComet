#!/usr/bin/env python3
"""Builds the studio logo mark and every site icon from the mascot illustration.

    python tools/make_brand.py

Reads   ArtDrop/incoming/mascot_hero.png   (the purple rock comet with its green-yellow trail, transparent)
Writes  assets/icons/logo-mark.png         44 x 44    header + footer logo, 1x
        assets/icons/logo-mark@2x.png      88 x 88    the same, 2x
        assets/icons/logo-mark@3x.png      132 x 132  the same, 3x
        assets/icons/favicon-32.png        32 x 32    on the night sky
        assets/icons/favicon.ico           16, 32, 48
        assets/icons/apple-touch-icon.png  180 x 180
        assets/icons/icon-192.png          192 x 192
        assets/icons/icon-512.png          512 x 512

The whole illustration is too busy at 44 px: the long trail of loose rocks turns into noise
and leaves the head small. So the mark is the rock head with the first rocks of its trail,
and the green-yellow trail fades out behind them.

Needs Python 3 and Pillow. Run it again whenever mascot_hero.png changes, then raise the
?v= number of the icon links (see README, "Cache stamps").
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "ArtDrop" / "incoming" / "mascot_hero.png"
ICONS = ROOT / "assets" / "icons"

DEEP, NIGHT, DUSK = (6, 12, 36), (10, 20, 54), (18, 26, 82)      # --deep, --night, page bottom
VIOLET = (140, 60, 250)                                          # --comet
HEAD_SHARE = 0.86                # how much of the picture, from its upper right corner, is the mark
FADE = (0.13, 0.3)                # where along the diagonal the trail starts and stops fading in


def premultiplied_resize(im, size):
    """Scale down without dark or light fringes round the see-through edge."""
    return im.convert("RGBa").resize((size, size), Image.LANCZOS).convert("RGBA")


def cut_mark():
    """The rock head with the start of its trail, on a transparent square.

    The comet flies to the upper right, so its head fills the upper right of the picture and the
    trail runs to the lower left. The mark is the upper right HEAD_SHARE of the picture; the
    trail fades out along the diagonal instead of being cut by the edge of the square."""
    im = Image.open(SOURCE).convert("RGBA")
    alpha = im.getchannel("A")
    left, top, right, bottom = alpha.point(lambda v: 255 if v > 40 else 0).getbbox()
    side = round(max(right - left, bottom - top) * HEAD_SHARE)
    box = (right - side, top, right, top + side)
    mark = im.crop(box)
    # 0 in the lower left corner, 255 in the upper right one; the trail fades between the two stops.
    low, high = FADE
    steps = 256
    ramp = Image.new("L", (steps, steps))
    ramp.putdata([round(255 * min(1.0, max(0.0, ((x + steps - 1 - y) / (2 * steps - 2) - low) / (high - low))))
                  for y in range(steps) for x in range(steps)])
    fade = ramp.resize((side, side), Image.BICUBIC)
    mark.putalpha(ImageChops.multiply(mark.getchannel("A"), fade))
    # Tight crop, then back on a square with a little air so no glow is clipped.
    mark = mark.crop(mark.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox())
    size = round(max(mark.size) * 1.04)
    square = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    square.alpha_composite(mark, ((size - mark.width) // 2, (size - mark.height) // 2))
    return square


def small(mark, size):
    out = premultiplied_resize(mark, size)
    if size <= 128:                                             # keep the facets crisp when tiny
        rgb = out.convert("RGB").filter(ImageFilter.UnsharpMask(radius=0.6, percent=70, threshold=1))
        out = Image.merge("RGBA", (*rgb.split(), out.getchannel("A")))
    return out


def night_tile(size):
    """The site's night sky: deep to night to dusk, with the violet glow of its top right corner."""
    tile = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(tile)
    for y in range(size):
        t = y / max(1, size - 1)
        a, b, u = (DEEP, NIGHT, t / 0.38) if t < 0.38 else (NIGHT, DUSK, (t - 0.38) / 0.62)
        draw.line((0, y, size, y), fill=tuple(round(a[i] + (b[i] - a[i]) * u) for i in range(3)))
    glow = Image.new("L", (size, size), 0)
    ImageDraw.Draw(glow).ellipse((size * 0.18, size * 0.12, size * 0.92, size * 0.86), fill=120)
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.16))
    tile.paste(Image.new("RGB", (size, size), VIOLET), (0, 0), glow)
    return tile


def icon(mark, size, share=0.8):
    tile = night_tile(size).convert("RGBA")
    inner = small(mark, round(size * share))
    offset = (size - inner.width) // 2
    tile.alpha_composite(inner, (offset, offset))
    return tile.convert("RGB")


def main():
    if not SOURCE.exists():
        raise SystemExit("Missing %s" % SOURCE)
    mark = cut_mark()
    ICONS.mkdir(parents=True, exist_ok=True)
    for name, size in (("logo-mark.png", 44), ("logo-mark@2x.png", 88), ("logo-mark@3x.png", 132)):
        small(mark, size).save(ICONS / name, optimize=True)
    icon(mark, 32, 0.94).save(ICONS / "favicon-32.png", optimize=True)
    icon(mark, 180).save(ICONS / "apple-touch-icon.png", optimize=True)
    icon(mark, 192).save(ICONS / "icon-192.png", optimize=True)
    icon(mark, 512).save(ICONS / "icon-512.png", optimize=True)
    frames = [icon(mark, size, 0.94) for size in (16, 32, 48)]
    frames[-1].save(ICONS / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)],
                    append_images=frames[:-1])
    for path in sorted(ICONS.iterdir()):
        print("  %-24s %6d bytes" % (path.name, path.stat().st_size))


if __name__ == "__main__":
    main()
