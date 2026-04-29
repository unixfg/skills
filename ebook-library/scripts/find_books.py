#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import sys


def emit_error(message, code, return_code=2):
    print(json.dumps({"error": message, "error_code": code}))
    return return_code


def search(db_path, query, limit=50):
    if not os.path.exists(db_path):
        return emit_error(f"DB not found: {db_path}", "DB_NOT_FOUND", 2)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    q = f"%{query.lower()}%"
    exact = query.lower()
    try:
        sql = (
            "SELECT b.id, b.title, group_concat(a.name, ', ') AS authors, "
            "b.pubdate, b.timestamp, b.last_modified "
            "FROM books b LEFT JOIN books_authors_link bal ON bal.book=b.id "
            "LEFT JOIN authors a ON a.id=bal.author "
            "WHERE lower(b.title) LIKE ? OR lower(a.name) LIKE ? "
            "GROUP BY b.id "
            "ORDER BY CASE "
            "WHEN lower(b.title) = ? THEN 0 "
            "WHEN lower(a.name) = ? THEN 1 "
            "ELSE 2 END, b.title "
            "LIMIT ?"
        )
        cur.execute(sql, (q, q, exact, exact, limit))
        rows = cur.fetchall()
        out = []
        for r in rows:
            out.append({
                "id": int(r[0]),
                "title": r[1],
                "authors": r[2],
                "pubdate": r[3],
                "timestamp": r[4],
                "last_modified": r[5],
            })
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        return emit_error(str(e), "METADATA_QUERY_ERROR", 3)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Find books by keyword in Calibre metadata')
    p.add_argument('--db-path', required=True, help='Path to metadata.db')
    p.add_argument('--query', required=True, help='Search term')
    p.add_argument('--limit', type=int, default=50)
    args = p.parse_args()
    sys.exit(search(args.db_path, args.query, args.limit))
