"""Descoberta de conteúdo (spec seção 6 e 26, passos 2-6).

Varre `content/pages` e `content/posts`, converte cada `.odt`, extrai o
front matter e monta os objetos `Page`/`Post`. Também identifica páginas
HTML "cruas" (ver `asteria/raw.py`) e valida que todos os identificadores
(nome do arquivo/pasta sem extensão) são únicos em todo o site.

Duas regras de varredura, intencionalmente diferentes:

- **`content/pages/` é recursiva**: subpastas servem para *organizar*
  páginas (ex: `content/pages/guia/instalacao.odt`), sem afetar `id`/URL —
  a navegação entre páginas é responsabilidade do `nav:` em `site.yaml`
  (ver `asteria/nav.py`), não da estrutura de diretórios. Uma subpasta que
  não contém nenhum `.odt` em toda a sua árvore, mas tem um `index.html`
  diretamente nela, é tratada como uma página HTML crua.
- **`content/posts/` é plana** (um nível só): agrupar posts em subpastas
  não faz sentido para uma listagem cronológica de blog. Uma subpasta
  imediata de `content/posts/` com `index.html` também vira uma página
  crua (útil para uma landing page especial ligada a um post, por
  exemplo), mas não há recursão além desse primeiro nível.
"""

from __future__ import annotations

from pathlib import Path

from .config import SiteConfig
from .converter import ODTConverter
from .document import Document, Page, Post
from .errors import Diagnostics
from .frontmatter import extract_frontmatter
from .raw import RawPage, load_raw_page


def _walk_pages(
    directory: Path, diagnostics: Diagnostics
) -> tuple[list[Path], list[Path]]:
    """Recursivo. Retorna (caminhos_odt, pastas_raw)."""
    odt_paths: list[Path] = []
    raw_dirs: list[Path] = []
    _walk_pages_rec(directory, odt_paths, raw_dirs, diagnostics)
    return odt_paths, raw_dirs


def _walk_pages_rec(
    directory: Path,
    odt_paths: list[Path],
    raw_dirs: list[Path],
    diagnostics: Diagnostics,
) -> None:
    if not directory.exists():
        return
    for entry in sorted(directory.iterdir()):
        if entry.is_file() and entry.suffix == ".odt":
            odt_paths.append(entry)
        elif entry.is_dir():
            if any(entry.rglob("*.odt")):
                # Pasta organizacional: contém (em algum nível) .odt —
                # recursa normalmente, sem afetar id/URL das páginas.
                _walk_pages_rec(entry, odt_paths, raw_dirs, diagnostics)
            elif (entry / "index.html").exists():
                raw_dirs.append(entry)
            else:
                diagnostics.warning(
                    f"Pasta em content/pages/ sem .odt nem index.html, ignorada: '{entry.name}'.",
                    source=str(entry),
                )


def _walk_posts(
    directory: Path, diagnostics: Diagnostics
) -> tuple[list[Path], list[Path]]:
    """Plano (só um nível). Retorna (caminhos_odt, pastas_raw)."""
    odt_paths: list[Path] = []
    raw_dirs: list[Path] = []
    if not directory.exists():
        return odt_paths, raw_dirs

    for entry in sorted(directory.iterdir()):
        if entry.is_file() and entry.suffix == ".odt":
            odt_paths.append(entry)
        elif entry.is_dir():
            if (entry / "index.html").exists():
                raw_dirs.append(entry)
            else:
                diagnostics.warning(
                    f"Pasta em content/posts/ sem index.html, ignorada: '{entry.name}' "
                    "(content/posts/ não é recursivo para .odt).",
                    source=str(entry),
                )

    return odt_paths, raw_dirs


def _load_document(
    path: Path,
    kind: str,
    converter: ODTConverter,
    diagnostics: Diagnostics,
) -> Document:
    doc_id = path.stem
    if not doc_id or not doc_id.replace("-", "").replace("_", "").isalnum():
        diagnostics.warning(
            f"Identificador de documento incomum derivado do nome de arquivo: '{doc_id}'.",
            source=str(path),
        )

    result = converter.convert(path, diagnostics)

    if result.metadata is not None:
        # O conversor (ex: odt2web) já reconheceu e extraiu o bloco de
        # metadados por conta própria (spec 5.3 — responsabilidade da
        # biblioteca ODT). O HTML já vem sem o bloco de front matter.
        fm = result.metadata
        content_html = result.html
    else:
        # Conversor não reconhece front matter nativamente (ex: o
        # FallbackConverter): o SSG procura o bloco padronizado
        # `div.ssg-frontmatter` no HTML (spec 5.2/5.3).
        fm, content_html = extract_frontmatter(
            result.html, source=str(path), diagnostics=diagnostics
        )
        if not fm.title:
            diagnostics.warning(
                "Documento sem 'title' no front matter; usando o nome do arquivo.",
                source=str(path),
            )

    cls = Page if kind == "page" else Post
    return cls(
        id=doc_id,
        kind=kind,
        source_path=path,
        frontmatter=fm,
        content_html=content_html,
        raw_content_html=content_html,
        images=result.images,
    )


def discover_content(
    config: SiteConfig, converter: ODTConverter, diagnostics: Diagnostics
) -> tuple[list[Page], list[Post], list[RawPage]]:
    pages: list[Page] = []
    posts: list[Post] = []
    raw_pages: list[RawPage] = []

    page_odts, page_raw_dirs = _walk_pages(config.pages_dir, diagnostics)
    for path in page_odts:
        pages.append(_load_document(path, "page", converter, diagnostics))  # type: ignore[arg-type]
    for raw_dir in page_raw_dirs:
        raw_pages.append(
            load_raw_page(raw_dir, config.url_patterns["pages"], diagnostics)
        )

    post_odts, post_raw_dirs = _walk_posts(config.posts_dir, diagnostics)
    for path in post_odts:
        posts.append(_load_document(path, "post", converter, diagnostics))  # type: ignore[arg-type]
    for raw_dir in post_raw_dirs:
        raw_pages.append(
            load_raw_page(raw_dir, config.url_patterns["posts"], diagnostics)
        )

    _validate_unique_ids(pages, posts, raw_pages, diagnostics)
    return pages, posts, raw_pages


def _validate_unique_ids(
    pages: list[Page],
    posts: list[Post],
    raw_pages: list[RawPage],
    diagnostics: Diagnostics,
) -> None:
    seen: dict[str, str] = {}  # id -> caminho de origem (str) já visto
    for item in [*pages, *posts, *raw_pages]:
        source = str(getattr(item, "source_path", None) or getattr(item, "source_dir", ""))
        if item.id in seen:
            diagnostics.error(
                f"ID duplicado '{item.id}': usado por '{seen[item.id]}' e '{source}'.",
                source=source,
            )
        else:
            seen[item.id] = source
