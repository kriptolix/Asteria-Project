"""
Everything the SSG knows about translations, in one place.

A source file names its language with a suffix (``welcome.pt-BR.odt``); a
file without a suffix is written in the site's default language
(``site.language``). Each file becomes a document with a ``lang`` and a
``translation_key`` (the file name minus that suffix), and every document
that shares a ``translation_key`` is a translation of the others.

This module owns:

  * ``detect_lang``           file name -> (translation_key, lang)
  * ``validate_translations`` known languages, and ONE document per
                              (translation_key, lang)
  * ``link_translations``     fills ``doc.translations``
  * ``TranslationIndex``      the single rule that turns a reference
                              (``[[welcome]]``, ``menu:``, ``nav:``,
                              ``home_page:``) into a document
  * ``SiteLanguages``         default language, URL prefix and the
                              per-language file names

UI string translations live in ``i18n_strings.py`` and locale date
formatting in ``dates.py``; both are about *rendering* a language, whereas
this module is about *which document* belongs to which language.

This module must not import ``config`` or ``document`` (they import from
here, directly or indirectly): it only relies on the attributes documents
expose (``id``, ``lang``, ``translation_key``, ``translations``, ``kind``,
``source_path``).
"""

from __future__ import annotations

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from typing import Any

from .errors import Diagnostics
from .urls import prefix_lang


# -- file names ---------------------------------------------------------------

def detect_lang(
    stem: str, languages: Collection[str], default_language: str
) -> tuple[str, str]:
    """Detects an explicit language in the file name.

    ``welcome.pt-BR`` -> ``("welcome", "pt-BR")`` when ``pt-BR`` is one of
    the site's languages. Anything else (no dot, or a dot followed by
    something that is not a known language) is returned untouched and
    assumed to be in the default language: ``("welcome", default)``.
    """
    if "." in stem:
        base, _, suffix = stem.rpartition(".")
        if base and suffix in languages:
            return base, suffix
    return stem, default_language


# -- validation ---------------------------------------------------------------

def validate_translations(
    documents: Iterable[Any], languages: Collection[str], diagnostics: Diagnostics
) -> None:
    """Checks what discovery cannot know file by file:

    * a document in a language the site doesn't list (warning);
    * two documents claiming the same (translation_key, lang) (error).
      Without this check the second one silently replaces the first in
      every registry, and a whole file just disappears from the site.
    """
    known = set(languages)
    first_seen: dict[tuple[str, str], Any] = {}

    for doc in documents:
        if doc.lang not in known:
            diagnostics.warning(
                f"{doc.kind.capitalize()} language '{doc.lang}' is not listed in "
                "i18n.languages (or site.language); it will still be "
                "built, but won't get a language prefix and won't be "
                "grouped with the site's other languages.",
                source=str(doc.source_path),
            )

        other = first_seen.setdefault((doc.translation_key, doc.lang), doc)
        if other is not doc:
            diagnostics.error(
                f"'{doc.source_path.name}' and '{other.source_path.name}' are both "
                f"the '{doc.lang}' version of '{doc.translation_key}', and only one "
                "document per language is allowed. Give one of them another "
                f"language suffix (e.g. '{doc.translation_key}.<lang>.odt') or fix its "
                "`lang:` in the front matter. Note that a file without a language "
                "suffix counts as being in the site's default language.",
                source=str(doc.source_path),
            )


# -- linking ------------------------------------------------------------------

def link_translations(documents: Iterable[Any]) -> None:
    """Populates `doc.translations` with the other versions (in other
    languages) of each document, grouped by `translation_key`.

    Call it separately for pages and for posts: a page and a post that
    happen to share a translation_key are not translations of each other.
    """
    groups: dict[str, list[Any]] = {}
    for doc in documents:
        groups.setdefault(doc.translation_key, []).append(doc)

    for group in groups.values():
        for doc in group:
            doc.translations = {d.lang: d for d in group if d is not doc}


# -- reference resolution -----------------------------------------------------

class TranslationIndex:
    """Resolves a reference to a document, in the language it is read in.

    This is the one place that implements the rule shared by
    ``[[references]]``, ``menu:``, ``nav:`` and ``home_page:``:

      1. ``ref`` is first tried as a ``translation_key``. If it names a
         group, the answer is the version in ``lang``, else the one in the
         default language, else any version.
      2. Otherwise ``ref`` is tried as an exact document ``id`` (this is
         how a specific translation can be pinned, e.g. ``welcome.en``).

    So ``welcome`` finds ``welcome.pt-BR.odt`` even when no plain
    ``welcome.odt`` exists: references never depend on which file is the
    "base" one.

    `documents` take part in both steps. `extra_targets` (raw pages, which
    have no language) are reachable by exact id only.
    """

    def __init__(
        self,
        documents: Iterable[Any],
        default_language: str,
        extra_targets: Iterable[Any] = (),
    ) -> None:
        self.default_language = default_language
        self._by_id: dict[str, Any] = {}
        self._groups: dict[str, dict[str, Any]] = {}

        for doc in documents:
            self._by_id[doc.id] = doc
            key = getattr(doc, "translation_key", None)
            lang = getattr(doc, "lang", None)
            if key and lang:
                self._groups.setdefault(key, {})[lang] = doc

        for target in extra_targets:
            self._by_id[target.id] = target

    def resolve(self, ref: str, lang: str = "") -> Any | None:
        """The document `ref` points to when read in `lang`, or None."""
        group = self._groups.get(ref)
        if group:
            return (
                group.get(lang)
                or group.get(self.default_language)
                or next(iter(group.values()))
            )
        return self._by_id.get(ref)

    def versions(self, ref: str) -> dict[str, Any]:
        """Every version of `ref`, as {lang: document} (empty if unknown).

        For a translation_key that is the whole group; for an exact id it
        is that document plus its already-linked translations.
        """
        group = self._groups.get(ref)
        if group:
            return dict(group)
        doc = self._by_id.get(ref)
        if doc is None or not getattr(doc, "lang", ""):
            return {}
        return {doc.lang: doc, **getattr(doc, "translations", {})}


# -- the site's languages -----------------------------------------------------

@dataclass(frozen=True)
class SiteLanguages:
    """The site's languages and everything that depends on which of them
    is the default one: the default language is served from the root,
    every other language under ``/<lang>/``."""

    default: str
    all: tuple[str, ...]

    @classmethod
    def from_config(cls, config: Any) -> "SiteLanguages":
        return cls(default=config.default_language, all=tuple(config.languages))

    def is_default(self, lang: str) -> bool:
        return not lang or lang == self.default

    def prefix(self, url: str, lang: str) -> str:
        """'/blog/' -> '/en/blog/' for a non-default language."""
        return prefix_lang(url, lang, self.default)

    def root_path(self, lang: str) -> str:
        return "/" if self.is_default(lang) else f"/{lang}/"

    def localized_filename(self, filename: str, lang: str) -> str:
        """'rss.xml' -> 'en-rss.xml' for a non-default language."""
        return filename if self.is_default(lang) else f"{lang}-{filename}"