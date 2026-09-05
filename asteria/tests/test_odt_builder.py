from pathlib import Path

from asteria.converter import FallbackConverter
from asteria.errors import Diagnostics
from asteria.odt_builder import OdtDocument


def test_odt_document_builds_and_converts_correctly(tmp_path: Path):
    path = tmp_path / "doc.odt"
    (
        OdtDocument(frontmatter={"title": "Teste"})
        .heading("Título Um", 1)
        .paragraph("Um parágrafo.")
        .list_items(["Item A", "Item B"])
        .save(path)
    )

    assert path.exists()

    result = FallbackConverter().convert(path, Diagnostics())
    assert "ssg-frontmatter" in result.html
    assert "Título Um" in result.html
    assert "Item A" in result.html
    assert "Item B" in result.html


def test_odt_document_escapes_special_characters(tmp_path: Path):
    path = tmp_path / "doc.odt"
    OdtDocument().paragraph("<script>alert('x')</script> & mais").save(path)

    result = FallbackConverter().convert(path, Diagnostics())
    assert "<script>" not in result.html
    assert "&amp;" in result.html or "&lt;script&gt;" in result.html
