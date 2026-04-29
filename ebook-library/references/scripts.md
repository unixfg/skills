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

If you need to discover the DB locations:

```bash
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
    "authors": "Bertrand Russell",
    "pubdate": "2004-06-02 00:00:00+00:00",
    "timestamp": "2026-03-10 20:25:41.246772+00:00",
    "last_modified": "2026-03-10 20:43:05.569779+00:00"
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

## 6. `list_books.py` - Browse, filter, and sort books

Useful when fuzzy title or author searches keep returning `[]`, or when the user asks for newest/recent books, books by date, or rated books.

```bash
python3 scripts/list_books.py \
  --db-path "$CALIBRE_METADATA_DB" \
  --limit 200
```

Default output is alphabetical by title and includes:

```json
[
  {
    "id": 4,
    "title": "The Problems of Philosophy",
    "authors": "Bertrand Russell",
    "pubdate": "2004-06-02 00:00:00+00:00",
    "timestamp": "2026-03-10 20:25:41.246772+00:00",
    "last_modified": "2026-03-10 20:43:05.569779+00:00",
    "formats": ["EPUB", "TXT"],
    "tags": ["Knowledge", "Philosophy -- Introductions"],
    "publishers": [],
    "rating": 10,
    "stars": 5
  }
]
```

Newest books by publication date:

```bash
python3 scripts/list_books.py \
  --db-path "$CALIBRE_METADATA_DB" \
  --sort pubdate \
  --order desc \
  --limit 10
```

Books published in a date range:

```bash
python3 scripts/list_books.py \
  --db-path "$CALIBRE_METADATA_DB" \
  --date-field pubdate \
  --from-date 2026-04-01 \
  --to-date 2026-04-30
```

Five top-rated books:

```bash
python3 scripts/list_books.py \
  --db-path "$CALIBRE_METADATA_DB" \
  --sort rating \
  --order desc \
  --rated \
  --limit 5
```

Count five-star books:

```bash
python3 scripts/list_books.py \
  --db-path "$CALIBRE_METADATA_DB" \
  --stars 5 \
  --count
```

Supported options:

- `--sort title|author|pubdate|timestamp|last_modified|rating`
- `--order asc|desc`
- `--query TEXT` matches title, author, tag, or publisher
- `--author TEXT`, `--tag TEXT`, `--format FORMAT`, `--publisher TEXT`
- `--date-field pubdate|timestamp|last_modified`
- `--from-date YYYY-MM-DD`, `--to-date YYYY-MM-DD`
- `--stars N`, `--min-stars N`, `--max-stars N` filter by 0-5 star values; half-star values such as `4.5` are accepted
- `--rated`, `--unrated` filter by whether a book has a rating
- `--count` returns `{"count": N}` instead of book rows

Use `pubdate` for publication date, `timestamp` for Calibre-added/imported date, and `last_modified` for modified date.
Calibre stores ratings internally as 0-10 integers; `rating` is that raw value, and `stars` is the human-facing 0-5 value.

## 7. `inspect_calibre_metadata.py` - Sanity-check metadata access

Use this to confirm that `metadata.db` is readable and inspect summary counts plus a small sample of books.

```bash
python3 scripts/inspect_calibre_metadata.py \
  --db-path "$CALIBRE_METADATA_DB" \
  --limit 20
```

It returns counts such as `book_count`, `author_count`, `format_counts`, and `sample_books`.

## Result Handling

- `find_books.py` and `list_books.py` return JSON arrays. Empty results are `[]`, not errors.
- `search_content.py` returns a JSON array for successful searches and a JSON error object for invalid `--book-id`, missing text, or empty queries.
- `get_excerpt.py` and `resolve_book.py` return JSON objects and use an `"error"` field for invalid book IDs, missing text, bad positions, or missing formats.
- When a `book_id` fails unexpectedly, rerun `find_books.py` first to confirm the title and author mapping before assuming the content index is wrong.
- Prefer `--book-id` searches whenever possible. Global content searches have to scan the full-text index and are much slower.
