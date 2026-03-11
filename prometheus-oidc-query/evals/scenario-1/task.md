# Query a Prometheus-compatible API with client credentials

Use the local `prometheus-oidc-query` tile resources.

Goal:
- validate the configuration first
- run an instant PromQL query for `up`
- explain whether authentication came from cache or from the token endpoint

Constraints:
- use the bundled scripts in `./scripts/`
- do not invent default URLs, client IDs, or secrets
- explain the concrete command used
