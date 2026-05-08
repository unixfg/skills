from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib import error


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "plex_media.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("plex_media", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Could not load {SCRIPT_PATH}")
plex_media = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = plex_media
SPEC.loader.exec_module(plex_media)


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


class PlexMediaTests(unittest.TestCase):
    def test_config_requires_base_url_and_token(self):
        with mock.patch.dict(plex_media.os.environ, {}, clear=True):
            report = plex_media.build_validation_report(plex_media.load_settings())

        self.assertFalse(report["valid"])
        self.assertIn("PLEX_TOKEN is required", report["errors"])
        self.assertIn("PLEX_BASE_URL or PLEX_URL is required", report["errors"])

    def test_search_media_constructs_headers_and_normalizes_video(self):
        payload = {
            "MediaContainer": {
                "SearchResult": [
                    {
                        "Metadata": {
                            "ratingKey": "42",
                            "key": "/library/metadata/42",
                            "guid": "imdb://tt3230854",
                            "type": "show",
                            "title": "The Expanse",
                            "year": 2015,
                            "librarySectionID": 2,
                            "librarySectionTitle": "TV Shows",
                            "summary": "A mystery across the system.",
                            "viewCount": 1,
                            "Guid": [{"id": "tvdb://280619"}, {"id": "bad://../../no"}],
                            "Genre": [{"tag": "Science fiction"}],
                            "Location": [{"path": "/TV/The Expanse"}],
                        }
                    }
                ]
            }
        }
        env = {
            "PLEX_BASE_URL": "http://plex.local:32400/",
            "PLEX_TOKEN": "secret-token",
            "PLEX_CLIENT_IDENTIFIER": "client-1",
        }
        with mock.patch.dict(plex_media.os.environ, env, clear=True):
            with mock.patch.object(plex_media.request, "urlopen", return_value=FakeResponse(payload)) as urlopen:
                result = plex_media.search_media("The Expanse", "tv", 5)

        req = urlopen.call_args.args[0]
        self.assertIn("/library/search?", req.full_url)
        self.assertIn("query=The+Expanse", req.full_url)
        self.assertIn("searchTypes=tv", req.full_url)
        self.assertEqual("secret-token", req.headers["X-plex-token"])
        self.assertEqual("client-1", req.headers["X-plex-client-identifier"])
        self.assertEqual(1, result["num_found"])
        item = result["results"][0]
        self.assertEqual("The Expanse", item["title"])
        self.assertTrue(item["watched"])
        self.assertEqual(["tt3230854"], item["external_ids"]["imdb"])
        self.assertEqual(["280619"], item["external_ids"]["tvdb"])
        self.assertEqual("https://www.imdb.com/title/tt3230854/", item["source_urls"]["imdb"])
        self.assertEqual(["Science fiction"], item["genres"])
        self.assertEqual(["/TV/The Expanse"], item["locations"])

    def test_get_media_fetches_children_when_requested(self):
        detail = {
            "MediaContainer": {
                "Metadata": [{"ratingKey": "42", "type": "show", "title": "Show"}]
            }
        }
        children = {
            "MediaContainer": {
                "Metadata": [{"ratingKey": "43", "type": "season", "title": "Season 1"}]
            }
        }

        def fake_urlopen(req, timeout):
            if req.full_url.endswith("/library/metadata/42"):
                return FakeResponse(detail)
            if "/library/metadata/42/children" in req.full_url:
                return FakeResponse(children)
            raise AssertionError(req.full_url)

        env = {"PLEX_URL": "http://plex.local:32400", "PLEX_TOKEN": "token"}
        with mock.patch.dict(plex_media.os.environ, env, clear=True):
            with mock.patch.object(plex_media.request, "urlopen", side_effect=fake_urlopen):
                result = plex_media.get_media("42", True, 10)

        self.assertEqual("Show", result["result"]["title"])
        self.assertEqual("Season 1", result["children"][0]["title"])

    def test_invalid_json_is_structured_error(self):
        env = {"PLEX_BASE_URL": "http://plex.local:32400", "PLEX_TOKEN": "token"}
        with mock.patch.dict(plex_media.os.environ, env, clear=True):
            with mock.patch.object(plex_media.request, "urlopen", return_value=FakeResponse(b"not-json")):
                with self.assertRaises(plex_media.ScriptError) as ctx:
                    plex_media.search_media("Dune", "movie", 5)

        self.assertEqual("INVALID_JSON_RESPONSE", ctx.exception.error_code)

    def test_http_error_is_structured_error(self):
        def fake_urlopen(req, timeout):
            raise error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b"nope"))

        env = {"PLEX_BASE_URL": "http://plex.local:32400", "PLEX_TOKEN": "bad"}
        with mock.patch.dict(plex_media.os.environ, env, clear=True):
            with mock.patch.object(plex_media.request, "urlopen", side_effect=fake_urlopen):
                with self.assertRaises(plex_media.ScriptError) as ctx:
                    plex_media.search_media("Dune", "movie", 5)

        self.assertEqual("HTTP_ERROR", ctx.exception.error_code)


if __name__ == "__main__":
    unittest.main()
