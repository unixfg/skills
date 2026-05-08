# Script Reference

Use this file when you need exact CLI syntax, output shape, or script-specific
failure handling.

## Shared contract

- Data source: configured Plex server only.
- Required env: `PLEX_TOKEN`.
- Base URL env: `PLEX_BASE_URL` preferred, then `PLEX_URL`.
- Optional env: `PLEX_CLIENT_IDENTIFIER`, `PLEX_TIMEOUT`.
- Output: machine-readable JSON on stdout.
- Errors include `error` and `error_code` and return non-zero.
- Default limit is `5`; maximum limit is `20`.
- Default timeout is `15` seconds.
- Requests send `Accept: application/json`, `X-Plex-Token`, and a stable
  `X-Plex-Client-Identifier`.

## `check_config.py`

```bash
python3 scripts/check_config.py
```

Returns config readiness without contacting Plex.

## `search_music.py`

```bash
python3 scripts/search_music.py --query "Massive Attack" --type artist --limit 5
```

Arguments:

- `--query` search text, required.
- `--type all|artist|album|track`, default `all`.
- `--limit`, default `5`, max `20`.
- `--timeout`, default from env or `15`.

Success payload:

```json
{
  "source": "Plex",
  "lookup_type": "music_search",
  "query": {"query": "Massive Attack", "type": "artist"},
  "num_found": 1,
  "results": [
    {
      "title": "Massive Attack",
      "type": "artist",
      "rating_key": "456",
      "library_section_title": "Music",
      "genres": ["Trip hop"],
      "external_ids": {"mbid": ["10ad..."]}
    }
  ]
}
```

## `get_music.py`

```bash
python3 scripts/get_music.py --rating-key 456 --include-children
```

Arguments:

- `--rating-key` Plex rating key, required.
- `--include-children` fetches `/library/metadata/{rating_key}/children` for
  artists/albums when available.
- `--children-limit`, default `50`, max `200`.
- `--timeout`, default from env or `15`.

Success payload includes `result` and, when requested, `children`.

## Error codes

- `CONFIG_ERROR`: missing Plex base URL or token.
- `INVALID_ARGUMENT`: invalid CLI argument.
- `INVALID_LIMIT`: limit outside supported range.
- `HTTP_ERROR`: Plex returned a non-success HTTP status.
- `NETWORK_ERROR`: Plex could not be reached.
- `INVALID_JSON_RESPONSE`: Plex did not return JSON.
- `NOT_FOUND`: requested rating key returned no metadata.
