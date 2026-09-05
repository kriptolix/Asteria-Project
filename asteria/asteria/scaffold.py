"""Scaffold de projeto novo (`asteria new`).

Cria a estrutura mínima de um site Asteria: `site.yaml`, `content/pages/`
e `content/posts/` vazios (prontos pra receber `.odt`), `static/`, uma
cópia do tema embutido em `theme/minimal/` (para o usuário poder
customizar sem afetar o tema padrão do pacote), `.gitignore`, e uma
página inicial de boas-vindas já em `.odt`, explicando o básico de como
usar o Asteria.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .errors import AsteriaError
from .odt_builder import OdtDocument

_SITE_YAML_TEMPLATE = """\
site:
  title: "{title}"
  description: ""
  url: "http://localhost:8000"
  language: "pt-BR"
  home_page: "bem-vindo"

# Menu, navegação, links sociais e outras configurações de apresentação
# ficam em theme/minimal/theme.yaml (namespace próprio do tema) — não
# aqui. Mais opções deste arquivo (feeds, taxonomias, urls, etc.) têm
# valores padrão razoáveis e não precisam ser configuradas agora — veja o
# README do Asteria ou examples/meu-site para exemplos completos.
"""

_THEME_YAML_MENU_LINE = "menu: []"
_THEME_YAML_MENU_REPLACEMENT = """\
menu:
  - page: "bem-vindo"
    title: "Início"\
"""

_GITIGNORE = """\
build/
.asteria-cache.json
__pycache__/
*.pyc
"""


def _welcome_page() -> OdtDocument:
    doc = OdtDocument(
        frontmatter={
            "title": "Bem-vindo ao Asteria",
            "description": "Como usar este site.",
        }
    )
    doc.heading("Bem-vindo ao Asteria", 1)
    doc.paragraph(
        "Este site foi criado com o Asteria, um gerador de sites estáticos "
        "cuja única fonte de conteúdo são arquivos .odt (LibreOffice "
        "Writer) — sem precisar aprender Markdown ou HTML."
    )

    doc.heading("Onde colocar conteúdo", 2)
    doc.paragraph(
        "Páginas ficam em content/pages/ (podem ser organizadas em "
        "subpastas à vontade, é só por organização — não afeta a URL). "
        "Posts de blog ficam em content/posts/ (sem subpastas). O nome do "
        "arquivo, sem a extensão .odt, vira o identificador único do "
        "documento e a base da sua URL."
    )

    doc.heading("Metadados (front matter)", 2)
    doc.paragraph(
        "No início do documento, escreva um bloco assim (cada informação "
        "numa linha, entre duas linhas só com três traços):"
    )
    doc.paragraph("---")
    doc.paragraph("title: Título da página")
    doc.paragraph("description: Um resumo curto")
    doc.paragraph("date: 2026-01-01")
    doc.paragraph("tags: exemplo, primeiro-post")
    doc.paragraph("---")
    doc.paragraph(
        "Esse bloco não aparece no site — é só reconhecido e usado como "
        "metadados. Campos disponíveis: title, description, date, author, "
        "tags, categories, slug, variant, toc, navigation."
    )

    doc.heading("Referenciando outras páginas", 2)
    doc.paragraph(
        "Para linkar outra página ou post, escreva \\[[id]] em qualquer "
        "lugar do texto (id = nome do arquivo sem .odt) — o Asteria "
        "resolve para um link de verdade durante o build, usando o título "
        "do documento automaticamente. Para um texto de link customizado, "
        "use \\[[id|texto do link]]. (Aqui nesta página, a barra invertida "
        "antes dos colchetes é só para mostrar a sintaxe sem que ela seja "
        "processada — na prática você escreve sem a barra.)"
    )

    doc.heading("Comandos", 2)
    doc.list_items(
        [
            "asteria build — gera o site em build/",
            "asteria serve — builda, serve localmente e recarrega o "
            "navegador sozinho a cada mudança",
            "asteria check — valida o projeto inteiro sem gerar nada",
            "asteria clean — remove o diretório build/",
        ]
    )

    doc.heading("Personalizando a aparência", 2)
    doc.paragraph(
        "O tema em theme/minimal/ (templates HTML + CSS) foi copiado pra "
        "dentro do seu projeto — pode editar à vontade. Apague a pasta "
        "inteira se quiser voltar a usar o tema padrão embutido no "
        "Asteria."
    )

    doc.paragraph(
        "Apague esta página (ou edite-a à vontade) quando estiver pronto "
        "para começar."
    )

    return doc


def create_project(target_dir: Path, title: str = "Meu Site") -> list[str]:
    """Cria o projeto em `target_dir` (criado se não existir). Recusa
    sobrescrever um diretório já existente e não vazio. Retorna a lista de
    caminhos criados, relativos a `target_dir`, para o CLI reportar."""

    if target_dir.exists() and any(target_dir.iterdir()):
        raise AsteriaError(
            f"'{target_dir}' já existe e não está vazio — escolha outro "
            "diretório ou esvazie-o antes de rodar 'asteria new'."
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    def _write_text(relative: str, content: str) -> None:
        path = target_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created.append(relative)

    _write_text("site.yaml", _SITE_YAML_TEMPLATE.format(title=title))
    _write_text(".gitignore", _GITIGNORE)

    (target_dir / "content" / "pages").mkdir(parents=True, exist_ok=True)
    (target_dir / "content" / "posts").mkdir(parents=True, exist_ok=True)
    (target_dir / "static").mkdir(parents=True, exist_ok=True)

    welcome_path = target_dir / "content" / "pages" / "bem-vindo.odt"
    _welcome_page().save(welcome_path)
    created.append(str(welcome_path.relative_to(target_dir)))

    bundled_theme = Path(__file__).parent / "themes" / "minimal"
    project_theme = target_dir / "themes" / "minimal"
    shutil.copytree(bundled_theme, project_theme)

    # Personaliza o theme.yaml recém-copiado: já deixa a página de
    # boas-vindas no menu (o tema embutido, por padrão, não referencia
    # nenhuma página específica — não teria como saber qual).
    theme_yaml_path = project_theme / "theme.yaml"
    theme_yaml_content = theme_yaml_path.read_text(encoding="utf-8")
    theme_yaml_content = theme_yaml_content.replace(
        _THEME_YAML_MENU_LINE, _THEME_YAML_MENU_REPLACEMENT
    )
    theme_yaml_path.write_text(theme_yaml_content, encoding="utf-8")

    for path in sorted(project_theme.rglob("*")):
        if path.is_file():
            created.append(str(path.relative_to(target_dir)))

    return created
