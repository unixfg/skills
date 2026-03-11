---
name: prometheus-oidc-query
description: "Run PromQL queries, inspect alert state, validate OAuth2 or OIDC client-credentials configuration, or troubleshoot bearer-token access to Prometheus-compatible APIs. Use when the user needs to query Prometheus through a token endpoint, check whether auth or TLS settings are correct, or inspect alert state without rebuilding a custom CLI."
---

# prometheus-oidc-query

Use the bundled Python scripts instead of re-implementing token handling or Prometheus HTTP requests.

## Workflow

1. Run `python3 scripts/check_config.py` when the user may have missing or malformed environment variables.
2. Run `python3 scripts/prom_query.py config` to inspect the redacted effective configuration.
3. Run `python3 scripts/prom_query.py query --expr '<promql>'` for instant PromQL queries.
4. Run `python3 scripts/prom_query.py alerts --state firing|pending|inactive` to inspect alert state.
5. Run `python3 scripts/prom_query.py token --refresh` only when debugging token acquisition or cache issues.

Read [docs/index.md](docs/index.md) when you need setup examples, configuration reference, or troubleshooting details.

## Configuration

Set these environment variables before querying:

- `PROM_QUERY_PROMETHEUS_URL`
- `PROM_QUERY_TOKEN_URL`
- `PROM_QUERY_CLIENT_ID`
- `PROM_QUERY_CLIENT_SECRET`

Optional:

- `PROM_QUERY_SCOPE`
- `PROM_QUERY_CA_BUNDLE`
- `PROM_QUERY_TIMEOUT`

## Result Handling

- `query` prints a JSON object with the submitted expression and the Prometheus API response body.
- `alerts` prints a JSON object with the alert state, generated expression, and the Prometheus API response body.
- `config` prints a redacted configuration and validation report.
- `token` prints cache and expiry metadata without exposing the raw token.
- `check_config.py` prints a validation report and exits non-zero when the required configuration is incomplete or invalid.

## Operating Rules

- Prefer `check_config.py` before deeper debugging when the user does not know which variable is wrong.
- Treat URLs, client IDs, scopes, and secrets as user-provided inputs. Do not invent environment-specific defaults.
- Never echo the raw client secret or access token.
- Distinguish token acquisition failures from Prometheus API failures in the explanation.
- Treat `alerts` as a convenience wrapper around `ALERTS{alertstate="<state>"}`.
