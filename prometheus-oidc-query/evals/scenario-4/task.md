# Validate configuration before attempting a query

Use the local `prometheus-oidc-query` tile resources.

Goal:
- confirm whether the current environment is ready for a query
- report missing or malformed configuration values
- avoid making any network request if the configuration is already invalid

Constraints:
- run `python3 scripts/check_config.py` first and report the full `errors` list or `valid: true`.
- rely on the local validation/reporting commands.
- never echo secrets back to the user.

Validate environment-driven Prometheus and OAuth2 configuration before making network requests.
