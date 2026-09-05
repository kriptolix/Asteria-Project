from asteria.cli import build_parser


def test_check_command_parses_converter_flag():
    parser = build_parser()
    args = parser.parse_args(["check", "--converter", "odt2web"])
    assert args.command == "check"
    assert args.converter == "odt2web"


def test_check_command_default_converter_is_auto():
    parser = build_parser()
    args = parser.parse_args(["check"])
    assert args.converter == "auto"


def test_serve_command_defaults():
    parser = build_parser()
    args = parser.parse_args(["serve"])
    assert args.host == "127.0.0.1"
    assert args.port == 8000
    assert args.no_watch is False
    assert args.converter == "auto"


def test_serve_command_custom_host_port_and_no_watch():
    parser = build_parser()
    args = parser.parse_args(
        ["serve", "--host", "0.0.0.0", "--port", "9999", "--no-watch"]
    )
    assert args.host == "0.0.0.0"
    assert args.port == 9999
    assert args.no_watch is True


def test_project_flag_available_on_all_subcommands():
    parser = build_parser()
    for cmd in ("build", "clean", "serve", "check"):
        args = parser.parse_args(["--project", "/tmp/algum-site", cmd])
        assert args.project == "/tmp/algum-site"


def test_new_command_parses_path_and_title():
    parser = build_parser()
    args = parser.parse_args(["new", "/tmp/meu-projeto", "--title", "Título X"])
    assert args.command == "new"
    assert args.path == "/tmp/meu-projeto"
    assert args.title == "Título X"


def test_new_command_default_title():
    parser = build_parser()
    args = parser.parse_args(["new", "/tmp/meu-projeto"])
    assert args.title == "Meu Site"


def test_clean_command_cache_flag_default_false():
    parser = build_parser()
    args = parser.parse_args(["clean"])
    assert args.cache is False


def test_clean_command_cache_flag_enabled():
    parser = build_parser()
    args = parser.parse_args(["clean", "--cache"])
    assert args.cache is True
