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
git add -A
git commit -m "Update site"
git push
```

Live in roughly 60 seconds. That is the whole workflow.

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

## Email address used on the site

Every contact route on the site points at one mailbox:

| Address | Used for |
| --- | --- |
| `studio@bouncycomet.com` | Everything: general, business and publishing, player support, press, privacy requests and legal notices |

This is the only mailbox that exists on the domain (Google Workspace). The contact form,
the footer, the contact cards, the Privacy Policy and the Terms of Service all use it.

If you later add branded aliases in Google Workspace (Users -> the studio user ->
**Add Alternate Emails** - aliases are free, new users are not), the site can be switched
back to `hello@` / `partners@` / `support@` / `privacy@` / `legal@` in a single commit.

--- | --- |
| `studio@bouncycomet.com` | General contact, footer |
| `studio@bouncycomet.com` | Business and publishing enquiries |
| `studio@bouncycomet.com` | Player support |
| `studio@bouncycomet.com` | Privacy requests, referenced in the Privacy Policy |
| `studio@bouncycomet.com` | Referenced in the Terms of Service |

---

## Before you call it done

- [ ] Create the six aliases above in Google Workspace (admin.google.com -> Users -> Aliases)
- [ ] Add real App Store / Google Play links to `diceback.html` and `games.html` at launch,
      replacing the disabled "Coming Soon" buttons
- [ ] Update the "Last updated" dates in `privacy.html` and `terms.html` when you change them
