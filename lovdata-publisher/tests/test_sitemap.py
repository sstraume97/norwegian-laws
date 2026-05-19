"""Tests for sitemap.py."""
from pathlib import Path

import pytest

from lovdata_publisher.sitemap import generate_sitemap, SITE_BASE


def test_generate_sitemap_writes_xml_and_robots(tmp_path):
    repo = tmp_path
    lover = repo / "lover"
    lover.mkdir()
    (lover / "lov-1998-07-17-56.md").write_text("---\nrefid: lov/...\n---\n", encoding="utf-8")

    historie = repo / "historie"
    historie.mkdir()
    (historie / "regnskapsloven.md").write_text("---\nrefid: lov/...\n---\n", encoding="utf-8")

    feeds = repo / "feeds"
    feeds.mkdir()
    (feeds / "lov-1998-07-17-56.xml").write_text("<feed/>", encoding="utf-8")

    site = repo / "_site"
    n = generate_sitemap(
        repo_root=str(repo),
        site_dir=str(site),
    )
    assert n > 0

    sitemap = site / "sitemap.xml"
    assert sitemap.exists()
    text = sitemap.read_text(encoding="utf-8")
    assert text.startswith('<?xml version="1.0"')
    assert "<urlset" in text
    # Core pages
    assert f"<loc>{SITE_BASE}/</loc>" in text
    assert f"<loc>{SITE_BASE}/feeds/</loc>" in text
    assert f"<loc>{SITE_BASE}/book/abonner.html</loc>" in text
    # Per-law page
    assert f"<loc>{SITE_BASE}/lover/lov-1998-07-17-56.html</loc>" in text
    # Historie page
    assert f"<loc>{SITE_BASE}/historie/regnskapsloven.html</loc>" in text
    # Feed file
    assert f"<loc>{SITE_BASE}/feeds/lov-1998-07-17-56.xml</loc>" in text

    robots = site / "robots.txt"
    assert robots.exists()
    assert "User-agent: *" in robots.read_text()
    assert "Sitemap:" in robots.read_text()


def test_generate_sitemap_handles_missing_dirs(tmp_path):
    """Should not crash when lover/, historie/, etc. don't exist."""
    site = tmp_path / "_site"
    n = generate_sitemap(repo_root=str(tmp_path), site_dir=str(site))
    # Still writes core pages
    assert n >= 7
    sitemap = site / "sitemap.xml"
    assert sitemap.exists()


def test_sitemap_is_valid_xml(tmp_path):
    """Sitemap must parse as XML."""
    import xml.etree.ElementTree as ET
    site = tmp_path / "_site"
    generate_sitemap(repo_root=str(tmp_path), site_dir=str(site))
    tree = ET.parse(site / "sitemap.xml")
    root = tree.getroot()
    assert root.tag.endswith("urlset")
