from pathlib import Path

from asteria.document import Post
from asteria.frontmatter import Frontmatter
from asteria.pagination import paginate


def _post(n: int) -> Post:
    return Post(
        id=f"post-{n}",
        kind="post",
        source_path=Path(f"post-{n}.odt"),
        frontmatter=Frontmatter(title=f"Post {n}", date=f"2026-01-{n:02d}"),
        content_html="",
        raw_content_html="",
    )


def test_paginate_splits_into_pages():
    posts = [_post(n) for n in range(1, 6)]
    pages = paginate(posts, per_page=2, base_url="/blog/")

    assert len(pages) == 3
    assert [p.number for p in pages] == [1, 2, 3]
    assert pages[0].url == "/blog/"
    assert pages[1].url == "/blog/page/2/"
    assert pages[2].url == "/blog/page/3/"
    assert len(pages[0].items) == 2
    assert len(pages[2].items) == 1


def test_paginate_prev_next_links():
    posts = [_post(n) for n in range(1, 4)]
    pages = paginate(posts, per_page=1, base_url="/blog/")

    assert pages[0].prev_url is None
    assert pages[0].next_url == "/blog/page/2/"
    assert pages[1].prev_url == "/blog/"
    assert pages[1].next_url == "/blog/page/3/"
    assert pages[2].next_url is None


def test_paginate_empty_list_returns_single_empty_page():
    pages = paginate([], per_page=10, base_url="/blog/")
    assert len(pages) == 1
    assert pages[0].items == []
    assert pages[0].total_pages == 1
