from asteria.sitemap import SitemapEntry, render_sitemap


def test_render_sitemap_basic():
    entries = [
        SitemapEntry(path="/sobre/"),
        SitemapEntry(path="/blog/artigo/", lastmod="2026-01-01"),
    ]
    xml = render_sitemap(entries, "https://example.com")

    assert "<?xml" in xml
    assert "<loc>https://example.com/sobre/</loc>" in xml
    assert "<loc>https://example.com/blog/artigo/</loc>" in xml
    assert "<lastmod>2026-01-01</lastmod>" in xml


def test_render_sitemap_strips_trailing_slash_from_site_url():
    entries = [SitemapEntry(path="/x/")]
    xml = render_sitemap(entries, "https://example.com/")
    assert "<loc>https://example.com/x/</loc>" in xml
    assert "https://example.com//x/" not in xml
