#!/usr/bin/env python3
"""Turn the artwork in ArtDrop/ into the web-ready files the site uses.

    python tools/import_art.py           import what has arrived, placeholder the rest
                                         (exit 1 when a file was REJECTED)
    python tools/import_art.py --check   change nothing; exit 1 unless every picture in
                                         assets/ is real art and is byte for byte what
                                         the last complete run wrote

Reads   ArtDrop/incoming/*.png          the 17 illustrations named in ArtDrop/GPT_PROMPT.md
        ArtDrop/reference/game/*.png    the 11 in-game screenshots (game_01_home.png ...)
        ArtDrop/reference/brand/*.png   the Dice Duo logo and the five game icons
Writes  assets/art/*  assets/shots/*
        assets/img/og-image.jpg         (only once hero_desktop.png is real)
        tools/art-manifest.json         status + checksum of every file written (no notes)
        ArtDrop/import-log.json         the notes of the last run (git-ignored, never published)
        ArtDrop/preview/cut_<sheet>.png numbered, named picture of how each sheet was cut

Needs Python 3.8+ and Pillow. Nothing else. Safe to run again and again: real art
simply replaces the placeholder that stood in for it.
"""
from __future__ import annotations

import argparse
import colorsys
import difflib
import hashlib
import json
import math
import os
import random
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageMath
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required:  python -m pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent
INCOMING = ROOT / "ArtDrop" / "incoming"
GAME = ROOT / "ArtDrop" / "reference" / "game"
BRAND = ROOT / "ArtDrop" / "reference" / "brand"
ART = ROOT / "assets" / "art"
SHOTS = ROOT / "assets" / "shots"
FONTS = ROOT / "assets" / "fonts"
OG_IMAGE = ROOT / "assets" / "img" / "og-image.jpg"
MANIFEST = ROOT / "tools" / "art-manifest.json"          # committed: status and checksums, no notes
LOG = ROOT / "ArtDrop" / "import-log.json"               # git-ignored: the notes of the last run
PREVIEW = ROOT / "ArtDrop" / "preview"                   # git-ignored: pictures for the owner to look at
OLD_MANIFEST = ART / "manifest.json"                     # the log used to be written here, inside the published site

LANCZOS = Image.Resampling.LANCZOS
BICUBIC = Image.Resampling.BICUBIC
Image.MAX_IMAGE_PIXELS = 80_000_000

# Site palette (the same values as the art brief and css/style.css).
NIGHT, DEEP, INDIGO, VIOLET = (10, 20, 54), (6, 12, 36), (27, 42, 107), (75, 42, 143)
TRAY, SKY, RED, YELLOW = (30, 91, 216), (46, 155, 240), (229, 57, 47), (255, 198, 26)
GOLD, GREEN, CREAM, PINK = (255, 184, 26), (61, 190, 61), (241, 232, 207), (255, 211, 216)
MINT, WHITE, ORANGE = (143, 227, 192), (255, 255, 255), (255, 122, 46)


# ==========================================================================
# What we expect, and what each file becomes
# ==========================================================================
#
# kind "cutout"  transparent subject. Trimmed, centred on a fixed canvas.
#                outs -> NAME.webp, NAME@2x.webp, NAME.png       (png = 1x fallback)
#                wide -> NAME-WIDTH.webp for each width, NAME.png: for a picture whose slot
#                        is very different on a phone and on a desktop (srcset + sizes)
# kind "scene"   opaque picture, cropped to its shape, several widths.
#                -> NAME-WIDTH.webp, NAME-WIDTH.jpg
# kind "tile"    opaque picture at one display size.
#                -> NAME.webp, NAME@2x.webp, NAME.jpg            (jpg = 1x fallback)
# kind "sheet"   transparent sprite sheet, cut into its items; each item is a cutout.

GAMES = ["grid-war", "diceback", "roll-race", "six-spots", "scoop-stack"]
GAME_GLOW = {"grid-war": SKY, "diceback": ORANGE, "roll-race": GREEN,
             "six-spots": YELLOW, "scoop-stack": (255, 120, 170)}


def _art_specs():
    specs = [
        # wide = (stem, shape, widths, width of the png fallback)
        dict(file="mascot_hero.png", size=(1536, 1536), kind="cutout",
             wide=[("mascot-hero", (1, 1), [200, 400, 800], 400)]),
        dict(file="mascot_wave.png", size=(1536, 1536), kind="cutout",
             wide=[("mascot-wave", (1, 1), [200, 400, 800], 400)], outs=[("mascot-wave-sm", 120, 120)]),
        dict(file="mascot_lost.png", size=(1536, 1536), kind="cutout",
             wide=[("mascot-lost", (1, 1), [200, 400, 800], 400)]),
        dict(file="hero_desktop.png", size=(2560, 1440), kind="scene", stem="hero-desktop", widths=[1280, 1920]),
        dict(file="hero_phone.png", size=(1440, 2160), kind="scene", stem="hero-phone", widths=[720, 1080]),
        dict(file="bg_night-sky.png", size=(2560, 1440), kind="scene", stem="bg-night-sky", widths=[1280, 1920]),
    ]
    for game in GAMES:
        specs.append(dict(file="game_%s.png" % game, size=(1536, 2048), kind="scene",
                          stem="game-" + game, widths=[300, 480, 768], game=game))
    specs += [
        # canvas = the largest slot the item is shown in, in CSS px (the @2x file is twice that).
        # hues   = the colour an item must mostly be, so that two swapped items are noticed.
        # extra  = more sizes of one item.
        dict(file="sheet_toys.png", size=(2560, 1280), kind="sheet", grid=(4, 2), canvas=160,
             items=["toy-die-five", "toy-die-two", "toy-token-red", "toy-token-yellow",
                    "toy-cone", "toy-x-yellow", "toy-line-red", "toy-star"],
             hues={"toy-die-five": "red", "toy-die-two": "red", "toy-token-red": "red",
                   "toy-token-yellow": "yellow", "toy-x-yellow": "yellow", "toy-line-red": "red",
                   "toy-star": "yellow"},
             extra={"toy-star": [("toy-star-sm", 40, 40)]}),          # the star beside "How you win"
        dict(file="sheet_modes.png", size=(1536, 1536), kind="sheet", grid=(2, 2), canvas=168,
             items=["mode-computer", "mode-same-phone", "mode-online", "mode-private-room"]),
        dict(file="sheet_features.png", size=(2400, 1600), kind="sheet", grid=(3, 2), canvas=96,
             items=["feature-skins", "feature-daily-reward", "feature-leaderboard",
                    "feature-fair-play", "feature-fast-matches", "feature-offline"]),
        dict(file="sheet_genres.png", size=(2400, 1600), kind="sheet", grid=(3, 2), canvas=96,
             items=["genre-puzzle", "genre-hypercasual", "genre-arcade",
                    "genre-hybrid-casual", "genre-multiplayer", "genre-kids-family"]),
        dict(file="studio_workshop.png", size=(2560, 1440), kind="scene", stem="studio-workshop",
             widths=[960, 1440, 1920]),
        dict(file="trail_divider.png", size=(2400, 800), kind="cutout", pad=0.0, solid=False, ring=0.5,
             wide=[("trail-divider", (3, 1), [600, 1200, 2400], 600)]),
    ]
    for spec in specs:
        spec.update(folder=INCOMING, out=ART, group="art")
        if spec["kind"] == "sheet":
            spec.setdefault("pad", 0.06)       # a little room for the glow around each item
    return specs


def _shot_specs():
    names = ["home", "grid-war", "diceback", "roll-race", "six-spots", "scoop-stack",
             "win", "store", "skins", "setup", "loading"]
    return [dict(file="game_%02d_%s.png" % (i + 1, name), size=(1080, 1920), kind="tile",
                 outs=[(name, 360, 640)], folder=GAME, out=SHOTS, group="shots")
            for i, name in enumerate(names)]


def _brand_specs():
    specs = [
        dict(file="dice-duo_logo.png", size=None, kind="cutout", pad=0.0, solid=False, ring=0.5,
             outs=[("dice-duo-logo", 600, 300)]),
    ]
    for game in GAMES:
        specs.append(dict(file="game-icon_%s.png" % game, size=None, kind="cutout", pad=0.02,
                          outs=[("icon-" + game, 128, 128)], game=game))
    for spec in specs:
        spec.update(folder=BRAND, out=ART, group="brand")
    return specs


ALL_SPECS = _art_specs() + _shot_specs() + _brand_specs()
REFERENCE_ONLY = {"bouncy-comet_logo-icon.png"}     # kept for the illustrator, not used by the site


class Problem(Exception):
    """The file is there but cannot be used as it is."""


# ==========================================================================
# Small image helpers
# ==========================================================================

def rel(path):
    return path.relative_to(ROOT).as_posix()


def sha1(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


def tidy(text):
    """A note never carries a folder of this computer, only file names."""
    text = str(text)
    for folder in (INCOMING, GAME, BRAND, ART, SHOTS, ROOT):
        for form in (str(folder), folder.as_posix()):
            text = text.replace(form + "\\", "").replace(form + "/", "").replace(form, folder.name)
    return re.sub(r"(?:[A-Za-z]:[\\/]+|(?<![\w.])/)(?:[^\\/:*?\"<>|\r\n']+[\\/]+)+", "", text)


def write_json(path, data):
    """Write through a temporary file: a reader sees the old file or the new one, never half of one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def open_image(path):
    """Open a picture as RGB or RGBA. A palette or grey PNG can carry transparency without
    an alpha band (TinyPNG and pngquant write those): it becomes RGBA here."""
    im = Image.open(path)
    im.load()
    if im.mode not in ("RGB", "RGBA") or "transparency" in im.info:
        transparent = "A" in im.getbands() or "transparency" in im.info
        im = im.convert("RGBA" if transparent else "RGB")
    return im


def ratio_text(size):
    w, h = size
    g = math.gcd(w, h)
    a, b = w // g, h // g
    return "%d:%d" % (a, b) if a <= 32 and b <= 32 else "%.2f:1" % (w / h)


FAST = False      # set while writing placeholders: they do not deserve the slowest encoder setting


def save_webp(im, path, quality):
    im.save(path, "WEBP", quality=quality, method=2 if FAST else 4)


def save_png(im, path):
    im.save(path, "PNG", optimize=not FAST)


def save_jpg(im, path, quality=82):
    im.convert("RGB").save(path, "JPEG", quality=quality, optimize=True, progressive=True)


def clear_share(alpha, below=250):
    """Share of the pixels that are at least partly transparent."""
    return sum(alpha.histogram()[:below]) / float(alpha.width * alpha.height)


def ring_clear(alpha):
    """Share of the outermost 2 px of the picture that is not solid. A faint glow may reach
    the border; a background that was never removed makes the whole border solid."""
    w, h = alpha.size
    ring = b"".join(alpha.crop(box).tobytes()
                    for box in ((0, 0, w, 2), (0, h - 2, w, h), (0, 2, 2, h - 2), (w - 2, 2, w, h - 2)))
    return sum(1 for value in ring if value < 200) / float(max(1, len(ring)))


def detail(im):
    """How much happens in a picture: the widest spread of any colour channel, on a small copy."""
    small = im.convert("RGB").resize((64, 64), Image.Resampling.BOX)
    return max(hi - lo for lo, hi in small.getextrema())


def cover(im, size):
    """Scale and centre-crop so the picture fills size exactly."""
    w, h = size
    scale = max(w / im.width, h / im.height)
    nw, nh = max(w, round(im.width * scale)), max(h, round(im.height * scale))
    im = im.resize((nw, nh), LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return im.crop((left, top, left + w, top + h))


def crop_to_ratio(im, want, notes, name):
    """Centre-crop an opaque picture to the wanted aspect ratio. Small mismatches
    are normal (image generators only make a few shapes), big ones are refused."""
    target = want[0] / want[1]
    got = im.width / im.height
    if abs(got - target) / target <= 0.015:
        return im
    if got > target:                       # too wide: trim left and right
        new_w = round(im.height * target)
        lost = 1 - new_w / im.width
        box = ((im.width - new_w) // 2, 0, (im.width - new_w) // 2 + new_w, im.height)
        sides = "left and right"
    else:                                  # too tall: trim top and bottom
        new_h = round(im.width / target)
        lost = 1 - new_h / im.height
        box = (0, (im.height - new_h) // 2, im.width, (im.height - new_h) // 2 + new_h)
        sides = "top and bottom"
    if lost > 0.30:
        raise Problem("wrong shape: it is %dx%d (%s) but %s must be %s. Cropping would lose %d%% of it."
                      % (im.width, im.height, ratio_text(im.size), name, ratio_text(want), round(lost * 100)))
    notes.append("shape is %s, wanted %s: cropped %d%% off the %s"
                 % (ratio_text(im.size), ratio_text(want), round(lost * 100), sides))
    return im.crop(box)


def feather_edges(im, width):
    """Fade the outermost pixels so a glow that reaches the border never ends in a hard line.
    The fade has round corners, so what is left of a wide glow is a soft blob, not a square."""
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((width, width, im.width - 1 - width, im.height - 1 - width),
                                           radius=min(im.size) * 0.3, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(width / 2))
    im.putalpha(ImageChops.multiply(im.getchannel("A"), mask))
    return im


def solid_box(im, solid=True):
    """The box of the subject itself (not its glow), and the box of everything visible."""
    alpha = im.getchannel("A")
    everything = alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
    if everything is None:
        raise Problem("the picture is completely transparent")
    box = (alpha.point(lambda v: 255 if v > 110 else 0).getbbox() if solid else None) or everything
    return box, everything


def fit_cutout(im, size, pad=0.04, solid=True):
    """Centre the subject of a transparent picture on a canvas.

    With solid=True the subject is sized by its solid part, so a soft glow does not make the
    toy itself small. A glow too wide for the margin makes the toy a little smaller (never
    below 62% of its normal size) so the glow is not cut by the canvas; what still runs off
    is faded out."""
    box, everything = solid_box(im, solid)
    w, h = size
    scale = min(w * (1 - 2 * pad) / (box[2] - box[0]), h * (1 - 2 * pad) / (box[3] - box[1]))
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    if solid:
        halo = im.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox() or box
        reach_x = max(cx - halo[0], halo[2] - cx, 1)
        reach_y = max(cy - halo[1], halo[3] - cy, 1)
        scale = min(scale, max(min(w * 0.49 / reach_x, h * 0.49 / reach_y), scale * 0.62))
    im = im.crop(everything)
    nw, nh = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    small = im.resize((nw, nh), LANCZOS)     # Pillow premultiplies RGBA for us
    left = round(w / 2 - (cx - everything[0]) * scale)
    top = round(h / 2 - (cy - everything[1]) * scale)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.paste(small, (left, top))
    if left < 0 or top < 0 or left + nw > w or top + nh > h:
        feather_edges(canvas, max(2, int(min(size) * max(pad, 0.04))))
    return canvas


# ==========================================================================
# Flat magenta background -> real transparency
# ==========================================================================

KEY_SOLID = 150   # this far from the background colour = certainly subject
GLOW_STEP = 8     # a glow gets at most this much more solid per pixel; a real edge jumps far more


def _grow(dist, region, step, rounds, allowed=None):
    """Spread region into neighbours whose value is at most `step` above a pixel already
    inside. It follows gentle slopes (glows, light trails, soft shadows) and stops at edges,
    and it never enters a pixel that is not `allowed`."""
    for _ in range(rounds):
        near = region.filter(ImageFilter.MaxFilter(3))
        top = ImageChops.multiply(dist, region).filter(ImageFilter.MaxFilter(3))
        gentle = ImageChops.subtract(dist, top).point(lambda v: 255 if v <= step else 0)
        if allowed is not None:
            gentle = ImageChops.darker(gentle, allowed)
        grown = ImageChops.lighter(region, ImageChops.darker(near, gentle))
        if ImageChops.difference(grown, region).getbbox() is None:
            break
        region = grown
    return region


def _soft_region(dist, core, allowed):
    """Everything the background reaches by gentle slopes through `allowed` pixels.
    Found on a reduced copy first (fast), then finished at full size."""
    cell = max(1, round(max(dist.size) / 800))
    if cell == 1:
        return _grow(dist, core, GLOW_STEP, 800, allowed)
    whole = lambda v: 255 if v == 255 else 0
    coarse = dist.filter(ImageFilter.MaxFilter(cell | 1)).reduce(cell)
    seed = core.filter(ImageFilter.MinFilter(cell | 1)).reduce(cell).point(whole)
    gate = allowed.filter(ImageFilter.MinFilter(cell | 1)).reduce(cell).point(whole)
    coarse = _grow(coarse, seed, GLOW_STEP * cell, 800, gate).resize(dist.size, Image.Resampling.NEAREST)
    start = ImageChops.lighter(core, ImageChops.darker(coarse, allowed))
    return _grow(dist, start, GLOW_STEP, cell * 3, allowed)


def _unmix(band, alpha, key):
    """One colour channel of the subject alone, from pixels that are part subject and part
    background:  pixel = alpha * subject + (1 - alpha) * key."""
    def expression(ops):
        value = key + (ops["c"] - key) * 255 / ops["max"](ops["a"], 1)
        return ops["convert"](ops["min"](ops["max"](value, 0), 255), "L")
    if hasattr(ImageMath, "lambda_eval"):
        return ImageMath.lambda_eval(expression, c=band, a=alpha)
    return ImageMath.eval("convert(min(max(k + (c - k) * 255 / max(a, 1), 0), 255), 'L')",   # Pillow < 10.3
                          c=band, a=alpha, k=key)


def flat_half_clear(alpha):
    """Share of a picture that is evenly half-transparent over an area.

    A glow slopes; a thin edge is thin. An even, half-transparent AREA is something else: a
    part of the subject whose colour is close to the background's (a pink scoop on magenta),
    which the background removal took for a glow and made see-through."""
    cell = max(1, round(max(alpha.size) / 400))
    small = alpha.reduce(cell) if cell > 1 else alpha
    half = small.point(lambda v: 255 if 60 <= v <= 230 else 0)
    spread = ImageChops.subtract(small.filter(ImageFilter.MaxFilter(13)), small.filter(ImageFilter.MinFilter(13)))
    flat = ImageChops.darker(half, spread.point(lambda v: 255 if v <= 6 else 0))
    flat = flat.filter(ImageFilter.MinFilter(5))                  # thin lines do not count
    return flat.histogram()[255] / float(small.width * small.height)


def key_magenta(im):
    """Return an RGBA copy with the flat magenta background removed, or None when the
    border is not flat magenta. Hard edges keep their antialiasing, glows and light trails
    become real soft transparency, and no pink is left in either.

    What it cannot know: a PINK part of the subject that touches a glow looks exactly like
    more glow. load_transparent() checks the result for that and refuses the file."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    raw = b"".join(rgb.crop(box).tobytes()
                   for box in ((0, 0, w, 2), (0, h - 2, w, h), (0, 0, 2, h), (w - 2, 0, w, h)))
    border = list(zip(raw[0::3], raw[1::3], raw[2::3]))
    key = tuple(sorted(p[i] for p in border)[len(border) // 2] for i in range(3))
    if not (key[0] > 190 and key[2] > 190 and key[1] < 100):
        return None
    spread = sorted(max(abs(p[0] - key[0]), abs(p[1] - key[1]), abs(p[2] - key[2])) for p in border)
    if spread[int(len(spread) * 0.6)] > 38:          # the border is not one flat colour
        return None
    floor = min(38, max(6, spread[int(len(spread) * 0.95)] + 4))    # how noisy the "flat" colour is

    red, green, blue = rgb.split()
    r, g, b = ImageChops.difference(rgb, Image.new("RGB", rgb.size, key)).split()
    dist = ImageChops.lighter(ImageChops.lighter(r, g), b)      # 0 = background colour
    core = dist.point(lambda v: 255 if v <= floor else 0)

    # Two kinds of soft thing can lie on the background, and each is followed on its own:
    #   light  a glow or a light trail. White, gold or yellow light never lowers the red
    #          channel, so a glow cannot lead into a lilac, purple, blue or green part.
    #   dark   a soft shadow. Red and blue fall together and green stays low, so a shadow
    #          cannot lead into a pink, red or yellow part.
    # A third stop, for both: a line where any colour channel jumps. The distance from the
    # background can stay the same across the border between a glow and a pink toy while
    # green and blue both jump there; a glow itself never changes that fast.
    jump = None
    for band in (red, green, blue):
        step = ImageChops.subtract(band.filter(ImageFilter.MaxFilter(3)), band.filter(ImageFilter.MinFilter(3)))
        jump = step if jump is None else ImageChops.lighter(jump, step)
    smooth = jump.point(lambda v: 255 if v < 20 else 0)
    light = ImageChops.darker(smooth, red.point(lambda v: 255 if v >= key[0] - 40 else 0))
    fall_r = red.point(lambda v: max(0, key[0] - v))
    fall_b = blue.point(lambda v: max(0, key[2] - v))
    dark = ImageChops.darker(ImageChops.difference(fall_r, fall_b).point(lambda v: 255 if v <= 60 else 0),
                             green.point(lambda v: 255 if v <= key[1] + 80 else 0))
    dark = ImageChops.darker(smooth, dark)
    region = ImageChops.lighter(_soft_region(dist, core, light), _soft_region(dist, core, dark))

    # Inside the soft region: the least alpha that explains the colour. On the thin rim
    # next to it: a steeper ramp, so the antialiased edge of the subject stays an edge.
    exact = dist.point(lambda v: 0 if v <= floor else (v - floor) * 255 // (255 - floor))
    ramp = dist.point(lambda v: 0 if v <= floor else 255 if v >= KEY_SOLID
                      else (v - floor) * 255 // (KEY_SOLID - floor))
    rim = region.filter(ImageFilter.MaxFilter(7))
    alpha = Image.composite(ramp, Image.new("L", rgb.size, 255), rim)
    alpha = Image.composite(exact, alpha, region)

    bands = [_unmix(band, alpha, k) for band, k in zip(rgb.split(), key)]
    # The least alpha always pushes a warm glow to pure yellow, which reads green on a
    # dark page. Where that happened, give the glow a little more alpha so it stays gold;
    # white light (blue channel high) is left alone.
    yellowed = ImageChops.darker(region, bands[1].point(lambda v: 255 if v >= 250 else 0))
    boost = ImageChops.multiply(alpha, bands[2].point(lambda v: (255 - v) * 56 // 255))
    alpha = Image.composite(ImageChops.add(alpha, boost), alpha, yellowed)
    bands = [_unmix(band, alpha, k) for band, k in zip(rgb.split(), key)]
    out = Image.merge("RGBA", bands + [alpha])
    clear = Image.new("RGBA", out.size, (0, 0, 0, 0))      # nothing keeps a colour under alpha 0
    out = Image.composite(out, clear, alpha.point(lambda v: 255 if v else 0))
    # How much of the picture became half-transparent (glows, shadows): the caller reports it.
    out.info["soft"] = sum(alpha.histogram()[40:216]) / float(w * h)
    return out


def load_transparent(path, notes, spec):
    """A cut-out picture as RGBA: real transparency, or a flat magenta background removed."""
    im = open_image(path)
    if im.mode == "RGBA" and im.getchannel("A").getextrema()[0] < 250:
        clear = ring_clear(im.getchannel("A"))
        if clear >= spec.get("ring", 0.75):
            return im
        if clear > 0.02:
            raise Problem("the background is only partly transparent: %d%% of the picture's outer edge is "
                          "solid. Ask for a fully transparent background with empty space all around "
                          "the subject." % round((1 - clear) * 100))
        # else: an opaque picture with a few stray transparent pixels. Treat it as opaque.
    keyed = key_magenta(im)
    if keyed is None:
        corner = im.convert("RGB").getpixel((2, 2))
        raise Problem("needs a transparent background but it is opaque, and the background is not flat "
                      "magenta #FF00FF either (corner colour is rgb%s). Ask for real transparency or a "
                      "perfectly flat #FF00FF background." % (corner,))
    notes.append("no alpha channel: removed the flat magenta background")
    if spec.get("solid", True):
        share = flat_half_clear(keyed.getchannel("A"))
        if share > 0.002:
            raise Problem("removing the magenta background left an evenly half-transparent area (%.1f%% of "
                          "the picture). A pink part of the subject was taken for background glow, or a glow "
                          "or shadow is too strong to separate. Ask for real transparency, or for the same "
                          "picture on magenta with hard edges and no glow, haze or shadow." % (share * 100))
        if keyed.info.get("soft", 0) > 0.004:
            # Glows and shadows were turned into soft transparency. A pink or salmon part of the
            # subject that touches a glow of the same colour cannot be told from that glow, so
            # a person has to look once.
            text = ("glows or shadows on the magenta background became soft transparency (%.1f%% of the "
                    "picture). A PINK part that touches a glow can be lost with it" % (keyed.info["soft"] * 100))
            try:
                PREVIEW.mkdir(parents=True, exist_ok=True)
                look = PREVIEW / ("keyed_%s.png" % Path(spec["file"]).stem)
                both = Image.new("RGB", (keyed.width * 2, keyed.height), (10, 20, 54))
                both.paste(im.convert("RGB"), (0, 0))
                both.paste(keyed, (keyed.width, 0), keyed)
                both.thumbnail((1800, 1800))
                both.save(look)
                text += ": compare before and after in %s" % rel(look)
            except OSError:
                pass
            notes.append(text)
    return keyed


# ==========================================================================
# Sprite sheets: find the islands, group them into items, order row by row
# ==========================================================================

def find_islands(alpha, cell, threshold):
    """Connected blobs of non-transparent pixels on a reduced copy of the alpha channel."""
    small = alpha.reduce(cell) if cell > 1 else alpha
    sw, sh = small.size
    data = bytearray(small.point(lambda v: 1 if v >= threshold else 0).tobytes())
    blobs = []
    pos = data.find(1)
    while pos != -1:
        stack = [pos]
        data[pos] = 2
        x0 = x1 = pos % sw
        y0 = y1 = pos // sw
        area = 0
        while stack:
            p = stack.pop()
            area += 1
            y, x = divmod(p, sw)
            if x < x0: x0 = x
            if x > x1: x1 = x
            if y < y0: y0 = y
            if y > y1: y1 = y
            for yy in (y - 1, y, y + 1):
                if 0 <= yy < sh:
                    row = yy * sw
                    for xx in (x - 1, x, x + 1):
                        if 0 <= xx < sw and data[row + xx] == 1:
                            data[row + xx] = 2
                            stack.append(row + xx)
        blobs.append(dict(box=[x0, y0, x1 + 1, y1 + 1], area=area))
        pos = data.find(1, pos + 1)
    return blobs, (sw, sh)


def box_gap(a, b):
    dx = max(0, a[0] - b[2], b[0] - a[2])
    dy = max(0, a[1] - b[3], b[1] - a[3])
    return math.hypot(dx, dy)


def group_islands(blobs, count, small_size, cell=1):
    """Join islands that sit close together (a die and its lightning trail, a globe and
    the die orbiting it) until exactly `count` items are left.
    Returns one dict per item: its box and its parts, largest part first."""
    sw, sh = small_size
    speck = max(3, sw * sh // 60000)
    blobs = [b for b in blobs if b["area"] >= speck]
    if len(blobs) < count:
        raise Problem("found only %d separate item(s), expected %d. Items are touching, overlapping, "
                      "or missing." % (len(blobs), count))
    if len(blobs) > 600:
        raise Problem("found %d separate fragments: the background is not clean" % len(blobs))

    parent = list(range(len(blobs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    pairs = sorted((box_gap(blobs[i]["box"], blobs[j]["box"]), i, j)
                   for i in range(len(blobs)) for j in range(i + 1, len(blobs)))
    groups = len(blobs)
    inside = 0.0          # widest gap we had to bridge inside one item
    between = None        # narrowest gap left between two different items
    for gap, i, j in pairs:
        ri, rj = find(i), find(j)
        if ri == rj:
            continue
        if groups > count:
            parent[ri] = rj
            groups -= 1
            inside = gap
        else:
            between = gap
            break
    if between is not None and inside > 0 and between < inside * 1.2:
        raise Problem("cannot tell the items apart: the loose parts of one item are as far from each "
                      "other (%d px) as two different items are (%d px). Space the items out more."
                      % (round(inside * cell), round(between * cell)))

    members = {}
    for index, blob in enumerate(blobs):
        members.setdefault(find(index), []).append(blob)
    items = []
    for parts in members.values():
        parts.sort(key=lambda blob: -blob["area"])
        boxes = [blob["box"] for blob in parts]
        items.append(dict(parts=parts, box=[min(b[0] for b in boxes), min(b[1] for b in boxes),
                                            max(b[2] for b in boxes), max(b[3] for b in boxes)]))
    areas = sorted((i["box"][2] - i["box"][0]) * (i["box"][3] - i["box"][1]) for i in items)
    median = areas[len(areas) // 2]
    if areas[0] < median * 0.03:
        raise Problem("one of the %d items is far smaller than the rest: a stray fragment was probably "
                      "counted as an item" % count)
    return items


def order_rows(items, cols, rows):
    """Reading order: top row first, left to right. The grid is only used to check the result."""
    middle = lambda item: (item["box"][1] + item["box"][3]) / 2
    items = sorted(items, key=middle)
    heights = sorted(i["box"][3] - i["box"][1] for i in items)
    step = heights[len(heights) // 2] * 0.5
    lines, current = [], [items[0]]
    for item in items[1:]:
        mean = sum(middle(i) for i in current) / len(current)
        if middle(item) - mean > step:
            lines.append(current)
            current = [item]
        else:
            current.append(item)
    lines.append(current)
    if len(lines) != rows or any(len(line) != cols for line in lines):
        raise Problem("items are not laid out as %d row(s) of %d: found row(s) of %s"
                      % (rows, cols, ", ".join(str(len(line)) for line in lines)))
    return [item for line in lines for item in sorted(line, key=lambda i: (i["box"][0] + i["box"][2]) / 2)]


def one_item_per_cell(items, cols, rows, small_size, cell):
    """Every item must fit inside one cell of the grid. Two items that were joined into one
    (a sheet with more items than asked for) are wider or taller than a cell."""
    cell_w, cell_h = small_size[0] / cols, small_size[1] / rows
    for number, item in enumerate(items, 1):
        box = item["box"]
        wide, tall = box[2] - box[0], box[3] - box[1]
        if wide > cell_w * 1.04 or tall > cell_h * 1.04:
            raise Problem("item %d is %d x %d px, larger than one cell of the %d x %d grid (%d x %d px): two "
                          "items were probably joined into one. The sheet must hold exactly %d items, "
                          "nothing between or around them."
                          % (number, wide * cell, tall * cell, cols, rows, round(cell_w * cell),
                             round(cell_h * cell), cols * rows))


def no_item_between(items, cell):
    """A large loose part must clearly belong to its own item. One that sits about as near
    to a neighbour (a ninth toy drawn between the cells) is an extra item, not a part."""
    middle = lambda box: ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    for number, item in enumerate(items, 1):
        main = item["parts"][0]
        home = middle(item["box"])
        for part in item["parts"][1:]:
            if part["area"] < main["area"] * 0.2:
                continue
            here = middle(part["box"])
            own = math.hypot(here[0] - home[0], here[1] - home[1])
            others = [math.hypot(here[0] - middle(o["box"])[0], here[1] - middle(o["box"])[1])
                      for o in items if o is not item]
            if others and own > min(others) * 0.5:
                raise Problem("item %d has a large separate part at about (%d, %d) px that lies between it and "
                              "its neighbour: an extra item. The sheet must hold exactly %d items, nothing "
                              "between or around them." % (number, here[0] * cell, here[1] * cell, len(items)))


def cut_sheet(im, spec, notes):
    """Cut a transparent sprite sheet into its items, in reading order."""
    cols, rows = spec["grid"]
    count = cols * rows
    alpha = im.getchannel("A")
    cell = max(1, math.ceil(max(im.size) / 640))
    error = None
    found = None
    for threshold in (24, 72, 140, 210):       # raise the bar if soft glows glue items together
        blobs, small_size = find_islands(alpha, cell, threshold)
        try:
            found = order_rows(group_islands(blobs, count, small_size, cell), cols, rows)
            one_item_per_cell(found, cols, rows, small_size, cell)
            no_item_between(found, cell)
            break
        except Problem as problem:
            error = problem
            found = None
    if found is None:
        raise error

    for number, (item, name) in enumerate(zip(found, spec["items"]), 1):
        parts = item["parts"]
        if len(parts) > 1:
            text = "item %d (%s) was put together from %d separate parts" % (number, name, len(parts))
            if parts[1]["area"] >= parts[0]["area"] * 0.25:
                text += ", two of them large: make sure this is ONE item in the cut picture"
            notes.append(text)

    full = [[i["box"][0] * cell, i["box"][1] * cell, min(im.width, i["box"][2] * cell),
             min(im.height, i["box"][3] * cell)] for i in found]
    items = []
    for index, box in enumerate(full):
        # Take generous room around the item so its glow comes along, but never
        # reach past the midpoint to a neighbour.
        pad = round(max(box[2] - box[0], box[3] - box[1]) * 0.6)
        left, top, right, bottom = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
        for other_index, other in enumerate(full):
            if other_index == index:
                continue
            if other[1] < box[3] and other[3] > box[1]:  # side by side
                if other[0] >= box[2]:
                    right = min(right, (box[2] + other[0]) // 2)
                elif other[2] <= box[0]:
                    left = max(left, (box[0] + other[2]) // 2)
            if other[0] < box[2] and other[2] > box[0]:  # above / below
                if other[1] >= box[3]:
                    bottom = min(bottom, (box[3] + other[1]) // 2)
                elif other[3] <= box[1]:
                    top = max(top, (box[1] + other[3]) // 2)
        crop = im.crop((max(0, left), max(0, top), min(im.width, right), min(im.height, bottom)))
        items.append(feather_edges(crop, max(2, min(crop.size) // 60)))
    return items


def main_colour(item):
    """"red", "yellow" or "other": the colour most of the strongly coloured pixels have."""
    small = item.resize((48, 48), Image.Resampling.BOX)
    red = yellow = total = 0
    data = small.convert("RGBA").tobytes()
    for at in range(0, len(data), 4):
        r, g, b, a = data[at:at + 4]
        if a < 200:
            continue
        hue, saturation, value = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if saturation < 0.45 or value < 0.35:
            continue
        total += 1
        degrees = hue * 360
        if degrees < 20 or degrees > 340:
            red += 1
        elif 32 <= degrees <= 68:
            yellow += 1
    if total < 20:
        return "other"
    return "red" if red > total * 0.5 else "yellow" if yellow > total * 0.5 else "other"


def check_order(spec, items, notes):
    """The cutter cannot read what an item IS, only where it is. Where the brief fixes a
    colour (the red token, the yellow token) a swap can still be noticed."""
    hues = spec.get("hues") or {}
    wrong = []
    for item, name in zip(items, spec["items"]):
        if name not in hues:
            continue
        seen = main_colour(item)
        if seen != "other" and seen != hues[name]:
            wrong.append("%s looks %s (expected %s)" % (name, seen, hues[name]))
    if len(wrong) >= 2:
        raise Problem("the items are not in the order of the brief: %s. Ask for the sheet again with the "
                      "items in the listed order." % "; ".join(wrong))
    for text in wrong:
        notes.append(text + ": check the order of the items in the cut picture")


def contact_sheet(spec, items, notes):
    """A numbered, named picture of the cut items: one look checks the count and the order."""
    cols, rows = spec["grid"]
    tile, label = 230, 40
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label)), (16, 24, 66))
    draw = ImageDraw.Draw(sheet)
    text_font = font(19)
    for index, (item, name) in enumerate(zip(items, spec["items"])):
        x, y = (index % cols) * tile, (index // cols) * (tile + label)
        draw.rectangle((x + 3, y + 3, x + tile - 4, y + tile + label - 4), outline=(70, 88, 170), width=2)
        thumb = fit_cutout(item.copy(), (tile - 30, tile - 30), spec.get("pad", 0.06), True)
        sheet.paste(thumb, (x + 15, y + 12), thumb)
        draw.text((x + 14, y + tile + 2), "%d  %s" % (index + 1, name), font=text_font, fill=(255, 255, 255))
    try:
        PREVIEW.mkdir(parents=True, exist_ok=True)
        path = PREVIEW / ("cut_%s.png" % Path(spec["file"]).stem)
        sheet.save(path)
        notes.append("cut into %d items: open %s and check the count and the order" % (len(items), rel(path)))
    except OSError as error:
        notes.append("could not write the picture of the cut items (%s)" % tidy(error))


# ==========================================================================
# Placeholders: soft gradients in the site palette, clearly labelled
# ==========================================================================

def font(size, display=False):
    names = (["LilitaOne-Regular.ttf"] if display else []) + ["Nunito-Bold.ttf", "LilitaOne-Regular.ttf"]
    for name in names:
        path = FONTS / name
        if path.exists():
            try:
                return ImageFont.truetype(str(path), int(size))
            except OSError:
                pass
    try:
        return ImageFont.load_default(int(size))
    except TypeError:                         # very old Pillow
        return ImageFont.load_default()


def gradient(size, stops):
    strip = Image.new("RGB", (1, 256))
    for y in range(256):
        t = y / 255
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p0 <= t <= p1:
                k = (t - p0) / (p1 - p0) if p1 > p0 else 0
                strip.putpixel((0, y), tuple(round(c0[i] + (c1[i] - c0[i]) * k) for i in range(3)))
                break
    return strip.resize(size, BICUBIC)


_RADIAL = ImageChops.invert(Image.radial_gradient("L"))


def glow(im, cx, cy, rx, ry, colour, strength=1.0):
    """Blend a soft round patch of colour into im (RGB or RGBA)."""
    rx, ry = max(2, int(rx)), max(2, int(ry))
    mask = _RADIAL.resize((rx * 2, ry * 2), Image.Resampling.BILINEAR)
    mask = mask.point(lambda v: int(255 * strength * (v / 255) ** 1.7))
    layer = Image.new("L", im.size, 0)
    layer.paste(mask, (int(cx - rx), int(cy - ry)))
    if im.mode == "RGBA":                      # pure colour, only the alpha fades: no dark fringe
        light = Image.new("RGBA", im.size, tuple(colour) + (0,))
        light.putalpha(layer)
        im.alpha_composite(light)
    else:
        im.paste(colour, (0, 0), layer)


def night_sky(size, seed, clouds=True):
    w, h = size
    im = gradient(size, [(0, DEEP), (0.42, (12, 24, 66)), (0.78, (36, 34, 112)), (1, VIOLET)])
    rng = random.Random(seed)
    draw = ImageDraw.Draw(im, "RGBA")
    unit = max(w, h) / 1600
    for _ in range(int(w * h / 7000)):
        x, y = rng.uniform(0, w), rng.uniform(0, h * 0.94)
        r = rng.choice([0.8, 0.8, 1, 1, 1.4, 2, 2.6]) * unit
        tint = (255, 226, 160) if rng.random() < 0.2 else WHITE
        draw.ellipse((x - r, y - r, x + r, y + r), fill=tint + (rng.randint(60, 220),))
    if clouds:
        for cx, colour, k in ((0.18, (255, 150, 190), 0.30), (0.52, (150, 130, 255), 0.26), (0.84, (255, 170, 150), 0.28)):
            glow(im, w * cx, h * 1.03, w * 0.30, h * 0.20, colour, k)
    return im


def tag(im, text, cx, cy, size):
    """The small label that makes a placeholder impossible to mistake for real art."""
    draw = ImageDraw.Draw(im, "RGBA" if im.mode == "RGB" else None)
    f = font(size)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=f)
    tw, th = right - left, bottom - top
    px, py = size * 0.75, size * 0.5
    cx = min(max(cx, tw / 2 + px + 2), im.width - tw / 2 - px - 2)
    box = (cx - tw / 2 - px, cy - th / 2 - py, cx + tw / 2 + px, cy + th / 2 + py)
    draw.rounded_rectangle(box, radius=th / 2 + py, fill=(6, 12, 36, 215),
                           outline=(255, 255, 255, 110), width=max(1, int(size) // 12))
    draw.text((cx - tw / 2 - left, cy - th / 2 - top), text, font=f, fill=(255, 255, 255, 240))


def toy(kind, size=512):
    """A simple stand-in toy on a transparent tile: die, token, cone, cross, bar, star, ball (the rock
    mascot), tray."""
    s = size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    u = s / 100
    if kind.startswith("die"):
        pips = int(kind[3:] or 5)
        d.rounded_rectangle((12 * u, 16 * u, 88 * u, 92 * u), radius=17 * u, fill=(150, 28, 24))
        d.rounded_rectangle((12 * u, 9 * u, 88 * u, 85 * u), radius=17 * u, fill=RED)
        d.rounded_rectangle((18 * u, 13 * u, 82 * u, 40 * u), radius=13 * u, fill=(240, 92, 78))
        d.rounded_rectangle((16 * u, 18 * u, 84 * u, 81 * u), radius=14 * u, fill=RED)
        spots = {1: [(50, 47)], 2: [(33, 30), (67, 64)], 3: [(31, 28), (50, 47), (69, 66)],
                 4: [(33, 30), (67, 30), (33, 64), (67, 64)],
                 5: [(31, 28), (69, 28), (50, 47), (31, 66), (69, 66)],
                 6: [(33, 27), (67, 27), (33, 47), (67, 47), (33, 67), (67, 67)]}[pips]
        for x, y in spots:
            d.ellipse(((x - 7.5) * u, (y - 7.5) * u, (x + 7.5) * u, (y + 7.5) * u), fill=WHITE)
    elif kind.startswith("token"):
        main = RED if kind.endswith("red") else YELLOW
        dark = (150, 28, 24) if kind.endswith("red") else (214, 140, 10)
        light = (242, 104, 92) if kind.endswith("red") else (255, 225, 120)
        d.ellipse((10 * u, 26 * u, 90 * u, 90 * u), fill=dark)
        d.ellipse((10 * u, 14 * u, 90 * u, 78 * u), fill=main)
        d.ellipse((24 * u, 24 * u, 76 * u, 66 * u), fill=light)
        d.ellipse((28 * u, 29 * u, 72 * u, 64 * u), fill=main)
    elif kind == "cone":
        d.polygon([(30 * u, 56 * u), (70 * u, 56 * u), (50 * u, 96 * u)], fill=(214, 150, 82))
        for y, colour in ((48, (255, 170, 200)), (34, MINT), (20, (170, 205, 255))):
            d.ellipse((27 * u, (y - 15) * u, 73 * u, (y + 15) * u), fill=colour)
        d.ellipse((44 * u, 0, 58 * u, 13 * u), fill=RED)
    elif kind == "cross":
        for a, b in (((22, 22), (78, 78)), ((78, 22), (22, 78))):
            d.line((a[0] * u, a[1] * u + 4 * u, b[0] * u, b[1] * u + 4 * u), fill=(214, 140, 10), width=int(20 * u))
        for a, b in (((22, 22), (78, 78)), ((78, 22), (22, 78))):
            d.line((a[0] * u, a[1] * u, b[0] * u, b[1] * u), fill=YELLOW, width=int(20 * u))
            for x, y in (a, b):
                d.ellipse(((x - 10) * u, (y - 10) * u, (x + 10) * u, (y + 10) * u), fill=YELLOW)
    elif kind == "bar":
        d.rounded_rectangle((14 * u, 42 * u, 86 * u, 64 * u), radius=11 * u, fill=(150, 28, 24))
        d.rounded_rectangle((14 * u, 38 * u, 86 * u, 58 * u), radius=10 * u, fill=RED)
        for x in (14, 86):
            d.ellipse(((x - 9) * u, 39 * u, (x + 9) * u, 57 * u), fill=(20, 28, 80))
    elif kind == "star":
        pts = []
        for i in range(10):
            radius = (44 if i % 2 == 0 else 19) * u
            angle = -math.pi / 2 + i * math.pi / 5
            pts.append((50 * u + radius * math.cos(angle), 52 * u + radius * math.sin(angle)))
        glow(im, 50 * u, 52 * u, 50 * u, 50 * u, GOLD, 0.55)
        d.polygon(pts, fill=YELLOW)
    elif kind.startswith("ball"):
        # The mascot stand-in: a purple faceted rock with glowing red cracks. No face.
        glow(im, 50 * u, 50 * u, 50 * u, 50 * u, (250, 46, 75), 0.45)
        rim = [(30, 16), (62, 11), (84, 28), (90, 56), (74, 82), (44, 89), (18, 72), (11, 42)]
        d.polygon([(x * u, y * u) for x, y in rim], fill=(46, 7, 85))
        core = (50, 50)
        for n in range(len(rim)):
            a, b = rim[n], rim[(n + 1) % len(rim)]
            shade = (140, 60, 250) if n in (0, 7) else (104, 38, 200) if n in (1, 6) else (86, 27, 165)
            d.polygon([(a[0] * u, a[1] * u), (b[0] * u, b[1] * u), (core[0] * u, core[1] * u)], fill=shade)
        for n in (1, 3, 4, 6):
            d.line((rim[n][0] * u, rim[n][1] * u, core[0] * u, core[1] * u), fill=(250, 46, 75), width=int(3.2 * u))
            d.line((rim[n][0] * u, rim[n][1] * u, core[0] * u, core[1] * u), fill=(251, 223, 151), width=max(1, int(1.0 * u)))
    else:                                       # "tray": a blue game tray with a cream board
        d.rounded_rectangle((6 * u, 16 * u, 94 * u, 94 * u), radius=14 * u, fill=(18, 58, 150))
        d.rounded_rectangle((6 * u, 8 * u, 94 * u, 86 * u), radius=14 * u, fill=TRAY)
        d.rounded_rectangle((16 * u, 17 * u, 84 * u, 77 * u), radius=7 * u, fill=CREAM)
    return im


def stamp(scene, tile, cx, cy, size, angle=0):
    tile = tile.resize((int(size), int(size)), LANCZOS)
    if angle:
        tile = tile.rotate(angle, resample=BICUBIC, expand=True)
    layer = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    layer.paste(tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)))
    return Image.alpha_composite(scene.convert("RGBA"), layer)


def comet_trail(size, start, bend, end, width, seed=1):
    """A green-yellow trail (the colour of the trail of the mascot) on a transparent layer, thin and faint
    at the start, bright at the end."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    steps = 220
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * bend[0] + t ** 2 * end[0]
        y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * bend[1] + t ** 2 * end[1]
        r = width * (0.12 + 0.88 * t) / 2
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(150 + int(80 * t), 235 + int(15 * t), 90 + int(70 * t), int(235 * t ** 1.4)))
    layer = layer.convert("RGBa").filter(ImageFilter.GaussianBlur(width * 0.22)).convert("RGBA")
    rng = random.Random(seed)
    draw = ImageDraw.Draw(layer)
    for _ in range(26):
        t = rng.uniform(0.15, 1)
        x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * bend[0] + t ** 2 * end[0] + rng.uniform(-1, 1) * width
        y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * bend[1] + t ** 2 * end[1] + rng.uniform(-1, 1) * width
        r = rng.uniform(0.03, 0.09) * width
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(236, 255, 190, rng.randint(140, 255)))
    return layer


def brand_icon(game):
    path = BRAND / ("game-icon_%s.png" % game)
    if not path.exists():
        return None
    try:
        icon = Image.open(path).convert("RGBA")
        return icon.crop(icon.getchannel("A").getbbox())
    except OSError:
        return None


def board_tile(game):
    """The real game icon when we have it, a plain tray otherwise."""
    icon = brand_icon(game)
    if icon is None:
        return toy("tray")
    side = max(icon.size)
    tile = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    tile.paste(icon, ((side - icon.width) // 2, (side - icon.height) // 2))
    return tile


def placeholder_scene(spec):
    """An opaque stand-in with the same composition the brief asks for."""
    name = spec["file"]
    w, h = spec["size"]
    seed = name
    if spec["group"] == "shots":                                     # a phone screen
        im = gradient((w, h), [(0, (20, 60, 170)), (0.5, TRAY), (1, (24, 44, 140))])
        draw = ImageDraw.Draw(im, "RGBA")
        draw.rounded_rectangle((w * 0.05, h * 0.03, w * 0.95, h * 0.1), radius=h * 0.03, fill=(10, 20, 54, 150))
        draw.rounded_rectangle((w * 0.08, h * 0.2, w * 0.92, h * 0.7), radius=w * 0.07, fill=(18, 58, 150, 255))
        draw.rounded_rectangle((w * 0.13, h * 0.225, w * 0.87, h * 0.675), radius=w * 0.04, fill=CREAM + (255,))
        draw.rounded_rectangle((w * 0.24, h * 0.815, w * 0.76, h * 0.895), radius=h * 0.04, fill=(32, 130, 44, 255))
        draw.rounded_rectangle((w * 0.24, h * 0.805, w * 0.76, h * 0.88), radius=h * 0.04, fill=GREEN + (255,))
        im = stamp(im, toy("die5"), w * 0.5, h * 0.75, w * 0.2, 10).convert("RGB")
        tag(im, "PLACEHOLDER", w * 0.5, h * 0.41, w / 14)
        tag(im, name, w * 0.5, h * 0.48, w / 20)
        return im
    if name.startswith("hero_"):
        phone = name == "hero_phone.png"
        im = night_sky((w, h), seed)
        # The same composition the brief asks of the real pictures.
        if phone:                                   # toys fill the lower 75%, the top fades to sky
            glow(im, w * 0.55, h * 0.62, w * 0.8, h * 0.42, (120, 80, 230), 0.55)
            trail = comet_trail((w, h), (-w * 0.1, h * 0.98), (w * 0.35, h * 0.8), (w * 0.78, h * 0.3), w * 0.2, seed)
            spots = [("grid-war", 0.27, 0.82, 0.36, -10), ("diceback", 0.72, 0.79, 0.40, 9),
                     ("roll-race", 0.22, 0.52, 0.30, 8), ("six-spots", 0.56, 0.57, 0.30, -6),
                     ("scoop-stack", 0.85, 0.52, 0.24, 12)]
            dice = [(0.42, 0.38, 0.12, 18), (0.88, 0.9, 0.14, -14), (0.12, 0.68, 0.1, 30)]
            ball = (0.76, 0.31, 0.24)
        else:                                       # the left 55% and the top 10% stay calm
            glow(im, w * 0.78, h * 0.55, w * 0.36, h * 0.6, (120, 80, 230), 0.55)
            trail = comet_trail((w, h), (w * 0.46, h * 1.05), (w * 0.68, h * 0.92), (w * 0.9, h * 0.28), h * 0.2, seed)
            spots = [("diceback", 0.70, 0.66, 0.27, -8), ("grid-war", 0.90, 0.74, 0.23, 10),
                     ("roll-race", 0.80, 0.37, 0.18, 7), ("six-spots", 0.63, 0.36, 0.15, -12),
                     ("scoop-stack", 0.955, 0.44, 0.13, 14)]
            dice = [(0.60, 0.84, 0.08, 20), (0.72, 0.2, 0.055, -18), (0.975, 0.9, 0.09, 12)]
            ball = (0.91, 0.26, 0.15)
        im = Image.alpha_composite(im.convert("RGBA"), trail)
        for game, x, y, size, angle in spots:
            im = stamp(im, board_tile(game), w * x, h * y, min(w, h) * size * (1.5 if phone else 1.25), angle)
        for x, y, size, angle in dice:
            im = stamp(im, toy("die5"), w * x, h * y, min(w, h) * size * 1.3, angle)
        im = stamp(im, toy("ball"), w * ball[0], h * ball[1], min(w, h) * ball[2])
        im = im.convert("RGB")
        tag(im, "PLACEHOLDER  " + name, w * (0.74 if not phone else 0.5), h * 0.955, w / (46 if not phone else 26))
        return im
    if name.startswith("bg_"):
        im = night_sky((w, h), seed)
        tag(im, "PLACEHOLDER  " + name, w * 0.5, h * 0.93, w / 60)
        return im
    if name.startswith("game_"):
        game = spec["game"]
        colour = GAME_GLOW[game]
        im = gradient((w, h), [(0, DEEP), (0.55, (14, 26, 78)), (1, (20, 22, 70))])
        rng = random.Random(seed)
        draw = ImageDraw.Draw(im, "RGBA")
        for _ in range(140):
            x, y, r = rng.uniform(0, w), rng.uniform(0, h * 0.7), rng.choice([1.5, 2, 3])
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, rng.randint(50, 190)))
        glow(im, w * 0.5, h * 0.42, w * 0.78, h * 0.5, colour, 0.8)
        glow(im, w * 0.5, h * 0.42, w * 0.4, h * 0.26, WHITE, 0.28)
        im = stamp(im, board_tile(game), w * 0.5, h * 0.44, w * 0.8, -7)
        im = stamp(im, toy("die5"), w * 0.78, h * 0.15, w * 0.22, 16).convert("RGB")
        tag(im, "PLACEHOLDER  " + name, w * 0.5, h * 0.035, w / 30)
        return im
    if name.startswith("studio_"):
        im = gradient((w, h), [(0, (14, 20, 60)), (0.6, (24, 28, 84)), (1, (40, 30, 74))])
        draw = ImageDraw.Draw(im, "RGBA")
        cx, cy, r = w * 0.27, h * 0.3, h * 0.2                      # round window with the sky in it
        draw.ellipse((cx - r * 1.12, cy - r * 1.12, cx + r * 1.12, cy + r * 1.12), fill=(60, 44, 40))
        window = night_sky((int(r * 2), int(r * 2)), seed, clouds=False)
        mask = Image.new("L", window.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, window.width - 1, window.height - 1), fill=255)
        im.paste(window, (int(cx - r), int(cy - r)), mask)
        im = stamp(im, toy("ball"), cx + r * 0.25, cy + r * 0.1, r * 1.1).convert("RGB")
        draw = ImageDraw.Draw(im, "RGBA")
        draw.rectangle((0, h * 0.66, w, h), fill=(120, 78, 46))         # the bench
        draw.rectangle((0, h * 0.66, w, h * 0.69), fill=(150, 100, 60))
        glow(im, w * 0.16, h * 0.5, w * 0.34, h * 0.6, (255, 190, 90), 0.6)     # the lamp
        # every prop on the left half: the right half is where the page's words go
        for kind, x, y, size, angle in (("tray", 0.24, 0.74, 0.32, -5), ("die5", 0.41, 0.8, 0.11, 14),
                                        ("token-red", 0.10, 0.86, 0.1, 0), ("token-yellow", 0.36, 0.9, 0.09, 0),
                                        ("cone", 0.46, 0.7, 0.14, 8), ("die2", 0.06, 0.72, 0.09, -20)):
            im = stamp(im, toy(kind), w * x, h * y, h * size * 1.3, angle)
        im = im.convert("RGB")
        tag(im, "PLACEHOLDER  " + name, w * 0.5, h * 0.95, w / 60)
        return im
    im = night_sky((w, h), seed)                                     # anything else: plain sky
    tag(im, "PLACEHOLDER  " + name, w * 0.5, h * 0.5, w / 30)
    return im


def placeholder_cutout(spec, stem, index=0):
    """A transparent stand-in for a mascot, a toy, an icon or the trail."""
    name = spec["file"]
    label = name if spec["kind"] != "sheet" else "%s  #%d" % (name, index + 1)
    if name == "trail_divider.png":
        w, h = 2400, 800
        im = comet_trail((w, h), (w * 0.06, h * 0.86), (w * 0.52, h * 0.84), (w * 0.9, h * 0.24), h * 0.22, name)
        tag(im, "PLACEHOLDER  " + name, w * 0.42, h * 0.4, 34)
        return im
    if name == "dice-duo_logo.png":
        im = Image.new("RGBA", (1200, 600), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        f = font(250, display=True)
        draw.text((112, 172), "Dice", font=f, fill=(20, 60, 170))
        draw.text((100, 160), "Dice", font=f, fill=WHITE)
        draw.text((632, 172), "Duo", font=f, fill=(214, 110, 10))
        draw.text((620, 160), "Duo", font=f, fill=YELLOW)
        tag(im, "PLACEHOLDER  " + name, 600, 520, 34)
        return im
    s = 800
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    if name.startswith("mascot_"):
        kind = {"mascot_hero.png": "ball", "mascot_wave.png": "ball-wink", "mascot_lost.png": "ball-lost"}[name]
        trail = comet_trail((s, s), (s * 0.02, s * 0.98), (s * 0.3, s * 0.82), (s * 0.56, s * 0.46), s * 0.3, name)
        if kind == "ball-lost":
            trail = comet_trail((s, s), (s * 0.5, s * 0.98), (s * 0.05, s * 0.8), (s * 0.5, s * 0.5), s * 0.24, name)
        im = Image.alpha_composite(im, trail)
        im = stamp(im, toy(kind), s * 0.6, s * 0.4, s * 0.66, {"ball": 0, "ball-wink": -12, "ball-lost": 10}[kind])
        tag(im, "PLACEHOLDER  " + name, s * 0.5, s * 0.9, 34)
        return im
    if name.startswith("game-icon_"):
        im = stamp(im, toy("tray"), s * 0.5, s * 0.5, s * 0.9, -6)
        tag(im, "PLACEHOLDER", s * 0.5, s * 0.5, 60)
        return im
    toys = {"toy-die-five": ("die5", 14), "toy-die-two": ("die2", -18), "toy-token-red": ("token-red", 0),
            "toy-token-yellow": ("token-yellow", 0), "toy-cone": ("cone", 8), "toy-x-yellow": ("cross", 6),
            "toy-line-red": ("bar", -14), "toy-star": ("star", 0)}
    if stem in toys:
        kind, angle = toys[stem]
        im = stamp(im, toy(kind), s * 0.5, s * 0.47, s * 0.8, angle)
        tag(im, "PLACEHOLDER", s * 0.5, s * 0.885, 54)
        return im
    # Mode, feature and genre icons: a glossy toy badge in a colour of its own.
    colours = [SKY, YELLOW, GREEN, (255, 120, 170), ORANGE, (150, 120, 255), MINT, RED]
    colour = colours[index % len(colours)]
    dark = tuple(int(c * 0.62) for c in colour)
    light = tuple(min(255, int(c + (255 - c) * 0.45)) for c in colour)
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((s * 0.12, s * 0.17, s * 0.88, s * 0.9), radius=s * 0.2, fill=dark)
    draw.rounded_rectangle((s * 0.12, s * 0.1, s * 0.88, s * 0.82), radius=s * 0.2, fill=colour)
    draw.rounded_rectangle((s * 0.18, s * 0.14, s * 0.82, s * 0.42), radius=s * 0.15, fill=light)
    draw.rounded_rectangle((s * 0.16, s * 0.2, s * 0.84, s * 0.78), radius=s * 0.17, fill=colour)
    side = ["die5", "token-red", "star", "token-yellow", "die2", "cone"][index % 6]
    im = stamp(im, toy(side), s * 0.5, s * 0.44, s * 0.42, [12, 0, 0, 0, -14, 8][index % 6])
    words = stem.split("-", 1)[1].replace("-", " ")
    tag(im, words, s * 0.5, s * 0.69, 56)
    tag(im, "PLACEHOLDER", s * 0.5, s * 0.935, 40)
    return im


# ==========================================================================
# Writing the web files
# ==========================================================================

def wrote(written, path, width, height):
    written.append(dict(path=rel(path), width=width, height=height))


def write_cutout(im, spec, outs, written, wide=()):
    folder = spec["out"]
    pad, solid = spec.get("pad", 0.04), spec.get("solid", True)
    for stem, w, h in outs:
        big = fit_cutout(im, (w * 2, h * 2), pad, solid)
        small = big.resize((w, h), LANCZOS)
        save_webp(small, folder / (stem + ".webp"), 88)
        save_webp(big, folder / (stem + "@2x.webp"), 84)
        save_png(small, folder / (stem + ".png"))
        wrote(written, folder / (stem + ".webp"), w, h)
        wrote(written, folder / (stem + "@2x.webp"), w * 2, h * 2)
        wrote(written, folder / (stem + ".png"), w, h)
    for stem, shape, widths, fallback in wide:
        top = max(widths)
        big = fit_cutout(im, (top, round(top * shape[1] / shape[0])), pad, solid)
        for width in widths:
            height = round(width * shape[1] / shape[0])
            out = big if width == top else big.resize((width, height), LANCZOS)
            save_webp(out, folder / ("%s-%d.webp" % (stem, width)), 84 if width == top else 88)
            wrote(written, folder / ("%s-%d.webp" % (stem, width)), width, height)
        height = round(fallback * shape[1] / shape[0])
        save_png(big.resize((fallback, height), LANCZOS), folder / (stem + ".png"))
        wrote(written, folder / (stem + ".png"), fallback, height)


def write_scene(im, spec, notes, written):
    want = spec["size"]
    im = im.convert("RGB")
    if im.width < max(spec["widths"]):
        notes.append("only %d px wide after cropping: the %d px web size is scaled up and will look soft"
                     % (im.width, max(spec["widths"])))
    for width in spec["widths"]:
        height = round(width * want[1] / want[0])
        out = cover(im, (width, height))
        stem = "%s-%d" % (spec["stem"], width)
        save_webp(out, spec["out"] / (stem + ".webp"), 80)
        save_jpg(out, spec["out"] / (stem + ".jpg"), 80)
        wrote(written, spec["out"] / (stem + ".webp"), width, height)
        wrote(written, spec["out"] / (stem + ".jpg"), width, height)


def write_tile(im, spec, written):
    im = im.convert("RGB")
    for stem, w, h in spec["outs"]:
        big = cover(im, (w * 2, h * 2))
        small = cover(im, (w, h))
        folder = spec["out"]
        save_webp(small, folder / (stem + ".webp"), 84)
        save_webp(big, folder / (stem + "@2x.webp"), 82)
        save_jpg(small, folder / (stem + ".jpg"), 84)
        wrote(written, folder / (stem + ".webp"), w, h)
        wrote(written, folder / (stem + "@2x.webp"), w * 2, h * 2)
        wrote(written, folder / (stem + ".jpg"), w, h)


def item_outs(spec, name):
    """Every size one item of a sheet is written at."""
    return [(name, spec["canvas"], spec["canvas"])] + list((spec.get("extra") or {}).get(name, []))


def write_placeholder(spec, written):
    global FAST
    FAST = True
    try:
        _write_placeholder(spec, written)
    finally:
        FAST = False


def _write_placeholder(spec, written):
    kind = spec["kind"]
    if kind == "scene":
        write_scene(placeholder_scene(spec), spec, [], written)
    elif kind == "tile":
        write_tile(placeholder_scene(spec), spec, written)
    elif kind == "sheet":
        for index, name in enumerate(spec["items"]):
            write_cutout(placeholder_cutout(spec, name, index), spec, item_outs(spec, name), written)
    else:
        outs, wide = spec.get("outs", []), spec.get("wide", [])
        first = (wide[0][0] if wide else outs[0][0])
        write_cutout(placeholder_cutout(spec, first), spec, outs, written, wide)


def check_size(im, spec, notes):
    want = spec["size"]
    if want is None:
        return
    if im.size != want:
        same_shape = abs(im.width / im.height - want[0] / want[1]) / (want[0] / want[1]) <= 0.015
        if im.width < want[0] and same_shape:
            notes.append("smaller than asked: %dx%d instead of %dx%d" % (im.size + want))
        elif not same_shape and spec["kind"] in ("cutout", "sheet"):
            notes.append("shape is %s (%dx%d), wanted %s: fine here, the subject is trimmed out anyway"
                         % ((ratio_text(im.size),) + im.size + (ratio_text(want),)))


def big_enough(im, spec, outs, wide, notes, label):
    """Refuse a subject far too small for its place; say so when it is only a little small."""
    solid, pad = spec.get("solid", True), spec.get("pad", 0.04)
    box, _everything = solid_box(im, solid)
    bw, bh = box[2] - box[0], box[3] - box[1]
    canvases = [(w * 2, h * 2) for _stem, w, h in outs]
    canvases += [(max(widths), round(max(widths) * shape[1] / shape[0])) for _stem, shape, widths, _f in wide]
    blow_up = max(min(cw * (1 - 2 * pad) / bw, ch * (1 - 2 * pad) / bh) for cw, ch in canvases)
    if blow_up > 2:
        raise Problem("%s is too small: the subject is only %d x %d px and would be blown up %.1f times. "
                      "Ask for a larger picture." % (label, bw, bh, blow_up))
    if blow_up > 1.2:
        notes.append("%s is a little small (%d x %d px): it is scaled up %.1f times and may look soft"
                     % (label, bw, bh, blow_up))


def import_real(spec, path, notes, written):
    kind = spec["kind"]
    if kind in ("cutout", "sheet"):
        im = load_transparent(path, notes, spec)
        check_size(im, spec, notes)
        if kind == "sheet":
            items = cut_sheet(im, spec, notes)
            check_order(spec, items, notes)
            for item, name in zip(items, spec["items"]):
                big_enough(item, spec, item_outs(spec, name), [], notes, name)
            contact_sheet(spec, items, notes)
            for item, name in zip(items, spec["items"]):
                write_cutout(item, spec, item_outs(spec, name), written)
            return im
        outs, wide = spec.get("outs", []), spec.get("wide", [])
        alpha = im.getchannel("A")
        edge = alpha.point(lambda v: 255 if v > 40 else 0).getbbox()
        if edge and spec.get("pad", 0.04) > 0 and (edge[0] <= 1 or edge[1] <= 1 or edge[2] >= im.width - 1
                                                   or edge[3] >= im.height - 1):
            notes.append("the subject touches the edge of the picture: check that nothing is cut off")
        if spec["group"] == "art" and spec.get("solid", True):
            box, _everything = solid_box(im)
            body = alpha.crop(box).point(lambda v: 255 if v > 200 else 0)
            filled = body.histogram()[255] / float(max(1, body.width * body.height))
            if filled > 0.995 and body.width * body.height > 0.5 * im.width * im.height:
                raise Problem("this is a rectangular picture with an empty margin, not a cut-out subject: "
                              "the background inside the rectangle is still there")
        big_enough(im, spec, outs, wide, notes, spec["file"])
        write_cutout(im, spec, outs, written, wide)
        return im

    im = open_image(path)
    if im.mode == "RGBA":
        alpha = im.getchannel("A")
        share = clear_share(alpha)
        if share > 0.005:
            raise Problem("%d%% of it is transparent, but this must be a full picture with nothing "
                          "see-through. Ask for it again with an opaque background." % max(1, round(share * 100)))
        flat = Image.new("RGB", im.size, NIGHT)
        flat.paste(im, mask=alpha)
        im = flat
    if detail(im) < 14:
        raise Problem("it is one flat colour (rgb%s): an empty canvas, not a picture" % (im.getpixel((2, 2)),))
    check_size(im, spec, notes)
    im = crop_to_ratio(im, spec["size"], notes, spec["file"])
    need = max(spec["widths"]) if kind == "scene" else max(w * 2 for _stem, w, _h in spec["outs"])
    if im.width < need * 0.6:
        raise Problem("too small: %d px wide after cropping, and the page shows it up to %d px wide. "
                      "Ask for at least %d px." % (im.width, need, need))
    if kind == "scene":
        write_scene(im, spec, notes, written)
    else:
        write_tile(im, spec, written)
    return im


def build_og_image(hero):
    """The 1200x630 social share picture: the hero art plus the studio name."""
    w, h = 1200, 630
    im = cover(hero.convert("RGB"), (w, h)).convert("RGBA")
    shade = Image.new("RGBA", (w, h), DEEP + (0,))
    ramp = Image.linear_gradient("L").transpose(Image.Transpose.ROTATE_270).resize((w, h))   # white left -> black right
    shade.putalpha(ramp.point(lambda v: int(min(255, max(0, (v - 95) * 2.0)) * 0.9)))
    im = Image.alpha_composite(im, shade)
    # The studio mark: the purple rock comet, as cut from the mascot by tools/make_brand.py.
    mark_path = ROOT / "assets" / "icons" / "logo-mark@3x.png"
    if mark_path.exists():
        mark = Image.open(mark_path).convert("RGBA")
        im.alpha_composite(mark, (62, 160))
    draw = ImageDraw.Draw(im)
    title = font(86, display=True)             # fits inside the calm left 45% of the hero art
    draw.text((71, 297), "Bouncy Comet", font=title, fill=(4, 9, 30))
    draw.text((66, 290), "Bouncy Comet", font=title, fill=WHITE)
    draw.text((70, 408), "Independent mobile game studio", font=font(32), fill=(201, 166, 255))
    draw.text((70, 458), "Makers of Dice Duo", font=font(28), fill=(214, 222, 250))
    OG_IMAGE.parent.mkdir(parents=True, exist_ok=True)
    save_jpg(im, OG_IMAGE, 88)


# ==========================================================================
# Run / check
# ==========================================================================

def find_source(spec):
    folder = spec["folder"]
    if not folder.is_dir():
        return None
    wanted = spec["file"].lower()
    for path in folder.iterdir():
        if path.is_file() and path.name.lower() == wanted:
            return path
    return None


def strangers():
    """Files in the drop folders that match no expected name, with the closest guess."""
    found = []
    for folder in (INCOMING, GAME, BRAND):
        if not folder.is_dir():
            continue
        expected = [s["file"] for s in ALL_SPECS if s["folder"] == folder]
        lower = {name.lower() for name in expected}
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.name.lower() in lower or path.name.startswith("."):
                continue
            if path.name in REFERENCE_ONLY:
                continue
            if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                continue
            guess = difflib.get_close_matches(path.stem.lower(), [Path(n).stem for n in expected], 1, 0.5)
            hint = "did you mean %s.png?" % guess[0] if guess else "not one of the expected names"
            if path.suffix.lower() != ".png":
                hint += " (must be a .png)"
            found.append("%s: %s" % (rel(path), hint))
    return found


def import_one(spec):
    """Import one source, or stand a placeholder in for it. Never raises: whatever goes
    wrong with one file is written down in its record and the run goes on."""
    notes, written = [], []
    want = "%dx%d" % spec["size"] if spec["size"] else "any size"
    if spec["kind"] in ("cutout", "sheet"):
        want += ", transparent"
    if spec["kind"] == "sheet":
        want += ", %d x %d items" % spec["grid"]
    record = dict(file=spec["file"], group=spec["group"], wanted=want, got=None)
    picture = None
    path = find_source(spec)
    status = "placeholder"
    if path is not None:
        try:
            with Image.open(path) as probe:
                record["got"] = "%dx%d" % probe.size
            picture = import_real(spec, path, notes, written)
            status = "real"
        except Problem as problem:
            status = "rejected"
            notes.append(str(problem))
        except Exception as error:          # a broken, huge or unreadable file must not stop the run
            status = "rejected"
            notes.append("cannot be used (%s: %s)" % (type(error).__name__, tidy(error)))
    if status != "real":
        written, picture = [], None
        try:
            write_placeholder(spec, written)
        except Exception as error:          # a locked or read-only output file, a full disk
            status = "rejected"
            notes.append("its files in assets/ could not be written (%s: %s): close whatever holds them "
                         "and run again" % (type(error).__name__, tidy(error)))
    record.update(status=status, notes=notes, outputs=written)
    return record, picture


def add_checksums(records):
    for record in records:
        for out in record["outputs"]:
            target = ROOT / out["path"]
            out["sha1"] = sha1(target) if target.exists() else None


def seal(sources):
    """A checksum of the manifest's own list, so a status changed by hand is noticed."""
    text = json.dumps(sources, sort_keys=True, separators=(",", ":")) + "|bouncy-comet-art"
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def expected_names(spec):
    """Every file one source is written to, whether or not this run managed to write it."""
    kind, names = spec["kind"], []
    if kind == "scene":
        for width in spec["widths"]:
            names += ["%s-%d.webp" % (spec["stem"], width), "%s-%d.jpg" % (spec["stem"], width)]
    elif kind == "tile":
        for stem, _w, _h in spec["outs"]:
            names += [stem + ".webp", stem + "@2x.webp", stem + ".jpg"]
    else:
        outs = list(spec.get("outs", []))
        if kind == "sheet":
            outs = [out for name in spec["items"] for out in item_outs(spec, name)]
        for stem, _w, _h in outs:
            names += [stem + ".webp", stem + "@2x.webp", stem + ".png"]
        for stem, _shape, widths, _fallback in spec.get("wide", []):
            names += ["%s-%d.webp" % (stem, width) for width in widths] + [stem + ".png"]
    return [rel(spec["out"] / name) for name in names]


def prune():
    """Remove pictures in assets/art and assets/shots under names this script does not write:
    left-overs of an earlier version of it, which no page uses any more."""
    keep = {name for spec in ALL_SPECS for name in expected_names(spec)}
    removed = []
    for folder in (ART, SHOTS):
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix.lower() in (".webp", ".png", ".jpg") and rel(path) not in keep:
                try:
                    path.unlink()
                    removed.append(rel(path))
                except OSError:
                    pass
    if OLD_MANIFEST.exists():
        try:
            OLD_MANIFEST.unlink()
            removed.append(rel(OLD_MANIFEST))
        except OSError:
            pass
    return removed


def run():
    ART.mkdir(parents=True, exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)
    # From here until the last line of this function the pictures in assets/ are in between
    # two states. Say so first: --check refuses a manifest that is not marked complete.
    write_json(MANIFEST, dict(complete=False, note="An import run started and did not finish. Run  "
                                                   "python tools/import_art.py  again."))
    records, hero = [], None
    for spec in ALL_SPECS:
        record, picture = import_one(spec)
        records.append(record)
        if spec["file"] == "hero_desktop.png" and record["status"] == "real":
            hero = picture
        status = record["status"]
        mark = {"real": "ok  ", "placeholder": "wait", "rejected": "BAD "}[status]
        print("  [%s] %-26s %s" % (mark, spec["file"],
                                    "real art imported" if status == "real" else
                                    "not there yet: placeholder written" if status == "placeholder" else
                                    "REJECTED, placeholder written"))
        for note in record["notes"]:
            print("         - " + note)

    # The share picture is built from the hero art, so it is a source of its own for --check.
    share = dict(file="og-image.jpg", group="share", wanted="1200x630, built from hero_desktop.png",
                 got=None, notes=[], outputs=[])
    if hero is not None:
        try:
            build_og_image(hero)
            share["status"] = "real"
            print("  [ok  ] og-image.jpg               rebuilt from the hero art")
        except Exception as error:
            share["status"] = "rejected"
            share["notes"].append("could not be written (%s: %s)" % (type(error).__name__, tidy(error)))
            print("  [BAD ] og-image.jpg               " + share["notes"][-1])
    else:
        share["status"] = "placeholder"
        share["notes"].append("still the old share picture: it is rebuilt when hero_desktop.png is real")
        print("  [wait] og-image.jpg               old share picture kept until hero_desktop.png is real")
    if OG_IMAGE.exists():
        wrote(share["outputs"], OG_IMAGE, 1200, 630)
    records.append(share)

    for path in prune():
        print("  [gone] %-26s left over from an earlier run, removed" % path)

    odd = strangers()
    for line in odd:
        print("  [?   ] " + line)

    add_checksums(records)
    waiting = [r["file"] for r in records if r["status"] != "real"]
    rejected = [r["file"] for r in records if r["status"] == "rejected"]
    # The notes stay on this computer; the manifest that is committed holds no free text.
    try:
        write_json(LOG, dict(note="Notes of the last  python tools/import_art.py  run. Not published.",
                             unexpected_files=odd,
                             sources=[dict(file=r["file"], status=r["status"], wanted=r["wanted"], got=r["got"],
                                           notes=r["notes"]) for r in records]))
    except OSError:
        pass
    sources = [dict(file=r["file"], group=r["group"], status=r["status"], outputs=r["outputs"]) for r in records]
    write_json(MANIFEST, dict(
        note="Written by tools/import_art.py. Do not edit by hand. A source that is not 'real' must not "
             "be published: run  python tools/import_art.py --check  before every push.",
        complete=True,
        placeholders=len(waiting),
        seal=seal(sources),
        sources=sources,
    ))
    real = len(records) - len(waiting)
    print("\n  %d of %d sources are real, %d still placeholder. Manifest: %s   Notes: %s"
          % (real, len(records), len(waiting), rel(MANIFEST), rel(LOG)))
    if rejected:
        print("  REJECTED: %s. Read the notes above, fix or replace the files, run again." % ", ".join(rejected))
        return 1
    return 0


def check():
    if not MANIFEST.exists():
        print("No %s yet: run  python tools/import_art.py  first." % rel(MANIFEST))
        return 1
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except ValueError:
        manifest = {}
    if manifest.get("complete") is not True or not isinstance(manifest.get("sources"), list):
        print("  NOT READY TO PUBLISH: the last import run did not finish (it was stopped or it crashed),\n"
              "  so nobody knows what is in assets/. Run  python tools/import_art.py  again.")
        return 1
    if manifest.get("seal") != seal(manifest["sources"]):
        print("  NOT READY TO PUBLISH: %s was changed by hand, so it proves nothing.\n"
              "  Run  python tools/import_art.py  again." % rel(MANIFEST))
        return 1
    notes = {}
    if LOG.exists():
        try:
            log = json.loads(LOG.read_text(encoding="utf-8"))
            notes = {source["file"]: source.get("notes", []) for source in log.get("sources", [])}
        except (ValueError, KeyError, TypeError):
            notes = {}
    bad = 0
    expected = {spec["file"] for spec in ALL_SPECS} | {"og-image.jpg"}
    listed = {record.get("file") for record in manifest["sources"]}
    for name in sorted(expected - listed):
        bad += 1
        print("  NOT LISTED  %s (the manifest is from an older version of this script: run the import again)" % name)
    for record in manifest["sources"]:
        if record.get("status") != "real":
            bad += 1
            print("  %-11s %s" % (str(record.get("status")).upper(), record.get("file")))
            for note in notes.get(record.get("file"), []):
                print("              - " + note)
        if not record.get("outputs"):
            bad += 1
            print("  NO FILES    %s" % record.get("file"))
        for out in record.get("outputs", []):
            target = ROOT / out["path"]
            if not target.exists():
                bad += 1
                print("  MISSING     %s" % out["path"])
            elif out.get("sha1") != sha1(target):
                bad += 1
                print("  CHANGED     %s is not the file the last import run wrote" % out["path"])
    if bad:
        print("\n  NOT READY TO PUBLISH: %d problem(s). Run  python tools/import_art.py  and read its notes." % bad)
        return 1
    print("  All %d sources are real art and every file is unchanged. Safe to publish." % len(manifest["sources"]))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="change nothing; exit 1 unless every picture in assets/ is real art and unchanged")
    args = parser.parse_args()
    sys.exit(check() if args.check else run())


if __name__ == "__main__":
    main()
