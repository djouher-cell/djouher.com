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
:root{--bg:#070f1c;--fg:#ece9e2;--muted:#9aa3b3;--line:rgba(236,233,226,.16);color-scheme:dark}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:400 1rem/1.6 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:30rem;margin:0 auto;padding:clamp(2.5rem,8vw,5rem) 1.25rem 2.5rem}
a{color:inherit}
a:focus-visible{outline:2px solid var(--fg);outline-offset:4px;border-radius:2px}
h1{margin:0 0 clamp(2.5rem,8vw,4rem);font-size:clamp(2.25rem,12vw,3.75rem);font-weight:300;line-height:1;letter-spacing:.3em;text-transform:uppercase}
.label{margin:0 0 1rem;font-size:.75rem;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}
img{display:block;width:100%;height:auto;aspect-ratio:1;background:#0b1a30}
h2{margin:0;font-weight:400}
.title{margin-top:1.5rem;font-size:1.875rem;line-height:1.2;letter-spacing:-.01em}
.meta{margin:.25rem 0 0;color:var(--muted)}
ul{list-style:none;margin:0;padding:0}
.listen{margin-top:2rem;border-top:1px solid var(--line)}
.listen a{display:flex;justify-content:space-between;align-items:center;min-height:3.25rem;border-bottom:1px solid var(--line);text-decoration:none}
.listen a:hover{color:#fff}
.listen a:hover .go{transform:translate(2px,-2px)}
.go{color:var(--muted);transition:transform .15s}
.about{margin-top:clamp(3.5rem,10vw,5rem)}
.about h2,footer h2{margin:0 0 1rem;font-size:.75rem;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}
.about p{margin:0;color:#cfd3da}
cite{font-style:italic}
footer{margin-top:clamp(3.5rem,10vw,5rem);padding-top:2rem;border-top:1px solid var(--line);font-size:.9375rem}
.follow{display:flex;flex-wrap:wrap;gap:.25rem 1.25rem;margin-bottom:2rem}
.follow a,.contact a{display:inline-block;padding:.35rem 0;text-decoration-color:var(--line);text-underline-offset:.25em}
.follow a:hover,.contact a:hover{text-decoration-color:currentColor}
.contact{margin:0 0 2rem}
small{display:block;color:var(--muted);font-size:.8125rem}
.sr{position:absolute;width:1px;height:1px;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.brand{margin:0 0 2.5rem;font-size:1.25rem;font-weight:300;letter-spacing:.3em;text-transform:uppercase}
h1.title{margin:0 0 1rem;letter-spacing:-.01em;text-transform:none;font-weight:400}
@media (min-width:56rem){.wrap{max-width:64rem;padding-inline:2.5rem}.release{display:grid;grid-template-columns:minmax(0,28rem) minmax(0,1fr);column-gap:4rem}.release .label{grid-column:1/-1}.info{align-self:end}.info .title{margin-top:0}.about,footer{margin-left:32rem}}
@media (prefers-reduced-motion:reduce){.go{transition:none}}
""".strip()
CSS = "".join(line.strip() for line in CSS.splitlines())
CSS_HASH = base64.b64encode(hashlib.sha256(CSS.encode()).digest()).decode()
CSP = f"default-src 'none'; img-src 'self'; style-src 'sha256-{CSS_HASH}'; base-uri 'none'; form-action 'none'"


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


def head(title, desc, canonical=True, robots="index,follow,max-image-preview:large"):
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
        '<meta name="theme-color" content="#070f1c">',
        '<link rel="icon" href="/favicon.ico" sizes="32x32">',
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
        f"<style>{CSS}</style>",
    ]
    return "".join(parts)


def index():
    links = "".join(
        f'<li><a href="{e(l["url"])}">'
        f'<span><span class="sr">{e(l.get("label") or "Listen")} – {e(R["title"])} on </span>{e(l["name"])}</span>'
        f'<span class="go" aria-hidden="true">↗</span></a></li>'
        for l in R["links"])
    follow = "".join(f'<li><a href="{e(p["url"])}" rel="me">{e(p["name"])}</a></li>' for p in A["profiles"])
    return (
        head(TITLE, DESC)
        + f'<script type="application/ld+json">{jsonld()}</script></head><body><div class="wrap">'
        + f'<header><h1>{e(A["name"])}</h1></header>'
        + f'<main><section class="release" id="{R["slug"]}" aria-labelledby="release-title">'
        + f'<p class="label">Latest release</p>'
        + '<picture>'
        + f'<source type="image/webp" srcset="{img}-640.webp 640w, {img}-1200.webp 1200w" sizes="(min-width:32.5rem) 30rem, calc(100vw - 2.5rem)">'
        + f'<img src="{img}-640.jpg" width="640" height="640" alt="{e(R["image"]["alt"])}" fetchpriority="high">'
        + '</picture>'
        + '<div class="info">'
        + f'<h2 class="title" id="release-title">{e(R["title"])}</h2>'
        + f'<p class="meta">{e(R["type"])} · <time datetime="{R["date"]}">{date.day} {date.strftime("%B %Y")}</time></p>'
        + f'<ul class="listen" aria-label="Listen to {e(R["title"])}">{links}</ul>'
        + '</div></section>'
        + f'<section class="about" aria-labelledby="about"><h2 id="about">About</h2><p>{A["bio"]}</p></section>'
        + '</main>'
        + '<footer>'
        + f'<nav aria-labelledby="follow"><h2 id="follow">Follow {e(A["name"])}</h2><ul class="follow">{follow}</ul></nav>'
        + f'<h2>Contact</h2><p class="contact"><a href="mailto:{A["contact"]}">{A["contact"]}</a></p>'
        + f'<small>© {date.year if date.year > dt.date.today().year else dt.date.today().year} {e(A["name"])}. Official website.</small>'
        + '</footer></div></body></html>\n'
    )


def notfound():
    return (head(f"Page not found – {A['name']}", "This page does not exist.", canonical=False, robots="noindex")
            + f'</head><body><div class="wrap"><header><p class="brand"><a href="/">{e(A["name"])}</a></p></header>'
            + '<main><h1 class="title">Page not found</h1>'
            + f'<p><a href="/">Go to the official website of {e(A["name"])}</a></p></main></div></body></html>\n')


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
<FilesMatch "\\.(webp|jpg|png|svg|ico)$">
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
           '<rect width="64" height="64" rx="12" fill="#070f1c"/>'
           '<circle cx="32" cy="32" r="16" fill="#ece9e2"/></svg>\n')
    (DIST / "favicon.svg").write_text(svg)
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    def draw(size, rounded):
        s = 4 * size
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s * 12 // 64 if rounded else 0, fill="#070f1c")
        r = s * 16 // 64
        d.ellipse([s // 2 - r, s // 2 - r, s // 2 + r, s // 2 + r], fill="#ece9e2")
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


def main():
    ensure_images()
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
    if (ROOT / "img").exists():
        shutil.copytree(ROOT / "img", DIST / "img")
    for f in sorted(DIST.rglob("*")):
        if f.is_file():
            print(f"{f.stat().st_size:>8}  {f.relative_to(DIST)}")


if __name__ == "__main__":
    main()
