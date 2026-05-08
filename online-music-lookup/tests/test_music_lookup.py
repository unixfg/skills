from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "music_lookup.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("music_lookup", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Could not load {SCRIPT_PATH}")
music_lookup = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = music_lookup
SPEC.loader.exec_module(music_lookup)


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


class MusicLookupTests(unittest.TestCase):
    def test_config_reports_oauth_but_does_not_require_it_for_search(self):
        env = {"MUSICBRAINZ_ID": "client", "MUSICBRAINZ_SECRET": "secret"}
        with mock.patch.dict(music_lookup.os.environ, env, clear=True):
            report = music_lookup.build_validation_report(music_lookup.load_settings())

        mb = report["sources"]["musicbrainz"]
        self.assertTrue(mb["available"])
        self.assertTrue(mb["oauth_configured"])
        self.assertFalse(mb["oauth_required_for_search"])

    def test_musicbrainz_artist_search_uses_user_agent_and_normalizes_result(self):
        mbid = "0383dadf-2a4e-4d10-a46a-e9e041da8eb3"
        payload = {
            "artists": [
                {
                    "id": mbid,
                    "name": "Queen",
                    "sort-name": "Queen",
                    "type": "Group",
                    "country": "GB",
                    "score": 100,
                    "tags": [{"name": "rock"}],
                }
            ]
        }
        with mock.patch.dict(music_lookup.os.environ, {"MUSICBRAINZ_DELAY_SECONDS": "0"}, clear=True):
            with mock.patch.object(music_lookup.request, "urlopen", return_value=FakeResponse(payload)) as urlopen:
                result = music_lookup.lookup_music("Queen", "artist", "musicbrainz", 5)

        req = urlopen.call_args.args[0]
        self.assertIn("musicbrainz.org/ws/2/artist", req.full_url)
        self.assertEqual(music_lookup.USER_AGENT, req.headers["User-agent"])
        item = result["results"][0]
        self.assertEqual("MusicBrainz", item["source"])
        self.assertEqual("Queen", item["title"])
        self.assertEqual("https://musicbrainz.org/artist/0383dadf-2a4e-4d10-a46a-e9e041da8eb3", item["source_urls"]["musicbrainz"])

    def test_all_musicbrainz_search_respects_delay_between_entity_requests(self):
        responses = [
            FakeResponse({"artists": []}),
            FakeResponse({"release-groups": []}),
            FakeResponse({"releases": []}),
            FakeResponse({"recordings": []}),
        ]
        with mock.patch.dict(music_lookup.os.environ, {"MUSICBRAINZ_DELAY_SECONDS": "0.25"}, clear=True):
            with mock.patch.object(music_lookup.request, "urlopen", side_effect=responses):
                with mock.patch.object(music_lookup.time, "sleep") as sleep:
                    result = music_lookup.lookup_music("nothing", "all", "musicbrainz", 5)

        self.assertEqual(0, result["num_found"])
        self.assertEqual(3, sleep.call_count)
        sleep.assert_called_with(0.25)

    def test_wikipedia_no_match_is_honest_empty_result(self):
        with mock.patch.object(music_lookup.request, "urlopen", return_value=FakeResponse({"query": {"search": []}})):
            result = music_lookup.lookup_music("definitely missing", "artist", "wikipedia", 5)

        self.assertEqual(0, result["num_found"])
        self.assertEqual([], result["results"])

    def test_invalid_limit_rejected(self):
        with self.assertRaises(music_lookup.ScriptError) as ctx:
            music_lookup.validate_limit(11)

        self.assertEqual("INVALID_LIMIT", ctx.exception.error_code)


if __name__ == "__main__":
    unittest.main()
