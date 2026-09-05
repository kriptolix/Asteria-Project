"""Funcoes de seguranca (secao 13 da especificacao).

O .odt deve ser tratado como entrada nao confiavel:
- texto e' sempre escapado antes de entrar no HTML;
- URLs sao validadas contra uma lista de esquemas permitidos, para evitar
  a inclusao de caminhos de arquivo locais (file://) ou esquemas
  potencialmente perigosos (javascript:, data: arbitrario, etc.);
- nenhuma macro, script ou conteudo incorporado do ODT e' executado -
  o pacote simplesmente nao possui codigo capaz de interpretar macros
  Basic/Python do ODF, entao esse conteudo e' ignorado por construcao.
"""
from __future__ import annotations

import html as _html
import re
from urllib.parse import urlparse

ALLOWED_URL_SCHEMES = {"http", "https", "mailto", "tel", ""}

# esquemas explicitamente perigosos ou que permitem escapar do sandbox do
# navegador / do diretorio de saida.
_DANGEROUS_SCHEMES = {"javascript", "file", "vbscript", "data"}


def escape_text(value: str) -> str:
    """Escapa texto para uso seguro em conteudo HTML."""
    return _html.escape(value, quote=False)


def escape_attr(value: str) -> str:
    """Escapa texto para uso seguro dentro de um atributo HTML (aspas duplas)."""
    return _html.escape(value, quote=True)


def sanitize_url(url: str, *, allow_relative: bool = True) -> str | None:
    """Sanitiza uma URL vinda do documento ODT.

    Retorna None se a URL for considerada perigosa (nesse caso o chamador
    deve omitir o link/atributo em vez de gera-lo).
    """
    if url is None:
        return None
    url = url.strip()
    if not url:
        return None

    # normaliza espacos em branco internos usados para ofuscar esquemas,
    # ex: "java\tscript:alert(1)"
    stripped = re.sub(r"[\s\x00-\x1f]+", "", url)
    parsed = urlparse(stripped)
    scheme = parsed.scheme.lower()

    if scheme in _DANGEROUS_SCHEMES:
        return None

    if scheme and scheme not in ALLOWED_URL_SCHEMES:
        # esquemas desconhecidos (ftp:, custom:, etc.) sao rejeitados por
        # padrao - a lista de permitidos pode ser estendida no futuro.
        return None

    if not scheme and not allow_relative:
        return None

    return escape_attr(url)


def is_safe_relative_path(path: str) -> bool:
    """Verifica que um caminho relativo de asset nao escapa do diretorio
    de saida (protege contra path traversal via nomes de arquivo no ODT)."""
    if not path:
        return False
    if path.startswith("/") or path.startswith("\\"):
        return False
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    depth = 0
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            depth -= 1
            if depth < 0:
                return False
        else:
            depth += 1
    return True
