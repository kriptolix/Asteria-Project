"""
Dates.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .errors import AsteriaError
from .i18n_strings import lookup

# What an author may write, besides plain ISO 8601: slashes instead of hyphens
# in the date (`2024/03/15`) and a space instead of the `T`, in any
# combination. All of them are normalised to ISO.
def _build_formats() -> tuple[tuple[str, bool], ...]:
    formats: list[tuple[str, bool]] = []
    for date_sep in ("-", "/"):
        day = f"%Y{date_sep}%m{date_sep}%d"
        formats.append((day, False))
        for sep in ("T", " "):
            for seconds in (":%S", ""):
                for tz in ("%z", ""):
                    formats.append((f"{day}{sep}%H:%M{seconds}{tz}", True))
    return tuple(formats)


_PARSE_FORMATS = _build_formats()

# Sorts before any real date (documents without a valid date go last in a
# newest-first listing).
UNDATED = datetime.min.replace(tzinfo=timezone.utc)

DATE_PLACEHOLDERS = "{day}, {month}, {month_num}, {year}"


# -- the one parser ------------------------------------------------------------

def _parse(raw: str | None) -> tuple[datetime, bool] | None:
    """(parsed value, whether the text had a time of day), or None."""
    if not raw:
        return None
    text = str(raw).strip()
    for fmt, has_time in _PARSE_FORMATS:
        try:
            return datetime.strptime(text, fmt), has_time
        except ValueError:
            continue
    return None


def parse_datetime(raw: str | None) -> datetime | None:
    """A date/datetime string as a `datetime` (naive when the text has no
    UTC offset), or None if it isn't a recognised date."""
    parsed = _parse(raw)
    return parsed[0] if parsed else None


def normalize_date(raw: str | None) -> str | None:
    """The ISO 8601 form of `raw`: 'YYYY-MM-DD' for a plain date,
    'YYYY-MM-DDTHH:MM:SS[+HH:MM]' when it has a time. None if unrecognised."""
    parsed = _parse(raw)
    if parsed is None:
        return None
    value, has_time = parsed
    return value.isoformat() if has_time else value.date().isoformat()


def iso_date(raw: str | None) -> str | None:
    """Just the 'YYYY-MM-DD' part (what a sitemap `lastmod` takes)."""
    value = parse_datetime(raw)
    return value.date().isoformat() if value else None


def to_utc(raw: str | None) -> datetime | None:
    """`raw` as an aware UTC datetime (a date means midnight; a time without
    an offset is taken as UTC). For ordering and for feeds."""
    value = parse_datetime(raw)
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# -- display -------------------------------------------------------------------

def format_date(
    strings: dict[str, dict[str, Any]],
    default_language: str,
    raw: str | None,
    lang: str = "",
    style: str = "long",
) -> str:
    """Backs the Jinja filter `{{ post.date | format_date(post.lang, "short") }}`
    (templating.create_environment binds `strings` and `default_language`).

    `style` is "long" or "short" (the theme's `date_long` / `date_short`
    pattern for `lang`), "iso" (YYYY-MM-DD), or any `strftime` pattern (those
    are not translated). Without a pattern — or month names, when the pattern
    uses `{month}` — for `lang`, its base language or the default language,
    the date comes out as ISO. A value that isn't a date is returned as is.
    """
    parsed = parse_datetime(raw)
    if parsed is None:
        return raw or ""
    day = parsed.date()

    if style == "iso":
        return day.isoformat()
    if style not in ("long", "short"):
        return parsed.strftime(style)

    pattern = lookup(strings, f"date_{style}", lang, default_language)
    if not isinstance(pattern, str):
        return day.isoformat()

    fields: dict[str, Any] = {"day": day.day, "month_num": day.month, "year": day.year}
    months = lookup(strings, "months", lang, default_language)
    if isinstance(months, list) and len(months) == 12:
        fields["month"] = months[day.month - 1]
    try:
        return pattern.format(**fields)
    except (KeyError, IndexError, ValueError):
        return day.isoformat()


def validate_date_strings(strings: dict[str, dict[str, Any]]) -> None:
    """Fails the build early, with a message that names the language and the
    key, when a theme's `months` / `date_long` / `date_short` can't work."""
    sample = {"day": 1, "month": "x", "month_num": 1, "year": 2000}
    for code, entries in strings.items():
        entries = entries or {}
        months = entries.get("months")
        if months is not None and not (
            isinstance(months, list)
            and len(months) == 12
            and all(isinstance(m, str) and m for m in months)
        ):
            raise AsteriaError(
                f"i18n: 'months' for language '{code}' must be a list of 12 month names "
                "(January first)."
            )
        for key in ("date_long", "date_short"):
            pattern = entries.get(key)
            if pattern is None:
                continue
            try:
                if not isinstance(pattern, str):
                    raise ValueError("it must be text")
                pattern.format(**sample)
            except (KeyError, IndexError, ValueError) as exc:
                raise AsteriaError(
                    f"i18n: '{key}' for language '{code}' is not a valid date pattern "
                    f"({exc!s}). Use {DATE_PLACEHOLDERS}, e.g. \"{{day}}/{{month_num:02}}/{{year}}\"."
                ) from exc