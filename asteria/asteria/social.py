"""Links de redes sociais no rodapé — estilo `extra.social:` do MkDocs
Material (comportamento conferido como referência: uma linha de ícones
circulares no rodapé, cada um linkando pra um perfil).

Config em `theme/<nome>/theme.yaml` (namespace do tema, não do site —
ícones e apresentação são decisão do tema):

    social:
      - platform: github
        url: "https://github.com/usuario"
      - platform: mastodon
        url: "https://mastodon.social/@usuario"
      - platform: email
        url: "mailto:contato@example.com"
      - platform: meu-site-x
        url: "https://x.example/perfil"
        label: "X"   # opcional: rótulo customizado (acessibilidade + monograma)

Os ícones são monogramas em SVG (círculo + 1-2 letras) desenhados para o
Asteria — não são cópias dos logotipos oficiais de cada rede (evita
qualquer questão de marca registrada) — mas continuam claramente
distintos e identificáveis em uso. Plataforma não reconhecida ainda
funciona: cai num monograma genérico com a primeira letra do `platform`
(ou do `label`, se informado).
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any

_KNOWN_LABELS = {
    "github": "GitHub",
    "gitlab": "GitLab",
    "twitter": "Twitter",
    "x": "X",
    "mastodon": "Mastodon",
    "linkedin": "LinkedIn",
    "youtube": "YouTube",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "discord": "Discord",
    "telegram": "Telegram",
    "rss": "RSS",
    "email": "E-mail",
}

_KNOWN_MONOGRAMS = {
    "github": "Gh",
    "gitlab": "Gl",
    "twitter": "Tw",
    "x": "X",
    "mastodon": "Mn",
    "linkedin": "in",
    "youtube": "Yt",
    "instagram": "Ig",
    "facebook": "Fb",
    "discord": "Dc",
    "telegram": "Tg",
    "rss": "RSS",
    "email": "@",
}


@dataclass
class SocialLink:
    platform: str
    url: str
    label: str
    svg: str  # markup completo do ícone (círculo + monograma), sem <a> em volta


def _monogram_svg(text: str) -> str:
    font_size = 9 if len(text) > 2 else 11
    return (
        '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">'
        '<circle cx="12" cy="12" r="11" fill="currentColor" opacity="0.12"></circle>'
        '<circle cx="12" cy="12" r="11" fill="none" stroke="currentColor" stroke-width="1.2"></circle>'
        f'<text x="12" y="12" text-anchor="middle" dominant-baseline="central" '
        f'font-family="system-ui, sans-serif" font-size="{font_size}" font-weight="600" '
        f'fill="currentColor">{escape(text)}</text>'
        "</svg>"
    )


def build_social_links(social_config: list[dict[str, Any]]) -> list[SocialLink]:
    links: list[SocialLink] = []
    for entry in social_config:
        platform = str(entry.get("platform", "")).strip().lower()
        url = entry.get("url")
        if not platform or not url:
            continue

        label = entry.get("label") or _KNOWN_LABELS.get(platform, platform.capitalize())
        monogram = entry.get("label", "")[:2] if entry.get("label") else _KNOWN_MONOGRAMS.get(
            platform, platform[:2].upper() if len(platform) >= 2 else platform.upper()
        )

        links.append(
            SocialLink(platform=platform, url=str(url), label=label, svg=_monogram_svg(monogram))
        )

    return links
