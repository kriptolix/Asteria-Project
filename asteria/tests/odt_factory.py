"""Helper de testes: cria arquivos .odt mínimos sem dependências externas."""
import zipfile
from pathlib import Path

MIMETYPE = b"application/vnd.oasis.opendocument.text"
MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
 <manifest:file-entry manifest:full-path="/" manifest:version="1.2" manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""
CONTENT_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
 xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
 xmlns:xlink="http://www.w3.org/1999/xlink"
 office:version="1.2">
 <office:body>
  <office:text>
"""
CONTENT_FOOTER = "  </office:text>\n </office:body>\n</office:document-content>\n"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def p(text=""):
    return f"   <text:p>{esc(text)}</text:p>\n"


def h(text, level=1):
    return f'   <text:h text:outline-level="{level}">{esc(text)}</text:h>\n'


def frontmatter_block(fields: dict) -> str:
    lines = ["---"] + [f"{k}: {v}" for k, v in fields.items()] + ["---"]
    return "".join(p(line) for line in lines)


def make_odt(path: Path, body_xml: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", MIMETYPE, compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/manifest.xml", MANIFEST)
        zf.writestr("content.xml", CONTENT_HEADER + body_xml + CONTENT_FOOTER)
    return path
