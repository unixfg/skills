from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "video_lookup.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("video_lookup", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Could not load {SCRIPT_PATH}")
video_lookup = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = video_lookup
SPEC.loader.exec_module(video_lookup)


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


class VideoLookupTests(unittest.TestCase):
    def test_config_reports_optional_sources_without_requiring_them(self):
        with mock.patch.dict(video_lookup.os.environ, {}, clear=True):
            report = video_lookup.build_validation_report(video_lookup.load_settings())

        self.assertTrue(report["valid"])
        self.assertTrue(report["sources"]["wikipedia"]["available"])
        self.assertFalse(report["sources"]["tmdb"]["available"])
        self.assertEqual("link-only from official metadata; no scraping", report["sources"]["imdb"]["mode"])

    def test_wikipedia_lookup_skips_unconfigured_optional_sources(self):
        wiki_payload = {
            "query": {
                "search": [
                    {
                        "pageid": 123,
                        "title": "Severance (TV series)",
                        "snippet": "A <span>science fiction</span> thriller.",
                    }
                ]
            }
        }
        with mock.patch.dict(video_lookup.os.environ, {}, clear=True):
            with mock.patch.object(video_lookup.request, "urlopen", return_value=FakeResponse(wiki_payload)) as urlopen:
                result = video_lookup.lookup_video("Severance", "tv", "all", None, False, 5)

        requested_urls = [call.args[0].full_url for call in urlopen.call_args_list]
        self.assertEqual(1, len(requested_urls))
        self.assertIn("en.wikipedia.org/w/api.php", requested_urls[0])
        self.assertNotIn("imdb.com", requested_urls[0])
        self.assertEqual("A science fiction thriller.", result["results"][0]["summary"])
        self.assertEqual("TMDB_READ_ACCESS_TOKEN or TMDB_API_KEY is not configured", result["sources"]["tmdb"]["skipped"])
        self.assertEqual("TVDB_API_KEY is not configured", result["sources"]["tvdb"]["skipped"])

    def test_tmdb_lookup_uses_bearer_auth_and_extracts_trailers_and_imdb_link(self):
        search_payload = {
            "results": [
                {
                    "id": 11,
                    "title": "Star Wars",
                    "release_date": "1977-05-25",
                    "overview": "Space opera.",
                    "vote_average": 8.2,
                }
            ]
        }
        detail_payload = {
            "imdb_id": "tt0076759",
            "external_ids": {"imdb_id": "tt0076759"},
            "videos": {
                "results": [
                    {
                        "site": "YouTube",
                        "key": "abc123",
                        "type": "Trailer",
                        "name": "Official Trailer",
                        "official": True,
                    },
                    {"site": "Vimeo", "key": "ignored", "type": "Trailer"},
                ]
            },
        }

        def fake_urlopen(req, timeout):
            if "/search/movie" in req.full_url:
                return FakeResponse(search_payload)
            if "/movie/11?" in req.full_url:
                return FakeResponse(detail_payload)
            raise AssertionError(req.full_url)

        with mock.patch.dict(video_lookup.os.environ, {"TMDB_READ_ACCESS_TOKEN": "token"}, clear=True):
            with mock.patch.object(video_lookup.request, "urlopen", side_effect=fake_urlopen) as urlopen:
                result = video_lookup.lookup_video("Star Wars", "movie", "tmdb", None, True, 5)

        first_req = urlopen.call_args_list[0].args[0]
        self.assertEqual("Bearer token", first_req.headers["Authorization"])
        item = result["results"][0]
        self.assertEqual("TMDB", item["source"])
        self.assertEqual("https://www.imdb.com/title/tt0076759/", item["source_urls"]["imdb"])
        self.assertEqual("https://www.youtube.com/watch?v=abc123", item["trailers"][0]["url"])

    def test_explicit_tmdb_without_credentials_is_config_error(self):
        with mock.patch.dict(video_lookup.os.environ, {}, clear=True):
            with self.assertRaises(video_lookup.ScriptError) as ctx:
                video_lookup.lookup_video("Star Wars", "movie", "tmdb", None, False, 5)

        self.assertEqual("CONFIG_ERROR", ctx.exception.error_code)

    def test_invalid_json_is_structured_error(self):
        with mock.patch.object(video_lookup.request, "urlopen", return_value=FakeResponse(b"not-json")):
            with self.assertRaises(video_lookup.ScriptError) as ctx:
                video_lookup.wikipedia_search("x", 1, 15)

        self.assertEqual("INVALID_JSON_RESPONSE", ctx.exception.error_code)


if __name__ == "__main__":
    unittest.main()
