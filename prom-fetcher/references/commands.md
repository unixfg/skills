# Command Reference

Use this file when you need exact command syntax, source-derived behavior, or troubleshooting details for the bundled `scripts/prom-fetcher/` project.

## Contents

- Build and install
- Configuration
- `query`
- `alerts`
- `config`
- Auth and token handling
- Common failures
- Source editing

## 1. Build and install

Run commands from `scripts/prom-fetcher/`.

Standard build:

```bash
make build
```

Direct Go build:

```bash
go build -o prom-fetcher .
```

Install on `PATH`:

```bash
make install
```

Notes:

- `make build` runs `go mod tidy` before `go build`.
- `make install` copies the binary into `~/.local/bin/prom-fetcher`.
- `make clean` removes the local binary from the source tree.
- `make test` runs `go test -v ./...`. The repo currently has no `_test.go` files, so this mainly catches compile regressions.
- `make build-dev` and `make build-static` exist for debug and static Linux builds.

## 2. Configuration

Typical local setup:

```bash
export PROM_FETCHER_CLIENT_SECRET="$(cat ~/.openclaw/secrets/keycloak-auth)"
```

Default config file:

```text
~/.config/prom-fetcher/config.yaml
```

Example file:

```yaml
keycloak_url: https://auth.doesthings.io
keycloak_realm: doesthings.io
client_id: prom-fetcher
prometheus_url: https://prometheus.doesthings.io
```

Custom config file:

```bash
./prom-fetcher --config /path/to/config.yaml config
```

Supported keys from the source:

- `keycloak_url`
- `keycloak_realm`
- `client_id`
- `prometheus_url`
- `client_secret`

Environment overrides use the `PROM_FETCHER_` prefix, for example:

- `PROM_FETCHER_CLIENT_SECRET`
- `PROM_FETCHER_KEYCLOAK_URL`
- `PROM_FETCHER_KEYCLOAK_REALM`
- `PROM_FETCHER_CLIENT_ID`
- `PROM_FETCHER_PROMETHEUS_URL`

Effective precedence is:

1. Built-in defaults
2. Config file values
3. `PROM_FETCHER_*` environment variables

`--config` changes which config file is loaded; it does not bypass environment overrides.

## 3. `query`

Run an instant PromQL query:

```bash
./prom-fetcher query 'up{job="prometheus"}'
```

Behavior from `main.go`:

- Sends `GET /api/v1/query?query=<promql>` to `prometheus_url`
- Adds `Authorization: Bearer <token>`
- Uses a 30 second HTTP timeout
- Prints indented JSON from the Prometheus API response

Typical failure modes:

- Token acquisition fails before the Prometheus request
- Prometheus returns a non-200 status and the CLI prints the response body
- Response JSON cannot be decoded

## 4. `alerts`

List alert series through the same query endpoint:

```bash
./prom-fetcher alerts
./prom-fetcher alerts --state pending
```

Behavior:

- Default query is `ALERTS{alertstate="firing"}`
- `--state` rewrites the query to `ALERTS{alertstate="<state>"}`
- The flag default is `firing`
- Output format is the same indented JSON object used by `query`

The current code does not validate the `--state` value before interpolating it into the query.

## 5. `config`

Inspect resolved non-secret settings:

```bash
./prom-fetcher config
```

Behavior:

- Prints `Configuration:` followed by YAML
- Shows `keycloak_url`, `keycloak_realm`, `client_id`, and `prometheus_url`
- Never prints the actual secret
- Adds one of these status lines:
  - `Client secret: set via PROM_FETCHER_CLIENT_SECRET`
  - `Client secret: NOT SET (set PROM_FETCHER_CLIENT_SECRET)`

## 6. Auth and token handling

Token flow:

1. Read cached token from `~/.prom-fetcher-token`
2. Treat it as expired 60 seconds early
3. If needed, request a new token from `https://<keycloak_url>/realms/<realm>/protocol/openid-connect/token`
4. Cache the new token with file mode `0600`

If the cached token looks wrong or stale, delete `~/.prom-fetcher-token` and retry.

oauth2-proxy requirement:

- Prometheus access only works when oauth2-proxy accepts JWT bearer tokens.
- The repo README calls out `--skip-jwt-bearer-tokens=true`.

## 7. Common failures

`PROM_FETCHER_CLIENT_SECRET environment variable not set`

- Export `PROM_FETCHER_CLIENT_SECRET`
- Or provide `client_secret` through another Viper source such as the config file
- Note that the error text only mentions the environment variable even though Viper can read other sources

`Error reading config: ...`

- The specified config file is unreadable or invalid YAML
- Re-run with `./prom-fetcher --config /path/to/config.yaml config` after fixing the file

`token request failed: 401 Unauthorized`

- `client_id`, `client_secret`, or realm settings do not match the Keycloak client
- Confirm the client has service-account access enabled

`prometheus returned 401 Unauthorized`

- oauth2-proxy is rejecting the bearer token
- The token was minted successfully but does not have access to the upstream
- Clear `~/.prom-fetcher-token` after changing auth settings

`request failed: ...`

- Network or TLS problem reaching Keycloak or Prometheus
- Confirm the configured URLs and local connectivity

## 8. Source editing

The CLI is currently a single-file Cobra app:

- `main.go` contains all commands and auth helpers
- `Makefile` wraps the common build targets
- `config.yaml.example` is the reference config
- `go.mod` and `go.sum` pin the bundled module dependencies

When adding a command:

1. Add a new function that returns `*cobra.Command`
2. Register it with `rootCmd.AddCommand(...)` in `init()`
3. Re-run `gofmt -w main.go`
4. Re-run `go test ./...` and `make build`
