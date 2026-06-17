# REY. — Singapore DJ & VIP Table Access (project context)

This repo is the **live website** for **REY.**, a premium Singapore DJ portfolio.
It is served via **GitHub Pages** at `https://workarounds81.github.io/reyvvip/`.

This file exists so any new Claude Code session picks up full context automatically.

---

## What this site is

A single-page marketing/booking site covering two services:

1. **B2C — VIP shared-table access.** Customers book a spot at a VIP table on club
   nights. Includes a live **split calculator** (S$150 customer / S$60 host cost /
   S$90 net) and a **club-night calendar engine**.
2. **B2B — private event DJ + sound production.** A quote builder that assembles a
   WhatsApp message with the event details.

Genres: melodic techno, tech house, progressive.
Tagline: *"Curating Sound. Bypassing Restrictions."*

All bookings/quotes route to **WhatsApp** via `https://wa.me/<number>?text=<message>`.

---

## Architecture — IMPORTANT

This is a **pure static site. No build step. No framework. No npm install to run.**

- **`index.html`** is the entire app: static HTML content + inline `<style>` +
  vanilla JS in a `<script>` at the bottom (wrapped in `"use strict";`).
- It was deliberately rebuilt from an earlier React/Babel/Tailwind version into
  static HTML **for SEO** — all text (headings, club names, reviews, FAQ) lives in
  the markup so search engines can crawl it. **Do not reintroduce a JS framework or
  CDN runtime** unless explicitly asked; it would undo the SEO work.
- To preview locally: just open `index.html` in a browser, or
  `python3 -m http.server` in this folder.

### SEO assets (keep these in sync with index.html)
- `robots.txt`, `sitemap.xml`, `site.webmanifest`
- JSON-LD in `index.html` `<head>`: 4 nodes — WebSite, ProfessionalService,
  Person, FAQPage (7 Q&As). Keep FAQ JSON-LD in sync with the visible FAQ section.
- Open Graph + Twitter Card meta tags drive the WhatsApp/IG link preview.
- `og-image.png` (1200×630) is the share card; icons are `icon-192.png`,
  `icon-512.png`, `apple-touch-icon.png`, `favicon-32.png`.
- Canonical URL throughout is `https://workarounds81.github.io/reyvvip/`.
  If the site ever moves to a custom domain, update the canonical, OG `url`,
  OG `image`, sitemap `<loc>`, robots `Sitemap:`, and JSON-LD `url` fields.

---

## Config knobs (edit these in `index.html`)

| What | Line(s) | Current placeholder → set to |
|------|---------|------------------------------|
| WhatsApp number | ~978 (`var WA_NUMBER`) | `6581234567` → real SG number, country code, no `+` |
| Instagram URL | ~74 (JSON-LD), ~937 (footer link) | `https://instagram.com/` → real profile |
| SoundCloud URL | ~75 (JSON-LD), ~938 (footer link) | `https://soundcloud.com/` → real profile |
| Table economics | ~979 (`HOST_COST`), calc fns ~1055 | `HOST_COST=60`, customer rate 150 |
| Mix length (secs) | ~979 (`TOTAL_SECS`) | `3734` (≈62:14 demo player) |

`WA_NUMBER` is read in several places (footer CTAs, VIP booking, B2B quote builder,
mobile CTA) — change it once at the `var WA_NUMBER` declaration; everything else
references that variable.

### Calendar engine
Club nights = Wed/Thu/Fri/Sat. Public-holiday eves are hardcoded in the
`SG_PH_EVES` array (2026–2027). `parseLocal()` builds dates with
`new Date(y, m-1, d)` to avoid UTC day-shift bugs. Extend `SG_PH_EVES` yearly.

---

## Content / decisions made so far

- **Reviews are representative placeholders.** Owner confirmed this is fine for now
  (promotion is word-of-mouth + social). No star-rating review schema is in the
  JSON-LD (deliberate — avoids Google rich-result policy issues with unverifiable
  reviews). Swap in real testimonials when available.
- Mobile-first; layout is fully responsive (single-column on phones, grid on
  desktop). Most traffic is expected on mobile.

---

## Deploy (GitHub Pages)

Settings → Pages → Source: **Deploy from a branch** → Branch **main** → **/ (root)**
→ Save. Live within a minute or two at `https://workarounds81.github.io/reyvvip/`.
A 404 right after enabling = give it a moment / hard-refresh.

There is **no CI/build** — Pages serves the files as-is. Commit to `main` and it's live.

---

## How to make changes

1. Edit `index.html` (and matching SEO asset if you touch URLs/FAQ/branding).
2. If regenerating `og-image.png` or icons: source SVGs were rendered with the
   `sharp` npm package (OG at density 144 then `.resize(1200,630)`). Re-render at
   the same dimensions.
3. Commit + push to `main`. Pages redeploys automatically.
