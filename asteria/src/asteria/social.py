"""
Social media links in the footer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import Diagnostics


@dataclass
class SocialLink:
    platform: str
    url: str
    label: str

    @property
    def initials(self) -> str:
        """Fallback text for platforms the theme has no icon for: the first
        letter of the first two words ("My Mastodon" -> "MM"), or the first
        two letters of a single word ("GitHub" -> "GI")."""
        words = self.label.split()
        if len(words) >= 2:
            return (words[0][0] + words[1][0]).upper()
        return self.label[:2].upper()


def build_social_links(
    social_config: list[Any], diagnostics: Diagnostics
) -> list[SocialLink]:
    """Builds the footer links from `social:` in site.yaml. Each entry needs
    `platform`, `url` and `label`; incomplete entries are skipped with a
    warning."""
    links: list[SocialLink] = []

    for entry in social_config:
        if not isinstance(entry, dict):
            diagnostics.warning(
                f"social: malformed item, ignored: {entry!r}", source="site.yaml"
            )
            continue

        platform = str(entry.get("platform") or "").strip().lower()
        url = str(entry.get("url") or "").strip()
        label = str(entry.get("label") or "").strip()

        if not platform or not url or not label:
            diagnostics.warning(
                "social: each item needs 'platform', 'url' and 'label' "
                f"— ignored: {entry!r}",
                source="site.yaml",
            )
            continue

        links.append(SocialLink(platform=platform, url=url, label=label))

    return links