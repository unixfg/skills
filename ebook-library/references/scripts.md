# Script Reference

Use this file when you need exact CLI syntax, expected output shape, or script-specific failure handling.

## Shared contracts

These conventions apply to all scripts in `scripts/`:

- Non-interactive CLI only.
- Use `--help` (all scripts expose usage text).
- Machine-readable JSON output on stdout.
- Structured errors as JSON on stdout, including both:
  - `"error"`: human-readable message
  - `"error_code"`: stable machine-readable code (e.g., `BOOK_NOT_FOUND`, `DB_NOT_FOUND`)
- Exit codes: `0` for success, non-zero for failure.

## Environment

All scripts are in `scripts/`.

Set these first or substitute explicit paths in each command:

```bash
export CALIBRE_LIBRARY_ROOT="/path/to/Calibre Library"
export CALIBRE_METADATA_DB="$CALIBRE_LIBRARY_ROOT/metadata.db"
export CALIBRE_FTS_DB="$CALIBRE_LIBRARY_ROOT/full-text-search.db"
```

If you need to discover the DB locations, check task-local or worktree-local DBs before broader scans:

```bash
pwd
find . -maxdepth 4 -name metadata.db 2>/dev/null
find . -maxdepth 4 -name full-text-search.db 2>/dev/null
find "$HOME" -name metadata.db 2>/dev/null
find "$HOME" -name full-text-search.db 2>/dev/null
```

## Contents

- `find_books.py`
- `search_content.py`
- `get_excerpt.py`
- `query-book.sh`
- `resolve_book.py`
- `list_books.py`
- `inspect_calibre_metadata.py`

## 1. `find_books.py` - Search by title or author

Fast path for title and author lookup. Typical runtime is under 0.1s.

```bash
python3 scripts/find_books.py \
  --db-path "$CALIBRE_METADATA_DB" \
  --query "The Problems of Philosophy" \
  --limit 5
```

Typical output:

```json
[
  {
    "id": 4,
    "title": "The Problems of Philosophy",
    "authors": "Bertrand Russell"
  }
]
```

If there are no matches, it prints `[]`. Retry with fewer words, an author surname, or `list_books.py --limit 200`.

Exact title matches are ranked ahead of looser substring matches.

## 2. `search_content.py` - Search book text

Searches the Calibre full-text index. Prefer `--book-id` whenever possible.

Within a specific book:

```bash
python3 scripts/search_content.py \
  --fts-db "$CALIBRE_FTS_DB" \
  --metadata-db "$CALIBRE_METADATA_DB" \
  --book-id 4 \
  --query "knowledge" \
  --context 400
```

Optional: add `--format EPUB` to force a specific format.

Across all books:

```bash
python3 scripts/search_content.py \
  --fts-db "$CALIBRE_FTS_DB" \
  --metadata-db "$CALIBRE_METADATA_DB" \
  --query "artificial intelligence" \
  --limit 10
```

When scoped to `--book-id`, the script searches one preferred text source and returns multiple occurrences from that book instead of one duplicate row per format.

If there are no matches, it prints `[]`. Invalid `--book-id` values return `{"error": "Book N not found", "error_code": "BOOK_NOT_FOUND"}`.

## 3. `get_excerpt.py` - Pull a longer passage

Get a larger excerpt around a keyword or absolute character position.

```bash
python3 scripts/get_excerpt.py \
  --fts-db "$CALIBRE_FTS_DB" \
  --metadata-db "$CALIBRE_METADATA_DB" \
  --book-id 4 \
  --around "knowledge" \
  --chars 800
```

Optional: add `--format EPUB` to keep the excerpt aligned with a specific content search result.

Options:

- `--around "keyword"` centers the excerpt on the first occurrence
- `--occurrence N` uses the Nth occurrence instead of the first
- `--position N` centers on a character position
- `--chars N` sets excerpt length, default `800`

Common failures are JSON objects like:

```json
{"error": "Book 4 not found", "error_code": "BOOK_NOT_FOUND"}
```

```json
{"error": "No text found for book 4", "error_code": "BOOK_TEXT_MISSING"}
```

```json
{"error": "Keyword 'X' not found in book", "error_code": "KEYWORD_NOT_FOUND", "book_id": 4, "title": "The Problems of Philosophy"}
```

The successful response also includes the chosen `format`.

## 4. `query-book.sh` - One-liner wrapper

Wrapper that combines find plus content search.

```bash
./scripts/query-book.sh "The Problems of Philosophy" "knowledge"
./scripts/query-book.sh --id 4 "knowledge"
```

Use this when the user names one book and wants a fast, single-command lookup.

The wrapper prefers an exact title match when one exists. If a partial title matches multiple books, it exits with an ambiguity list instead of silently picking the first result.

## 5. `resolve_book.py` - Resolve a filesystem path

Resolve a Calibre book ID to a concrete file path.

```bash
python3 scripts/resolve_book.py \
  --metadata-db "$CALIBRE_METADATA_DB" \
  --library-root "$CALIBRE_LIBRARY_ROOT" \
  --book-id 4 \
  --format EPUB
```

If the preferred format is missing, the script falls back to the first available format and returns `available_formats`.

Format matching is case-insensitive, so `--format epub` works.

If `exists` is `false`, the Calibre metadata is stale or the file moved.

## 6. `list_books.py` - Browse titles alphabetically

Useful when fuzzy title or author searches keep returning `[]`.

```bash
python3 scripts/list_books.py \
  --db-path "$CALIBRE_METADATA_DB" \
  --limit 200
```

## 7. `inspect_calibre_metadata.py` - Sanity-check metadata access

Use this to confirm that `metadata.db` is readable and inspect summary counts plus a small sample of books.

```bash
python3 scripts/inspect_calibre_metadata.py \
  --db-path "$CALIBRE_METADATA_DB" \
  --limit 20
```

It returns counts such as `book_count`, `author_count`, `format_counts`, and `sample_books`.

## Result Handling

- `find_books.py` returns a JSON array. Empty results are `[]`, not errors.
- `search_content.py` returns a JSON array for successful searches and a JSON error object for invalid `--book-id`, missing text, or empty queries.
- `get_excerpt.py` and `resolve_book.py` return JSON objects and use an `"error"` field for invalid book IDs, missing text, bad positions, or missing formats.
- When a `book_id` fails unexpectedly, rerun `find_books.py` first to confirm the title and author mapping before assuming the content index is wrong.
- Prefer `--book-id` searches whenever possible. Global content searches have to scan the full-text index and are much slower.
