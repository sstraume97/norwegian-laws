"""Generate an XML sitemap for the deployed site.

Lists every per-law page, historie page, feed, and core navigation page so
search engines can index the entire corpus. Without a sitemap, only a few
top-level pages get crawled and the 4,200+ law pages stay invisible to
Google searches.

The sitemap goes to `_site/sitemap.xml` and is referenced from `robots.txt`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

SITE_BASE = "https://sondreskarsten.github.io/norwegian-laws"


def generate_sitemap(
    repo_root: str = ".",
    site_dir: str = "_site",
    lover_dir: str = "lover",
    forskrifter_dir: str = "forskrifter",
    historie_dir: str = "historie",
    feeds_dir: str = "feeds",
) -> int:
    """Generate sitemap.xml + robots.txt. Returns number of URLs."""
    root = Path(repo_root)
    out_site = Path(site_dir)
    out_site.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = []

    def add(loc: str, priority: float = 0.5, changefreq: str = "weekly"):
        urls.append((loc, today, changefreq, priority))

    # Core landing pages — highest priority
    add(f"{SITE_BASE}/", 1.0, "weekly")
    add(f"{SITE_BASE}/feeds/", 0.9, "weekly")
    add(f"{SITE_BASE}/book/abonner.html", 0.9, "monthly")
    add(f"{SITE_BASE}/book/sok.html", 0.8, "monthly")
    add(f"{SITE_BASE}/book/diff.html", 0.8, "monthly")
    add(f"{SITE_BASE}/book/about.html", 0.6, "monthly")
    add(f"{SITE_BASE}/book/versjoner.html", 0.6, "monthly")

    # Per-law HTML pages
    for d, prefix in [(lover_dir, "lover"), (forskrifter_dir, "forskrifter")]:
        src = root / d
        if not src.is_dir():
            continue
        for md_file in sorted(src.glob("*.md")):
            add(f"{SITE_BASE}/{prefix}/{md_file.stem}.html", 0.7, "weekly")

    # Historie pages
    h_src = root / historie_dir
    if h_src.is_dir():
        for md_file in sorted(h_src.glob("*.md")):
            add(f"{SITE_BASE}/historie/{md_file.stem}.html", 0.5, "weekly")

    # Per-law Atom feeds (not really "pages" but Google indexes them as links)
    f_src = root / feeds_dir
    if f_src.is_dir():
        for xml_file in sorted(f_src.glob("*.xml")):
            add(f"{SITE_BASE}/feeds/{xml_file.name}", 0.4, "weekly")

    # Write sitemap.xml
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, lastmod, changefreq, priority in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{changefreq}</changefreq>")
        lines.append(f"    <priority>{priority:.1f}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")

    sitemap_path = out_site / "sitemap.xml"
    sitemap_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Wrote sitemap.xml with {len(urls)} URLs")

    # Write robots.txt
    robots_path = out_site / "robots.txt"
    robots_path.write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE}/sitemap.xml\n",
        encoding="utf-8",
    )
    print(f"  Wrote robots.txt")

    return len(urls)


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    site = sys.argv[2] if len(sys.argv) > 2 else "_site"
    generate_sitemap(repo_root=root, site_dir=site)
