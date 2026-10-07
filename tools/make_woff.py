#!/usr/bin/env python3
"""Pack the site's TrueType fonts as WOFF: the same font, unchanged, only compressed.

    python tools/make_woff.py

Reads   assets/fonts/*.ttf
Writes  assets/fonts/*.woff       (about half the size)

Needs Python 3 and nothing else. WOFF 1.0 is a container: every table of the font is
stored as it is, compressed with zlib. Nothing is removed, renamed or subset, so the
fonts stay exactly the fonts their licences (assets/fonts/*-OFL.txt) describe.
Run it again only if a .ttf in assets/fonts is replaced.

WOFF2 would be about 20% smaller still, but it needs the Brotli compressor, which is
not part of Python. If fonttools and brotli are ever installed, "fonttools ttLib.woff2
compress" makes the .woff2 files; add them in front of the .woff lines in css/style.css.
"""
import struct
import sys
import zlib
from pathlib import Path

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def to_woff(data):
    flavor, count = struct.unpack(">4sH", data[:6])
    tables = []
    for index in range(count):
        tag, checksum, offset, length = struct.unpack(">4sLLL", data[12 + index * 16:28 + index * 16])
        tables.append((tag, checksum, data[offset:offset + length]))
    tables.sort(key=lambda table: table[0])

    directory, body = [], []
    position = 44 + 20 * count
    sfnt_size = 12 + 16 * count
    for tag, checksum, raw in tables:
        packed = zlib.compress(raw, 9)
        if len(packed) >= len(raw):
            packed = raw                                # stored as it is
        directory.append(struct.pack(">4sLLLL", tag, position, len(packed), len(raw), checksum))
        padding = (4 - len(packed) % 4) % 4
        body.append(packed + b"\0" * padding)
        position += len(packed) + padding
        sfnt_size += (len(raw) + 3) & ~3
    header = struct.pack(">4s4sLHHLHHLLLLL", b"wOFF", flavor, position, count, 0, sfnt_size, 1, 0, 0, 0, 0, 0, 0)
    return header + b"".join(directory) + b"".join(body)


def from_woff(data):
    """Unpack a WOFF again (only used to prove the round trip keeps every table)."""
    count = struct.unpack(">H", data[12:14])[0]
    tables = {}
    for index in range(count):
        tag, offset, packed, length, _checksum = struct.unpack(">4sLLLL", data[44 + index * 20:64 + index * 20])
        raw = data[offset:offset + packed]
        tables[tag] = raw if packed == length else zlib.decompress(raw)
    return tables


def main():
    fonts = sorted(FONTS.glob("*.ttf"))
    if not fonts:
        sys.exit("no .ttf files in %s" % FONTS)
    for path in fonts:
        data = path.read_bytes()
        woff = to_woff(data)
        count = struct.unpack(">H", data[4:6])[0]
        original = {}
        for index in range(count):
            tag, _checksum, offset, length = struct.unpack(">4sLLL", data[12 + index * 16:28 + index * 16])
            original[tag] = data[offset:offset + length]
        if from_woff(woff) != original:
            sys.exit("%s: the packed font does not unpack to the same tables" % path.name)
        target = path.with_suffix(".woff")
        target.write_bytes(woff)
        print("  %-24s %7d bytes  ->  %-24s %7d bytes  (%d%%)"
              % (path.name, len(data), target.name, len(woff), round(100 * len(woff) / len(data))))


if __name__ == "__main__":
    main()
