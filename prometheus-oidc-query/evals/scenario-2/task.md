# Diagnose token endpoint misconfiguration

Use the local `prometheus-oidc-query` tile resources.

Goal:
- determine why token acquisition is failing
- identify which configuration value is most likely wrong
- recommend the next command to confirm the diagnosis

Constraints:
- start with validation tooling (`python3 scripts/check_config.py` or `python3 scripts/prom_query.py config`).
- distinguish token endpoint failures from Prometheus API failures.
- when needed, run `python3 scripts/prom_query.py token --refresh` and report the result.
- do not suggest editing the script unless the issue is clearly in the code.

Diagnose token endpoint and client-credentials misconfiguration using the tile's validation and token inspection flow.
