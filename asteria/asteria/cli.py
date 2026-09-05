"""CLI do Asteria (spec seção 23).

Todos os comandos previstos na spec estão implementados: `build`, `clean`,
`serve`, `check` e `new`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import run_build
from .cache import clear_cache
from .config import load_config
from .errors import AsteriaError
from .scaffold import create_project
from .server import serve as run_serve
from .writer import clean_output


def _cmd_build(args: argparse.Namespace) -> int:
    project_root = Path(args.project).resolve()
    try:
        result = run_build(project_root, converter_name=args.converter)
    except AsteriaError as exc:
        print(f"ERRO FATAL: {exc}", file=sys.stderr)
        return 1

    for diag in result.diagnostics:
        print(diag)

    if not result.success:
        print(
            f"\nBuild falhou: {len(result.diagnostics.errors)} erro(s), "
            f"{len(result.diagnostics.warnings)} aviso(s).",
            file=sys.stderr,
        )
        return 1

    print(
        f"\nBuild concluído: {len(result.pages)} página(s), {len(result.posts)} post(s), "
        f"{len(result.generated_files)} arquivo(s) gerado(s), "
        f"{len(result.diagnostics.warnings)} aviso(s) -> {result.output_dir}"
    )
    return 0


def _cmd_clean(args: argparse.Namespace) -> int:
    project_root = Path(args.project).resolve()
    config = load_config(project_root / "site.yaml")
    clean_output(config)
    print(f"Diretório de saída removido: {config.output_dir}")
    if args.cache:
        if clear_cache(project_root):
            print("Cache de conversão incremental removido.")
        else:
            print("Não havia cache de conversão para remover.")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    project_root = Path(args.project).resolve()
    return run_serve(
        project_root,
        host=args.host,
        port=args.port,
        converter_name=args.converter,
        watch=not args.no_watch,
    )


def _cmd_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project).resolve()
    try:
        result = run_build(project_root, converter_name=args.converter, dry_run=True)
    except AsteriaError as exc:
        print(f"ERRO FATAL: {exc}", file=sys.stderr)
        return 1

    for diag in result.diagnostics:
        print(diag)

    if not result.success:
        print(
            f"\nValidação falhou: {len(result.diagnostics.errors)} erro(s), "
            f"{len(result.diagnostics.warnings)} aviso(s).",
            file=sys.stderr,
        )
        return 1

    print(
        f"\nValidação ok: {len(result.pages)} página(s), {len(result.posts)} post(s), "
        f"{len(result.diagnostics.warnings)} aviso(s). Nenhum arquivo foi escrito "
        "(use 'asteria build' para gerar o site)."
    )
    return 0


def _cmd_new(args: argparse.Namespace) -> int:
    target_dir = Path(args.path).resolve()
    try:
        created = create_project(target_dir, title=args.title)
    except AsteriaError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    print(f"Projeto criado em {target_dir}\n")
    for relative in created:
        print(f"  {relative}")
    print(
        f"\nPróximos passos:\n  cd {args.path}\n  asteria serve\n"
        "\nA página inicial (content/pages/bem-vindo.odt) explica o "
        "básico — abra-a no LibreOffice Writer para editar."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asteria", description="SSG baseado em ODT")
    parser.add_argument(
        "--project",
        default=".",
        help="Diretório raiz do projeto (onde está site.yaml). Padrão: diretório atual.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    converter_choices = ["auto", "odt2web"]
    converter_help = "Conversor ODT→HTML a usar. 'auto' e 'odt2web' são equivalentes hoje."

    build_p = subparsers.add_parser("build", help="Gera o site")
    build_p.add_argument("--converter", default="auto", choices=converter_choices, help=converter_help)
    build_p.set_defaults(func=_cmd_build)

    clean_p = subparsers.add_parser("clean", help="Remove os arquivos gerados")
    clean_p.add_argument(
        "--cache",
        action="store_true",
        help="Também remove o cache de conversão incremental (.asteria-cache.json).",
    )
    clean_p.set_defaults(func=_cmd_clean)

    serve_p = subparsers.add_parser("serve", help="Gera o site e serve localmente")
    serve_p.add_argument("--host", default="127.0.0.1", help="Endereço para servir. Padrão: 127.0.0.1.")
    serve_p.add_argument("--port", type=int, default=8000, help="Porta para servir. Padrão: 8000.")
    serve_p.add_argument("--converter", default="auto", choices=converter_choices, help=converter_help)
    serve_p.add_argument(
        "--no-watch",
        action="store_true",
        help="Não observar mudanças em content/static/theme/site.yaml (sem rebuild automático).",
    )
    serve_p.set_defaults(func=_cmd_serve)

    check_p = subparsers.add_parser(
        "check", help="Valida o projeto (YAML, ODT, IDs, referências) sem gerar o site"
    )
    check_p.add_argument("--converter", default="auto", choices=converter_choices, help=converter_help)
    check_p.set_defaults(func=_cmd_check)

    new_p = subparsers.add_parser("new", help="Cria um novo projeto Asteria")
    new_p.add_argument("path", help="Diretório onde criar o projeto (criado se não existir).")
    new_p.add_argument("--title", default="Meu Site", help="Título do site. Padrão: 'Meu Site'.")
    new_p.set_defaults(func=_cmd_new)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
