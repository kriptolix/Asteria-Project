"""Namespaces XML do OpenDocument Format usados pelo pacote."""

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "dc": "http://purl.org/dc/elements/1.1/",
    "number": "urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
    "presentation": "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
}


def tag(prefix: str, name: str) -> str:
    """Retorna a tag qualificada '{uri}name' para uso com ElementTree."""
    return f"{{{NS[prefix]}}}{name}"


def q(qualified: str) -> str:
    """Converte 'prefix:name' em '{uri}name'."""
    prefix, name = qualified.split(":", 1)
    return tag(prefix, name)
