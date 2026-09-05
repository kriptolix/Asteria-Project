"""Constroi pacotes .odt minimos em memoria, para nao depender do
LibreOffice na suite de testes (secao 18 pede documentos "produzidos pelo
LibreOffice" no conjunto real, mas para testes automatizados unitarios
construimos ODT sinteticos, validos, cobrindo cada recurso isoladamente)."""
from __future__ import annotations

import io
import zipfile

MANIFEST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">
 <manifest:file-entry manifest:full-path="/" manifest:version="1.3" manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
{extra}</manifest:manifest>
"""

DEFAULT_STYLES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles
    xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
    xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
    xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
    xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    office:version="1.3">
  <office:styles>
    <style:style style:name="Standard" style:family="paragraph"/>
    <style:style style:name="Text_20_Body" style:display-name="Text Body" style:family="paragraph" style:parent-style-name="Standard"/>
    <style:style style:name="Heading_20_1" style:display-name="Heading 1" style:family="paragraph" style:parent-style-name="Standard"/>
    <style:style style:name="Heading_20_2" style:display-name="Heading 2" style:family="paragraph" style:parent-style-name="Standard"/>
    <style:style style:name="Title" style:family="paragraph" style:parent-style-name="Standard"/>
    <style:style style:name="Quotation" style:family="paragraph" style:parent-style-name="Standard"/>
    <style:style style:name="Caption" style:family="paragraph" style:parent-style-name="Standard"/>
    {extra_styles}
  </office:styles>
  <office:automatic-styles>
    {extra_automatic_styles}
  </office:automatic-styles>
</office:document-styles>
"""

DEFAULT_META_XML = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta
    xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
    xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    office:version="1.3">
  <office:meta>
    <dc:title>{title}</dc:title>
    <meta:initial-creator>{author}</meta:initial-creator>
    <dc:description>{description}</dc:description>
  </office:meta>
</office:document-meta>
"""

CONTENT_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
    xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
    xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
    xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
    xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
    xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
    office:version="1.3">
  <office:automatic-styles>
    {automatic_styles}
  </office:automatic-styles>
  <office:body>
    <office:text>
      {body}
    </office:text>
  </office:body>
</office:document-content>
"""


def build_odt(
    body_xml: str,
    *,
    automatic_styles: str = "",
    extra_styles: str = "",
    extra_automatic_styles: str = "",
    title: str = "Documento de teste",
    author: str = "Autor de Teste",
    description: str = "",
    pictures: dict[str, bytes] | None = None,
) -> bytes:
    """Monta um .odt valido em memoria a partir de um trecho de XML para
    dentro de <office:text>...</office:text>."""
    pictures = pictures or {}

    content_xml = CONTENT_TEMPLATE.format(automatic_styles=automatic_styles, body=body_xml)
    styles_xml = DEFAULT_STYLES_XML.format(
        extra_styles=extra_styles, extra_automatic_styles=extra_automatic_styles,
    )
    meta_xml = DEFAULT_META_XML.format(title=title, author=author, description=description)

    extra_manifest_entries = "".join(
        f' <manifest:file-entry manifest:full-path="Pictures/{name}" '
        f'manifest:media-type="image/png"/>\n'
        for name in pictures
    )
    manifest_xml = MANIFEST_TEMPLATE.format(extra=extra_manifest_entries)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        zf.writestr("content.xml", content_xml)
        zf.writestr("styles.xml", styles_xml)
        zf.writestr("meta.xml", meta_xml)
        zf.writestr("META-INF/manifest.xml", manifest_xml)
        for name, data in pictures.items():
            zf.writestr(f"Pictures/{name}", data)
    return buf.getvalue()


# um PNG 1x1 valido, para testes de imagem
TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000a49444154789c6360000002000155bfabd400000000"
    "49454e44ae426082"
)
