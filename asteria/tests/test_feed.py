from pathlib import Path

from asteria.config import load_config
from asteria.document import Post
from asteria.feed import render_atom, render_rss
from asteria.frontmatter import Frontmatter


def _post(n: int, date: str) -> Post:
    post = Post(
        id=f"post-{n}",
        kind="post",
        source_path=Path(f"post-{n}.odt"),
        frontmatter=Frontmatter(title=f"Post {n}", date=date, description="Resumo."),
        content_html="<p>Conteúdo</p>",
        raw_content_html="",
    )
    post.url = f"/blog/post-{n}/"
    return post


def _config(tmp_path: Path):
    (tmp_path / "site.yaml").write_text(
        "site:\n  title: Meu Site\n  url: https://example.com\n", encoding="utf-8"
    )
    return load_config(tmp_path / "site.yaml")


def test_render_rss_contains_items(tmp_path: Path):
    config = _config(tmp_path)
    posts = [_post(1, "2026-01-01"), _post(2, "2026-02-01")]
    xml = render_rss(config, posts)

    assert "<rss version=\"2.0\">" in xml
    assert "<title>Post 1</title>" in xml
    assert "<link>https://example.com/blog/post-1/</link>" in xml
    assert "Resumo." in xml


def test_render_atom_contains_entries(tmp_path: Path):
    config = _config(tmp_path)
    posts = [_post(1, "2026-01-01")]
    xml = render_atom(config, posts)

    assert '<feed xmlns="http://www.w3.org/2005/Atom">' in xml
    assert "<title>Post 1</title>" in xml
    assert 'href="https://example.com/blog/post-1/"' in xml


def test_render_rss_handles_missing_date(tmp_path: Path):
    config = _config(tmp_path)
    post = _post(1, "")
    post.frontmatter.date = None
    xml = render_rss(config, [post])
    assert "<pubDate>" in xml  # não quebra, usa a data atual como fallback
