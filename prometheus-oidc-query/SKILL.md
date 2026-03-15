---
name: prometheus-oidc-query
description: >
  Use when the user asks for Prometheus metrics, monitoring data, or Grafana/PromQL
  query support on an OAuth2/OIDC-protected Prometheus-compatible endpoint. This skill
  helps run `prom_query.py` instant queries, inspect `ALERTS` states, refresh/check OAuth2
  tokens, and validate query/config prerequisites before making network calls.
compatibility: >
  Requires outbound access to a Prometheus-compatible HTTP API and the token endpoint.
  This skill is read-only and does not modify cluster, token, or metric data.
---

# prometheus-oidc-query

Use this skill when a user asks to query Prometheus or inspect alert state through
an OAuth2/OIDC-protected Prometheus-compatible endpoint.

## Workflow

1. Validate configuration with `python3 scripts/check_config.py` (or `python3 scripts/prom_query.py config`).
2. If configuration is invalid, report concrete missing/malformed values and stop; do not invent values.
3. If valid, run the exact helper needed for the user intent:
   - `python3 scripts/prom_query.py query --expr '<promql>'` for instant queries.
   - `python3 scripts/prom_query.py alerts --state firing|pending|inactive` for alert-state checks.
   - `python3 scripts/prom_query.py token --refresh` for fresh token inspection/debugging.
4. Return results using values from script output (for example `query`, `state`, `auth_source`, and `response`).
5. Never suggest custom query paths like raw `curl` calls unless scripts are unavailable and the user explicitly asks for a workaround.

## Environment

Required:

- `PROM_QUERY_PROMETHEUS_URL`
- `PROM_QUERY_TOKEN_URL`
- `PROM_QUERY_CLIENT_ID`
- `PROM_QUERY_CLIENT_SECRET`

Optional:

- `PROM_QUERY_SCOPE`
- `PROM_QUERY_CA_BUNDLE`
- `PROM_QUERY_TIMEOUT` (seconds)

## Decision tree

- User needs token validation/troubleshooting only → run `config`/`token` first.
- User asks for a direct PromQL expression → use `query` with that expression.
- User asks about alert state or mentions `ALERTS` → use `alerts` subcommand.
- User needs environment readiness before any live call → start with `check_config.py`.
- User asks for examples / setup details → use `docs/index.md`.

## Orchestration (preferred flow)

1. **Preflight:** run `python3 scripts/check_config.py` and capture `valid` + `errors`.
   - If `valid` is `false`, report the exact `errors` list and do not make any network calls.
2. **Query path:** call `query` only after preflight success.
   - Report query used in output (`query` field) and token origin (`auth_source`).
3. **No-match/empty result handling:** report empty `response.result` honestly; do not infer metrics or invent values.
4. **Token behavior:** if auth source is `token_endpoint` in first run or cache misses, mention that and recommend `python3 scripts/prom_query.py token` checks.
5. **Retry/fallback:**
   - If receiving token errors, retry with `python3 scripts/prom_query.py token --refresh` after confirming credentials.
   - If Prometheus API returns errors, call out endpoint and response body before advising config fixes.

## Result handling

- Keep secrets redacted (`client_secret` and raw tokens are not printed).
- Scripts return machine-readable JSON payloads.
- On script failures, return `{ "error": ..., "error_code": ... }` with non-zero exit code.
- For command reference and exact payload fields, see [references/scripts.md](references/scripts.md).

For exact command syntax, output structures, and error codes, use [references/scripts.md](references/scripts.md).
