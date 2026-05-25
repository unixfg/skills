from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "search_content.py"
SAMPLE_LIBRARY = Path(__file__).resolve().parents[1] / "sample-library"
METADATA_DB = SAMPLE_LIBRARY / "metadata.db"
FTS_DB = SAMPLE_LIBRARY / "full-text-search.db"

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("search_content", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Could not load {SCRIPT_PATH}")
search_content = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = search_content
SPEC.loader.exec_module(search_content)


class SearchContentTests(unittest.TestCase):
    def run_search(self, **kwargs: object) -> tuple[int, object]:
        output = io.StringIO()
        with redirect_stdout(output):
            return_code = search_content.search_content(
                str(FTS_DB),
                str(METADATA_DB),
                **kwargs,
            )
        return return_code, json.loads(output.getvalue())

    def test_scoped_content_search_returns_real_snippet(self) -> None:
        return_code, payload = self.run_search(
            book_id=1,
            query="Nautilus",
            limit=2,
            context_chars=220,
        )

        self.assertEqual(0, return_code)
        self.assertGreaterEqual(len(payload), 1)
        first = payload[0]
        self.assertEqual(1, first["book_id"])
        self.assertEqual("Twenty Thousand Leagues under the Sea", first["title"])
        self.assertEqual("Jules Verne", first["authors"])
        self.assertIn("Nautilus", first["snippet"])

    def test_scoped_content_search_no_match_returns_empty_array(self) -> None:
        return_code, payload = self.run_search(
            book_id=1,
            query="phrase absent from the bundled sample library 12345",
            limit=2,
            context_chars=220,
        )

        self.assertEqual(0, return_code)
        self.assertEqual([], payload)


if __name__ == "__main__":
    unittest.main()
