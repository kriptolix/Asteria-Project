"""Configuração própria do tema (`theme/<nome>/theme.yaml`).

Dois namespaces distintos são expostos aos templates:

- `site.*`: configurações do SSG — estrutura fixa, sempre presente,
  com defaults sensatos (ver `asteria.config.SiteConfig`). Fatos sobre o
  site que não mudam com a troca de tema (URL, idioma, diretórios).
- `theme.*`: namespace livre do tema, lido de `theme/<nome>/theme.yaml`
  — cada chave que o arquivo define vira `theme.<chave>` nos templates
  (menu, nav, social, e qualquer chave customizada que o tema use, tipo
  um subtítulo). **Sem fallback silencioso**: o ambiente Jinja do Asteria
  usa `StrictUndefined`, então um template que referencia `theme.algo`
  não declarado em `theme.yaml` quebra o build com um erro claro — cabe
  ao autor do tema declarar em `theme.yaml` toda chave que seus próprios
  templates usam (mesmo que com um valor vazio/padrão), em vez de deixar
  o template assumir silenciosamente que ela existe.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .errors import AsteriaError


def load_theme_config(theme_dir: Path) -> dict[str, Any]:
    """Lê `theme.yaml` de dentro da pasta do tema (`theme_dir`, já
    resolvida — projeto ou embutida no pacote, ver `SiteConfig.theme_dir`).
    Arquivo ausente vira um namespace vazio (tema sem configuração
    própria) — mas isso é diferente de uma chave especificamente ausente
    *dentro* do arquivo: essa segunda situação é responsabilidade do
    Jinja (`StrictUndefined`) detectar quando o template a usa, não deste
    carregador.
    """
    path = theme_dir / "theme.yaml"
    if not path.exists():
        return {}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise AsteriaError(f"YAML inválido em {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise AsteriaError(f"O conteúdo de {path} deve ser um mapeamento YAML.")

    return data
