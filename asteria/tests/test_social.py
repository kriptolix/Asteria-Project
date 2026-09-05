from asteria.social import build_social_links


def test_known_platform_gets_label_and_monogram():
    links = build_social_links([{"platform": "github", "url": "https://github.com/x"}])

    assert len(links) == 1
    assert links[0].platform == "github"
    assert links[0].label == "GitHub"
    assert "Gh" in links[0].svg
    assert "<svg" in links[0].svg


def test_unknown_platform_falls_back_to_generic_monogram():
    links = build_social_links([{"platform": "minharede", "url": "https://x.example"}])

    assert links[0].label == "Minharede"
    assert links[0].svg  # ainda gera um ícone válido


def test_custom_label_overrides_default():
    links = build_social_links(
        [{"platform": "github", "url": "https://github.com/x", "label": "Meu GitHub"}]
    )
    assert links[0].label == "Meu GitHub"


def test_entry_without_url_is_skipped():
    assert build_social_links([{"platform": "github"}]) == []


def test_no_social_config_returns_empty_list():
    assert build_social_links([]) == []
