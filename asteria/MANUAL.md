# Asteria — Complete User Manual

Asteria is a static site generator (SSG) that builds pages and blog posts
from **OpenDocument Text (`.odt`)** files — you write your content in
LibreOffice Writer, Word, or any ODT-compatible editor, and Asteria converts
it to a themeable, multi-language, cache-friendly static site.

This manual documents every configuration option, content convention, and
CLI command. For a shorter, task-oriented introduction, see `README.md`.

## Table of contents

1. [Requirements](#1-requirements)
2. [Installation](#2-installation)
3. [Quick start](#3-quick-start)
4. [Project structure](#4-project-structure)
5. [CLI reference](#5-cli-reference)
6. [Configuration (`site.yaml`)](#6-configuration-siteyaml)
7. [Writing content in ODT](#7-writing-content-in-odt)
8. [Pages, posts, and raw HTML pages](#8-pages-posts-and-raw-html-pages)
9. [Internal references](#9-internal-references)
10. [Blog excerpts](#10-blog-excerpts)
11. [Multi-language content (i18n)](#11-multi-language-content-i18n)
12. [Asset fingerprinting (cache busting)](#12-asset-fingerprinting-cache-busting)
13. [Theming](#13-theming)
14. [Feeds, sitemap, and robots.txt](#14-feeds-sitemap-and-robotstxt)
15. [Known limitations](#15-known-limitations)
16. [Python API](#16-python-api)

---

## 1. Requirements

- Python 3.11+ (the codebase uses `from __future__ import annotations` and
  modern type-hint syntax such as `str | None`).
- A working `odt2web` installation: it is the converter `build`, `check` and
  `serve` use. (A minimal standard-library fallback converter exists for the
  project's own tests; it is not selectable from the CLI — `--converter` only
  accepts `auto` and `odt2web`, see [CLI reference](#5-cli-reference).)
- Jinja2, PyYAML — installed automatically as dependencies of the package.

## 2. Installation

Install the package from your project (however you distribute/package it —
e.g. `pip install asteria-ssg[watch]` or `pip install -e .` from a local checkout), then
confirm it's on your `PATH`:

**Obs:** Asteria can also be installed without [watch], but in that case, change tracking and automatic reloading will not be available. 

```bash
asteria-ssg --help
```

## 3. Quick start

```bash
# 1. Scaffold a new project. With no argument, it creates ./my-site
asteria-ssg new
# ...or give it an explicit name/path:
asteria-ssg new blog-example

cd my-site

# 2. Serve it locally, with live rebuild on file changes
asteria-ssg serve

# 3. When you're ready, build the final static site
asteria-ssg build
```

The generated project comes with a starter page
(`source/content/pages/welcome.odt`) you can edit or delete.

## 4. Project structure

`asteria-ssg new` scaffolds this layout (the starter content may vary between
versions):

```
my-site/
├── .asteria-cache.json        # conversion cache; created by build/serve, safe to delete
├── result/                    # the generated site (see output.directory); created by build
└── source/                    # everything you edit lives here
    ├── site.yaml               # site-wide configuration
    ├── content/
    │   ├── pages/               # standalone pages (*.odt)
    │   └── posts/                # blog posts (*.odt)
    ├── static/                  # copied as-is to the output root
    └── themes/
        └── minimal/              # the active theme
            ├── theme.yaml
            ├── i18n.yaml
            ├── base.html
            ├── layouts/          # page, post, blog, taxonomy_index, taxonomy_term, 404
            ├── partials/         # header, footer, nav, menu, breadcrumbs, ...
            ├── css/
            ├── js/
            ├── fonts/
            └── images/
```

By default, `asteria-ssg build` writes the generated site to `my-site/result/`
(a sibling of `source/` — see `output.directory` in the
[configuration reference](#6-configuration-siteyaml)). The theme folder is a
**copy** that belongs to your project: edit it freely (see
[Theming](#13-theming)).

All Asteria CLI commands are run against a **project root** — the directory
that *contains* `source/`, not `source/` itself. The default project root is
the current directory (`--project .`).

## 5. CLI reference

The `--project` flag is global and must come **before** the subcommand:

```bash
asteria-ssg --project /path/to/my-site build
```

If omitted, `--project` defaults to `.` (the current directory).

| Command | Description |
|---|---|
| `asteria-ssg new [path]` | Scaffolds a new project at `path`. If `path` is omitted, defaults to `./my-site`. Fails if the target directory already exists and is not empty. |
| `asteria-ssg build [--converter {auto,odt2web}]` | Converts all content and writes the full site to `output.directory`. The output directory is emptied first — everything except `.git` and `.nojekyll`, so a Git repository or GitHub Pages marker living in it survives. Exits non-zero on any error-level diagnostic. |
| `asteria-ssg check [--converter {auto,odt2web}]` | Runs the exact same pipeline as `build` (parses YAML, converts every ODT, resolves IDs/references, renders every template) but **writes nothing to disk**. Use it in CI or before committing content. |
| `asteria-ssg serve [--host HOST] [--port PORT] [--converter {auto,odt2web}] [--no-watch]` | Builds the site and serves `output.directory` locally. `--host` defaults to `127.0.0.1`, `--port` to `8000`. By default it watches `content/`, `static/`, `site.yaml` and the active theme folder, and rebuilds and reloads the browser automatically; pass `--no-watch` to disable that. Watching needs the optional `watchfiles` package (`pip install "asteria-ssg[watch]"`); without it the site is built and served once, with no live reload. |
| `asteria-ssg clean [--cache]` | Empties the output directory (same rule as `build`: `.git` and `.nojekyll` are kept). With `--cache`, also deletes the incremental conversion cache file (`.asteria-cache.json`) in the project root. |
| `asteria-ssg reset-theme [--yes]` | Copies Asteria's bundled `minimal` theme over `source/themes/minimal`, discarding your edits to every file that exists in the bundled theme (extra files you added are left alone). Asks for confirmation unless `--yes` is given. It always targets the folder named `minimal`, whatever `theme.name` says. |

The `--converter` flag selects the ODT→HTML converter. `auto` and `odt2web`
are equivalent today (both use the `odt2web` library); `build`'s default is
`odt2web` while `serve`/`check` default to `auto` — in practice this makes no
difference.

### 5.1 Diagnostics: errors and warnings

`build` and `check` print one line per diagnostic. **Errors** make the command
exit non-zero; **warnings** never do. The ones you are most likely to meet:

| Level | Examples |
|---|---|
| Error | Two documents with the same `id`. Two documents that are the same language version of the same document (see [11.2](#112-naming-translated-files)). A `[[reference]]` that points to nothing. A `template:` front matter value that names a layout the theme doesn't have. |
| Warning | A document without a `title:`. An unknown or duplicated front matter field. A language that isn't configured. A `menu:` / `nav:` entry that resolves to nothing. A `home_page` that no `menu:` entry points to, or that doesn't exist. A folder in `content/` with neither `.odt` files nor an `index.html` (it is ignored). |

Two kinds of failure are **not** diagnostics:

- An unreadable `site.yaml`, `theme.yaml` or `i18n.yaml` (missing, or invalid
  YAML) stops everything immediately with a `FATAL ERROR` line.
- A mistake inside a template — an undefined variable, a bad `{% import %}` —
  stops the build with a Jinja error that names the template and the line.

### 5.2 A failed build leaves the previous output untouched

Errors found while reading the content (duplicate IDs, translation
collisions, broken `[[references]]`) stop the build **before anything is
written**: the output directory keeps whatever the last successful build left
there. That matters most with `serve`, which keeps serving that old copy while
you fix the problem — if the site doesn't seem to change, look at the terminal
for errors before suspecting the browser or the cache.

### 5.3 The conversion cache

To keep rebuilds fast, Asteria stores the converted HTML and extracted images
of each `.odt` in `.asteria-cache.json` (project root), keyed by the file's
absolute path and invalidated when its modification time or size changes. The
cache only covers the ODT→HTML conversion: languages, URLs, menus, references
and templates are recomputed on every build, so a stale cache can never leave
you with stale translations or links. It is always safe to delete
(`asteria-ssg clean --cache`).

## 6. Configuration (`site.yaml`)

`site.yaml` lives at `source/site.yaml`. You only need to specify the keys
you want to override — anything you omit falls back to the defaults shown
below, and this merge happens recursively per sub-key (so you can set just
`blog.posts_per_page` without repeating the rest of the `blog:` block).

### 6.1 `site`

```yaml
site:
  title: "My Site"
  description: ""
  url: "http://localhost:8000"
  language: "en"
  home_page: "welcome"
```

| Key | Default | Meaning |
|---|---|---|
| `title` | `"My Site"` | Site name, used in `<title>`, Open Graph tags, and feeds. |
| `description` | `""` | Site-wide description, used as the default `<meta name="description">` and in feed channel metadata. |
| `url` | `"http://localhost:8000"` | Absolute base URL of the deployed site (no trailing slash needed — it's stripped automatically). Used to build absolute links in feeds, `sitemap.xml`, canonical URLs, and Open Graph tags. **Set this to your real production URL before deploying.** |
| `language` | `"en"` | The site's **default language**: the language of every document without a language suffix, served from the root with unprefixed URLs. It is the only place the default language is set (see [i18n](#11-multi-language-content-i18n)). |
| `home_page` | `"welcome"` | The `id` of the page to serve at `/` (the filename without extension, e.g. `welcome` for `welcome.odt`). Use the special value `blog` to make the blog index the home page instead. It is resolved like a `menu:` entry (translation key first, then exact id); Asteria warns if no `menu:` entry points to it. |

### 6.2 `content`

```yaml
content:
  pages: "content/pages"
  posts: "content/posts"
```

Paths are relative to `source/`. Change these if you want a different
content layout.

### 6.3 `output`

```yaml
output:
  directory: "../result"
```

Where the generated site is written, relative to `source/` (so the default
puts it in `my-site/result/`, next to `source/`). An absolute path is also
accepted.

### 6.4 `static`

```yaml
static:
  directory: "static"
```

Relative to `source/`. Everything in this directory is copied verbatim to
the root of the output (e.g. `source/static/favicon.ico` →
`result/favicon.ico`). Use it for files that must keep a fixed name
(favicons, `CNAME`, manually-managed files) — see
[asset fingerprinting](#12-asset-fingerprinting-cache-busting) for why this
matters.

### 6.5 `theme`

```yaml
theme:
  name: "minimal"
  directory: "themes"
```

| Key | Default | Meaning |
|---|---|---|
| `name` | `"minimal"` | Selects the theme: Asteria looks for `source/<directory>/<name>/`. |
| `directory` | `"themes"` | The folder, relative to `source/`, that holds the themes. |

If that folder doesn't exist, Asteria silently falls back to its own bundled
`minimal` theme — whatever `name` says, so a mistyped name gives you the bundled
theme rather than an error. `asteria-ssg reset-theme` restores the bundled
`minimal` theme over your project's copy.

### 6.6 `blog`

```yaml
blog:
  posts_per_page: 10
  excerpt_enabled: true
  excerpt_length: 280
```

| Key | Default | Meaning |
|---|---|---|
| `posts_per_page` | `10` | How many posts appear per page of the paginated blog index (`/blog/`, `/blog/page/2/`, ...). The blog index's own URL isn't set here — it's derived from `urls.posts` (see [`urls`](#69-urls)). |
| `excerpt_enabled` | `true` | See [Blog excerpts](#10-blog-excerpts) for the full behavior. |
| `excerpt_length` | `280` | Character length used for the automatically-generated excerpt when no `[[more]]` marker is present. |

### 6.7 `i18n`

```yaml
i18n:
  languages: []
  strings: {}
```

| Key | Default | Meaning |
|---|---|---|
| `languages` | `[]` | The *additional* languages your pages/posts are written in, besides the default one. Listing the default language here too is harmless. |
| `strings` | `{}` | Site-level overrides and additions for the theme's UI strings (see [11.5](#115-ui-strings-i18nyaml)). |

There is no `default_language` key: the default language is `site.language`.
A leftover `i18n.default_language` is still accepted when it equals
`site.language`, and is an error when it doesn't (so the two can never pull in
different directions).

See [Multi-language content](#11-multi-language-content-i18n) for the full
explanation.

### 6.8 `assets`

```yaml
assets:
  fingerprint: true
```

Toggles content-hash renaming of theme assets (`css/`, `js/`, `fonts/`,
`images/`). See [Asset fingerprinting](#12-asset-fingerprinting-cache-busting).

### 6.9 `urls`

```yaml
urls:
  pages: "/pages/{slug}/"
  posts: "/blog/{slug}/"
  tags: "/tags/{slug}/"
  categories: "/categories/{slug}/"
  tags_index: "/tags/"
  categories_index: "/categories/"
```

URL patterns. `{slug}` is the only placeholder available, and is filled with
the document's slug (either an explicit `slug:` front matter field, or an
automatic slugification of the filename — see
[front matter](#71-front-matter-reference)). A missing leading
`/` and a missing trailing `/` are added automatically (the trailing one unless
the last path segment contains a dot).

For non-default languages, Asteria automatically prepends `/{lang}` to every
one of these — you never write the language into the pattern yourself (see
[i18n](#11-multi-language-content-i18n)).

**`urls.posts` is the only setting for the blog's URL structure.** The
paginated blog index (`/blog/`, `/blog/page/2/`, ...) isn't configured
separately — it's derived automatically from `urls.posts` by stripping the
`{slug}/` part (`"/blog/{slug}/"` → index at `/blog/`; `"/articles/{slug}/"`
→ index at `/articles/`), so there's exactly one place to change if you
want your blog somewhere else, and the listing can never drift out of sync
with individual post URLs.

### 6.10 `feeds`

```yaml
feeds:
  enabled: true
  format: "rss"   # "rss" | "atom"
```

When enabled, Asteria writes `rss.xml` (or `atom.xml`) at the output root for
the default language, containing every post of that language, newest first (title, link, publish
date, and excerpt). Additional languages get their
own feed named `{lang}-rss.xml` / `{lang}-atom.xml`.

### 6.11 `sitemap`

```yaml
sitemap:
  enabled: true
```

Writes `sitemap.xml` at the output root, listing every page, post, raw HTML page, blog
index page, taxonomy page, and language-specific home page that was
generated.

### 6.12 `robots`

```yaml
robots:
  enabled: true
```

Writes `robots.txt` at the output root (`User-agent: * / Allow: /`), plus a
`Sitemap:` line pointing at `sitemap.xml` if `sitemap.enabled` is also true.

### 6.13 `search`

```yaml
search:
  enabled: true
```

Writes `search-index.json` at the output root: a JSON list with
`{title, url, date, excerpt}` for every page and post of the default language
(the excerpt can contain HTML when a post uses a `[[more]]` marker). Each
additional language gets its own `{lang}-search-index.json`. Asteria only
generates the file; showing a search box that uses it is up to the theme.

### 6.14 `menu`

```yaml
menu:
  - welcome        # a page, by translation key or exact id
  - about
  - blog           # reserved word: the blog index
```

The flat top-level menu, exposed to templates as `site.menu` (see
[Theming](#13-theming)). Each entry is the name of a page — and nothing else:
its label comes from the page itself, already in the right language
(`menu_title:` front matter if the page has one, else `title:`), so a
translated site needs no per-language labels here.

- A page reference is resolved as a **translation key** first: `about`
  follows the language of the page being rendered, falling back to the
  default language and then to any translation that exists. If no translation
  key matches, it is tried as an **exact document id** (`about.pt`), which
  pins the item to one specific translation.
- Only **pages** can be menu entries — not posts, and not raw HTML pages.
- `blog` links to that language's blog index (see [`urls`](#69-urls)). Its label
  is the `blog_menu_label` UI string ("Blog" if the theme doesn't define it).
  Asteria never adds a blog entry on its own: list it if you want it.
- An entry that resolves to nothing gives a warning and a `#` link.
- The older form `- page: welcome` (with an optional `title:` override) still
  works but is deprecated and warns.

### 6.15 `nav`

```yaml
nav:
  - welcome
  - docs-index:          # a branch: the key is a document id...
      - installation     # ...and the list holds its children
      - usage
      - reference:       # branches nest to any depth
          - cli
          - configuration
```

The hierarchical sidebar navigation, exposed as `site.nav`. Each entry is a
document id, or a single-key mapping whose key is a document id and whose
value is the list of its children. Every id — leaf and branch alike — is
resolved exactly like a `menu:` entry (translation key first, exact id second,
and it follows the page's language). Titles come from the documents
(`nav_title:` front matter, else `title:`); a branch's own link goes to the
document named by its key.

- Unlike `menu:`, `nav:` may also point to posts and to raw HTML pages (by
  exact id).
- A leaf that resolves to nothing warns and is shown without a link. A branch
  whose key resolves to nothing warns and is dropped with its children.
- The sidebar only appears when the theme supports it (`navigation` in its
  `theme.yaml`, see [13.1](#131-themeyaml)) and the document doesn't set
  `navigation: false`.

### 6.16 `social`

```yaml
social:
  - platform: "github"
    url: "https://github.com/you/your-repo"
    label: "GitHub"
  - platform: "e-mail"
    url: "mailto:you@example.com"
    label: "E-mail"
```

The footer's social links, exposed as `site.social`. `platform` identifies the
service, `url` is where it points, and `label` is the accessible name/tooltip.
How a link is drawn is up to the theme: the bundled one shows
`images/<platform>.svg` for the platforms listed in its `known_platforms`
(`theme.yaml`) and the platform's initials for any other.

### 6.17 Full example

```yaml
site:
  title: "Asteria Docs"
  description: "Documentation and updates for the Asteria SSG."
  url: "https://docs.example.com"
  language: "en"             # the default language, served from the root
  home_page: "welcome"

blog:
  posts_per_page: 8
  excerpt_length: 220

i18n:
  languages: ["pt", "es"]    # additional languages

menu:
  - welcome
  - docs-index
  - blog

nav:
  - welcome
  - docs-index:
      - installation
      - usage

social:
  - platform: "github"
    url: "https://github.com/you/your-repo"
    label: "GitHub"

assets:
  fingerprint: true

feeds:
  enabled: true
  format: "atom"

theme:
  name: "minimal"
```

## 7. Writing content in ODT

Every page and post is a single `.odt` file. The **filename** (without
extension) becomes the document's `id` — it must be unique across the whole
site, and is used for cross-references (`[[id]]`) and, by default, for the
URL slug.

### 7.1 Front matter reference

At the very start of the document, add a fenced block delimited by `---`,
with one `key: value` pair per line:

```
---
title: My First Post
date: 2024-03-15
author: Jane Doe
tags: python, static-sites, tutorial
categories: tutorials
description: A short summary shown in listings and search results.
slug: my-first-post
variant: dark
toc: true
navigation: false
lang: en
---

The rest of the document is your actual content — headings, paragraphs,
lists, tables, and images, all written normally in your ODT editor.
```

| Field | Type | Default | Meaning |
|---|---|---|---|
| `title` | text | filename | The document's title. If omitted, Asteria warns and falls back to the filename. |
| `date` | text | — | Publish date. Use `YYYY-MM-DD`: posts are ordered by this text, and every date-aware part understands it. Feeds also accept `YYYY-MM-DDTHH:MM:SS` and `YYYY-MM-DDTHH:MM:SS±HHMM` (a date no format recognises is published as "now"); the [`format_date`](#133-filters-and-globals) filter additionally accepts `YYYY-MM-DDTHH:MM`, `YYYY-MM-DD HH:MM[:SS]` and `YYYY/MM/DD`. |
| `author` | text | — | Author name. |
| `tags` | comma-separated list | `[]` | Post tags — generates individual tag pages plus a tag index. Pages ignore this. |
| `categories` | comma-separated list | `[]` | Same as `tags`, under `/categories/`. |
| `description` | text | `""` | Short summary. Used as the excerpt when `blog.excerpt_enabled: false` (see [Blog excerpts](#10-blog-excerpts)), and available to theme templates for meta description overrides. |
| `slug` | text | slugified filename | Overrides the automatic URL slug. The automatic one is the filename *without its language suffix*, so all translations of a document share it. |
| `variant` | text | theme's `default_variant` | A per-document variant name, exposed to the theme as `page.variant`; the bundled theme loads `css/{variant}.css` for it. |
| `toc` | boolean | theme's `toc` | Whether this document shows the table-of-contents sidebar. Overrides the theme's global switch; when omitted the document inherits it, and a theme that doesn't declare `toc` never shows one. (The heading tree itself, `page.toc`, is always built.) |
| `navigation` | boolean | theme's `navigation` | Same idea for the `site.nav` sidebar. |
| `lang` | text | detected from filename | Explicitly sets this document's language, overriding the filename-based detection (see [i18n](#11-multi-language-content-i18n)). |
| `template` | text | `layouts/page.html` / `layouts/post.html` | Renders this document with another layout of the theme, as a path relative to the theme folder (`layouts/wiki.html`). A name the theme doesn't have is an error (the default layout is used for the output). |
| `featured` | boolean | `false` | Lists the document in `site.featured_pages` / `site.featured_posts`. |
| `cover` | text | — | Path of a cover image (`/images/cover.jpg`), exposed as `page.cover` (a leading `/` is added if missing). It is never extracted from the document body: the file is a separate asset. |
| `menu_title` | text | `title` | Label for this document in the `menu:`, when the page title is too long for it. |
| `nav_title` | text | `title` | Same, for the `nav:` sidebar. |

Boolean fields accept `false`/`no`/`0`/`off` (case-insensitive) as false;
any other non-empty value is true; an empty or missing value uses the
default shown above.

Any field **not** in this list is preserved (Asteria emits a warning, since
it's likely a typo) and is reachable in templates via
`page.frontmatter.extra.your_key` / `post.frontmatter.extra.your_key`.

### 7.2 Body content

Write normally: headings (`Heading 1`–`Heading 6` styles), paragraphs,
bulleted/numbered lists, tables, links, and inline images are all converted
to their HTML equivalents. Images embedded in the document are extracted and
copied alongside the generated page.

## 8. Pages, posts, and raw HTML pages

- **Pages** (`content/pages/*.odt`) are standalone content — About, Contact,
  documentation, etc. They may be organized in subfolders for your own
  convenience; subfolders don't affect the URL, which is always
  `urls.pages` filled with the page's slug.
- **Posts** (`content/posts/*.odt`) are chronological blog content. Unlike
  pages, `content/posts/` is **not** scanned recursively — every post must be
  a direct child of that directory.
- **Raw HTML pages**: instead of an `.odt` file, you can create a folder
  containing an `index.html` (plus any assets it needs) inside `content/pages/`
  or `content/posts/`. Asteria copies the whole folder as-is to the corresponding
  URL, without any conversion. This is useful for publishing externally-built
  content (an exported prototype, a WebGL build, etc.) at its own URL, which
  you can then link to with `[[its-id]]`. A folder with neither `.odt` files nor
  an `index.html` is ignored with a warning.

  Optionally add a `raw.yaml` inside that folder:

  ```yaml
  title: "Interactive Demo"
  ```

  `title` is used as the label in `nav:` and as the link text for
  `[[its-id]]` references. Raw pages do **not** participate in multi-language
  routing, and cannot be `menu:` entries (see
  [limitations](#15-known-limitations)).

## 9. Internal references

Anywhere in a document's body, reference another page or post by its `id`:

| Syntax | Result |
|---|---|
| `[[some-id]]` | A link (`<a href="...">`) to that document, using its title as the link text. |
| `[[some-id\|Custom label]]` | Same link, with custom link text. |
| `\[[some-id]]` | Escaped — renders the literal text `[[some-id]]` instead of resolving it. |

If the referenced `id` doesn't exist, Asteria reports an error diagnostic
(visible in `asteria-ssg build`/`asteria-ssg check` output) and renders a visible
`<span class="broken-reference">[[some-id]]</span>` in the HTML, so it's easy
to spot while reviewing a draft.

**ID character set:** letters, digits, `_`, `-`, and `.` are recognized
inside `[[...]]`.

**Embedding raw HTML (iframes, embeds, widgets):** this isn't `[[...]]`
syntax at all — write a `:::html ... :::` fenced block directly in your ODT
document, recognized by the `odt2web` converter itself, before Asteria ever
sees the resulting HTML:

```
:::html
<iframe src="https://example.com/map" width="600" height="400"></iframe>
:::
```


### 9.1 References follow the current document's language

`some-id` is resolved as a **translation_key** first (see
[i18n](#11-multi-language-content-i18n)): a plain `[[about]]` written inside
a `pt` document automatically links to the `pt` translation of "about" if
one exists, falling back to the site's default language, and finally to any
translation that exists — the same resolution `menu:` and `nav:` use (see
[`menu`](#614-menu)). You don't need to hardcode a language-specific id
in every cross-reference; write `[[about]]` once and it follows whichever
document it's used from.

If no translation_key matches, `some-id` is tried as an **exact document
id** instead (e.g. `[[about.pt]]`) — use this form when you specifically
want to link to one particular translation regardless of the current
document's language, such as a "read this in Portuguese" link.


## 10. Blog excerpts

Controlled by `blog.excerpt_enabled` and `blog.excerpt_length`
(see [`blog`](#66-blog)):

- **`excerpt_enabled: true` (default).** If the post's body contains a
  `[[more]]` marker (on its own paragraph), everything **before** the marker
  becomes the excerpt, and the marker itself is removed from the full post.
  If there's no marker, Asteria generates an excerpt by stripping HTML tags
  from the content and truncating to `excerpt_length` characters (adding
  `…`) — this always happens when a post has no marker, **even if** a
  `description` front matter field is set.
- **`excerpt_enabled: false`.** The excerpt is simply the `description`
  front matter field, if set; otherwise it falls back to the post's title.

Example using a marker:

```
This paragraph, and anything before the marker below, is shown in blog
listings and feeds.

[[more]]

Everything from here on is only shown on the post's own page.
```

## 11. Multi-language content (i18n)

Both pages and posts can be authored in multiple languages. Nothing changes
in a single-language site — this feature is entirely opt-in.

### 11.1 Configuring the languages

```yaml
site:
  language: "en"            # the default language: clean, unprefixed URLs
i18n:
  languages: ["pt", "es"]   # any *additional* languages besides the default
```

`site.language` is the one place the default language is set. It is served
with clean, unprefixed URLs; every other language listed in `i18n.languages`
is served under a `/{lang}/` prefix. A language code is any text (`pt`,
`pt-BR`, …), but it is matched **exactly** — it is case-sensitive, and
`pt-br` is not `pt-BR` — between the filename suffixes, the `lang:` front
matter field and this configuration.

### 11.2 Naming translated files

A file without a language suffix is written in the **default language**. To
add a translation, put the language code as an extra extension segment:

```
content/posts/hello-world.odt       -> default language (e.g. "en")
content/posts/hello-world.pt.odt    -> "pt" translation
content/posts/hello-world.es.odt    -> "es" translation

content/pages/about.odt
content/pages/about.pt.odt
```

The rules:

- **Which suffixes count.** Only a suffix that is a configured language (the
  default or one of `i18n.languages`) is read as a language. In a site whose
  languages are `en` and `pt`, `hello-world.fr.odt` is just a file whose name
  contains a dot, written in the default language.
- **Translation key.** The filename without its language suffix
  (`hello-world`) is the document's *translation key*; documents that share
  it are translations of one another, share the same **slug**, and are linked
  through `page.translations`. Their **IDs** stay distinct (`hello-world`,
  `hello-world.pt`, `hello-world.es`), since the ID is the full filename stem.
- **One document per language.** A translation key can have only one document
  per language, and that **includes the unsuffixed file**, which already *is*
  the default-language version. In a site whose default language is `pt-BR`,
  `welcome.odt` is the Portuguese page: adding `welcome.pt-BR.odt` next to it,
  or keeping an English text in `welcome.odt`, makes two `pt-BR` versions and
  fails the build with an error naming both files. Put the English text in
  `welcome.en.odt` (and list `en` under `i18n.languages`) instead. Giving the
  default language an explicit suffix is fine as long as no unsuffixed file for
  the same document exists.
- **`lang:` front matter** sets the language explicitly and takes priority over
  whatever the filename implies. This is handy if you don't want the
  dotted-filename convention — and a trap when you copy a document to start a
  translation: the `lang:` line comes along with the text, so change it, or the
  copy is still a version of the original's language (a collision error).
- **A language that isn't configured** (typically a `lang:` value that is not
  in `site.language` / `i18n.languages`) gets a warning. The document is still
  built, under `/{lang}/`, but it is left out of the blog index, feeds, tags,
  categories and search index, and the site has no home page or menu for that
  language.

### 11.3 What gets localized automatically

For every language (the default and each one in `i18n.languages`):

- **Post and page URLs** get the `/{lang}/` prefix (default language
  excluded).
- **The blog index** (`/blog/`, `/{lang}/blog/`, with pagination) only lists
  posts in that language.
- **Tags and categories** (index pages and individual term pages) are
  computed per language, so a tag cloud never mixes posts from different
  languages.
- **RSS/Atom feeds and the search index** are generated per language (see
  [`feeds`](#610-feeds) and [`search`](#613-search)).
- **`previous`/`next` post navigation** never crosses a language boundary.
- **`menu:` and `nav:`** are resolved separately for each language, following
  the translation-key rule of [section 9.1](#91-references-follow-the-current-documents-language).
- **`[[references]]`** follow the language of the document they are written
  in.
- **The home page** (`site.home_page`) gets a version for every language
  that has one available:
  - If `home_page` points to a page ID, each language uses that page's
    *translation* in that language (via the mechanism above) as its `/`
    (or `/{lang}/`) index — silently skipped for a non-default language that
    has no translation of that page (for the default language, a missing home
    page is a warning).
  - If `home_page: blog`, each language's own blog page 1 becomes that
    language's home.
- **`sitemap.xml`** includes every language-specific home, blog index,
  taxonomy page, and content URL.

Not localized: the single `404.html` (it is in the default language) and
raw HTML pages (see [limitations](#15-known-limitations)).

### 11.4 What templates get for free

- `lang` — the language of the page being rendered; present in **every**
  template, including the blog, taxonomy and 404 pages.
- `page.lang` / `post.lang` — the document's language code.
- `page.translations` / `post.translations` — a `{lang: Document}` dict of
  this document's other language versions (empty if there are none).
- `site.languages` — the full list of configured language codes (default
  first), and `site.default_language`.
- `site.blog_index_urls` — a `{lang: url}` dict, useful as a fallback target
  for a language switcher on pages that have no direct translation.
- `site.menu`, `site.nav`, `site.tags`, … already hold the current language's
  version.
- The bundled theme implements a language switcher
  (`partials/_lang_switcher.html`, called from `partials/_header.html`) and
  `hreflang` alternate `<link>` tags in `base.html` with exactly these
  variables. A switcher link points to the translation of the current page,
  and to that language's blog index when the page has none. See
  [Theming](#13-theming) if you're customizing it — in particular, macros don't
  see `lang` or `page` unless `base.html` passes them in.

### 11.5 UI strings (`i18n.yaml`)

Text a theme writes itself (button labels, "Made with", pagination…) is
translated with the `t()` function, from the theme's `i18n.yaml`. The file maps
a language to its strings:

```yaml
# themes/minimal/i18n.yaml
en:
  made_with: "Made with"
  reading_time: "{minutes} min read"
pt-BR:
  made_with: "Feito com"
  reading_time: "{minutes} min de leitura"
```

```html
{{ t("made_with", lang) }}
{{ t("reading_time", post.lang, minutes=post.reading_time) }}
```

To change or add strings without editing the theme, put them under
`i18n.strings` in `site.yaml`, in the same shape; they are merged over the
theme's.

`t(key, lang)` looks for the key in `lang`, then in the default language. If
neither has it, it renders `??key??` — a visible marker, so after a build
`grep -r '??' result/` finds every missing translation (it only finds the ones on
pages that were generated: a string used only on an empty blog page, say, won't
show up until that page exists). Pass `fallback="text"` to render a default
text instead. Placeholders in `{braces}` are filled from the keyword arguments.

Asteria itself asks the theme for three strings — `blog_menu_label` (the
`blog` menu entry and the blog breadcrumb), `tags_label` and `categories_label`
(the taxonomy page titles) — and falls back to "Blog", "Tags" and "Categories"
when the theme doesn't define them.

### 11.6 Dates

The `format_date` filter writes a front matter date in the reader's language:
`{{ post.date | format_date(post.lang, "long") }}` gives `15 de março de 2024`
for `pt-BR` and `March 15, 2024` for `en`. See [13.3](#133-filters-and-globals).

## 12. Asset fingerprinting (cache busting)

```yaml
assets:
  fingerprint: true   # default
```

When enabled, every file under the theme's `css/`, `js/`, `fonts/`, and
`images/` output directories is renamed with a hash of its content, e.g.
`style.css` → `style.a1b2c3d4e5.css`. Because the hash is derived from the
file's content, it changes automatically whenever you edit the file — which
means the browser never serves a stale cached copy during `asteria-ssg serve`,
and you can set long, aggressive cache lifetimes for these assets in
production without worrying about invalidation.

**In your templates**, reference these assets through the `asset()`
function instead of hardcoding the path:

```html
<link rel="stylesheet" href="{{ asset('/css/' ~ theme_css ~ '.css') }}">
<img src="{{ asset('/images/logo.svg') }}" alt="Logo">
```

`asset()` looks up the real, hashed path from the manifest; if the path
isn't in the manifest (fingerprinting disabled, or the file lives outside
`css/js/fonts/images`), it's returned unchanged, so calling `asset()` is
always safe even on paths you don't expect to be fingerprinted.

Fingerprinting runs on the *output* folders `css/`, `js/`, `fonts/` and
`images/`, after both the theme's assets and `static/` have been copied there —
so a file from `static/images/` is fingerprinted too. Files that live
**outside** those four folders (e.g. `static/favicon.ico`, a `static/favicon/`
folder, `static/robots.txt` overrides) are **not**, since they're typically
referenced by a fixed, well-known name.

References *between* assets are kept working: inside the `css/` and `js/`
files, a literal path to a fingerprinted file (a `url('/fonts/foo.woff2')` in a
stylesheet, say) is rewritten to its hashed name.

A manifest of every rename is also written to `asset-manifest.json` at the
output root, for debugging or for external tooling.

Set `assets.fingerprint: false` to disable this entirely and serve assets
under their original names.

## 13. Theming

A theme is a directory under `source/themes/<name>/` (see
[`theme`](#65-theme)). The theme's own `README.md` is the complete reference of
everything its templates can read; this section is the overview.

| File | Purpose |
|---|---|
| `layouts/page.html`, `post.html`, `blog.html`, `taxonomy_index.html`, `taxonomy_term.html`, `404.html` | The six layouts Asteria renders, by exactly these names: a page, a post, one page of the paginated blog index, the tag/category index (used for both `/tags/` and `/categories/`, told apart by `kind_label`), a single tag/category page, and the not-found page. Others can be chosen per document with the `template:` front matter field. |
| `base.html` | The shared HTML shell the layouts extend (a convention: Asteria doesn't render it directly). |
| `partials/` | Macros and fragments the templates import — header, footer, navigation, menu, breadcrumbs, language switcher, social links, table of contents. Also a convention. |
| `theme.yaml` | Theme options (optional) — see below. |
| `i18n.yaml` | UI string translations (optional) — see [11.5](#115-ui-strings-i18nyaml). |
| `css/`, `js/`, `fonts/`, `images/` | Static theme assets, copied to the output and optionally fingerprinted (see previous section). |

Template names are relative to the theme folder (`{% extends "base.html" %}`,
`{% import "partials/_nav.html" as navmacros %}`). The menu, the sidebar
navigation and the social links are **not** configured in the theme: they come
from `menu:`, `nav:` and `social:` in `site.yaml` and reach the templates as
`site.menu`, `site.nav` and `site.social`.

### 13.1 `theme.yaml`

```yaml
toc: true
navigation: true
default_variant: "light"
known_platforms: ["github", "mastodon"]
```

`theme.yaml` holds the theme's own options and nothing else — Asteria adds no
defaults to it, and a theme without one simply has an empty `theme`. Two keys
are read by Asteria itself, to decide which optional sidebars the theme
supports; the rest is the theme's business:

| Key | Meaning |
|---|---|
| `toc` | The table-of-contents sidebar. Absent = the theme doesn't support it (never shown). `true` / `false` = on / off by default for every document; a document's own `toc:` front matter overrides it either way. |
| `navigation` | The same, for the `site.nav` sidebar and the `navigation:` front matter field. It is shown only when `site.nav` isn't empty. |
| `default_variant` | Read by the bundled `base.html`: the CSS variant loaded when a document doesn't set its own `variant:`. The template falls back to `"light"` when it is missing. |
| `known_platforms` | Read by the bundled `_social_links.html`: the social platforms that have an icon at `images/<platform>.svg`; every other platform shows its initials. |

Any other top-level key you add is passed through untouched and available in
templates as `theme.your_key`. Because the templates run with
`StrictUndefined`, read optional keys with a default
(`theme.your_key | default("x")`).

### 13.2 Template context variables

Every template — whatever its layout — receives:

| Variable | Type / notes |
|---|---|
| `site` | The site-wide data: `title`, `description`, `url`, `language`, `default_language`, `languages`, `blog_index_url`, `blog_index_urls`, `feed_url`, `menu`, `nav`, `social`, `categories`, `tags`, `featured_pages`, `featured_posts`, `pages`, `posts`, `tocs`. The language-dependent ones already hold the current language's version. |
| `theme` | The theme's `theme.yaml` dict (see 13.1). |
| `lang` | The language of the page being rendered (the default language on the 404 page). |
| `canonical_path` | This page's own path, e.g. `/blog/hello-world/` (`/404.html` on the 404 page). |
| `og_type` | `"article"` for posts, `"website"` otherwise. |
| `show_navigation` | Boolean. On documents it already combines the theme's `navigation` switch, the document's front matter and whether `site.nav` is empty; elsewhere it is always `false`. |
| `breadcrumbs` | List of `{title, url}` — the site root (in the page's language) first, the current page last; empty on the 404 page. |

On top of those:

- **page and post layouts**: `page` (the current `Document`), `post` (the very
  same object — both names are always set so a template can use whichever
  reads better), `content` (safe HTML) and `show_toc` (Boolean, like
  `show_navigation`).
- **`blog.html`**: `posts` (the current page's items) and `pagination`
  (`items`, `number`, `total_pages`, `url`, `prev_url`, `next_url`).
- **`taxonomy_index.html`**: `terms` (each with `name`, `slug`, `url`,
  `posts`) and `kind_label` — the translated name of the taxonomy, from the
  `tags_label` / `categories_label` UI strings.
- **`taxonomy_term.html`**: `term`, `posts` and `kind_label`.

`page` and `post` do **not** exist on the blog, taxonomy and 404 layouts.
Neither does `theme_css`: the bundled `base.html` computes it itself, from
`page.variant` and `theme.default_variant`.

### 13.3 Filters and globals

| Name | Use |
|---|---|
| `{{ value \| safe_content }}` | Marks a trusted HTML string (already generated by the pipeline, e.g. `content`) safe to render without escaping. |
| `{{ text \| slug }}` | Slugifies arbitrary text the same way Asteria slugifies filenames. |
| `{{ date \| format_date(lang, style) }}` | Formats a front matter `date:` for a reader of `lang`. `style` is `"long"` (the default; `15 de março de 2024`, `March 15, 2024`), `"short"` (`15/03/2024`; `03/15/2024` in English) or any `strftime` pattern. Month names and word order are built in for `pt-BR`, `pt`, `es`, `en` and `fr`; other languages fall back to English. A value that isn't a recognised date is returned unchanged. |
| `{{ t("key", lang, **kwargs) }}` | A UI string in `lang`, falling back to the default language (see [11.5](#115-ui-strings-i18nyaml)). Renders `??key??` when the string doesn't exist — or the `fallback=` text, if you pass one. |
| `{{ asset('/css/style.css') }}` | Resolves a static asset path through the fingerprint manifest — see [section 12](#12-asset-fingerprinting-cache-busting). |
| `{{ nav_branch_active(entry, canonical_path) }}` | Returns `true` if `entry` (a `site.nav` item) or any of its descendants matches the current path — useful for highlighting the active section. |
| `{{ menu_item_active(item, canonical_path) }}` | Returns `true` if the `site.menu` item points to the current path. |
| `{{ current_year }}` | The year the site was built, for footers. |

### 13.4 Writing templates: what trips people up

- **Imported macros don't see the page's context.** `{% import "partials/_x.html" as x %}`
  brings the macros in *without* the page's variables: inside a macro only its
  own arguments, the globals above and the macro file's own variables exist.
  `lang`, `page`, `post`, `site` and `theme` are not there, and referencing
  one fails the build with `'…' is undefined`. Pass what a macro needs as
  arguments — the bundled `base.html` calls
  `header.render_header(site, canonical_path, current_lang, doc_translations)`
  for exactly this reason.
- **Take the language from `lang`, never from `site.language`.** The latter is
  the default language, so a page in another language would get the default
  language's text. The same goes for links: don't hardcode `/` or `/tags/…` —
  the root of a non-default language is `/{lang}/`. Use `term.url`, `page.url`
  and `site.blog_index_urls[lang]`, which already carry the prefix.
- **Check `page is defined`** before reading anything off `page` in a partial
  that is also used by the blog, taxonomy and 404 layouts.

### 13.5 Updating a theme

The theme in `source/themes/<name>/` is your project's own copy, so a new Asteria
version never changes it. To go back to the bundled `minimal` theme, run
`asteria-ssg reset-theme` (it overwrites the files the bundled theme has, so
copy any edits you want to keep first).

## 14. Feeds, sitemap, and robots.txt

These (and the search index) are generated automatically at the output root
according to the `feeds`, `sitemap`, `robots` and `search` config blocks
documented in [section 6](#6-configuration-siteyaml) — there is nothing to
write by hand for these, only configuration to adjust.

## 15. Known limitations

- **Raw HTML pages are not localized.** Folders containing an `index.html`
  (see [section 8](#8-pages-posts-and-raw-html-pages)) don't participate in
  language detection, prefixing, or the translations mechanism. They can be
  reached from `[[...]]` and `nav:` only by their own exact id, and not at all
  from `menu:`, which only lists pages.
- **There is a single 404 page**, in the default language.
- **Some `site` values are the same on every page**, whatever its language:
  `site.language`, `site.blog_index_url` (the default language's) and
  `site.feed_url` (the default language's feed). For the current language use
  `lang` and `site.blog_index_urls`.
- **A document in a language that isn't configured** is built under its
  `/{lang}/` prefix but appears in no listing (see
  [11.2](#112-naming-translated-files)).

## 16. Python API

The `asteria.api` module is the frontend-agnostic API the CLI itself is built
on: anything that is not a terminal — a GUI, a script, a test — should import
from it instead of shelling out to `asteria-ssg`.

```python
from pathlib import Path
from asteria.api import AsteriaError, build_project

try:
    result = build_project(Path("my-site"))
except AsteriaError as exc:          # fatal: bad site.yaml, ...
    print("fatal:", exc)
else:
    for diagnostic in result.diagnostics:
        print(diagnostic)
    print(result.success, len(result.pages), "pages ->", result.output_dir)
```

| Function | What it does |
|---|---|
| `build_project(root, converter_name="odt2web")` | A full build; returns a `BuildResult` (`success`, `diagnostics`, `pages`, `posts`, `output_dir`, `generated_files`, `cache_hits`, `cache_misses`). Content errors are in `diagnostics`, not exceptions. |
| `check_project(root, converter_name="auto")` | The same validation without writing anything. |
| `clean_project(root, remove_cache=False)` | Empties the output directory (and optionally the cache); returns a `CleanResult`. |
| `clear_project_cache(root)` | Deletes the conversion cache; `True` if there was one. |
| `create_new_project(target_dir)` | Scaffolds a project; returns the relative paths it created. |
| `reset_project_theme(root)` | Restores the bundled `minimal` theme; returns its path. |
| `load_project_config(root)` / `load_project_theme(root)` | The parsed `site.yaml` (`SiteConfig`) / the active theme's `theme.yaml` (`ThemeConfig`: `name`, `source` — `"project"` or `"bundled"` —, `directory`, `data`). |
| `list_project_pages(root)` | The project's pages with their titles, read from the conversion cache only — nothing is converted or written. Pages not cached yet come back with `cached=False` and their id as title. |
| `describe_project_page(root, odt_path)` | One `.odt` of the project (a page or a post), e.g. the file picked in a file chooser: its `translation_key` (what `menu:` / `nav:` entries should reference) and its `menu_label` / `nav_label`. Converts just that file if it isn't cached. |
| `DevServer(root, watch=True, live_reload=None, ...)` | The non-blocking development server behind `serve`: `start()`, `stop()`, `rebuild()`, `status()`. A frontend with its own file watcher passes `watch=False, live_reload=True` and calls `rebuild()` itself. `discover_watch_paths(root)` and `watch_backend_available()` support it. |

`PageInfo` has `id`, `kind`, `translation_key`, `lang`, `title`, `menu_title`,
`nav_title`, `cached`, and the `menu_label` / `nav_label` properties (the
label each of them would show, with the same fallback to the title).