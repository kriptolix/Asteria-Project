Asteria Documentation

Asteria is a Python Static Site Generator (SSG) whose only content source is ODT. ODT-to-HTML conversion is performed by the odt2web library.

1. Project Structure

A typical project contains:

my-site/
├── site.yaml
├── content/
│   ├── pages/
│   └── posts/
├── static/
├── theme/
│   └── minimal/
└── build/


The Python package itself is organized as follows:

asteria/
├── cli.py              CLI: build, clean, serve, check, new
├── config.py           site.yaml and fixed site.* namespace
├── theme_config.py     theme.yaml and free theme.* namespace
├── converter.py        ODTConverter, Odt2WebConverter, FallbackConverter
├── cache.py            incremental conversion cache
├── frontmatter.py      front matter extraction
├── document.py         Document / Page / Post models
├── discovery.py        content discovery
├── raw.py              raw HTML pages
├── references.py       [[id]] / escaped references
├── nav.py              hierarchical navigation
├── social.py           footer social links
├── taxonomy.py         tags and categories
├── pagination.py       blog pagination
├── toc.py              per-document table of contents
├── urls.py              slugification and centralized URL generation
├── templating.py       Jinja2 environment
├── writer.py            file writing and asset copying
├── sitemap.py           sitemap.xml generation
├── feed.py              RSS/Atom generation
├── server.py            development server, watch and live reload
├── scaffold.py          asteria new
├── odt_builder.py       ODT generation used by the scaffold
├── build.py             build pipeline orchestration
├── errors.py            diagnostics collection
└── themes/minimal/      bundled minimal theme

tests/                   pytest suite

2. Content Discovery
Pages

content/pages/ is recursive.

For example:

content/pages/
├── index.odt
└── guide/
    └── installation.odt


Subdirectories are organizational only. They do not affect document IDs or URLs.

Navigation between pages should use nav: rather than relying on the directory structure.

Posts

content/posts/ is intentionally flat. Posts are intended to form a chronological blog listing, so grouping them into subdirectories is not supported.

Document IDs

The filename without the .odt extension becomes the document ID.

For example:

content/pages/installation.odt


has the ID:

installation


IDs must be unique across pages, posts, and raw pages. Duplicate IDs are reported during the build.

3. Front Matter

Front matter is an optional block at the beginning of an ODT document:

---
title: My Article
date: 2026-01-01
author: John Doe
tags: python, web
categories: technology
description: A short summary
slug: custom-url
variant: dark
toc: false
navigation: true
---


All fields are optional.

Supported fields
title — document title.
date — publication date, primarily used by posts.
author — document author.
tags — document tags.
categories — document categories.
description — document description and SEO metadata.
slug — custom URL slug.
variant — CSS color variant for this document.
toc — enables/disables the automatic table of contents. Defaults to true.
navigation — enables/disables the nav: sidebar for this document. Defaults to false.

variant overrides the theme's default_variant.

4. Template Namespaces

Asteria intentionally separates site configuration from theme configuration.

site.*

site.* is a fixed namespace loaded from site.yaml.

The structure is stable and includes fields such as:

site.title
site.url
site.language
site.blog_index_url
site.feed_url
site.description


These fields always exist and have sensible defaults.

theme.*

theme.* is a free-form namespace defined by the active theme's:

theme/<name>/theme.yaml


Every key declared there becomes available as theme.<key>.

For example:

subtitle: "A blog about things"

menu:
  - page: about
    title: About


becomes:

theme.subtitle
theme.menu


Theme configuration can therefore expose arbitrary presentation-specific data such as menus, navigation, social links, colors, or custom values.

Strict Theme Variables

Asteria uses Jinja2 StrictUndefined.

If a template references:

{{ theme.subtitle }}


but subtitle is not declared in theme.yaml, the build fails with an explicit error.

There is no silent fallback to an empty value.

Theme authors must therefore declare every key used by their templates, even optional keys:

subtitle: ""
social: []


This allows themes to evolve independently without requiring changes to the Asteria core.

5. Theme Configuration

A complete example:

sidebar_toc: true
default_variant: light

subtitle: "A blog about things"

menu:
  - page: about
    title: About

nav:
  - home
  - User Guide:
      - installation
      - configuration
  - Custom Title: about

social:
  - platform: github
    url: "https://github.com/user"
  - platform: mastodon
    url: "https://mastodon.social/@user"
  - platform: email
    url: "mailto:contact@example.com"

menu

menu defines the header menu.

A menu item using:

page: about


references the document whose ID is about.

The special page ID blog refers to the blog index.

If posts exist and the home page is not the blog, Asteria automatically adds a Blog item at the end of the menu unless the menu already references page: blog.

nav

nav defines hierarchical sidebar navigation.

For example:

nav:
  - home
  - User Guide:
      - installation
      - configuration


Sections are rendered using native HTML <details> and <summary> elements, so no JavaScript is required for collapsing/expanding them.

The branch containing the current page is automatically expanded.

The sidebar is only displayed for documents with:

navigation: true


This is disabled by default to prevent blog posts from unexpectedly displaying the full site navigation.

nav is independent of menu.

social

Supported platforms include:

github
gitlab
twitter
x
mastodon
linkedin
youtube
instagram
facebook
discord
telegram
rss
email


Recognized platforms receive a built-in monogram SVG. Unknown platforms use a generic monogram based on their initials.

The icons are original drawings rather than copies of official platform logos.

6. Document References

Documents can reference each other using:

[[id]]


or:

[[id|Custom text]]


The first form automatically uses the referenced document's title.

To display the syntax literally, escape it:

\[[id]]


This produces:

[[id]]


without attempting to resolve the reference.

A reference to an unknown ID is a build error. The generated HTML also contains a visible:

<span class="broken-reference">


element to make the problem easy to locate.

7. Raw HTML Pages

Raw pages are intended for content that requires more control than ODT provides, such as completely custom HTML/CSS pages that should not inherit or leak theme styling.

A directory under content/pages/ or content/posts/ is considered a raw page when:

it contains no .odt files; and
it contains an index.html directly inside the directory.

Example:

content/pages/gallery/
├── index.html
├── style.css
└── js.js


The page is copied verbatim, byte-for-byte, to its corresponding URL.

8. Home Page

The home page is configured in site.yaml:

site:
  home_page: home


The value can also be:

site:
  home_page: blog


which makes the blog index the home page.

If home_page does not resolve to a valid document, Asteria emits a warning rather than an error. The rest of the site is still generated, but no root index.html is produced.

9. SEO and Distribution

Asteria automatically generates:

per-document <title> and meta descriptions, with site-level fallbacks;
canonical URLs;
basic Open Graph metadata;
sitemap.xml;
RSS 2.0 or Atom feeds;
robots.txt referencing the sitemap;
404.html from the active theme.

Open Graph uses:

og:title
og:description
og:type
og:url
og:site_name


og:type is article for posts and website for other pages.

Feed format is configured through:

feeds:
  format: rss


The resulting feed is:

/rss.xml


For Atom:

feeds:
  format: atom


produces:

/atom.xml

10. Incremental Builds

Asteria stores its incremental conversion cache in:

.asteria-cache.json


The cache is keyed by each ODT file's:

path;
modification time;
file size.

Only the ODT-to-HTML conversion step is cached.

This is intentional because conversion is the most expensive part of the pipeline and is where odt2web performs the actual document parsing.

The following stages still run completely on every build:

references;
table of contents;
navigation;
taxonomies;
blog pagination;
sitemap;
feeds;
template rendering.

This prevents stale cross-document data. For example, adding a new post must recalculate the previous/next relationship of an existing post.

The cache can be removed with:

asteria clean --cache

11. Color Variants

Themes can provide multiple CSS variants without changing HTML templates.

The bundled minimal theme provides:

css/light.css
css/dark.css


The site's default variant is configured in theme.yaml:

default_variant: dark


A single document can override it through front matter:

---
variant: dark
---


To create a new variant, add a CSS file:

theme/minimal/css/custom.css


It can import the light variant and override only the required color variables.

The new variant can then be selected with either:

default_variant: custom


or:

variant: custom

12. Themes

If the project contains:

theme/<name>/


Asteria uses that theme.

Otherwise, it falls back to the bundled:

asteria/themes/minimal/


asteria new copies the minimal theme into the new project so it can be customized directly.

site.yaml controls only:

which theme is selected (theme.name);
where the theme is located (theme.directory).

Theme-specific behavior such as:

default color variant;
menu;
navigation;
social links;
custom variables;

belongs in theme/<name>/theme.yaml.

13. Build Pipeline

The build process conceptually performs the following operations:

Load and validate site.yaml.
Load the selected theme and its theme.yaml.
Discover pages, posts, and raw pages.
Convert ODT documents to HTML.
Extract front matter.
Build the document model.
Validate unique IDs and references.
Resolve document references.
Build taxonomies.
Build navigation.
Generate table of contents.
Calculate blog pagination.
Render templates.
Generate sitemap and feeds.
Generate robots.txt and 404.html.
Write the resulting files and static assets.

asteria check executes the same validation/build logic but does not write generated files to disk.

14. CLI Development Commands
Build
asteria build


Generates the complete site under:

build/

Development Server
asteria serve


The development server:

builds the site;
serves build/ over HTTP;
watches content/, static/, theme/, and site.yaml;
automatically rebuilds after changes;
sends live-reload events to connected browsers.

Disable watching and live reload with:

asteria serve --no-watch

Validation
asteria check


The command reports the same errors and warnings as build without writing generated files, making it suitable for CI.

Cleaning
asteria clean


removes:

build/


while:

asteria clean --cache


also removes:

.asteria-cache.json

15. Scaffold
asteria new my-site


creates:

site.yaml;
content/pages/;
content/posts/;
static/;
a copy of the default theme;
.gitignore;
an initial welcome page in .odt.

The command refuses to overwrite a non-empty directory.

The ODT welcome page is generated by odt_builder.py.

16. Converter Architecture

The conversion layer exposes an ODTConverter interface.

The primary implementation is:

Odt2WebConverter


which delegates ODT-to-HTML conversion to odt2web.

A:

FallbackConverter


exists primarily for testing and environments where the production converter is unavailable.

The converter is deliberately isolated from the rest of the build pipeline so the content processing and rendering layers do not depend directly on the conversion implementation.

17. Tests

Development dependencies can be installed with:

pip install -e ".[dev]"


The test suite uses pytest:

pytest


Tests cover the build pipeline, configuration, content discovery, references, navigation, themes, rendering, conversion, caching, feeds, and other core functionality.

18. Planned Features

The following features are not currently implemented:

Drafts (draft: true) with an option such as --drafts.
Syntax highlighting for code blocks.
Redirects from old URLs to new URLs.
i18n / multilingual sites.
Asset fingerprinting for cache busting.
Search infrastructure, such as a JavaScript search index.