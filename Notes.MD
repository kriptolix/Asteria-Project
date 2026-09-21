:::html
<iframe src="https://example.com/map" width="600" height="400"></iframe>
:::

problemas do odt2web
.
<span class="odt-char-t2">eu </span>

##

adicionar menu title ao front matter, isso vai permitir remover title


##
elementos adicionais:
Tabs
card
grid
PrevNext

Topbar + conteúdo central
Topbar + sidebar esquerda + conteúdo
Topbar + sidebar direita + conteúdo
Topbar + sidebar dupla + conteúdo
Hero + conteúdo em blocos
Grid de cards
Lista/timeline
Layout editorial de coluna única

1. Blog
Editorial
Topbar: logo à esquerda, navegação à direita
Header: título/subtítulo do blog
Conteúdo: coluna principal relativamente estreita
Sidebar: direita, com categorias, tags, posts recentes
Posts: lista vertical, imagem opcional + título + resumo + metadata
Footer: links e informações básicas

Estrutura: Topbar → Header → [Posts | Sidebar] → Footer

┌─────────────────────────────────────────┐
│ LOGO                 Nav       Search   │
├─────────────────────────────────────────┤
│                                         │
│              BLOG                       │
│       Artigos e novidades               │
│                                         │
├─────────────────────────┬───────────────┤
│                         │ CATEGORIAS    │
│  POST                   │               │
│  Título                 │ • Design      │
│  Resumo                 │ • Tecnologia  │
│                         │ • Negócios    │
│  ───────────────────    │               │
│  POST                   │ RECENTES      │
│  Título                 │               │
│                         │               │
└─────────────────────────┴───────────────┘

Cards
Topbar: logo + navegação
Hero: título e descrição curta
Conteúdo: grid de 2–3 colunas
Cards: imagem, categoria, título, resumo, data
Sidebar: não
Footer

Estrutura: Topbar → Hero → Grid → Footer

┌─────────────────────────────────────────┐
│ LOGO                         NAV         │
├─────────────────────────────────────────┤
│                                         │
│           ÚLTIMOS ARTIGOS               │
│                                         │
├────────────────┬────────────────────────┤
│   ┌─────────┐  │   ┌─────────┐          │
│   │  IMAGE  │  │   │  IMAGE  │          │
│   └─────────┘  │   └─────────┘          │
│   Título       │   Título               │
│   Resumo       │   Resumo               │
├────────────────┼────────────────────────┤
│   ┌─────────┐  │   ┌─────────┐          │
│   │  IMAGE  │  │   │  IMAGE  │          │
│   └─────────┘  │   └─────────┘          │
│   Título       │   Título               │
└────────────────┴────────────────────────┘

Sidebar
Topbar: logo + navegação
Layout principal: sidebar esquerda fixa/estática
Sidebar: categorias, navegação, busca
Conteúdo: lista de posts
Posts: título + metadata + resumo, com pouca imagem
Footer

Estrutura: Topbar → [Sidebar | Posts] → Footer

┌─────────────────────────────────────────┐
│ LOGO                 NAV                │
├───────────────┬─────────────────────────┤
│ CATEGORIAS    │                         │
│               │  TÍTULO DO POST         │
│ Design        │  21 setembro 2026       │
│ Tecnologia    │                         │
│ Dev           │  Resumo do artigo...    │
│               │                         │
│ TAGS          │  ─────────────────      │
│ #css          │                         │
│ #javascript   │  TÍTULO DO POST         │
│ #web          │  20 setembro 2026       │
│               │                         │
└───────────────┴─────────────────────────┘

2. Site institucional
Corporate
Topbar: logo + navegação + CTA
Hero: título grande, descrição, CTA e imagem/ilustração
Seções: alternância de texto/imagem
Features: grid de 3–4 itens
Depoimentos/logos: opcional
CTA final
Footer: navegação completa

Estrutura: Topbar → Hero → Features → Sections → CTA → Footer

┌─────────────────────────────────────────┐
│ LOGO       Products  Solutions   [CTA]  │
├─────────────────────────────────────────┤
│                                         │
│          TÍTULO GRANDE                  │
│          Mensagem principal             │
│          Descrição                      │
│                                         │
│          [ COMEÇAR ]                    │
│                                         │
│             ┌────────────┐              │
│             │   IMAGE    │              │
│             └────────────┘              │
├─────────────────────────────────────────┤
│          FEATURES / BENEFÍCIOS          │
│     ┌───────┐ ┌───────┐ ┌───────┐      │
│     │       │ │       │ │       │      │
└─────┴───────┴─┴───────┴─┴───────┴──────┘

Minimal
Topbar: logo + poucos links
Hero: grande área de apresentação
Conteúdo: bastante espaço em branco
Seções: blocos horizontais simples
Poucos componentes visuais
Footer: compacto

Estrutura: Topbar → Hero → Sections → Footer

┌─────────────────────────────────────────┐
│ LOGO                       ABOUT CONTACT │
├─────────────────────────────────────────┤
│                                         │
│                                         │
│     Construímos coisas                  │
│     que importam.                       │
│                                         │
│     Pequena descrição.                  │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│     SEÇÃO                               │
│     Texto curto                 IMAGE   │
│                                         │
├─────────────────────────────────────────┤
│     SEÇÃO                               │
│     IMAGE                Texto curto    │
│                                         │
└─────────────────────────────────────────┘

Sidebar
Topbar: logo
Sidebar esquerda: navegação principal
Conteúdo: página institucional
Hero: menor, integrado ao conteúdo
Seções: títulos + texto + mídia
Footer: dentro ou abaixo do conteúdo

Estrutura: Topbar → [Sidebar | Content]

┌──────────────┬──────────────────────────┐
│ LOGO         │                          │
│              │       SOBRE NÓS          │
│ Home         │                          │
│ Sobre        │       Título             │
│ Serviços     │       Texto...           │
│ Projetos     │                          │
│ Contato      │       ──────────         │
│              │       Nossa história     │
│              │       Texto...           │
└──────────────┴──────────────────────────┘

3. Landing Page
Centered
Topbar: logo central/esquerda + navegação + CTA
Hero: tudo centralizado
Headline: muito grande
CTA: 1–2 botões
Imagem/demo: abaixo do hero
Features: grid
Pricing/benefícios: opcional
CTA final
Footer

Estrutura: Topbar → Centered Hero → Demo → Features → CTA → Footer

┌─────────────────────────────────────────┐
│ LOGO              FEATURES  PRICING     │
├─────────────────────────────────────────┤
│                                         │
│              [ NOVO ]                   │
│                                         │
│       SEU GRANDE TÍTULO                 │
│       EM DUAS OU TRÊS LINHAS            │
│                                         │
│       Descrição curta do produto.       │
│                                         │
│       [ COMEÇAR AGORA ]                 │
│                                         │
│       ┌─────────────────────┐           │
│       │                     │           │
│       │      PRODUCT UI     │           │
│       │                     │           │
│       └─────────────────────┘           │
└─────────────────────────────────────────┘

Split
Topbar: logo + navegação
Hero: duas colunas
esquerda: título, descrição, CTA
direita: imagem/produto
Features: blocos alternados
Depoimentos: opcional
CTA final
Footer

Estrutura: Topbar → [Text | Visual] → Features → CTA → Footer

┌─────────────────────────────────────────┐
│ LOGO                    NAV      [CTA]  │
├───────────────────────┬─────────────────┤
│                       │                 │
│  TÍTULO PRINCIPAL     │                 │
│                       │     IMAGE       │
│  Descrição...         │                 │
│                       │                 │
│  [ COMEÇAR ]          │                 │
│                       │                 │
└───────────────────────┴─────────────────┘
│                                         │
│       FEATURES / BENEFÍCIOS             │
└─────────────────────────────────────────┘

Product
Topbar: logo + navegação + CTA
Hero: produto em destaque
Product showcase: screenshot/mockup grande
Features: cada seção apresenta uma funcionalidade
Comparação/benefícios: opcional
Pricing: opcional
CTA final
Footer

Estrutura: Topbar → Product Hero → Showcase → Features → Pricing → CTA → Footer

┌─────────────────────────────────────────┐
│ LOGO        PRODUCT  PRICING   [START] │
├─────────────────────────────────────────┤
│                                         │
│        O PRODUTO É O HERO               │
│                                         │
│       Título + descrição                │
│                                         │
│     ┌───────────────────────────┐       │
│     │                           │       │
│     │       SCREENSHOT          │       │
│     │       DO PRODUTO          │       │
│     │                           │       │
│     └───────────────────────────┘       │
├─────────────────────────────────────────┤
│          FEATURE 1                      │
│  texto                 screenshot       │
├─────────────────────────────────────────┤
│          FEATURE 2                      │
│  screenshot             texto           │
└─────────────────────────────────────────┘

4. Docs / Wiki
Sidebar
Topbar: logo + busca + links
Sidebar esquerda: árvore de navegação
Conteúdo: documentação
Breadcrumb: no topo do conteúdo
Footer: navegação anterior/próxima

Estrutura: Topbar → [Sidebar | Content]

┌─────────────────────────────────────────┐
│ LOGO       SEARCH             GITHUB    │
├──────────────┬──────────────────────────┤
│ GETTING      │                          │
│ STARTED      │  Getting Started         │
│              │                          │
│ Introduction │  Lorem ipsum...          │
│ Installation │                          │
│ Components   │  ## Installation         │
│ Guides       │                          │
│ API          │  Code example            │
│              │  ┌────────────────────┐  │
│              │  │ npm install ...    │  │
│              │  └────────────────────┘  │
└──────────────┴──────────────────────────┘

Double Sidebar
Topbar: logo + busca
Sidebar esquerda: navegação da documentação
Conteúdo: artigo
Sidebar direita: índice da página (On this page)
Código: blocos destacados
Footer: prev/next

Estrutura: Topbar → [Nav | Content | TOC]

┌──────────────────────────────────────────────────┐
│ LOGO                 SEARCH                       │
├────────────┬─────────────────────────┬───────────┤
│ NAV        │                         │ ON THIS   │
│            │   TÍTULO                │ PAGE      │
│ Getting    │                         │           │
│ Started    │   Introdução            │ Intro     │
│ Guides     │                         │ Setup     │
│ API        │   Texto...              │ Config    │
│            │                         │           │
│            │   ## Configuração       │           │
│            │                         │           │
└────────────┴─────────────────────────┴───────────┘

Tree
Topbar: logo + busca
Sidebar: árvore hierárquica expansível
Conteúdo: artigo/documento
Breadcrumb: caminho dentro da árvore
Navegação: anterior/próximo
Footer

Estrutura: Topbar → [Tree | Content]

┌───────────────┬─────────────────────────────┐
│ DOCUMENTAÇÃO  │                             │
│               │  Home > Guides > Components │
│ ▼ Guides      │                             │
│   ▼ Basics    │  Components                 │
│     Intro     │                             │
│     Install   │  Introdução...              │
│               │                             │
│   ▼ Advanced  │  ## Button                  │
│     Routing   │                             │
│     Plugins   │  ## Card                    │
│               │                             │
│ ▼ Reference   │                             │
│   API         │                             │
└───────────────┴─────────────────────────────┘

5. Portfolio
Grid
Topbar: logo/nome + navegação
Hero: apresentação curta
Filtros: categorias de projetos
Grid: 2–4 colunas
Cards: imagem + título + categoria
Footer

Estrutura: Topbar → Hero → Filters → Grid → Footer

┌─────────────────────────────────────────┐
│ NOME                    WORK ABOUT      │
├─────────────────────────────────────────┤
│                                         │
│ Olá, sou João.                          │
│ Designer / Developer                    │
│                                         │
├────────────────┬────────────────────────┤
│                │                        │
│    PROJECT 1   │       PROJECT 2        │
│    ┌────────┐  │       ┌────────┐       │
│    │ IMAGE  │  │       │ IMAGE  │       │
│    └────────┘  │       └────────┘       │
│                │                        │
├────────────────┼────────────────────────┤
│    PROJECT 3   │       PROJECT 4        │
└────────────────┴────────────────────────┘

Editorial
Topbar: nome + navegação
Hero: apresentação pessoal
Conteúdo: lista vertical de projetos
Projeto: imagem grande + descrição + tecnologias
Sidebar: opcional com informações pessoais
Footer

Estrutura: Topbar → Intro → Project List → Footer

┌─────────────────────────────────────────┐
│ NOME                         ABOUT      │
├─────────────────────────────────────────┤
│                                         │
│ Desenvolvedor e designer independente.  │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  2026                                   │
│  ┌──────────────────────────────────┐   │
│  │                                  │   │
│  │          PROJECT IMAGE           │   │
│  │                                  │   │
│  └──────────────────────────────────┘   │
│  Projeto X                              │
│  Descrição / tecnologias               │
│                                         │
├─────────────────────────────────────────┤
│  2025                                   │
│  ┌──────────────────────────────────┐   │
│  │          PROJECT IMAGE           │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘

Fullscreen
Topbar: navegação mínima sobreposta
Projetos: grandes blocos ocupando quase toda a viewport
Cada projeto: imagem/visual dominante + título sobreposto
Navegação: scroll vertical/horizontal
Detalhes: aparecem ao entrar no projeto
Footer: mínimo

Estrutura: Overlay Topbar → Fullscreen Projects → Footer

┌─────────────────────────────────────────┐
│ NOME                         ABOUT ↗    │
│                                         │
│                                         │
│                                         │
│            PROJECT IMAGE                │
│                                         │
│                                         │
│        Projeto / Cliente                │
│        ← 01 / 05 →                      │
│                                         │
│                                         │
└─────────────────────────────────────────┘