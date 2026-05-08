from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "plex_music.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("plex_music", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Could not load {SCRIPT_PATH}")
plex_music = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = plex_music
SPEC.loader.exec_module(plex_music)


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


class PlexMusicTests(unittest.TestCase):
    def test_config_requires_base_url_and_token(self):
        with mock.patch.dict(plex_music.os.environ, {}, clear=True):
            report = plex_music.build_validation_report(plex_music.load_settings())

        self.assertFalse(report["valid"])
        self.assertIn("PLEX_TOKEN is required", report["errors"])

    def test_search_music_constructs_headers_and_normalizes_album_track(self):
        payload = {
            "MediaContainer": {
                "SearchResult": [
                    {
                        "Metadata": {
                            "ratingKey": "77",
                            "type": "album",
                            "title": "Blue Lines",
                            "year": 1991,
                            "librarySectionTitle": "Music",
                            "Guid": [{"id": "musicbrainz://3f0aa...bad"}],
                            "Genre": [{"tag": "Trip hop"}],
                            "Location": [{"path": "/Music/Massive Attack/Blue Lines"}],
                        }
                    },
                    {
                        "Metadata": {
                            "ratingKey": "78",
                            "type": "track",
                            "title": "Safe From Harm",
                            "parentTitle": "Blue Lines",
                            "grandparentTitle": "Massive Attack",
                            "viewCount": 2,
                            "Media": [{"Part": [{"file": "/Music/file.flac"}]}],
                        }
                    },
                ]
            }
        }
        env = {
            "PLEX_BASE_URL": "http://plex.local:32400",
            "PLEX_TOKEN": "secret-token",
        }
        with mock.patch.dict(plex_music.os.environ, env, clear=True):
            with mock.patch.object(plex_music.request, "urlopen", return_value=FakeResponse(payload)) as urlopen:
                result = plex_music.search_music("Blue Lines", "all", 5)

        req = urlopen.call_args.args[0]
        self.assertIn("searchTypes=music", req.full_url)
        self.assertEqual("secret-token", req.headers["X-plex-token"])
        self.assertEqual(2, result["num_found"])
        album = result["results"][0]
        track = result["results"][1]
        self.assertEqual("Blue Lines", album["title"])
        self.assertEqual(["Trip hop"], album["genres"])
        self.assertEqual(["/Music/Massive Attack/Blue Lines"], album["locations"])
        self.assertEqual("Massive Attack", track["artist"])
        self.assertEqual("Blue Lines", track["album"])
        self.assertTrue(track["listened"])
        self.assertEqual(["/Music/file.flac"], track["locations"])

    def test_get_music_no_metadata_is_not_found(self):
        env = {"PLEX_URL": "http://plex.local:32400", "PLEX_TOKEN": "token"}
        payload = {"MediaContainer": {"Metadata": []}}
        with mock.patch.dict(plex_music.os.environ, env, clear=True):
            with mock.patch.object(plex_music.request, "urlopen", return_value=FakeResponse(payload)):
                with self.assertRaises(plex_music.ScriptError) as ctx:
                    plex_music.get_music("99", False, 10)

        self.assertEqual("NOT_FOUND", ctx.exception.error_code)

    def test_invalid_limit_rejected(self):
        with self.assertRaises(plex_music.ScriptError) as ctx:
            plex_music.validate_limit(21)

        self.assertEqual("INVALID_LIMIT", ctx.exception.error_code)


if __name__ == "__main__":
    unittest.main()
