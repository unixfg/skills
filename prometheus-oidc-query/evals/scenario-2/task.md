# Diagnose token endpoint misconfiguration

Use the local `prometheus-oidc-query` tile resources.

Goal:
- determine why token acquisition is failing
- identify which configuration value is most likely wrong
- recommend the next command to confirm the diagnosis

Constraints:
- start with the local validation tooling
- distinguish token endpoint failures from Prometheus API failures
- do not suggest editing the script unless the issue is clearly in the code
