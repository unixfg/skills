#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import sys


SORT_COLUMNS = {
    "title": "b.title COLLATE NOCASE",
    "author": "b.author_sort COLLATE NOCASE",
    "pubdate": "b.pubdate",
    "timestamp": "b.timestamp",
    "last_modified": "b.last_modified",
}
DATE_COLUMNS = {
    "pubdate": "b.pubdate",
    "timestamp": "b.timestamp",
    "last_modified": "b.last_modified",
}
ORDERS = {"asc": "ASC", "desc": "DESC"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def emit_error(message, code, return_code=2):
    print(json.dumps({"error": message, "error_code": code}))
    return return_code


def parse_list(value, separator="\x1f"):
    if not value:
        return []
    return [item for item in value.split(separator) if item]


def validate_date(value, option_name):
    if value is None:
        return None
    if not DATE_RE.match(value):
        raise ValueError(f"{option_name} must use YYYY-MM-DD")
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{option_name} must be a valid calendar date")
    return value


def list_books(
    db_path,
    limit=200,
    sort="title",
    order="asc",
    query=None,
    author=None,
    tag=None,
    format_filter=None,
    publisher=None,
    date_field="pubdate",
    from_date=None,
    to_date=None,
):
    if not os.path.exists(db_path):
        return emit_error(f"DB not found: {db_path}", "DB_NOT_FOUND", 2)

    sort = sort.lower()
    order = order.lower()
    date_field = date_field.lower()
    if sort not in SORT_COLUMNS:
        return emit_error(
            f"Invalid sort '{sort}'. Expected one of: {', '.join(SORT_COLUMNS)}",
            "INVALID_SORT",
            2,
        )
    if order not in ORDERS:
        return emit_error(
            f"Invalid order '{order}'. Expected one of: {', '.join(ORDERS)}",
            "INVALID_ORDER",
            2,
        )
    if date_field not in DATE_COLUMNS:
        return emit_error(
            f"Invalid date field '{date_field}'. Expected one of: {', '.join(DATE_COLUMNS)}",
            "INVALID_DATE_FIELD",
            2,
        )
    if limit < 1:
        return emit_error("--limit must be greater than zero", "INVALID_LIMIT", 2)

    try:
        from_date = validate_date(from_date, "--from-date")
        to_date = validate_date(to_date, "--to-date")
    except ValueError as e:
        return emit_error(str(e), "INVALID_DATE", 2)
    if from_date and to_date and from_date > to_date:
        return emit_error("--from-date must be on or before --to-date", "INVALID_DATE_RANGE", 2)

    where_clauses = []
    params = []

    def like_filter(value):
        return f"%{value.lower()}%"

    if query:
        q = like_filter(query)
        where_clauses.append(
            """
            (
                lower(b.title) LIKE ?
                OR EXISTS (
                    SELECT 1 FROM books_authors_link bal
                    JOIN authors a ON a.id = bal.author
                    WHERE bal.book = b.id AND lower(a.name) LIKE ?
                )
                OR EXISTS (
                    SELECT 1 FROM books_tags_link btl
                    JOIN tags t ON t.id = btl.tag
                    WHERE btl.book = b.id AND lower(t.name) LIKE ?
                )
                OR EXISTS (
                    SELECT 1 FROM books_publishers_link bpl
                    JOIN publishers p ON p.id = bpl.publisher
                    WHERE bpl.book = b.id AND lower(p.name) LIKE ?
                )
            )
            """
        )
        params.extend([q, q, q, q])

    if author:
        where_clauses.append(
            """
            EXISTS (
                SELECT 1 FROM books_authors_link bal
                JOIN authors a ON a.id = bal.author
                WHERE bal.book = b.id AND lower(a.name) LIKE ?
            )
            """
        )
        params.append(like_filter(author))

    if tag:
        where_clauses.append(
            """
            EXISTS (
                SELECT 1 FROM books_tags_link btl
                JOIN tags t ON t.id = btl.tag
                WHERE btl.book = b.id AND lower(t.name) LIKE ?
            )
            """
        )
        params.append(like_filter(tag))

    if format_filter:
        where_clauses.append(
            """
            EXISTS (
                SELECT 1 FROM data d
                WHERE d.book = b.id AND upper(d.format) = upper(?)
            )
            """
        )
        params.append(format_filter)

    if publisher:
        where_clauses.append(
            """
            EXISTS (
                SELECT 1 FROM books_publishers_link bpl
                JOIN publishers p ON p.id = bpl.publisher
                WHERE bpl.book = b.id AND lower(p.name) LIKE ?
            )
            """
        )
        params.append(like_filter(publisher))

    date_column = DATE_COLUMNS[date_field]
    if from_date:
        where_clauses.append(f"date({date_column}) >= date(?)")
        params.append(from_date)
    if to_date:
        where_clauses.append(f"date({date_column}) <= date(?)")
        params.append(to_date)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    sort_column = SORT_COLUMNS[sort]
    order_sql = ORDERS[order]

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        sql = f"""
            SELECT
                b.id,
                b.title,
                (
                    SELECT group_concat(name, ', ')
                    FROM (
                        SELECT a.name
                        FROM books_authors_link bal
                        JOIN authors a ON a.id = bal.author
                        WHERE bal.book = b.id
                        ORDER BY bal.id
                    )
                ) AS authors,
                b.pubdate,
                b.timestamp,
                b.last_modified,
                (
                    SELECT group_concat(format, char(31))
                    FROM (
                        SELECT d.format
                        FROM data d
                        WHERE d.book = b.id
                        ORDER BY d.format
                    )
                ) AS formats,
                (
                    SELECT group_concat(name, char(31))
                    FROM (
                        SELECT t.name
                        FROM books_tags_link btl
                        JOIN tags t ON t.id = btl.tag
                        WHERE btl.book = b.id
                        ORDER BY t.name
                    )
                ) AS tags,
                (
                    SELECT group_concat(name, char(31))
                    FROM (
                        SELECT p.name
                        FROM books_publishers_link bpl
                        JOIN publishers p ON p.id = bpl.publisher
                        WHERE bpl.book = b.id
                        ORDER BY p.name
                    )
                ) AS publishers
            FROM books b
            {where_sql}
            ORDER BY {sort_column} {order_sql}, b.title COLLATE NOCASE ASC, b.id ASC
            LIMIT ?
        """
        cur.execute(sql, (*params, limit))
        rows = cur.fetchall()
        res = [
            {
                "id": int(r[0]),
                "title": r[1],
                "authors": r[2],
                "pubdate": r[3],
                "timestamp": r[4],
                "last_modified": r[5],
                "formats": parse_list(r[6]),
                "tags": parse_list(r[7]),
                "publishers": parse_list(r[8]),
            }
            for r in rows
        ]
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        return emit_error(str(e), "LIST_ERROR", 3)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='List books from Calibre metadata.db')
    p.add_argument('--db-path', required=True, help='Path to metadata.db')
    p.add_argument('--limit', type=int, default=200)
    p.add_argument('--sort', default='title', help='Sort by title, author, pubdate, timestamp, or last_modified')
    p.add_argument('--order', default='asc', help='Sort order: asc or desc')
    p.add_argument('--query', help='Match title, author, tag, or publisher')
    p.add_argument('--author', help='Filter by author name')
    p.add_argument('--tag', help='Filter by tag name')
    p.add_argument('--format', dest='format_filter', help='Filter by file format, such as EPUB or PDF')
    p.add_argument('--publisher', help='Filter by publisher name')
    p.add_argument('--date-field', default='pubdate', help='Date field for date filters: pubdate, timestamp, or last_modified')
    p.add_argument('--from-date', help='Inclusive start date in YYYY-MM-DD format')
    p.add_argument('--to-date', help='Inclusive end date in YYYY-MM-DD format')
    args = p.parse_args()
    sys.exit(list_books(
        args.db_path,
        args.limit,
        args.sort,
        args.order,
        args.query,
        args.author,
        args.tag,
        args.format_filter,
        args.publisher,
        args.date_field,
        args.from_date,
        args.to_date,
    ))
