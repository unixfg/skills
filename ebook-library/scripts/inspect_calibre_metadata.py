#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import sys


def emit_error(message, code, return_code=2):
    print(json.dumps({"error": message, "error_code": code}))
    return return_code


def fetch_metadata(db_path, limit=200):
    if not os.path.exists(db_path):
        return emit_error(f"DB not found: {db_path}", "DB_NOT_FOUND", 2)
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM books")
        book_count = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM authors")
        author_count = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM data")
        format_row_count = int(cur.fetchone()[0])

        cur.execute(
            """
            SELECT format, COUNT(*)
            FROM data
            GROUP BY format
            ORDER BY COUNT(*) DESC, format
            """
        )
        format_counts = {fmt: count for fmt, count in cur.fetchall()}

        cur.execute(
            """
            SELECT b.id, b.title, group_concat(a.name, ', ') as authors
            FROM books b
            LEFT JOIN books_authors_link bal ON bal.book = b.id
            LEFT JOIN authors a ON a.id = bal.author
            GROUP BY b.id
            ORDER BY b.title
            LIMIT ?
            """,
            (limit,),
        )
        sample_books = []
        for row in cur.fetchall():
            sample_books.append({
                "id": int(row[0]),
                "title": row[1],
                "authors": row[2],
            })

        print(
            json.dumps(
                {
                    "book_count": book_count,
                    "author_count": author_count,
                    "format_row_count": format_row_count,
                    "format_counts": format_counts,
                    "sample_books": sample_books,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as e:
        return emit_error(str(e), "INSPECT_ERROR", 3)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Calibre metadata inspector (read-only).')
    p.add_argument('--db-path', required=True, help='Path to metadata.db')
    p.add_argument('--limit', type=int, default=200, help='Max number of books to fetch')
    args = p.parse_args()
    rc = fetch_metadata(args.db_path, args.limit)
    sys.exit(rc)
