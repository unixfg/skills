#!/usr/bin/env python3
"""Shared read-only Plex video library helpers."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


DEFAULT_LIMIT = 5
MAX_LIMIT = 20
DEFAULT_TIMEOUT = 15.0
DEFAULT_CLIENT_IDENTIFIER = "librarian-bot-plex-media-library"
USER_AGENT = "plex-media-library/1.0.0"
VIDEO_TYPES = {"movie", "show", "season", "episode"}
GUID_RE = re.compile(r"^(?P<source>[A-Za-z0-9_.-]+)://(?P<id>[A-Za-z0-9_.:-]+)$")
IMDB_RE = re.compile(r"^tt\d+$")


class ScriptError(Exception):
    """Error that should be printed as a JSON payload."""

    def __init__(self, message: str, *, error_code: str, return_code: int = 2):
        super().__init__(message)
        self.error_code = error_code
        self.return_code = return_code


@dataclass(frozen=True)
class Settings:
    base_url: str | None
    token: str | None
    client_identifier: str
    timeout: float


def print_json(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def print_error(message: str, *, code: str) -> None:
    print_json({"error": message, "error_code": code})


def load_settings(timeout: float | None = None) -> Settings:
    try:
        timeout_value = timeout if timeout is not None else float(os.environ.get("PLEX_TIMEOUT", DEFAULT_TIMEOUT))
    except (TypeError, ValueError) as exc:
        raise ScriptError("PLEX_TIMEOUT must be numeric", error_code="INVALID_ARGUMENT") from exc
    validate_timeout(timeout_value)
    base_url = (os.environ.get("PLEX_BASE_URL") or os.environ.get("PLEX_URL") or "").strip()
    return Settings(
        base_url=base_url.rstrip("/") if base_url else None,
        token=(os.environ.get("PLEX_TOKEN") or "").strip() or None,
        client_identifier=(
            os.environ.get("PLEX_CLIENT_IDENTIFIER") or DEFAULT_CLIENT_IDENTIFIER
        ).strip(),
        timeout=timeout_value,
    )


def validate_settings(settings: Settings) -> list[str]:
    errors: list[str] = []
    if not settings.base_url:
        errors.append("PLEX_BASE_URL or PLEX_URL is required")
    if not settings.token:
        errors.append("PLEX_TOKEN is required")
    return errors


def build_validation_report(settings: Settings) -> dict[str, Any]:
    errors = validate_settings(settings)
    return {
        "valid": not errors,
        "errors": errors,
        "required_env": {
            "PLEX_TOKEN": bool(settings.token),
            "PLEX_BASE_URL_or_PLEX_URL": bool(settings.base_url),
        },
        "base_url": settings.base_url,
        "client_identifier_configured": bool(os.environ.get("PLEX_CLIENT_IDENTIFIER")),
        "timeout": settings.timeout,
    }


def require_settings(settings: Settings) -> None:
    errors = validate_settings(settings)
    if errors:
        raise ScriptError("; ".join(errors), error_code="CONFIG_ERROR")


def validate_limit(value: int, *, maximum: int = MAX_LIMIT) -> int:
    if value < 1:
        raise ScriptError("--limit must be greater than zero", error_code="INVALID_LIMIT")
    if value > maximum:
        raise ScriptError(f"--limit must be {maximum} or less", error_code="INVALID_LIMIT")
    return value


def validate_timeout(value: float) -> float:
    if value <= 0:
        raise ScriptError("--timeout must be greater than zero", error_code="INVALID_ARGUMENT")
    return value


def validate_rating_key(value: str) -> str:
    if not re.fullmatch(r"\d+", value):
        raise ScriptError("--rating-key must be numeric", error_code="INVALID_ARGUMENT")
    return value


def build_url(settings: Settings, path: str, params: dict[str, Any] | None = None) -> str:
    require_settings(settings)
    assert settings.base_url is not None
    url = f"{settings.base_url}{path}"
    if params:
        url = f"{url}?{parse.urlencode(params, doseq=True)}"
    return url


def fetch_json(settings: Settings, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    require_settings(settings)
    url = build_url(settings, path, params)
    req = request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "X-Plex-Token": settings.token or "",
            "X-Plex-Client-Identifier": settings.client_identifier,
            "X-Plex-Product": "Librarian Bot",
            "X-Plex-Version": "1.0.0",
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=settings.timeout) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        message = f"GET {url} failed with HTTP {exc.code}"
        if body:
            message = f"{message}: {body}"
        raise ScriptError(message, error_code="HTTP_ERROR", return_code=3) from exc
    except (error.URLError, TimeoutError, socket.timeout) as exc:
        reason = getattr(exc, "reason", exc)
        raise ScriptError(f"GET {url} failed: {reason}", error_code="NETWORK_ERROR", return_code=3) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScriptError(f"GET {url} returned invalid JSON", error_code="INVALID_JSON_RESPONSE", return_code=3) from exc
    if not isinstance(payload, dict):
        raise ScriptError(f"GET {url} returned a non-object JSON payload", error_code="INVALID_JSON_RESPONSE", return_code=3)
    return payload


def compact_text(value: Any, *, max_len: int = 1000) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text:
        return None
    return text[:max_len]


def compact_list(values: Any, *, max_items: int = 20) -> list[Any]:
    if values is None:
        return []
    items = values if isinstance(values, list) else [values]
    out: list[Any] = []
    seen: set[str] = set()
    for item in items:
        if item is None:
            continue
        if isinstance(item, str):
            item = compact_text(item)
        if item in ("", None):
            continue
        key = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= max_items:
            break
    return out


def list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in compact_list(value, max_items=200) if isinstance(item, dict)]


def first_year(*values: Any) -> int | None:
    for value in values:
        if value is None:
            continue
        match = re.search(r"\b(\d{4})\b", str(value))
        if match:
            return int(match.group(1))
    return None


def parse_external_ids(metadata: dict[str, Any]) -> tuple[dict[str, list[str]], dict[str, str]]:
    ids: dict[str, list[str]] = {}
    urls: dict[str, str] = {}
    guid_values = [metadata.get("guid")]
    guid_values.extend(item.get("id") for item in list_of_dicts(metadata.get("Guid")))

    for raw in compact_list(guid_values, max_items=50):
        match = GUID_RE.fullmatch(str(raw))
        if not match:
            continue
        source = match.group("source").lower()
        identifier = match.group("id")
        ids.setdefault(source, [])
        if identifier not in ids[source]:
            ids[source].append(identifier)
        if source == "imdb" and IMDB_RE.fullmatch(identifier):
            urls["imdb"] = f"https://www.imdb.com/title/{identifier}/"
        elif source == "tmdb" and identifier.isdigit():
            urls.setdefault("tmdb", f"https://www.themoviedb.org/movie/{identifier}")
        elif source == "tvdb" and identifier.isdigit():
            urls.setdefault("tvdb", f"https://thetvdb.com/dereferrer/series/{identifier}")
    return ids, urls


def media_locations(metadata: dict[str, Any]) -> list[str]:
    locations: list[str] = []
    for item in list_of_dicts(metadata.get("Location")):
        path = compact_text(item.get("path"))
        if path and path not in locations:
            locations.append(path)
    for media in list_of_dicts(metadata.get("Media")):
        for part in list_of_dicts(media.get("Part")):
            file_path = compact_text(part.get("file"))
            if file_path and file_path not in locations:
                locations.append(file_path)
    return locations[:20]


def tag_names(metadata: dict[str, Any], key: str) -> list[str]:
    names = []
    for item in list_of_dicts(metadata.get(key)):
        tag = compact_text(item.get("tag"))
        if tag and tag not in names:
            names.append(tag)
    return names[:20]


def normalize_media(metadata: dict[str, Any]) -> dict[str, Any]:
    external_ids, source_urls = parse_external_ids(metadata)
    media_type = compact_text(metadata.get("type"))
    result: dict[str, Any] = {
        "title": compact_text(metadata.get("title")),
        "type": media_type,
        "year": first_year(metadata.get("year"), metadata.get("originallyAvailableAt")),
        "rating_key": compact_text(metadata.get("ratingKey")),
        "key": compact_text(metadata.get("key")),
        "guid": compact_text(metadata.get("guid")),
        "library_section_id": metadata.get("librarySectionID"),
        "library_section_title": compact_text(metadata.get("librarySectionTitle")),
        "summary": compact_text(metadata.get("summary")),
        "tagline": compact_text(metadata.get("tagline")),
        "content_rating": compact_text(metadata.get("contentRating")),
        "rating": metadata.get("rating"),
        "audience_rating": metadata.get("audienceRating"),
        "originally_available_at": compact_text(metadata.get("originallyAvailableAt")),
        "duration_ms": metadata.get("duration"),
        "view_count": metadata.get("viewCount", 0),
        "last_viewed_at": metadata.get("lastViewedAt"),
        "watched": bool(metadata.get("viewCount") or metadata.get("lastViewedAt")),
        "child_count": metadata.get("childCount"),
        "season_count": metadata.get("seasonCount"),
        "leaf_count": metadata.get("leafCount"),
        "viewed_leaf_count": metadata.get("viewedLeafCount"),
        "genres": tag_names(metadata, "Genre"),
        "collections": tag_names(metadata, "Collection"),
        "locations": media_locations(metadata),
        "external_ids": external_ids,
        "source_urls": source_urls,
    }
    return {key: value for key, value in result.items() if value not in (None, "", [], {})}


def extract_metadata(payload: dict[str, Any]) -> list[dict[str, Any]]:
    container = payload.get("MediaContainer")
    if not isinstance(container, dict):
        return []
    metadata = []
    for item in list_of_dicts(container.get("Metadata")):
        metadata.append(item)
    for search_result in list_of_dicts(container.get("SearchResult")):
        item = search_result.get("Metadata")
        if isinstance(item, dict):
            metadata.append(item)
    return metadata


def search_media(query: str, media_type: str, limit: int, timeout: float | None = None) -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        raise ScriptError("--query is required", error_code="INVALID_ARGUMENT")
    limit = validate_limit(limit)
    settings = load_settings(timeout)
    search_types = "movies,tv"
    if media_type == "movie":
        search_types = "movies"
    elif media_type in ("tv", "show"):
        search_types = "tv"
    elif media_type != "all":
        raise ScriptError("--type must be one of all, movie, tv, show", error_code="INVALID_ARGUMENT")

    payload = fetch_json(
        settings,
        "/library/search",
        {
            "query": query,
            "limit": limit,
            "searchTypes": search_types,
            "includeCollections": 0,
            "includeExternalMedia": 0,
        },
    )
    results = []
    for item in extract_metadata(payload):
        normalized = normalize_media(item)
        if normalized.get("type") in VIDEO_TYPES:
            results.append(normalized)
        if len(results) >= limit:
            break
    return {
        "source": "Plex",
        "lookup_type": "media_search",
        "query": {"query": query, "type": media_type},
        "num_found": len(results),
        "results": results,
    }


def get_media(rating_key: str, include_children: bool, children_limit: int, timeout: float | None = None) -> dict[str, Any]:
    rating_key = validate_rating_key(rating_key)
    children_limit = validate_limit(children_limit, maximum=200)
    settings = load_settings(timeout)
    payload = fetch_json(settings, f"/library/metadata/{rating_key}")
    items = extract_metadata(payload)
    if not items:
        raise ScriptError(f"Plex metadata not found for rating key {rating_key}", error_code="NOT_FOUND", return_code=4)
    result = normalize_media(items[0])
    output: dict[str, Any] = {
        "source": "Plex",
        "lookup_type": "media_detail",
        "query": {"rating_key": rating_key, "include_children": include_children},
        "result": result,
    }
    if include_children:
        child_payload = fetch_json(
            settings,
            f"/library/metadata/{rating_key}/children",
            {"X-Plex-Container-Size": children_limit},
        )
        output["children"] = [normalize_media(item) for item in extract_metadata(child_payload)[:children_limit]]
    return output


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--timeout", type=float, default=None)


def run_main(func) -> int:
    try:
        print_json(func())
        return 0
    except ScriptError as exc:
        print_error(str(exc), code=exc.error_code)
        return exc.return_code
