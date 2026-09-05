from pathlib import Path

from asteria.config import load_config
from asteria.templating import make_site_view


def test_site_view_has_only_fixed_ssg_config(tmp_path: Path):
    """SiteView agora é só o namespace fixo do SSG — menu/nav/social/extra
    migraram pro namespace do tema (theme.yaml)."""
    (tmp_path / "site.yaml").write_text(
        "site:\n  title: T\n  url: https://x.example\n", encoding="utf-8"
    )
    config = load_config(tmp_path / "site.yaml")
    site_view = make_site_view(config, feed_url="/rss.xml")

    assert site_view.title == "T"
    assert site_view.url == "https://x.example"
    assert site_view.feed_url == "/rss.xml"
    for attr in ("menu", "nav", "social", "extra", "sidebar_toc"):
        assert not hasattr(site_view, attr)
