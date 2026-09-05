from asteria.errors import Diagnostics
from asteria.nav import build_nav


class _Target:
    def __init__(self, title, url):
        self.title = title
        self.url = url


def _registry():
    return {
        "inicio": _Target("Início", "/pages/inicio/"),
        "sobre": _Target("Sobre nós", "/pages/sobre/"),
        "instalacao": _Target("Instalação", "/pages/instalacao/"),
        "configuracao": _Target("Configuração", "/pages/configuracao/"),
        "personagens": _Target("Personagens", "/pages/personagens/"),
        "arquetipos": _Target("Arquétipos", "/pages/arquetipos/"),
        "o-cientista": _Target("O Cientista", "/pages/o-cientista/"),
        "aspectos": _Target("Aspectos", "/pages/aspectos/"),
    }


def test_bare_string_uses_document_title():
    diagnostics = Diagnostics()
    nav = build_nav(["inicio"], _registry(), diagnostics)

    assert len(nav) == 1
    assert nav[0].title == "Início"  # veio do documento, não do nav:
    assert nav[0].url == "/pages/inicio/"
    assert not diagnostics.has_errors


def test_single_key_mapping_overrides_title():
    diagnostics = Diagnostics()
    nav = build_nav([{"Página Inicial": "inicio"}], _registry(), diagnostics)

    assert nav[0].title == "Página Inicial"
    assert nav[0].url == "/pages/inicio/"


def test_section_with_list_value_has_no_own_link_by_default():
    diagnostics = Diagnostics()
    nav = build_nav(
        [{"Guia": [{"Instalação": "instalacao"}, "configuracao"]}],
        _registry(),
        diagnostics,
    )

    section = nav[0]
    assert section.title == "Guia"
    assert section.url is None
    assert len(section.children) == 2
    assert section.children[0].title == "Instalação"
    assert section.children[1].title == "Configuração"  # título do doc


def test_section_index_page_convention_first_bare_child():
    """Primeiro filho solto (string) vira o link do título da seção e some
    da listagem de filhos — convenção equivalente ao index.md do MkDocs.
    Aplica-se em qualquer nível de aninhamento, inclusive subseções."""
    diagnostics = Diagnostics()
    nav = build_nav(
        [
            {
                "Personagens": [
                    "personagens",
                    {"Arquétipos": ["arquetipos", "o-cientista"]},
                    "aspectos",
                ]
            }
        ],
        _registry(),
        diagnostics,
    )

    section = nav[0]
    assert section.title == "Personagens"
    assert section.url == "/pages/personagens/"  # veio do primeiro filho solto
    # 'personagens' não deve aparecer duplicado na listagem de filhos.
    child_titles = [c.title for c in section.children]
    assert "Personagens" not in child_titles
    assert child_titles == ["Arquétipos", "Aspectos"]

    subsection = section.children[0]
    assert subsection.title == "Arquétipos"
    # A convenção também vale para a subseção: seu primeiro filho solto
    # ('arquetipos') vira o link do próprio título "Arquétipos".
    assert subsection.url == "/pages/arquetipos/"
    assert [c.title for c in subsection.children] == ["O Cientista"]


def test_nested_sections_arbitrary_depth():
    diagnostics = Diagnostics()
    nav = build_nav(
        [{"A": [{"B": [{"C": ["inicio"]}]}]}],
        _registry(),
        diagnostics,
    )
    section_c = nav[0].children[0].children[0]
    assert section_c.title == "C"
    # único filho ('inicio') é solto -> vira o link do próprio "C".
    assert section_c.url == "/pages/inicio/"
    assert section_c.children == []


def test_missing_id_warns_and_keeps_placeholder():
    diagnostics = Diagnostics()
    nav = build_nav(["nao-existe"], _registry(), diagnostics)

    assert nav[0].url is None
    assert nav[0].title == "nao-existe"
    assert diagnostics.warnings
    assert "nao-existe" in diagnostics.warnings[0].message


def test_malformed_item_warns_and_is_skipped():
    diagnostics = Diagnostics()
    nav = build_nav([{"a": "inicio", "b": "sobre"}], _registry(), diagnostics)

    assert nav == []
    assert diagnostics.warnings


def test_empty_nav_config_returns_empty_list():
    diagnostics = Diagnostics()
    assert build_nav([], {}, diagnostics) == []
    assert build_nav(None, {}, diagnostics) == []
