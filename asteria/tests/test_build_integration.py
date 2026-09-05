from pathlib import Path

import pytest

from asteria.build import run_build

EXAMPLE_ROOT = Path(__file__).parent.parent / "examples" / "meu-site"


def _copy_example(dest: Path) -> Path:
    """Copia o site de exemplo para `dest`, sem arrastar `build/` nem
    `.asteria-cache.json` que outros testes (que rodam direto em
    EXAMPLE_ROOT) possam ter deixado para trás."""
    import shutil

    shutil.copytree(
        EXAMPLE_ROOT, dest, ignore=shutil.ignore_patterns("build", ".asteria-cache.json")
    )
    return dest


def test_build_example_site_produces_expected_files():
    result = run_build(EXAMPLE_ROOT, converter_name="fallback")

    assert result.success
    assert len(result.pages) == 5
    assert len(result.posts) == 2

    output = result.output_dir
    assert (output / "index.html").exists()
    assert (output / "pages" / "sobre" / "index.html").exists()
    assert (output / "blog" / "primeiro-artigo" / "index.html").exists()
    assert (output / "css" / "light.css").exists()

    home_html = (output / "index.html").read_text(encoding="utf-8")
    assert "Bem-vindo" in home_html
    assert "ssg-frontmatter" not in home_html
    assert '<a href="/pages/sobre/">Sobre este projeto</a>' in home_html


def test_build_example_site_generates_blog_taxonomy_and_toc():
    result = run_build(EXAMPLE_ROOT, converter_name="fallback")
    assert result.success

    output = result.output_dir
    assert (output / "blog" / "index.html").exists()
    assert (output / "tags" / "index.html").exists()
    assert (output / "tags" / "python" / "index.html").exists()
    assert (output / "categories" / "tecnologia" / "index.html").exists()

    post_html = (output / "blog" / "primeiro-artigo" / "index.html").read_text(
        encoding="utf-8"
    )
    assert 'id="introducao"' in post_html
    assert 'id="instalacao"' in post_html
    assert "sidebar-toc" in post_html
    assert 'href="/blog/segundo-artigo/"' in post_html  # navegação "próximo"

    tag_html = (output / "tags" / "python" / "index.html").read_text(encoding="utf-8")
    assert "Meu primeiro artigo" in tag_html


def test_build_example_site_generates_seo_and_distribution_files():
    result = run_build(EXAMPLE_ROOT, converter_name="fallback")
    assert result.success

    output = result.output_dir
    assert (output / "sitemap.xml").exists()
    assert (output / "robots.txt").exists()
    assert (output / "rss.xml").exists()

    sitemap = (output / "sitemap.xml").read_text(encoding="utf-8")
    assert "<loc>https://example.com/blog/primeiro-artigo/</loc>" in sitemap
    assert "<lastmod>2026-08-10</lastmod>" in sitemap

    robots = (output / "robots.txt").read_text(encoding="utf-8")
    assert "Sitemap: https://example.com/sitemap.xml" in robots

    rss = (output / "rss.xml").read_text(encoding="utf-8")
    assert "<title>Meu primeiro artigo</title>" in rss

    post_html = (output / "blog" / "primeiro-artigo" / "index.html").read_text(
        encoding="utf-8"
    )
    assert '<link rel="canonical" href="https://example.com/blog/primeiro-artigo/">' in post_html
    assert '<meta property="og:type" content="article">' in post_html

    page_html = (output / "pages" / "sobre" / "index.html").read_text(encoding="utf-8")
    assert '<meta property="og:type" content="website">' in page_html

    assert len(result.generated_files) > 0
    assert "sitemap.xml" in result.generated_files


def test_build_example_site_copies_raw_page_verbatim_and_embeds_iframe():
    result = run_build(EXAMPLE_ROOT, converter_name="fallback")
    assert result.success

    output = result.output_dir
    raw_index = output / "pages" / "ficha-exemplo" / "index.html"
    raw_css = output / "pages" / "ficha-exemplo" / "style.css"
    assert raw_index.exists()
    assert raw_css.exists()

    source_index = EXAMPLE_ROOT / "content" / "pages" / "ficha-exemplo" / "index.html"
    source_css = EXAMPLE_ROOT / "content" / "pages" / "ficha-exemplo" / "style.css"
    assert raw_index.read_bytes() == source_index.read_bytes()
    assert raw_css.read_bytes() == source_css.read_bytes()

    # raw.yaml é metadado interno do Asteria, não deve ir pro output.
    assert not (output / "pages" / "ficha-exemplo" / "raw.yaml").exists()

    sobre_html = (output / "pages" / "sobre" / "index.html").read_text(encoding="utf-8")
    assert '<iframe src="/pages/ficha-exemplo/"' in sobre_html
    assert 'title="Ficha do Guerreiro"' in sobre_html
    assert "height:420px" in sobre_html

    sitemap = (output / "sitemap.xml").read_text(encoding="utf-8")
    assert "<loc>https://example.com/pages/ficha-exemplo/</loc>" in sitemap


def test_build_fails_with_clear_error_on_broken_reference(tmp_path: Path):
    import shutil

    project = tmp_path / "site"
    _copy_example(project)
    quebrado = project / "content" / "pages" / "inicio.odt"

    # Corrompe uma referência existente injetando uma referência inválida
    # diretamente no zip do .odt (troca 'sobre' por um id inexistente).
    import zipfile

    data = quebrado.read_bytes()
    tmp_zip = project / "content" / "pages" / "inicio2.odt"
    with zipfile.ZipFile(quebrado) as zin:
        content = zin.read("content.xml").decode("utf-8")
    content = content.replace("[[sobre]]", "[[pagina-inexistente]]")
    with zipfile.ZipFile(quebrado) as zin, zipfile.ZipFile(tmp_zip, "w") as zout:
        for item in zin.infolist():
            if item.filename == "content.xml":
                zout.writestr(item, content)
            else:
                zout.writestr(item, zin.read(item.filename))
    quebrado.unlink()
    tmp_zip.rename(quebrado)

    result = run_build(project, converter_name="fallback")

    assert not result.success
    assert any("pagina-inexistente" in e.message for e in result.diagnostics.errors)


def test_build_home_page_can_point_to_blog_index(tmp_path: Path):
    import shutil
    import yaml

    project = tmp_path / "site"
    _copy_example(project)
    config_path = project / "site.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["site"]["home_page"] = "blog"
    config_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    result = run_build(project, converter_name="fallback")

    assert result.success
    index_html = (result.output_dir / "index.html").read_text(encoding="utf-8")
    assert "<h1>Blog</h1>" in index_html


def test_build_home_page_missing_generates_warning_not_error(tmp_path: Path):
    import shutil
    import yaml

    project = tmp_path / "site"
    _copy_example(project)
    config_path = project / "site.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["site"]["home_page"] = "pagina-que-nao-existe"
    config_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    result = run_build(project, converter_name="fallback")

    assert result.success  # continua sendo apenas um warning
    assert not (result.output_dir / "index.html").exists()
    assert any(
        "pagina-que-nao-existe" in w.message for w in result.diagnostics.warnings
    )


def test_build_raw_page_id_colliding_with_page_id_errors(tmp_path: Path):
    import shutil

    project = tmp_path / "site"
    _copy_example(project)
    # 'sobre.odt' já existe em content/pages/; uma pasta 'sobre/' (sem
    # extensão) é uma entrada de diretório diferente, mas gera o mesmo id.
    raw_dir = project / "content" / "pages" / "sobre"
    raw_dir.mkdir(parents=True)
    (raw_dir / "index.html").write_text("<p>conflito</p>", encoding="utf-8")

    result = run_build(project, converter_name="fallback")

    assert not result.success
    assert any("ID duplicado" in e.message for e in result.diagnostics.errors)


def test_build_auto_adds_blog_to_menu_when_posts_exist_and_home_is_not_blog():
    # site.yaml de exemplo: home_page = 'inicio' (não 'blog') e há posts.
    result = run_build(EXAMPLE_ROOT, converter_name="fallback")
    assert result.success

    home_html = (result.output_dir / "index.html").read_text(encoding="utf-8")
    assert '<a href="/blog/">Blog</a>' in home_html


def test_build_does_not_duplicate_blog_menu_entry_if_already_present(tmp_path: Path):
    import yaml

    project = tmp_path / "site"
    _copy_example(project)
    theme_yaml_path = project / "theme" / "minimal" / "theme.yaml"
    data = yaml.safe_load(theme_yaml_path.read_text(encoding="utf-8"))
    data["menu"].append({"page": "blog", "title": "Artigos"})
    theme_yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    result = run_build(project, converter_name="fallback")
    assert result.success

    home_html = (result.output_dir / "index.html").read_text(encoding="utf-8")
    assert home_html.count('href="/blog/"') == 1
    assert '<a href="/blog/">Artigos</a>' in home_html


def test_build_does_not_add_blog_to_menu_when_home_is_blog(tmp_path: Path):
    import shutil
    import yaml

    project = tmp_path / "site"
    _copy_example(project)
    config_path = project / "site.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["site"]["home_page"] = "blog"
    config_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    result = run_build(project, converter_name="fallback")
    assert result.success

    index_html = (result.output_dir / "index.html").read_text(encoding="utf-8")
    assert '<a href="/blog/">Blog</a>' not in index_html


def test_build_toc_can_be_disabled_per_document(tmp_path: Path):
    import shutil

    from .odt_factory import frontmatter_block, h, make_odt, p

    project = tmp_path / "site"
    _copy_example(project)
    make_odt(
        project / "content" / "pages" / "sem-toc.odt",
        frontmatter_block({"title": "Sem TOC", "toc": "false"})
        + h("Primeiro título", 2)
        + p("x")
        + h("Segundo título", 2)
        + p("y"),
    )

    result = run_build(project, converter_name="fallback")
    assert result.success

    html = (result.output_dir / "pages" / "sem-toc" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "sidebar-toc" not in html


def test_build_navigation_sidebar_only_shown_when_enabled_per_document(tmp_path: Path):
    import shutil

    from .odt_factory import frontmatter_block, make_odt, p

    project = tmp_path / "site"
    _copy_example(project)
    make_odt(
        project / "content" / "pages" / "com-nav.odt",
        frontmatter_block({"title": "Com Nav", "navigation": "true"}) + p("x"),
    )
    make_odt(
        project / "content" / "pages" / "sem-nav.odt",
        frontmatter_block({"title": "Sem Nav"}) + p("y"),
    )

    result = run_build(project, converter_name="fallback")
    assert result.success

    with_nav_html = (result.output_dir / "pages" / "com-nav" / "index.html").read_text(
        encoding="utf-8"
    )
    without_nav_html = (result.output_dir / "pages" / "sem-nav" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "sidebar-nav" in with_nav_html
    assert "sidebar-nav" not in without_nav_html


def test_build_generates_404_page():
    result = run_build(EXAMPLE_ROOT, converter_name="fallback")
    assert result.success
    html = (result.output_dir / "404.html").read_text(encoding="utf-8")
    assert "404" in html
    assert "Página não encontrada" in html


def test_build_footer_shows_social_links_from_config():
    result = run_build(EXAMPLE_ROOT, converter_name="fallback")
    assert result.success
    html = (result.output_dir / "index.html").read_text(encoding="utf-8")
    assert 'class="social-link"' in html
    assert "github.com/exemplo" in html


def test_build_injects_live_reload_script_only_when_requested(tmp_path: Path):
    import shutil

    from asteria.server import LIVE_RELOAD_SCRIPT

    project_a = tmp_path / "sem-reload"
    project_b = tmp_path / "com-reload"
    _copy_example(project_a)
    _copy_example(project_b)
    for p in (project_a, project_b):
        (p / ".asteria-cache.json").unlink(missing_ok=True)

    without = run_build(project_a, converter_name="fallback")
    with_reload = run_build(
        project_b, converter_name="fallback", live_reload_script=LIVE_RELOAD_SCRIPT
    )

    home_without = (without.output_dir / "index.html").read_text(encoding="utf-8")
    home_with = (with_reload.output_dir / "index.html").read_text(encoding="utf-8")

    assert "__asteria_live_reload__" not in home_without
    assert "__asteria_live_reload__" in home_with

    # Página crua nunca recebe o script, mesmo com live reload ativo.
    raw_html = (with_reload.output_dir / "pages" / "ficha-exemplo" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "__asteria_live_reload__" not in raw_html


def test_build_reuses_cache_on_second_run(tmp_path: Path):
    import shutil

    project = tmp_path / "site"
    _copy_example(project)

    first = run_build(project, converter_name="fallback")
    second = run_build(project, converter_name="fallback")

    assert first.success and second.success
    assert first.cache_misses > 0
    assert second.cache_hits == first.cache_misses
    assert second.cache_misses == 0
    assert (project / ".asteria-cache.json").exists()


def test_build_cache_invalidates_when_file_changes(tmp_path: Path):
    import shutil

    project = tmp_path / "site"
    _copy_example(project)

    run_build(project, converter_name="fallback")

    import os
    import time

    target = project / "content" / "pages" / "sobre.odt"
    time.sleep(0.01)
    data = target.read_bytes()
    target.write_bytes(data)
    os.utime(target, None)

    second = run_build(project, converter_name="fallback")
    assert second.cache_misses == 1


def test_check_dry_run_does_not_touch_cache_file(tmp_path: Path):
    import shutil

    project = tmp_path / "site"
    _copy_example(project)
    (project / ".asteria-cache.json").unlink(missing_ok=True)

    run_build(project, converter_name="fallback", dry_run=True)

    assert not (project / ".asteria-cache.json").exists()


def test_build_renders_custom_extra_key_from_site_yaml():
    result = run_build(EXAMPLE_ROOT, converter_name="fallback")
    assert result.success
    home_html = (result.output_dir / "index.html").read_text(encoding="utf-8")
    assert "Feito inteiramente a partir de documentos ODT" in home_html


def test_build_global_default_variant_applies_to_all_pages_without_override(tmp_path: Path):
    import yaml

    project = tmp_path / "site"
    _copy_example(project)
    theme_yaml_path = project / "theme" / "minimal" / "theme.yaml"
    data = yaml.safe_load(theme_yaml_path.read_text(encoding="utf-8"))
    data["default_variant"] = "dark"
    theme_yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    result = run_build(project, converter_name="fallback")
    assert result.success

    sobre_html = (result.output_dir / "pages" / "sobre" / "index.html").read_text(
        encoding="utf-8"
    )
    contato_html = (result.output_dir / "pages" / "contato" / "index.html").read_text(
        encoding="utf-8"
    )
    # 'sobre' não tem variant próprio -> usa o padrão global (dark).
    assert '<link rel="stylesheet" href="/css/dark.css">' in sobre_html
    # 'contato' já pedia variant: dark explicitamente -> continua dark.
    assert '<link rel="stylesheet" href="/css/dark.css">' in contato_html


def test_build_per_document_variant_overrides_global_default(tmp_path: Path):
    import shutil

    from .odt_factory import frontmatter_block, make_odt, p

    project = tmp_path / "site"
    _copy_example(project)
    make_odt(
        project / "content" / "pages" / "clara.odt",
        frontmatter_block({"title": "Clara", "variant": "light"}) + p("x"),
    )

    import yaml

    config_path = project / "site.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["theme"]["default_variant"] = "dark"
    config_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    result = run_build(project, converter_name="fallback")
    assert result.success

    clara_html = (result.output_dir / "pages" / "clara" / "index.html").read_text(
        encoding="utf-8"
    )
    assert '<link rel="stylesheet" href="/css/light.css">' in clara_html


def test_build_with_terminal_theme_succeeds(tmp_path: Path):
    import yaml

    project = tmp_path / "site"
    _copy_example(project)
    config_path = project / "site.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["theme"]["name"] = "terminal"
    config_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    result = run_build(project, converter_name="fallback")

    assert result.success
    home_html = (result.output_dir / "index.html").read_text(encoding="utf-8")
    assert 'href="/css/light.css"' in home_html
    assert "window-chrome" in home_html
    assert (result.output_dir / "css" / "light.css").exists()
    assert (result.output_dir / "css" / "dark.css").exists()


def test_build_with_terminal_theme_dark_variant(tmp_path: Path):
    import shutil

    import yaml

    project = tmp_path / "site"
    _copy_example(project)

    # Copia o tema terminal (embutido no pacote) pra dentro do projeto,
    # pra poder editar o theme.yaml dele (default_variant).
    bundled_terminal = Path(__file__).parent.parent / "asteria" / "themes" / "terminal"
    project_terminal = project / "theme" / "terminal"
    shutil.copytree(bundled_terminal, project_terminal)

    theme_yaml_path = project_terminal / "theme.yaml"
    theme_data = yaml.safe_load(theme_yaml_path.read_text(encoding="utf-8"))
    theme_data["default_variant"] = "dark"
    theme_yaml_path.write_text(yaml.safe_dump(theme_data, allow_unicode=True), encoding="utf-8")

    config_path = project / "site.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["theme"]["name"] = "terminal"
    config_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    result = run_build(project, converter_name="fallback")

    assert result.success
    home_html = (result.output_dir / "index.html").read_text(encoding="utf-8")
    assert 'href="/css/dark.css"' in home_html


def test_build_breaks_loudly_on_undeclared_theme_key(tmp_path: Path):
    """Regressão: uma chave usada num template do tema e não declarada no
    theme.yaml correspondente deve quebrar o build com um erro claro
    (Jinja StrictUndefined) — nunca falhar silenciosamente."""
    project = tmp_path / "site"
    _copy_example(project)

    base_html = project / "theme" / "minimal" / "base.html"
    content = base_html.read_text(encoding="utf-8")
    assert "<p>&copy; {{ site.title }}</p>" in content
    content = content.replace(
        "<p>&copy; {{ site.title }}</p>",
        "<p>&copy; {{ site.title }} {{ theme.chave_nao_declarada }}</p>",
    )
    base_html.write_text(content, encoding="utf-8")

    with pytest.raises(Exception):
        run_build(project, converter_name="fallback")


def test_build_theme_yaml_menu_nav_social_all_resolve_correctly():
    """Confirma que theme.yaml (não site.yaml) é a fonte de menu/nav/social
    depois da migração de namespace."""
    result = run_build(EXAMPLE_ROOT, converter_name="fallback")
    assert result.success

    home_html = (result.output_dir / "index.html").read_text(encoding="utf-8")
    assert '<a href="/pages/sobre/">Sobre</a>' in home_html  # menu
    assert "social-link" in home_html  # social

    instalacao_html = (result.output_dir / "pages" / "instalacao" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "sidebar-nav" in instalacao_html  # nav (navigation: true nessa página)
