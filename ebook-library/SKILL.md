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

## Non-negotiable rules

- Use a real Calibre library only. The source of truth is `metadata.db` and, for text lookup, `full-text-search.db`.
- Never create substitute `sample-library` content, fake JSON catalogs, invented book files, or ad hoc metadata when the real library is missing.
- If the task says to use `./sample-library`, first verify that `./sample-library/metadata.db` exists. If it does not, stop and report the missing path instead of improvising.
- If `metadata.db` is missing or unreadable, stop and report that metadata lookup cannot proceed.
- If `full-text-search.db` is missing or unreadable, metadata lookup can still proceed, but content search and excerpts cannot.

## Environment discovery

1. If you already know the library location, set these first:

```bash
export CALIBRE_LIBRARY_ROOT="/path/to/Calibre Library"
export CALIBRE_METADATA_DB="$CALIBRE_LIBRARY_ROOT/metadata.db"
export CALIBRE_FTS_DB="$CALIBRE_LIBRARY_ROOT/full-text-search.db"
```

2. If the task explicitly names a bundled library such as `./sample-library`, verify those exact paths first:

```bash
test -r ./sample-library/metadata.db && echo "metadata ok"
test -r ./sample-library/full-text-search.db && echo "fts ok"
```

3. If the library root is unknown, discover DB paths first:

```bash
find "$HOME" -name metadata.db 2>/dev/null
find "$HOME" -name full-text-search.db 2>/dev/null
```

4. Before running any lookup, confirm what is actually available:

```bash
test -r "$CALIBRE_METADATA_DB" && echo "metadata ok"
test -r "$CALIBRE_FTS_DB" && echo "fts ok"
```

If `metadata.db` is missing, stop.
If `full-text-search.db` is missing, restrict yourself to metadata/path tasks and say content search is unavailable.

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
- When a hit needs proof, follow with `get_excerpt.py` and quote the returned snippet.
- If the expected bundled library is absent, say so plainly; do not replace it with made-up content.
- If you had to discover the library location, report the path you actually used.

## Orchestration (preferred flow)

1. **Environment/checkpoint:** verify the library root and DB paths before starting.
   - If the task names a specific bundled path such as `./sample-library`, check that exact path first.
   - If a provided path is unreadable, stop and report exactly which file is missing.
   - Never substitute a homemade library when the expected one is absent.
2. **For title/author/topic questions:** run `find_books.py`.
   - If results are empty, run `inspect_calibre_metadata.py` to confirm DB accessibility and give a short sample set,
   - then retry with a shorter/partial query before returning no-match.
3. **For phrase/quote tasks:**
   - if a candidate `book_id` is already known, run `search_content.py` scoped to that ID,
   - otherwise run a global `search_content.py`.
   - If global search returns empty, confirm the search target with `inspect_calibre_metadata.py` and retry with a narrower phrase before reporting no hit.
4. **For ambiguous/empty candidate discovery:** if `find_books.py` returns multiple plausible titles, fetch short context with additional scoped `search_content.py` searches before selecting one candidate.
5. **For hit verification:** when a hit is found and needs proof, call `get_excerpt.py` to produce a stable snippet; if this returns an error, re-run a broader quote search in the same source before concluding failure.
6. **For path resolution:** if `resolve_book.py` returns `exists: false`, verify `book_id` via `find_books.py` (in case of stale IDs), then retry resolution with the known preferred format.
7. Return results with transparent evidence fields: book id, title, author, method used, and snippet/path depending on query.

## Result handling

- Empty arrays (`[]`) are valid "no result" responses.
- `search_content.py`/`get_excerpt.py`/`resolve_book.py` can return structured errors for invalid IDs, missing text, or bad positions.
- If a `book_id` seems stale, rerun metadata lookup first (`find_books.py` by title/author context), then retry `resolve_book.py` before concluding the library is broken.

## Boundaries

- Do not infer file conversions or imports from search output.
- Do not guess book titles/authors when lookup returns no match.
- Prefer precise scoped searches to reduce unnecessary full-library scans.

For exact script arguments, output formats, examples, and error payloads, see `references/scripts.md`.
