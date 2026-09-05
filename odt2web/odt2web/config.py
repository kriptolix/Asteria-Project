"""Configuracao via YAML (secao 16 da especificacao, adaptada de TOML
para YAML).

Exemplo de arquivo aceito:

    output:
      document: false
      css: true
      assets: assets
      allow_raw_html: false

    columns:
      enabled: true

    styles:
      Title: h1
      Heading 1: h2
      Heading 2: h3
      Quotation: blockquote
      Lead:
        tag: p
        class: lead
"""
from __future__ import annotations

import yaml


class ConfigError(Exception):
    pass


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise ConfigError(f"Erro ao ler config YAML '{path}': {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(
            f"Config YAML '{path}' deve ter um mapeamento na raiz "
            f"(ex: 'output:', 'styles:'), nao {type(data).__name__}"
        )
    return data


def config_to_options(data: dict) -> dict:
    """Converte a estrutura YAML em um dicionario de kwargs compativel com
    a assinatura de convert()/convert_bytes()."""
    options: dict = {}

    output = data.get("output") or {}
    if "document" in output:
        options["document"] = bool(output["document"])
    if "css" in output:
        options["css"] = bool(output["css"])
    if "assets" in output:
        options["assets_dir"] = str(output["assets"])
    if "allow_raw_html" in output:
        options["allow_raw_html"] = bool(output["allow_raw_html"])
    if "extract_images" in output:
        options["extract_images"] = bool(output["extract_images"])

    columns = data.get("columns") or {}
    if "enabled" in columns and not columns["enabled"]:
        # desabilita deteccao de colunas forcando 1 coluna em todas as secoes
        options["disable_columns"] = True

    styles = data.get("styles")
    if styles:
        options["style_map"] = dict(styles)

    return options
