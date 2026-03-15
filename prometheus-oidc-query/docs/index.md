# Prometheus OIDC Query

Use this tile to run instant PromQL queries against a Prometheus-compatible HTTP API using OAuth2 or OIDC client credentials.

## Quickstart

Set the required environment variables:

```bash
export PROM_QUERY_PROMETHEUS_URL="https://prometheus.example.com"
export PROM_QUERY_TOKEN_URL="https://auth.example.com/oauth/token"
export PROM_QUERY_CLIENT_ID="prometheus-reader"
export PROM_QUERY_CLIENT_SECRET="replace-me"
```

Validate the configuration before querying:

```bash
python3 scripts/check_config.py
python3 scripts/prom_query.py config
```

Run the full smoke test suite against a live configuration:

```bash
./scripts/smoke_test.sh
```

Run an instant query:

```bash
python3 scripts/prom_query.py query --expr 'up'
```

Inspect alerts:

```bash
python3 scripts/prom_query.py alerts --state firing
```

## Commands

`python3 scripts/prom_query.py query --expr '<promql>'`
- Submit an instant query to `PROM_QUERY_PROMETHEUS_URL/api/v1/query`.

`python3 scripts/prom_query.py alerts --state firing|pending|inactive`
- Query `ALERTS{alertstate="<state>"}` through the same endpoint.

`python3 scripts/prom_query.py config`
- Print the redacted effective configuration and validation report.

`python3 scripts/prom_query.py token [--refresh]`
- Inspect token cache metadata. Use `--refresh` to bypass the cache.

`python3 scripts/check_config.py`
- Validate the required environment variables and URL syntax. Exit non-zero when invalid.

## Configuration Reference

Required environment variables:

- `PROM_QUERY_PROMETHEUS_URL`: Base URL for the Prometheus-compatible HTTP API.
- `PROM_QUERY_TOKEN_URL`: Token endpoint that accepts OAuth2 client credentials.
- `PROM_QUERY_CLIENT_ID`: OAuth2 client ID.
- `PROM_QUERY_CLIENT_SECRET`: OAuth2 client secret.

Optional environment variables:

- `PROM_QUERY_SCOPE`: Space-delimited scope passed to the token endpoint.
- `PROM_QUERY_CA_BUNDLE`: Path to a custom CA bundle for TLS validation.
- `PROM_QUERY_TIMEOUT`: Request timeout in seconds. Defaults to `30`.
- `XDG_CACHE_HOME`: Overrides the cache base directory used for token metadata.

The token cache lives at `$XDG_CACHE_HOME/prometheus-oidc-query/token-cache.json` or `~/.cache/prometheus-oidc-query/token-cache.json` when `XDG_CACHE_HOME` is unset.

## Output Shape

`query` and `alerts` return JSON objects with:

- `query`: The submitted PromQL expression.
- `response`: The decoded Prometheus API response body.

`alerts` also includes `state`.

`config` and `check_config.py` return JSON with:

- `valid`: Boolean validation result.
- `errors`: List of validation problems.
- `resolved_config`: Redacted effective settings, including URLs, client ID, timeout, and whether a client secret is set.
- `required_env`: Presence map for required variables.
- `optional_env`: Redacted optional settings.
- `cache`: Cache path metadata.

`token` returns JSON with:

- `source`: `cache` or `token_endpoint`
- `expires_at`
- `expires_in_seconds`
- `token_type`
- `scope`
- `cache_path`

## Troubleshooting

401 or 403 during token acquisition:
- Verify `PROM_QUERY_TOKEN_URL`, client ID, client secret, and optional scope.

401 or 403 from Prometheus:
- Confirm the token is accepted by the upstream or any proxy in front of Prometheus.

TLS failures:
- Verify the target URL certificate chain or set `PROM_QUERY_CA_BUNDLE` to the correct CA bundle.

Timeouts:
- Increase `PROM_QUERY_TIMEOUT` and verify network reachability to both the token endpoint and Prometheus.

Empty Prometheus results:
- Re-run the command with a simpler query such as `up` before assuming auth is broken.

## Migration Note

This tile replaces the old internal `prom-fetcher` package. It intentionally removes:

- bundled Go source code and build steps
- machine-specific secret paths
- Keycloak- or proxy-specific defaults
- `PROM_FETCHER_*` environment naming


## Command Contracts

For exact arguments, output schema, and error codes, see [references/scripts.md](../references/scripts.md).
