#!/usr/bin/env python3
"""Read-only Open Library book lookup helper."""

from __future__ import annotations

import argparse
import json
import re
import socket
import sys
from typing import Any
from urllib import error, parse, request


BASE_URL = "https://openlibrary.org"
DEFAULT_LIMIT = 5
MAX_LIMIT = 20
DEFAULT_TIMEOUT = 15.0
USER_AGENT = "online-book-lookup/1.0.1 (low-volume human-triggered lookup)"
KEY_PATTERNS = {
    "author": re.compile(r"^/authors/OL\d+A$"),
    "edition": re.compile(r"^/books/OL\d+M$"),
    "work": re.compile(r"^/works/OL\d+W$"),
}
SEARCH_FIELDS = ",".join(
    [
        "key",
        "title",
        "author_name",
        "first_publish_year",
        "publish_date",
        "publisher",
        "isbn",
        "cover_i",
        "edition_key",
        "subject",
    ]
)


class ScriptError(Exception):
    """Error that should be printed as a JSON payload."""

    def __init__(self, message: str, *, error_code: str, return_code: int = 2):
        super().__init__(message)
        self.error_code = error_code
        self.return_code = return_code


class HttpStatusError(ScriptError):
    """HTTP response with a non-success status."""

    def __init__(self, url: str, status: int, body: str):
        message = f"GET {url} failed with HTTP {status}"
        if body:
            message = f"{message}: {body}"
        super().__init__(message, error_code="HTTP_ERROR", return_code=3)
        self.status = status
        self.url = url
        self.body = body


def print_json(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def print_error(message: str, *, code: str) -> None:
    print_json({"error": message, "error_code": code})


def validate_limit(value: int) -> int:
    if value < 1:
        raise ScriptError("--limit must be greater than zero", error_code="INVALID_LIMIT")
    if value > MAX_LIMIT:
        raise ScriptError(
            f"--limit must be {MAX_LIMIT} or less",
            error_code="INVALID_LIMIT",
        )
    return value


def validate_timeout(value: float) -> float:
    if value <= 0:
        raise ScriptError("--timeout must be greater than zero", error_code="INVALID_TIMEOUT")
    return value


def normalize_isbn(value: str) -> str:
    normalized = re.sub(r"[\s-]+", "", value).upper()
    if not re.fullmatch(r"(?:\d{9}[\dX]|\d{13})", normalized):
        raise ScriptError(
            "--isbn must be a valid-looking ISBN-10 or ISBN-13",
            error_code="INVALID_ISBN",
        )
    return normalized


def build_url(path: str, params: dict[str, Any] | None = None) -> str:
    url = f"{BASE_URL}{path}"
    if params:
        query = parse.urlencode(params, doseq=True)
        url = f"{url}?{query}"
    return url


def fetch_json(url: str, timeout: float) -> dict[str, Any]:
    req = request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        raise HttpStatusError(url, exc.code, body) from exc
    except (error.URLError, TimeoutError, socket.timeout) as exc:
        reason = getattr(exc, "reason", exc)
        raise ScriptError(
            f"GET {url} failed: {reason}",
            error_code="NETWORK_ERROR",
            return_code=3,
        ) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScriptError(
            f"GET {url} returned invalid JSON",
            error_code="INVALID_JSON_RESPONSE",
            return_code=3,
        ) from exc

    if not isinstance(payload, dict):
        raise ScriptError(
            f"GET {url} returned a non-object JSON payload",
            error_code="INVALID_JSON_RESPONSE",
            return_code=3,
        )
    return payload


def compact_list(value: Any, *, max_items: int = 10) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = [value]

    out = []
    seen = set()
    for item in items:
        if item is None:
            continue
        normalized = item.strip() if isinstance(item, str) else item
        if normalized == "":
            continue
        key = json.dumps(normalized, sort_keys=True) if isinstance(normalized, (dict, list)) else normalized
        if key in seen:
            continue
        seen.add(key)
        out.append(normalized)
        if len(out) >= max_items:
            break
    return out


def split_isbns(values: Any) -> tuple[list[str], list[str]]:
    isbn_10: list[str] = []
    isbn_13: list[str] = []
    for value in compact_list(values, max_items=100):
        text = normalize_identifier_text(str(value))
        if len(text) == 10 and text not in isbn_10:
            isbn_10.append(text)
        elif len(text) == 13 and text not in isbn_13:
            isbn_13.append(text)
    return isbn_10[:10], isbn_13[:10]


def normalize_identifier_text(value: str) -> str:
    return re.sub(r"[\s-]+", "", value).upper()


def first_item(value: Any) -> Any:
    items = compact_list(value, max_items=1)
    return items[0] if items else None


def first_year(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"\b(\d{4})\b", str(value))
    if not match:
        return None
    return int(match.group(1))


def safe_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text:
        return None
    return text[:500]


def safe_text_list(value: Any, *, max_items: int = 10) -> list[str]:
    return compact_list([safe_text(item) for item in compact_list(value, max_items=max_items)], max_items=max_items)


def openlibrary_key(key: str | None, kind: str) -> str | None:
    if not isinstance(key, str):
        return None
    if KEY_PATTERNS[kind].fullmatch(key):
        return key
    return None


def ensure_key_prefix(key: str | None, prefix: str, kind: str) -> str | None:
    if not key:
        return None
    prefixed = key if key.startswith(prefix) else f"{prefix}{key}"
    return openlibrary_key(prefixed, kind)


def page_url(key: str | None) -> str | None:
    if not key:
        return None
    return f"{BASE_URL}{key}"


def api_url(key: str | None) -> str | None:
    if not key:
        return None
    return f"{BASE_URL}{key}.json"


def cover_urls_from_id(cover_id: Any) -> dict[str, str]:
    if isinstance(cover_id, int):
        safe_cover_id = str(cover_id)
    elif isinstance(cover_id, str) and re.fullmatch(r"\d+", cover_id):
        safe_cover_id = cover_id
    else:
        return {}
    return {
        "small": f"https://covers.openlibrary.org/b/id/{safe_cover_id}-S.jpg",
        "medium": f"https://covers.openlibrary.org/b/id/{safe_cover_id}-M.jpg",
        "large": f"https://covers.openlibrary.org/b/id/{safe_cover_id}-L.jpg",
    }


def cover_urls_from_isbn(isbn: str | None) -> dict[str, str]:
    if not isbn:
        return {}
    return {
        "small": f"https://covers.openlibrary.org/b/isbn/{isbn}-S.jpg",
        "medium": f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg",
        "large": f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg",
    }


def source_urls(work_key: str | None = None, edition_key: str | None = None, isbn: str | None = None) -> dict[str, str]:
    urls: dict[str, str] = {}
    work_key = openlibrary_key(work_key, "work")
    edition_key = openlibrary_key(edition_key, "edition")
    if work_key:
        urls["work"] = page_url(work_key) or ""
        urls["work_api"] = api_url(work_key) or ""
    if edition_key:
        urls["edition"] = page_url(edition_key) or ""
        urls["edition_api"] = api_url(edition_key) or ""
    if isbn:
        urls["isbn_api"] = build_url(f"/isbn/{parse.quote(isbn)}.json")
    return urls


def normalize_search_doc(doc: dict[str, Any]) -> dict[str, Any]:
    work_key = openlibrary_key(doc.get("key"), "work")
    edition_key = ensure_key_prefix(first_item(doc.get("edition_key")), "/books/", "edition")
    isbn_10, isbn_13 = split_isbns(doc.get("isbn"))
    cover = cover_urls_from_id(doc.get("cover_i"))

    return {
        "title": safe_text(doc.get("title")),
        "authors": safe_text_list(doc.get("author_name")),
        "first_publish_year": doc.get("first_publish_year"),
        "publish_date": safe_text(first_item(doc.get("publish_date"))),
        "publishers": safe_text_list(doc.get("publisher")),
        "isbn_10": isbn_10,
        "isbn_13": isbn_13,
        "subjects": safe_text_list(doc.get("subject")),
        "openlibrary_work_key": work_key,
        "openlibrary_edition_key": edition_key,
        "cover_urls": cover,
        "source_urls": source_urls(work_key=work_key, edition_key=edition_key),
    }


def extract_ref_key(ref: Any, kind: str) -> str | None:
    if isinstance(ref, dict):
        key = ref.get("key")
        return openlibrary_key(key, kind)
    if isinstance(ref, str):
        return openlibrary_key(ref, kind)
    return None


def search_doc_for_isbn(isbn: str, timeout: float) -> dict[str, Any] | None:
    payload = fetch_json(
        build_url(
            "/search.json",
            {
                "isbn": isbn,
                "fields": SEARCH_FIELDS,
                "limit": 1,
            },
        ),
        timeout,
    )
    docs = payload.get("docs", [])
    if not isinstance(docs, list) or not docs or not isinstance(docs[0], dict):
        return None
    return docs[0]


def author_names_from_edition(edition: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for author in compact_list(edition.get("authors"), max_items=10):
        if not isinstance(author, dict):
            continue
        name = safe_text(author.get("name")) or safe_text(author.get("personal_name"))
        if name and name not in names:
            names.append(name)
    return names


def normalize_isbn_edition(isbn: str, edition: dict[str, Any], search_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    search_result = normalize_search_doc(search_doc) if search_doc else {}
    edition_key = openlibrary_key(edition.get("key"), "edition")
    work_key = extract_ref_key(first_item(edition.get("works")), "work")
    if not work_key:
        work_key = search_result.get("openlibrary_work_key")

    authors = search_result.get("authors") or author_names_from_edition(edition)

    isbn_values = compact_list(edition.get("isbn_10"), max_items=100)
    isbn_values.extend(compact_list(edition.get("isbn_13"), max_items=100))
    if not isbn_values:
        isbn_values = [isbn]
    isbn_10, isbn_13 = split_isbns(isbn_values)
    if isbn not in isbn_10 and isbn not in isbn_13:
        if len(isbn) == 10:
            isbn_10.insert(0, isbn)
        elif len(isbn) == 13:
            isbn_13.insert(0, isbn)

    edition_covers = compact_list(edition.get("covers"), max_items=1)
    cover_urls = (
        cover_urls_from_id(first_item(edition_covers))
        or search_result.get("cover_urls")
        or cover_urls_from_isbn(isbn)
    )

    publish_date = safe_text(edition.get("publish_date")) or search_result.get("publish_date")
    first_publish_year = search_result.get("first_publish_year") or first_year(publish_date)
    subjects = safe_text_list(edition.get("subjects"), max_items=10)
    subjects = compact_list(subjects + compact_list(search_result.get("subjects"), max_items=10), max_items=10)

    final_edition_key = edition_key or search_result.get("openlibrary_edition_key")

    return {
        "title": safe_text(edition.get("title")) or search_result.get("title"),
        "authors": authors,
        "first_publish_year": first_publish_year,
        "publish_date": publish_date,
        "publishers": safe_text_list(edition.get("publishers")) or search_result.get("publishers", []),
        "isbn_10": isbn_10[:10],
        "isbn_13": isbn_13[:10],
        "subjects": subjects,
        "openlibrary_work_key": work_key,
        "openlibrary_edition_key": final_edition_key,
        "cover_urls": cover_urls,
        "source_urls": source_urls(work_key=work_key, edition_key=final_edition_key, isbn=isbn),
    }


def lookup_isbn(isbn_value: str, timeout: float) -> dict[str, Any]:
    isbn = normalize_isbn(isbn_value)
    url = build_url(f"/isbn/{parse.quote(isbn)}.json")
    try:
        edition = fetch_json(url, timeout)
    except HttpStatusError as exc:
        if exc.status == 404:
            return {
                "source": "Open Library",
                "lookup_type": "isbn",
                "query": {"isbn": isbn},
                "num_found": 0,
                "results": [],
            }
        raise

    search_doc = search_doc_for_isbn(isbn, timeout)

    return {
        "source": "Open Library",
        "lookup_type": "isbn",
        "query": {"isbn": isbn},
        "num_found": 1,
        "results": [normalize_isbn_edition(isbn, edition, search_doc)],
    }


def lookup_search(
    *,
    query: str | None,
    title: str | None,
    author: str | None,
    limit: int,
    timeout: float,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "fields": SEARCH_FIELDS,
        "limit": limit,
    }
    query_payload: dict[str, str] = {}
    if query:
        params["q"] = query
        query_payload["query"] = query
    if title:
        params["title"] = title
        query_payload["title"] = title
    if author:
        params["author"] = author
        query_payload["author"] = author

    payload = fetch_json(build_url("/search.json", params), timeout)
    docs = payload.get("docs", [])
    if not isinstance(docs, list):
        raise ScriptError(
            "Open Library search response did not include a docs array",
            error_code="INVALID_JSON_RESPONSE",
            return_code=3,
        )

    return {
        "source": "Open Library",
        "lookup_type": "search",
        "query": query_payload,
        "num_found": int(payload.get("numFound") or 0),
        "results": [normalize_search_doc(doc) for doc in docs[:limit] if isinstance(doc, dict)],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Look up book metadata from Open Library")
    parser.add_argument("--query", help="Broad Open Library search query")
    parser.add_argument("--title", help="Title for structured title/author search")
    parser.add_argument("--author", help="Author for structured title/author search")
    parser.add_argument("--isbn", help="ISBN-10 or ISBN-13 for exact edition lookup")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"Maximum search results, 1-{MAX_LIMIT}")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="HTTP timeout in seconds")
    return parser.parse_args(argv)


def validate_lookup_args(args: argparse.Namespace) -> None:
    validate_limit(args.limit)
    validate_timeout(args.timeout)

    has_search = bool(args.query or args.title or args.author)
    if args.isbn and has_search:
        raise ScriptError(
            "Use --isbn alone, or use --query/--title/--author for search",
            error_code="INVALID_ARGUMENTS",
        )
    if args.query and (args.title or args.author):
        raise ScriptError(
            "Use --query alone, or use --title/--author for structured search",
            error_code="INVALID_ARGUMENTS",
        )
    if not args.isbn and not has_search:
        raise ScriptError(
            "Provide --isbn, --query, --title, or --author",
            error_code="INVALID_ARGUMENTS",
        )


def run(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        validate_lookup_args(args)
        if args.isbn:
            payload = lookup_isbn(args.isbn, args.timeout)
        else:
            payload = lookup_search(
                query=args.query,
                title=args.title,
                author=args.author,
                limit=args.limit,
                timeout=args.timeout,
            )
        print_json(payload)
        return 0
    except ScriptError as exc:
        print_error(str(exc), code=exc.error_code)
        return exc.return_code


if __name__ == "__main__":
    sys.exit(run())
