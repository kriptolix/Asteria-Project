"""Escrita dos arquivos finais e cópia de assets (spec seção 22, 26 passo 13/16)."""

from __future__ import annotations

import shutil
from pathlib import Path

from .config import SiteConfig
from .converter import ExtractedImage


def write_page(output_dir: Path, relative_path: str, html: str) -> Path:
    target = output_dir / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target


def write_text_file(output_dir: Path, relative_path: str, content: str) -> Path:
    target = output_dir / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def copy_static_assets(config: SiteConfig) -> None:
    """Copia static/ (assets do site) e theme/<nome>/css|js (assets do tema)."""
    output_dir = config.output_dir

    if config.static_dir.exists():
        _copy_tree(config.static_dir, output_dir)

    theme_dir = config.theme_dir
    for sub in ("css", "js", "fonts", "images"):
        src = theme_dir / sub
        if src.exists():
            _copy_tree(src, output_dir / sub)


def _copy_tree(src: Path, dst: Path, exclude: set[str] | None = None) -> None:
    exclude = exclude or set()
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        if item.name in exclude:
            continue
        rel = item.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def write_document_images(
    output_dir: Path, images: list[ExtractedImage], subdir: str = ""
) -> None:
    """Grava as imagens de um documento dentro do seu próprio diretório de
    saída (`subdir`, geralmente derivado de `urls.url_to_output_dir`), para
    que fiquem ao lado do `index.html` da página/post, não em uma pasta
    `/images/` global.
    """
    target_dir = output_dir / subdir if subdir else output_dir
    for image in images:
        target = target_dir / image.output_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(image.data)


def clean_output(config: SiteConfig) -> None:
    if config.output_dir.exists():
        shutil.rmtree(config.output_dir)


def copy_raw_pages(output_dir: Path, raw_pages: list) -> None:
    """Copia cada pasta de página HTML "crua" verbatim para a saída, num
    diretório próprio isolado (ver `asteria.raw`). Nada é reescrito ou
    processado — é exatamente o que o usuário colocou em `content/raw/`.
    """
    for page in raw_pages:
        target_dir = output_dir / page.url.strip("/")
        _copy_tree(page.source_dir, target_dir, exclude={"raw.yaml"})


def list_generated_files(output_dir: Path) -> list[str]:
    """Lista relativa de todos os arquivos gerados (spec 14 — 'relatório de
    arquivos gerados')."""
    if not output_dir.exists():
        return []
    return sorted(
        str(p.relative_to(output_dir))
        for p in output_dir.rglob("*")
        if p.is_file()
    )
