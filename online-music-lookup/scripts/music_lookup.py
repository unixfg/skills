#!/usr/bin/env python3
"""Read-only online music lookup helpers."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import socket
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
MUSICBRAINZ_API = "https://musicbrainz.org/ws/2"
DEFAULT_LIMIT = 5
MAX_LIMIT = 10
DEFAULT_TIMEOUT = 15.0
DEFAULT_MB_DELAY = 1.0
USER_AGENT = "online-music-lookup/1.0.0 (https://github.com/unixfg/skills)"
TAG_RE = re.compile(r"<[^>]+>")
MBID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class ScriptError(Exception):
    """Error that should be printed as a JSON payload."""

    def __init__(self, message: str, *, error_code: str, return_code: int = 2):
        super().__init__(message)
        self.error_code = error_code
        self.return_code = return_code


@dataclass(frozen=True)
class Settings:
    musicbrainz_id: str | None
    musicbrainz_secret: str | None
    timeout: float
    musicbrainz_delay: float


def print_json(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def print_error(message: str, *, code: str) -> None:
    print_json({"error": message, "error_code": code})


def validate_timeout(value: float) -> float:
    if value <= 0:
        raise ScriptError("--timeout must be greater than zero", error_code="INVALID_ARGUMENT")
    return value


def validate_limit(value: int) -> int:
    if value < 1:
        raise ScriptError("--limit must be greater than zero", error_code="INVALID_LIMIT")
    if value > MAX_LIMIT:
        raise ScriptError(f"--limit must be {MAX_LIMIT} or less", error_code="INVALID_LIMIT")
    return value


def load_settings(timeout: float | None = None) -> Settings:
    timeout_value = timeout if timeout is not None else DEFAULT_TIMEOUT
    try:
        delay = float(os.environ.get("MUSICBRAINZ_DELAY_SECONDS", DEFAULT_MB_DELAY))
    except (TypeError, ValueError) as exc:
        raise ScriptError("MUSICBRAINZ_DELAY_SECONDS must be numeric", error_code="INVALID_ARGUMENT") from exc
    validate_timeout(timeout_value)
    if delay < 0:
        raise ScriptError("MUSICBRAINZ_DELAY_SECONDS must not be negative", error_code="INVALID_ARGUMENT")
    return Settings(
        musicbrainz_id=(os.environ.get("MUSICBRAINZ_ID") or "").strip() or None,
        musicbrainz_secret=(os.environ.get("MUSICBRAINZ_SECRET") or "").strip() or None,
        timeout=timeout_value,
        musicbrainz_delay=delay,
    )


def build_validation_report(settings: Settings) -> dict[str, Any]:
    return {
        "valid": True,
        "sources": {
            "wikipedia": {"available": True, "required": True},
            "musicbrainz": {
                "available": True,
                "required": True,
                "oauth_configured": bool(settings.musicbrainz_id and settings.musicbrainz_secret),
                "oauth_required_for_search": False,
                "user_agent": USER_AGENT,
                "delay_seconds": settings.musicbrainz_delay,
            },
        },
    }


def request_json(url: str, *, timeout: float, headers: dict[str, str] | None = None) -> dict[str, Any]:
    req = request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            **(headers or {}),
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
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


def strip_snippet(value: Any) -> str | None:
    text = compact_text(value)
    if not text:
        return None
    return html.unescape(TAG_RE.sub("", text))


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


def wikipedia_search(query: str, limit: int, timeout: float) -> list[dict[str, Any]]:
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': query,
        'srnamespace': 0,
        'srlimit': limit,
        'format': 'json',
    }
    url = f"{WIKIPEDIA_API}?{parse.urlencode(params)}"
    payload = request_json(url, timeout=timeout)
    results = []
    search_payload = payload.get("query", {}).get("search", []) if isinstance(payload.get("query"), dict) else []
    for item in list_of_dicts(search_payload):
        title = compact_text(item.get("title"))
        pageid = item.get("pageid")
        result = {
            "source": "Wikipedia",
            "title": title,
            "type": "wiki_page",
            "pageid": pageid,
            "summary": strip_snippet(item.get("snippet")),
            "source_urls": {
                "wikipedia": f"https://en.wikipedia.org/?curid={pageid}" if isinstance(pageid, int) else None
            },
        }
        results.append({key: value for key, value in result.items() if value not in (None, "", [], {})})
    return results


def artist_credit(value: Any) -> list[str]:
    names = []
    for item in list_of_dicts(value):
        name = compact_text(item.get("name"))
        if name and name not in names:
            names.append(name)
        artist = item.get("artist")
        if isinstance(artist, dict):
            artist_name = compact_text(artist.get("name"))
            if artist_name and artist_name not in names:
                names.append(artist_name)
    return names[:10]


def mb_source_url(entity: str, mbid: Any) -> str | None:
    if isinstance(mbid, str) and MBID_RE.fullmatch(mbid):
        return f"https://musicbrainz.org/{entity}/{mbid}"
    return None


def normalize_musicbrainz(entity: str, item: dict[str, Any]) -> dict[str, Any]:
    mbid = compact_text(item.get("id"))
    common: dict[str, Any] = {
        "source": "MusicBrainz",
        "type": entity,
        "mbid": mbid,
        "score": item.get("score"),
        "disambiguation": compact_text(item.get("disambiguation")),
        "source_urls": {"musicbrainz": mb_source_url(entity, mbid)},
    }
    if entity == "artist":
        common.update(
            {
                "name": compact_text(item.get("name")),
                "title": compact_text(item.get("name")),
                "sort_name": compact_text(item.get("sort-name")),
                "artist_type": compact_text(item.get("type")),
                "country": compact_text(item.get("country")),
                "life_span": item.get("life-span") if isinstance(item.get("life-span"), dict) else None,
                "tags": [tag.get("name") for tag in list_of_dicts(item.get("tags")) if tag.get("name")],
            }
        )
    elif entity == "release-group":
        common.update(
            {
                "title": compact_text(item.get("title")),
                "primary_type": compact_text(item.get("primary-type")),
                "secondary_types": compact_list(item.get("secondary-types"), max_items=10),
                "first_release_date": compact_text(item.get("first-release-date")),
                "artist_credit": artist_credit(item.get("artist-credit")),
            }
        )
    elif entity == "release":
        labels = []
        for label_info in list_of_dicts(item.get("label-info")):
            label = label_info.get("label")
            if isinstance(label, dict):
                name = compact_text(label.get("name"))
                if name and name not in labels:
                    labels.append(name)
        common.update(
            {
                "title": compact_text(item.get("title")),
                "date": compact_text(item.get("date")),
                "country": compact_text(item.get("country")),
                "status": compact_text(item.get("status")),
                "barcode": compact_text(item.get("barcode")),
                "artist_credit": artist_credit(item.get("artist-credit")),
                "labels": labels[:10],
            }
        )
    elif entity == "recording":
        common.update(
            {
                "title": compact_text(item.get("title")),
                "length_ms": item.get("length"),
                "artist_credit": artist_credit(item.get("artist-credit")),
                "first_release_date": compact_text(item.get("first-release-date")),
                "isrcs": compact_list(item.get("isrcs"), max_items=10),
            }
        )
    return {key: value for key, value in common.items() if value not in (None, "", [], {})}


def musicbrainz_search(settings: Settings, query: str, entity_type: str, limit: int) -> list[dict[str, Any]]:
    entity_types = ["artist", "release-group", "release", "recording"] if entity_type == "all" else [entity_type]
    results = []
    first = True
    for entity in entity_types:
        if not first and settings.musicbrainz_delay:
            time.sleep(settings.musicbrainz_delay)
        first = False
        url = f"{MUSICBRAINZ_API}/{entity}?{parse.urlencode({'query': query, 'fmt': 'json', 'limit': limit})}"
        payload = request_json(url, timeout=settings.timeout)
        key = f"{entity}s"
        if entity == "release-group":
            key = "release-groups"
        for item in list_of_dicts(payload.get(key)):
            results.append(normalize_musicbrainz(entity, item))
            if len(results) >= limit:
                return results
    return results[:limit]


def source_status(available: bool, used: bool, num_found: int = 0, skipped: str | None = None) -> dict[str, Any]:
    status: dict[str, Any] = {"available": available, "used": used, "num_found": num_found}
    if skipped:
        status["skipped"] = skipped
    return status


def lookup_music(
    query: str,
    entity_type: str,
    source: str,
    limit: int,
    timeout: float | None = None,
) -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        raise ScriptError("--query is required", error_code="INVALID_ARGUMENT")
    if entity_type not in ("all", "artist", "release", "release-group", "recording"):
        raise ScriptError("--type must be one of all, artist, release, release-group, recording", error_code="INVALID_ARGUMENT")
    if source not in ("all", "wikipedia", "musicbrainz"):
        raise ScriptError("--source must be one of all, wikipedia, musicbrainz", error_code="INVALID_ARGUMENT")
    limit = validate_limit(limit)
    settings = load_settings(timeout)

    results: list[dict[str, Any]] = []
    sources: dict[str, dict[str, Any]] = {}

    if source in ("all", "wikipedia"):
        wiki_results = wikipedia_search(query, limit, settings.timeout)
        results.extend(wiki_results)
        sources["wikipedia"] = source_status(True, True, len(wiki_results))
    else:
        sources["wikipedia"] = source_status(True, False)

    if source in ("all", "musicbrainz"):
        mb_results = musicbrainz_search(settings, query, entity_type, limit)
        results.extend(mb_results)
        sources["musicbrainz"] = source_status(True, True, len(mb_results))
        sources["musicbrainz"]["oauth_configured"] = bool(settings.musicbrainz_id and settings.musicbrainz_secret)
        sources["musicbrainz"]["oauth_required_for_search"] = False
    else:
        sources["musicbrainz"] = source_status(True, False)
        sources["musicbrainz"]["oauth_configured"] = bool(settings.musicbrainz_id and settings.musicbrainz_secret)
        sources["musicbrainz"]["oauth_required_for_search"] = False

    return {
        "source": "online-music-lookup",
        "lookup_type": "music_search",
        "query": {"query": query, "type": entity_type, "source": source},
        "sources": sources,
        "num_found": len(results),
        "results": results,
    }


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--timeout", type=float, default=None)


def run_main(func) -> int:
    try:
        print_json(func())
        return 0
    except ScriptError as exc:
        print_error(str(exc), code=exc.error_code)
        return exc.return_code
