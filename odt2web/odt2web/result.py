"""Tipos publicos retornados pela API (secao 2 da especificacao)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .model import Metadata


class WarningLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Warning:
    message: str
    level: WarningLevel = WarningLevel.WARNING
    source: str | None = None  # ex: "parser", "renderer", "assets"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"[{self.level.value}] {self.message}"


@dataclass
class Asset:
    """Um recurso extraido do pacote ODT (normalmente uma imagem)."""
    original_path: str  # caminho dentro do .odt, ex: Pictures/10000000...png
    output_path: str  # caminho relativo referenciado pelo HTML
    data: bytes = field(repr=False, default=b"")
    media_type: str | None = None
    written_to: str | None = None  # caminho absoluto em disco, se escrito


@dataclass
class ConversionResult:
    html: str
    css: str | None
    assets: list[Asset] = field(default_factory=list)
    metadata: Metadata = field(default_factory=Metadata)
    front_matter: dict | None = None
    warnings: list[Warning] = field(default_factory=list)

    def write(self, output_dir: str, html_filename: str = "index.html",
              css_filename: str = "style.css") -> None:
        """Escreve html/css/assets em output_dir. Usado internamente pela
        API de alto nivel quando output_dir e' informado, mas tambem pode
        ser chamado manualmente."""
        import os

        os.makedirs(output_dir, exist_ok=True)
        html_path = os.path.join(output_dir, html_filename)
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(self.html)

        if self.css is not None:
            css_path = os.path.join(output_dir, css_filename)
            with open(css_path, "w", encoding="utf-8") as fh:
                fh.write(self.css)

        for asset in self.assets:
            asset_path = os.path.join(output_dir, asset.output_path)
            os.makedirs(os.path.dirname(asset_path), exist_ok=True)
            with open(asset_path, "wb") as fh:
                fh.write(asset.data)
            asset.written_to = asset_path
