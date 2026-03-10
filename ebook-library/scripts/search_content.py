#!/usr/bin/env python3
"""
Search book content using Calibre's full-text-search.db.

Note: Calibre's FTS5 tables use a custom tokenizer that isn't available outside
Calibre, so we query the underlying books_text table directly with LIKE.
"""
import sqlite3
import json
import argparse
import os
import sys

from calibre_utils import build_excerpt, choose_preferred_format, normalize_format


def _load_book_metadata(meta_conn, book_id):
    meta_cur = meta_conn.cursor()
    meta_cur.execute(
        """
        SELECT b.title, group_concat(a.name, ', ')
        FROM books b
        LEFT JOIN books_authors_link bal ON bal.book = b.id
        LEFT JOIN authors a ON a.id = bal.author
        WHERE b.id = ?
        GROUP BY b.id
        """,
        (book_id,),
    )
    meta_row = meta_cur.fetchone()
    if not meta_row:
        return None
    return {"title": meta_row[0], "authors": meta_row[1]}


def _search_single_book(fts_conn, meta_conn, book_id, query, limit, context_chars, format_filter):
    metadata = _load_book_metadata(meta_conn, book_id)
    if not metadata:
        print(json.dumps({"error": f"Book {book_id} not found"}))
        return 1

    fts_cur = fts_conn.cursor()
    if format_filter:
        fts_cur.execute(
            """
            SELECT format, searchable_text
            FROM books_text
            WHERE book = ? AND upper(format) = ?
            ORDER BY format
            """,
            (book_id, normalize_format(format_filter)),
        )
    else:
        fts_cur.execute(
            """
            SELECT format, searchable_text
            FROM books_text
            WHERE book = ?
            ORDER BY format
            """,
            (book_id,),
        )

    rows = fts_cur.fetchall()
    if not rows:
        print(json.dumps({"error": f"No text found for book {book_id}"}))
        return 1

    selected_format = choose_preferred_format([row[0] for row in rows], format_filter)
    searchable_text = next(text for fmt, text in rows if fmt == selected_format)
    lower_text = searchable_text.lower()
    lower_query = query.lower()

    results = []
    start = 0
    while len(results) < limit:
        pos = lower_text.find(lower_query, start)
        if pos == -1:
            break
        results.append(
            {
                "book_id": book_id,
                "title": metadata["title"],
                "authors": metadata["authors"],
                "format": selected_format,
                "snippet": build_excerpt(searchable_text, pos, context_chars),
            }
        )
        start = pos + 1

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


def search_content(
    fts_db,
    metadata_db,
    query,
    limit=20,
    context_chars=300,
    book_id=None,
    format_filter=None,
):
    if not os.path.exists(fts_db):
        print(json.dumps({"error": f"FTS DB not found: {fts_db}"}))
        return 2
    if not os.path.exists(metadata_db):
        print(json.dumps({"error": f"Metadata DB not found: {metadata_db}"}))
        return 2
    if not query:
        print(json.dumps({"error": "Query must not be empty"}))
        return 1

    fts_conn = sqlite3.connect(fts_db)
    meta_conn = sqlite3.connect(metadata_db)

    try:
        if book_id is not None:
            return _search_single_book(
                fts_conn,
                meta_conn,
                book_id,
                query,
                limit,
                context_chars,
                format_filter,
            )

        pattern = f"%{query}%"
        fts_cur = fts_conn.cursor()

        if format_filter:
            fts_cur.execute("""
                SELECT book, format, instr(lower(searchable_text), lower(?)) as pos
                FROM books_text
                WHERE lower(searchable_text) LIKE lower(?) AND upper(format) = ?
                ORDER BY book
                LIMIT ?
            """, (query, pattern, normalize_format(format_filter), limit * 3))
        else:
            fts_cur.execute("""
                SELECT DISTINCT book, format, instr(lower(searchable_text), lower(?)) as pos
                FROM books_text
                WHERE lower(searchable_text) LIKE lower(?)
                ORDER BY book,
                    CASE upper(format)
                        WHEN 'EPUB' THEN 0
                        WHEN 'AZW3' THEN 1
                        WHEN 'KFX' THEN 2
                        WHEN 'MOBI' THEN 3
                        WHEN 'PDF' THEN 4
                        ELSE 5
                    END,
                    format
                LIMIT ?
            """, (query, pattern, limit * 3))

        seen_books = set()
        results = []

        for row in fts_cur.fetchall():
            bid, fmt, pos = row
            if bid in seen_books:
                continue
            seen_books.add(bid)

            # Get book metadata
            metadata = _load_book_metadata(meta_conn, bid)
            title = metadata["title"] if metadata else f"Book {bid}"
            authors = metadata["authors"] if metadata else None

            # Get context snippet centered on the match
            start = max(1, pos - context_chars // 2)
            fts_cur.execute("""
                SELECT substr(searchable_text, ?, ?)
                FROM books_text WHERE book = ? AND format = ?
            """, (start, context_chars, bid, fmt))
            snippet_row = fts_cur.fetchone()
            snippet = snippet_row[0].strip() if snippet_row and snippet_row[0] else ""
            
            results.append({
                "book_id": bid,
                "title": title,
                "authors": authors,
                "format": fmt,
                "snippet": snippet
            })
            
            if len(results) >= limit:
                break
        
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return 3

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Search book content via Calibre FTS')
    p.add_argument('--fts-db', required=True, help='Path to full-text-search.db')
    p.add_argument('--metadata-db', required=True, help='Path to metadata.db')
    p.add_argument('--query', required=True, help='Search term')
    p.add_argument('--book-id', type=int, help='Limit search to a specific book ID (faster)')
    p.add_argument('--format', help='Prefer or restrict to a specific format (for example EPUB)')
    p.add_argument('--limit', type=int, default=10, help='Max results (default: 10)')
    p.add_argument('--context', type=int, default=300, help='Context chars around match (default: 300)')
    args = p.parse_args()
    sys.exit(
        search_content(
            args.fts_db,
            args.metadata_db,
            args.query,
            args.limit,
            args.context,
            args.book_id,
            args.format,
        )
    )
