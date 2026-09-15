#!/usr/bin/env python3
"""Build djouher.com into ./dist from site.json.

Usage:  python3 build.py            (GitHub Pages output: CNAME + .nojekyll)
        python3 build.py --apache   (also writes .htaccess for Apache/LiteSpeed hosting)

New release: edit the "release" block in site.json (title, slug, type, date,
links, image.source = URL of the official square cover). On the next build the
cover is downloaded once and saved as img/<slug>-{640,1200}.{webp,jpg}.
On GitHub, pushing to main rebuilds and redeploys automatically.
Requires Python 3.9+ and Pillow (pip install pillow).
"""
import base64, datetime as dt, hashlib, html, io, json, pathlib, shutil, sys, urllib.request

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "dist"
S = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
A, R, D = S["artist"], S["release"], S["domain"].rstrip("/")
e = lambda s: html.escape(s, quote=True)
date = dt.date.fromisoformat(R["date"])
img = "/" + R["image"]["base"]
TODAY = dt.date.today().isoformat()

TITLE = f"{A['name']} – Official Website · {R['title']}"
DESC = (f"Official website of {A['name']}, North African indie-pop singer from Kabylie. "
        f"Listen to the {R['type'].lower()} “{R['title']}” on Spotify, Apple Music, YouTube and Deezer.")

CSS = """
@font-face{font-family:"Bebas Neue";src:url(/fonts/bebas-neue.woff2) format("woff2");font-display:swap}
:root{--bg:#000;--fg:#f2eee8;--muted:#a29d96;--line:rgba(242,238,232,.18);--accent:#e5483d;--d:"Bebas Neue",Impact,"Arial Narrow",sans-serif;--pad:clamp(1rem,4vw,2.5rem);color-scheme:dark}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);font:400 1rem/1.6 "Helvetica Neue",Helvetica,Arial,system-ui,sans-serif;-webkit-font-smoothing:antialiased;padding-bottom:3.5rem}
a{color:inherit}
a:focus-visible{outline:2px solid var(--fg);outline-offset:4px}
img{display:block;max-width:100%;height:auto}
h1,h2{margin:0;font-family:var(--d);font-weight:400;text-transform:uppercase;line-height:.86}
ul{list-style:none;margin:0;padding:0}
em{font:italic 400 1.0625rem/1.2 Georgia,"Times New Roman",serif;color:var(--accent);letter-spacing:0;text-transform:none}
.up{font-size:.6875rem;letter-spacing:.22em;text-transform:uppercase}
.skip{position:absolute;left:var(--pad);top:-4rem;z-index:9;background:var(--fg);color:var(--bg);padding:.6rem 1rem}
.skip:focus{top:1rem}
.top{position:absolute;inset:0 0 auto;z-index:2;display:flex;justify-content:space-between;align-items:center;padding:1.25rem var(--pad)}
.brand{display:none;font:400 1.625rem/1 var(--d);letter-spacing:.14em;text-decoration:none;text-transform:uppercase}
.top nav{display:flex;justify-content:space-between;flex:1;gap:1rem}
.top nav a,.bar a{text-decoration:none;padding:.5rem 0}
.top nav a:hover,.bar a:hover{color:var(--accent)}
.hero{position:relative;min-height:calc(100vh - 3.5rem);min-height:calc(100svh - 3.5rem);display:flex;align-items:flex-end;overflow:hidden;background:#03060c}
.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:var(--pos,50% 50%)}
.hero::after{content:"";position:absolute;inset:0;background:linear-gradient(to top,#000 0,rgba(0,0,0,.72) 24%,rgba(0,0,0,0) 55%)}
.hero-in{position:relative;z-index:1;width:100%;padding:0 var(--pad) clamp(2rem,6vh,4rem);text-align:center}
.hero h1{font-size:clamp(5.5rem,34.5vw,34rem);letter-spacing:.01em;margin:0 -.02em}
.cta{margin:clamp(1rem,3vh,1.75rem) 0 0;display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:.75rem 1.5rem}
.btn{display:inline-flex;align-items:center;gap:.75em;min-height:2.875rem;padding:0 1.4rem;border:1px solid var(--fg);text-decoration:none;transition:background .2s,color .2s}
.btn:hover{background:var(--fg);color:var(--bg)}
.sec{max-width:84rem;margin:0 auto;padding:clamp(4.5rem,12vw,9rem) var(--pad) 0}
.release{display:grid;gap:clamp(2rem,5vw,4.5rem)}
.cover{width:100%;aspect-ratio:1;background:#0b1a30}
.title{font-size:clamp(4rem,13vw,9.5rem);margin:.35rem 0 0}
.meta{margin:1rem 0 2.25rem;color:var(--muted)}
.listen{border-top:1px solid var(--line)}
.listen a{display:flex;justify-content:space-between;align-items:center;gap:1rem;min-height:4rem;border-bottom:1px solid var(--line);text-decoration:none}
.pf{font:400 clamp(1.75rem,4vw,2.375rem)/1 var(--d);letter-spacing:.03em;text-transform:uppercase;transition:color .2s}
.act{color:var(--muted);white-space:nowrap}
.listen a:hover .pf{color:var(--accent)}
.listen a:hover .act{color:var(--fg)}
.about{display:grid;gap:1.5rem}
.about h2,.foot h2{font-size:clamp(3rem,9vw,6.5rem)}
.about p{margin:0;max-width:34em;font-size:clamp(1.125rem,2.1vw,1.5rem);line-height:1.5;color:#dcd8d1}
cite{font-style:italic}
.foot{padding-bottom:3rem;display:grid;gap:3rem}
.follow{display:flex;flex-wrap:wrap;gap:.25rem 1.75rem;margin-top:1.25rem}
.follow a{font:400 clamp(1.75rem,4vw,2.5rem)/1.3 var(--d);letter-spacing:.03em;text-transform:uppercase;text-decoration:none}
.follow a:hover{color:var(--accent)}
.mail{display:inline-block;margin-top:1.25rem;font-size:clamp(1.125rem,2.4vw,1.5rem);text-underline-offset:.3em;text-decoration-thickness:1px}
.legal{grid-column:1/-1;margin:0;padding-top:2rem;border-top:1px solid var(--line);color:var(--muted)}
.bar{position:fixed;inset:auto 0 0;z-index:5;display:flex;align-items:center;gap:1rem;min-height:3.5rem;padding:0 var(--pad);background:#000;border-top:1px solid var(--line)}
.bar b{font-weight:400;display:flex;align-items:center;gap:.6rem}
.bar b::before{content:"";width:.5rem;height:.5rem;border-radius:50%;background:var(--accent)}
.bar i{font-style:normal;color:var(--muted);display:none}
.bar span{margin-left:auto;display:flex;gap:1.25rem}
.nf{min-height:100svh;display:grid;place-content:center;gap:1.5rem;text-align:center;padding:var(--pad)}
.nf h1{font-size:clamp(4rem,14vw,10rem)}
.brand.on{display:block}
.sr{position:absolute;width:1px;height:1px;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
@media (min-width:40rem){.brand{display:block}.top nav{flex:none;gap:clamp(1.5rem,3vw,2.75rem)}.bar i{display:inline}}
@media (min-width:60rem){.release{grid-template-columns:minmax(0,1fr) minmax(0,1fr);align-items:end}.about,.foot{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.about p{padding-top:.6rem}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
""".strip()
CSS = "".join(line.strip() for line in CSS.splitlines()).replace("var(--pos,50% 50%)", S["hero"].get("position", "50% 50%"))
CSS_HASH = base64.b64encode(hashlib.sha256(CSS.encode()).digest()).decode()
CSP = f"default-src 'none'; connect-src 'self'; img-src 'self'; font-src 'self'; style-src 'sha256-{CSS_HASH}'; base-uri 'none'; form-action 'none'"


def jsonld():
    artist_id, rel_id = f"{D}/#artist", f"{D}/#{R['slug']}"
    same = [p["url"] for p in A["profiles"]] + A.get("sameAsExtra", [])
    graph = [
        {"@type": "WebSite", "@id": f"{D}/#website", "url": f"{D}/", "name": A["name"],
         "inLanguage": "en", "publisher": {"@id": artist_id}},
        {"@type": "ProfilePage", "@id": f"{D}/#webpage", "url": f"{D}/", "name": TITLE,
         "description": DESC, "inLanguage": "en", "isPartOf": {"@id": f"{D}/#website"},
         "mainEntity": {"@id": artist_id}, "primaryImageOfPage": f"{D}{img}-1200.jpg",
         "dateModified": TODAY},
        {"@type": "MusicGroup", "@id": artist_id, "name": A["name"], "url": f"{D}/",
         "description": A["description"], "genre": A["genre"], "image": f"{D}{img}-1200.jpg",
         "email": A["contact"], "sameAs": same, "album": {"@id": rel_id}},
        {"@type": "MusicAlbum", "@id": rel_id, "name": R["title"],
         "albumReleaseType": f"https://schema.org/{R['type']}Release",
         "byArtist": {"@id": artist_id}, "datePublished": R["date"],
         "image": f"{D}{img}-1200.jpg", "url": f"{D}/#{R['slug']}",
         "sameAs": [l["url"] for l in R["links"] if "watch?v=" not in l["url"]],
         "numTracks": 1 if R["type"] == "Single" else None,
         "track": {"@type": "MusicRecording", "name": R["title"], "duration": R.get("duration"),
                   "byArtist": {"@id": artist_id}, "inAlbum": {"@id": rel_id}}},
    ]
    clean = lambda o: {k: v for k, v in o.items() if v is not None}
    graph = [clean(g) for g in graph]
    return json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, separators=(",", ":"))


def head(title, desc, canonical=True, robots="index,follow,max-image-preview:large", preload=""):
    og = f"{D}{img}-1200.jpg"
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>{e(title)}</title>",
        f'<meta name="description" content="{e(desc)}">',
        f'<meta name="robots" content="{robots}">',
        f'<meta http-equiv="Content-Security-Policy" content="{CSP}">',
        '<meta name="referrer" content="strict-origin-when-cross-origin">',
    ]
    if canonical:
        parts += [
            f'<link rel="canonical" href="{D}/">',
            '<meta property="og:type" content="website">',
            f'<meta property="og:site_name" content="{e(A["name"])}">',
            f'<meta property="og:title" content="{e(title)}">',
            f'<meta property="og:description" content="{e(desc)}">',
            f'<meta property="og:url" content="{D}/">',
            f'<meta property="og:image" content="{og}">',
            '<meta property="og:image:type" content="image/jpeg">',
            '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="1200">',
            f'<meta property="og:image:alt" content="{e(R["image"]["alt"])}">',
            '<meta property="og:locale" content="en_US">',
            '<meta name="twitter:card" content="summary_large_image">',
        ]
    parts += [
        '<meta name="theme-color" content="#000000">',
        '<link rel="icon" href="/favicon.ico" sizes="32x32">',
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
        '<link rel="preload" href="/fonts/bebas-neue.woff2" as="font" type="font/woff2" crossorigin>',
        preload,
        f"<style>{CSS}</style>",
    ]
    return "".join(parts)


def index():
    H = S["hero"]
    hero = "/" + H["image"]
    title = e(R["title"])
    links = "".join(
        f'<li><a href="{e(l["url"])}"><span class="pf">{e(l["name"])}</span>'
        f'<span class="act up">{e(l.get("action") or ("Watch" if "watch?v=" in l["url"] else "Listen"))}<span class="sr"> to {title} on {e(l["name"])}</span> ↗</span></a></li>'
        for l in R["links"])
    follow = "".join(f'<li><a href="{e(p["url"])}" rel="me">{e(p["name"])}</a></li>' for p in A["profiles"])
    first = R["links"][0]
    apple = next((l for l in R["links"] if l["name"] == "Apple Music"), None)
    bar_links = f'<a href="{e(first["url"])}">{e(first["name"])}</a>' + (f'<a href="{e(apple["url"])}">Apple Music</a>' if apple else "")
    preload = (f'<link rel="preload" as="image" type="image/webp" imagesrcset="{hero}-800.webp 800w, {hero}-1400.webp 1400w" '
               'imagesizes="100vw" fetchpriority="high">')
    year = max(date.year, dt.date.today().year)
    return (
        head(TITLE, DESC, preload=preload)
        + f'<script type="application/ld+json">{jsonld()}</script></head><body>'
        + '<a class="skip up" href="#listen">Skip to the latest release</a>'
        + f'<header class="top"><a class="brand" href="/">{e(A["name"])}</a>'
        + '<nav class="up" aria-label="Sections"><a href="#listen">Listen</a><a href="#about">About</a><a href="#follow">Follow</a><a href="#contact">Contact</a></nav></header>'
        + '<main>'
        + f'<section class="hero" aria-labelledby="name">'
        + f'<img src="{hero}-800.webp" srcset="{hero}-800.webp 800w, {hero}-1400.webp 1400w" sizes="100vw" width="1400" height="1400" alt="{e(H["alt"])}" fetchpriority="high">'
        + '<div class="hero-in">'
        + f'<h1 id="name">{e(A["name"])}</h1>'
        + f'<p class="cta"><em>New {e(R["type"].lower())}</em><a class="btn up" href="#listen">Listen to {title}</a></p>'
        + '</div></section>'
        + f'<section class="sec release" id="listen" aria-labelledby="release-title">'
        + '<picture>'
        + f'<source type="image/webp" srcset="{img}-640.webp 640w, {img}-1200.webp 1200w" sizes="(min-width:60rem) 42rem, calc(100vw - 2rem)">'
        + f'<img class="cover" src="{img}-640.jpg" width="640" height="640" alt="{e(R["image"]["alt"])}" loading="lazy" decoding="async">'
        + '</picture>'
        + '<div class="info">'
        + '<p class="up"><em>Latest release</em></p>'
        + f'<h2 class="title" id="release-title">{title}</h2>'
        + f'<p class="meta up">{e(R["type"])} · <time datetime="{R["date"]}">{date.day} {date.strftime("%B %Y")}</time></p>'
        + f'<ul class="listen" aria-label="Listen to {title}">{links}</ul>'
        + '</div></section>'
        + f'<section class="sec about" id="about" aria-labelledby="about-h"><h2 id="about-h">About</h2><p>{A["bio"]}</p></section>'
        + '</main>'
        + '<footer class="sec foot">'
        + f'<nav id="follow" aria-labelledby="follow-h"><h2 id="follow-h">Follow</h2><ul class="follow">{follow}</ul></nav>'
        + f'<div id="contact"><h2>Contact</h2><a class="mail" href="mailto:{A["contact"]}">{A["contact"]}</a></div>'
        + f'<p class="legal up">© {year} {e(A["name"])} · Official website</p>'
        + '</footer>'
        + f'<aside class="bar up" aria-label="Listen now"><b>Listen now</b><i>{e(A["name"])} — {title}</i><span>{bar_links}</span></aside>'
        + '</body></html>\n'
    )


def notfound():
    return (head(f"Page not found – {A['name']}", "This page does not exist.", canonical=False, robots="noindex")
            + '</head><body>'
            + f'<header class="top"><a class="brand on" href="/">{e(A["name"])}</a></header>'
            + '<main class="nf"><p class="up"><em>Error 404</em></p><h1>Page not found</h1>'
            + f'<p><a class="btn up" href="/">Back to {e(A["name"])}</a></p></main></body></html>\n')


def htaccess():
    csp = CSP + "; frame-ancestors 'none'"
    return f"""# djouher.com – generated by build.py
Options -Indexes -MultiViews
DirectoryIndex index.html
ErrorDocument 404 /404.html

<IfModule mod_rewrite.c>
RewriteEngine On
# 1. One canonical origin: https://djouher.com (no www, HTTPS only)
RewriteCond %{{HTTPS}} !=on [OR]
RewriteCond %{{HTTP_HOST}} ^www\\. [NC]
RewriteRule ^ https://djouher.com%{{REQUEST_URI}} [R=301,L,NE]
# 2. /index.html -> /
RewriteCond %{{THE_REQUEST}} \\s/+index\\.html[\\s?] [NC]
RewriteRule ^index\\.html$ / [R=301,L]
</IfModule>

<IfModule mod_headers.c>
Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
Header always set X-Content-Type-Options "nosniff"
Header always set Referrer-Policy "strict-origin-when-cross-origin"
Header always set Permissions-Policy "camera=(), microphone=(), geolocation=(), interest-cohort=()"
Header always set X-Frame-Options "DENY"
Header always set Content-Security-Policy "{csp}"
<FilesMatch "\\.(html)$">
Header set Cache-Control "public, max-age=300, must-revalidate"
</FilesMatch>
<FilesMatch "\\.(webp|jpg|png|svg|ico|woff2)$">
Header set Cache-Control "public, max-age=31536000, immutable"
</FilesMatch>
</IfModule>

<IfModule mod_deflate.c>
AddOutputFilterByType DEFLATE text/html text/plain text/xml application/xml image/svg+xml
</IfModule>

AddType image/webp .webp
AddType image/svg+xml .svg
AddDefaultCharset utf-8
"""


def favicons():
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
           '<rect width="64" height="64" rx="12" fill="#000"/>'
           '<circle cx="32" cy="32" r="16" fill="#f2eee8"/></svg>\n')
    (DIST / "favicon.svg").write_text(svg)
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    def draw(size, rounded):
        s = 4 * size
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s * 12 // 64 if rounded else 0, fill="#000")
        r = s * 16 // 64
        d.ellipse([s // 2 - r, s // 2 - r, s // 2 + r, s // 2 + r], fill="#f2eee8")
        return im.resize((size, size), Image.LANCZOS)
    draw(32, True).save(DIST / "favicon.ico", sizes=[(32, 32)])
    draw(180, False).convert("RGB").save(DIST / "apple-touch-icon.png", optimize=True)


def ensure_images():
    """Create img/<slug>-{640,1200}.{webp,jpg} from image.source if missing."""
    base = ROOT / R["image"]["base"]
    wanted = [base.with_name(f"{base.name}-{w}.{x}") for w in (640, 1200) for x in ("webp", "jpg")]
    if all(f.exists() for f in wanted):
        return
    src = R["image"].get("source")
    if not src:
        sys.exit(f"Missing cover files for {R['slug']} and no image.source in site.json")
    from PIL import Image
    req = urllib.request.Request(src, headers={"User-Agent": "djouher.com build"})
    im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=60).read())).convert("RGB")
    side = min(im.size)
    im = im.crop(((im.width - side) // 2, (im.height - side) // 2, (im.width + side) // 2, (im.height + side) // 2))
    base.parent.mkdir(parents=True, exist_ok=True)
    for w in (640, 1200):
        r = im.resize((w, w), Image.LANCZOS)
        r.save(base.with_name(f"{base.name}-{w}.webp"), "WEBP", quality=80, method=6)
        r.save(base.with_name(f"{base.name}-{w}.jpg"), "JPEG", quality=82, optimize=True, progressive=True)
    print("cover images generated from", src)


FONT_URL = "https://cdn.jsdelivr.net/npm/@fontsource/bebas-neue@5.3.0/files/bebas-neue-latin-400-normal.woff2"


def ensure_assets():
    """Fetch the display font and derive the small hero image if they are missing."""
    font = ROOT / "fonts" / "bebas-neue.woff2"
    if not font.exists():
        font.parent.mkdir(exist_ok=True)
        req = urllib.request.Request(FONT_URL, headers={"User-Agent": "djouher.com build"})
        font.write_bytes(urllib.request.urlopen(req, timeout=60).read())
        print("font downloaded")
    hero = ROOT / S["hero"]["image"]
    big, small = hero.with_name(hero.name + "-1400.webp"), hero.with_name(hero.name + "-800.webp")
    if big.exists() and not small.exists():
        from PIL import Image
        Image.open(big).convert("RGB").resize((800, 800), Image.LANCZOS).save(small, "WEBP", quality=68, method=6)
        print("hero-800 generated")


def main():
    ensure_images()
    ensure_assets()
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    (DIST / "index.html").write_text(index(), encoding="utf-8")
    (DIST / "404.html").write_text(notfound(), encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {D}/sitemap.xml\n")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{D}/</loc><lastmod>{TODAY}</lastmod></url>\n</urlset>\n")
    if "--apache" in sys.argv:
        (DIST / ".htaccess").write_text(htaccess())
    else:
        (DIST / "CNAME").write_text(D.split("://")[1] + "\n")
        (DIST / ".nojekyll").write_text("")
    favicons()
    for d in ("img", "fonts"):
        if (ROOT / d).exists():
            shutil.copytree(ROOT / d, DIST / d)
    for f in sorted(DIST.rglob("*")):
        if f.is_file():
            print(f"{f.stat().st_size:>8}  {f.relative_to(DIST)}")


if __name__ == "__main__":
    main()
