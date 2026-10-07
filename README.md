# Bouncy Comet — bouncycomet.com

Marketing site for **Bouncy Comet**, an independent mobile game studio making
puzzle, hypercasual, arcade, hybrid-casual, multiplayer and kids' games.

First title, in closed testing on Android: **Dice Duo: 2 Player Board Games**, one app with
five two-player dice games (Grid War, DiceBack, Roll Race, Six Spots, Scoop Stack).
"Dice Duo" is the product; "DiceBack" is one of its five games.

The look is "a toybox floating in a night sky": dark indigo pages, glossy toy colours, and the
studio mascot, Comet: a purple rock comet with glowing red lava cracks and a green-yellow trail.
The accent colours of the site are sampled from it (violet, lilac, lava red, a touch of lime).

---

## Stack

Plain static HTML, CSS and vanilla JavaScript. **No build step, no npm, no framework.**
What is in the repo is exactly what ships.

```
index.html        Home — hero art, the five games, ways to play, real screenshots, how we build
games.html        Portfolio — Dice Duo, its five games, and the prototype directions
diceback.html     Dice Duo page (file name kept for old links) — a section per game with its
                  rules in three steps, modes, features, 11 screenshots, FAQ
about.html        Workshop illustration, studio story, genres, the four-step path, the house-rules board
contact.html      Contact form + routes
privacy.html      Privacy Policy (app-store ready)
terms.html        Terms of Service
account-deletion.html  Dice Duo account/data deletion request and retention information
privacy-policy.html, terms-of-service.html   Redirects to the two pages above
404.html          Not-found page (uses root-absolute paths — see note below)

css/style.css     Full design system: tokens, components, responsive, reduced-motion
js/main.js        Nav, scroll reveal, rails (carousels), toy parallax, screenshot lightbox, contact form

assets/art/       Illustrations, cut and resized by tools/import_art.py
assets/shots/     Real game screenshots, resized by tools/import_art.py
assets/fonts/     Lilita One + Nunito Bold, self-hosted (.woff, .ttf fallback), with their licences
assets/img/       The social share (OG) image, built by tools/import_art.py from the hero art
assets/icons/     The logo mark, favicons, apple-touch-icon, PWA icons: all made by tools/make_brand.py

tools/import_art.py     Turns the art in ArtDrop/ into the files in assets/art and assets/shots
tools/art-manifest.json Written by import_art.py: status and checksum of every picture (no notes)
tools/make_woff.py      Packs assets/fonts/*.ttf as .woff (same font, only compressed)
tools/make_brand.py     Cuts the logo mark out of ArtDrop/incoming/mascot_hero.png and builds every icon
tools/stamp_assets.py   Writes ?v=<checksum> on every picture, CSS, JS and icon link (see "Cache stamps")
ArtDrop/          Source art, the art brief, reference shots, import notes. Git-ignored, never published.

CNAME             Custom domain for GitHub Pages
.nojekyll         Stops GitHub Pages running Jekyll over the files
robots.txt        Crawl rules + sitemap pointer
sitemap.xml       Page index for search engines
site.webmanifest  PWA metadata
serve.py          Local preview server
```

---

## Preview locally

```bash
python serve.py
```

Then open <http://localhost:8000>. Pass a port to override: `python serve.py 3000`.

The server also serves `404.html` for missing paths, so the 404 page can be tested properly.

---

## Deploy

**The site is live at <https://bouncycomet.com>.**

Hosted on GitHub Pages from the `main` branch, root folder. Everything below is already
done; it is recorded here so the setup can be rebuilt or debugged later.

| Piece | Value |
| --- | --- |
| Repo | <https://github.com/shakil140/BouncyComet> (public - Pages needs this on the free plan) |
| Source | `main` branch, `/ (root)` |
| Custom domain | `bouncycomet.com`, set automatically from the `CNAME` file |
| Certificate | Let's Encrypt, issued 21 Sep 2026, auto-renews |
| Registrar / DNS | Squarespace (migrated from Google Domains) |

### Updating the site

```bash
python tools/stamp_assets.py
python tools/import_art.py --check
git add -A
git commit -m "Update site"
git push
```

Live in roughly 60 seconds. That is the whole workflow. The first line renews the cache stamps
(below). The second must say "Safe to publish": it fails while any placeholder picture is still
in `assets/`.

### Cache stamps

Pictures keep their file names when they are replaced (a placeholder and the real picture are both
`assets/art/mascot-lost-400.webp`), and so do `css/style.css`, `js/main.js` and the icons. GitHub
Pages lets browsers keep a file for ten minutes and browsers often keep it longer, so a visitor
could go on seeing the old picture under the same address. Every link to a picture, the stylesheet,
the script, an icon or the manifest therefore ends in `?v=` plus the first 8 characters of the
file's SHA-1: the address changes exactly when the file does.

```bash
python tools/stamp_assets.py           # after an import, after make_brand.py, after editing CSS or JS
python tools/stamp_assets.py --check   # changes nothing, fails if a stamp is out of date
```

It only rewrites the `?v=` part of links that are already in the pages; fonts are left alone.
When a new picture is added to a page, write its plain path and run the script.

### DNS records at Squarespace

Set under **Domains -> bouncycomet.com -> DNS -> DNS Settings**. The four A records are
GitHub's load-balanced Pages edge; all four are required.

| Type | Host | Value |
| --- | --- | --- |
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `shakil140.github.io` |

Do **not** touch the `MX`, `TXT` (SPF) or `google._domainkey` (DKIM) records - those run
Google Workspace email on this domain. Deleting them breaks mail.

### Path convention — important

Every page uses **relative** asset paths (`css/style.css`, `assets/img/…`) **except `404.html`**,
which uses **root-absolute** paths (`/css/style.css`). This is deliberate: a 404 can be served
from any URL depth, so relative paths there would break.

---

## Images

All artwork goes through one script. It needs Python 3 and Pillow, nothing else.

```bash
python tools/import_art.py
```

It reads three folders inside `ArtDrop/` (git-ignored, never published):

| Folder | What goes in | Names |
| --- | --- | --- |
| `ArtDrop/incoming/` | The 17 illustrations from the art brief `ArtDrop/GPT_PROMPT.md` | `mascot_hero.png`, `hero_desktop.png`, `game_grid-war.png`, `sheet_toys.png` ... exactly as in the brief |
| `ArtDrop/reference/game/` | 11 real screenshots of the game, 1080×1920 | `game_01_home.png` ... `game_11_loading.png` |
| `ArtDrop/reference/brand/` | The Dice Duo logo and the five game icons | `dice-duo_logo.png`, `game-icon_grid-war.png` ... |

and writes `assets/art/`, `assets/shots/` and `tools/art-manifest.json`. What it does:

- **Checks every file.** Wrong name: it says which file it does not know and guesses the
  name you meant. Wrong shape: a small mismatch is centre-cropped (image generators only
  make a few shapes) and reported; a big one is refused with the reason. Also refused:
  a picture far too small for its place, a "full picture" with see-through parts, an empty
  one-colour canvas, a cut-out whose background was never removed, a file that is not an image.
- **Makes transparency.** A cut-out should arrive with real transparency. Without an alpha
  channel it must sit on flat magenta `#FF00FF`: the script removes it, keeps edges clean and
  turns glows into soft transparency. A glow never leads into a lilac, purple, blue or green
  part, a shadow never into a pink one, and a colour edge always stops it. One case no
  program can decide: a pink part that touches a glow of the same colour. So when glows were
  found on magenta the script says so and writes a before/after picture to
  `ArtDrop/preview/keyed_<name>.png`. Look at it once.
- **Cuts the four sprite sheets** (`sheet_toys`, `sheet_modes`, `sheet_features`,
  `sheet_genres`) into single items. It finds the separate islands of pixels, joins loose
  parts that belong together, orders the items row by row, and refuses the sheet when the
  count or the layout is wrong, when an item is larger than a grid cell (two items joined)
  or when an extra item sits between two others. It cannot read what an item *is*, so it
  writes `ArtDrop/preview/cut_<sheet>.png`, a numbered and named picture of the cuts: check
  count and order with one look. On the toys sheet a red/yellow swap is caught by colour.
- **Writes web sizes**, with fixed names and pixel sizes, so the only thing that changes in the
  HTML is the cache stamp (`python tools/stamp_assets.py`):

| Kind | Files | Used for |
| --- | --- | --- |
| Small cut-out (toys, icons, logo, footer mascot) | `NAME.webp`, `NAME@2x.webp`, `NAME.png` at its real slot size | `<picture>` with a 1x/2x `srcset` |
| Large cut-out (mascots, comet trail) | `NAME-WIDTH.webp` (200/400/800, trail 600/1200/2400), `NAME.png` | `<picture>` with width `srcset` + `sizes`: a phone never downloads the desktop file |
| Scene (hero, sky, game cards, workshop) | `NAME-WIDTH.webp`, `NAME-WIDTH.jpg` | `<picture>` with width `srcset` + `sizes` |
| Screenshot | `NAME.webp`, `NAME@2x.webp`, `NAME.jpg` (360×640 at 1x) | Phone frames; the lightbox opens `@2x` and falls back to the `.jpg` |

- **Stands in for what has not arrived.** A missing or refused file gets a clearly labelled
  PLACEHOLDER of the right size, so the layout can be judged before the art is done.
  Run the script again when new files arrive: real art simply replaces its placeholder.
- **Builds the share image.** Once `hero_desktop.png` is real it rebuilds
  `assets/img/og-image.jpg` (1200×630) from the hero art plus the studio name. Until then
  the old image stays and counts as a placeholder.
- **Never stops half-way.** One bad, huge or locked file is noted and the run goes on. The
  script exits with 1 when anything was refused.

`tools/art-manifest.json` (committed) lists every source as `real`, `placeholder` or
`rejected`, with a checksum of every file written and no free text. The notes of the last
run are in `ArtDrop/import-log.json`, which is never published.

```bash
python tools/import_art.py --check
```

changes nothing and exits with an error unless every source is real art **and** every
picture in `assets/` is byte for byte the file the last complete run wrote. It also fails
after a run that was stopped or crashed, and when the manifest was edited by hand.
Run it before every push.

Every image in the pages has explicit `width`/`height`. Everything below the first screen,
and every decorative loose toy, is `loading="lazy"`.

---

## Fonts

Two fonts, both self-hosted in `assets/fonts/` with their licence files. The site makes
no third-party request of any kind.

| Font | Files | Used for | Licence | From |
| --- | --- | --- | --- | --- |
| Lilita One | `LilitaOne-Regular.woff` (15 KB), `.ttf` fallback | Headings, buttons | SIL OFL 1.1 (`LilitaOne-OFL.txt`) | The game's own UI font, copied unchanged from the Dice Duo Unity project (`Assets/_DiceBack/Art/Fonts/`) |
| Nunito Bold | `Nunito-Bold.woff` (59 KB), `.ttf` fallback | Labels, navigation, captions | SIL OFL 1.1 (`Nunito-OFL.txt`) | Same place |

The `.woff` files are made by `python tools/make_woff.py`: the same fonts, every table
unchanged, only compressed (WOFF 1.0, plain zlib, no extra software). Nothing is subset or
renamed, so the licences are untouched. Both are preloaded in every page's `<head>`.
WOFF2 would be about a fifth smaller again but needs `fonttools` and `brotli`.

Body text uses the visitor's system font. (Nunito Regular for body text would look more
of a piece; it needs two more font files from the same OFL family, which are not in the
repo yet.) `account-deletion.html` uses system fonts for everything (class `sysfont` on
`<html>`) under a strict Content-Security-Policy; that policy allows the site's own font
files (`font-src 'self'`) only so Chrome does not log an error for the `@font-face` rules
it never uses there.

---

## Editing content

Everything is hand-written HTML — open the page and edit the copy. Shared pieces:

- **Header and footer** are duplicated verbatim in every page. Change one, change all of them.
  Only the `is-active` / `aria-current="page"` marker differs per page.
- **Icons are never emoji.** Step numbers are the CSS die (`<span class="die die--3">`),
  "we will not" marks are the CSS cross (`<span class="cross">`), everything else is art.
- **Buttons, one colour rule.** Green (`btn--primary`) is the page's main action (the game's Roll
  button). Comet violet (`btn--comet`) is contact and partnership only: the Contact button in the
  menu, "Talk publishing", "Get in touch". Glass (`btn--ghost`) is the second choice.
- **Accent colours** come from the mascot and live in `:root`: `--comet` `#8C3CFA` (fills, glows),
  `--comet-deep` `#561BA5`, `--comet-night` `#2E0755`, `--lilac` `#C9A6FF` (accent words, eyebrows,
  links: 5.9:1 or more on every surface), `--lava` `#FA2E4B` with `--lava-core` `#FBDF97` (lines,
  dividers and glows only, never small text), `--lime` `#B7F26A` (focus rings and small sparks).
  `--yellow` is now only a toy colour.
- **Logo and icons.** The mark beside the wordmark is a cut of the mascot's head with the start of
  its trail. `python tools/make_brand.py` rebuilds it and every favicon / app icon from
  `ArtDrop/incoming/mascot_hero.png`; run it before `tools/import_art.py` (the share image uses the
  mark), then `tools/stamp_assets.py`.
- **Words on pictures.** The art brief keeps the left 55% of the home hero and the right 50%
  of the About banner calm; `css/style.css` (section 10) keeps the text inside those halves at
  every width, and below 1024px (About: 1100px) text and picture are separate blocks. If a
  text column is made wider, change the brief and the picture too.
- **If `js/main.js` does not load**, the one inline line in each `<head>` takes the `js` class
  away again after the page has loaded, so nothing stays hidden. If that line is edited, put
  its new SHA-256 into the Content-Security-Policy of `account-deletion.html`.
- **Wording.** The product is "Dice Duo"; "DiceBack" is one of its five games. Game rules on
  the Dice Duo page follow the in-game how-to-play text: change them there first.
- **Design tokens** (colors, radii, shadows, spacing) live in `:root` at the top of `css/style.css`.
- **Contact form** currently opens the visitor's own email client via `mailto:`.
  `js/main.js` has a commented block showing how to swap in a Formspree or Web3Forms endpoint
  if you want real inbox delivery without a server.

---

## Email addresses used on the site

These need to exist (mailbox or forwarding) before launch:

| Address | Used for |
| --- | --- |
| `hello@bouncycomet.com` | General contact, footer |
| `partners@bouncycomet.com` | Business and publishing enquiries |
| `support@bouncycomet.com` | Player support |
| `privacy@bouncycomet.com` | Privacy requests, referenced in the Privacy Policy |
| `legal@bouncycomet.com` | Referenced in the Terms of Service |

---

## Outstanding

- Dice Duo's public account-deletion resource is
  <https://bouncycomet.com/account-deletion.html>. Its prominent request button opens
  an email to `privacy@bouncycomet.com`; it is support-assisted, not an automated form.
  Keep that inbox monitored, verify account ownership, and use the game server's
  existing admin deletion action. Do not ask for passwords or substitute direct SQL.
  The page describes the current retained match IDs, moderation records, logs and
  backups; disclosure alone does not resolve their retention-policy gaps.
- Privacy and terms were aligned on 1 October 2026 with the current Dice Duo
  account/gameplay flows, advertising SDKs, 13+ audience and verified deletion
  behaviour. Retention exceptions are disclosed truthfully. Finish bounded
  retention review, age/consent and user-content runtime controls before release;
  published words alone do not implement those controls.
- The in-game policy entry must remain available independently of ad/CMP state.
  Use `https://bouncycomet.com/privacy.html` in the server's audited config workflow
  and include the reliable fallback/menu fix in the final Android build.

- [ ] Five illustrations are still missing (`sheet_toys`, `sheet_features`, `sheet_genres`,
      `studio_workshop`, `trail_divider`); the brief now orders them in the purple-comet style.
- [ ] Paste `ArtDrop/GPT_PROMPT.md` into GPT (its first lines say what to attach), save the 17
      illustrations into `ArtDrop/incoming/`, run `python tools/import_art.py`, look at
      `ArtDrop/preview/cut_*.png`, and publish only when `python tools/import_art.py --check` passes
- [ ] `privacy.html` needs three sentences revised by the owner (legal wording is not touched
      by design work), plus its "Last updated" date:
      section 3 still says "Some pages load Google Fonts" (no page does: fonts are self-hosted);
      it names the app "Dice Duo: 2 Player Dice Games" while the site says "2 Player Board Games";
      its Scope lists DiceBack, Six Spots and Scoop Stack but not Grid War and Roll Race.
- [ ] Confirm the wording about coin entry fees (Dice Duo page: the note under "Four ways to
      start a match" and the FAQ "Is Dice Duo free?"): matches against the computer and online
      quick matches have a coin entry fee and pay coins to the winner; two players on one phone
      is always free. Private rooms are not mentioned because the server can switch their fee.
- [ ] Add the real Google Play link to `diceback.html`, `games.html` and `index.html` at launch,
      replacing the plain "Coming soon to Google Play" text
- [ ] Update the "Last updated" dates in `privacy.html` and `terms.html` when you change them

## Done

- [x] Site live at <https://bouncycomet.com> with a Let's Encrypt certificate
- [x] Enforce HTTPS is on - `http://` and both `www` forms 301 to `https://bouncycomet.com`
- [x] `hello@`, `partners@`, `support@`, `privacy@` and `legal@` created as free Workspace
      aliases on `studio@bouncycomet.com` - every address the site publishes now resolves
