# odt2web — CSS Classes Reference

This document lists every CSS class the converter can emit in its HTML
output, so you can write your own theme/stylesheet against them instead
of relying on the library's built-in `generate_css()` output (or in
addition to it — see [Using your own theme](#using-your-own-theme) at
the end).

Classes fall into two groups:

- **Fixed classes** — always named exactly as shown, emitted automatically
  based on document structure (columns, notes, images, etc.).
- **User-defined classes** — classes *you* choose via `style_map`, applied
  to whatever ODT paragraph/character styles you map them to. These aren't
  hard-coded by the library, but are covered here since they're the other
  half of how theming works.

---

## Images

Produced by `_render_image()`. Applied to the `<figure>` element when the
image has a caption, otherwise directly on the `<img>` element.

| Class | Meaning | When it appears |
|---|---|---|
| `odt-image` | Base marker class, always present on every image/figure. | Always |
| `odt-image-small` | Image's width (or height, if width is missing) is ≤ 6cm in the source document. | When width or height is known |
| `odt-image-medium` | Width/height is > 6cm and ≤ 12cm. | When width or height is known |
| `odt-image-large` | Width/height is > 12cm. | When width or height is known |
| `odt-image-landscape` | Width is greater than height. | When both width and height are known |
| `odt-image-portrait` | Height is greater than width. | When both width and height are known |
| `odt-image-square` | Width and height are (approximately) equal. | When both width and height are known |
| `odt-image-align-left` | Image was anchored/aligned left in the ODT. | When the frame's graphic style sets a resolvable horizontal position |
| `odt-image-align-center` | Image was anchored/aligned center in the ODT. | Same as above |
| `odt-image-align-right` | Image was anchored/aligned right in the ODT. | Same as above |

Notes:
- The size buckets are based on the *original* document's physical
  dimensions (cm), not the rendered pixel size — treat them as a rough
  "was this a small inline image or a big feature image" signal, not an
  exact measurement.
- Alignment is only set when the ODT frame's style resolves to a plain
  `left`/`center`/`right` horizontal position. Positions like "from left
  by Xcm" or mirrored-page "inside"/"outside" don't map to a fixed side,
  so no alignment class is added in those cases — style `.odt-image` as a
  sensible default for those.
- The exact original dimensions are still available as an inline
  `style="width:...; height:..."` on the `<img>` tag itself (not on the
  `<figure>`), independent of these classes.

Example output:
```html
<figure class="odt-image odt-image-small odt-image-landscape odt-image-align-right">
  <img src="assets/image-001.png" alt="" style="width:5cm; height:3cm">
  <figcaption>A caption</figcaption>
</figure>
```

---

## Multi-column sections

Produced by `render_section()`, on the wrapping `<section>` element for
any ODT section using more than one column.

| Class | Meaning |
|---|---|
| `odt-columns` | Base marker class for any multi-column section. |
| `odt-columns-N` | `N` is the actual column count (e.g. `odt-columns-2`, `odt-columns-3`). One such class is emitted per distinct column count used in the document. |

Example output:
```html
<section class="odt-columns odt-columns-2">
  ...
</section>
```

The library's own `generate_css()` will emit matching
`.odt-columns-N { column-count: N; ... }` rules using the actual
gap/rule values from the ODT if you keep `css=True`; if you supply your
own theme instead, target `.odt-columns-N` directly.

---

## Footnotes / endnotes

Produced by `render_inline()` (for the inline reference marker) and
`render_notes()` (for the notes list at the end of the document).

| Class | Applies to | Meaning |
|---|---|---|
| `odt-note-ref` | `<sup>` wrapping the inline footnote marker (e.g. `¹`) | Marks an inline note reference in the body text |
| `odt-notes` | `<section>` wrapping the full notes list | Marks the block of collected footnotes/endnotes at the end of the document |
| `odt-note-backref` | `<a>` inside each note's `<li>` | The "back to text" (↩) link at the end of each note |

Each note reference/list item also carries plain (non-class) `id`
attributes (`fnref-{id}` / `{id}`) used for the anchor links between
them — useful if you want to style `:target` states.

---

## Page breaks

Produced by `_render_page_break()`.

| Class | Applies to | Meaning |
|---|---|---|
| `odt-page-break` | `<hr>` | Marks an explicit page break from the source document (manual or "break before" on a paragraph style) |

---

## Raw HTML blocks (when disabled)

Produced by `_render_raw_html()` — **only** when a `:::html ... :::`
block exists in the document but `allow_raw_html=False` (the default).
In that case the content is shown as escaped text instead of being
injected as live HTML.

| Class | Applies to | Meaning |
|---|---|---|
| `odt-raw-html-disabled` | `<pre>` | Wraps the escaped, literal text of a raw-HTML block that was blocked because `allow_raw_html` wasn't enabled |

When `allow_raw_html=True`, the block's HTML is emitted as-is with no
wrapper or class — style whatever markup the block itself contains.

---

## Front matter

Produced by `render_front_matter()`, when the document starts with a
`---` delimited key/value block that gets extracted as front matter.

| Class | Applies to | Meaning |
|---|---|---|
| `ssg-frontmatter` | `<div>` (also carries `data-ssg="frontmatter"`) | Wraps the extracted front-matter fields, rendered as empty `<meta data-key="..." content="...">` tags for SSGs that want to read them back out of the HTML |

This block has no visible content by design (it's metadata, not body
text) — it typically doesn't need styling, but the class/attribute are
there if your SSG pipeline scans the HTML for them.

---

## Inline character styles (no built-in formatting)

Produced by `_render_inline_node()` for `Span`s that carry a named ODT
character style but none of the recognized formatting flags (bold,
italic, underline, strikethrough, super/subscript, code).

| Class | Applies to | Meaning |
|---|---|---|
| `odt-char-{slug}` | `<span>` | `{slug}` is a lowercased, slugified version of the ODT character style's name (e.g. a style named "Highlight" becomes `odt-char-highlight`). Lets you style custom character styles from the ODT that don't correspond to standard HTML formatting. |

---

## Code blocks

Produced by `_render_code_block()`. These follow the `highlight.js` /
Prism / Shiki convention rather than an `odt-*` prefix, so any
off-the-shelf syntax-highlighting theme will already recognize them:

| Class | Applies to | Meaning |
|---|---|---|
| `language-{lang}` | `<code>` inside `<pre>` | `{lang}` is the detected language, either from a dedicated `style_map` class (e.g. `{"tag": "pre", "class": "language-python"}`) or a Markdown-style ` ```python ` fence on the first line of the block. Omitted if no language could be determined. |

---

## User-defined classes via `style_map`

Beyond the fixed classes above, **you** control classes for regular
paragraph/heading content by mapping ODT style names to a tag + class in
`style_map`:

```python
style_map = {
    "Lead": {"tag": "p", "class": "lead"},
    "Warning": {"tag": "div", "class": "callout callout-warning"},
}
```

Any class you specify this way is emitted verbatim on the matching
element — there's no library-imposed naming convention here, so pick
whatever fits your theme. This is the main mechanism for turning
document-specific ODT paragraph styles (e.g. "Pull Quote", "Sidebar",
"Warning Box") into themeable HTML hooks beyond the standard tags.

---

## Using your own theme

If you want full control and don't need the library's automatic CSS:

```python
result = convert("article.odt", css=False)
```

This skips `generate_css()` entirely — you'll get none of the
`.odt-columns-N`, `blockquote`, `pre`, `table`, etc. rules it would
otherwise produce, and can write a single stylesheet covering all the
classes in this document (plus your own `style_map` classes) to theme
every converted document consistently.