#!/usr/bin/env python3
"""
Resolve a Calibre book ID to its filesystem path.

Calibre stores books at: {library_root}/{books.path}/{data.name}.{format}
"""
import argparse
import json
import os
import sqlite3
import sys

from calibre_utils import choose_preferred_format, normalize_format


def resolve(metadata_db, library_root, book_id, format_pref="EPUB"):
    if not os.path.exists(metadata_db):
        print(json.dumps({"error": f"Metadata DB not found: {metadata_db}"}))
        return 2
    
    conn = sqlite3.connect(metadata_db)
    cur = conn.cursor()
    
    try:
        # Get book path from books table
        cur.execute("SELECT title, path FROM books WHERE id = ?", (book_id,))
        row = cur.fetchone()
        if not row:
            print(json.dumps({"error": f"Book {book_id} not found"}))
            return 1
        
        title, book_path = row
        
        # Get available formats from data table
        cur.execute("SELECT format, name FROM data WHERE book = ?", (book_id,))
        formats = {r[0]: r[1] for r in cur.fetchall()}
        
        if not formats:
            print(json.dumps({"error": f"No formats found for book {book_id}"}))
            return 1
        
        # Pick preferred format or first available
        fmt = choose_preferred_format(formats.keys(), normalize_format(format_pref))
        
        filename = f"{formats[fmt]}.{fmt.lower()}"
        full_path = os.path.join(library_root, book_path, filename)
        
        result = {
            "book_id": book_id,
            "title": title,
            "format": fmt,
            "path": full_path,
            "exists": os.path.exists(full_path),
            "available_formats": sorted(formats.keys())
        }
        print(json.dumps(result, indent=2))
        return 0
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return 3

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Resolve book ID to file path')
    p.add_argument('--metadata-db', required=True, help='Path to metadata.db')
    p.add_argument('--library-root', required=True, help='Calibre library root')
    p.add_argument('--book-id', required=True, type=int, help='Book ID')
    p.add_argument('--format', default='EPUB', help='Preferred format (default: EPUB)')
    args = p.parse_args()
    sys.exit(resolve(args.metadata_db, args.library_root, args.book_id, args.format))
