#!/usr/bin/env python3
"""Read-only online movie and TV lookup helpers."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import socket
import sys
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
TMDB_API = "https://api.themoviedb.org/3"
TVDB_API = "https://api4.thetvdb.com/v4"
DEFAULT_LIMIT = 5
MAX_LIMIT = 10
DEFAULT_TIMEOUT = 15.0
USER_AGENT = "online-video-lookup/1.0.0 (https://github.com/unixfg/skills)"
IMDB_RE = re.compile(r"^tt\d+$")
TAG_RE = re.compile(r"<[^>]+>")


class ScriptError(Exception):
    """Error that should be printed as a JSON payload."""

    def __init__(self, message: str, *, error_code: str, return_code: int = 2):
        super().__init__(message)
        self.error_code = error_code
        self.return_code = return_code


@dataclass(frozen=True)
class Settings:
    tmdb_read_access_token: str | None
    tmdb_api_key: str | None
    tvdb_api_key: str | None
    tvdb_pin: str | None
    timeout: float


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


def validate_year(value: str | None) -> int | None:
    if not value:
        return None
    if not re.fullmatch(r"\d{4}", value):
        raise ScriptError("--year must be a four-digit year", error_code="INVALID_ARGUMENT")
    return int(value)


def load_settings(timeout: float | None = None) -> Settings:
    timeout_value = timeout if timeout is not None else DEFAULT_TIMEOUT
    validate_timeout(timeout_value)
    return Settings(
        tmdb_read_access_token=(os.environ.get("TMDB_READ_ACCESS_TOKEN") or "").strip() or None,
        tmdb_api_key=(os.environ.get("TMDB_API_KEY") or "").strip() or None,
        tvdb_api_key=(os.environ.get("TVDB_API_KEY") or "").strip() or None,
        tvdb_pin=(os.environ.get("TVDB_PIN") or "").strip() or None,
        timeout=timeout_value,
    )


def build_validation_report(settings: Settings) -> dict[str, Any]:
    return {
        "valid": True,
        "sources": {
            "wikipedia": {"available": True, "required": True},
            "tmdb": {
                "available": bool(settings.tmdb_read_access_token or settings.tmdb_api_key),
                "required": False,
                "auth": "bearer" if settings.tmdb_read_access_token else ("api_key" if settings.tmdb_api_key else None),
            },
            "tvdb": {
                "available": bool(settings.tvdb_api_key),
                "required": False,
                "pin_configured": bool(settings.tvdb_pin),
            },
            "imdb": {
                "available": False,
                "required": False,
                "mode": "link-only from official metadata; no scraping",
            },
        },
    }


def request_json(
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    method: str = "GET",
) -> dict[str, Any]:
    req = request.Request(
        url,
        data=data,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            **(headers or {}),
        },
        method=method,
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        message = f"{method} {url} failed with HTTP {exc.code}"
        if body:
            message = f"{message}: {body}"
        raise ScriptError(message, error_code="HTTP_ERROR", return_code=3) from exc
    except (error.URLError, TimeoutError, socket.timeout) as exc:
        reason = getattr(exc, "reason", exc)
        raise ScriptError(f"{method} {url} failed: {reason}", error_code="NETWORK_ERROR", return_code=3) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScriptError(f"{method} {url} returned invalid JSON", error_code="INVALID_JSON_RESPONSE", return_code=3) from exc
    if not isinstance(payload, dict):
        raise ScriptError(f"{method} {url} returned a non-object JSON payload", error_code="INVALID_JSON_RESPONSE", return_code=3)
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


def first_year(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"\b(\d{4})\b", str(value))
    return int(match.group(1)) if match else None


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


def tmdb_headers(settings: Settings) -> dict[str, str]:
    if settings.tmdb_read_access_token:
        return {"Authorization": f"Bearer {settings.tmdb_read_access_token}"}
    return {}


def tmdb_url(path: str, settings: Settings, params: dict[str, Any]) -> str:
    query = dict(params)
    if not settings.tmdb_read_access_token and settings.tmdb_api_key:
        query["api_key"] = settings.tmdb_api_key
    return f"{TMDB_API}{path}?{parse.urlencode(query, doseq=True)}"


def tmdb_available(settings: Settings) -> bool:
    return bool(settings.tmdb_read_access_token or settings.tmdb_api_key)


def tmdb_source_url(media_type: str, tmdb_id: Any) -> str | None:
    if not isinstance(tmdb_id, int):
        return None
    return f"https://www.themoviedb.org/{'movie' if media_type == 'movie' else 'tv'}/{tmdb_id}"


def imdb_url(imdb_id: str | None) -> str | None:
    if imdb_id and IMDB_RE.fullmatch(imdb_id):
        return f"https://www.imdb.com/title/{imdb_id}/"
    return None


def normalize_trailers(videos_payload: Any) -> list[dict[str, Any]]:
    videos = videos_payload.get("results") if isinstance(videos_payload, dict) else videos_payload
    out = []
    for video in list_of_dicts(videos):
        site = compact_text(video.get("site"))
        key = compact_text(video.get("key"))
        video_type = compact_text(video.get("type"))
        if site != "YouTube" or not key:
            continue
        if video_type not in ("Trailer", "Teaser"):
            continue
        item = {
            "name": compact_text(video.get("name")),
            "site": site,
            "type": video_type,
            "official": bool(video.get("official")),
            "published_at": compact_text(video.get("published_at")),
            "url": f"https://www.youtube.com/watch?v={parse.quote(key)}",
        }
        out.append({k: v for k, v in item.items() if v not in (None, "", [], {})})
    return out[:5]


def tmdb_details(settings: Settings, media_type: str, tmdb_id: int, include_trailers: bool) -> dict[str, Any]:
    append = ["external_ids"]
    if include_trailers:
        append.append("videos")
    url = tmdb_url(
        f"/{media_type}/{tmdb_id}",
        settings,
        {"language": "en-US", "append_to_response": ",".join(append)},
    )
    return request_json(url, timeout=settings.timeout, headers=tmdb_headers(settings))


def normalize_tmdb(item: dict[str, Any], media_type: str, details: dict[str, Any] | None, include_trailers: bool) -> dict[str, Any]:
    title = compact_text(item.get("title") or item.get("name"))
    date = compact_text(item.get("release_date") or item.get("first_air_date"))
    external_ids = details.get("external_ids", {}) if isinstance(details, dict) else {}
    imdb_id = compact_text((details or {}).get("imdb_id") or external_ids.get("imdb_id"))
    source_urls = {"tmdb": tmdb_source_url(media_type, item.get("id"))}
    imdb_link = imdb_url(imdb_id)
    if imdb_link:
        source_urls["imdb"] = imdb_link
    tvdb_id = external_ids.get("tvdb_id") if isinstance(external_ids, dict) else None
    if isinstance(tvdb_id, int):
        source_urls["tvdb"] = f"https://thetvdb.com/dereferrer/series/{tvdb_id}"
    result: dict[str, Any] = {
        "source": "TMDB",
        "title": title,
        "original_title": compact_text(item.get("original_title") or item.get("original_name")),
        "type": media_type,
        "tmdb_id": item.get("id"),
        "year": first_year(date),
        "release_date": date,
        "summary": compact_text(item.get("overview")),
        "vote_average": item.get("vote_average"),
        "popularity": item.get("popularity"),
        "external_ids": {
            "imdb": [imdb_id] if imdb_id else [],
            "tvdb": [str(tvdb_id)] if tvdb_id else [],
        },
        "source_urls": source_urls,
    }
    if include_trailers and details:
        result["trailers"] = normalize_trailers(details.get("videos"))
    return {key: value for key, value in result.items() if value not in (None, "", [], {})}


def tmdb_search(settings: Settings, query: str, media_type: str, year: int | None, limit: int, include_trailers: bool) -> list[dict[str, Any]]:
    if not tmdb_available(settings):
        return []
    media_types = ["movie", "tv"] if media_type == "all" else [media_type]
    results = []
    for current_type in media_types:
        params: dict[str, Any] = {
            "query": query,
            "include_adult": "false",
            "language": "en-US",
            "page": 1,
        }
        if year and current_type == "movie":
            params["year"] = year
            params["primary_release_year"] = year
        elif year and current_type == "tv":
            params["year"] = year
            params["first_air_date_year"] = year
        payload = request_json(
            tmdb_url(f"/search/{current_type}", settings, params),
            timeout=settings.timeout,
            headers=tmdb_headers(settings),
        )
        for item in list_of_dicts(payload.get("results")):
            tmdb_id = item.get("id")
            details = None
            if isinstance(tmdb_id, int):
                details = tmdb_details(settings, current_type, tmdb_id, include_trailers)
            results.append(normalize_tmdb(item, current_type, details, include_trailers))
            if len(results) >= limit:
                return results
    return results[:limit]


def tvdb_available(settings: Settings) -> bool:
    return bool(settings.tvdb_api_key)


def tvdb_login(settings: Settings) -> str:
    body: dict[str, Any] = {"apikey": settings.tvdb_api_key}
    if settings.tvdb_pin:
        body["pin"] = settings.tvdb_pin
    payload = request_json(
        f"{TVDB_API}/login",
        timeout=settings.timeout,
        headers={"Content-Type": "application/json"},
        data=json.dumps(body).encode("utf-8"),
        method="POST",
    )
    token = payload.get("data", {}).get("token") if isinstance(payload.get("data"), dict) else payload.get("token")
    if not isinstance(token, str) or not token:
        raise ScriptError("TVDB login response did not include a token", error_code="INVALID_JSON_RESPONSE", return_code=3)
    return token


def normalize_tvdb(item: dict[str, Any]) -> dict[str, Any]:
    entity_type = compact_text(item.get("type"))
    tvdb_id = item.get("tvdb_id") or item.get("id")
    source_urls = {}
    if isinstance(tvdb_id, int):
        if entity_type == "movie":
            source_urls["tvdb"] = f"https://thetvdb.com/dereferrer/movie/{tvdb_id}"
        else:
            source_urls["tvdb"] = f"https://thetvdb.com/dereferrer/series/{tvdb_id}"
    imdb_id = compact_text(item.get("imdb_id"))
    remote_ids = item.get("remote_ids")
    if not imdb_id and isinstance(remote_ids, dict):
        imdb_id = compact_text(remote_ids.get("imdb"))
    imdb_link = imdb_url(imdb_id)
    if imdb_link:
        source_urls["imdb"] = imdb_link
    external_ids = {}
    if imdb_id:
        external_ids["imdb"] = [imdb_id]
    result = {
        "source": "TVDB",
        "title": compact_text(item.get("name") or item.get("title")),
        "type": "movie" if entity_type == "movie" else "tv",
        "tvdb_id": tvdb_id,
        "year": first_year(item.get("year") or item.get("first_air_time")),
        "summary": compact_text(item.get("overview")),
        "status": compact_text(item.get("status")),
        "network": compact_text(item.get("network")),
        "country": compact_text(item.get("country")),
        "image_url": compact_text(item.get("image_url")),
        "external_ids": external_ids,
        "source_urls": source_urls,
    }
    return {key: value for key, value in result.items() if value not in (None, "", [], {})}


def tvdb_search(settings: Settings, query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    if not tvdb_available(settings):
        return []
    token = tvdb_login(settings)
    types = ["movie", "series"] if media_type == "all" else (["movie"] if media_type == "movie" else ["series"])
    results = []
    for tvdb_type in types:
        url = f"{TVDB_API}/search?{parse.urlencode({'query': query, 'type': tvdb_type})}"
        payload = request_json(
            url,
            timeout=settings.timeout,
            headers={"Authorization": f"Bearer {token}"},
        )
        data = payload.get("data")
        for item in list_of_dicts(data):
            results.append(normalize_tvdb(item))
            if len(results) >= limit:
                return results
    return results[:limit]


def source_status(available: bool, used: bool, num_found: int = 0, skipped: str | None = None) -> dict[str, Any]:
    status: dict[str, Any] = {"available": available, "used": used, "num_found": num_found}
    if skipped:
        status["skipped"] = skipped
    return status


def lookup_video(
    query: str,
    media_type: str,
    source: str,
    year_text: str | None,
    include_trailers: bool,
    limit: int,
    timeout: float | None = None,
) -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        raise ScriptError("--query is required", error_code="INVALID_ARGUMENT")
    if media_type not in ("all", "movie", "tv"):
        raise ScriptError("--type must be one of all, movie, tv", error_code="INVALID_ARGUMENT")
    if source not in ("all", "wikipedia", "tmdb", "tvdb"):
        raise ScriptError("--source must be one of all, wikipedia, tmdb, tvdb", error_code="INVALID_ARGUMENT")
    limit = validate_limit(limit)
    year = validate_year(year_text)
    settings = load_settings(timeout)

    results: list[dict[str, Any]] = []
    sources: dict[str, dict[str, Any]] = {}

    use_wikipedia = source in ("all", "wikipedia")
    if use_wikipedia:
        wiki_results = wikipedia_search(query, limit, settings.timeout)
        results.extend(wiki_results)
        sources["wikipedia"] = source_status(True, True, len(wiki_results))
    else:
        sources["wikipedia"] = source_status(True, False)

    use_tmdb = source in ("all", "tmdb")
    if use_tmdb and tmdb_available(settings):
        tmdb_results = tmdb_search(settings, query, media_type, year, limit, include_trailers)
        results.extend(tmdb_results)
        sources["tmdb"] = source_status(True, True, len(tmdb_results))
    elif use_tmdb and source == "tmdb":
        raise ScriptError("TMDB_READ_ACCESS_TOKEN or TMDB_API_KEY is required for --source tmdb", error_code="CONFIG_ERROR")
    else:
        skipped = None if not use_tmdb else "TMDB_READ_ACCESS_TOKEN or TMDB_API_KEY is not configured"
        sources["tmdb"] = source_status(tmdb_available(settings), False, skipped=skipped)

    use_tvdb = source in ("all", "tvdb")
    if use_tvdb and tvdb_available(settings):
        tvdb_results = tvdb_search(settings, query, media_type, limit)
        results.extend(tvdb_results)
        sources["tvdb"] = source_status(True, True, len(tvdb_results))
    elif use_tvdb and source == "tvdb":
        raise ScriptError("TVDB_API_KEY is required for --source tvdb", error_code="CONFIG_ERROR")
    else:
        skipped = None if not use_tvdb else "TVDB_API_KEY is not configured"
        sources["tvdb"] = source_status(tvdb_available(settings), False, skipped=skipped)

    sources["imdb"] = {
        "available": False,
        "used": False,
        "mode": "link-only from official metadata; no scraping",
    }

    return {
        "source": "online-video-lookup",
        "lookup_type": "video_search",
        "query": {
            "query": query,
            "type": media_type,
            "source": source,
            "year": year,
            "include_trailers": include_trailers,
        },
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
