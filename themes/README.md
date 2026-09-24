> Themes I am working on involving proof-of-concept resources, pretty much broken now.

## Theme Structure

```
theme
├── base.html
├── css
│   ├── dark.css
│   └── light.css
├── i18n.yaml    
├── js
│   └── nav.js
├── layouts
│   ├── 404.html
│   ├── blog.html
│   ├── page.html
│   ├── post.html
│   ├── taxonomy_index.html
│   └── taxonomy_term.html
├── partials
│   ├── _breadcrumbs.html
│   ├── _footer.html
│   ├── _header.html
│   ├── _lang_switcher.html
│   ├── _nav.html
│   ├── _site_menu.html
│   ├── _social_links.html
│   └── _toc.html
├── README.md
└── theme.yaml
```

# Asteria — Template Context Reference

Everything a theme (Jinja2 templates in `themes/<name>/`) can read: global
functions/filters, the objects passed into `render_template()`, and which
keys are available in which template. Jinja runs with `StrictUndefined`, so
referencing anything not listed here raises an error instead of silently
rendering empty — always check this list (or `site`/`theme`'s own fields)
before using a variable in a new theme you're adapting.

## 1. Global functions & filters

Available in every template, regardless of which one.

| Name | Kind | Description |
|---|---|---|
| `asset(path)` | global | Resolves a `/css/style.css`-style path to its fingerprinted output name (`/css/style.a1b2c3.css`) when `assets.fingerprint` is on. Identity function otherwise. Always call this for anything under the theme's `css/`, `js/`, `fonts/`, `images/` folders. |
| `slug` | filter | `{{ text\|slug }}` → same slugify used internally for URLs/heading IDs (lowercase, accents stripped, non-alphanumerics collapsed to `-`). |
| `safe_content` | filter | Marks a string as safe HTML (skips autoescaping). Used internally to build `content`; only call it yourself on HTML you generated/trust. |
| `nav_branch_active(entry, path)` | global | `true` if `entry.url == path`, or if any of `entry.children` (recursively) matches. Built for `site.nav` (`NavEntry` objects). |
| `menu_item_active(item, path)` | global | `true` if `item.url == path`. Same idea as `nav_branch_active`, for the flat `site.menu` dicts — no recursion needed since menu items have no children. |

Jinja itself also provides `truncate`, `striptags`, `wordcount`, `length`,
`first`/`last`, `sort`, `groupby`, etc. — no need to reinvent these.

## 2. `site` — sitewide data (`templating.SiteView`)

Present in **every** template.

| Key | Type | Description |
|---|---|---|
| `site.title` | str | From `site.yaml` `site.title`. |
| `site.description` | str | Site description/tagline. |
| `site.url` | str | Base URL, no trailing slash. |
| `site.language` | str | Site's primary language code. |
| `site.blog_index_url` | str | URL of the blog listing in the *current* language (`/blog/`, or `/pt/blog/`). |
| `site.blog_index_urls` | dict[lang, str] | Blog index URL for every configured language — for a language switcher. |
| `site.feed_url` | str \| None | `/rss.xml` or `/atom.xml`, or `None` if `feeds.enabled: false`. |
| `site.languages` | list[str] | Default language first, then the rest of `i18n.languages`. |
| `site.default_language` | str | The site's default language code. |
| `site.menu` | list[dict] | Flat top-level menu, from `menu:` in `site.yaml`. Each item: `{title, url, page_id}`. |
| `site.nav` | list[`NavEntry`] | Hierarchical sidebar navigation, from `nav:` in `site.yaml`. See §5. |
| `site.social` | list[`SocialLink`] | Footer/social links, from `social:` in `site.yaml`. See §5. |
| `site.categories` | list[`Term`] | Every category used by any post in the current language, with post counts — for a sidebar/browse-by-category widget on *any* page, not just the taxonomy index. See §5. |
| `site.tags` | list[`Term`] | Same, for tags. |
| `site.featured_pages` | list[`Page`] | Pages with `featured: true` in front matter, current language. |
| `site.featured_posts` | list[`Post`] | Posts with `featured: true` in front matter, current language. |
| `site.pages` | list[`Page`] | Every page in the current language, unfiltered, in discovery order. For a "recent posts" widget in a sidebar or footer shown on *any* page — not just `blog.html`. |
| `site.posts` | list[`Post`] | Every post in the current language, unfiltered, newest-first. |

`site.menu`, `site.nav`, `site.categories`, `site.tags`,
`site.featured_pages`, `site.featured_posts`, `site.pages` and
`site.posts` are swapped per-language automatically — a template never
needs to filter these by `lang` itself.

## 3. `theme` — theme-exclusive settings (`theme.yaml` + `theme.params` override)

Present in every template. Content is whatever the theme's own
`theme.yaml` defines (colors, layout toggles, etc.), plus two keys Asteria
always guarantees:

| Key | Type | Description |
|---|---|---|
| `theme.sidebar_toc` | bool | Default: `true`. Whether the theme should show a table-of-contents sidebar (still gated per-document by `show_toc`, see §6). |
| `theme.default_variant` | str | Default: `"light"`. Fallback CSS variant name when a document doesn't set its own `variant:`. |
| `theme.<anything else>` | — | Whatever the theme's `theme.yaml` declares — e.g. `theme.accent_color`, `theme.show_author_bio`. Check that specific theme's `theme.yaml`. |

## 4. Document objects (`page`, `post`, and items inside `posts`, `pagination.items`, `term.posts`, `site.featured_pages`, `site.featured_posts`)

`Page` and `Post` share this exact shape (`document.Document`).

| Key | Type | Description |
|---|---|---|
| `.id` | str | Filename without extension; unique across the whole site. |
| `.kind` | str | `"page"` or `"post"`. |
| `.title` | str | From front matter `title:`, falls back to `.id`. |
| `.date` | str \| None | Raw string from front matter `date:` (no parsing/formatting done by Asteria). |
| `.author` | str \| None | Plain string from front matter `author:`. |
| `.tags` | list[str] | Plain strings from front matter `tags:` (comma-separated). For clickable links with counts, use `site.tags` (`Term` objects) instead. |
| `.categories` | list[str] | Same, for `categories:`. |
| `.description` | str | From front matter `description:`. |
| `.slug` | str | URL slug — explicit `slug:` override, or auto-slugified id. |
| `.url` | str | Final absolute URL, language-prefixed if applicable. |
| `.variant` | str \| None | Per-document CSS variant override (`variant:` in front matter). |
| `.featured` | bool | `featured: true` in front matter. |
| `.cover` | str \| None | Cover image path (`cover:` in front matter), normalized to start with `/`. Never extracted from the `.odt` body — always a separate asset. Wrap with `asset()` if it lives under the theme's fingerprinted folders. |
| `.template` | str \| None | Explicit template override (`template:` in front matter), e.g. `"wiki.html"`. |
| `.toc_enabled` | bool | Whether auto-TOC is on for this doc (`toc:` in front matter, default `true`). |
| `.navigation_enabled` | bool | Whether the `site.nav` sidebar should show on this doc (`navigation:` in front matter, default `false`). |
| `.toc` | list[`TocEntry`] | The generated heading tree (only meaningful if `.toc_enabled`). |
| `.content` | str | Raw HTML string (**not** autoescape-safe on its own — inside `page.html`/`post.html` prefer the pre-wrapped `content` context variable, §6). |
| `.excerpt` | str | Manual (`[[more]]`) excerpt if present, else description, else an auto-truncated plain-text summary (HTML stripped) up to `blog.excerpt_length` chars. |
| `.word_count` | int | Approximate word count of the rendered content, HTML tags stripped. Whitespace-based — a rough count on CJK-style scripts without spaces. |
| `.reading_time` | int | Estimated reading time in whole minutes, rounded up, at ~200 words/minute (same figure Hugo's `.ReadingTime` defaults to). Always at least `1`. |
| `.lang` | str | Document's resolved language code. |
| `.translation_key` | str | Groups this doc with its translations. |
| `.translations` | dict[lang, Document] | Other language versions of this same document, keyed by language. |
| `.previous` / `.next` | Post \| None | Chronologically adjacent post in the same language (posts only — always `None` on pages). |

## 5. Supporting objects

**`Term`** (`site.categories` / `site.tags` / `taxonomy_index.html`'s `terms` / `taxonomy_term.html`'s `term`):

| Key | Description |
|---|---|
| `.name` | Display name (first spelling encountered). |
| `.slug` | URL slug. |
| `.url` | Full URL to that term's page. |
| `.posts` | Posts tagged with this term, newest first. |

**`NavEntry`** (`site.nav`, recursive):
`.title`, `.url` (str \| None — a pure section header has no URL of its own), `.children` (list[`NavEntry`]).

**`SocialLink`** (`site.social`):
`.platform`, `.url`, `.label`.

**Pagination `Page`** (`blog.html`'s `pagination`; **note**: unrelated to the `document.Page` class, just an unfortunate name collision internal to Asteria):
`.items` (posts on this page), `.number`, `.total_pages`, `.url`, `.prev_url`, `.next_url` (either `None` at the ends).

**`TocEntry`** (`.toc`, recursive):
`.id` (heading anchor), `.title`, `.level` (1–6), `.children`.


## 6. Context available per template

| Key | `page.html` / `post.html` / custom (`template:`) | `blog.html` | `taxonomy_index.html` | `taxonomy_term.html` | `404.html` |
|---|:---:|:---:|:---:|:---:|:---:|
| `site`, `theme` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `theme_css` | ✅ (doc's `variant` or theme default) | ✅ | ✅ | ✅ | ✅ |
| `canonical_path` | ✅ | ✅ | ✅ | ✅ | ✅ (`/404.html`) |
| `og_type` | ✅ (`article`/`website`) | ✅ (`website`) | ✅ (`website`) | ✅ (`website`) | ✅ (`website`) |
| `show_navigation` | ✅ | ❌ (always `false`) | ❌ | ❌ | ❌ |
| `breadcrumbs` | ✅ | ✅ | ✅ | ✅ | ✅ (empty) |
| `lang` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `page`, `post` | ✅ (both point to the *same* `Document`, regardless of kind) | ❌ | ❌ | ❌ | ❌ |
| `content` | ✅ (`Markup`-wrapped, safe to output directly) | ❌ | ❌ | ❌ | ❌ |
| `show_toc` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `posts` | ❌ | ✅ (current page's items) | ❌ | ✅ (`term.posts`) | ❌ |
| `pagination` | ❌ | ✅ | ❌ | ❌ | ❌ |
| `terms` | ❌ | ❌ | ✅ | ❌ | ❌ |
| `term`, `kind_label` | ❌ | ❌ | ✅ (`kind_label` only) | ✅ | ❌ |