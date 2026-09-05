"""Páginas HTML "cruas" — caso de borda para quem precisa de mais controle
do que o ODT permite (ex: uma "ficha" com HTML/CSS 100% autoral).

Abordagem genérica: qualquer subpasta dentro de `content/pages/` ou
`content/posts/` que **não contenha nenhum `.odt`**, mas tenha um
`index.html` diretamente dentro dela, é tratada como uma página crua — não
existe uma pasta dedicada `content/raw/` separada. A pasta inteira (HTML,
CSS, JS, imagens, o que for) é copiada **verbatim** para sua própria URL,
usando o mesmo padrão de URL de onde ela foi encontrada (`urls.pages` ou
`urls.posts`) — sem passar pela conversão ODT, sem o layout do tema, sem
CSS do tema injetado.

Estrutura esperada:

    content/pages/ficha-exemplo/index.html      (obrigatório — ponto de entrada)
    content/pages/ficha-exemplo/style.css        (opcional, qualquer asset próprio)
    content/pages/ficha-exemplo/raw.yaml         (opcional: title / height)

`raw.yaml` (opcional, não é copiado pro output):

    title: Ficha do Guerreiro
    height: 900

Páginas cruas participam da checagem de unicidade de `id` (junto com
páginas e posts) e do registro de referências (`[[id]]` / `[[embed:id]]`),
mas não entram em listagens curadas (índice do blog, tags/categorias, feed
RSS/Atom), já que não têm data nem front matter reais.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .errors import Diagnostics
from .urls import build_url, slugify

DEFAULT_EMBED_HEIGHT = 600


@dataclass
class RawPage:
    id: str
    source_dir: Path
    title: str = ""
    height: int = DEFAULT_EMBED_HEIGHT
    slug: str = ""
    url: str = ""

    def __post_init__(self) -> None:
        if not self.slug:
            self.slug = slugify(self.id)
        if not self.title:
            self.title = self.id


def load_raw_page(
    source_dir: Path, url_pattern: str, diagnostics: Diagnostics
) -> RawPage:
    """Constrói um `RawPage` a partir de uma pasta já identificada como
    contendo um `index.html` (a detecção em si fica em `discovery.py`, que
    sabe se está olhando dentro de `pages/` ou `posts/`)."""
    meta: dict = {}
    meta_path = source_dir / "raw.yaml"
    if meta_path.exists():
        try:
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            diagnostics.warning(
                f"raw.yaml inválido, ignorado: {exc}", source=str(meta_path)
            )
            meta = {}

    page = RawPage(
        id=source_dir.name,
        source_dir=source_dir,
        title=str(meta.get("title", "")) or source_dir.name,
        height=int(meta.get("height", DEFAULT_EMBED_HEIGHT)),
    )
    page.url = build_url(url_pattern, slug=page.slug)
    return page
