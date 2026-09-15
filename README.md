# djouher.com

Official website of Djouher. One static page, no framework, no tracking.

## Update the latest release

1. Edit the `release` block in `site.json`: `title`, `slug`, `type`, `date`,
   `duration`, `image.source` (URL of the official square cover), `image.alt`
   and the streaming `links`.
2. Commit to `main`. GitHub Actions runs `build.py`, saves the cover in
   `img/` and redeploys https://djouher.com within a minute or two.

Artist bio, profiles and contact live in the `artist` block of `site.json`.

## Design assets

- `img/hero-*.webp`: hero photo (I Killed Her shoot). Replace both files to change it; alt text and crop position are in `site.json` → `hero`.
- `fonts/bebas-neue.woff2`: Bebas Neue (SIL Open Font License), Latin subset, self-hosted.

## Local build

```
pip install pillow
python3 build.py            # output in dist/ (GitHub Pages)
python3 build.py --apache   # adds .htaccess for Apache/LiteSpeed hosting
```

## Hosting

GitHub Pages (free) with the custom domain `djouher.com`.
DNS stays at Hostinger: four `A` records for `@` (185.199.108.153,
185.199.109.153, 185.199.110.153, 185.199.111.153) and a `CNAME` for `www`
pointing to `djouher-cell.github.io`. Email records are untouched.
