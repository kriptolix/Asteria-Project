from asteria.toc import inject_heading_ids_and_build_toc


def test_toc_builds_nested_tree_and_injects_ids():
    html = (
        "<h2>Introdução</h2><p>x</p>"
        "<h2>Instalação</h2><p>y</p>"
        "<h3>Linux</h3><p>z</p>"
        "<h3>Windows</h3><p>w</p>"
        "<h2>Conclusão</h2>"
    )
    new_html, tree = inject_heading_ids_and_build_toc(html)

    assert 'id="introducao"' in new_html
    assert 'id="instalacao"' in new_html
    assert 'id="linux"' in new_html

    assert [e.title for e in tree] == ["Introdução", "Instalação", "Conclusão"]
    instalacao = tree[1]
    assert [c.title for c in instalacao.children] == ["Linux", "Windows"]


def test_toc_resolves_id_collisions():
    html = "<h2>Introdução</h2><h2>Introdução</h2>"
    new_html, tree = inject_heading_ids_and_build_toc(html)

    assert 'id="introducao"' in new_html
    assert 'id="introducao-2"' in new_html
    assert tree[0].id == "introducao"
    assert tree[1].id == "introducao-2"


def test_toc_empty_html_returns_empty_tree():
    new_html, tree = inject_heading_ids_and_build_toc("<p>sem títulos</p>")
    assert tree == []
    assert new_html == "<p>sem títulos</p>"
