from pathlib import Path

from asteria.cache import CachingConverter, load_cache, save_cache
from asteria.converter import ConversionResult, ExtractedImage
from asteria.errors import Diagnostics

from .odt_factory import frontmatter_block, make_odt, p


class _CountingConverter:
    name = "counting"

    def __init__(self):
        self.calls = 0

    def convert(self, odt_path, diagnostics):
        self.calls += 1
        return ConversionResult(
            html=f"<p>conteúdo {self.calls}</p>",
            images=[ExtractedImage(original_path="Pictures/x.png", data=b"abc", output_name="x.png")],
            converter_name="counting",
        )


def test_caching_converter_hits_on_unchanged_file(tmp_path: Path):
    odt = make_odt(tmp_path / "doc.odt", frontmatter_block({"title": "X"}) + p("y"))
    inner = _CountingConverter()
    cache = CachingConverter(inner, {})
    diagnostics = Diagnostics()

    r1 = cache.convert(odt, diagnostics)
    r2 = cache.convert(odt, diagnostics)

    assert inner.calls == 1  # segunda chamada veio do cache
    assert cache.hits == 1
    assert cache.misses == 1
    assert r1.html == r2.html
    assert r2.images[0].data == b"abc"


def test_caching_converter_misses_when_file_changes(tmp_path: Path):
    odt = make_odt(tmp_path / "doc.odt", frontmatter_block({"title": "X"}) + p("y"))
    inner = _CountingConverter()
    cache = CachingConverter(inner, {})
    diagnostics = Diagnostics()

    cache.convert(odt, diagnostics)

    import os
    import time

    time.sleep(0.01)
    odt.write_bytes(odt.read_bytes() + b"\x00")  # muda tamanho e mtime
    os.utime(odt, None)

    cache.convert(odt, diagnostics)

    assert inner.calls == 2
    assert cache.misses == 2


def test_save_and_load_cache_roundtrip(tmp_path: Path):
    odt = make_odt(tmp_path / "doc.odt", frontmatter_block({"title": "X"}) + p("y"))
    inner = _CountingConverter()
    entries: dict = {}
    cache = CachingConverter(inner, entries)
    diagnostics = Diagnostics()
    cache.convert(odt, diagnostics)

    save_cache(tmp_path, entries)
    loaded = load_cache(tmp_path)

    assert list(loaded.keys()) == list(entries.keys())

    inner2 = _CountingConverter()
    cache2 = CachingConverter(inner2, loaded)
    cache2.convert(odt, diagnostics)
    assert inner2.calls == 0  # veio inteiramente do cache persistido em disco


def test_load_cache_missing_file_returns_empty(tmp_path: Path):
    assert load_cache(tmp_path) == {}


def test_load_cache_corrupted_file_returns_empty(tmp_path: Path):
    (tmp_path / ".asteria-cache.json").write_text("{not json", encoding="utf-8")
    assert load_cache(tmp_path) == {}
