"""Package Reader (secao 3.1 da especificacao).

Le o .odt como um pacote ZIP (formato ODF) e da acesso a:
- content.xml
- styles.xml
- meta.xml
- settings.xml
- manifest.xml
- recursos binarios em Pictures/ e outros

Nao depende do LibreOffice.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree as ET


class InvalidOdtError(Exception):
    """Levantado quando o arquivo nao e' um pacote ODT valido."""


@dataclass
class OdtPackage:
    content_xml: ET.Element | None
    styles_xml: ET.Element | None
    meta_xml: ET.Element | None
    settings_xml: ET.Element | None
    manifest_entries: dict[str, str]  # full-path -> media-type
    resources: dict[str, bytes]  # caminho dentro do zip -> bytes (Pictures/, etc.)
    mimetype: str | None


def _parse_xml(data: bytes) -> ET.Element:
    # xml.etree nao expande entidades externas nem processa DTDs por
    # padrao, o que mitiga ataques XXE/bilhao-de-risadas comuns; ainda
    # assim tratamos o conteudo como nao confiavel (secao 13).
    return ET.fromstring(data)


def read_odt_bytes(data: bytes) -> OdtPackage:
    """Le um pacote .odt a partir de bytes em memoria."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise InvalidOdtError("Arquivo nao e' um ZIP/ODT valido") from exc

    names = set(zf.namelist())

    mimetype = None
    if "mimetype" in names:
        mimetype = zf.read("mimetype").decode("ascii", errors="replace").strip()

    def read_optional_xml(name: str) -> ET.Element | None:
        if name not in names:
            return None
        try:
            return _parse_xml(zf.read(name))
        except ET.ParseError as exc:
            raise InvalidOdtError(f"XML invalido em {name}: {exc}") from exc

    content_xml = read_optional_xml("content.xml")
    if content_xml is None:
        raise InvalidOdtError("content.xml ausente - nao parece ser um .odt valido")

    styles_xml = read_optional_xml("styles.xml")
    meta_xml = read_optional_xml("meta.xml")
    settings_xml = read_optional_xml("settings.xml")

    manifest_entries: dict[str, str] = {}
    manifest_root = read_optional_xml("META-INF/manifest.xml")
    if manifest_root is not None:
        ns = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
        for entry in manifest_root.findall(f"{{{ns}}}file-entry"):
            full_path = entry.get(f"{{{ns}}}full-path")
            media_type = entry.get(f"{{{ns}}}media-type", "")
            if full_path:
                manifest_entries[full_path] = media_type

    resources: dict[str, bytes] = {}
    for name in names:
        if name.startswith("Pictures/") or name.startswith("media/") or name.startswith("Thumbnails/"):
            if not name.endswith("/"):
                resources[name] = zf.read(name)

    return OdtPackage(
        content_xml=content_xml,
        styles_xml=styles_xml,
        meta_xml=meta_xml,
        settings_xml=settings_xml,
        manifest_entries=manifest_entries,
        resources=resources,
        mimetype=mimetype,
    )


def read_odt_file(path: str) -> OdtPackage:
    """Le um pacote .odt a partir de um caminho no sistema de arquivos."""
    with open(path, "rb") as fh:
        data = fh.read()
    return read_odt_bytes(data)
