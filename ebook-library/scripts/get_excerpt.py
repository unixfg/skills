#!/usr/bin/env python3
"""
Get an excerpt from a book around a specific keyword or at a position.

Usage:
  get_excerpt.py --book-id 2525 --around "Abdulla" --chars 800
  get_excerpt.py --book-id 2525 --position 50000 --chars 1000
"""
import argparse
import json
import os
import sqlite3
import sys

from calibre_utils import build_excerpt, choose_preferred_format, normalize_format


def emit_error(message, code, return_code=2):
    print(json.dumps({"error": message, "error_code": code}))
    return return_code


def get_excerpt(
    fts_db,
    metadata_db,
    book_id,
    around=None,
    position=None,
    chars=800,
    occurrence=1,
    format_filter=None,
):
    if not os.path.exists(fts_db):
        return emit_error(f"FTS DB not found: {fts_db}", "DB_NOT_FOUND", 2)
    if not os.path.exists(metadata_db):
        return emit_error(f"Metadata DB not found: {metadata_db}", "DB_NOT_FOUND", 2)
    if not around and position is None:
        return emit_error("Must specify --around or --position", "INVALID_ARGUMENT", 1)
    if occurrence < 1:
        return emit_error("Occurrence must be at least 1", "INVALID_ARGUMENT", 1)

    fts_conn = sqlite3.connect(fts_db)
    meta_conn = sqlite3.connect(metadata_db)

    try:
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
            return emit_error(f"Book {book_id} not found", "BOOK_NOT_FOUND", 1)
        title, authors = meta_row

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
            return emit_error(f"No text found for book {book_id}", "BOOK_TEXT_MISSING", 1)

        selected_format = choose_preferred_format([row[0] for row in rows], format_filter)
        text = next(searchable_text for fmt, searchable_text in rows if fmt == selected_format)
        text_len = len(text)

        if around:
            search_text = text.lower()
            keyword = around.lower()
            pos = -1
            for _ in range(occurrence):
                pos = search_text.find(keyword, pos + 1)
                if pos == -1:
                    break

            if pos == -1:
                return emit_error(
                    f"Keyword '{around}' not found in book",
                    "KEYWORD_NOT_FOUND",
                    1,
                )
        else:
            if position < 0 or position >= text_len:
                return emit_error(f"Position {position} is outside the book text", "POSITION_OUT_OF_RANGE", 1)
            pos = position

        result = {
            "book_id": book_id,
            "title": title,
            "authors": authors,
            "format": selected_format,
            "position": pos,
            "total_length": text_len,
            "excerpt": build_excerpt(text, pos, chars),
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        return emit_error(str(e), "EXCERPT_ERROR", 3)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Get excerpt from a book')
    p.add_argument('--fts-db', required=True, help='Path to full-text-search.db')
    p.add_argument('--metadata-db', required=True, help='Path to metadata.db')
    p.add_argument('--book-id', required=True, type=int, help='Book ID')
    p.add_argument('--around', help='Keyword to center excerpt on')
    p.add_argument('--position', type=int, help='Character position to center on')
    p.add_argument('--format', help='Prefer a specific format (for example EPUB)')
    p.add_argument('--chars', type=int, default=800, help='Excerpt length (default: 800)')
    p.add_argument('--occurrence', type=int, default=1, help='Which occurrence of keyword (default: 1)')
    args = p.parse_args()
    sys.exit(
        get_excerpt(
            args.fts_db,
            args.metadata_db,
            args.book_id,
            args.around,
            args.position,
            args.chars,
            args.occurrence,
            args.format,
        )
    )
