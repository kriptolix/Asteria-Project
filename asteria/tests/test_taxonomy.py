from pathlib import Path

from asteria.config import load_config
from asteria.document import Post
from asteria.frontmatter import Frontmatter
from asteria.taxonomy import collect_categories, collect_tags


def _post(n: int, tags, categories, date) -> Post:
    return Post(
        id=f"post-{n}",
        kind="post",
        source_path=Path(f"post-{n}.odt"),
        frontmatter=Frontmatter(title=f"Post {n}", date=date, tags=tags, categories=categories),
        content_html="",
        raw_content_html="",
    )


def _config(tmp_path: Path):
    (tmp_path / "site.yaml").write_text("site:\n  title: T\n", encoding="utf-8")
    return load_config(tmp_path / "site.yaml")


def test_collect_tags_merges_case_insensitively(tmp_path: Path):
    posts = [
        _post(1, ["Python", "Web"], ["Tecnologia"], "2026-01-01"),
        _post(2, ["python"], ["tecnologia"], "2026-01-02"),
    ]
    config = _config(tmp_path)
    tags = collect_tags(posts, config)

    by_slug = {t.slug: t for t in tags}
    assert set(by_slug) == {"python", "web"}
    assert len(by_slug["python"].posts) == 2
    assert by_slug["python"].name == "Python"  # primeira grafia encontrada
    assert by_slug["python"].url == "/tags/python/"


def test_collect_categories_sorted_posts_desc_by_date(tmp_path: Path):
    posts = [
        _post(1, [], ["Tecnologia"], "2026-01-01"),
        _post(2, [], ["Tecnologia"], "2026-06-01"),
    ]
    config = _config(tmp_path)
    categories = collect_categories(posts, config)

    assert len(categories) == 1
    ordered_ids = [p.id for p in categories[0].posts]
    assert ordered_ids == ["post-2", "post-1"]
