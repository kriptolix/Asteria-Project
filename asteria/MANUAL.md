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

---

## 1. Requirements

- Python 3.11+ (the codebase uses `from __future__ import annotations` and
  modern type-hint syntax such as `str | None`).
- A working `odt2web` installation for the default converter (`asteria build`
  uses it unless you pick `--converter fallback` for quick tests — see
  [CLI reference](#5-cli-reference)).
- Jinja2, PyYAML — installed automatically as dependencies of the package.

## 2. Installation

Install the package from your project (however you distribute/package it —
e.g. `pip install asteria` or `pip install -e .` from a local checkout), then
confirm it's on your `PATH`:

```bash
asteria --help
```

## 3. Quick start

```bash
# 1. Scaffold a new project. With no argument, it creates ./my_site
asteria new
# ...or give it an explicit name/path:
asteria new blog-example

cd my_site

# 2. Serve it locally, with live rebuild on file changes
asteria serve

# 3. When you're ready, build the final static site
asteria build
```

The generated project comes with a starter page
(`source/content/pages/welcome.odt`) you can edit or delete.

## 4. Project structure

`asteria new` scaffolds this layout:

```
my_site/
└── source/                    # everything you edit lives here
    ├── site.yaml               # site-wide configuration
    ├── content/
    │   ├── pages/               # standalone pages (*.odt)
    │   └── posts/                # blog posts (*.odt)
    ├── static/                  # copied as-is to the output root
    └── themes/
        └── minimal/              # the active theme
            ├── theme.yaml
            ├── base.html
            ├── page.html
            ├── post.html
            ├── blog.html
            ├── taxonomy_index.html
            ├── taxonomy_term.html
            ├── 404.html
            ├── _nav.html
            ├── css/
            ├── js/
            ├── fonts/
            └── images/
```

By default, `asteria build` writes the generated site to `my_site/result/`
(a sibling of `source/` — see `output.directory` in the
[configuration reference](#6-configuration-siteyaml)).

All Asteria CLI commands are run against a **project root** — the directory
that *contains* `source/`, not `source/` itself. The default project root is
the current directory (`--project .`).

## 5. CLI reference

The `--project` flag is global and must come **before** the subcommand:

```bash
asteria --project /path/to/my_site build
```

If omitted, `--project` defaults to `.` (the current directory).

| Command | Description |
|---|---|
| `asteria new [path]` | Scaffolds a new project at `path`. If `path` is omitted, defaults to `./my_site`. Fails if the target directory already exists and is not empty. |
| `asteria build [--converter {auto,odt2web}]` | Converts all content and writes the full site to `output.directory`. Exits non-zero on any error-level diagnostic. |
| `asteria check [--converter {auto,odt2web}]` | Runs the exact same pipeline as `build` (parses YAML, converts every ODT, resolves IDs/references) but **writes nothing to disk**. Use it in CI or before committing content. |
| `asteria serve [--host HOST] [--port PORT] [--converter {auto,odt2web}] [--no-watch]` | Builds the site and serves it locally. `--host` defaults to `127.0.0.1`, `--port` to `8000`. By default it watches `content/`, `static/`, `themes/`, and `site.yaml` and rebuilds automatically; pass `--no-watch` to disable that. |
| `asteria clean [--cache]` | Deletes the output directory (`output.directory`). With `--cache`, also deletes the incremental conversion cache file (`.asteria-cache.json`) in the project root. |

The `--converter` flag selects the ODT→HTML converter. `auto` and `odt2web`
are equivalent today (both use the `odt2web` library); `build`'s default is
`odt2web` while `serve`/`check` default to `auto` — in practice this makes no
difference.

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
| `language` | `"en"` | Fallback/default site language (see [i18n](#11-multi-language-content-i18n); `i18n.default_language` overrides this specifically for content language routing). |
| `home_page` | `"welcome"` | The `id` of the page to serve at `/` (the filename without extension, e.g. `welcome` for `welcome.odt`). Use the special value `blog` to make the blog index the home page instead. |

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
puts it in `my_site/result/`, next to `source/`). An absolute path is also
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
```

`name` selects the theme directory: Asteria looks for
`source/themes/<name>/`. If that directory doesn't exist, Asteria falls back
to its own bundled `minimal` theme.

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
  default_language: ""
```

See [Multi-language content](#11-multi-language-content-i18n) for the full
explanation. In short: `default_language` (falls back to `site.language` if
empty) is the language with no URL prefix; `languages` lists any *additional*
languages your pages/posts may be written in.

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
[front matter](#71-front-matter-reference)). All values must be a path
starting with `/`; a trailing slash is added automatically if missing (unless
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
the default language, containing the most recent posts (title, link,
publish date, and excerpt) of that language. Additional languages get their
own feed named `{lang}-rss.xml` / `{lang}-atom.xml`.

### 6.11 `sitemap`

```yaml
sitemap:
  enabled: true
```

Writes `sitemap.xml` at the output root, listing every page, post, blog
index page, taxonomy page, and language-specific home page that was
generated.

### 6.12 `robots`

```yaml
robots:
  enabled: true
```

Writes `robots.txt` at the output root (`User-agent: * / Allow: /`), plus a
`Sitemap:` line pointing at `sitemap.xml` if `sitemap.enabled` is also true.

### 6.13 Full example

```yaml
site:
  title: "Asteria Docs"
  description: "Documentation and updates for the Asteria SSG."
  url: "https://docs.example.com"
  language: "en"
  home_page: "welcome"

blog:
  posts_per_page: 8
  excerpt_length: 220

i18n:
  languages: ["pt", "es"]
  default_language: "en"

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
| `date` | text | — | Publish date. Use `YYYY-MM-DD` (sorts correctly and is understood by the feed generator); `YYYY-MM-DDTHH:MM:SS` and `YYYY-MM-DDTHH:MM:SS±HHMM` are also accepted for feeds specifically. |
| `author` | text | — | Author name. |
| `tags` | comma-separated list | `[]` | Post tags — generates individual tag pages plus a tag index. Pages ignore this. |
| `categories` | comma-separated list | `[]` | Same as `tags`, under `/categories/`. |
| `description` | text | `""` | Short summary. Used as the excerpt when `blog.excerpt_enabled: false` (see [Blog excerpts](#10-blog-excerpts)), and available to theme templates for meta description overrides. |
| `slug` | text | slugified `id` | Overrides the automatic URL slug. |
| `variant` | text | theme's `default_variant` | Selects an alternate stylesheet, `css/{variant}.css`, for this document only. |
| `toc` | boolean | `true` | Enables automatic heading IDs and a table-of-contents tree for this document (exposed to templates as `page.toc` / `post.toc`). |
| `navigation` | boolean | `false` | Shows the theme's sidebar navigation (`theme.nav`) on this document. |
| `lang` | text | detected from filename | Explicitly sets this document's language, overriding the filename-based detection (see [i18n](#11-multi-language-content-i18n)). |

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
  containing an `index.html` (plus any assets it needs). Asteria copies the
  whole folder as-is to the corresponding URL, without any conversion. This
  is useful for publishing externally-built content (an exported prototype,
  a WebGL build, etc.) at its own URL, which you can then link to normally
  with `[[its-id]]`.

  Optionally add a `raw.yaml` inside that folder:

  ```yaml
  title: "Interactive Demo"
  ```

  `title` is used for menus/navigation labels and as the link text for
  `[[its-id]]` references. Raw pages do **not** currently participate in
  multi-language routing (see [limitations](#15-known-limitations)).

## 9. Internal references

Anywhere in a document's body, reference another page or post by its `id`:

| Syntax | Result |
|---|---|
| `[[some-id]]` | A link (`<a href="...">`) to that document, using its title as the link text. |
| `[[some-id\|Custom label]]` | Same link, with custom link text. |
| `\[[some-id]]` | Escaped — renders the literal text `[[some-id]]` instead of resolving it. |

If the referenced `id` doesn't exist, Asteria reports an error diagnostic
(visible in `asteria build`/`asteria check` output) and renders a visible
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
translation that exists — the same resolution `menu:` uses (see
[`menu`](#131-themeyaml)). You don't need to hardcode a language-specific id
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
i18n:
  default_language: "en"    # falls back to site.language if empty
  languages: ["pt", "es"]   # any *additional* languages besides the default
```

`default_language` is served with clean, unprefixed URLs. Every other
language listed in `languages` is served under a `/{lang}/` prefix.

### 11.2 Naming translated files

Name the default-language file normally, and add the language code as an
extra extension segment for translations:

```
content/posts/hello-world.odt       -> default language (e.g. "en")
content/posts/hello-world.pt.odt    -> "pt" translation
content/posts/hello-world.es.odt    -> "es" translation

content/pages/about.odt
content/pages/about.pt.odt
```

All three files share the same **slug** (`hello-world` / `about`), and are
linked to each other as translations of one another — but keep **distinct
IDs** (`hello-world`, `hello-world.pt`, `hello-world.es`), since the ID is
the full filename stem.

Alternatively (or additionally), set `lang: pt` explicitly in the front
matter — it takes priority over whatever the filename implies. This is handy
if you don't want the dotted-filename convention, though see the ID caveat
in [limitations](#15-known-limitations) if you rename the file to avoid the
dot.

If a document's language isn't listed under `i18n.languages` (or isn't the
default), Asteria still builds it, but emits a warning: it won't get a
language URL prefix and won't be grouped with the site's other languages.

### 11.3 What gets localized automatically

For every language in `i18n.languages` (including the default):

- **Post and page URLs** get the `/{lang}/` prefix (default language
  excluded).
- **The blog index** (`/blog/`, `/{lang}/blog/`, with pagination) only lists
  posts in that language.
- **Tags and categories** (index pages and individual term pages) are
  computed per language, so a tag cloud never mixes posts from different
  languages.
- **RSS/Atom feeds** are generated per language (see [`feeds`](#610-feeds)).
- **`previous`/`next` post navigation** never crosses a language boundary.
- **The home page** (`site.home_page`) gets a version for every language
  that has one available:
  - If `home_page` points to a page ID, each language uses that page's
    *translation* in that language (via the mechanism above) as its `/`
    (or `/{lang}/`) index — silently skipped for a language that has no
    translation of that page.
  - If `home_page: blog`, each language's own blog page 1 becomes that
    language's home.
- **`sitemap.xml`** includes every language-specific home, blog index,
  taxonomy page, and content URL.

### 11.4 What templates get for free

- `page.lang` / `post.lang` — the document's language code.
- `page.translations` / `post.translations` — a `{lang: Document}` dict of
  this document's other language versions (empty if there are none).
- `site.languages` — the full list of configured language codes (default
  first).
- `site.default_language`.
- `site.blog_index_urls` — a `{lang: url}` dict, useful as a fallback target
  for a language switcher on pages that have no direct translation.
- The bundled `base.html` already implements a language switcher and
  `hreflang` alternate `<link>` tags using exactly these variables — see
  [Theming](#13-theming) if you're customizing it.

## 12. Asset fingerprinting (cache busting)

```yaml
assets:
  fingerprint: true   # default
```

When enabled, every file under the theme's `css/`, `js/`, `fonts/`, and
`images/` output directories is renamed with a hash of its content, e.g.
`style.css` → `style.a1b2c3d4e5.css`. Because the hash is derived from the
file's content, it changes automatically whenever you edit the file — which
means the browser never serves a stale cached copy during `asteria serve`,
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

Files under `static/` that live **outside** those four subfolders (e.g.
`static/favicon.ico`, `static/robots.txt` overrides) are **not**
fingerprinted, since they're typically referenced by a fixed, well-known
name. A manifest of every rename is also written to
`asset-manifest.json` at the output root, for debugging or for external
tooling.

Set `assets.fingerprint: false` to disable this entirely and serve assets
under their original names.

## 13. Theming

A theme is a directory under `source/themes/<name>/` containing:

| File | Purpose |
|---|---|
| `theme.yaml` | Theme configuration (menu, navigation, social links, variants — see below). |
| `base.html` | The shared HTML shell every other template extends. |
| `page.html` | Renders a single page. |
| `post.html` | Renders a single post. |
| `blog.html` | Renders one page of the paginated blog index. |
| `taxonomy_index.html` | Renders the tag/category index (used for both `/tags/` and `/categories/`, distinguished by `kind_label`). |
| `taxonomy_term.html` | Renders a single tag/category page and its posts. |
| `404.html` | Renders the not-found page. |
| `_nav.html` | Must define a `render_nav(items, current_path)` Jinja macro, imported by `base.html` for the sidebar navigation. |
| `css/`, `js/`, `fonts/`, `images/` | Static theme assets, copied to the output and optionally fingerprinted (see previous section). |

### 13.1 `theme.yaml`

```yaml
subtitle: "Notes on static sites"
sidebar_toc: true
default_variant: "light"

menu:
  - page: "welcome"
    title: "Home"
  - page: "about"         # resolves per-language automatically (translation_key)
    title: "About"
  - page: "about.pt"      # pins this one item to the pt version, always
    title: "Sobre (PT)"
  - page: "blog"          # special: links to the blog index

nav:
  - "welcome"
  - "Documentation":
      - "docs-index"       # first item becomes the section's own link
      - "installation"
      - "usage"

social:
  - platform: "github"
    url: "https://github.com/you/your-repo"
    label: "GitHub"
  - platform: "mastodon"
    url: "https://mastodon.social/@you"
    label: "Mastodon"
```

| Key | Meaning |
|---|---|
| `subtitle` | Optional tagline shown under the site title in `base.html`. |
| `sidebar_toc` | Default: `true`. Whether the automatic table-of-contents sidebar is shown at all (still gated per-document by front matter `toc:`). |
| `default_variant` | Default: `"light"`. Selects `css/{variant}.css` when a document doesn't set its own `variant:` front matter. |
| `menu` | Top navigation bar. Each entry needs `page` and optionally `title` (defaults to `page`). `page` is resolved as a **translation_key** first — so `page: about` automatically links to whichever translation of "about" matches the language of the page currently being rendered, falling back to the site's default language, and finally to any translation that exists. If no translation_key matches, `page` is tried as an **exact document id** instead (e.g. `page: "about.pt"`) — use this form to pin a menu item to one specific translation regardless of the current language, or to reference an untranslated document. The special value `blog` links to that language's blog index (see [`urls`](#69-urls) for where that URL comes from). If there are posts, `home_page` isn't the blog, and you haven't added a `blog` entry yourself, Asteria adds one automatically (also correctly localized per language). A `page`/`translation_key` that resolves to nothing produces a build warning and a `#` link. |
| `nav` | Sidebar navigation tree, shown on documents with `navigation: true` in front matter. Entries are page IDs (strings) or `{"Section title": [...]}` for nested sections — if the first child of a section is a plain ID, it becomes the section heading's own link. Every id (leaf entries and section-index entries alike) is resolved exactly like `menu`'s `page:` above: **translation_key first** (so `- "about"` follows the current document's language, falling back to the default language and then to any translation), **exact document id second** (e.g. `- "about.pt"` to pin one specific translation). An id that resolves to nothing produces a build warning; the entry is still shown, with no link. |
| `social` | Footer social links. Each entry needs `platform` (used to look up `images/{platform}.svg` in the theme), `url`, and `label` (used for the accessible name/tooltip). |

Any other top-level key you add to `theme.yaml` is passed through untouched
and available in templates as `theme.your_key`.

### 13.2 Template context variables

Available on **every** page (via `base.html`, unless noted):

| Variable | Type / notes |
|---|---|
| `site` | `title`, `description`, `url`, `language`, `blog_index_url`, `feed_url`, `languages`, `default_language`, `blog_index_urls` |
| `theme` | The merged `theme.yaml` dict, plus resolved `menu`, `nav`, `social` |
| `theme_css` | The CSS variant name to load (without extension) |
| `canonical_path` | This page's own path, e.g. `/blog/hello-world/` |
| `og_type` | `"article"` for posts, `"website"` otherwise |
| `show_toc` / `show_navigation` | Booleans, already combining the theme default and the document's own front matter |
| `breadcrumbs` | List of `{title, url}`, last entry is the current page (not linked) |
| `lang` | This page's language code (defaults to `site.default_language` when not applicable, e.g. on the 404 page) |

Additional variables per template:

- **`page.html`**: `page` (the current `Document`), `content` (safe HTML).
- **`post.html`**: `post` (same object as `page`, both keys are always set to
  the current document so templates can use whichever name reads better),
  `content`.
- **`blog.html`**: `posts` (the current page's items), `pagination`
  (`items`, `number`, `total_pages`, `url`, `prev_url`, `next_url`).
- **`taxonomy_index.html`**: `terms` (each with `name`, `slug`, `url`,
  `posts`), `kind_label` (`"Tags"` or `"Categorias"` — a display label, not
  an i18n key).
- **`taxonomy_term.html`**: `term`, `posts`, `kind_label`.

### 13.3 Available filters and globals

| Name | Use |
|---|---|
| `{{ value \| safe_content }}` | Marks a trusted HTML string (already generated by the pipeline, e.g. `content`) safe to render without escaping. |
| `{{ text \| slug }}` | Slugifies arbitrary text the same way Asteria slugifies filenames. |
| `{{ asset('/css/style.css') }}` | Resolves a static asset path through the fingerprint manifest — see [section 12](#12-asset-fingerprinting-cache-busting). |
| `{{ nav_branch_active(entry, canonical_path) }}` | Returns `true` if `entry` (a nav item) or any of its descendants matches the current path — useful for highlighting the active section in `_nav.html`. |

## 14. Feeds, sitemap, and robots.txt

These are generated automatically at the output root according to the
`feeds`, `sitemap`, and `robots` config blocks documented in
[section 6](#6-configuration-siteyaml) — there is nothing to write by hand
for these, only configuration to adjust.

## 15. Known limitations

- **Raw HTML pages are not localized.** Folders containing an `index.html`
  (see [section 8](#8-pages-posts-and-raw-html-pages)) don't participate in
  language detection, prefixing, or the translations mechanism — so they
  also aren't resolvable as a translation_key from `[[...]]`, `menu:`, or
  `nav:`, only by their own exact id.