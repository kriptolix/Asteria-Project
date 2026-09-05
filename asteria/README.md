Asteria

Asteria is a Python Static Site Generator (SSG) whose only content source is ODT. ODT-to-HTML conversion is handled by odt2web.

Getting Started
pip install -e .
pip install odt2web

asteria new my-site
cd my-site
asteria serve


asteria serve builds the site, starts a local HTTP server, watches for changes, and automatically rebuilds and reloads the browser.

Commands
Command	Description
asteria new <path> [--title]	Creates a new project with configuration, content directories, static assets, a customizable theme, and a welcome page.
asteria build [--converter]	Builds the site into build/.
asteria serve [--host] [--port] [--no-watch]	Builds and serves the site locally with automatic rebuild and live reload.
asteria check [--converter]	Runs the full validation/build pipeline without writing files. Useful for CI.
asteria clean [--cache]	Removes build/; with --cache, also removes the incremental build cache.
Content
content/pages/ contains recursive pages.
content/posts/ contains flat blog posts.
The filename without .odt is the document ID and must be unique across the entire site.
ODT documents may contain front matter for metadata and per-document options.
Documents can reference each other using [[id]] or [[id|custom text]].
HTML-only pages can be created using a directory containing an index.html and no .odt files.
Configuration

The site is configured through site.yaml. Theme-specific configuration lives in theme/<name>/theme.yaml.

Templates expose two namespaces:

site.* — fixed site configuration.
theme.* — theme-defined configuration.

Theme variables use Jinja2's StrictUndefined, so missing theme configuration causes a clear build error instead of silently rendering an empty value.

Themes

A project can provide its own theme/<name>/ directory. Otherwise, Asteria uses the bundled minimal theme.

Themes can define:

layouts and templates;
navigation and menus;
social links;
CSS color variants;
arbitrary theme-specific configuration.

The bundled minimal theme provides light and dark variants.

Development
pip install -e ".[dev]"
pytest


For architecture, content rules, configuration, themes, the build pipeline, and implementation details, see DOCUMENTATION.md.