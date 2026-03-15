# Script Reference

Use this file for exact CLI syntax, expected payloads, and error handling.

## Shared contracts

These conventions apply to all bundled scripts:

- Non-interactive CLI only.
- `--help` is available and preferred over guessing flags.
- All successful command output is JSON on **stdout**.
- Errors are JSON on **stdout**:
  - `{"error": "...", "error_code": "..."}`
- Exit status is non-zero for failures.

## 1. `scripts/prom_query.py`

Top-level help:

```bash
python3 scripts/prom_query.py -h
```

### `config`

```bash
python3 scripts/prom_query.py config
```

Returns configuration validation and redacted values.

Success example:

```json
{
  "cache": {...},
  "errors": [],
  "optional_env": {...},
  "required_env": {...},
  "resolved_config": {...},
  "valid": true
}
```

Typical validation failure (`valid: false`) includes all issues in `errors` and exits non-zero.

### `query`

```bash
python3 scripts/prom_query.py query --expr 'up'
```

Output:

```json
{
  "auth_source": "cache|token_endpoint",
  "query": "up",
  "response": {"status": "success", "data": {...}}
}
```

### `alerts`

```bash
python3 scripts/prom_query.py alerts --state pending
```

Behavior: emits the same structure as `query` and adds `state`.
Generated expression is `ALERTS{alertstate="<state>"}`.

### `token`

```bash
python3 scripts/prom_query.py token
python3 scripts/prom_query.py token --refresh
```

Returns metadata for cached/fresh token source.

```json
{
  "cache_path": ".../token-cache.json",
  "expires_at": 1234567890,
  "expires_in_seconds": 3600,
  "scope": "read",
  "source": "cache",
  "token_type": "Bearer"
}
```

## 2. `scripts/check_config.py`

Validate local config and emit the same validation payload shape as
`prom_query.py config`.

```bash
python3 scripts/check_config.py
```

On invalid timeout format it returns:

```json
{
  "error": "PROM_QUERY_TIMEOUT must be a number",
  "error_code": "INVALID_TIMEOUT"
}
```

## 3. `scripts/smoke_test.sh`

Run local unit tests plus a live end-to-end smoke pass against the configured
Prometheus and token endpoints.

```bash
./scripts/smoke_test.sh
```

Required environment variables are the same as `prom_query.py`:

- `PROM_QUERY_PROMETHEUS_URL`
- `PROM_QUERY_TOKEN_URL`
- `PROM_QUERY_CLIENT_ID`
- `PROM_QUERY_CLIENT_SECRET`

The script runs, in order:

1. `python3 -m unittest -v tests/test_prom_query.py`
2. `python3 scripts/check_config.py`
3. `python3 scripts/prom_query.py config`
4. `python3 scripts/prom_query.py token --refresh`
5. `python3 scripts/prom_query.py token`
6. `python3 scripts/prom_query.py query --expr 'up'`
7. `python3 scripts/prom_query.py alerts --state firing`
8. `python3 scripts/prom_query.py alerts --state pending`
9. `python3 scripts/prom_query.py alerts --state inactive`

## Known error codes

- `INVALID_TIMEOUT`
- `INVALID_CONFIG`
- `TOKEN_REQUEST_FAILED`
- `PROMETHEUS_REQUEST_FAILED`
- `TOKEN_RESPONSE_INVALID`
- `INVALID_JSON_RESPONSE`
- `INVALID_COMMAND`
- `SCRIPT_ERROR`

`script` errors are in the form `{ "error": "...", "error_code": "..." }`.
