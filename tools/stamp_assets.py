#!/usr/bin/env python3
"""Cache stamps: gives every picture, stylesheet, script and icon link a ?v=<checksum>.

    python tools/stamp_assets.py           rewrite the links in every page and the manifest
    python tools/stamp_assets.py --check   change nothing; exit 1 if any link is out of date

Why: the art keeps its file names when it is replaced (a placeholder and the real picture are
both assets/art/mascot-lost-400.webp), and so do css/style.css and js/main.js. A browser or a
CDN that already holds the old file under that name goes on showing it. The stamp is the first
8 characters of the file's SHA-1, so the address changes exactly when the file does and an
unchanged file stays cached.

Not a build step: the pages stay hand-written and what is in the repo is what ships. This only
rewrites the ?v= part of links that are already there. Fonts are left alone (they never change).

Run it after  python tools/import_art.py , after  python tools/make_brand.py  and after any
edit of css/style.css or js/main.js.
"""
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The manifest first: the pages link to it, so its own stamps must be in place before it is checksummed.
PAGES = [ROOT / "site.webmanifest"] + sorted(ROOT.glob("*.html"))

# css/style.css, js/main.js and the manifest where they open an attribute (href="...", never a mention in
# a comment), and assets/<folder>/<name>.<picture type> anywhere; each with an optional old stamp.
LINK = re.compile(
    r"(?P<path>(?:(?:(?<=\")|(?<=\"/))(?:css/style\.css|js/main\.js|site\.webmanifest)"
    r"|assets/(?:art|shots|icons|img)/[A-Za-z0-9_@.\-]+\.(?:png|jpe?g|webp|ico)))"
    r"(?:\?v=[0-9a-f]+)?")


def stamp(path, cache={}):
    if path not in cache:
        target = ROOT / path
        cache[path] = hashlib.sha1(target.read_bytes()).hexdigest()[:8] if target.is_file() else None
    return cache[path]


def restamp(text, missing):
    def swap(match):
        path = match.group("path")
        value = stamp(path)
        if value is None:
            missing.add(path)
            return path
        return "%s?v=%s" % (path, value)
    return LINK.sub(swap, text)


def main():
    check = "--check" in sys.argv[1:]
    stale, missing, links = [], set(), 0
    for page in PAGES:
        raw = page.read_bytes().decode("utf-8")
        new = restamp(raw, missing)
        links += len(LINK.findall(new))
        if new != raw:
            stale.append(page.name)
            if not check:
                page.write_bytes(new.encode("utf-8"))
    for path in sorted(missing):
        print("  MISSING  %s (linked from a page, not in the repo)" % path)
    if check:
        if stale or missing:
            print("  STALE    %s\n  Run  python tools/stamp_assets.py" % ", ".join(stale))
            return 1
        print("  All %d links carry the checksum of their file." % links)
        return 0
    print("  %d links stamped in %d files%s." % (links, len(PAGES),
          (", changed: " + ", ".join(stale)) if stale else ", nothing to change"))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
