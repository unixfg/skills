# Script Reference

Use this file when you need exact CLI syntax, output shape, or script-specific
failure handling.

## Shared contract

- Wikipedia source: `https://en.wikipedia.org/w/api.php`.
- Optional TMDB source: `TMDB_READ_ACCESS_TOKEN` preferred, or `TMDB_API_KEY`.
- Optional TVDB source: `TVDB_API_KEY`, with optional `TVDB_PIN`.
- IMDb behavior: link IDs only from official metadata; no scraping.
- Output: machine-readable JSON on stdout.
- Errors include `error` and `error_code` and return non-zero.
- Default limit is `5`; maximum limit is `10`.
- Default timeout is `15` seconds.

## `check_config.py`

```bash
python3 scripts/check_config.py
```

Returns source readiness:

```json
{
  "valid": true,
  "sources": {
    "wikipedia": {"available": true},
    "tmdb": {"available": false},
    "tvdb": {"available": false}
  }
}
```

## `lookup_video.py`

```bash
python3 scripts/lookup_video.py --query "Severance" --type tv --include-trailers
```

Arguments:

- `--query` search text, required.
- `--type all|movie|tv`, default `all`.
- `--source all|wikipedia|tmdb|tvdb`, default `all`.
- `--year` optional year hint.
- `--include-trailers` fetches TMDB video metadata for TMDB results.
- `--limit`, default `5`, max `10`.
- `--timeout`, default `15`.

Success payload:

```json
{
  "source": "online-video-lookup",
  "lookup_type": "video_search",
  "query": {"query": "Severance", "type": "tv"},
  "sources": {
    "wikipedia": {"available": true, "used": true, "num_found": 1},
    "tmdb": {"available": true, "used": true, "num_found": 1},
    "tvdb": {"available": false, "used": false, "skipped": "TVDB_API_KEY is not configured"}
  },
  "num_found": 2,
  "results": []
}
```

## Error codes

- `INVALID_ARGUMENT`: invalid query, source, type, timeout, or year.
- `INVALID_LIMIT`: limit outside supported range.
- `CONFIG_ERROR`: an explicitly requested optional source is not configured.
- `HTTP_ERROR`: a source returned a non-success HTTP status.
- `NETWORK_ERROR`: a source could not be reached.
- `INVALID_JSON_RESPONSE`: a source did not return JSON.
