#!/bin/bash
# query-book.sh - Simple wrapper to search within a specific book
#
# Usage:
#   ./query-book.sh "The Problems of Philosophy" "knowledge"
#   ./query-book.sh --id 4 "knowledge"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LIBRARY_ROOT="${CALIBRE_LIBRARY_ROOT:-}"
FTS_DB="${CALIBRE_FTS_DB:-}"
META_DB="${CALIBRE_METADATA_DB:-}"

if [[ -n "$LIBRARY_ROOT" ]]; then
    FTS_DB="${FTS_DB:-$LIBRARY_ROOT/full-text-search.db}"
    META_DB="${META_DB:-$LIBRARY_ROOT/metadata.db}"
fi

usage() {
    echo "Usage: $0 <title-or-id> <search-term> [--chars N]"
    echo "       $0 --id <book-id> <search-term> [--chars N]"
    echo ""
    echo "Examples:"
    echo "  $0 'The Problems of Philosophy' 'knowledge'"
    echo "  $0 --id 4 'knowledge'"
    echo ""
    echo "Set CALIBRE_METADATA_DB and CALIBRE_FTS_DB, or set CALIBRE_LIBRARY_ROOT."
    exit 1
}

ensure_db_paths() {
    if [[ -n "$META_DB" && -n "$FTS_DB" ]]; then
        return
    fi

    echo "Calibre database paths are not configured." >&2
    echo "Set CALIBRE_METADATA_DB and CALIBRE_FTS_DB, or set CALIBRE_LIBRARY_ROOT." >&2
    echo 'To locate them, try:' >&2
    echo '  find "$HOME" -name metadata.db 2>/dev/null' >&2
    echo '  find "$HOME" -name full-text-search.db 2>/dev/null' >&2
    exit 2
}

BOOK_ID=""
TITLE=""
QUERY=""
CHARS=500

while [[ $# -gt 0 ]]; do
    case $1 in
        --id)
            BOOK_ID="$2"
            shift 2
            ;;
        --chars)
            CHARS="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            if [[ -z "$TITLE" && -z "$BOOK_ID" ]]; then
                TITLE="$1"
            elif [[ -z "$QUERY" ]]; then
                QUERY="$1"
            fi
            shift
            ;;
    esac
done

if [[ -z "$QUERY" ]]; then
    usage
fi

ensure_db_paths

# If we have a title, find the book ID first
if [[ -n "$TITLE" && -z "$BOOK_ID" ]]; then
    echo "Finding book: $TITLE" >&2
    if ! RESULT=$(python3 "$SCRIPT_DIR/find_books.py" --db-path "$META_DB" --query "$TITLE" --limit 10); then
        echo "$RESULT" >&2
        exit 2
    fi

    if SELECTION=$(TITLE="$TITLE" python3 -c '
import json
import os
import sys

title = os.environ["TITLE"].strip().lower()
results = json.load(sys.stdin)

if isinstance(results, dict) and "error" in results:
    print(json.dumps(results), file=sys.stderr)
    raise SystemExit(3)
if not results:
    print(f"Book not found: {os.environ['"'"'TITLE'"'"']}", file=sys.stderr)
    raise SystemExit(1)

exact = [row for row in results if row.get("title", "").strip().lower() == title]
if len(exact) == 1:
    row = exact[0]
elif len(results) == 1:
    row = results[0]
else:
    print(f"Ambiguous title: {os.environ['"'"'TITLE'"'"']}", file=sys.stderr)
    print("Matches:", file=sys.stderr)
    for row in results:
        print(f"  {row['"'"'id'"'"']}: {row['"'"'title'"'"']} - {row.get('"'"'authors'"'"') or '"'"'Unknown author'"'"'}", file=sys.stderr)
    raise SystemExit(2)

print(f"{row['"'"'id'"'"']}\t{row['"'"'title'"'"']}")
' <<<"$RESULT")
    then
        :
    else
        selection_status=$?
        exit $selection_status
    fi

    BOOK_ID="${SELECTION%%$'\t'*}"
    BOOK_TITLE="${SELECTION#*$'\t'}"
    echo "Found: $BOOK_TITLE (ID: $BOOK_ID)" >&2
fi

# Search within the book
echo "Searching for '$QUERY' in book $BOOK_ID..." >&2
python3 "$SCRIPT_DIR/search_content.py" \
    --fts-db "$FTS_DB" \
    --metadata-db "$META_DB" \
    --book-id "$BOOK_ID" \
    --query "$QUERY" \
    --context "$CHARS" \
    --limit 5
