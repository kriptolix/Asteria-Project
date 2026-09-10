"""Writing the final files and copying assets."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from .config import SiteConfig
from .converter import ExtractedImage


FINGERPRINT_SUBDIRS: tuple[str, ...] = ("css", "js", "fonts", "images")

_HASH_LENGTH = 10


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
    
    target_dir = output_dir / subdir if subdir else output_dir
    for image in images:
        target = target_dir / image.output_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(image.data)


def _content_hash(path: Path, length: int = _HASH_LENGTH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:length]


def fingerprint_assets(
    output_dir: Path, subdirs: tuple[str, ...] = FINGERPRINT_SUBDIRS
) -> dict[str, str]:
   
    manifest: dict[str, str] = {}

    for subdir in subdirs:
        base = output_dir / subdir
        if not base.exists():
            continue
        
        # Materialize the list before renaming, to avoid iterating over a
        # directory that is being modified.
        for file_path in sorted(p for p in base.rglob("*") if p.is_file()):
            digest = _content_hash(file_path)
            new_path = file_path.with_name(f"{file_path.stem}.{digest}{file_path.suffix}")
            file_path.replace(new_path)

            original_rel = "/" + file_path.relative_to(output_dir).as_posix()
            fingerprinted_rel = "/" + new_path.relative_to(output_dir).as_posix()
            manifest[original_rel] = fingerprinted_rel

    return manifest


def clean_output(config: SiteConfig) -> None:
    if config.output_dir.exists():
        shutil.rmtree(config.output_dir)


def copy_raw_pages(output_dir: Path, raw_pages: list) -> None:
   
    for page in raw_pages:
        target_dir = output_dir / page.url.strip("/")
        _copy_tree(page.source_dir, target_dir, exclude={"raw.yaml"})


def list_generated_files(output_dir: Path) -> list[str]:
    
    if not output_dir.exists():
        return []

    files = []

    for path in output_dir.rglob("*"):
        if path.is_file():
            relative_path = path.relative_to(output_dir)
            files.append(str(relative_path))

    return sorted(files)

