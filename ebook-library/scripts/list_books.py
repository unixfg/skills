#!/usr/bin/env python3
import json
import sqlite3
import argparse
import os
import sys

def list_books(db_path, limit=200):
    if not os.path.exists(db_path):
        print(json.dumps({"error": f"DB not found: {db_path}"}))
        return 2
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute("SELECT b.id, b.title FROM books b ORDER BY b.title LIMIT ?", (limit,))
        rows = cur.fetchall()
        res = [{"id": int(r[0]), "title": r[1]} for r in rows]
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return 3

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='List books from Calibre metadata.db')
    p.add_argument('--db-path', required=True, help='Path to metadata.db')
    p.add_argument('--limit', type=int, default=200)
    args = p.parse_args()
    sys.exit(list_books(args.db_path, args.limit))
