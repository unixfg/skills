#!/usr/bin/env python3
"""Prometheus query helper with OAuth2 client-credentials auth."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request


CACHE_DIRECTORY = "prometheus-oidc-query"
CACHE_FILENAME = "token-cache.json"
DEFAULT_TIMEOUT_SECONDS = 30.0
REFRESH_SKEW_SECONDS = 60


class ScriptError(Exception):
    """Raised when the script cannot continue and should fail with an error payload."""

    def __init__(self, message: str, *, error_code: str):
        super().__init__(message)
        self.error_code = error_code


class ConfigError(ScriptError):
    """Raised when configuration is incomplete or invalid."""


class HttpRequestError(ScriptError):
    """Raised when an HTTP request fails."""


@dataclass
class Settings:
    prometheus_url: str | None
    token_url: str | None
    client_id: str | None
    client_secret: str | None
    scope: str | None
    ca_bundle: str | None
    timeout: float
    cache_path: Path


def cache_path() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))
    return base / CACHE_DIRECTORY / CACHE_FILENAME


def load_settings() -> Settings:
    timeout_text = os.environ.get("PROM_QUERY_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        timeout = float(timeout_text)
    except ValueError as exc:
        raise ConfigError(
            "PROM_QUERY_TIMEOUT must be a number",
            error_code="INVALID_TIMEOUT",
        ) from exc

    if timeout <= 0:
        raise ConfigError(
            "PROM_QUERY_TIMEOUT must be greater than zero",
            error_code="INVALID_TIMEOUT",
        )

    return Settings(
        prometheus_url=os.environ.get("PROM_QUERY_PROMETHEUS_URL"),
        token_url=os.environ.get("PROM_QUERY_TOKEN_URL"),
        client_id=os.environ.get("PROM_QUERY_CLIENT_ID"),
        client_secret=os.environ.get("PROM_QUERY_CLIENT_SECRET"),
        scope=os.environ.get("PROM_QUERY_SCOPE"),
        ca_bundle=os.environ.get("PROM_QUERY_CA_BUNDLE"),
        timeout=timeout,
        cache_path=cache_path(),
    )


def validate_url(value: str | None, field_name: str) -> str | None:
    if not value:
        return f"{field_name} is required"

    parsed = parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return f"{field_name} must be an absolute http or https URL"
    return None


def build_validation_report(settings: Settings) -> dict[str, Any]:
    errors: list[str] = []

    for field_name, value in (
        ("PROM_QUERY_PROMETHEUS_URL", settings.prometheus_url),
        ("PROM_QUERY_TOKEN_URL", settings.token_url),
    ):
        problem = validate_url(value, field_name)
        if problem:
            errors.append(problem)

    if not settings.client_id:
        errors.append("PROM_QUERY_CLIENT_ID is required")
    if not settings.client_secret:
        errors.append("PROM_QUERY_CLIENT_SECRET is required")
    if settings.ca_bundle and not Path(settings.ca_bundle).is_file():
        errors.append("PROM_QUERY_CA_BUNDLE must point to an existing file")

    return {
        "valid": not errors,
        "errors": errors,
        "resolved_config": {
            "prometheus_url": settings.prometheus_url,
            "token_url": settings.token_url,
            "client_id": settings.client_id,
            "client_secret_set": bool(settings.client_secret),
            "scope": settings.scope or None,
            "ca_bundle": settings.ca_bundle or None,
            "timeout": settings.timeout,
        },
        "required_env": {
            "PROM_QUERY_PROMETHEUS_URL": bool(settings.prometheus_url),
            "PROM_QUERY_TOKEN_URL": bool(settings.token_url),
            "PROM_QUERY_CLIENT_ID": bool(settings.client_id),
            "PROM_QUERY_CLIENT_SECRET": bool(settings.client_secret),
        },
        "optional_env": {
            "PROM_QUERY_SCOPE": settings.scope or None,
            "PROM_QUERY_CA_BUNDLE": settings.ca_bundle or None,
            "PROM_QUERY_TIMEOUT": settings.timeout,
        },
        "cache": {
            "path": str(settings.cache_path),
            "parent_exists": settings.cache_path.parent.exists(),
            "exists": settings.cache_path.exists(),
        },
    }


def ensure_valid_settings(settings: Settings) -> None:
    report = build_validation_report(settings)
    if report["valid"]:
        return
    raise ConfigError("; ".join(report["errors"]), error_code="INVALID_CONFIG")


def build_ssl_context(settings: Settings) -> ssl.SSLContext:
    if settings.ca_bundle:
        return ssl.create_default_context(cafile=settings.ca_bundle)
    return ssl.create_default_context()


def print_json(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def print_error(message: str, *, code: str) -> None:
    print_json({"error": message, "error_code": code})


def read_json_response(response: Any) -> dict[str, Any]:
    raw = response.read().decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HttpRequestError(
            "received a non-JSON response",
            error_code="INVALID_JSON_RESPONSE",
        ) from exc


def request_json(
    url: str,
    *,
    method: str,
    timeout: float,
    context: ssl.SSLContext,
    headers: dict[str, str] | None = None,
    form: dict[str, str] | None = None,
    error_code: str,
) -> dict[str, Any]:
    encoded_form = None
    request_headers = dict(headers or {})
    if form is not None:
        encoded_form = parse.urlencode(form).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

    req = request.Request(url, data=encoded_form, headers=request_headers, method=method)

    try:
        with request.urlopen(req, timeout=timeout, context=context) as response:
            return read_json_response(response)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        message = f"{method} {url} failed with HTTP {exc.code}"
        if body:
            message = f"{message}: {body}"
        raise HttpRequestError(message, error_code=error_code) from exc
    except error.URLError as exc:
        raise HttpRequestError(f"{method} {url} failed: {exc.reason}", error_code=error_code) from exc


def read_cached_token(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    expires_at = payload.get("expires_at")
    access_token = payload.get("access_token")
    if not isinstance(expires_at, (int, float)) or not isinstance(access_token, str):
        return None

    if expires_at - REFRESH_SKEW_SECONDS <= time.time():
        return None

    return payload


def write_cached_token(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.chmod(temp_path, 0o600)
    temp_path.replace(path)


def fetch_access_token(settings: Settings, context: ssl.SSLContext) -> dict[str, Any]:
    form = {
        "grant_type": "client_credentials",
        "client_id": settings.client_id or "",
        "client_secret": settings.client_secret or "",
    }
    if settings.scope:
        form["scope"] = settings.scope

    token_response = request_json(
        settings.token_url or "",
        method="POST",
        timeout=settings.timeout,
        context=context,
        form=form,
        error_code="TOKEN_REQUEST_FAILED",
    )

    access_token = token_response.get("access_token")
    token_type = token_response.get("token_type", "Bearer")
    expires_in = token_response.get("expires_in", 3600)
    scope = token_response.get("scope", settings.scope)

    if not isinstance(access_token, str) or not access_token:
        raise HttpRequestError(
            "token endpoint response did not include access_token",
            error_code="TOKEN_RESPONSE_INVALID",
        )

    try:
        expires_in_seconds = int(expires_in)
    except (TypeError, ValueError) as exc:
        raise HttpRequestError(
            "token endpoint response included an invalid expires_in",
            error_code="TOKEN_RESPONSE_INVALID",
        ) from exc

    payload = {
        "access_token": access_token,
        "token_type": token_type,
        "scope": scope,
        "expires_at": int(time.time()) + expires_in_seconds,
    }
    write_cached_token(settings.cache_path, payload)
    return payload


def get_access_token(
    settings: Settings,
    context: ssl.SSLContext,
    *,
    force_refresh: bool = False,
) -> tuple[str, dict[str, Any]]:
    if not force_refresh:
        cached = read_cached_token(settings.cache_path)
        if cached:
            return "cache", cached

    return "token_endpoint", fetch_access_token(settings, context)


def token_metadata(source: str, token_payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    expires_at = int(token_payload["expires_at"])
    return {
        "cache_path": str(settings.cache_path),
        "expires_at": expires_at,
        "expires_in_seconds": max(0, expires_at - int(time.time())),
        "scope": token_payload.get("scope"),
        "source": source,
        "token_type": token_payload.get("token_type", "Bearer"),
    }


def perform_query(settings: Settings, context: ssl.SSLContext, expression: str) -> dict[str, Any]:
    source, token_payload = get_access_token(settings, context)
    endpoint = f"{settings.prometheus_url.rstrip('/')}/api/v1/query"
    query_string = parse.urlencode({"query": expression})
    response = request_json(
        f"{endpoint}?{query_string}",
        method="GET",
        timeout=settings.timeout,
        context=context,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token_payload['access_token']}",
        },
        error_code="PROMETHEUS_REQUEST_FAILED",
    )
    return {
        "auth_source": source,
        "query": expression,
        "response": response,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    query_parser = subparsers.add_parser("query", help="Run an instant PromQL query")
    query_parser.add_argument("--expr", required=True, help="PromQL expression")

    alerts_parser = subparsers.add_parser("alerts", help="Query ALERTS by state")
    alerts_parser.add_argument(
        "--state",
        default="firing",
        choices=["firing", "pending", "inactive"],
        help="Alert state to query",
    )

    subparsers.add_parser("config", help="Print redacted configuration")

    token_parser = subparsers.add_parser("token", help="Inspect token cache metadata")
    token_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore any cached token and fetch a fresh one",
    )

    return parser


def run_command(args: argparse.Namespace, settings: Settings) -> dict[str, Any]:
    report = build_validation_report(settings)
    if args.command == "config":
        return report

    ensure_valid_settings(settings)
    context = build_ssl_context(settings)

    if args.command == "query":
        return perform_query(settings, context, args.expr)
    if args.command == "alerts":
        expression = f'ALERTS{{alertstate="{args.state}"}}'
        payload = perform_query(settings, context, expression)
        payload["state"] = args.state
        return payload
    if args.command == "token":
        source, token_payload = get_access_token(settings, context, force_refresh=args.refresh)
        return token_metadata(source, token_payload, settings)

    raise ScriptError(f"unknown command: {args.command}", error_code="INVALID_COMMAND")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        settings = load_settings()
        payload = run_command(args, settings)
    except ScriptError as exc:
        print_error(str(exc), code=getattr(exc, "error_code", "SCRIPT_ERROR"))
        return 1

    print_json(payload)
    if args.command == "config" and not payload["valid"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
