from asteria.urls import build_url, slugify, url_to_output_path


def test_slugify_accents_and_spaces():
    assert slugify("Instalação no Linux") == "instalacao-no-linux"
    assert slugify("Python & Web!") == "python-web"


def test_build_url_pages_pattern():
    assert build_url("/{slug}/", slug="sobre") == "/sobre/"


def test_build_url_posts_pattern():
    assert build_url("/blog/{slug}/", slug="meu-artigo") == "/blog/meu-artigo/"


def test_url_to_output_path():
    assert url_to_output_path("/sobre/") == "sobre/index.html"
    assert url_to_output_path("/") == "index.html"
    assert url_to_output_path("/sitemap.xml") == "sitemap.xml"
