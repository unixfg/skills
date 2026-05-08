---
name: openclaw-vault
description: >
  Use when working with a local HashiCorp Vault instance that backs OpenClaw
  secrets: storing, retrieving, deleting, checking health, unsealing, managing
  a local service or container, or troubleshooting OpenClaw secret access.
---

# OpenClaw Vault

## Scope

Use this skill for a local Vault deployment used by OpenClaw. Assume details are
deployment-specific and discover them before changing anything.

Default assumptions when local config does not say otherwise:

- Vault API: `VAULT_ADDR`, defaulting to `http://127.0.0.1:8200`
- KV engine: KV v2
- KV mount: `VAULT_KV_MOUNT`, defaulting to `openclaw`
- Auth: `VAULT_TOKEN`, `VAULT_TOKEN_FILE`, or a local `vault` wrapper

## Ground Rules

- Keep Vault local. Do not expose it through public binds, proxies, ingress, or
  firewall changes unless the operator explicitly requests that architecture.
- Never print or paste root tokens, unseal keys, or scoped tokens. Avoid
  printing stored secret values unless the user explicitly asks to retrieve one
  in a private/local context; otherwise mention paths, fields, and status only.
- Prefer a local `vault` wrapper or Vault CLI when available. It should obtain
  the token from the environment or a token file without putting secrets in
  process arguments.
- Use user-level service and rootless container commands when the deployment is
  rootless. Use `sudo` only for system-level service, firewall, or sysctl work.
- For KV v2 HTTP API calls, remember that the API path includes `/data/` even
  when the logical secret path does not.

## Discover State

Run small checks before changing configuration:

```sh
export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
export VAULT_KV_MOUNT="${VAULT_KV_MOUNT:-openclaw}"

command -v vault
vault status
curl --noproxy '*' -sS "$VAULT_ADDR/v1/sys/health" | jq '{initialized, sealed, version}'
systemctl --user list-units '*vault*' --no-pager
podman ps --format '{{.Names}} {{.Status}}' | rg -i vault
```

If OpenClaw config is available, inspect only non-secret Vault settings such as
address, mount, token-file path, service name, or container name. Do not display
token contents.

## Common Secret Operations

Use `key=-` to read the secret value from stdin without placing it in shell
history or process arguments:

```sh
read -rsp "Secret value: " SECRET_VALUE
echo
printf '%s' "$SECRET_VALUE" | vault kv put -mount="$VAULT_KV_MOUNT" service/name key=-
unset SECRET_VALUE
```

Read a field without printing metadata:

```sh
vault kv get -mount="$VAULT_KV_MOUNT" -field=key service/name
```

Delete a secret:

```sh
vault kv delete -mount="$VAULT_KV_MOUNT" service/name
```

For a non-secret smoke test, write and remove a temporary path:

```sh
path="smoke/openclaw-vault-$(date +%s)"
printf '%s' "smoke-value" | vault kv put -mount="$VAULT_KV_MOUNT" "$path" key=-
vault kv get -mount="$VAULT_KV_MOUNT" -field=key "$path"
vault kv delete -mount="$VAULT_KV_MOUNT" "$path"
```

## HTTP API Fallback

Use the HTTP API when the local CLI wrapper is unavailable or broken. Keep the
token in a temporary curl config instead of a command argument:

```sh
export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
export VAULT_KV_MOUNT="${VAULT_KV_MOUNT:-openclaw}"
: "${VAULT_TOKEN_FILE:?Set VAULT_TOKEN_FILE to a readable token file}"
secret_path="service/name"

read -rsp "Secret value: " SECRET_VALUE
echo

headers="$(mktemp)"
body="$(mktemp)"

printf 'header = "X-Vault-Token: %s"\n' "$(cat "$VAULT_TOKEN_FILE")" > "$headers"
jq -n --arg v "$SECRET_VALUE" '{data: {key: $v}}' > "$body"

curl --noproxy '*' -sS \
  --config "$headers" \
  --request POST \
  --data @"$body" \
  "$VAULT_ADDR/v1/$VAULT_KV_MOUNT/data/$secret_path"

rm -f "$headers" "$body"
unset SECRET_VALUE
```

Read back the logical path through the KV v2 API path:

```sh
headers="$(mktemp)"
printf 'header = "X-Vault-Token: %s"\n' "$(cat "$VAULT_TOKEN_FILE")" > "$headers"

curl --noproxy '*' -sS \
  --config "$headers" \
  "$VAULT_ADDR/v1/$VAULT_KV_MOUNT/data/$secret_path" \
  | jq '.data.data'

rm -f "$headers"
```

## Unseal

Only unseal when `vault status` or `/v1/sys/health` reports `sealed: true`.
Read the unseal key from a file or protected input without displaying it:

```sh
request="$(mktemp)"
jq -Rs '{key: (rtrimstr("\n"))}' < "$VAULT_UNSEAL_KEY_FILE" > "$request"

curl --noproxy '*' -sS \
  --request PUT \
  --data @"$request" \
  "$VAULT_ADDR/v1/sys/unseal" \
  | jq '{initialized, sealed, version}'

rm -f "$request"
vault status
```

## OpenClaw Integration Checks

OpenClaw should receive Vault settings through environment variables or config,
typically including:

- `VAULT_ADDR`
- `VAULT_TOKEN_FILE` or another non-interactive token source
- KV mount or logical secret path conventions

When troubleshooting an OpenClaw gateway, verify that the process inherited
Vault-related environment variables without printing token contents:

```sh
pid="$(pgrep -f 'openclaw.*gateway' | head -n1)"
tr '\0' '\n' < "/proc/$pid/environ" | rg '^VAULT_(ADDR|TOKEN_FILE|KV_MOUNT)='
```

If OpenClaw started before Vault settings changed, restart the relevant
OpenClaw service or process after confirming the intended service name.
