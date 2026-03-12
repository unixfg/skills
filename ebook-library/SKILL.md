---
name: ebook-library
description: >
  Use this skill when the user asks to search or browse a Calibre ebook library. It helps find books by title/author/topic, locate file paths, and search inside EPUB/AZW3 text for quotes or passages.

  Do not use this skill for conversion, metadata editing, downloads, recommendations, or non-Calibre sources.
compatibility: >
  Requires filesystem access to a local Calibre library.
  Metadata search requires `metadata.db`.
  Content search and excerpts require `full-text-search.db`.
---

# Ebook Library Skill

Use this skill when a user wants to look up, search, or resolve books in a local Calibre collection.

This skill is read-only. It can inspect Calibre databases and file paths but does not write to library metadata.

## Environment discovery

1. If you already know the library location:
   - `CALIBRE_LIBRARY_ROOT`
   - `CALIBRE_METADATA_DB="$CALIBRE_LIBRARY_ROOT/metadata.db"`
   - `CALIBRE_FTS_DB="$CALIBRE_LIBRARY_ROOT/full-text-search.db"`

2. If unknown, discover DB paths first (`metadata.db`, then `full-text-search.db`).

## Decision tree

- User asks for books by metadata (title, author, topic) → use `find_books.py`.
- User asks for a quote/passage (global or in one book) → use `search_content.py` (prefer `--book-id` when possible).
- User asks for nearby context around a hit → use `get_excerpt.py`.
- User asks for file path → use `resolve_book.py`.
- User asks to browse when search is vague → use `list_books.py`.
- User asks for quick sanity checks → use `inspect_calibre_metadata.py`.

### Quick example

```bash
python3 scripts/find_books.py --db-path "$CALIBRE_METADATA_DB" --query "Dune"
python3 scripts/search_content.py --fts-db "$CALIBRE_FTS_DB" --metadata-db "$CALIBRE_METADATA_DB" --book-id 4 --query "knowledge"
```

## Orchestration (preferred flow)

1. For known title/author questions, identify candidates with `find_books.py`.
2. If multiple candidates, disambiguate before deeper searches.
3. For phrase/quote tasks:
   - run scoped search with `--book-id` if you know the book,
   - otherwise use global content search.
4. For a returned hit that needs context, call `get_excerpt.py`.
5. Return results with enough evidence for transparency (book id, title, author, and snippet/path depending on query).

## Result handling

- Empty arrays (`[]`) are valid "no result" responses.
- `search_content.py`/`get_excerpt.py`/`resolve_book.py` can return structured errors for invalid IDs, missing text, or bad positions.
- If a `book_id` seems stale, re-run a metadata search before concluding the library is broken.

## Boundaries

- Do not infer file conversions or imports from search output.
- Do not guess book titles/authors when lookup returns no match.
- Prefer precise scoped searches to reduce unnecessary full-library scans.

For exact script arguments, output formats, examples, and error payloads, see `references/scripts.md`.
