# Asteria

**Asteria** is a static site generator that builds your pages and blog posts
straight from **OpenDocument Text (`.odt`)** files. Write in LibreOffice
Writer, Word, or any ODT-compatible editor — Asteria converts it into a
fast, themeable static site.

> Looking for the full configuration reference? See
> **[MANUAL.md](MANUAL.md)** for a complete guide covering every setting,
> front matter field, and template variable.

## Features

- **Write in ODT, not Markdown.** Headings, lists, tables, and images
  convert automatically — no learning curve for non-technical writers.
- **Pages and posts**, with tags, categories, pagination, and RSS/Atom
  feeds out of the box.
- **Multi-language content.** Translate any page or post with a simple
  filename convention; Asteria handles URL prefixes, per-language blog
  indexes, feeds, and a ready-made language switcher.
- **Cache-safe by default.** Static assets are automatically
  content-hashed, so browsers never serve a stale CSS/JS file during
  development or after a deploy.
- **Internal cross-references** (`[[page-id]]`) between your own content,
  validated at build time.
- **Live-reloading dev server** (`asteria serve`) that rebuilds on save.
- **Fully themeable** with plain Jinja2 templates.

## Requirements

- Python 3.11+
- The `odt2web` library (used by the default ODT→HTML converter)

## Installation

```bash
pip install asteria
```

*(or, from a local checkout: `pip install -e .`)*

## Quick start

```bash
# Scaffold a new project (defaults to ./my_site if no path is given)
asteria new my-blog
cd my-blog

# Serve locally with auto-rebuild on changes
asteria serve
# -> http://127.0.0.1:8000

# Build the final static site
asteria build
```

## Project structure

```
my-blog/
└── source/
    ├── site.yaml            # site configuration
    ├── content/
    │   ├── pages/            # standalone pages (*.odt)
    │   └── posts/             # blog posts (*.odt)
    ├── static/                # copied as-is to the site root
    └── themes/
        └── minimal/             # the active theme
```

`asteria build` writes the generated site to `my-blog/result/` by default.

## Basic usage

### Writing a page or post

Create an `.odt` file under `content/pages/` or `content/posts/`. Start it
with a front matter block, then write your content normally:

```
---
title: My First Post
date: 2024-03-15
author: Jane Doe
tags: hello, first-post
---

Welcome to my new blog! This is a regular paragraph, written like any
other document in your ODT editor.
```

The filename (without extension) becomes the page's unique ID and, by
default, its URL slug — `content/posts/my-first-post.odt` becomes
`/blog/my-first-post/`.

### Configuring your site

Edit `source/site.yaml`:

```yaml
site:
  title: "My Blog"
  description: "Thoughts on things I like."
  url: "https://myblog.example.com"
  home_page: "welcome"

blog:
  posts_per_page: 10
```

You only need to set the keys you want to change — everything else falls
back to sensible defaults. See **[MANUAL.md](MANUAL.md#6-configuration-siteyaml)**
for the full list of options (multi-language setup, feeds, sitemap,
URL patterns, asset fingerprinting, and more).

### Linking to your own content

```
See the [[getting-started]] guide for more details.
```

### CLI commands

| Command | What it does |
|---|---|
| `asteria new [path]` | Scaffold a new project (default: `./my_site`) |
| `asteria build` | Build the full static site |
| `asteria serve` | Build and serve locally, rebuilding on changes |
| `asteria check` | Validate content and configuration without writing any files |
| `asteria clean` | Remove the generated output (and optionally the build cache) |

Run `asteria <command> --help` for all available flags.

## Documentation

The **[complete manual](MANUAL.md)** covers:

- Every `site.yaml` option, with examples
- Front matter reference
- Multi-language content (i18n)
- Internal references
- Blog excerpts (`[[more]]`)
- Asset fingerprinting / cache busting
- Theming: required templates, available context variables, filters
- Known limitations

## License

Add your license of choice here (e.g. MIT).

## Contributing

Issues and pull requests are welcome.