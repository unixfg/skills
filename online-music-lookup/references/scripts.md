# Script Reference

Use this file when you need exact CLI syntax, output shape, or script-specific
failure handling.

## Shared contract

- Wikipedia source: `https://en.wikipedia.org/w/api.php`.
- MusicBrainz source: `https://musicbrainz.org/ws/2/`.
- Optional OAuth readiness env: `MUSICBRAINZ_ID`, `MUSICBRAINZ_SECRET`.
- Output: machine-readable JSON on stdout.
- Errors include `error` and `error_code` and return non-zero.
- Default limit is `5`; maximum limit is `10`.
- Default timeout is `15` seconds.
- MusicBrainz requests use a meaningful User-Agent and are spaced to respect
  the one-request-per-second public API guidance.

## `check_config.py`

```bash
python3 scripts/check_config.py
```

Returns source readiness and OAuth presence without making network requests:

```json
{
  "valid": true,
  "sources": {
    "wikipedia": {"available": true},
    "musicbrainz": {"available": true, "oauth_configured": true, "oauth_required_for_search": false}
  }
}
```

## `lookup_music.py`

```bash
python3 scripts/lookup_music.py --query "Blue Lines Massive Attack" --type release-group
```

Arguments:

- `--query` search text, required.
- `--type all|artist|release|release-group|recording`, default `all`.
- `--source all|wikipedia|musicbrainz`, default `all`.
- `--limit`, default `5`, max `10`.
- `--timeout`, default `15`.

Success payload:

```json
{
  "source": "online-music-lookup",
  "lookup_type": "music_search",
  "query": {"query": "Blue Lines Massive Attack", "type": "release-group"},
  "sources": {
    "wikipedia": {"available": true, "used": true, "num_found": 1},
    "musicbrainz": {"available": true, "used": true, "num_found": 1}
  },
  "num_found": 2,
  "results": []
}
```

## Error codes

- `INVALID_ARGUMENT`: invalid query, source, type, or timeout.
- `INVALID_LIMIT`: limit outside supported range.
- `HTTP_ERROR`: a source returned a non-success HTTP status.
- `NETWORK_ERROR`: a source could not be reached.
- `INVALID_JSON_RESPONSE`: a source did not return JSON.
