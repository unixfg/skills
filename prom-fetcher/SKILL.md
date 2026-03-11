---
name: prom-fetcher
description: "Use when the user needs to build, configure, troubleshoot, or run the prom-fetcher Go CLI for Prometheus queries through Keycloak-authenticated oauth2-proxy."
---

# prom-fetcher

Use this skill when the user is working with the bundled `prom-fetcher` Go CLI in `scripts/prom-fetcher/`: build it from source, install it locally, inspect config, run PromQL queries, or troubleshoot Keycloak and oauth2-proxy access.

## Execution Model

This skill is command-driven.

- Use the bundled source tree in `scripts/prom-fetcher/` as the default working copy.
- Prefer running commands there over restating Go, Prometheus, or Keycloak basics.
- Read [references/commands.md](references/commands.md) when the task needs exact CLI syntax, config precedence, source layout, or failure handling.
- The bundled project has no `_test.go` files, so `go test ./...` is a compile smoke test, not behavioral coverage.

## Environment

- Bundled source: `scripts/prom-fetcher/`
- Default config: `~/.config/prom-fetcher/config.yaml`
- Bundled example config: `scripts/prom-fetcher/config.yaml.example`
- Token cache: `~/.prom-fetcher-token`
- Secret source on this machine: `~/.openclaw/secrets/keycloak-auth`

`prom-fetcher` uses Viper, so `PROM_FETCHER_*` environment variables override file-backed settings. On this machine, the usual setup is exporting `PROM_FETCHER_CLIENT_SECRET` from `~/.openclaw/secrets/keycloak-auth`.

## Quick Decision Tree

**"Build or rebuild the CLI"** -> `make build`

**"Install it on PATH"** -> `make install`

**"Run without installing"** -> `./prom-fetcher <subcommand>`

**"Execute a PromQL query"** -> `./prom-fetcher query '<promql>'`

**"List alerts"** -> `./prom-fetcher alerts --state firing|pending`

**"Show resolved config"** -> `./prom-fetcher config`

**"Update dependencies after code changes"** -> `go get -u ./...`, then `go mod tidy`, then `go test ./...`

**"Auth or 401 issue"** -> confirm `PROM_FETCHER_CLIENT_SECRET`, inspect or clear `~/.prom-fetcher-token`, and verify oauth2-proxy accepts bearer tokens

**"Need exact syntax or troubleshooting details"** -> read [references/commands.md](references/commands.md)

## Common Workflows

### Build and run a query

```bash
cd scripts/prom-fetcher
export PROM_FETCHER_CLIENT_SECRET="$(cat ~/.openclaw/secrets/keycloak-auth)"
make build
./prom-fetcher query 'up{job="prometheus"}'
```

If `make build` fails, run `go mod tidy` and retry. If the query fails with auth errors, use the troubleshooting notes in [references/commands.md](references/commands.md).

### Install and inspect config

```bash
cd scripts/prom-fetcher
make install
prom-fetcher config
```

Use `--config /path/to/config.yaml` when the user wants a nondefault config file.

### Update the CLI after source changes

```bash
cd scripts/prom-fetcher
gofmt -w main.go
go test ./...
make build
```

All current commands live in `main.go`. New subcommands follow the existing `cobra.Command` pattern and must be registered in `init()`.

## Notes

- `query` and `alerts` print indented JSON from Prometheus's `/api/v1/query` endpoint.
- `config` prints YAML without the secret, then prints whether a client secret is set.
- Access tokens are cached locally and treated as expired 60 seconds early.
- oauth2-proxy must allow JWT bearer tokens or Prometheus requests will fail even with a valid Keycloak token.
