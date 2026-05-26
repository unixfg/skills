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
SCRIPT_PATH = SCRIPT_DIR / "find_books.py"

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("find_books", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Could not load {SCRIPT_PATH}")
find_books = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = find_books
SPEC.loader.exec_module(find_books)


class FindBooksTests(unittest.TestCase):
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
                    pubdate TEXT,
                    timestamp TEXT,
                    last_modified TEXT,
                    series_index REAL
                );
                CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE books_authors_link (book INTEGER, author INTEGER);
                CREATE TABLE series (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE books_series_link (id INTEGER PRIMARY KEY, book INTEGER, series INTEGER);

                INSERT INTO books VALUES
                    (1, 'Hench', '2020-09-22 00:00:00+00:00', '2026-01-01', '2026-01-02', 1.0),
                    (2, 'Villain', '2026-05-19 00:00:00+00:00', '2026-01-03', '2026-01-04', 2.0),
                    (3, 'Starter Villain', '2023-09-19 00:00:00+00:00', '2026-01-05', '2026-01-06', 1.0);
                INSERT INTO authors VALUES
                    (1, 'Natalie Zina Walschots'),
                    (2, 'John Scalzi');
                INSERT INTO books_authors_link VALUES
                    (1, 1),
                    (2, 1),
                    (3, 2);
                INSERT INTO series VALUES
                    (1, 'Hench'),
                    (2, 'Starter Villain');
                INSERT INTO books_series_link VALUES
                    (1, 1, 1),
                    (2, 2, 1),
                    (3, 3, 2);
                """
            )
            conn.commit()
        finally:
            conn.close()

    def run_find(self, query: str) -> tuple[int, object]:
        output = io.StringIO()
        with redirect_stdout(output):
            return_code = find_books.search(str(self.metadata_db), query, limit=10)
        return return_code, json.loads(output.getvalue())

    def test_title_lookup_returns_series_metadata(self) -> None:
        return_code, payload = self.run_find("Villain")

        self.assertEqual(0, return_code)
        self.assertEqual("Villain", payload[0]["title"])
        self.assertEqual("Hench", payload[0]["series"])
        self.assertEqual(2.0, payload[0]["series_index"])

    def test_series_name_is_searchable(self) -> None:
        return_code, payload = self.run_find("Hench")

        self.assertEqual(0, return_code)
        self.assertEqual(["Hench", "Villain"], [row["title"] for row in payload])
        self.assertEqual([1.0, 2.0], [row["series_index"] for row in payload])


if __name__ == "__main__":
    unittest.main()
