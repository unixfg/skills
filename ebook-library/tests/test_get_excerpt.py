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
SCRIPT_PATH = SCRIPT_DIR / "get_excerpt.py"

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("get_excerpt", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Could not load {SCRIPT_PATH}")
get_excerpt = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = get_excerpt
SPEC.loader.exec_module(get_excerpt)


class GetExcerptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.metadata_db = root / "metadata.db"
        self.fts_db = root / "full-text-search.db"
        self._build_metadata_db()
        self._build_fts_db()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _build_metadata_db(self) -> None:
        conn = sqlite3.connect(self.metadata_db)
        try:
            conn.executescript(
                """
                CREATE TABLE books (id INTEGER PRIMARY KEY, title TEXT);
                CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE books_authors_link (book INTEGER, author INTEGER);
                INSERT INTO books (id, title) VALUES (2572, 'Villain');
                INSERT INTO authors (id, name) VALUES (1, 'Natalie Zina Walschots');
                INSERT INTO books_authors_link (book, author) VALUES (2572, 1);
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _build_fts_db(self) -> None:
        text = (
            "It was a better than average attendance, with participants from "
            "Data, Research, Comms, Information & Identities, and Disruption. "
            + ("padding " * 1500)
            + "Someone from I&I, one of Menachem's new hires, openly cheered."
        )
        conn = sqlite3.connect(self.fts_db)
        try:
            conn.executescript(
                """
                CREATE TABLE books_text (
                    book INTEGER,
                    format TEXT,
                    searchable_text TEXT
                );
                """
            )
            conn.execute(
                "INSERT INTO books_text (book, format, searchable_text) VALUES (?, ?, ?)",
                (2572, "EPUB", text),
            )
            conn.commit()
        finally:
            conn.close()

    def run_excerpt(self, **kwargs: object) -> tuple[int, object]:
        output = io.StringIO()
        with redirect_stdout(output):
            return_code = get_excerpt.get_excerpt(
                str(self.fts_db),
                str(self.metadata_db),
                **kwargs,
            )
        return return_code, json.loads(output.getvalue())

    def test_centered_chars_behavior_still_works(self) -> None:
        return_code, payload = self.run_excerpt(
            book_id=2572,
            around="I&I",
            chars=80,
        )

        self.assertEqual(0, return_code)
        self.assertEqual(2572, payload["book_id"])
        self.assertEqual("Villain", payload["title"])
        self.assertIn("I&I", payload["excerpt"])
        self.assertNotIn("Information & Identities", payload["excerpt"])

    def test_before_after_window_can_include_distant_relevant_text(self) -> None:
        return_code, payload = self.run_excerpt(
            book_id=2572,
            around="I&I",
            before_chars=13000,
            after_chars=200,
        )

        self.assertEqual(0, return_code)
        self.assertEqual(2572, payload["book_id"])
        self.assertEqual("Natalie Zina Walschots", payload["authors"])
        self.assertIn("Information & Identities", payload["excerpt"])
        self.assertIn("I&I", payload["excerpt"])
        self.assertLess(payload["start_position"], payload["position"])
        self.assertGreater(payload["end_position"], payload["position"])


if __name__ == "__main__":
    unittest.main()
