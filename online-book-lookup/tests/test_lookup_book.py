from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib import error


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "lookup_book.py"
SPEC = importlib.util.spec_from_file_location("lookup_book", SCRIPT_PATH)
if SPEC is None:
    raise ImportError(f"Could not load spec for {SCRIPT_PATH}")
lookup_book = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lookup_book
SPEC.loader.exec_module(lookup_book)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")


class LookupBookTests(unittest.TestCase):
    def test_search_query_constructs_url_and_normalizes_result(self):
        payload = {
            "numFound": 1,
            "docs": [
                {
                    "key": "/works/OL893415W",
                    "title": "Dune",
                    "author_name": ["Frank Herbert"],
                    "first_publish_year": 1965,
                    "publish_date": ["1965", "1990"],
                    "publisher": ["Chilton Books"],
                    "isbn": ["0441172717", "9780441172719"],
                    "cover_i": 12345,
                    "edition_key": ["OL262758W"],
                    "subject": ["Science fiction", "Arrakis"],
                }
            ],
        }

        with mock.patch.object(
            lookup_book.request,
            "urlopen",
            return_value=FakeResponse(payload),
        ) as urlopen:
            result = lookup_book.lookup_search(
                query="Dune",
                title=None,
                author=None,
                limit=5,
                timeout=15,
            )

        requested_url = urlopen.call_args.args[0].full_url
        self.assertIn("/search.json?", requested_url)
        self.assertIn("q=Dune", requested_url)
        self.assertIn("fields=", requested_url)
        self.assertEqual(result["num_found"], 1)
        self.assertEqual(result["results"][0]["title"], "Dune")
        self.assertEqual(result["results"][0]["authors"], ["Frank Herbert"])
        self.assertEqual(result["results"][0]["isbn_10"], ["0441172717"])
        self.assertEqual(result["results"][0]["isbn_13"], ["9780441172719"])
        self.assertEqual(result["results"][0]["openlibrary_edition_key"], "/books/OL262758W")
        self.assertIn("medium", result["results"][0]["cover_urls"])

    def test_title_author_search_constructs_structured_query(self):
        with mock.patch.object(
            lookup_book.request,
            "urlopen",
            return_value=FakeResponse({"numFound": 0, "docs": []}),
        ) as urlopen:
            result = lookup_book.lookup_search(
                query=None,
                title="The Left Hand of Darkness",
                author="Ursula K. Le Guin",
                limit=3,
                timeout=15,
            )

        requested_url = urlopen.call_args.args[0].full_url
        self.assertIn("title=The+Left+Hand+of+Darkness", requested_url)
        self.assertIn("author=Ursula+K.+Le+Guin", requested_url)
        self.assertIn("limit=3", requested_url)
        self.assertEqual(result["query"]["title"], "The Left Hand of Darkness")
        self.assertEqual(result["query"]["author"], "Ursula K. Le Guin")
        self.assertEqual(result["results"], [])

    def test_isbn_lookup_fetches_work_and_author_followups(self):
        edition = {
            "key": "/books/OL7353617M",
            "title": "Fantastic Mr. Fox",
            "authors": [{"key": "/authors/OL34184A"}],
            "works": [{"key": "/works/OL45804W"}],
            "publish_date": "1998",
            "publishers": ["Puffin"],
            "isbn_10": ["0140328726"],
            "isbn_13": ["9780140328721"],
            "covers": [8739161],
        }
        work = {
            "key": "/works/OL45804W",
            "title": "Fantastic Mr. Fox",
            "first_publish_date": "1970",
            "subjects": ["Foxes", "Farmers"],
        }
        author = {"key": "/authors/OL34184A", "name": "Roald Dahl"}

        def fake_urlopen(req, timeout):
            url = req.full_url
            if url.endswith("/isbn/9780140328721.json"):
                return FakeResponse(edition)
            if url.endswith("/works/OL45804W.json"):
                return FakeResponse(work)
            if url.endswith("/authors/OL34184A.json"):
                return FakeResponse(author)
            raise AssertionError(f"unexpected URL {url}")

        with mock.patch.object(lookup_book.request, "urlopen", side_effect=fake_urlopen):
            result = lookup_book.lookup_isbn("978-0-140-32872-1", timeout=15)

        self.assertEqual(result["lookup_type"], "isbn")
        self.assertEqual(result["query"]["isbn"], "9780140328721")
        self.assertEqual(result["num_found"], 1)
        book = result["results"][0]
        self.assertEqual(book["title"], "Fantastic Mr. Fox")
        self.assertEqual(book["authors"], ["Roald Dahl"])
        self.assertEqual(book["first_publish_year"], 1970)
        self.assertEqual(book["isbn_10"], ["0140328726"])
        self.assertEqual(book["isbn_13"], ["9780140328721"])
        self.assertEqual(book["subjects"], ["Foxes", "Farmers"])
        self.assertEqual(book["source_urls"]["work_api"], "https://openlibrary.org/works/OL45804W.json")
        self.assertEqual(book["source_urls"]["isbn_api"], "https://openlibrary.org/isbn/9780140328721.json")

    def test_isbn_404_returns_empty_success(self):
        def fake_urlopen(req, timeout):
            raise error.HTTPError(
                req.full_url,
                404,
                "Not Found",
                {},
                io.BytesIO(b"not found"),
            )

        with mock.patch.object(lookup_book.request, "urlopen", side_effect=fake_urlopen):
            result = lookup_book.lookup_isbn("9780000000000", timeout=15)

        self.assertEqual(result["num_found"], 0)
        self.assertEqual(result["results"], [])

    def test_limit_validation_rejects_values_above_cap(self):
        with self.assertRaises(lookup_book.ScriptError) as ctx:
            lookup_book.validate_limit(21)

        self.assertEqual(ctx.exception.error_code, "INVALID_LIMIT")

    def test_invalid_json_is_reported_as_structured_error(self):
        with mock.patch.object(
            lookup_book.request,
            "urlopen",
            return_value=FakeResponse(b"not-json"),
        ):
            with self.assertRaises(lookup_book.ScriptError) as ctx:
                lookup_book.fetch_json("https://openlibrary.org/search.json?q=x", timeout=15)

        self.assertEqual(ctx.exception.error_code, "INVALID_JSON_RESPONSE")

    def test_run_reports_http_error_without_traceback(self):
        def fake_urlopen(req, timeout):
            raise error.HTTPError(
                req.full_url,
                500,
                "Server Error",
                {},
                io.BytesIO(b"upstream failed"),
            )

        with mock.patch.object(lookup_book.request, "urlopen", side_effect=fake_urlopen):
            with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                rc = lookup_book.run(["--query", "Dune"])

        self.assertEqual(rc, 3)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["error_code"], "HTTP_ERROR")
        self.assertIn("HTTP 500", payload["error"])

    def test_invalid_argument_combination_is_reported(self):
        with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
            rc = lookup_book.run(["--isbn", "9780140328721", "--query", "fox"])

        self.assertEqual(rc, 2)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["error_code"], "INVALID_ARGUMENTS")


if __name__ == "__main__":
    unittest.main()
