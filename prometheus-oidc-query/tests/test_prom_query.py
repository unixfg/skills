from __future__ import annotations

import importlib.util
import sys
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "prom_query.py"
)
SPEC = importlib.util.spec_from_file_location("prom_query", SCRIPT_PATH)
prom_query = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = prom_query
SPEC.loader.exec_module(prom_query)


class PromQueryTests(unittest.TestCase):
    def make_settings(self, cache_dir: Path, **overrides):
        base = {
            "prometheus_url": "https://prometheus.example.com",
            "token_url": "https://auth.example.com/oauth/token",
            "client_id": "reader",
            "client_secret": "secret",
            "scope": None,
            "ca_bundle": None,
            "timeout": 30.0,
            "cache_path": cache_dir / "token-cache.json",
        }
        base.update(overrides)
        return prom_query.Settings(**base)

    def test_validation_report_flags_missing_required_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = self.make_settings(
                Path(temp_dir),
                prometheus_url="not-a-url",
                token_url=None,
                client_id="",
                client_secret="",
            )

            report = prom_query.build_validation_report(settings)

        self.assertFalse(report["valid"])
        self.assertIn(
            "PROM_QUERY_PROMETHEUS_URL must be an absolute http or https URL",
            report["errors"],
        )
        self.assertIn("PROM_QUERY_TOKEN_URL is required", report["errors"])
        self.assertIn("PROM_QUERY_CLIENT_ID is required", report["errors"])
        self.assertIn("PROM_QUERY_CLIENT_SECRET is required", report["errors"])


    def test_load_settings_rejects_invalid_timeout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with unittest.mock.patch.dict(os.environ, {"PROM_QUERY_TIMEOUT": "not-a-number"}):
                with self.assertRaises(prom_query.ConfigError) as ctx:
                    prom_query.load_settings()

        self.assertEqual(ctx.exception.error_code, "INVALID_TIMEOUT")
        self.assertIn("must be a number", str(ctx.exception))

    def test_read_cached_token_ignores_expiring_tokens(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "token-cache.json"
            cache_path.write_text(
                '{"access_token": "abc", "expires_at": %d}'
                % (int(time.time()) + 10),
                encoding="utf-8",
            )

            cached = prom_query.read_cached_token(cache_path)

        self.assertIsNone(cached)

    def test_get_access_token_uses_existing_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = self.make_settings(Path(temp_dir))
            prom_query.write_cached_token(
                settings.cache_path,
                {
                    "access_token": "cached-token",
                    "expires_at": int(time.time()) + 3600,
                    "scope": None,
                    "token_type": "Bearer",
                },
            )

            with mock.patch.object(prom_query, "fetch_access_token") as fetch_access_token:
                source, token_payload = prom_query.get_access_token(
                    settings,
                    context=mock.Mock(),
                )

        self.assertEqual(source, "cache")
        self.assertEqual(token_payload["access_token"], "cached-token")
        fetch_access_token.assert_not_called()

    def test_get_access_token_refreshes_and_writes_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = self.make_settings(Path(temp_dir))
            with mock.patch.object(
                prom_query,
                "request_json",
                return_value={
                    "access_token": "fresh-token",
                    "expires_in": 1200,
                    "scope": "metrics:read",
                    "token_type": "Bearer",
                },
            ) as request_json:
                source, token_payload = prom_query.get_access_token(
                    settings,
                    context=mock.Mock(),
                    force_refresh=True,
                )

            cached = prom_query.read_cached_token(settings.cache_path)

        self.assertEqual(source, "token_endpoint")
        self.assertEqual(token_payload["access_token"], "fresh-token")
        self.assertEqual(cached["scope"], "metrics:read")
        request_json.assert_called_once()

    def test_perform_query_wraps_response_with_query_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = self.make_settings(Path(temp_dir))
            with mock.patch.object(
                prom_query,
                "get_access_token",
                return_value=(
                    "cache",
                    {
                        "access_token": "cached-token",
                        "expires_at": int(time.time()) + 3600,
                    },
                ),
            ):
                with mock.patch.object(
                    prom_query,
                    "request_json",
                    return_value={"status": "success", "data": {"result": []}},
                ) as request_json:
                    payload = prom_query.perform_query(
                        settings,
                        context=mock.Mock(),
                        expression='up{job="prometheus"}',
                    )

        self.assertEqual(payload["auth_source"], "cache")
        self.assertEqual(payload["query"], 'up{job="prometheus"}')
        self.assertEqual(payload["response"]["status"], "success")
        self.assertIn("/api/v1/query?query=", request_json.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
