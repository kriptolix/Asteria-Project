> Themes I am working on involving proof-of-concept resources. None of them are working; most were created during various stages of Asteria's development and haven't been adapted to the current version.

## Theme Structure

```
theme
├── base.html
├── css
│   ├── dark.css
│   └── light.css
├── fonts                  (optional)
├── i18n.yaml              (optional: UI string translations, see `t()`)
├── images                 (optional: e.g. social icons, `<platform>.svg`)
├── js
│   └── nav.js
├── layouts
│   ├── 404.html
│   ├── blog.html
│   ├── page.html
│   ├── post.html
│   ├── taxonomy_index.html
│   └── taxonomy_term.html
├── partials
│   ├── _breadcrumbs.html
│   ├── _footer.html
│   ├── _header.html
│   ├── _lang_switcher.html
│   ├── _nav.html
│   ├── _site_menu.html
│   ├── _social_links.html
│   └── _toc.html
├── README.md
└── theme.yaml             (optional)
```

Template names are relative to the theme folder (`{% extends "base.html" %}`,
`{% import "partials/_nav.html" as nav %}`). Asteria itself only requires the
six files in `layouts/` — it renders `layouts/page.html`, `layouts/post.html`,
`layouts/blog.html`, `layouts/taxonomy_index.html`,
`layouts/taxonomy_term.html` and `layouts/404.html` by those exact names. A
document can use another layout with `template: layouts/<name>.html` in its
front matter. `base.html` and `partials/` are just the usual way to share
markup between them.

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
| `format_date(raw, lang, style)` | filter | `{{ post.date \| format_date(post.lang, "short") }}`. Formats a front matter `date:` for a reader of `lang`. `style` is `"long"` (default: `15 de março de 2024`, `March 15, 2024`), `"short"` (`15/03/2024`, but `03/15/2024` in English) or any `strftime` pattern. Month names and word order exist for `pt-BR`, `pt`, `es`, `en` and `fr`; any other language falls back to English. A value that isn't a recognised date is returned unchanged. |
| `t(key, lang, **kwargs)` | global | A UI string from the theme's `i18n.yaml` (merged with `i18n.strings` from `site.yaml`), in `lang` — falling back to the site's default language. `{placeholders}` in the string are filled from `kwargs`: `{{ t("reading_time", post.lang, minutes=post.reading_time) }}`. A key that exists in neither language renders as `??key??`; pass `fallback="text"` to render that text instead. |
| `current_year` | global | The year the site was built (for footers). |

Jinja itself also provides `truncate`, `striptags`, `wordcount`, `length`,
`first`/`last`, `sort`, `groupby`, etc. — no need to reinvent these.

## 2. `site` — sitewide data (`templating.SiteView`)

Present in **every** template.

| Key | Type | Description |
|---|---|---|
| `site.title` | str | From `site.yaml` `site.title`. |
| `site.description` | str | Site description/tagline. |
| `site.url` | str | Base URL, no trailing slash. |
| `site.language` | str | The site's default language — the same value as `site.default_language` (both come from `site.language` in `site.yaml`). It is **not** the language of the page being rendered: use `lang` (§6) for that. |
| `site.blog_index_url` | str | URL of the blog listing in the **default** language (`/blog/`) — the same value on every page. For the current language use `site.blog_index_urls[lang]`. |
| `site.blog_index_urls` | dict[lang, str] | Blog index URL for every configured language — for a language switcher. |
| `site.feed_url` | str \| None | `/rss.xml` or `/atom.xml` (the default language's feed; other languages have `/{lang}-rss.xml` / `/{lang}-atom.xml`), or `None` if `feeds.enabled: false`. The same value on every page. |
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
| `site.tocs` | dict[str, list[`TocEntry`]] | The heading tree of every document in the current language whose table of contents is enabled (see `theme.toc` in §3 and `toc:` in front matter), keyed by the document's URL. `partials/_nav.html` uses it to nest a page's headings under its entry in the sidebar. |

`site.menu`, `site.nav`, `site.categories`, `site.tags`,
`site.featured_pages`, `site.featured_posts`, `site.pages`, `site.posts` and
`site.tocs` are swapped per-language automatically — a template never
needs to filter these by `lang` itself. Everything else
(`title`, `description`, `url`, `language`, `default_language`, `languages`,
`blog_index_url`, `blog_index_urls`, `feed_url`, `social`) is the same on every
page. On `404.html` the whole `site` is the default language's.

## 3. `theme` — theme-exclusive settings (`theme.yaml`)

Present in every template. It is exactly the content of the theme's own
`theme.yaml` and nothing more: Asteria adds no defaults, and there is no
site-level override layer (a theme without a `theme.yaml` gets an empty
`theme`). Because of `StrictUndefined`, read optional keys with a default:
`theme.default_variant | default("light")`.

Two keys are read by Asteria itself, to decide which optional features the
theme supports (they drive `show_toc` / `show_navigation`, see §6):

| Key | Type | Description |
|---|---|---|
| `theme.toc` | bool | Table-of-contents sidebar. Missing or empty = the theme doesn't support it, so `show_toc` is always `false`. `true` / `false` sets the default for every document, and a document's own `toc:` front matter overrides it either way. |
| `theme.navigation` | bool | Same, for the `site.nav` sidebar (`show_navigation`, which also needs a non-empty `site.nav`) and the `navigation:` front matter field. |
| `theme.<anything else>` | — | Whatever the theme declares. This theme's templates read `theme.default_variant` (CSS variant loaded when a document sets no `variant:`; `base.html` falls back to `"light"`) and `theme.known_platforms` (social platforms that have an icon at `images/<platform>.svg`; the others show their initials). |

## 4. Document objects (`page`, `post`, and items inside `posts`, `pagination.items`, `term.posts`, `site.featured_pages`, `site.featured_posts`)

`Page` and `Post` share this exact shape (`document.Document`).

| Key | Type | Description |
|---|---|---|
| `.id` | str | Filename without extension, so it **includes** a language suffix (`welcome.pt-BR`); unique across the whole site. |
| `.kind` | str | `"page"` or `"post"`. |
| `.title` | str | From front matter `title:`, falls back to `.id`. |
| `.date` | str \| None | Raw string from front matter `date:`. Posts are ordered by this string (so write `YYYY-MM-DD`); format it for display with the `format_date` filter (§1). |
| `.author` | str \| None | Plain string from front matter `author:`. |
| `.tags` | list[str] | Plain strings from front matter `tags:` (comma-separated). For clickable links with counts, use `site.tags` (`Term` objects) instead. |
| `.categories` | list[str] | Same, for `categories:`. |
| `.description` | str | From front matter `description:`. |
| `.slug` | str | URL slug — explicit `slug:` override, or the slugified `translation_key` (the filename without its language suffix), so all translations of a document share one slug. |
| `.url` | str | Final absolute URL, language-prefixed if applicable. |
| `.variant` | str \| None | Per-document CSS variant override (`variant:` in front matter). |
| `.featured` | bool | `featured: true` in front matter. |
| `.cover` | str \| None | Cover image path (`cover:` in front matter), normalized to start with `/`. Never extracted from the `.odt` body — always a separate asset. Wrap with `asset()` if it lives under the theme's fingerprinted folders. |
| `.template` | str \| None | Explicit layout override (`template:` in front matter): a path relative to the theme folder, e.g. `"layouts/wiki.html"`. A name that doesn't exist is a build error (the default layout is used instead). |
| `.menu_title` / `.nav_title` | str \| None | `menu_title:` / `nav_title:` front matter. Already applied to the labels in `site.menu` / `site.nav` (which fall back to `.title`), so templates rarely need them. |
| `.frontmatter` | `Frontmatter` | The parsed front matter block. `.frontmatter.extra` is a dict with every field Asteria doesn't know (e.g. `page.frontmatter.extra.subtitle`). |
| `.toc_enabled` | bool \| None | The document's own `toc:` override; `None` when it doesn't set one (inherit the theme's `theme.toc`). To know whether the TOC is actually shown, use `show_toc` (§6). |
| `.navigation_enabled` | bool \| None | The document's own `navigation:` override; `None` = inherit the theme's `theme.navigation`. To know whether the sidebar is actually shown, use `show_navigation` (§6). |
| `.toc` | list[`TocEntry`] | The generated heading tree. It is always built; whether the theme shows it is up to `show_toc` (§6). |
| `.content` | str | Raw HTML string (**not** autoescape-safe on its own — inside `page.html`/`post.html` prefer the pre-wrapped `content` context variable, §6). |
| `.excerpt` | str | With `blog.excerpt_enabled: false`: the `description`, else the title. Otherwise: the part of the post before its `[[more]]` marker (HTML, already marked safe) if it has one, else an auto-truncated plain-text summary (HTML stripped) up to `blog.excerpt_length` chars — even when a `description` is set. |
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
`.title`, `.url` (str \| None — `None` only for an entry whose id didn't resolve to any document; the build warns about it), `.children` (list[`NavEntry`]).

**`SocialLink`** (`site.social`):
`.platform`, `.url`, `.label`, `.initials` (short text to show for a platform that has no icon, see `partials/_social_links.html`).

**Pagination `Page`** (`blog.html`'s `pagination`; **note**: unrelated to the `document.Page` class, just an unfortunate name collision internal to Asteria):
`.items` (posts on this page), `.number`, `.total_pages`, `.url`, `.prev_url`, `.next_url` (either `None` at the ends).

**`TocEntry`** (`.toc`, recursive):
`.id` (heading anchor), `.title`, `.level` (1–6), `.children`.


## 6. Context available per template

Every template is rendered with the same base context, so a key marked ✅ in
the first rows exists in **all** of them. Only the last rows are specific to
one kind of template.

| Key | `page.html` / `post.html` / custom (`template:`) | `blog.html` | `taxonomy_index.html` | `taxonomy_term.html` | `404.html` |
|---|:---:|:---:|:---:|:---:|:---:|
| `site`, `theme` | ✅ | ✅ | ✅ | ✅ | ✅ (default language's `site`) |
| `lang` | ✅ the document's language | ✅ the listing's language | ✅ | ✅ | ✅ (the default language) |
| `canonical_path` | ✅ (`page.url`) | ✅ (that page of the listing) | ✅ | ✅ | ✅ (`/404.html`) |
| `og_type` | ✅ (`article` for posts, `website` for pages) | ✅ (`website`) | ✅ (`website`) | ✅ (`website`) | ✅ (`website`) |
| `show_navigation` | ✅ (see §3) | ✅ always `false` | ✅ always `false` | ✅ always `false` | ✅ always `false` |
| `breadcrumbs` | ✅ | ✅ | ✅ | ✅ | ✅ (empty) |
| `page`, `post` | ✅ (both point to the *same* `Document`, regardless of kind) | ❌ | ❌ | ❌ | ❌ |
| `content` | ✅ (`Markup`-wrapped, safe to output directly) | ❌ | ❌ | ❌ | ❌ |
| `show_toc` | ✅ (see §3) | ❌ | ❌ | ❌ | ❌ |
| `posts` | ❌ | ✅ (current page's items) | ❌ | ✅ (`term.posts`) | ❌ |
| `pagination` | ❌ | ✅ | ❌ | ❌ | ❌ |
| `terms` | ❌ | ❌ | ✅ | ❌ | ❌ |
| `term` | ❌ | ❌ | ❌ | ✅ | ❌ |
| `kind_label` | ❌ | ❌ | ✅ | ✅ | ❌ |

`kind_label` is the translated name of the taxonomy (`tags_label` /
`categories_label` in the theme's UI strings, falling back to `Tags` /
`Categories`), and the blog breadcrumb uses `blog_menu_label` (falling back to
`Blog`).

Things that are **not** context variables, even though a template may use
them:

- `theme_css` — `base.html` computes it itself (`{% set theme_css = ... %}`)
  from `page.variant` and `theme.default_variant`.
- `current_lang` — also a local of `base.html`
  (`{% set current_lang = lang if lang is defined else site.default_language %}`).

## 7. Gotchas when writing templates

- **Imported macros don't see the page's context.** `{% import "partials/_x.html" as x %}`
  imports *without* context: inside a macro only its own arguments, the
  globals from §1 and the macro file's own variables exist. `lang`, `page`,
  `post`, `site`, `theme`… are **not** there, and `StrictUndefined` turns
  that into `'…' is undefined`. Pass what a macro needs as arguments, e.g.
  `header.render_header(site, canonical_path, current_lang, translations)`.
  (`{% include %}` and `{% extends %}`/blocks do see the context.)
- **`page` / `post` only exist on document templates.** On the blog, the
  taxonomy pages and the 404 use `lang` for the language, and test
  `page is defined` before reading anything off `page`.
- **UI text belongs in `i18n.yaml`, in the language of the page.** Use
  `t("key", lang)` and never `site.language` for it: `site.language` is the
  default language, so every translated page would show the default
  language's text.
- **Links must follow the language too.** Don't hardcode `/` or `/tags/…`:
  the root of a non-default language is `/{lang}/`. Take URLs from the
  objects (`term.url`, `page.url`, `site.blog_index_urls[lang]`), which already
  carry the prefix.