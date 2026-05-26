from __future__ import annotations

import importlib.util
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "list_books.py"

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("list_books", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Could not load {SCRIPT_PATH}")
list_books = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = list_books
SPEC.loader.exec_module(list_books)


class ListBooksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.metadata_db = Path(self.temp_dir.name) / "metadata.db"
        self._build_metadata_db()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _build_metadata_db(self) -> None:
        conn = sqlite3.connect(self.metadata_db)
        try:
            conn.executescript(
                """
                CREATE TABLE books (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    author_sort TEXT,
                    pubdate TEXT,
                    timestamp TEXT,
                    last_modified TEXT,
                    series_index REAL
                );
                CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE books_authors_link (id INTEGER PRIMARY KEY, book INTEGER, author INTEGER);
                CREATE TABLE series (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE books_series_link (id INTEGER PRIMARY KEY, book INTEGER, series INTEGER);
                CREATE TABLE data (book INTEGER, format TEXT);
                CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE books_tags_link (book INTEGER, tag INTEGER);
                CREATE TABLE publishers (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE books_publishers_link (book INTEGER, publisher INTEGER);
                CREATE TABLE ratings (id INTEGER PRIMARY KEY, rating INTEGER);
                CREATE TABLE books_ratings_link (book INTEGER, rating INTEGER);

                INSERT INTO books VALUES
                    (1, 'Hench', 'Walschots, Natalie Zina', '2020-09-22 00:00:00+00:00', '2026-01-01', '2026-01-02', 1.0),
                    (2, 'Villain', 'Walschots, Natalie Zina', '2026-05-19 00:00:00+00:00', '2026-01-03', '2026-01-04', 2.0),
                    (3, 'Starter Villain', 'Scalzi, John', '2023-09-19 00:00:00+00:00', '2026-01-05', '2026-01-06', 1.0);
                INSERT INTO authors VALUES
                    (1, 'Natalie Zina Walschots'),
                    (2, 'John Scalzi');
                INSERT INTO books_authors_link VALUES
                    (1, 1, 1),
                    (2, 2, 1),
                    (3, 3, 2);
                INSERT INTO series VALUES
                    (1, 'Hench'),
                    (2, 'Starter Villain');
                INSERT INTO books_series_link VALUES
                    (1, 1, 1),
                    (2, 2, 1),
                    (3, 3, 2);
                INSERT INTO data VALUES
                    (1, 'EPUB'),
                    (2, 'EPUB'),
                    (3, 'EPUB');
                """
            )
            conn.commit()
        finally:
            conn.close()

    def run_list(self, **kwargs: object) -> tuple[int, object]:
        output = io.StringIO()
        with redirect_stdout(output):
            return_code = list_books.list_books(
                str(self.metadata_db),
                limit=10,
                **kwargs,
            )
        return return_code, json.loads(output.getvalue())

    def test_series_filter_sorts_by_series_index(self) -> None:
        return_code, payload = self.run_list(
            series="Hench",
            sort="series_index",
            order="asc",
        )

        self.assertEqual(0, return_code)
        self.assertEqual(["Hench", "Villain"], [row["title"] for row in payload])
        self.assertEqual(["Hench", "Hench"], [row["series"] for row in payload])
        self.assertEqual([1.0, 2.0], [row["series_index"] for row in payload])

    def test_query_can_match_series_name(self) -> None:
        return_code, payload = self.run_list(query="Hench", sort="series_index")

        self.assertEqual(0, return_code)
        self.assertEqual(["Hench", "Villain"], [row["title"] for row in payload])


if __name__ == "__main__":
    unittest.main()
