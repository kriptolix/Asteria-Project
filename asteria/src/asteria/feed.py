"""
RSS 2.0 / Atom feed generation for posts
"""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape

from .config import SiteConfig
from .dates import to_utc
from .document import Post




def render_rss(config: SiteConfig, posts: list[Post]) -> str:
    site_url = config.url
    build_date = format_datetime(datetime.now(tz=timezone.utc))

    items = []
    for post in posts:
        link = f"{site_url}{post.url}"
        published = to_utc(post.date)
        # RSS `pubDate` is optional: an undated post simply has none, rather
        # than a date invented at build time.
        pub_date = (
            f"    <pubDate>{format_datetime(published)}</pubDate>\n" if published else ""
        )
        items.append(
            "  <item>\n"
            f"    <title>{escape(post.title)}</title>\n"
            f"    <link>{escape(link)}</link>\n"
            f"    <guid>{escape(link)}</guid>\n"
            f"{pub_date}"
            f"    <description>{escape(post.excerpt)}</description>\n"
            "  </item>"
        )

    body = "\n".join(items)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "<channel>\n"
        f"  <title>{escape(config.title)}</title>\n"
        f"  <link>{escape(site_url)}</link>\n"
        f"  <description>{escape(config.description)}</description>\n"
        f"  <lastBuildDate>{build_date}</lastBuildDate>\n"
        f"{body}\n"
        "</channel>\n"
        "</rss>\n"
    )


def render_atom(config: SiteConfig, posts: list[Post]) -> str:
    site_url = config.url
    updated = datetime.now(tz=timezone.utc).isoformat()

    entries = []
    for post in posts:
        link = f"{site_url}{post.url}"
        # Atom requires `updated`: an undated post gets the build time.
        updated_at = to_utc(post.date) or datetime.now(tz=timezone.utc)
        entries.append(
            "  <entry>\n"
            f"    <title>{escape(post.title)}</title>\n"
            f'    <link href="{escape(link)}"/>\n'
            f"    <id>{escape(link)}</id>\n"
            f"    <updated>{updated_at.isoformat()}</updated>\n"
            f"    <summary>{escape(post.excerpt)}</summary>\n"
            "  </entry>"
        )

    body = "\n".join(entries)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        f"  <title>{escape(config.title)}</title>\n"
        f'  <link href="{escape(site_url)}"/>\n'
        f"  <id>{escape(site_url)}/</id>\n"
        f"  <updated>{updated}</updated>\n"
        f"{body}\n"
        "</feed>\n"
    )