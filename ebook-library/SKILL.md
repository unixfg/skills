---
name: ebook-library
description: "Use when the user asks about a Calibre ebook library or book collection: find books, search metadata or full text in EPUB/AZW3 files, or locate book paths via Calibre databases."
---

# ebook-library

Use this skill when the user wants to search a Calibre library, find books in an ebook collection, look inside EPUB or AZW3 content, or locate a book file on disk.

Access a Calibre ebook library via read-only SQLite queries.

## Database Discovery

Prefer environment variables so commands stay portable:

- `CALIBRE_LIBRARY_ROOT` - directory containing the Calibre library
- `CALIBRE_METADATA_DB` - full path to `metadata.db`
- `CALIBRE_FTS_DB` - full path to `full-text-search.db`

If you know the library root, derive the DB paths from it:

```bash
export CALIBRE_LIBRARY_ROOT="/path/to/Calibre Library"
export CALIBRE_METADATA_DB="$CALIBRE_LIBRARY_ROOT/metadata.db"
export CALIBRE_FTS_DB="$CALIBRE_LIBRARY_ROOT/full-text-search.db"
```

If you do not know where the DBs are, locate them first:

```bash
find "$HOME" -name metadata.db 2>/dev/null
find "$HOME" -name full-text-search.db 2>/dev/null
```

`metadata.db` usually lives in the library root. If you only find `metadata.db`, use its parent directory as `CALIBRE_LIBRARY_ROOT`.

## Quick Decision Tree

**"What books do I have about X?"** → `find_books.py --query "X"`

**"I only remember part of the title/author"** → `find_books.py --query "partial phrase"`; if it returns `[]`, fall back to `list_books.py`

**"Find a quote/passage in a specific book"** → `search_content.py --book-id N --query "phrase"`

**"Search all books for a topic"** → `search_content.py --query "topic"` (slower, 10-20s)

**"Get more context around a match"** → `get_excerpt.py --book-id N --around "keyword" --chars 1000`

**"Get the file path to read a book"** → `resolve_book.py --book-id N`

**"Browse titles when search terms are too vague"** → `list_books.py --limit 200`

## Detailed Script Reference

See `references/scripts.md` when you need exact commands, output shapes, fallback behavior, or error cases for a specific script.

---

## Common Workflows

### Find a character/quote in a book I know the title of

```bash
# Step 1: Get book ID
python3 scripts/find_books.py --db-path "$CALIBRE_METADATA_DB" --query "Automatic Noodle"
# → book_id: 2525

# Step 2: Search within that book
python3 scripts/search_content.py \
  --fts-db "$CALIBRE_FTS_DB" \
  --metadata-db "$CALIBRE_METADATA_DB" \
  --book-id 2525 \
  --query "chef" \
  --context 400
```

If step 1 returns multiple books, disambiguate by author before searching content. If it returns `[]`, retry with fewer title words or an author surname, then fall back to `list_books.py`.

If step 2 returns `[]`, widen the phrase, try a more distinctive term, or search across all books if you may have the wrong title.

### Discover books on a topic

```bash
python3 scripts/search_content.py \
  --fts-db "$CALIBRE_FTS_DB" \
  --metadata-db "$CALIBRE_METADATA_DB" \
  --query "machine learning" \
  --limit 10
```

If this returns `[]`, try a shorter query, search metadata first with `find_books.py`, or ask for a narrower author/title hint before doing another global scan.

### Read a book's content

```bash
# Get path
python3 scripts/resolve_book.py \
  --metadata-db "$CALIBRE_METADATA_DB" \
  --library-root "$CALIBRE_LIBRARY_ROOT" \
  --book-id 2525

# Then use ebook-convert or similar to extract text
```

If the returned format is not what you want, re-run with `--format EPUB` or another value from `available_formats`.

### Get a longer passage after finding a hit

```bash
# Step 1: Find a match and note the book_id plus a nearby word
python3 scripts/search_content.py \
  --fts-db "$CALIBRE_FTS_DB" \
  --metadata-db "$CALIBRE_METADATA_DB" \
  --book-id 2525 \
  --query "chef"

# Step 2: Pull a larger excerpt around that word
python3 scripts/get_excerpt.py \
  --fts-db "$CALIBRE_FTS_DB" \
  --metadata-db "$CALIBRE_METADATA_DB" \
  --book-id 2525 \
  --around "chef" \
  --chars 1200
```

If `get_excerpt.py` says the keyword is not found, copy a nearby word from the snippet or use `--position` with a known character offset.

---

## Result Handling

- `find_books.py` returns a JSON array. Empty results are `[]`, not errors.
- `search_content.py` returns a JSON array for successful searches and a JSON error object for invalid `--book-id`, missing text, or empty queries.
- `get_excerpt.py` and `resolve_book.py` return JSON objects and use an `"error"` field for invalid book IDs, missing text, bad positions, or missing formats.
- When a `book_id` fails unexpectedly, re-run `find_books.py` first to confirm the title/author mapping before assuming the content index is wrong.
- Prefer `--book-id` searches whenever possible. Global content searches hit a 4.5 GB database and are much slower.

---

## Notes

- **Substring matching:** Searches use LIKE, so "ramen" matches "Sacramento"
- **Global searches are slow:** The FTS database is 4.5GB. Always use `--book-id` when possible.
- **Two formats per book:** Many books have both AZW3 and EPUB; results may show both.
- **Read-only workflow:** These scripts query Calibre databases and file paths only; they do not modify the library.
