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

## Library discovery and validation

Use a real Calibre library only. The source of truth is `metadata.db` and, for text lookup, `full-text-search.db`.
Never create substitute library content, fake JSON catalogs, invented book files, or ad hoc metadata when the real library is missing.

1. If you already know the library location, set these first:

```bash
export CALIBRE_LIBRARY_ROOT="/path/to/Calibre Library"
export CALIBRE_METADATA_DB="$CALIBRE_LIBRARY_ROOT/metadata.db"
export CALIBRE_FTS_DB="$CALIBRE_LIBRARY_ROOT/full-text-search.db"
```

2. If the library root is unknown, first check task-local or worktree-local DBs, then scan broader locations:

```bash
pwd
find . -maxdepth 4 -name metadata.db 2>/dev/null
find . -maxdepth 4 -name full-text-search.db 2>/dev/null
find "$HOME" -name metadata.db 2>/dev/null
find "$HOME" -name full-text-search.db 2>/dev/null
```

3. Before running any lookup, verify what is actually readable:

```bash
test -r "$CALIBRE_METADATA_DB" && echo "metadata ok"
test -r "$CALIBRE_FTS_DB" && echo "fts ok"
```

- If the task names a specific library path, check that exact path first.
- If `metadata.db` is missing or unreadable, stop and report the missing path.
- If `full-text-search.db` is missing or unreadable, restrict yourself to metadata/path tasks and say content search is unavailable.
- When you discover the library dynamically, report the exact verified DB path or root you actually used; do not normalize, shorten, or rewrite it.

## Decision tree

- User asks for books by metadata (title, author, topic) → use `find_books.py`.
- User asks for a quote/passage (global or in one book) → use `search_content.py` (prefer `--book-id` when possible).
- User asks for nearby context around a hit → use `get_excerpt.py`.
- User asks for file path → use `resolve_book.py`.
- User asks to browse when search is vague → use `list_books.py`.
- User asks for quick sanity checks → use `inspect_calibre_metadata.py`.

## Common commands

Use these directly for the most common tasks.

### Find books by title, author, or topic

```bash
python3 scripts/find_books.py \
  --db-path "$CALIBRE_METADATA_DB" \
  --query "Dune" \
  --limit 5
```

Returns a JSON array like:

```json
[{"id": 4, "title": "Dune", "authors": "Frank Herbert"}]
```

### Search for a phrase inside one known book

```bash
python3 scripts/search_content.py \
  --fts-db "$CALIBRE_FTS_DB" \
  --metadata-db "$CALIBRE_METADATA_DB" \
  --book-id 4 \
  --query "knowledge" \
  --context 400
```

Use this first when you already know the target `book_id`.

### Search for a phrase across the whole library

```bash
python3 scripts/search_content.py \
  --fts-db "$CALIBRE_FTS_DB" \
  --metadata-db "$CALIBRE_METADATA_DB" \
  --query "artificial intelligence" \
  --limit 10
```

### Pull a longer excerpt around a hit

```bash
python3 scripts/get_excerpt.py \
  --fts-db "$CALIBRE_FTS_DB" \
  --metadata-db "$CALIBRE_METADATA_DB" \
  --book-id 4 \
  --around "knowledge" \
  --chars 800
```

### Resolve a Calibre book ID to a file path

```bash
python3 scripts/resolve_book.py \
  --metadata-db "$CALIBRE_METADATA_DB" \
  --library-root "$CALIBRE_LIBRARY_ROOT" \
  --book-id 4 \
  --format EPUB
```

### Browse books when search terms are vague

```bash
python3 scripts/list_books.py \
  --db-path "$CALIBRE_METADATA_DB" \
  --limit 50
```

### Sanity-check database access

```bash
python3 scripts/inspect_calibre_metadata.py \
  --db-path "$CALIBRE_METADATA_DB" \
  --limit 20
```

## Quick response rules

- `find_books.py` and `search_content.py` return `[]` for honest no-match cases.
- Invalid book IDs return structured JSON errors such as `{"error": "Book 999 not found", "error_code": "BOOK_NOT_FOUND"}`.
- Prefer `search_content.py --book-id ...` over global content search whenever possible.
- For clue-based identification tasks, prefer content search before metadata browsing; use metadata afterward to confirm the selected match.
- When a hit needs proof, follow with `get_excerpt.py` and quote the returned snippet.
- If you had to discover the library location, report the exact verified path you actually used.

## Orchestration (fallback rules)

After the library discovery step, use the decision tree and common commands above. Apply these extra fallback rules only when the first pass does not resolve the task:

1. If `find_books.py` returns no results, run `inspect_calibre_metadata.py` to confirm DB accessibility, then retry with a shorter or partial query.
2. If a global phrase search returns no results, confirm the target with `inspect_calibre_metadata.py`, then retry with a narrower phrase.
3. If `find_books.py` returns multiple plausible titles, run scoped `search_content.py` searches to disambiguate before choosing a candidate.
4. If a hit needs proof, run `get_excerpt.py`; if it errors, retry with a broader search in the same source before concluding failure.
5. If `resolve_book.py` returns `exists: false`, verify the `book_id` via `find_books.py`, then retry path resolution with the preferred format.
6. Return transparent evidence fields: book id, title, author, method used, and snippet or path as appropriate.

## Result handling

- Empty arrays (`[]`) are valid "no result" responses.
- `search_content.py`/`get_excerpt.py`/`resolve_book.py` can return structured errors for invalid IDs, missing text, or bad positions.
- If a `book_id` seems stale, rerun metadata lookup first (`find_books.py` by title/author context), then retry `resolve_book.py` before concluding the library is broken.

## Boundaries

- Do not infer file conversions or imports from search output.
- Do not guess book titles/authors when lookup returns no match.
- Prefer precise scoped searches to reduce unnecessary full-library scans.

For exact script arguments, output formats, examples, and error payloads, see [references/scripts.md](references/scripts.md).
