#!/usr/bin/env python3
"""Shared helpers for Calibre library scripts."""

from __future__ import annotations

PREFERRED_FORMATS = ("EPUB", "AZW3", "KFX", "MOBI", "PDF")


def normalize_format(fmt: str | None) -> str | None:
    if fmt is None:
        return None
    return fmt.upper()


def format_sort_key(fmt: str, preferred: str | None = None) -> tuple[int, str]:
    normalized = normalize_format(fmt) or ""
    preferred_normalized = normalize_format(preferred)
    if preferred_normalized and normalized == preferred_normalized:
        return (0, normalized)
    if normalized in PREFERRED_FORMATS:
        return (1 + PREFERRED_FORMATS.index(normalized), normalized)
    return (1 + len(PREFERRED_FORMATS), normalized)


def choose_preferred_format(formats, preferred: str | None = None):
    available = list(formats)
    if not available:
        return None
    return sorted(available, key=lambda fmt: format_sort_key(fmt, preferred))[0]


def build_excerpt(text: str, position: int, chars: int) -> str:
    start = max(0, position - chars // 2)
    end = min(len(text), start + chars)
    excerpt = text[start:end]

    if start > 0:
        first_space = excerpt.find(" ")
        if 0 < first_space < 50:
            excerpt = excerpt[first_space + 1 :]
    if end < len(text):
        last_space = excerpt.rfind(" ")
        if last_space > len(excerpt) - 50:
            excerpt = excerpt[:last_space]
    return excerpt.strip()
