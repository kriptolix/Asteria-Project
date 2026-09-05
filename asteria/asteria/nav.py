"""Navegação hierárquica configurável — formato inspirado no `nav:` do
MkDocs Material (comportamento verificado como referência).

No MkDocs, cada item de `nav:` é:

- uma string solta (`- index.md`) → um link cujo título vem do próprio
  arquivo (H1/front matter), não de um nome escrito no `nav:`;
- um mapeamento de uma chave (`- Título: caminho.md`) → um link com título
  explícito;
- um mapeamento cujo valor é uma lista (`- Título: [...]`) → uma **seção**
  (o "Título" é só um rótulo de agrupamento, não necessariamente um link).

O Asteria segue exatamente esse mesmo formato YAML, só trocando "caminho de
arquivo" por **`id`** (mesma convenção de `[[id]]`), já que documentos no
Asteria são endereçados por id, não por caminho:

    nav:
      - inicio                       # título vem do próprio documento
      - Início: inicio                 # título explícito
      - Sob um Céu Estranho:
          - sob-um-ceu-estranho         # ↓ ver "página-índice de seção" abaixo
          - basico
          - Nave:
              - nave
          - Personagens:
              - personagens              # também vira a página-índice de "Personagens"
              - Arquétipos:
                  - arquetipos
                  - o-cientista
              - aspectos

**Página-índice de seção**: no MkDocs, uma seção "ganha" um link próprio
quando o primeiro item dos seus filhos é o `index.md` da mesma pasta. Sem
pastas por documento no Asteria, a convenção equivalente é posicional: se o
**primeiro item** dentro de uma seção for uma string solta (um id, não uma
subseção), esse id vira o link do próprio título da seção — o item some da
listagem de filhos (o título já aponta pra ele) exatamente como o MkDocs
faz com `index.md`. Para uma seção **sem** página própria (só um
agrupamento), simplesmente não coloque um id solto como primeiro filho.

Cada seção é renderizada como um elemento colapsável (`<details>`); o ramo
que contém a página atual abre automaticamente, os demais começam
fechados — não há necessidade de configurar isso manualmente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import Diagnostics


@dataclass
class NavEntry:
    title: str
    url: str | None = None
    children: list["NavEntry"] = field(default_factory=list)


def _resolve(
    page_id: str, title_override: str | None, registry: dict[str, Any], diagnostics: Diagnostics
) -> NavEntry:
    target = registry.get(page_id)
    if target is None:
        diagnostics.warning(
            f"nav: item referencia id inexistente: '{page_id}'.", source="site.yaml"
        )
        return NavEntry(title=title_override or page_id, url=None)
    return NavEntry(title=title_override or target.title, url=target.url)


def _resolve_url_only(
    page_id: str, registry: dict[str, Any], diagnostics: Diagnostics
) -> str | None:
    target = registry.get(page_id)
    if target is None:
        diagnostics.warning(
            f"nav: item referencia id inexistente: '{page_id}'.", source="site.yaml"
        )
        return None
    return target.url


def _parse_items(
    items: list[Any], registry: dict[str, Any], diagnostics: Diagnostics
) -> list[NavEntry]:
    result: list[NavEntry] = []

    for raw in items:
        if isinstance(raw, str):
            result.append(_resolve(raw, None, registry, diagnostics))
            continue

        if not isinstance(raw, dict) or len(raw) != 1:
            diagnostics.warning(
                f"nav: item mal formado, ignorado: {raw!r}", source="site.yaml"
            )
            continue

        (title, value), = raw.items()

        if isinstance(value, str):
            result.append(_resolve(value, title, registry, diagnostics))
        elif isinstance(value, list):
            children_raw = list(value)
            own_url: str | None = None

            # Convenção de "página-índice de seção": primeiro filho solto
            # (string) vira o link do título da seção, e some da listagem.
            if children_raw and isinstance(children_raw[0], str):
                own_url = _resolve_url_only(children_raw[0], registry, diagnostics)
                children_raw = children_raw[1:]

            children = _parse_items(children_raw, registry, diagnostics)
            result.append(NavEntry(title=title, url=own_url, children=children))
        else:
            diagnostics.warning(
                f"nav: valor inválido para '{title}' (esperado id ou lista).",
                source="site.yaml",
            )

    return result


def build_nav(
    nav_config: list[Any], registry: dict[str, Any], diagnostics: Diagnostics
) -> list[NavEntry]:
    return _parse_items(nav_config or [], registry, diagnostics)
