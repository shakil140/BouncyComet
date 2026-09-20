# Bouncy Comet — bouncycomet.com

Marketing site for **Bouncy Comet**, an independent mobile game studio making
puzzle, hypercasual, arcade, hybrid-casual, multiplayer and kids' games.

First title in development: **DiceBack — 2 Player Dice Game**.

---

## Stack

Plain static HTML, CSS and vanilla JavaScript. **No build step, no npm, no framework.**
What is in the repo is exactly what ships.

```
index.html        Home — studio pitch, genres, featured game
games.html        Portfolio — DiceBack + prototype directions
diceback.html     DiceBack deep-dive — rules, modes, features, 15 screenshots, FAQ
about.html        Studio story, how we work, principles
contact.html      Contact routes + form
privacy.html      Privacy Policy (app-store ready)
terms.html        Terms of Service
404.html          Not-found page (uses root-absolute paths — see note below)

css/style.css     Full design system: tokens, components, responsive, reduced-motion
js/main.js        Nav, scroll reveal, screenshot lightbox, contact form

assets/img/       DiceBack screenshots (webp + jpg, 1x + 2x) and the OG image
assets/icons/     Favicons, apple-touch-icon, PWA icons

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

Hosted on **GitHub Pages**, served from the `main` branch, root folder.

- Repo: <https://github.com/shakil140/BouncyComet>
- Preview URL: <https://shakil140.github.io/BouncyComet/>
- Live URL: <https://bouncycomet.com>

### Step 0 - make the repo public

GitHub Pages only serves **public** repos on the free plan. This repo is currently private,
so Pages cannot be turned on yet.

**Settings -> General -> scroll to Danger Zone -> Change repository visibility -> Make public.**

(Nothing secret is in here: it is a marketing site. If you would rather keep it private you
need GitHub Pro, or deploy to Cloudflare Pages / Netlify instead, which serve private repos
on their free tiers.)

### First push

```bash
git add -A
git commit -m "Launch Bouncy Comet website"
git push -u origin main
```

Then in the repo: **Settings -> Pages -> Build and deployment -> Source: Deploy from a branch**,
branch `main`, folder `/ (root)`. The `CNAME` file already in the repo sets the custom domain
to `bouncycomet.com` automatically. Tick **Enforce HTTPS** once the certificate is issued
(takes a few minutes after DNS resolves).

### DNS at Squarespace

`bouncycomet.com` uses Squarespace nameservers. Add these records in
**Squarespace -> Domains -> bouncycomet.com -> DNS Settings**:

| Type | Host | Value |
| --- | --- | --- |
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `shakil140.github.io` |

Remove any existing A or CNAME record on `@` or `www` that points at Squarespace's own
site builder, or it will fight these.

### Every later update

```bash
git add -A
git commit -m "Update site"
git push
```

Live in roughly 60 seconds.

### Path convention — important

Every page uses **relative** asset paths (`css/style.css`, `assets/img/…`) **except `404.html`**,
which uses **root-absolute** paths (`/css/style.css`). This is deliberate: a 404 can be served
from any URL depth, so relative paths there would break.

---

## Images

Screenshots are generated from the Unity screen designs. To regenerate after adding
or replacing a screen, re-run the optimizer that produced them — each screen ships as:

| Variant | Size | Purpose |
| --- | --- | --- |
| `diceback-NAME.webp` | 540×959 | Primary, modern browsers |
| `diceback-NAME.jpg` | 540×959 | Fallback |
| `diceback-NAME@2x.webp` | 1080×1918 | Retina + lightbox |
| `diceback-NAME@2x.jpg` | 1080×1918 | Retina fallback |

All are served through `<picture>` with explicit `width`/`height` to avoid layout shift.

---

## Editing content

Everything is hand-written HTML — open the page and edit the copy. Shared pieces:

- **Header and footer** are duplicated verbatim in every page. Change one, change all of them.
  Only the `is-active` / `aria-current="page"` marker differs per page.
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

## Before you call it done

- [ ] Set up the five email addresses above (forwarding is fine)
- [ ] Fill in the governing-law jurisdiction placeholder in `terms.html`
- [ ] Add real App Store / Google Play links to `diceback.html` and `games.html` at launch,
      replacing the disabled "Coming Soon" buttons
- [ ] Update the "Last updated" dates in `privacy.html` and `terms.html` when you change them
