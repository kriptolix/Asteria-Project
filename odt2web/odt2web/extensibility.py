"""Extensibilidade (secao 17 da especificacao).

Permite registrar renderers para elementos especificos sem modificar o
parser. Um estilo ODT pode ser mapeado, via style_map, para um "tag"
com prefixo "custom:" (ex: {"tag": "custom:note"}); quando o renderer
encontra esse prefixo, delega para a funcao registrada aqui em vez de
gerar uma tag HTML padrao.

Exemplo:

    from odt2web import register_renderer

    @register_renderer("custom:note")
    def render_note(node, context):
        return f"<div class='note'>...</div>"

    style_map = {"Warning": {"tag": "custom:note"}}
"""
from __future__ import annotations

from typing import Callable, Protocol


class RendererProtocol(Protocol):
    def __call__(self, node, context) -> str: ...


_REGISTRY: dict[str, RendererProtocol] = {}


def register_renderer(name: str) -> Callable[[RendererProtocol], RendererProtocol]:
    """Decorator que registra um renderer customizado global sob `name`
    (ex: 'custom:note'). Pode tambem ser usado como funcao comum:
    register_renderer("custom:note")(minha_funcao).
    """

    def decorator(func: RendererProtocol) -> RendererProtocol:
        _REGISTRY[name] = func
        return func

    return decorator


def unregister_renderer(name: str) -> None:
    _REGISTRY.pop(name, None)


def get_default_renderers() -> dict[str, RendererProtocol]:
    """Retorna uma copia do registro global, usada por padrao pelo
    convert()/convert_bytes() quando o chamador nao passa custom_renderers
    explicitamente."""
    return dict(_REGISTRY)


def clear_registry() -> None:
    """Util em testes, para nao vazar registros entre execucoes."""
    _REGISTRY.clear()
