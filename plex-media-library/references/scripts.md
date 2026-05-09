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
- Use `search_media.py` for title searches. Use `list_media.py` for wildcard,
  latest/newest TV, newest episode, recently added, and broad inventory
  questions.

## `check_config.py`

```bash
python3 scripts/check_config.py
```

Returns:

```json
{
  "valid": true,
  "errors": [],
  "required_env": {
    "PLEX_TOKEN": true,
    "PLEX_BASE_URL_or_PLEX_URL": true
  },
  "base_url": "http://plex.plex.svc.cluster.local:32400",
  "client_identifier_configured": false
}
```

## `search_media.py`

```bash
python3 scripts/search_media.py --query "The Expanse" --type tv --limit 5
```

Arguments:

- `--query` search text, required.
- `--type all|movie|tv|show`, default `all`.
- `--limit`, default `5`, max `20`.
- `--timeout`, default from env or `15`.
- `--query "*"` returns `INVALID_ARGUMENT`; it is not an all-items search.

Success payload:

```json
{
  "source": "Plex",
  "lookup_type": "media_search",
  "query": {"query": "The Expanse", "type": "tv"},
  "num_found": 1,
  "results": [
    {
      "title": "The Expanse",
      "type": "show",
      "year": 2015,
      "rating_key": "123",
      "library_section_title": "TV Shows",
      "watched": true,
      "external_ids": {"imdb": ["tt3230854"], "tvdb": ["280619"]},
      "source_urls": {"imdb": "https://www.imdb.com/title/tt3230854/"}
    }
  ]
}
```

## `list_media.py`

```bash
python3 scripts/list_media.py --type episode --sort originallyAvailableAt:desc --limit 10
python3 scripts/list_media.py --type tv --latest-episodes --limit 5
python3 scripts/list_media.py --type episode --sort addedAt:desc --limit 10
```

Arguments:

- `--type movie|tv|show|season|episode`, required.
- `--latest-episodes` lists episodes from the TV library and defaults `--sort`
  to `originallyAvailableAt:desc`.
- `--sort`, optional Plex sort such as `originallyAvailableAt:desc` or
  `addedAt:desc`.
- `--limit`, default `5`, max `20`.
- `--timeout`, default from env or `15`.

Success payload:

```json
{
  "source": "Plex",
  "lookup_type": "media_list",
  "query": {
    "type": "episode",
    "section_key": "2",
    "section_title": "TV Shows",
    "sort": "originallyAvailableAt:desc",
    "latest_episodes": true
  },
  "num_found": 1,
  "results": [
    {
      "title": "One Way Out",
      "type": "episode",
      "grandparent_title": "Andor",
      "parent_title": "Season 1",
      "season_index": 1,
      "episode_index": 10,
      "originally_available_at": "2022-11-09",
      "added_at": 1700000000
    }
  ]
}
```

## `get_media.py`

```bash
python3 scripts/get_media.py --rating-key 123 --include-children
```

Arguments:

- `--rating-key` Plex rating key, required.
- `--include-children` fetches `/library/metadata/{rating_key}/children` for
  shows/seasons when available.
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
