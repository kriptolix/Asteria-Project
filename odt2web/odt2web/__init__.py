"""odt2web - biblioteca Python para converter documentos ODT em HTML/CSS.

API minima:

    from odt2web import convert

    result = convert("artigo.odt")
    print(result.html)
    print(result.css)
"""
from __future__ import annotations

from .assets import extract_assets
from .codeblocks import merge_code_blocks
from .css import generate_css
from .extensibility import get_default_renderers, register_renderer, unregister_renderer
from .metadata import parse_metadata
from .model import Document, Metadata
from .parser import parse_document
from .reader import InvalidOdtError, OdtPackage, read_odt_bytes, read_odt_file
from .renderer import render_document, wrap_full_document
from .result import Asset, ConversionResult, Warning, WarningLevel

__all__ = [
    "convert",
    "convert_bytes",
    "check",
    "ConversionResult",
    "Asset",
    "Metadata",
    "Warning",
    "WarningLevel",
    "InvalidOdtError",
    "register_renderer",
    "unregister_renderer",
]

__version__ = "0.1.0"


def _disable_columns(document: Document) -> None:
    for section in document.sections:
        section.columns = 1
        section.column_gap = None
        section.column_rule = None


def _build_result(
    package: OdtPackage,
    *,
    css: bool = True,
    extract_images: bool = True,
    assets_dir: str = "assets",
    document: bool = False,
    style_map: dict | None = None,
    custom_renderers: dict | None = None,
    disable_columns: bool = False,
    allow_raw_html: bool = False,
) -> ConversionResult:
    doc_model = parse_document(package)
    doc_model.metadata = parse_metadata(package.meta_xml, package.content_xml)

    if disable_columns:
        _disable_columns(doc_model)

    merge_code_blocks(doc_model.sections, style_map or {})

    if extract_images:
        assets = extract_assets(doc_model, package, assets_dir=assets_dir)
    else:
        assets = []
        doc_model.warnings.append(
            "extract_images=False: imagens nao foram extraidas; os caminhos "
            "originais do pacote ODT foram preservados no HTML e podem nao "
            "resolver corretamente"
        )

    renderers = get_default_renderers()
    if custom_renderers:
        renderers.update(custom_renderers)

    body_html, render_ctx = render_document(
        doc_model, style_map=style_map or {}, custom_renderers=renderers,
        allow_raw_html=allow_raw_html,
    )

    css_text = generate_css(render_ctx) if css else None

    if document:
        html = wrap_full_document(body_html, css_text, doc_model.metadata)
    else:
        html = body_html

    warnings = [Warning(message=w, level=WarningLevel.WARNING, source="parser")
                for w in doc_model.warnings]
    warnings += [Warning(message=w, level=WarningLevel.WARNING, source="renderer")
                 for w in render_ctx.warnings]

    return ConversionResult(
        html=html,
        css=css_text,
        assets=assets,
        metadata=doc_model.metadata,
        front_matter=doc_model.front_matter,
        warnings=warnings,
    )


# valores padrao "reais" da biblioteca, aplicados somente depois que
# argumentos explicitos e config YAML ja foram considerados (permite que
# o config sobrescreva o default quando o chamador nao passa o argumento).
_LIBRARY_DEFAULTS = dict(
    css=True, extract_images=True, assets_dir="assets", document=False,
    allow_raw_html=False,
)


def _merge_options(*, css, extract_images, assets_dir, document, style_map,
                    custom_renderers, allow_raw_html, config) -> tuple[dict, bool]:
    from .config import config_to_options, load_config

    # so entram no dict os argumentos que o chamador de fato passou
    # (diferentes do sentinel None); os demais ficam para o config/defaults.
    explicit = {
        "css": css, "extract_images": extract_images, "assets_dir": assets_dir,
        "document": document, "allow_raw_html": allow_raw_html,
    }
    options: dict = {k: v for k, v in explicit.items() if v is not None}
    if style_map is not None:
        options["style_map"] = style_map
    if custom_renderers is not None:
        options["custom_renderers"] = custom_renderers

    disable_columns = False
    if config:
        file_options = config_to_options(load_config(config))
        for key, value in file_options.items():
            if key == "style_map":
                merged = dict(value)
                merged.update(style_map or {})
                options["style_map"] = merged
            elif key == "disable_columns":
                disable_columns = value
            elif key not in options:
                options[key] = value

    for key, default in _LIBRARY_DEFAULTS.items():
        options.setdefault(key, default)

    return options, disable_columns


def convert(
    path: str,
    *,
    output_dir: str | None = None,
    css: bool | None = None,
    extract_images: bool | None = None,
    assets_dir: str | None = None,
    document: bool | None = None,
    style_map: dict | None = None,
    custom_renderers: dict | None = None,
    allow_raw_html: bool | None = None,
    config: str | None = None,
) -> ConversionResult:
    """Converte um arquivo .odt em HTML/CSS.

    Args:
        path: caminho para o arquivo .odt.
        output_dir: se informado, grava index.html/style.css/assets neste
            diretorio (secao 10).
        css: gera CSS automaticamente (secao 9). Default True.
        extract_images: extrai imagens incorporadas para arquivos
            separados (secao 10). Default True.
        assets_dir: subdiretorio (relativo ao HTML) para os assets.
            Default "assets".
        document: se True, produz um documento HTML completo
            (doctype/html/head/body); se False (default), produz apenas o
            fragmento, pensado para integracao com SSGs (secao 12).
        style_map: mapeamento de estilos ODT -> HTML (secoes 6 e 7).
        custom_renderers: renderers adicionais por chamada, alem dos
            registrados globalmente via @register_renderer (secao 17).
        allow_raw_html: se True, blocos ':::html' ... ':::' no documento
            sao emitidos como HTML literal, sem escaping (ver
            odt2web.rawhtml). Default False - o .odt e' tratado como
            entrada nao confiavel por padrao (secao 13); so habilite para
            documentos de autores em quem voce confia.
        config: caminho para um arquivo YAML de configuracao (secao 16).
            Argumentos explicitos passados nesta chamada tem prioridade
            sobre o arquivo; o arquivo tem prioridade sobre os defaults.
    """
    options, disable_columns = _merge_options(
        css=css, extract_images=extract_images, assets_dir=assets_dir,
        document=document, style_map=style_map, custom_renderers=custom_renderers,
        allow_raw_html=allow_raw_html, config=config,
    )
    package = read_odt_file(path)
    result = _build_result(package, disable_columns=disable_columns, **options)
    if output_dir:
        result.write(output_dir)
    return result


def convert_bytes(
    data: bytes,
    *,
    css: bool | None = None,
    extract_images: bool | None = None,
    assets_dir: str | None = None,
    document: bool | None = None,
    style_map: dict | None = None,
    custom_renderers: dict | None = None,
    allow_raw_html: bool | None = None,
    config: str | None = None,
) -> ConversionResult:
    """Igual a convert(), mas a partir de bytes em memoria (secao 2)."""
    options, disable_columns = _merge_options(
        css=css, extract_images=extract_images, assets_dir=assets_dir,
        document=document, style_map=style_map, custom_renderers=custom_renderers,
        allow_raw_html=allow_raw_html, config=config,
    )
    package = read_odt_bytes(data)
    return _build_result(package, disable_columns=disable_columns, **options)


def check(path: str) -> list[Warning]:
    """Valida um documento .odt sem gerar HTML (secao 15, `--check`).

    Levanta InvalidOdtError se o pacote nao puder ser lido. Retorna a
    lista de avisos encontrados durante o parsing (documento ainda
    valido, mas com recursos parcialmente suportados, por exemplo)."""
    package = read_odt_file(path)
    doc_model = parse_document(package)
    return [Warning(message=w, level=WarningLevel.WARNING, source="parser")
            for w in doc_model.warnings]
