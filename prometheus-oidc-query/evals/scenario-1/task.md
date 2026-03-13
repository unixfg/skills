# Query a Prometheus-compatible API with client credentials

Use the local `prometheus-oidc-query` tile resources.

Goal:
- validate the configuration first
- run an instant PromQL query for `up`
- explain whether authentication came from cache or from the token endpoint

Constraints:
- run `python3 scripts/check_config.py` and inspect `valid` before any live query.
- use only bundled scripts in `./scripts/`.
- do not invent default URLs, client IDs, or secrets.
- include the concrete command used when possible.
- if configuration is invalid, report what is missing and do not attempt the query; also state that auth_source is not determinable until a successful query.

Run a standard PromQL instant query with the bundled helper script and explain token-cache behavior.
