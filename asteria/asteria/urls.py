"""Geração centralizada de URLs (spec seção 13).

Nenhum outro módulo deve montar uma URL "na mão" — tudo passa por aqui, para
que a estrutura de URLs continue configurável em um único lugar.
"""

from __future__ import annotations

import re
import unicodedata

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Normaliza um texto para um slug seguro em URLs/IDs HTML."""
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = _SLUG_RE.sub("-", value).strip("-")
    return value or "documento"


def build_url(pattern: str, **kwargs: str) -> str:
    """Aplica um padrão de URL, ex: '/blog/{slug}/' -> '/blog/meu-post/'."""
    url = pattern.format(**kwargs)
    if not url.startswith("/"):
        url = "/" + url
    if not url.endswith("/") and "." not in url.rsplit("/", 1)[-1]:
        url += "/"
    return url


def url_to_output_path(url: str) -> str:
    """Converte uma URL ('/sobre/') no caminho relativo do arquivo de saída
    ('sobre/index.html')."""
    path = url.strip("/")
    if not path:
        return "index.html"
    if "." in path.rsplit("/", 1)[-1]:
        return path
    return f"{path}/index.html"


def url_to_output_dir(url: str) -> str:
    """Diretório de saída correspondente a uma URL, sem o `index.html`
    (ex: '/blog/artigo/' -> 'blog/artigo'; '/' -> '').

    Usado para colocar as imagens de um documento no mesmo diretório da
    sua própria página, em vez de uma pasta `/images/` compartilhada.
    """
    output_path = url_to_output_path(url)
    if output_path == "index.html":
        return ""
    return output_path.rsplit("/", 1)[0]
